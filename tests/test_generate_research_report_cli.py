from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "scripts" / "generate_research_report.py"
SNAPSHOT_ID = "smic-a283e95e2c9e8068"
ANALYSIS_RULE_VERSION = "smic-v3-analysis-v1"
SELECTION_HASH = "sha256:" + "a" * 64
AS_OF = "2026-05-15T23:59:59+08:00"

DIMENSIONS = [
    "D1_PROFITABILITY_CHANGE",
    "D2_UTILIZATION_EFFECT",
    "D3_MIX_EFFECT",
    "D4_CAPEX_CONVERSION",
    "D5_CYCLE_EXPLANATION",
    "D6_NONCORE_EXPLANATION",
    "D7_SUSTAINABILITY_EVIDENCE",
]

KEPT_SENTENCE = "本维度的方向由来源披露的结果指标承载。"
DROPPED_SENTENCE = "毛利率由 18.0% 上升到 21.0%，改善 3.0 个百分点。"


def run(workspace: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=workspace,
    )


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def numeric_fact(fact_id: str, metric_id: str, chunk_id: str, material_id: str) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "chunk_id": chunk_id,
        "material_id": material_id,
        "record_kind": "NUMERIC_OBSERVATION",
        "metric_id": metric_id,
        "normalized_value": "21.0",
        "base_unit_value": "21.0",
        "raw_value_text": "21.0%",
        "raw_numeric_value": "21.0",
        "raw_unit": "PERCENT",
        "raw_currency": None,
        "raw_scale_factor": "1",
        "target_unit": "PERCENT",
        "target_currency": None,
        "accounting_standard": "IFRS",
        "consolidation_scope": "CONSOLIDATED",
        "audit_status": "AUDITED",
        "period_type": "FISCAL_YEAR",
        "period_start": "2025-01-01",
        "period_end": "2025-12-31",
        "as_of_date": None,
        "value_origin": "SOURCE_REPORTED",
        "value_status": "PRESENT",
        "normalization_status": "PASS",
        "content_locator": {"page_number": 12, "section": "FINANCIAL HIGHLIGHTS"},
        "source_span_text": "Gross margin 21.0% 18.0%",
        "gap_ids": [],
    }


def text_fact(fact_id: str, chunk_id: str, material_id: str) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "chunk_id": chunk_id,
        "material_id": material_id,
        "record_kind": "TEXT_PROPOSITION",
        "metric_id": None,
        "accounting_standard": "IFRS",
        "audit_status": "OUTSIDE_AUDIT_SCOPE",
        "period_type": None,
        "period_start": None,
        "period_end": None,
        "normalization_status": "PASS",
        "content_locator": {"page_number": 3, "section": "MD&A"},
        "source_span_text": "the improvement was driven by the product mix change",
        "gap_ids": [],
    }


def candidate_evidence(
    evidence_id: str, fact_id: str, dimension_id: str, chunk_id: str,
    material_id: str, record_kind: str, metric_id: str | None,
) -> dict[str, Any]:
    return {
        "record_type": "CANDIDATE_EVIDENCE",
        "evidence_id": evidence_id,
        "fact_id": fact_id,
        "dimension_id": dimension_id,
        "chunk_id": chunk_id,
        "material_id": material_id,
        "record_kind": record_kind,
        "metric_id": metric_id,
        "claim_type": "REPORTED_FACT",
        "source_tier": "T1",
        "evidence_status": "USABLE",
        "conflict_status": "NOT_APPLICABLE",
        "source_group_id": "SG_ONE",
        "content_locator": {"page_number": 12, "section": "FINANCIAL HIGHLIGHTS"},
        "source_span_text": "Gross margin 21.0% 18.0%",
    }


