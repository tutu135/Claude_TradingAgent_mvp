from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "scripts" / "govern_validate_research_evidence.py"
RULES_FILE = REPO_ROOT / "rules" / "source-governance.yaml"
SNAPSHOT_ID = "smic-a283e95e2c9e8068"

# Real Ticket 03 outputs used by the end-to-end test (skipped if absent).
TICKET03_DIR = REPO_ROOT / "tmp" / "ticket03-final"
SNAPSHOT_DIR = REPO_ROOT / "single-stock-demo-v3"


def sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def make_fact(**overrides: Any) -> dict[str, Any]:
    text = overrides.get("source_span_text", "营业收入 100")
    fact = {
        "fact_id": "FACT_0001",
        "chunk_id": "CHUNK_0001",
        "material_id": "MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS",
        "snapshot_id": SNAPSHOT_ID,
        "record_kind": "NUMERIC_OBSERVATION",
        "metric_id": "REVENUE",
        "normalized_value": "100",
        "value_status": "PRESENT",
        "period_type": "FISCAL_YEAR",
        "period_start": "2024-01-01",
        "period_end": "2024-12-31",
        "accounting_standard": "CAS",
        "consolidation_scope": "CONSOLIDATED",
        "target_currency": "CNY",
        "target_unit": "MONEY",
        "raw_unit": "MONEY",
        "entity_id": "SMIC_GROUP",
        "audit_status": "AUDITED",
        "normalization_status": "PASS",
        "source_chunk_text_hash": sha256_text(text),
        "source_span_text": text,
        "content_locator": {"section": "financials", "page_number": 1},
        "speaker_or_publisher": None,
        "target_period": None,
        "period_nature": None,
        "uncertainty_text": None,
        "gap_ids": [],
    }
    fact.update(overrides)
    fact["source_chunk_text_hash"] = sha256_text(fact["source_span_text"])
    return fact


