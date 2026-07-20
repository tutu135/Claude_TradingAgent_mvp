from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "scripts" / "normalize_research_facts.py"


def run_cli(
    args: list[str], *, bind_upstream_fixture: bool = True
) -> subprocess.CompletedProcess[str]:
    if (
        bind_upstream_fixture
        and "--context-file" in args
        and "--retrieval-file" in args
    ):
        context_file = Path(args[args.index("--context-file") + 1])
        retrieval_file = Path(args[args.index("--retrieval-file") + 1])
        retrieval = yaml.safe_load(retrieval_file.read_text(encoding="utf-8"))
        query_rule_version = retrieval.setdefault(
            "query_rule_version", "context-fixture-v1"
        )
        rows = [
            json.loads(line)
            for line in context_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        for row in rows:
            row.setdefault("query_rule_version", query_rule_version)
        context_file.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        canonical = "".join(
            json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
            for row in rows
        )
        context_hash = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        retrieval.setdefault(
            "clean_rebuild",
            {
                "first": {"context_hash": context_hash},
                "second": {"context_hash": context_hash},
            },
        )
        retrieval_file.write_text(
            yaml.safe_dump(retrieval, sort_keys=False), encoding="utf-8"
        )
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class NormalizeResearchFactsCliTests(unittest.TestCase):
    def test_rejects_retrieval_without_required_context_binding_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            context_file = workspace / "context.jsonl"
            context_file.write_text("", encoding="utf-8")
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "rule_version": "normalization-binding-required-v1",
                        "mapping_version": "mapping-binding-required-v1",
                    }
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(workspace / "output"),
                ],
                bind_upstream_fixture=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("required context binding metadata", result.stderr)

    def test_multiple_unbound_context_periods_remain_ambiguous(self) -> None:
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from normalize_research_facts import period_for_position, periods_from_chunk_context

        periods = periods_from_chunk_context(
            {
                "numeric_context": {
                    "periods": ["2025 Q1", "2026 Q1"],
                    "column_periods": [],
                }
            }
        )

        period = period_for_position(periods, 0)

        self.assertEqual(period["period_mapping_status"], "AMBIGUOUS")
        self.assertIsNone(period["period_start"])
        self.assertIsNone(period["period_end"])

    def test_reads_only_candidate_context_and_emits_atomic_decimal_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            context_file = workspace / "context.jsonl"
            candidate = {
                "snapshot_id": "smic-a283e95e2c9e8068",
                "query_rule_version": "context-fixture-v1",
                "chunk_id": "CHUNK_CANDIDATE",
                "material_id": "MATERIAL_SMIC_FIXTURE",
                "structure_type": "TRANSCRIPT_SPEAKER_TURN",
                "content_locator": {
                    "section": "Earnings Call Transcript",
                    "paragraph_locator": "paragraph:p[21]",
                },
                "text": "Revenue was $2,505.5 million in Q1 2026, and gross margin was 20.1%.",
                "text_hash": "sha256:fixture",
                "candidate_context": True,
                "matched_query_ids": ["D1_EN"],
                "selection_reasons": ["DIRECT_HIT"],
                "numeric_context": {"headers": [], "units": [], "periods": [], "footnotes": []},
            }
            excluded = {
                **candidate,
                "chunk_id": "CHUNK_NOT_CANDIDATE",
                "text": "Revenue was $999.0 million in Q4 2025.",
                "candidate_context": False,
            }
            context_file.write_text(
                json.dumps(candidate) + "\n" + json.dumps(excluded) + "\n",
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "retrieval_status": "PASS",
                        "query_rule_version": "context-fixture-v1",
                    }
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "rule_version": "normalization-fixture-v1",
                        "mapping_version": "mapping-fixture-v1",
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_REVENUE_FIXTURE",
                                "metric_id": "REVENUE",
                                "aliases": ["revenue"],
                            },
                            {
                                "rule_id": "METRIC_GROSS_MARGIN_FIXTURE",
                                "metric_id": "GROSS_MARGIN",
                                "aliases": ["gross margin"],
                            },
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            existing_gaps_file = workspace / "gaps.yaml"
            existing_gaps_file.write_text(
                yaml.safe_dump(
                    {"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}
                ),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(existing_gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(
                [fact["record_kind"] for fact in facts],
                ["TEXT_PROPOSITION", "NUMERIC_OBSERVATION", "NUMERIC_OBSERVATION"],
            )
            self.assertTrue(all(fact["chunk_id"] == "CHUNK_CANDIDATE" for fact in facts))
            self.assertTrue(all(fact["claim_type"] == "UNASSESSED" for fact in facts))
            revenue = next(fact for fact in facts if fact.get("metric_id") == "REVENUE")
            margin = next(fact for fact in facts if fact.get("metric_id") == "GROSS_MARGIN")
            self.assertEqual(revenue["raw_value_text"], "$2,505.5 million")
            self.assertEqual(revenue["raw_numeric_value"], "2505.5")
            self.assertEqual(revenue["raw_currency"], "USD")
            self.assertEqual(revenue["raw_scale_factor"], "1000000")
            self.assertEqual(revenue["base_unit_value"], "2505500000.0")
            self.assertEqual(revenue["period_type"], "SINGLE_QUARTER")
            self.assertEqual(revenue["period_start"], "2026-01-01")
            self.assertEqual(revenue["period_end"], "2026-03-31")
            self.assertEqual(margin["raw_value_text"], "20.1%")
            self.assertEqual(margin["raw_unit"], "PERCENT")
            self.assertIsNone(margin["base_unit_value"])
            self.assertNotIn("999.0", (output_dir / "normalized-facts.jsonl").read_text(encoding="utf-8"))

    def test_table_context_preserves_parentheses_zero_na_and_dash_without_inventing_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                json.dumps(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "chunk_id": "CHUNK_TABLE",
                        "material_id": "MATERIAL_SMIC_FIXTURE",
                        "structure_type": "PDF_TABLE",
                        "content_locator": {"page_number": 10, "table_number": 1},
                        "text": "Reported values\t(12.0)\t0\tN/A\t—",
                        "text_hash": "sha256:fixture-table",
                        "candidate_context": True,
                        "matched_query_ids": ["G_ADJUSTMENT_BRIDGE_EN"],
                        "selection_reasons": ["DIRECT_HIT"],
                        "numeric_context": {
                            "headers": ["USD million", "2025"],
                            "column_headers": [
                                "Reported values",
                                "Government grants | 2025",
                                "Government grants | 2025",
                                "Government grants | 2025",
                                "Government grants | 2025",
                            ],
                            "column_periods": [[], ["2025"], ["2025"], ["2025"], ["2025"]],
                            "units": ["USD million"],
                            "periods": ["2025"],
                            "footnotes": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "retrieval_status": "PASS",
                    }
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "rule_version": "normalization-fixture-v2",
                        "mapping_version": "mapping-fixture-v2",
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_GOVERNMENT_GRANTS_FIXTURE",
                                "metric_id": "GOVERNMENT_GRANTS_RECOGNIZED_IN_PNL",
                                "aliases": ["government grants"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            numeric = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl").read_text(encoding="utf-8").splitlines()
                if json.loads(line)["record_kind"] == "NUMERIC_OBSERVATION"
            ]
            by_raw = {fact["raw_value_text"]: fact for fact in numeric}
            self.assertEqual(by_raw["(12.0)"]["raw_numeric_value"], "-12.0")
            self.assertEqual(by_raw["(12.0)"]["raw_currency"], "USD")
            self.assertEqual(by_raw["(12.0)"]["raw_scale_factor"], "1000000")
            self.assertEqual(by_raw["(12.0)"]["base_unit_value"], "-12000000.0")
            self.assertTrue(
                all(
                    fact["metric_id"] == "GOVERNMENT_GRANTS_RECOGNIZED_IN_PNL"
                    for fact in numeric
                )
            )
            self.assertEqual(by_raw["0"]["value_status"], "EXPLICIT_ZERO")
            self.assertEqual(by_raw["N/A"]["value_status"], "NOT_APPLICABLE")
            self.assertIsNone(by_raw["N/A"]["raw_numeric_value"])
            self.assertEqual(by_raw["—"]["value_status"], "UNKNOWN")
            self.assertIsNone(by_raw["—"]["raw_numeric_value"])
            self.assertEqual(by_raw["(12.0)"]["period_type"], "FISCAL_YEAR")
            self.assertEqual(by_raw["(12.0)"]["period_start"], "2025-01-01")
            self.assertEqual(by_raw["(12.0)"]["period_end"], "2025-12-31")

    def test_accounting_currency_scope_and_audit_fields_inherit_independently_with_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            material_id = "MATERIAL_SMIC_FIXTURE"
            guard = {
                "snapshot_id": "smic-a283e95e2c9e8068",
                "chunk_id": "CHUNK_GUARD",
                "material_id": material_id,
                "structure_type": "PDF_PARAGRAPH_GROUP",
                "content_locator": {"page_number": 1, "section": "Quarterly results"},
                "text": "The consolidated financial information is prepared in accordance with International Financial Reporting Standards (IFRS). The results are unaudited. All currency figures in this report are in US Dollars unless stated otherwise.",
                "text_hash": "sha256:guard",
                "candidate_context": True,
                "matched_query_ids": ["G_ACCOUNTING_SCOPE_EN", "G_PERIOD_UNIT_EN"],
                "selection_reasons": ["DIRECT_HIT"],
                "numeric_context": {"headers": [], "units": [], "periods": [], "footnotes": []},
            }
            target = {
                **guard,
                "chunk_id": "CHUNK_TARGET",
                "content_locator": {"page_number": 2, "section": "Quarterly results"},
                "text": "Revenue was 100.0 million in Q1 2026.",
                "text_hash": "sha256:target",
                "matched_query_ids": ["D1_EN"],
                "numeric_context": {
                    "headers": ["Revenue"],
                    "units": ["million"],
                    "periods": ["Q1 2026"],
                    "footnotes": [],
                },
            }
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                json.dumps(guard) + "\n" + json.dumps(target) + "\n",
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "rule_version": "normalization-fixture-v3",
                        "mapping_version": "mapping-fixture-v3",
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_REVENUE_FIXTURE",
                                "metric_id": "REVENUE",
                                "aliases": ["revenue"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            revenue = next(
                fact
                for fact in facts
                if fact["record_kind"] == "NUMERIC_OBSERVATION"
                and fact["chunk_id"] == "CHUNK_TARGET"
            )
            self.assertEqual(revenue["accounting_standard"], "IFRS")
            self.assertEqual(revenue["consolidation_scope"], "CONSOLIDATED")
            self.assertEqual(revenue["audit_status"], "UNAUDITED")
            self.assertEqual(revenue["raw_currency"], "USD")
            self.assertEqual(revenue["accounting_standard_source"]["chunk_id"], "CHUNK_GUARD")
            self.assertEqual(revenue["consolidation_scope_source"]["chunk_id"], "CHUNK_GUARD")
            self.assertEqual(revenue["audit_status_source"]["chunk_id"], "CHUNK_GUARD")
            self.assertEqual(revenue["currency_source"]["chunk_id"], "CHUNK_GUARD")
            self.assertEqual(
                len(
                    {
                        revenue["accounting_standard_source"]["rule_id"],
                        revenue["consolidation_scope_source"]["rule_id"],
                        revenue["audit_status_source"]["rule_id"],
                        revenue["currency_source"]["rule_id"],
                    }
                ),
                4,
            )

    def test_ytd_difference_creates_separate_reproducible_quarter_derivation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            common: dict[str, Any] = {
                "snapshot_id": "smic-a283e95e2c9e8068",
                "material_id": "MATERIAL_SMIC_FIXTURE",
                "structure_type": "PDF_PARAGRAPH_GROUP",
                "content_locator": {"section": "Condensed consolidated financial statements"},
                "candidate_context": True,
                "matched_query_ids": ["D1_EN", "G_ACCOUNTING_SCOPE_EN"],
                "selection_reasons": ["DIRECT_HIT"],
                "numeric_context": {"headers": [], "units": [], "periods": [], "footnotes": []},
            }
            q1 = {
                **common,
                "chunk_id": "CHUNK_YTD_Q1",
                "content_locator": {**common["content_locator"], "page_number": 1},
                "text": "Unaudited consolidated IFRS revenue for the three months ended March 31, 2025 was USD 90.0 million.",
                "text_hash": "sha256:q1",
            }
            q2 = {
                **common,
                "chunk_id": "CHUNK_YTD_Q2",
                "content_locator": {**common["content_locator"], "page_number": 2},
                "text": "Unaudited consolidated IFRS revenue for the six months ended June 30, 2025 was USD 200.0 million.",
                "text_hash": "sha256:q2",
            }
            context_file = workspace / "context.jsonl"
            context_file.write_text(json.dumps(q1) + "\n" + json.dumps(q2) + "\n", encoding="utf-8")
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "rule_version": "normalization-fixture-v4",
                        "mapping_version": "mapping-fixture-v4",
                        "allowed_derivations": ["YTD_DIFFERENCE"],
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_REVENUE_FIXTURE",
                                "metric_id": "REVENUE",
                                "aliases": ["revenue"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            derived = next(fact for fact in facts if fact["record_kind"] == "DERIVATION")
            inputs = [fact for fact in facts if fact["record_kind"] == "NUMERIC_OBSERVATION"]
            self.assertEqual(derived["derivation_type"], "YTD_DIFFERENCE")
            self.assertEqual(derived["derivation_rule_id"], "DERIVE_YTD_DIFFERENCE_SMIC_CALENDAR_V1")
            self.assertEqual(derived["input_fact_ids"], [inputs[1]["fact_id"], inputs[0]["fact_id"]])
            self.assertEqual(derived["derived_value"], "110.0")
            self.assertEqual(derived["base_unit_value"], "110000000.0")
            self.assertEqual(derived["period_type"], "SINGLE_QUARTER")
            self.assertEqual(derived["fiscal_quarter"], 2)
            self.assertEqual(derived["period_start"], "2025-04-01")
            self.assertEqual(derived["period_end"], "2025-06-30")
            self.assertEqual(derived["audit_status"], "OUTSIDE_AUDIT_SCOPE")
            self.assertEqual(derived["input_precision_effect"], "ROUNDED")
            self.assertEqual(derived["value_origin"], "SYSTEM_DERIVED")
            self.assertEqual(derived["claim_type"], "UNASSESSED")
            self.assertTrue(all(fact["value_origin"] == "SOURCE_REPORTED" for fact in inputs))

    def test_ytd_difference_currency_break_is_blocked_with_gap_but_sources_survive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            common: dict[str, Any] = {
                "snapshot_id": "smic-a283e95e2c9e8068",
                "material_id": "MATERIAL_SMIC_FIXTURE",
                "structure_type": "PDF_PARAGRAPH_GROUP",
                "content_locator": {"section": "Condensed consolidated financial statements"},
                "candidate_context": True,
                "matched_query_ids": ["D1_EN"],
                "selection_reasons": ["DIRECT_HIT"],
                "numeric_context": {"headers": [], "units": [], "periods": [], "footnotes": []},
            }
            q1 = {
                **common,
                "chunk_id": "CHUNK_CNY_Q1",
                "content_locator": {**common["content_locator"], "page_number": 1},
                "text": "Unaudited consolidated IFRS revenue for the three months ended March 31, 2025 was CNY 90.0 million.",
                "text_hash": "sha256:cny-q1",
            }
            q2 = {
                **common,
                "chunk_id": "CHUNK_USD_Q2",
                "content_locator": {**common["content_locator"], "page_number": 2},
                "text": "Unaudited consolidated IFRS revenue for the six months ended June 30, 2025 was USD 200.0 million.",
                "text_hash": "sha256:usd-q2",
            }
            context_file = workspace / "context.jsonl"
            context_file.write_text(json.dumps(q1) + "\n" + json.dumps(q2) + "\n", encoding="utf-8")
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "rule_version": "normalization-fixture-v5",
                        "mapping_version": "mapping-fixture-v5",
                        "allowed_derivations": ["YTD_DIFFERENCE"],
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_REVENUE_FIXTURE",
                                "metric_id": "REVENUE",
                                "aliases": ["revenue"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            sources = [fact for fact in facts if fact["record_kind"] == "NUMERIC_OBSERVATION"]
            blocked = next(fact for fact in facts if fact["record_kind"] == "DERIVATION")
            self.assertEqual(len(sources), 2)
            self.assertEqual({fact["raw_currency"] for fact in sources}, {"CNY", "USD"})
            self.assertEqual(blocked["derivation_status"], "BLOCKED")
            self.assertEqual(blocked["normalization_status"], "BLOCKED")
            self.assertEqual(blocked["comparability_status"], "COMPARABILITY_BREAK")
            self.assertIn("CURRENCY_MISMATCH", blocked["comparability_reason_codes"])
            self.assertIsNone(blocked["derived_value"])
            self.assertEqual(len(blocked["gap_ids"]), 1)
            gaps = yaml.safe_load((output_dir / "gaps.yaml").read_text(encoding="utf-8"))["gaps"]
            self.assertIn(blocked["gap_ids"][0], {gap["gap_id"] for gap in gaps})
            validation = yaml.safe_load(
                (output_dir / "normalization-validation.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(validation["normalization_run_status"], "WARN")

    def test_cas_to_ifrs_bridge_sums_only_details_and_attaches_check_to_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            rows = [
                (1, "CHUNK_BASE", "CAS base profit attributable to owners was CNY 100.0 million in Q1 2026."),
                (1, "CHUNK_DETAIL", "Adjustment detail for profit attributable to owners was CNY -20.0 million in Q1 2026."),
                (1, "CHUNK_SUBTOTAL", "Bridge subtotal for profit attributable to owners was CNY 999.0 million in Q1 2026."),
                (1, "CHUNK_TARGET", "Target profit attributable to owners was CNY 80.0 million in Q1 2026."),
                (2, "CHUNK_BASE_2", "CAS base profit attributable to owners was CNY 50.0 million in Q1 2026."),
                (2, "CHUNK_DETAIL_2", "Adjustment detail for profit attributable to owners was CNY -10.0 million in Q1 2026."),
                (2, "CHUNK_SUBTOTAL_2", "Bridge subtotal for profit attributable to owners was CNY 999.0 million in Q1 2026."),
                (2, "CHUNK_TARGET_2", "Target profit attributable to owners was CNY 40.0 million in Q1 2026."),
                (3, "CHUNK_BASE_3", "CAS base profit attributable to owners was CNY 10.0 million."),
                (3, "CHUNK_DETAIL_3", "Adjustment detail for profit attributable to owners was CNY -2.0 million."),
                (3, "CHUNK_SUBTOTAL_3", "Bridge subtotal for profit attributable to owners was CNY 999.0 million."),
                (3, "CHUNK_TARGET_3", "Target profit attributable to owners was CNY 8.0 million."),
            ]
            context_rows = []
            for page, chunk_id, text_value in rows:
                context_rows.append(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "chunk_id": chunk_id,
                        "material_id": "MATERIAL_SMIC_BRIDGE_FIXTURE",
                        "structure_type": "PDF_TABLE",
                        "content_locator": {
                            "section": "IFRS CAS reconciliation",
                            "page_number": page,
                            "table_number": 1,
                        },
                        "text": "Unaudited consolidated " + text_value,
                        "text_hash": "sha256:" + chunk_id,
                        "candidate_context": True,
                        "matched_query_ids": ["G_ADJUSTMENT_BRIDGE_EN"],
                        "selection_reasons": ["DIRECT_HIT"],
                        "numeric_context": {"headers": [], "units": [], "periods": [], "footnotes": []},
                    }
                )
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                "".join(json.dumps(row) + "\n" for row in context_rows), encoding="utf-8"
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "rule_version": "normalization-fixture-v6",
                        "mapping_version": "mapping-fixture-v6",
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_PROFIT_OWNERS_FIXTURE",
                                "metric_id": "PROFIT_ATTRIBUTABLE_TO_OWNERS",
                                "aliases": ["profit attributable to owners"],
                            }
                        ],
                        "bridge_row_rules": [
                            {
                                "rule_id": "BRIDGE_BASE_FIXTURE",
                                "match_text": "cas base",
                                "row_role": "BASE",
                                "accounting_role": "CAS",
                                "equity_attribution": "OWNERS_OF_PARENT",
                            },
                            {
                                "rule_id": "BRIDGE_DETAIL_FIXTURE",
                                "match_text": "adjustment detail",
                                "row_role": "ADJUSTMENT_DETAIL",
                                "bridge_operation": "ADD",
                                "accounting_role": "BRIDGE_ADJUSTMENT",
                                "equity_attribution": "OWNERS_OF_PARENT",
                            },
                            {
                                "rule_id": "BRIDGE_SUBTOTAL_FIXTURE",
                                "match_text": "bridge subtotal",
                                "row_role": "SUBTOTAL",
                                "accounting_role": "BRIDGE_SUBTOTAL",
                                "equity_attribution": "OWNERS_OF_PARENT",
                            },
                            {
                                "rule_id": "BRIDGE_TARGET_FIXTURE",
                                "match_text": "target",
                                "row_role": "TARGET",
                                "accounting_role": "IFRS",
                                "equity_attribution": "OWNERS_OF_PARENT",
                            },
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            numeric = [fact for fact in facts if fact["record_kind"] == "NUMERIC_OBSERVATION"]
            targets = [fact for fact in numeric if fact.get("bridge_row_role") == "TARGET"]
            self.assertEqual(len(targets), 3)
            mapped_targets = [
                target for target in targets if target["period_mapping_status"] == "MAPPED"
            ]
            self.assertTrue(
                all(
                    target["reconciliation_check"]["reconciliation_status"] == "PASS"
                    for target in mapped_targets
                )
            )
            target = next(fact for fact in targets if fact["raw_numeric_value"] == "80.0")
            subtotal = next(fact for fact in numeric if fact.get("bridge_row_role") == "SUBTOTAL")
            check = target["reconciliation_check"]
            self.assertEqual(check["direction"], "CAS_TO_IFRS")
            self.assertEqual(check["reconciliation_status"], "PASS")
            self.assertEqual(check["recomputed_ifrs_target"], "80000000.0")
            self.assertEqual(check["source_reported_ifrs_target"], "80000000.0")
            self.assertEqual(check["difference"], "0.0")
            self.assertTrue(
                all(target["accounting_standard"] == "IFRS" for target in targets)
            )
            self.assertTrue(
                all(
                    fact["accounting_standard"] == "CAS"
                    for fact in numeric
                    if fact.get("bridge_row_role") == "BASE"
                )
            )
            detail = next(
                fact for fact in numeric if fact.get("bridge_row_role") == "ADJUSTMENT_DETAIL"
            )
            self.assertEqual(detail["source_display_sign"], "NEGATIVE")
            self.assertEqual(detail["normalized_signed_amount"], "-20000000.0")
            unknown_target = next(
                fact for fact in targets if fact["raw_numeric_value"] == "8.0"
            )
            self.assertEqual(
                unknown_target["reconciliation_check"]["reconciliation_status"],
                "UNKNOWN",
            )
            self.assertIn(
                "period_start",
                unknown_target["reconciliation_check"]["mismatch_fields"],
            )
            self.assertEqual(check["tolerance"], "150000.00")
            self.assertNotIn(subtotal["fact_id"], check["input_fact_ids"])
            subtotal_row = next(row for row in check["rows"] if row["row_role"] == "SUBTOTAL")
            self.assertFalse(subtotal_row["included_in_sum"])
            self.assertEqual(target["normalization_status"], "PASS")

    def test_text_proposition_preserves_condition_negation_and_uncertainty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            source_text = "If demand remains stable, gross margin may improve but will not exceed 20% in Q2 2026."
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                json.dumps(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "chunk_id": "CHUNK_QUALIFIED_TEXT",
                        "material_id": "MATERIAL_SMIC_FIXTURE",
                        "structure_type": "TRANSCRIPT_SPEAKER_TURN",
                        "content_locator": {
                            "section": "Earnings Call Transcript",
                            "paragraph_locator": "paragraph:p[1]",
                        },
                        "text": source_text,
                        "text_hash": "sha256:qualified",
                        "candidate_context": True,
                        "matched_query_ids": ["D7_EN"],
                        "selection_reasons": ["DIRECT_HIT"],
                        "numeric_context": {"headers": [], "units": [], "periods": [], "footnotes": []},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "rule_version": "normalization-fixture-v7",
                        "mapping_version": "mapping-fixture-v7",
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_GROSS_MARGIN_FIXTURE",
                                "metric_id": "GROSS_MARGIN",
                                "aliases": ["gross margin"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            proposition = next(fact for fact in facts if fact["record_kind"] == "TEXT_PROPOSITION")
            self.assertEqual(proposition["source_span_text"], source_text)
            self.assertEqual(proposition["condition_text"], "If demand remains stable")
            self.assertEqual(proposition["uncertainty_text"], "may")
            self.assertEqual(proposition["polarity"], "NEGATED")
            self.assertEqual(proposition["target_period"], "Q2 2026")
            self.assertEqual(proposition["applicability_scope"], "Q2 2026")
            self.assertEqual(proposition["claim_type"], "UNASSESSED")

    def test_repeated_source_rows_have_unique_fact_ids_and_clean_rebuild_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            repeated = {
                "snapshot_id": "smic-a283e95e2c9e8068",
                "chunk_id": "CHUNK_REPEATED_ROWS",
                "material_id": "MATERIAL_SMIC_FIXTURE",
                "structure_type": "PDF_TABLE",
                "content_locator": {"page_number": 1, "table_number": 1},
                "text": "Revenue USD 10.0 million\nRevenue USD 10.0 million",
                "text_hash": "sha256:repeated",
                "candidate_context": True,
                "matched_query_ids": ["D1_EN"],
                "selection_reasons": ["DIRECT_HIT"],
                "numeric_context": {
                    "headers": ["Revenue", "2025"],
                    "units": ["USD million"],
                    "periods": ["2025"],
                    "footnotes": [],
                },
            }
            context_file = workspace / "context.jsonl"
            context_file.write_text(json.dumps(repeated) + "\n", encoding="utf-8")
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "rule_version": "normalization-fixture-v8",
                        "mapping_version": "mapping-fixture-v8",
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_REVENUE_FIXTURE",
                                "metric_id": "REVENUE",
                                "aliases": ["revenue"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(len(facts), len({fact["fact_id"] for fact in facts}))
            validation = yaml.safe_load(
                (output_dir / "normalization-validation.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(validation["duplicate_fact_ids"], [])
            self.assertTrue(validation["clean_rebuild_hashes_match"])

    def test_rejects_context_without_exact_snapshot_v3_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                json.dumps(
                    {
                        "chunk_id": "CHUNK_MISSING_SNAPSHOT",
                        "material_id": "MATERIAL_SMIC_FIXTURE",
                        "candidate_context": False,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "rule_version": "normalization-fixture-v9",
                        "mapping_version": "mapping-fixture-v9",
                    }
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(workspace / "output"),
                ]
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exact Snapshot v3 identity", result.stderr)

    def test_fixed_derivations_block_non_positive_and_sign_change_rates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            quarter_rows = [
                (
                    "CHUNK_Q1",
                    "Unaudited consolidated IFRS gross profit was USD 20.0 million and revenue was USD 100.0 million in Q1 2025.",
                ),
                ("CHUNK_Q2", "Unaudited consolidated IFRS revenue was USD 200.0 million in Q2 2025."),
                ("CHUNK_Q3", "Unaudited consolidated IFRS revenue was USD 400.0 million in Q3 2025."),
                ("CHUNK_Q4", "Unaudited consolidated IFRS revenue was USD 800.0 million in Q4 2025."),
                ("CHUNK_Q5", "Unaudited consolidated IFRS revenue was USD 0.0 million in Q1 2026."),
                ("CHUNK_Q6", "Unaudited consolidated IFRS revenue was USD -10.0 million in Q2 2026."),
                ("CHUNK_Q7", "Unaudited consolidated IFRS revenue was USD -5.0 million in Q3 2026."),
                ("CHUNK_Q8", "Unaudited consolidated IFRS revenue was USD 10.0 million in Q4 2026."),
            ]
            context_rows = []
            for page, (chunk_id, text_value) in enumerate(quarter_rows, start=1):
                context_rows.append(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "chunk_id": chunk_id,
                        "material_id": "MATERIAL_SMIC_TTM_FIXTURE",
                        "structure_type": "PDF_PARAGRAPH_GROUP",
                        "content_locator": {
                            "section": "Condensed consolidated financial statements",
                            "page_number": page,
                            "paragraph_group": "page_text",
                        },
                        "text": text_value,
                        "text_hash": "sha256:" + chunk_id,
                        "candidate_context": True,
                        "matched_query_ids": ["D1_EN"],
                        "selection_reasons": ["DIRECT_HIT"],
                        "numeric_context": {
                            "headers": [],
                            "units": [],
                            "periods": [],
                            "footnotes": [],
                        },
                    }
                )
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                "".join(json.dumps(row) + "\n" for row in context_rows),
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "rule_version": "normalization-fixture-v10",
                        "mapping_version": "mapping-fixture-v10",
                        "allowed_derivations": [
                            "TTM_SUM",
                            "GROSS_MARGIN",
                            "PERIOD_CHANGE_PERCENT",
                        ],
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_REVENUE_FIXTURE",
                                "metric_id": "REVENUE",
                                "aliases": ["revenue"],
                            },
                            {
                                "rule_id": "METRIC_GROSS_PROFIT_FIXTURE",
                                "metric_id": "GROSS_PROFIT",
                                "aliases": ["gross profit"],
                            },
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            derived = [fact for fact in facts if fact["record_kind"] == "DERIVATION"]
            ttm = next(
                fact
                for fact in derived
                if fact["derivation_type"] == "TTM_SUM"
                and fact["period_end"] == "2025-12-31"
            )
            margin = next(
                fact for fact in derived if fact["derivation_type"] == "GROSS_MARGIN"
            )
            changes = [
                fact
                for fact in derived
                if fact["derivation_type"] == "PERIOD_CHANGE_PERCENT"
            ]
            self.assertEqual(ttm["base_unit_value"], "1500000000.0")
            self.assertEqual(ttm["period_start"], "2025-01-01")
            self.assertEqual(ttm["period_end"], "2025-12-31")
            self.assertEqual(len(ttm["input_fact_ids"]), 4)
            self.assertEqual(margin["normalized_value"], "20.0")
            self.assertEqual(margin["target_unit"], "PERCENT")
            passing_changes = [
                change for change in changes if change["derivation_status"] == "PASS"
            ]
            blocked_changes = [
                change for change in changes if change["derivation_status"] == "BLOCKED"
            ]
            self.assertEqual(
                {change["normalized_value"] for change in passing_changes},
                {"100", "-100"},
            )
            self.assertEqual(
                {
                    change["comparability_reason_codes"][0]
                    for change in blocked_changes
                },
                {
                    "BLOCKED_ZERO_DENOMINATOR",
                    "BLOCKED_NON_POSITIVE_BASE",
                    "BLOCKED_SIGN_CHANGE",
                },
            )
            self.assertTrue(
                all(
                    change["normalized_value"] is None
                    and change["absolute_change_base_unit_value"] is not None
                    and change["gap_ids"]
                    for change in blocked_changes
                )
            )
            self.assertTrue(all(fact["claim_type"] == "UNASSESSED" for fact in derived))
            self.assertTrue(all(fact["value_origin"] == "SYSTEM_DERIVED" for fact in derived))

    def test_government_funding_adjustment_is_parallel_sensitivity_with_full_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                json.dumps(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "chunk_id": "CHUNK_GOVERNMENT_SENSITIVITY",
                        "material_id": "MATERIAL_SMIC_GOVERNMENT_FIXTURE",
                        "structure_type": "PDF_PARAGRAPH_GROUP",
                        "content_locator": {
                            "section": "Condensed consolidated financial statements",
                            "page_number": 1,
                            "paragraph_group": "page_text",
                        },
                        "text": "Unaudited consolidated IFRS profit from operations was USD 100.0 million, government funding recognized in profit from operations was USD 10.0 million, and revenue was USD 200.0 million in Q1 2026.",
                        "text_hash": "sha256:government",
                        "candidate_context": True,
                        "matched_query_ids": ["D6_EN", "G_ADJUSTMENT_BRIDGE_EN"],
                        "selection_reasons": ["DIRECT_HIT"],
                        "numeric_context": {
                            "headers": [],
                            "units": [],
                            "periods": [],
                            "footnotes": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "rule_version": "normalization-fixture-v11",
                        "mapping_version": "mapping-fixture-v11",
                        "allowed_derivations": ["SENSITIVITY_EX_GOVERNMENT_FUNDING"],
                        "adjustment_whitelist": [
                            {
                                "adjustment_id": "GOVERNMENT_FUNDING_RECOGNIZED_IN_OPERATING_PROFIT",
                                "formula_id": "SENSITIVITY_EX_GOVERNMENT_FUNDING",
                            }
                        ],
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_OPERATING_PROFIT_FIXTURE",
                                "metric_id": "PROFIT_FROM_OPERATIONS",
                                "aliases": ["profit from operations"],
                            },
                            {
                                "rule_id": "METRIC_GOVERNMENT_FIXTURE",
                                "metric_id": "GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL",
                                "aliases": ["government funding recognized"],
                            },
                            {
                                "rule_id": "METRIC_REVENUE_FIXTURE",
                                "metric_id": "REVENUE",
                                "aliases": ["revenue"],
                            },
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            source_facts = [
                fact for fact in facts if fact["record_kind"] == "NUMERIC_OBSERVATION"
            ]
            sensitivities = [fact for fact in facts if fact["record_kind"] == "DERIVATION"]
            adjusted_profit = next(
                fact
                for fact in sensitivities
                if fact["metric_id"]
                == "PROFIT_FROM_OPERATIONS_EX_GOVERNMENT_FUNDING_SENSITIVITY"
            )
            adjusted_margin = next(
                fact
                for fact in sensitivities
                if fact["metric_id"]
                == "OPERATING_MARGIN_EX_GOVERNMENT_FUNDING_SENSITIVITY"
            )
            self.assertEqual(adjusted_profit["base_unit_value"], "90000000.0")
            self.assertEqual(adjusted_margin["normalized_value"], "45.00")
            self.assertEqual(adjusted_profit["sensitivity_label"], "政府资金剔除敏感性营业利润")
            self.assertEqual(adjusted_margin["sensitivity_label"], "政府资金剔除敏感性营业利润率")
            self.assertEqual(len(adjusted_profit["adjustment_bridge"]), 3)
            self.assertEqual(
                adjusted_profit["adjustment_bridge"][1]["role"], "ADJUSTMENT_SUBTRACT"
            )
            self.assertTrue(
                all(fact["value_origin"] == "SOURCE_REPORTED" for fact in source_facts)
            )
            self.assertTrue(
                all(fact["claim_type"] == "UNASSESSED" for fact in sensitivities)
            )

    def test_wafer_capacity_preserves_count_basis_and_measurement_basis(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                json.dumps(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "chunk_id": "CHUNK_WAFER_CAPACITY",
                        "material_id": "MATERIAL_SMIC_WAFER_FIXTURE",
                        "structure_type": "PDF_TABLE",
                        "content_locator": {"page_number": 1, "table_number": 1},
                        "text": "Monthly capacity was 910,000 in Q1 2026.",
                        "text_hash": "sha256:wafer",
                        "candidate_context": True,
                        "matched_query_ids": ["D2_EN"],
                        "selection_reasons": ["DIRECT_HIT"],
                        "numeric_context": {
                            "headers": ["Monthly capacity"],
                            "units": ["8-inch equivalent wafers per month"],
                            "periods": ["Q1 2026"],
                            "footnotes": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "rule_version": "normalization-fixture-v12",
                        "mapping_version": "mapping-fixture-v12",
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_MONTHLY_CAPACITY_FIXTURE",
                                "metric_id": "MONTHLY_CAPACITY_EIGHT_INCH_EQUIVALENT",
                                "aliases": ["monthly capacity"],
                            }
                        ],
                        "wafer_basis_rules": [
                            {
                                "rule_id": "WAFER_BASIS_EIGHT_INCH_EQUIVALENT_V1",
                                "match_text": "8-inch equivalent",
                                "wafer_basis": "EIGHT_INCH_EQUIVALENT",
                            }
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            capacity_values = [
                fact for fact in facts if fact["record_kind"] == "NUMERIC_OBSERVATION"
            ]
            self.assertEqual(len(capacity_values), 1)
            capacity = capacity_values[0]
            self.assertEqual(capacity["raw_numeric_value"], "910000")
            self.assertEqual(capacity["raw_unit"], "COUNT")
            self.assertEqual(capacity["base_unit_value"], "910000")
            self.assertEqual(capacity["wafer_basis"], "EIGHT_INCH_EQUIVALENT")
            self.assertEqual(capacity["measurement_basis"], "MONTHLY_CAPACITY")
            self.assertEqual(capacity["period_type"], "SINGLE_QUARTER")

    def test_composition_share_records_not_applicable_total_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                json.dumps(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "chunk_id": "CHUNK_APPLICATION_MIX",
                        "material_id": "MATERIAL_SMIC_APPLICATION_FIXTURE",
                        "structure_type": "PDF_TABLE",
                        "content_locator": {"page_number": 1, "table_number": 1},
                        "text": "By application, smartphone accounted for 30.0% in Q1 2026.",
                        "text_hash": "sha256:application",
                        "candidate_context": True,
                        "matched_query_ids": ["D3_EN"],
                        "selection_reasons": ["DIRECT_HIT"],
                        "numeric_context": {
                            "headers": [],
                            "units": [],
                            "periods": ["Q1 2026"],
                            "footnotes": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "rule_version": "normalization-fixture-composition-v1",
                        "mapping_version": "mapping-fixture-composition-v1",
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_APPLICATION_MIX_FIXTURE",
                                "metric_id": "APPLICATION_REVENUE_SHARE",
                                "aliases": ["by application"],
                            }
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            shares = [
                fact
                for fact in facts
                if fact.get("metric_id") == "APPLICATION_REVENUE_SHARE"
            ]
            self.assertEqual(len(shares), 1)
            share = shares[0]
            self.assertEqual(share["composition_set_id"], "SMIC_APPLICATION_REVENUE_MIX")
            check = share["composition_check"]
            self.assertEqual(check["status"], "CHECK_NOT_APPLICABLE")
            self.assertEqual(
                check["reason_code"],
                "SET_NOT_CONFIRMED_COMPLETE_EXCLUSIVE_SAME_DENOMINATOR",
            )
            self.assertEqual(check["rule_id"], "COMPOSITION_TOTAL_CHECK_V1")
            # No category total is derived from a lone share observation.
            self.assertFalse(
                any(
                    fact["record_kind"] == "DERIVATION"
                    and fact.get("metric_id") == "APPLICATION_REVENUE_SHARE"
                    for fact in facts
                )
            )

    def test_capex_metrics_stay_distinct_without_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                json.dumps(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "chunk_id": "CHUNK_CAPEX",
                        "material_id": "MATERIAL_SMIC_CAPEX_FIXTURE",
                        "structure_type": "PDF_PARAGRAPH_GROUP",
                        "content_locator": {
                            "section": "Liquidity",
                            "page_number": 1,
                            "paragraph_group": "page_text",
                        },
                        "text": "Capital expenditure was USD 2,000.0 million and capital commitments were USD 500.0 million in Q1 2026.",
                        "text_hash": "sha256:capex",
                        "candidate_context": True,
                        "matched_query_ids": ["D5_EN"],
                        "selection_reasons": ["DIRECT_HIT"],
                        "numeric_context": {
                            "headers": [],
                            "units": [],
                            "periods": [],
                            "footnotes": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "rule_version": "normalization-fixture-capex-v1",
                        "mapping_version": "mapping-fixture-capex-v1",
                        "allowed_derivations": [
                            "YTD_DIFFERENCE",
                            "TTM_SUM",
                            "PERIOD_CHANGE_PERCENT",
                        ],
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_CAPEX_INCURRED_FIXTURE",
                                "metric_id": "CAPITAL_EXPENDITURE_INCURRED",
                                "aliases": ["capital expenditure"],
                            },
                            {
                                "rule_id": "METRIC_CAPEX_COMMITTED_FIXTURE",
                                "metric_id": "CAPITAL_COMMITMENTS_UNPAID",
                                "aliases": ["capital commitments"],
                            },
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            capex = {
                fact["metric_id"]: fact
                for fact in facts
                if fact["record_kind"] == "NUMERIC_OBSERVATION"
                and fact.get("metric_id")
                in {"CAPITAL_EXPENDITURE_INCURRED", "CAPITAL_COMMITMENTS_UNPAID"}
            }
            self.assertEqual(
                set(capex),
                {"CAPITAL_EXPENDITURE_INCURRED", "CAPITAL_COMMITMENTS_UNPAID"},
            )
            self.assertEqual(
                capex["CAPITAL_EXPENDITURE_INCURRED"]["base_unit_value"],
                "2000000000.0",
            )
            self.assertEqual(
                capex["CAPITAL_COMMITMENTS_UNPAID"]["base_unit_value"], "500000000.0"
            )
            # The two capex calibers are never combined into a derived record.
            self.assertFalse(
                any(fact["record_kind"] == "DERIVATION" for fact in facts)
            )

    def test_non_whitelist_government_funding_is_adjustment_tbd(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                json.dumps(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "chunk_id": "CHUNK_GOVERNMENT_TBD",
                        "material_id": "MATERIAL_SMIC_GOVERNMENT_TBD_FIXTURE",
                        "structure_type": "PDF_PARAGRAPH_GROUP",
                        "content_locator": {
                            "section": "Other income",
                            "page_number": 1,
                            "paragraph_group": "page_text",
                        },
                        "text": "Government grants recognized were USD 5.0 million in Q1 2026.",
                        "text_hash": "sha256:government-tbd",
                        "candidate_context": True,
                        "matched_query_ids": ["G_ADJUSTMENT_BRIDGE_EN"],
                        "selection_reasons": ["DIRECT_HIT"],
                        "numeric_context": {
                            "headers": [],
                            "units": [],
                            "periods": [],
                            "footnotes": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "rule_version": "normalization-fixture-govtbd-v1",
                        "mapping_version": "mapping-fixture-govtbd-v1",
                        "allowed_derivations": ["SENSITIVITY_EX_GOVERNMENT_FUNDING"],
                        "adjustment_whitelist": [
                            {
                                "adjustment_id": "GOVERNMENT_FUNDING_RECOGNIZED_IN_OPERATING_PROFIT",
                                "formula_id": "SENSITIVITY_EX_GOVERNMENT_FUNDING",
                            }
                        ],
                        "adjustment_tbd_reason_codes": [
                            "NOT_PROVEN_IN_BASE_METRIC",
                            "AWAITING_USER_CONFIRMATION",
                        ],
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_GOVERNMENT_FIXTURE",
                                "metric_id": "GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL",
                                "aliases": ["government grants recognized"],
                            }
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            funding = [
                fact
                for fact in facts
                if fact.get("metric_id") == "GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL"
            ]
            self.assertEqual(len(funding), 1)
            candidate = funding[0]
            self.assertEqual(
                candidate["adjustment_candidate_status"], "ADJUSTMENT_TBD"
            )
            self.assertEqual(
                candidate["adjustment_tbd_reason_code"], "NOT_PROVEN_IN_BASE_METRIC"
            )
            self.assertIsNone(candidate["adjustment_id"])
            # The candidate is preserved, not silently used as an adjustment.
            self.assertEqual(candidate["value_origin"], "SOURCE_REPORTED")
            self.assertFalse(
                any(
                    fact["record_kind"] == "DERIVATION"
                    and fact.get("derivation_type")
                    == "SENSITIVITY_EX_GOVERNMENT_FUNDING"
                    for fact in facts
                )
            )

    def test_local_retrieval_fail_blocks_only_the_failed_query_family(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            context_rows = []
            for chunk_id, material_id, query_id, amount in (
                ("CHUNK_FAILED", "MATERIAL_SMIC_FAILED", "D2_FAILED", "1.0"),
                ("CHUNK_GOOD", "MATERIAL_SMIC_GOOD", "D1_GOOD", "2.0"),
            ):
                context_rows.append(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "chunk_id": chunk_id,
                        "material_id": material_id,
                        "structure_type": "PDF_PARAGRAPH_GROUP",
                        "content_locator": {
                            "section": "Condensed consolidated financial statements",
                            "page_number": 1,
                            "paragraph_group": "page_text",
                        },
                        "text": (
                            "Unaudited consolidated IFRS revenue was USD "
                            f"{amount} million in Q1 2026."
                        ),
                        "text_hash": "sha256:" + chunk_id,
                        "candidate_context": True,
                        "matched_query_ids": [query_id],
                        "selection_reasons": ["DIRECT_HIT"],
                        "numeric_context": {
                            "headers": [],
                            "units": [],
                            "periods": [],
                            "footnotes": [],
                        },
                    }
                )
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                "".join(json.dumps(row) + "\n" for row in context_rows),
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "retrieval_status": "FAIL",
                        "diagnostics": {
                            "failure_scope": "LOCAL",
                            "failed_query_family_ids": ["D2"],
                        },
                        "queries": [
                            {"query_id": "D1_GOOD", "query_family_id": "D1"},
                            {"query_id": "D2_FAILED", "query_family_id": "D2"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "rule_version": "normalization-local-retrieval-v1",
                        "mapping_version": "mapping-local-retrieval-v1",
                        "entity_mappings": [
                            {
                                "rule_id": "ENTITY_SMIC_FIXTURE",
                                "material_prefix": "MATERIAL_SMIC_",
                                "source_label": "SMIC",
                                "entity_id": "SMIC_GROUP",
                            }
                        ],
                        "metric_mappings": [
                            {
                                "rule_id": "METRIC_REVENUE_FIXTURE",
                                "metric_id": "REVENUE",
                                "aliases": ["revenue"],
                            }
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            facts = [
                json.loads(line)
                for line in (output_dir / "normalized-facts.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual({fact["chunk_id"] for fact in facts}, {"CHUNK_GOOD"})
            gaps = yaml.safe_load((output_dir / "gaps.yaml").read_text(encoding="utf-8"))
            self.assertTrue(
                any(gap["gap_kind"] == "RETRIEVAL_QUALITY_FAIL" for gap in gaps["gaps"])
            )
            validation = yaml.safe_load(
                (output_dir / "normalization-validation.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(validation["normalization_run_status"], "WARN")

    def test_rejects_context_not_bound_to_retrieval_clean_rebuild_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                json.dumps(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "query_rule_version": "context-binding-v1",
                        "chunk_id": "CHUNK_HASH_BINDING",
                        "material_id": "MATERIAL_SMIC_FIXTURE",
                        "candidate_context": False,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "query_rule_version": "context-binding-v1",
                        "retrieval_status": "PASS",
                        "clean_rebuild": {
                            "first": {"context_hash": "sha256:not-the-context"},
                            "second": {"context_hash": "sha256:not-the-context"},
                        },
                    }
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "rule_version": "normalization-binding-v1",
                        "mapping_version": "mapping-binding-v1",
                    }
                ),
                encoding="utf-8",
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(workspace / "output"),
                ]
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("context hash is not bound", result.stderr)

    def test_rejects_normalization_output_inside_frozen_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            context_file = workspace / "context.jsonl"
            context_file.write_text("", encoding="utf-8")
            retrieval_file = workspace / "retrieval-validation.yaml"
            retrieval_file.write_text(
                yaml.safe_dump(
                    {"snapshot_id": "smic-a283e95e2c9e8068", "retrieval_status": "PASS"}
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "accounting.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "rule_version": "normalization-output-boundary-v1",
                        "mapping_version": "mapping-output-boundary-v1",
                    }
                ),
                encoding="utf-8",
            )
            gaps_file = snapshot_dir / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "gaps": []}),
                encoding="utf-8",
            )

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--context-file",
                    str(context_file),
                    "--retrieval-file",
                    str(retrieval_file),
                    "--rules-file",
                    str(rules_file),
                    "--existing-gaps-file",
                    str(gaps_file),
                    "--output-dir",
                    str(snapshot_dir),
                ]
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside the frozen snapshot", result.stderr)
            self.assertFalse((snapshot_dir / "normalized-facts.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