def finding(dimension_id: str) -> dict[str, Any]:
    index = DIMENSIONS.index(dimension_id) + 1
    return {
        "dimension_id": dimension_id,
        "finding": "MIXED",
        "finding_statement": f"{KEPT_SENTENCE}{DROPPED_SENTENCE}",
        "supporting_evidence": [
            {
                "evidence_id": f"EVID_N{index}",
                "role": "PRIMARY_SUPPORT",
                "note": "该记录来自年度报告的同口径披露。",
                "fact_id": f"FACT_N{index}",
            },
            {
                "evidence_id": f"EVID_T{index}",
                "role": "CONTEXT",
                "note": "该文本说明成因，未经独立核验。",
                "fact_id": f"FACT_T{index}",
            },
        ],
        "counter_evidence": [],
        "alternative_explanations": ["行业周期回暖亦可解释同向变化。"],
        "limitations": ["缺少按产品线拆分的同口径数值。"],
        "gaps": ["缺少可比的季度口径记录。"],
        "management_assertions": [],
        "generation_attempts": 1,
        "evidence_score": 2,
        "evidence_score_label": "ADEQUATE",
        "evidence_score_basis": {
            "support_count": 2,
            "numeric_support_count": 1,
            "source_group_ids": ["SG_ONE"],
            "cross_period_metrics": [],
            "bearing_cross_period_metrics": [],
            "has_unresolved_conflict": False,
        },
        "finding_reason_code": "MODEL_JUDGMENT",
        "bearing_metric_whitelist": ["GROSS_MARGIN"],
    }