def make_chunk(fact: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    chunk = {
        "chunk_id": fact["chunk_id"],
        "snapshot_id": SNAPSHOT_ID,
        "material_id": fact["material_id"],
        "text_hash": fact["source_chunk_text_hash"],
        "content_locator": {"section": (fact.get("content_locator") or {}).get("section")},
        "speaker_label": fact.get("speaker_or_publisher"),
    }
    chunk.update(overrides)
    return chunk


def make_material(material_id: str, **overrides: Any) -> dict[str, Any]:
    material = {
        "material_id": material_id,
        "as_of_eligible": True,
        "parse_status": "PARSED",
        "source_use_note": {"usage_basis": "test"},
    }
    material.update(overrides)
    return material


def signature_for(fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "material_id": fact["material_id"],
        "metric_id": fact["metric_id"],
        "period_start": fact["period_start"],
        "period_end": fact["period_end"],
        "period_type": fact["period_type"],
        "accounting_standard": fact["accounting_standard"],
        "target_currency": fact["target_currency"],
        "target_unit": fact["target_unit"],
        "normalized_value": fact["normalized_value"],
        "span_hash": sha256_text(fact["source_span_text"]),
    }


def rules_with(
    governance: list[dict[str, Any]], verified_facts: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    rules = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    rules["material_governance"] = governance
    rules["snapshot_conflict_eligibility_overrides"] = {
        "snapshot_id": SNAPSHOT_ID,
        "rationale": "UPSTREAM_PERIOD_CLASSIFICATION_UNRELIABLE",
        "verified_facts": verified_facts or [],
    }
    return rules


def governance_row(material_id: str, tier: str, category: str, group: str) -> dict[str, Any]:
    return {
        "material_id": material_id,
        "source_tier": tier,
        "material_category": category,
        "source_group_id": group,
    }


class GovernValidateFixtureTests(unittest.TestCase):
    def _run(
        self,
        facts: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
        materials: list[dict[str, Any]],
        rules: dict[str, Any],
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any], list[dict[str, Any]]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": SNAPSHOT_ID, "files": []}),
                encoding="utf-8",
            )
            (snapshot_dir / "materials.jsonl").write_text(
                "".join(json.dumps(m) + "\n" for m in materials), encoding="utf-8"
            )
            facts_file = workspace / "facts.jsonl"
            facts_file.write_text(
                "".join(json.dumps(f) + "\n" for f in facts), encoding="utf-8"
            )
            context_file = workspace / "context.jsonl"
            context_file.write_text(
                "".join(json.dumps(c) + "\n" for c in chunks), encoding="utf-8"
            )
            gaps_file = workspace / "gaps.yaml"
            gaps_file.write_text(
                yaml.safe_dump({"snapshot_id": SNAPSHOT_ID, "gaps": []}), encoding="utf-8"
            )
            rules_file = workspace / "rules.yaml"
            rules_file.write_text(yaml.safe_dump(rules, allow_unicode=True), encoding="utf-8")
            output_dir = workspace / "out"
            result = run_cli(
                [
                    "--snapshot-dir", str(snapshot_dir),
                    "--facts-file", str(facts_file),
                    "--context-file", str(context_file),
                    "--rules-file", str(rules_file),
                    "--existing-gaps-file", str(gaps_file),
                    "--output-dir", str(output_dir),
                ]
            )
            validation: dict[str, Any] = {}
            evidence: list[dict[str, Any]] = []
            if (output_dir / "evidence-validation.yaml").exists():
                validation = yaml.safe_load(
                    (output_dir / "evidence-validation.yaml").read_text(encoding="utf-8")
                )
            if (output_dir / "governed-evidence.jsonl").exists():
                evidence = [
                    json.loads(line)
                    for line in (output_dir / "governed-evidence.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()
                    if line.strip()
                ]
            return result, validation, evidence

    def test_clean_fixture_passes(self) -> None:
        # Clean issuer + industry facts: all metric_id present, all PASS, no interim
        # FISCAL_YEAR pollution, no whitelist -> zero new gaps -> PASS.
        facts = [
            make_fact(fact_id=f"FACT_{i}", chunk_id=f"CHUNK_{i}", source_span_text=f"营业收入 {i}")
            for i in range(1, 6)
        ]
        facts.append(
            make_fact(
                fact_id="FACT_TEXT",
                chunk_id="CHUNK_TEXT",
                record_kind="TEXT_PROPOSITION",
                metric_id=None,
                value_status=None,
                period_type=None,
                source_span_text="产能利用率保持高位",
            )
        )
        materials = [make_material("MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS")]
        governance = [
            governance_row(
                "MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS",
                "T1",
                "ISSUER_STATUTORY_DISCLOSURE",
                "SG_A",
            )
        ]
        chunks = [make_chunk(f) for f in facts]
        result, validation, evidence = self._run(
            facts, chunks, materials, rules_with(governance)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(validation["validation_status"], "PASS")
        self.assertTrue(validation["clean_rebuild_hashes_match"])
        self.assertEqual(len(evidence), len(facts))
        self.assertEqual(validation["new_gap_ids"], [])
        self.assertTrue(all(row["evidence_status"] == "USABLE" for row in evidence))
        # fact_id : evidence_id is 1:1
        self.assertEqual(
            len({row["evidence_id"] for row in evidence}), len(evidence)
        )

    def test_warn_fixture_quarantine_and_missing_metric(self) -> None:
        # WARN via: an as_of-ineligible material (quarantine) + a numeric fact missing
        # metric_id (aggregate gap) + a PARTIAL fact (restricted, not by itself WARN).
        clean = [
            make_fact(fact_id=f"FACT_{i}", chunk_id=f"CHUNK_{i}", source_span_text=f"收入 {i}")
            for i in range(1, 4)
        ]
        partial = make_fact(
            fact_id="FACT_PARTIAL",
            chunk_id="CHUNK_PARTIAL",
            normalization_status="PARTIAL",
            source_span_text="部分规整",
        )
        missing_metric = make_fact(
            fact_id="FACT_NOMETRIC",
            chunk_id="CHUNK_NOMETRIC",
            metric_id=None,
            source_span_text="未映射指标 42",
        )
        ineligible = make_fact(
            fact_id="FACT_QUAR",
            chunk_id="CHUNK_QUAR",
            material_id="MATERIAL_SIA_2023_ANNUAL_SALES",
            source_span_text="行业销售",
            metric_id="GLOBAL_SEMICONDUCTOR_SALES",
        )
        facts = [*clean, partial, missing_metric, ineligible]
        chunks = [make_chunk(f) for f in facts]
        materials = [
            make_material("MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS"),
            make_material("MATERIAL_SIA_2023_ANNUAL_SALES", as_of_eligible=False),
        ]
        governance = [
            governance_row(
                "MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS",
                "T1",
                "ISSUER_STATUTORY_DISCLOSURE",
                "SG_A",
            ),
            governance_row(
                "MATERIAL_SIA_2023_ANNUAL_SALES", "T2", "INDUSTRY_ASSOCIATION", "SG_SIA"
            ),
        ]
        result, validation, evidence = self._run(
            facts, chunks, materials, rules_with(governance)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(validation["validation_status"], "WARN")
        by_id = {row["fact_id"]: row for row in evidence}
        self.assertEqual(by_id["FACT_QUAR"]["evidence_status"], "QUARANTINED")
        self.assertEqual(by_id["FACT_QUAR"]["permitted_use"], "NOT_USABLE")
        self.assertIn(
            "MATERIAL_AS_OF_INELIGIBLE", by_id["FACT_QUAR"]["quarantine_reason_codes"]
        )
        self.assertEqual(by_id["FACT_PARTIAL"]["evidence_status"], "RESTRICTED")
        self.assertEqual(
            by_id["FACT_NOMETRIC"]["conflict_exclusion_reason"], "MISSING_METRIC_ID"
        )
        # aggregate missing-metric gap present; no per-record explosion
        self.assertTrue(
            any(g.startswith("GAP_EVIDENCE_") for g in validation["new_gap_ids"])
        )

    def test_warn_fixture_unresolved_conflict(self) -> None:
        # Two whitelisted facts, identical comparable key, different values, identical
        # audit/tier/statutory rank -> tie -> CONFLICT_UNRESOLVED -> WARN.
        fact_a = make_fact(
            fact_id="FACT_A",
            chunk_id="CHUNK_A",
            material_id="MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS",
            normalized_value="100",
            source_span_text="口径A 100",
        )
        fact_b = make_fact(
            fact_id="FACT_B",
            chunk_id="CHUNK_B",
            material_id="MATERIAL_SMIC_2024_ANNUAL_REPORT_IFRS_HKEX",
            normalized_value="200",
            source_span_text="口径B 200",
        )
        facts = [fact_a, fact_b]
        chunks = [make_chunk(f) for f in facts]
        materials = [
            make_material("MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS"),
            make_material("MATERIAL_SMIC_2024_ANNUAL_REPORT_IFRS_HKEX"),
        ]
        governance = [
            governance_row(
                "MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS",
                "T1",
                "ISSUER_STATUTORY_DISCLOSURE",
                "SG_A",
            ),
            governance_row(
                "MATERIAL_SMIC_2024_ANNUAL_REPORT_IFRS_HKEX",
                "T1",
                "ISSUER_STATUTORY_DISCLOSURE",
                "SG_B",
            ),
        ]
        verified = [
            {"fact_id": "FACT_A", "eligibility": "INCLUDE", "review_reason": "TEST", "signature": signature_for(fact_a)},
            {"fact_id": "FACT_B", "eligibility": "INCLUDE", "review_reason": "TEST", "signature": signature_for(fact_b)},
        ]
        result, validation, evidence = self._run(
            facts, chunks, materials, rules_with(governance, verified)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(validation["validation_status"], "WARN")
        stats = validation["statistics"]
        self.assertEqual(stats["eligible_fact_count"], 2)
        self.assertEqual(stats["comparison_pair_count"], 1)
        self.assertEqual(stats["detected_conflict_group_count"], 1)
        self.assertEqual(stats["unresolved_conflict_group_count"], 1)
        for row in evidence:
            self.assertEqual(row["conflict_status"], "CONFLICT_UNRESOLVED")
            self.assertEqual(row["evidence_status"], "RESTRICTED")

    def test_warn_fixture_resolved_conflict_reports_winner(self) -> None:
        # Same comparable key, different values, different audit rank -> resolved winner.
        fact_a = make_fact(
            fact_id="FACT_A",
            chunk_id="CHUNK_A",
            material_id="MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS",
            normalized_value="100",
            audit_status="AUDITED",
            source_span_text="已审 100",
        )
        fact_b = make_fact(
            fact_id="FACT_B",
            chunk_id="CHUNK_B",
            material_id="MATERIAL_SMIC_2024_ANNUAL_REPORT_IFRS_HKEX",
            normalized_value="200",
            audit_status="UNAUDITED",
            source_span_text="未审 200",
        )
        facts = [fact_a, fact_b]
        chunks = [make_chunk(f) for f in facts]
        materials = [
            make_material("MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS"),
            make_material("MATERIAL_SMIC_2024_ANNUAL_REPORT_IFRS_HKEX"),
        ]
        governance = [
            governance_row(
                "MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS",
                "T1",
                "ISSUER_STATUTORY_DISCLOSURE",
                "SG_A",
            ),
            governance_row(
                "MATERIAL_SMIC_2024_ANNUAL_REPORT_IFRS_HKEX",
                "T1",
                "ISSUER_STATUTORY_DISCLOSURE",
                "SG_B",
            ),
        ]
        verified = [
            {"fact_id": "FACT_A", "eligibility": "INCLUDE", "review_reason": "TEST", "signature": signature_for(fact_a)},
            {"fact_id": "FACT_B", "eligibility": "INCLUDE", "review_reason": "TEST", "signature": signature_for(fact_b)},
        ]
        result, validation, evidence = self._run(
            facts, chunks, materials, rules_with(governance, verified)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        stats = validation["statistics"]
        self.assertEqual(stats["detected_conflict_group_count"], 1)
        self.assertEqual(stats["unresolved_conflict_group_count"], 0)
        winner = {row["fact_id"]: row["conflict_winner_evidence_id"] for row in evidence}
        expected = evidence[0]["conflict_winner_evidence_id"]
        self.assertTrue(expected)
        self.assertTrue(all(v == expected for v in winner.values()))
        for row in evidence:
            self.assertEqual(row["conflict_status"], "RESOLVED")
            self.assertEqual(row["conflict_resolution_rule_id"], "RESOLVE_METRIC_CONFLICT_FR042_V1")

    def test_fail_fixture_whitelist_signature_drift_fails_closed(self) -> None:
        # A whitelisted fact whose registered value no longer matches -> FAIL, and the
        # affected fact is not eligible (fail closed), yet diagnostics still emit.
        fact = make_fact(fact_id="FACT_DRIFT", chunk_id="CHUNK_DRIFT", normalized_value="100")
        signature = signature_for(fact)
        signature["normalized_value"] = "999"  # drift
        facts = [fact]
        chunks = [make_chunk(f) for f in facts]
        materials = [make_material("MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS")]
        governance = [
            governance_row(
                "MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS",
                "T1",
                "ISSUER_STATUTORY_DISCLOSURE",
                "SG_A",
            )
        ]
        verified = [
            {"fact_id": "FACT_DRIFT", "eligibility": "INCLUDE", "review_reason": "TEST", "signature": signature}
        ]
        result, validation, evidence = self._run(
            facts, chunks, materials, rules_with(governance, verified)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(validation["validation_status"], "FAIL")
        checks = {c["check"]: c for c in validation["checks"]}
        self.assertEqual(checks["whitelist_signature"]["status"], "FAIL")
        # diagnostics still produced
        self.assertEqual(len(evidence), 1)
        # fail closed: drifted fact excluded from conflict eligibility
        self.assertEqual(evidence[0]["conflict_eligibility"], "EXCLUDED")

    def test_fail_fixture_dangling_chunk_reference(self) -> None:
        fact = make_fact(fact_id="FACT_DANGLE", chunk_id="CHUNK_MISSING")
        facts = [fact]
        chunks: list[dict[str, Any]] = []  # no chunk provides CHUNK_MISSING
        materials = [make_material("MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS")]
        governance = [
            governance_row(
                "MATERIAL_SMIC_2024_A_SHARE_ANNUAL_REPORT_HKEX_OVERSEAS",
                "T1",
                "ISSUER_STATUTORY_DISCLOSURE",
                "SG_A",
            )
        ]
        result, validation, evidence = self._run(
            facts, chunks, materials, rules_with(governance)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(validation["validation_status"], "FAIL")
        checks = {c["check"]: c for c in validation["checks"]}
        self.assertEqual(checks["id_reference_integrity"]["status"], "FAIL")
        self.assertEqual(checks["locator_chain_consistency"]["status"], "FAIL")

    def test_transcript_claim_types_and_tier_override(self) -> None:
        material_id = "MATERIAL_SMIC_2026_Q1_EARNINGS_CALL_TRANSCRIPT_ALPHASPREAD"
        ai = make_fact(
            fact_id="FACT_AI",
            chunk_id="CHUNK_AI",
            material_id=material_id,
            record_kind="TEXT_PROPOSITION",
            metric_id=None,
            value_status=None,
            period_type=None,
            speaker_or_publisher="ALPHASPREAD_AI_SUMMARY",
            source_span_text="Revenue was strong.",
        )
        guidance = make_fact(
            fact_id="FACT_GUIDE",
            chunk_id="CHUNK_GUIDE",
            material_id=material_id,
            record_kind="TEXT_PROPOSITION",
            metric_id=None,
            value_status=None,
            period_type=None,
            speaker_or_publisher="Dr. Zhao Haijun",
            source_span_text="We expect revenue to grow next quarter.",
        )
        assertion = make_fact(
            fact_id="FACT_ASSERT",
            chunk_id="CHUNK_ASSERT",
            material_id=material_id,
            record_kind="TEXT_PROPOSITION",
            metric_id=None,
            value_status=None,
            period_type=None,
            speaker_or_publisher="Dr. Wu Junfeng",
            source_span_text="Utilization reached a high level.",
        )
        operator = make_fact(
            fact_id="FACT_OP",
            chunk_id="CHUNK_OP",
            material_id=material_id,
            record_kind="TEXT_PROPOSITION",
            metric_id=None,
            value_status=None,
            period_type=None,
            speaker_or_publisher="OPERATOR",
            source_span_text="Welcome to the call.",
        )
        facts = [ai, guidance, assertion, operator]
        chunks = [
            make_chunk(ai, content_locator={"section": "AI Summary Earnings Call"}),
            make_chunk(guidance),
            make_chunk(assertion),
            make_chunk(operator),
        ]
        materials = [make_material(material_id)]
        governance = [
            governance_row(material_id, "T3", "THIRD_PARTY_TRANSCRIPT", "SG_TX")
        ]
        result, validation, evidence = self._run(
            facts, chunks, materials, rules_with(governance)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        by_id = {row["fact_id"]: row for row in evidence}
        self.assertEqual(by_id["FACT_AI"]["claim_type"], "THIRD_PARTY_VIEW")
        self.assertEqual(by_id["FACT_AI"]["source_tier"], "T4")  # AI summary downgrade
        self.assertEqual(by_id["FACT_GUIDE"]["claim_type"], "MANAGEMENT_GUIDANCE")
        self.assertEqual(by_id["FACT_ASSERT"]["claim_type"], "MANAGEMENT_ASSERTION")
        self.assertEqual(by_id["FACT_OP"]["claim_type"], "THIRD_PARTY_VIEW")
        for row in evidence:
            self.assertEqual(row["evidence_status"], "RESTRICTED")  # T3/T4 never USABLE


@unittest.skipUnless(
    (TICKET03_DIR / "normalized-facts.jsonl").exists()
    and (SNAPSHOT_DIR / "snapshot-manifest.yaml").exists(),
    "real Snapshot v3 Ticket 03 outputs are required for the end-to-end test",
)
class GovernValidateEndToEndTests(unittest.TestCase):
    def _run_real(self, output_dir: Path) -> dict[str, Any]:
        result = run_cli(
            [
                "--snapshot-dir", str(SNAPSHOT_DIR),
                "--facts-file", str(TICKET03_DIR / "normalized-facts.jsonl"),
                "--context-file", str(TICKET03_DIR / "context.jsonl"),
                "--rules-file", str(RULES_FILE),
                "--existing-gaps-file", str(TICKET03_DIR / "gaps.yaml"),
                "--output-dir", str(output_dir),
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return yaml.safe_load(
            (output_dir / "evidence-validation.yaml").read_text(encoding="utf-8")
        )

    def test_real_v3_warn_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first_dir = Path(temp_dir) / "first"
            second_dir = Path(temp_dir) / "second"
            first = self._run_real(first_dir)
            second = self._run_real(second_dir)

            self.assertEqual(first["validation_status"], "WARN")
            self.assertTrue(first["clean_rebuild_hashes_match"])
            for check in first["checks"]:
                self.assertNotEqual(check["status"], "FAIL", check["check"])

            # one governed evidence per fact
            fact_count = sum(
                1
                for line in (TICKET03_DIR / "normalized-facts.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            )
            self.assertEqual(first["statistics"]["evidence_count"], fact_count)

            # zero cross-source conflict, but proven by real comparison, not by skipping
            stats = first["statistics"]
            self.assertEqual(stats["detected_conflict_group_count"], 0)
            self.assertEqual(stats["candidate_fact_count"], 71)
            self.assertEqual(stats["eligible_fact_count"], 2)

            # two clean rebuilds produce identical evidence + validation hashes
            first_hash = (first_dir / "governed-evidence.jsonl").read_bytes()
            second_hash = (second_dir / "governed-evidence.jsonl").read_bytes()
            self.assertEqual(first_hash, second_hash)
            self.assertEqual(
                first["clean_rebuild_hashes"]["first_evidence"],
                second["clean_rebuild_hashes"]["first_evidence"],
            )


if __name__ == "__main__":
    unittest.main()