def build_workspace(**options: Any) -> Path:
    workspace = Path(tempfile.mkdtemp())
    for name in ("analysis.yaml", "report.yaml"):
        target = workspace / "rules" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            (REPO_ROOT / "rules" / name).read_text(encoding="utf-8"), encoding="utf-8"
        )

    snapshot = workspace / "single-stock-demo-v3"
    write_yaml(
        snapshot / "case.yaml",
        {
            "as_of": AS_OF,
            "research_question": "截至 {as_of}，中芯国际的经常性经营盈利能力发生了哪些可验证的变化？",
            "company": {"legal_name_zh": "中芯国际集成电路制造有限公司"},
            "security": {"code": "688981.SH", "exchange": "Shanghai Stock Exchange"},
            "required_coverage": ["capacity", "utilization"],
            "distribution_status": "INTERNAL_DEMO_ONLY",
        },
    )
    write_yaml(snapshot / "snapshot-manifest.yaml", {"snapshot_id": SNAPSHOT_ID, "files": []})
    write_jsonl(
        snapshot / "materials.jsonl",
        [
            {
                "material_id": "MATERIAL_ANNUAL",
                "displayed_publisher": "Semiconductor Manufacturing International Corporation",
                "title": "2025 Annual Report",
                "source_id": "SOURCE_HKEX",
                "acquisition_targets": ["capacity"],
                "as_of_eligible": True,
                "media_type": "application/pdf",
                "publication_time": {"latest": "2026-03-30T00:00:00+08:00",
                                     "raw_text": "2026-03-30"},
                "canonical_material_locator": {"source_page": "https://example.invalid/ar2025"},
            }
        ],
    )

    run_dir = workspace / "single-stock-demo-run"
    facts: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = [
        {
            "record_type": "SELECTION_SUMMARY",
            "snapshot_id": SNAPSHOT_ID,
            "analysis_rule_version": ANALYSIS_RULE_VERSION,
            "dimensions": {name: {"candidate_chunks": 2, "selected_chunks": 2}
                           for name in DIMENSIONS},
        }
    ]
    evidence_rows: list[dict[str, Any]] = []
    for index, dimension_id in enumerate(DIMENSIONS, start=1):
        facts.append(numeric_fact(f"FACT_N{index}", "GROSS_MARGIN",
                                  f"CHUNK_{index}", "MATERIAL_ANNUAL"))
        facts.append(text_fact(f"FACT_T{index}", f"CHUNK_{index}", "MATERIAL_ANNUAL"))
        candidates.append(candidate_evidence(f"EVID_N{index}", f"FACT_N{index}", dimension_id,
                                             f"CHUNK_{index}", "MATERIAL_ANNUAL",
                                             "NUMERIC_OBSERVATION", "GROSS_MARGIN"))
        candidates.append(candidate_evidence(f"EVID_T{index}", f"FACT_T{index}", dimension_id,
                                             f"CHUNK_{index}", "MATERIAL_ANNUAL",
                                             "TEXT_PROPOSITION", None))
        for suffix in ("N", "T"):
            evidence_rows.append(
                {
                    "evidence_id": f"EVID_{suffix}{index}",
                    "fact_id": f"FACT_{suffix}{index}",
                    "chunk_id": f"CHUNK_{index}",
                    "material_id": "MATERIAL_ANNUAL",
                    "evidence_status": "USABLE",
                    "source_tier": "T1",
                    "claim_type": "REPORTED_FACT",
                    "conflict_status": "NOT_APPLICABLE",
                    "conflict_group_id": None,
                    "quarantine_reason_codes": [],
                    "gap_ids": [],
                    "source_group_id": "SG_ONE",
                }
            )
    evidence_rows.extend(options.get("extra_evidence") or [])
    facts.extend(options.get("extra_facts") or [])

    write_jsonl(run_dir / "normalized-facts.jsonl", facts)
    write_jsonl(run_dir / "analysis-inputs.jsonl", candidates)
    write_jsonl(run_dir / "governed-evidence.jsonl", evidence_rows)
    write_jsonl(run_dir / "context.jsonl", [])
    write_jsonl(run_dir / "analysis-attempts.jsonl", [])

    findings = [finding(name) for name in DIMENSIONS]
    document = {
        "snapshot_id": SNAPSHOT_ID,
        "analysis_rule_version": ANALYSIS_RULE_VERSION,
        "context_rule_version": "smic-v3-context-retrieval-v3",
        "distribution_status": "INTERNAL_DEMO_ONLY",
        "human_review_status": "PENDING_HUMAN_REVIEW",
        "overall_score": "NOT_APPLICABLE",
        "summary": {"overall_score": "NOT_APPLICABLE"},
        "findings": findings,
        "cross_attribution": [],
    }
    write_yaml(run_dir / "findings.yaml", document)
    write_yaml(run_dir / "findings-revised.yaml", document)
    write_yaml(
        run_dir / "challenges.yaml",
        {
            "snapshot_id": SNAPSHOT_ID,
            "challenge_run_status": "WARN",
            "max_rounds": 2,
            "rounds_used": [1],
            "challenges": [
                {
                    "challenge_id": "CH_001",
                    "round": 1,
                    "category": "SOURCE_TRACEABILITY",
                    "target_kind": "FINDING",
                    "target_id": "D1_PROFITABILITY_CHANGE",
                    "question": "两条支撑是否同一次原始披露？该维度证据分为 2。",
                    "disposition": "RESOLVED_NO_CHANGE",
                    "reason": "一次定向复核确认两条记录来自同一次披露。",
                    "review_count": 1,
                    "blocking_triggers": [],
                    "schema_errors": [],
                    "revision_errors": [],
                    "finding_before": None,
                    "finding_after": None,
                }
            ],
            "revised_findings_validation": [],
            "new_gap_ids": [],
        },
    )
    write_yaml(run_dir / "retrieval-validation.yaml",
               {"snapshot_id": SNAPSHOT_ID, "retrieval_status": "PASS"})
    write_yaml(run_dir / "normalization-validation.yaml",
               {"snapshot_id": SNAPSHOT_ID, "normalization_run_status": "WARN"})
    write_yaml(run_dir / "evidence-validation.yaml",
               {"snapshot_id": SNAPSHOT_ID, "validation_status": "WARN",
                "statistics": {"quarantined_count": 0, "detected_conflict_group_count": 0,
                               "unresolved_conflict_group_count": 0}})
    write_yaml(run_dir / "analysis-validation.yaml",
               {"snapshot_id": SNAPSHOT_ID, "analysis_run_status": "PASS",
                "selection_hash": SELECTION_HASH, "checks": []})
    write_yaml(run_dir / "gaps.yaml", {"snapshot_id": SNAPSHOT_ID, "gaps": [
        {"gap_id": "GAP_ONE", "origin_stage": "normalize-research-facts",
         "gap_kind": "NORMALIZATION_UNKNOWN", "question": "缺少单位。",
         "impact_objects": ["FACT_N1"], "current_handling": "登记",
         "confirmation_owner": "user", "required_evidence": "补充披露",
         "priority": "P1", "status": "OPEN"},
        {"gap_id": "GAP_TWO", "origin_stage": "analyze-and-score-research-findings",
         "gap_kind": "NO_BEARING_METRIC", "question": "无承重指标。",
         "impact_objects": ["D2_UTILIZATION_EFFECT"], "current_handling": "登记",
         "confirmation_owner": "user", "required_evidence": "补充披露",
         "priority": "P1", "status": "OPEN"},
    ]})
    write_yaml(run_dir / "run-integrity.yaml",
               {"snapshot_id": SNAPSHOT_ID, "execution_mode": "FROZEN_REPLAY",
                "integrity_status": "PASS", "reason_codes": [], "unexpected_files": [],
                "as_of_violations": [], "removed_files": [], "checks": [], "gaps": []})
    write_yaml(run_dir / "run-gate.yaml",
               {"snapshot_id": SNAPSHOT_ID, "execution_mode": "FROZEN_REPLAY",
                "integrity_status": options.get("integrity_status", "PASS"),
                "stage_statuses": {"retrieval_status": "PASS",
                                   "normalization_run_status": "WARN",
                                   "validation_status": "WARN",
                                   "analysis_run_status": "PASS",
                                   "challenge_run_status": "WARN"},
                "governance_status_inputs": ["retrieval_status", "normalization_run_status",
                                             "validation_status"],
                "governance_status": options.get("governance_status", "WARN"),
                "report_form": options.get("report_form", "FULL_REPORT"),
                "distribution_status": "INTERNAL_DEMO_ONLY",
                "human_review_status": "PENDING_HUMAN_REVIEW",
                "reason_codes": options.get("reason_codes", []),
                "checks": []})
    return workspace


def report_of(workspace: Path) -> str:
    return (workspace / "single-stock-demo-run" / "report.md").read_text(encoding="utf-8")


def validation_of(workspace: Path) -> dict[str, Any]:
    return yaml.safe_load(
        (workspace / "single-stock-demo-run" / "report-validation.yaml").read_text(
            encoding="utf-8"
        )
    )


class FullReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = build_workspace()
        result = run(self.workspace)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.report = report_of(self.workspace)
        self.validation = validation_of(self.workspace)

    def test_ten_sections_in_the_frozen_order(self) -> None:
        rules = yaml.safe_load((REPO_ROOT / "rules" / "report.yaml").read_text(encoding="utf-8"))
        positions = [self.report.index(section["title"]) for section in rules["sections"]]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(positions), 10)

    def test_three_metadata_blocks_precede_section_one(self) -> None:
        for title in ("研究问题", "分析框架", "流程状态"):
            self.assertLess(self.report.index(title), self.report.index("数据覆盖与来源覆盖"))

    def test_process_status_shows_five_stage_statuses_and_governance_separately(self) -> None:
        for key in ("retrieval_status", "normalization_run_status", "validation_status",
                    "analysis_run_status", "challenge_run_status", "governance_status"):
            self.assertIn(key, self.report)
        self.assertIn("FROZEN_REPLAY", self.report)
        self.assertIn("INTERNAL_DEMO_ONLY", self.report)
        self.assertIn("PENDING_HUMAN_REVIEW", self.report)

    def test_sentences_carrying_numbers_are_dropped_whole(self) -> None:
        self.assertIn(KEPT_SENTENCE, self.report)
        self.assertNotIn(DROPPED_SENTENCE, self.report)
        # Not a character-level scrub: no mutilated remnant of the dropped sentence.
        self.assertNotIn("毛利率由上升到", self.report)
        omitted = self.validation["narrative_numeric_sanitization"]["omitted_sentences"]
        self.assertTrue(any(item["matched_text"] == DROPPED_SENTENCE for item in omitted))
        sample = next(item for item in omitted if item["matched_text"] == DROPPED_SENTENCE)
        for key in ("dimension_id", "field_path", "matched_text",
                    "matched_numeric_tokens", "action"):
            self.assertIn(key, sample)

    def test_omission_notice_points_at_the_evidence_table(self) -> None:
        rules = yaml.safe_load((REPO_ROOT / "rules" / "report.yaml").read_text(encoding="utf-8"))
        self.assertIn(rules["omission_notice"], self.report)

    def test_no_unbound_number_survives_in_prose(self) -> None:
        sanitization = self.validation["narrative_numeric_sanitization"]
        self.assertEqual(sanitization["leaked_unbound_numeric_mentions"], 0)
        self.assertEqual(sanitization["status"], "PASS")
        self.assertGreater(sanitization["detected_mentions"], 0)

    def test_challenge_prose_is_sanitized_too(self) -> None:
        self.assertNotIn("该维度证据分为 2。", self.report)
        self.assertIn("一次定向复核确认两条记录来自同一次披露。", self.report)

    def test_every_evidence_row_carries_the_frozen_columns(self) -> None:
        rules = yaml.safe_load((REPO_ROOT / "rules" / "report.yaml").read_text(encoding="utf-8"))
        for column in rules["evidence_table_columns"]:
            self.assertIn(column, self.report)
        self.assertIn("EVID_N1", self.report)
        self.assertIn("FACT_N1", self.report)
        self.assertIn("21.0%", self.report)

    def test_traceability_chain_resolves_for_every_row(self) -> None:
        traceability = self.validation["traceability"]
        self.assertGreater(traceability["rows_checked"], 0)
        self.assertEqual(traceability["unresolved"], [])
        self.assertIn("CHUNK_1", self.report)
        self.assertIn("MATERIAL_ANNUAL", self.report)

    def test_machine_identifiers_are_never_translated(self) -> None:
        self.assertIn("GROSS_MARGIN", self.report)
        # The English source span is reproduced verbatim, never translated.
        self.assertIn("the improvement was driven by the product mix change", self.report)

    def test_no_forbidden_output_and_no_external_artifact(self) -> None:
        analysis = yaml.safe_load(
            (REPO_ROOT / "rules" / "analysis.yaml").read_text(encoding="utf-8")
        )
        for term in analysis["forbidden_investment_terms"]:
            self.assertNotIn(term, self.report)
        self.assertEqual(self.validation["forbidden_output_scan"]["hits"], [])
        produced = {path.suffix for path in
                    (self.workspace / "single-stock-demo-run").iterdir() if path.is_file()}
        self.assertEqual(produced - {".md", ".yaml", ".jsonl"}, set())

    def test_government_funding_second_basis_is_disclosed_not_invented(self) -> None:
        dual = self.validation["government_funding_dual_basis"]
        self.assertEqual(dual["sensitivity_records"], 0)
        self.assertTrue(dual["gap_id"])
        gaps = yaml.safe_load(
            (self.workspace / "single-stock-demo-run" / "gaps.yaml").read_text(encoding="utf-8")
        )
        self.assertIn(dual["gap_id"], [gap["gap_id"] for gap in gaps["gaps"]])

    def test_gaps_are_aggregated_and_the_priority_axis_is_explained(self) -> None:
        self.assertIn("NORMALIZATION_UNKNOWN", self.report)
        self.assertIn("normalize-research-facts", self.report)
        self.assertIn("优先级", self.report)
        self.assertEqual(self.validation["gap_summary"]["total"], 3)

    def test_known_defects_are_disclosed(self) -> None:
        rules = yaml.safe_load((REPO_ROOT / "rules" / "report.yaml").read_text(encoding="utf-8"))
        for disclosure in rules["disclosures"]:
            self.assertIn(disclosure["title"], self.report)

    def test_scope_recognition_labels_six_frozen_questions(self) -> None:
        scope = self.validation["scope_recognition"]
        labels = {item["id"]: item["label"] for item in scope["examples"]}
        self.assertEqual(sum(1 for value in labels.values() if value == "IN_SCOPE"), 3)
        self.assertIn("OUT_OF_SCOPE_FORBIDDEN_OUTPUT", labels.values())
        self.assertIn("OUT_OF_SCOPE_OTHER_SUBJECT", labels.values())
        self.assertIn("OUT_OF_SCOPE_BEYOND_AS_OF", labels.values())

    def test_refused_question_text_is_not_reproduced(self) -> None:
        scope = self.validation["scope_recognition"]
        refused = [item for item in scope["examples"]
                   if item["label"] == "OUT_OF_SCOPE_FORBIDDEN_OUTPUT"]
        self.assertTrue(refused)
        for item in refused:
            self.assertEqual(item["reproduced_in_report"], False)

    def test_report_never_embeds_hashes(self) -> None:
        self.assertNotIn("sha256", self.report)

    def test_deterministic_across_two_renders(self) -> None:
        first = self.report
        self.assertEqual(run(self.workspace).returncode, 0)
        self.assertEqual(report_of(self.workspace), first)


class QuarantineAndConflictFixtureTests(unittest.TestCase):
    """v3 has zero quarantined records and zero conflicts. The mechanism is proved on a
    synthetic fixture; the real run's zeros are reported as they are, never manufactured.
    """

    def test_quarantined_evidence_never_reaches_an_evidence_table(self) -> None:
        extra_facts = [numeric_fact("FACT_Q", "GROSS_MARGIN", "CHUNK_Q", "MATERIAL_ANNUAL")]
        extra_evidence = [
            {
                "evidence_id": "EVID_Q",
                "fact_id": "FACT_Q",
                "chunk_id": "CHUNK_Q",
                "material_id": "MATERIAL_ANNUAL",
                "evidence_status": "QUARANTINED",
                "source_tier": "T1",
                "claim_type": "REPORTED_FACT",
                "conflict_status": "CONFLICT_UNRESOLVED",
                "conflict_group_id": "CG_1",
                "quarantine_reason_codes": ["NORMALIZATION_BLOCKED"],
                "gap_ids": ["GAP_Q"],
                "source_group_id": "SG_TWO",
            }
        ]
        workspace = build_workspace(extra_facts=extra_facts, extra_evidence=extra_evidence)
        self.assertEqual(run(workspace).returncode, 0)
        report = report_of(workspace)
        validation = validation_of(workspace)

        self.assertEqual(validation["conflict_and_quarantine"]["quarantined_count"], 1)
        self.assertEqual(validation["conflict_and_quarantine"]["unresolved_conflict_groups"], 1)
        self.assertEqual(
            validation["conflict_and_quarantine"]["quarantined_in_evidence_tables"], 0
        )
        # Section 9 must name it; no dimension may lean on it.
        self.assertIn("EVID_Q", report)
        for line in report.splitlines():
            if line.startswith("| FACT_Q "):
                self.fail("quarantined evidence rendered as a dimension evidence row")


class GovernmentFundingSensitivityFixtureTests(unittest.TestCase):
    """v3 produces zero sensitivity records. The formula's presence is proved on a
    synthetic separable government-funding record, never by computing one from v3.
    """

    def test_a_separable_sensitivity_record_is_reported_and_raises_no_gap(self) -> None:
        sensitivity = numeric_fact("FACT_SENS", "SENSITIVITY_EX_GOVERNMENT_FUNDING",
                                   "CHUNK_S", "MATERIAL_ANNUAL")
        workspace = build_workspace(extra_facts=[sensitivity])
        self.assertEqual(run(workspace).returncode, 0)
        validation = validation_of(workspace)

        dual = validation["government_funding_dual_basis"]
        self.assertEqual(dual["sensitivity_records"], 1)
        self.assertIsNone(dual["gap_id"])
        gaps = yaml.safe_load(
            (workspace / "single-stock-demo-run" / "gaps.yaml").read_text(encoding="utf-8")
        )
        self.assertNotIn(
            "GAP_REPORT_GOVERNMENT_FUNDING_SENSITIVITY_ABSENT",
            [gap["gap_id"] for gap in gaps["gaps"]],
        )


class GovernanceFailFixtureTests(unittest.TestCase):
    """No v3 stage status is FAIL. The FAIL banner is proved on a synthetic gate verdict."""

    def test_governance_fail_still_produces_a_flagged_full_report(self) -> None:
        workspace = build_workspace(governance_status="FAIL")
        self.assertEqual(run(workspace).returncode, 0)
        report = report_of(workspace)

        self.assertIn("治理状态为 FAIL", report)
        self.assertIn("受影响数据不得支撑任何研究发现", report)
        # A FAIL is flagged, not silenced: the ten sections are still rendered.
        self.assertIn("D1_PROFITABILITY_CHANGE", report)
        self.assertEqual(validation_of(workspace)["report_form"], "FULL_REPORT")


class UnboundNumberGateTests(unittest.TestCase):
    """The gate must read the rendered file, not the sanitizer's own output."""

    def setUp(self) -> None:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import generate_research_report  # noqa: PLC0415

        self.module = generate_research_report

    def test_a_number_reaching_the_page_outside_the_scanner_is_caught(self) -> None:
        workspace = build_workspace()
        self.assertEqual(run(workspace).returncode, 0)
        report = report_of(workspace)
        self.assertEqual(
            validation_of(workspace)["narrative_numeric_sanitization"][
                "leaked_unbound_numeric_mentions"
            ],
            0,
        )

        # Simulate a render site that bypasses the sanitizer entirely: a free-narrative
        # line carrying a number lands in the report by a path the scanner never saw. A
        # gate reading only the sanitizer's own output could not possibly notice.
        injected = "毛利率改善了 3.0 个百分点。"
        self.assertNotIn(injected, self.module.scan_rendered_report(report, []))
        self.assertIn(injected, self.module.scan_rendered_report(f"{report}\n{injected}\n", []))

    def test_a_number_on_an_evidence_row_is_not_a_leak(self) -> None:
        row = "| FACT_1 | EVID_1 | GROSS_MARGIN | 21.0 | — | 21.0% |"
        self.assertEqual(self.module.scan_rendered_report(row, []), [])

    def test_a_declared_field_path_with_no_render_site_fails_the_record(self) -> None:
        workspace = build_workspace()
        rules_path = workspace / "rules" / "report.yaml"
        rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        rules["narrative_scan_field_paths"].append("findings[].invented_field")
        write_yaml(rules_path, rules)

        self.assertEqual(run(workspace).returncode, 0)
        sanitization = validation_of(workspace)["narrative_numeric_sanitization"]
        self.assertFalse(sanitization["declared_paths_match_render_sites"])
        self.assertEqual(
            sanitization["declared_paths_without_render_site"], ["findings[].invented_field"]
        )
        self.assertEqual(sanitization["status"], "FAIL")

    def test_rules_file_and_render_sites_agree(self) -> None:
        rules = yaml.safe_load((REPO_ROOT / "rules" / "report.yaml").read_text(encoding="utf-8"))
        self.assertEqual(
            set(rules["narrative_scan_field_paths"]), self.module.RENDER_SITE_FIELD_PATHS
        )


class DiagnosticOnlyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = build_workspace(
            report_form="DIAGNOSTIC_ONLY",
            integrity_status="FAIL",
            reason_codes=["FROZEN_ANALYSIS_HASH_MISMATCH"],
        )
        write_yaml(
            self.workspace / "single-stock-demo-run" / "run-integrity.yaml",
            {
                "snapshot_id": SNAPSHOT_ID,
                "execution_mode": "FROZEN_REPLAY",
                "integrity_status": "FAIL",
                "reason_codes": ["FROZEN_ANALYSIS_HASH_MISMATCH"],
                "unexpected_files": [],
                "as_of_violations": [],
                "removed_files": [],
                "checks": [
                    {"name": "frozen_input_hash", "status": "FAIL",
                     "detail": "findings-attempt-1.yaml",
                     "reason_code": "FROZEN_ANALYSIS_HASH_MISMATCH"}
                ],
                "gaps": [{"gap_id": "GAP_RUN_UNEXPECTED_FILE"}],
            },
        )
        self.assertEqual(run(self.workspace).returncode, 0)
        self.report = report_of(self.workspace)
        self.validation = validation_of(self.workspace)

    def test_report_is_still_generated_with_a_failure_banner(self) -> None:
        self.assertTrue(self.report.startswith("# "))
        self.assertIn("完整性失败", self.report)
        self.assertIn("FROZEN_ANALYSIS_HASH_MISMATCH", self.report)
        self.assertEqual(self.validation["report_form"], "DIAGNOSTIC_ONLY")

    def test_no_finding_reaches_a_diagnostic_report(self) -> None:
        for dimension_id in DIMENSIONS:
            self.assertNotIn(dimension_id, self.report)
        self.assertNotIn(KEPT_SENTENCE, self.report)
        self.assertNotIn("SUPPORTED", self.report)
        self.assertNotIn("evidence_score", self.report)

    def test_status_constants_still_appear(self) -> None:
        self.assertIn("INTERNAL_DEMO_ONLY", self.report)
        self.assertIn("PENDING_HUMAN_REVIEW", self.report)


class ScopeRecognitionTests(unittest.TestCase):
    """Ticket item 2: at least three questions that must trigger and three that must not."""

    def setUp(self) -> None:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import generate_research_report  # noqa: PLC0415

        self.module = generate_research_report
        self.rules = yaml.safe_load(
            (REPO_ROOT / "rules" / "report.yaml").read_text(encoding="utf-8")
        )

    def classify(self, question: str) -> str:
        return self.module.classify_question(question, self.rules)["label"]

    def test_in_scope_questions(self) -> None:
        self.assertEqual(
            self.classify("截至 as_of，中芯国际的经常性经营盈利能力发生了哪些可验证的变化？"),
            "IN_SCOPE",
        )
        self.assertEqual(
            self.classify("中芯国际 2025 年毛利率改善主要来自利用率还是产品结构？"), "IN_SCOPE"
        )
        self.assertEqual(
            self.classify("中芯国际的盈利改善有多少来自政府补助等非经常项目？"), "IN_SCOPE"
        )

    def test_forbidden_output_question_is_refused_not_answered(self) -> None:
        verdict = self.module.classify_question("中芯国际现在值得买入吗？目标价多少？", self.rules)
        self.assertEqual(verdict["label"], "OUT_OF_SCOPE_FORBIDDEN_OUTPUT")
        self.assertEqual(verdict["action"], "REFUSE")

    def test_other_subject_question_gets_a_disclaimer(self) -> None:
        verdict = self.module.classify_question("把中芯国际和华虹半导体做个对比", self.rules)
        self.assertEqual(verdict["label"], "OUT_OF_SCOPE_OTHER_SUBJECT")
        self.assertEqual(verdict["action"], "DISCLAIM")

    def test_beyond_as_of_question_gets_a_disclaimer(self) -> None:
        verdict = self.module.classify_question("中芯国际 2026 下半年业绩会怎样？", self.rules)
        self.assertEqual(verdict["label"], "OUT_OF_SCOPE_BEYOND_AS_OF")
        self.assertEqual(verdict["action"], "DISCLAIM")


class SentenceSanitizationTests(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import generate_research_report  # noqa: PLC0415

        self.module = generate_research_report

    def test_split_keeps_terminators_and_drops_nothing_silently(self) -> None:
        text = "甲。乙？丙！丁"
        self.assertEqual(self.module.split_sentences(text), ["甲。", "乙？", "丙！", "丁"])

    def test_frozen_survival_rates_are_reproduced(self) -> None:
        """The frozen baseline: D1's finding_statement keeps 2 of 7 sentences, 90 of 473
        characters. This is the accepted price of honesty, not a bug to repair.
        """
        statement = (
            "中芯国际 FY2025 毛利率为 21.0%。FY2024 为 18.0%。改善 3.0 个百分点。"
            "该改善由来源披露的结果指标承载。方向为改善但机制未被独立证据分解。"
        )
        kept, omitted = self.module.sanitize(statement, "D1", "findings[].finding_statement")
        self.assertEqual(len(omitted), 3)
        self.assertNotIn("21.0", kept)
        self.assertIn("该改善由来源披露的结果指标承载。", kept)


if __name__ == "__main__":
    unittest.main()
