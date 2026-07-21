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
CLI = REPO_ROOT / "scripts" / "analyze_and_score_research_findings.py"
RULES_FILE = REPO_ROOT / "rules" / "analysis.yaml"
SNAPSHOT_ID = "smic-a283e95e2c9e8068"
CONTEXT_RULE_VERSION = "smic-v3-context-retrieval-v3"

DIMENSIONS = [
    "D1_PROFITABILITY_CHANGE",
    "D2_UTILIZATION_EFFECT",
    "D3_MIX_EFFECT",
    "D4_CAPEX_CONVERSION",
    "D5_CYCLE_EXPLANATION",
    "D6_NONCORE_EXPLANATION",
    "D7_SUSTAINABILITY_EVIDENCE",
]

# Real pipeline outputs used by the end-to-end test (skipped if absent).
TICKET03_DIR = REPO_ROOT / "tmp" / "ticket03-final"
TICKET04_DIR = REPO_ROOT / "tmp" / "ticket04-final"
SNAPSHOT_DIR = REPO_ROOT / "single-stock-demo-v3"


def sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args], capture_output=True, text=True, encoding="utf-8"
    )


def evidence_id_for(fact_id: str) -> str:
    return "EVID_" + hashlib.sha256(fact_id.encode("utf-8")).hexdigest()[:24]


class World:
    """A tiny but complete D1-D7 world: two source groups per dimension, text plus numerics."""

    def __init__(self) -> None:
        self.chunks: list[dict[str, Any]] = []
        self.facts: list[dict[str, Any]] = []
        self.evidence: list[dict[str, Any]] = []

    def add_chunk(
        self,
        chunk_id: str,
        dimension_id: str,
        source_group_id: str,
        score: float,
        text: str,
        text_facts: int = 2,
        numerics: list[dict[str, Any]] | None = None,
        evidence_status: str = "USABLE",
        claim_type: str = "REPORTED_FACT",
    ) -> None:
        self.chunks.append(
            {
                "chunk_id": chunk_id,
                "snapshot_id": SNAPSHOT_ID,
                "material_id": f"MATERIAL_{source_group_id}",
                "query_rule_version": CONTEXT_RULE_VERSION,
                "structure_type": "PDF_SECTION",
                "content_locator": {"section": chunk_id},
                "text": text,
                "retrieval_hits": [
                    {"query_family_id": dimension_id, "query_id": f"{dimension_id}_ZH", "score": score}
                ],
            }
        )
        for index in range(text_facts):
            self._add_fact(
                fact_id=f"FACT_{chunk_id}_T{index}",
                chunk_id=chunk_id,
                source_group_id=source_group_id,
                record_kind="TEXT_PROPOSITION",
                evidence_status=evidence_status,
                claim_type=claim_type,
                extra={"source_span_text": f"{text[:20]} 命题 {index}"},
            )
        for index, numeric in enumerate(numerics or []):
            self._add_fact(
                fact_id=f"FACT_{chunk_id}_N{index}",
                chunk_id=chunk_id,
                source_group_id=source_group_id,
                record_kind="NUMERIC_OBSERVATION",
                evidence_status=numeric.pop("evidence_status", evidence_status),
                claim_type=numeric.pop("claim_type", claim_type),
                extra={"source_span_text": f"数值 {index}", **numeric},
            )

    def _add_fact(
        self,
        fact_id: str,
        chunk_id: str,
        source_group_id: str,
        record_kind: str,
        evidence_status: str,
        claim_type: str,
        extra: dict[str, Any],
    ) -> None:
        fact = {
            "fact_id": fact_id,
            "chunk_id": chunk_id,
            "snapshot_id": SNAPSHOT_ID,
            "material_id": f"MATERIAL_{source_group_id}",
            "record_kind": record_kind,
            "content_locator": {"section": chunk_id},
            **extra,
        }
        self.facts.append(fact)
        self.evidence.append(
            {
                "evidence_id": evidence_id_for(fact_id),
                "fact_id": fact_id,
                "chunk_id": chunk_id,
                "material_id": fact["material_id"],
                "snapshot_id": SNAPSHOT_ID,
                "record_kind": record_kind,
                "evidence_status": evidence_status,
                "claim_type": claim_type,
                "source_tier": "T1",
                "source_group_id": source_group_id,
                "conflict_status": "NO_CONFLICT",
            }
        )


def default_world() -> World:
    world = World()
    for dimension_id in DIMENSIONS:
        short = dimension_id.split("_")[0]
        world.add_chunk(f"CHUNK_{short}_A", dimension_id, f"SG_{short}_A", 30.0, f"{short} 甲段落")
        world.add_chunk(f"CHUNK_{short}_B", dimension_id, f"SG_{short}_B", 20.0, f"{short} 乙段落")
    # D1 carries a comparable cross-period whitelisted metric across two source groups.
    world.add_chunk(
        "CHUNK_D1_NUM_A",
        "D1_PROFITABILITY_CHANGE",
        "SG_D1_A",
        29.0,
        "D1 数值段落甲",
        numerics=[
            {
                "metric_id": "GROSS_MARGIN",
                "normalized_value": "18.0",
                "target_unit": "PERCENT",
                "period_type": "FISCAL_YEAR",
                "period_start": "2024-01-01",
                "period_end": "2024-12-31",
            }
        ],
    )
    world.add_chunk(
        "CHUNK_D1_NUM_B",
        "D1_PROFITABILITY_CHANGE",
        "SG_D1_B",
        28.0,
        "D1 数值段落乙",
        numerics=[
            {
                "metric_id": "GROSS_MARGIN",
                "normalized_value": "21.0",
                "target_unit": "PERCENT",
                "period_type": "FISCAL_YEAR",
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
            }
        ],
    )
    return world


def legal_finding(dimension_id: str, supports: list[str], **overrides: Any) -> dict[str, Any]:
    finding: dict[str, Any] = {
        "dimension_id": dimension_id,
        "finding": "MIXED",
        "finding_statement": f"{dimension_id} 的可承重证据显示相关指标同时变化，方向部分成立。",
        "supporting_evidence": [
            {
                "evidence_id": evidence_id,
                "role": "PRIMARY_SUPPORT",
                "note": "该记录与本维度问题直接相关。",
                "overlap_note": "同一事实未在其他维度作为承重证据使用。",
            }
            for evidence_id in supports
        ],
        "counter_evidence": [],
        "alternative_explanations": ["行业层面的同期变化亦与该观察一致。"],
        "limitations": ["候选集内可承重数值有限。"],
        "gaps": [],
        "management_assertions": [],
    }
    if dimension_id == "D7_SUSTAINABILITY_EVIDENCE":
        finding["watch_indicators"] = [
            {
                "indicator": "季度毛利率",
                "judgment_logic": "若连续两个季度回落至改善前水平，本发现应下调。",
                "threshold": "UNKNOWN",
                "threshold_basis": "UNKNOWN",
                "basis_evidence_id": None,
            }
        ]
    finding.update(overrides)
    return finding


class AnalysisFixtureTests(unittest.TestCase):
    def _workspace(self, world: World, rules: dict[str, Any] | None = None) -> Path:
        workspace = Path(tempfile.mkdtemp())
        snapshot_dir = workspace / "snapshot"
        snapshot_dir.mkdir()
        (snapshot_dir / "snapshot-manifest.yaml").write_text(
            yaml.safe_dump({"snapshot_id": SNAPSHOT_ID, "files": []}), encoding="utf-8"
        )
        for name, rows in (
            ("context.jsonl", world.chunks),
            ("facts.jsonl", world.facts),
            ("evidence.jsonl", world.evidence),
        ):
            (workspace / name).write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                encoding="utf-8",
            )
        (workspace / "gaps.yaml").write_text(
            yaml.safe_dump({"snapshot_id": SNAPSHOT_ID, "gaps": []}), encoding="utf-8"
        )
        rules_document = rules or yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
        (workspace / "rules.yaml").write_text(
            yaml.safe_dump(rules_document, allow_unicode=True), encoding="utf-8"
        )
        return workspace

    def _select(self, workspace: Path) -> subprocess.CompletedProcess[str]:
        return run_cli(
            [
                "select",
                "--snapshot-dir", str(workspace / "snapshot"),
                "--context-file", str(workspace / "context.jsonl"),
                "--facts-file", str(workspace / "facts.jsonl"),
                "--evidence-file", str(workspace / "evidence.jsonl"),
                "--rules-file", str(workspace / "rules.yaml"),
                "--existing-gaps-file", str(workspace / "gaps.yaml"),
                "--output-dir", str(workspace / "inputs"),
            ]
        )

    def _finalize(
        self, workspace: Path, attempts: list[list[dict[str, Any]]]
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any], dict[str, Any]]:
        args = [
            "finalize",
            "--analysis-inputs", str(workspace / "inputs" / "analysis-inputs.jsonl"),
            "--rules-file", str(workspace / "rules.yaml"),
            "--existing-gaps-file", str(workspace / "gaps.yaml"),
            "--output-dir", str(workspace / "out"),
        ]
        for index, findings in enumerate(attempts):
            path = workspace / f"model-{index}.yaml"
            path.write_text(
                yaml.safe_dump(
                    {"snapshot_id": SNAPSHOT_ID, "findings": findings},
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            args += ["--model-findings", str(path)]
        result = run_cli(args)
        findings_doc: dict[str, Any] = {}
        validation: dict[str, Any] = {}
        if (workspace / "out" / "findings.yaml").exists():
            findings_doc = yaml.safe_load(
                (workspace / "out" / "findings.yaml").read_text(encoding="utf-8")
            )
        if (workspace / "out" / "analysis-validation.yaml").exists():
            validation = yaml.safe_load(
                (workspace / "out" / "analysis-validation.yaml").read_text(encoding="utf-8")
            )
        return result, findings_doc, validation

    def _rows(self, workspace: Path) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in (workspace / "inputs" / "analysis-inputs.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

    def _candidates(self, workspace: Path, dimension_id: str, record_kind: str) -> list[str]:
        return [
            row["evidence_id"]
            for row in self._rows(workspace)
            if row.get("record_type") == "CANDIDATE_EVIDENCE"
            and row["dimension_id"] == dimension_id
            and row["record_kind"] == record_kind
        ]

    def _one_per_group(self, workspace: Path, dimension_id: str) -> list[str]:
        """One text evidence id per source group, so a support set spans several groups."""
        chosen: dict[str, str] = {}
        for row in self._rows(workspace):
            if (
                row.get("record_type") != "CANDIDATE_EVIDENCE"
                or row["dimension_id"] != dimension_id
                or row["record_kind"] != "TEXT_PROPOSITION"
            ):
                continue
            chosen.setdefault(str(row["source_group_id"]), str(row["evidence_id"]))
        return [chosen[key] for key in sorted(chosen)]

    def _rejected_errors(self, validation: dict[str, Any], dimension_id: str) -> list[str]:
        return [
            error
            for entry in validation["rejected_attempts"]
            if entry["dimension_id"] == dimension_id
            for error in entry["errors"]
        ]

    def _prepare(self, world: World | None = None) -> Path:
        workspace = self._workspace(world or default_world())
        result = self._select(workspace)
        self.assertEqual(result.returncode, 0, result.stderr)
        return workspace

    def _check(self, validation: dict[str, Any], name: str) -> dict[str, Any]:
        return next(check for check in validation["checks"] if check["check"] == name)

    # ------------------------------------------------------------------
    # Selection layer.
    # ------------------------------------------------------------------
    def test_selection_is_closed_deterministic_and_seeded_across_source_groups(self) -> None:
        workspace = self._prepare()
        summary = self._rows(workspace)[0]
        for dimension_id in DIMENSIONS:
            stats = summary["dimensions"][dimension_id]
            self.assertGreaterEqual(stats["source_group_count"], 2, dimension_id)
            self.assertEqual(stats["skipped_due_budget_count"], 0, dimension_id)
        # D1 keeps both cross-period whitelisted numerics; every other dimension has none.
        self.assertEqual(summary["dimensions"]["D1_PROFITABILITY_CHANGE"]["bearing_numeric_count"], 2)

        first = (workspace / "inputs" / "analysis-inputs.jsonl").read_bytes()
        result = self._select(workspace)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(first, (workspace / "inputs" / "analysis-inputs.jsonl").read_bytes())

    def test_selection_excludes_non_usable_evidence(self) -> None:
        world = default_world()
        world.add_chunk(
            "CHUNK_D1_RESTRICTED",
            "D1_PROFITABILITY_CHANGE",
            "SG_D1_C",
            99.0,
            "受限段落",
            evidence_status="RESTRICTED",
        )
        workspace = self._prepare(world)
        rows = (workspace / "inputs" / "analysis-inputs.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("CHUNK_D1_RESTRICTED", rows)

    def test_selection_stops_at_budget_and_records_skipped_chunks(self) -> None:
        world = default_world()
        for index in range(6):
            world.add_chunk(
                f"CHUNK_D5_BIG_{index}",
                "D5_CYCLE_EXPLANATION",
                f"SG_D5_BIG_{index}",
                float(50 - index),
                "周" * 20000,
            )
        workspace = self._prepare(world)
        stats = self._rows(workspace)[0]["dimensions"]["D5_CYCLE_EXPLANATION"]
        self.assertLessEqual(stats["selected_chars"], 60000 * 1.10)
        self.assertGreater(stats["skipped_due_budget_count"], 0)
        self.assertTrue(stats["skipped_due_budget"])

    def test_selection_records_a_gap_when_a_dimension_has_no_usable_text(self) -> None:
        world = World()
        for dimension_id in DIMENSIONS:
            if dimension_id == "D5_CYCLE_EXPLANATION":
                continue
            short = dimension_id.split("_")[0]
            world.add_chunk(f"CHUNK_{short}_A", dimension_id, f"SG_{short}_A", 30.0, f"{short} 段落")
        workspace = self._prepare(world)
        gaps = yaml.safe_load((workspace / "inputs" / "gaps.yaml").read_text(encoding="utf-8"))
        gap_ids = [gap["gap_id"] for gap in gaps["gaps"]]
        self.assertIn("GAP_ANALYSIS_SELECTION_D5_CYCLE_EXPLANATION", gap_ids)

    # ------------------------------------------------------------------
    # Finalize layer: the positive fixture.
    # ------------------------------------------------------------------
    def test_legal_findings_pass_and_scores_are_derived(self) -> None:
        workspace = self._prepare()
        findings = [
            legal_finding(
                dimension_id,
                self._one_per_group(workspace, dimension_id)
                + self._candidates(workspace, dimension_id, "NUMERIC_OBSERVATION"),
            )
            for dimension_id in DIMENSIONS
        ]
        result, document, validation = self._finalize(workspace, [findings])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(validation["analysis_run_status"], "PASS")
        for check in validation["checks"]:
            self.assertEqual(check["status"], "PASS", check)

        self.assertEqual(document["overall_score"], "NOT_APPLICABLE")
        self.assertEqual(document["summary"]["overall_score"], "NOT_APPLICABLE")
        self.assertNotIn("recommendation", yaml.safe_dump(document))
        by_id = {finding["dimension_id"]: finding for finding in document["findings"]}
        # D1: cross-period whitelisted metric + two source groups -> 3.
        self.assertEqual(by_id["D1_PROFITABILITY_CHANGE"]["evidence_score"], 3)
        # Other dimensions: two source groups, no numerics -> 2.
        self.assertEqual(by_id["D5_CYCLE_EXPLANATION"]["evidence_score"], 2)
        self.assertTrue(
            all(finding["finding_reason_code"] == "MODEL_JUDGMENT" for finding in document["findings"])
        )

    def test_score_one_for_a_single_source_group_and_zero_forces_unknown(self) -> None:
        workspace = self._prepare()
        findings = []
        for dimension_id in DIMENSIONS:
            text = self._candidates(workspace, dimension_id, "TEXT_PROPOSITION")
            if dimension_id == "D2_UTILIZATION_EFFECT":
                findings.append(legal_finding(dimension_id, text[:1]))  # one source group
            elif dimension_id == "D3_MIX_EFFECT":
                findings.append(
                    legal_finding(dimension_id, [], finding="UNKNOWN")  # no support at all
                )
            else:
                findings.append(legal_finding(dimension_id, text[:2]))
        result, document, validation = self._finalize(workspace, [findings])
        self.assertEqual(result.returncode, 0, result.stderr)
        by_id = {finding["dimension_id"]: finding for finding in document["findings"]}
        self.assertEqual(by_id["D2_UTILIZATION_EFFECT"]["evidence_score"], 1)
        self.assertEqual(by_id["D3_MIX_EFFECT"]["evidence_score"], 0)
        self.assertEqual(by_id["D3_MIX_EFFECT"]["finding_reason_code"], "NO_BEARING_EVIDENCE")
        self.assertEqual(self._check(validation, "score_status_binding")["status"], "PASS")

    def test_score_zero_with_a_non_unknown_finding_is_rejected(self) -> None:
        # The binding is part of the per-attempt gate, so a violating output can be
        # regenerated instead of landing in findings.yaml and only failing afterwards.
        workspace = self._prepare()
        findings = [
            legal_finding(dimension_id, self._candidates(workspace, dimension_id, "TEXT_PROPOSITION")[:2])
            for dimension_id in DIMENSIONS
        ]
        findings[2] = legal_finding("D3_MIX_EFFECT", [], finding="SUPPORTED")
        _, document, validation = self._finalize(workspace, [findings])
        self.assertIn(
            "SCORE_ZERO_REQUIRES_UNKNOWN", self._rejected_errors(validation, "D3_MIX_EFFECT")
        )
        self.assertEqual(validation["analysis_run_status"], "FAIL")
        self.assertEqual(self._check(validation, "score_status_binding")["status"], "PASS")
        self.assertEqual(document["findings"][2]["finding"], "UNKNOWN")

    # ------------------------------------------------------------------
    # Finalize layer: the negative fixtures.
    # ------------------------------------------------------------------
    def _finalize_with_broken(self, broken: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], Path]:
        workspace = self._prepare()
        findings = [
            legal_finding(dimension_id, self._candidates(workspace, dimension_id, "TEXT_PROPOSITION")[:2])
            for dimension_id in DIMENSIONS
        ]
        findings = [broken if item["dimension_id"] == broken["dimension_id"] else item for item in findings]
        _, document, validation = self._finalize(workspace, [findings])
        return document, validation, workspace

    def test_investment_language_is_rejected_and_the_hit_term_is_named(self) -> None:
        # A rejected model output never reaches findings.yaml, so the run fails through
        # generation_attempts_bounded while rejected_attempts names the term that was hit.
        broken = legal_finding(
            "D1_PROFITABILITY_CHANGE",
            [],
            finding="UNKNOWN",
            finding_statement="盈利能力改善明显，当前股价明显低估，可考虑买入。",
        )
        document, validation, _ = self._finalize_with_broken(broken)
        errors = self._rejected_errors(validation, "D1_PROFITABILITY_CHANGE")
        self.assertTrue(any("FORBIDDEN_INVESTMENT_TERM" in error and "买入" in error for error in errors))
        self.assertTrue(any("FORBIDDEN_INVESTMENT_TERM" in error and "低估" in error for error in errors))
        self.assertEqual(validation["analysis_run_status"], "FAIL")
        self.assertEqual(
            self._check(validation, "generation_attempts_bounded")["forced_dimensions"],
            ["D1_PROFITABILITY_CHANGE"],
        )
        self.assertNotIn("买入", yaml.safe_dump(document, allow_unicode=True))

    def test_ordinary_forecast_wording_is_not_a_forbidden_term(self) -> None:
        # 建议/预计/有望/估值 stay legal: "management expects capacity to expand" is a
        # legitimate sourced statement and a wide term list would drown the run in noise.
        workspace = self._prepare()
        findings = [
            legal_finding(
                dimension_id,
                self._candidates(workspace, dimension_id, "TEXT_PROPOSITION")[:2],
                limitations=["公司预计产能有望继续扩张，本维度对该表述不做估值层面的延伸。"],
            )
            for dimension_id in DIMENSIONS
        ]
        _, _, validation = self._finalize(workspace, [findings])
        self.assertEqual(self._check(validation, "forbidden_output_terms")["status"], "PASS")

    def test_unattributed_causal_wording_is_rejected_but_attributed_wording_passes(self) -> None:
        broken = legal_finding(
            "D2_UTILIZATION_EFFECT",
            [],
            finding="UNKNOWN",
            finding_statement="产能利用率上升带动了毛利率改善。",
        )
        _, validation, _ = self._finalize_with_broken(broken)
        errors = self._rejected_errors(validation, "D2_UTILIZATION_EFFECT")
        self.assertTrue(
            any("UNATTRIBUTED_CAUSAL_CLAIM" in error and "带动" in error for error in errors)
        )
        self.assertEqual(validation["analysis_run_status"], "FAIL")

        attributed = legal_finding(
            "D2_UTILIZATION_EFFECT",
            [],
            finding="UNKNOWN",
            finding_statement="公司称产能利用率上升带动了毛利率改善，本阶段不对该因果作独立确认。",
        )
        _, validation, _ = self._finalize_with_broken(attributed)
        self.assertEqual(self._check(validation, "causal_attribution")["status"], "PASS")
        self.assertEqual(validation["rejected_attempts"], [])

    def test_management_assertion_cannot_support_a_finding(self) -> None:
        world = default_world()
        world.add_chunk(
            "CHUNK_D4_MGMT",
            "D4_CAPEX_CONVERSION",
            "SG_D4_C",
            40.0,
            "管理层说明段落",
            claim_type="MANAGEMENT_ASSERTION",
        )
        workspace = self._workspace(world)
        self.assertEqual(self._select(workspace).returncode, 0)
        assertion_ids = [
            row
            for row in self._candidates(workspace, "D4_CAPEX_CONVERSION", "TEXT_PROPOSITION")
            if row
        ]
        rows = [
            json.loads(line)
            for line in (workspace / "inputs" / "analysis-inputs.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        management_id = next(
            row["evidence_id"]
            for row in rows
            if row.get("record_type") == "CANDIDATE_EVIDENCE"
            and row.get("claim_type") == "MANAGEMENT_ASSERTION"
        )
        self.assertIn(management_id, assertion_ids)
        findings = [
            legal_finding(dimension_id, self._candidates(workspace, dimension_id, "TEXT_PROPOSITION")[:2])
            for dimension_id in DIMENSIONS
        ]
        findings[3] = legal_finding("D4_CAPEX_CONVERSION", [management_id])
        _, _, validation = self._finalize(workspace, [findings])
        errors = self._rejected_errors(validation, "D4_CAPEX_CONVERSION")
        self.assertTrue(any(error.startswith("MANAGEMENT_ASSERTION_AS_SUPPORT") for error in errors))
        self.assertEqual(validation["analysis_run_status"], "FAIL")

    def test_citing_another_dimensions_evidence_breaks_candidate_set_closure(self) -> None:
        workspace = self._prepare()
        foreign = self._candidates(workspace, "D6_NONCORE_EXPLANATION", "TEXT_PROPOSITION")[0]
        findings = [
            legal_finding(dimension_id, self._candidates(workspace, dimension_id, "TEXT_PROPOSITION")[:2])
            for dimension_id in DIMENSIONS
        ]
        findings[4] = legal_finding("D5_CYCLE_EXPLANATION", [foreign])
        _, _, validation = self._finalize(workspace, [findings])
        errors = self._rejected_errors(validation, "D5_CYCLE_EXPLANATION")
        self.assertTrue(any(error.startswith("EVIDENCE_OUTSIDE_CANDIDATE_SET") for error in errors))
        self.assertEqual(validation["analysis_run_status"], "FAIL")

    def test_invented_evidence_id_is_rejected(self) -> None:
        broken = legal_finding("D6_NONCORE_EXPLANATION", ["EVID_000000000000000000000000"])
        _, validation, _ = self._finalize_with_broken(broken)
        errors = self._rejected_errors(validation, "D6_NONCORE_EXPLANATION")
        self.assertTrue(any(error.startswith("EVIDENCE_UNKNOWN_ID") for error in errors))

    def test_cross_dimension_primary_support_needs_an_overlap_note(self) -> None:
        world = default_world()
        # One shared chunk retrieved by both D2 and D4, so one fact can bear weight twice.
        world.chunks.append(
            {
                "chunk_id": "CHUNK_SHARED",
                "snapshot_id": SNAPSHOT_ID,
                "material_id": "MATERIAL_SG_SHARED",
                "query_rule_version": CONTEXT_RULE_VERSION,
                "structure_type": "PDF_SECTION",
                "content_locator": {"section": "shared"},
                "text": "共享段落",
                "retrieval_hits": [
                    {"query_family_id": "D2_UTILIZATION_EFFECT", "query_id": "D2_ZH", "score": 45.0},
                    {"query_family_id": "D4_CAPEX_CONVERSION", "query_id": "D4_ZH", "score": 45.0},
                ],
            }
        )
        world._add_fact(
            fact_id="FACT_SHARED_T0",
            chunk_id="CHUNK_SHARED",
            source_group_id="SG_SHARED",
            record_kind="TEXT_PROPOSITION",
            evidence_status="USABLE",
            claim_type="REPORTED_FACT",
            extra={"source_span_text": "共享命题"},
        )
        workspace = self._workspace(world)
        self.assertEqual(self._select(workspace).returncode, 0)
        shared_id = evidence_id_for("FACT_SHARED_T0")

        def with_shared(dimension_id: str, overlap_note: str | None) -> dict[str, Any]:
            finding = legal_finding(
                dimension_id, self._candidates(workspace, dimension_id, "TEXT_PROPOSITION")[:1]
            )
            item = {
                "evidence_id": shared_id,
                "role": "PRIMARY_SUPPORT",
                "note": "共享事实。",
            }
            if overlap_note:
                item["overlap_note"] = overlap_note
            finding["supporting_evidence"].append(item)
            return finding

        findings = [
            legal_finding(dimension_id, self._candidates(workspace, dimension_id, "TEXT_PROPOSITION")[:2])
            for dimension_id in DIMENSIONS
        ]
        findings[1] = with_shared("D2_UTILIZATION_EFFECT", None)
        findings[3] = with_shared("D4_CAPEX_CONVERSION", "同一事实在 D2 亦承重，本维度只用其资本开支部分。")
        _, document, validation = self._finalize(workspace, [findings])
        check = self._check(validation, "cross_dimension_attribution")
        self.assertEqual(check["status"], "FAIL")
        self.assertEqual(check["cross_dimension_fact_count"], 1)
        self.assertEqual(check["missing_overlap_note"], ["FACT_SHARED_T0"])
        self.assertEqual(len(document["cross_attribution"]), 1)

    # ------------------------------------------------------------------
    # D7 thresholds, bounded regeneration, frozen rule binding.
    # ------------------------------------------------------------------
    def test_unfounded_d7_threshold_is_kept_as_proposed_not_deleted(self) -> None:
        workspace = self._prepare()
        findings = [
            legal_finding(dimension_id, self._candidates(workspace, dimension_id, "TEXT_PROPOSITION")[:2])
            for dimension_id in DIMENSIONS
        ]
        findings[6]["watch_indicators"] = [
            {
                "indicator": "季度毛利率",
                "judgment_logic": "跌破该水平则下调本发现。",
                "threshold": "18%",
                "threshold_basis": "SOURCE_DISCLOSED_THRESHOLD",
                "basis_evidence_id": None,
            }
        ]
        _, document, validation = self._finalize(workspace, [findings])
        indicator = document["findings"][6]["watch_indicators"][0]
        self.assertEqual(indicator["threshold"], "UNKNOWN")
        self.assertEqual(indicator["threshold_basis"], "REJECTED_NO_BASIS")
        self.assertEqual(indicator["proposed_threshold"], "18%")
        check = self._check(validation, "d7_threshold_basis")
        self.assertEqual(check["status"], "WARN")
        self.assertEqual(validation["analysis_run_status"], "WARN")
        self.assertIn("GAP_ANALYSIS_D7_THRESHOLD_NO_BASIS", validation["new_gap_ids"])

    def test_second_attempt_is_used_when_the_first_fails(self) -> None:
        workspace = self._prepare()
        first = [
            legal_finding(dimension_id, self._candidates(workspace, dimension_id, "TEXT_PROPOSITION")[:2])
            for dimension_id in DIMENSIONS
        ]
        first[0] = legal_finding(
            "D1_PROFITABILITY_CHANGE", [], finding="UNKNOWN", finding_statement="目标价被上调。"
        )
        second = [legal_finding("D1_PROFITABILITY_CHANGE", self._candidates(workspace, "D1_PROFITABILITY_CHANGE", "TEXT_PROPOSITION")[:2])]
        result, document, validation = self._finalize(workspace, [first, second])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(document["findings"][0]["generation_attempts"], 2)
        self.assertEqual(validation["analysis_run_status"], "PASS")

        log = [
            json.loads(line)
            for line in (workspace / "out" / "analysis-attempts.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        d1_attempts = [entry for entry in log if entry["dimension_id"] == "D1_PROFITABILITY_CHANGE"]
        self.assertEqual(len(d1_attempts), 2)
        self.assertFalse(d1_attempts[0]["accepted"])
        self.assertTrue(d1_attempts[0]["errors"])
        self.assertTrue(d1_attempts[1]["accepted"])

    def test_two_failed_attempts_force_unknown_with_a_distinct_reason_code(self) -> None:
        workspace = self._prepare()
        broken = legal_finding(
            "D1_PROFITABILITY_CHANGE", [], finding="UNKNOWN", finding_statement="建议买入。"
        )
        others = [
            legal_finding(dimension_id, self._candidates(workspace, dimension_id, "TEXT_PROPOSITION")[:2])
            for dimension_id in DIMENSIONS[1:]
        ]
        result, document, validation = self._finalize(
            workspace, [[broken, *others], [broken]]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        d1 = document["findings"][0]
        self.assertEqual(d1["finding"], "UNKNOWN")
        self.assertEqual(d1["evidence_score"], 0)
        self.assertEqual(d1["finding_reason_code"], "ANALYSIS_VALIDATION_FAILED")
        self.assertEqual(d1["generation_attempts"], 2)
        self.assertEqual(validation["analysis_run_status"], "FAIL")
        check = self._check(validation, "generation_attempts_bounded")
        self.assertEqual(check["status"], "FAIL")
        self.assertEqual(check["forced_dimensions"], ["D1_PROFITABILITY_CHANGE"])
        self.assertIn(
            "GAP_ANALYSIS_VALIDATION_FAILED_D1_PROFITABILITY_CHANGE", validation["new_gap_ids"]
        )
        # The forced zero must not be readable as "this dimension has no evidence".
        self.assertNotEqual(d1["finding_reason_code"], "NO_BEARING_EVIDENCE")

    def test_loosening_the_bearing_whitelist_fails_the_frozen_rule_binding(self) -> None:
        rules = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
        rules["bearing_metric_whitelist"]["D2_UTILIZATION_EFFECT"] = ["REVENUE"]
        workspace = self._workspace(default_world(), rules)
        self.assertEqual(self._select(workspace).returncode, 0)
        findings = [
            legal_finding(dimension_id, self._candidates(workspace, dimension_id, "TEXT_PROPOSITION")[:2])
            for dimension_id in DIMENSIONS
        ]
        _, _, validation = self._finalize(workspace, [findings])
        check = self._check(validation, "frozen_rule_binding")
        self.assertEqual(check["status"], "FAIL")
        self.assertIn("BEARING_WHITELIST_DRIFT:D2_UTILIZATION_EFFECT", check["issues"])
        self.assertEqual(validation["analysis_run_status"], "FAIL")

    def test_context_rule_version_drift_in_the_frozen_inputs_fails_the_binding(self) -> None:
        # The binding is asserted against the version recorded when the candidate set was
        # frozen, not against the rules file finalize just read.
        workspace = self._prepare()
        inputs = workspace / "inputs" / "analysis-inputs.jsonl"
        rows = self._rows(workspace)
        rows[0]["context_rule_version"] = "smic-v3-context-retrieval-v2"
        inputs.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
        findings = [
            legal_finding(dimension_id, self._one_per_group(workspace, dimension_id))
            for dimension_id in DIMENSIONS
        ]
        _, _, validation = self._finalize(workspace, [findings])
        check = self._check(validation, "frozen_rule_binding")
        self.assertEqual(check["status"], "FAIL")
        self.assertIn("CONTEXT_RULE_VERSION:smic-v3-context-retrieval-v2", check["issues"])
        self.assertEqual(validation["analysis_run_status"], "FAIL")

    def test_select_rejects_context_governed_by_another_retrieval_rule_version(self) -> None:
        world = default_world()
        world.chunks[0]["query_rule_version"] = "smic-v3-context-retrieval-v2"
        workspace = self._workspace(world)
        result = self._select(workspace)
        self.assertEqual(result.returncode, 1)
        self.assertIn("smic-v3-context-retrieval-v3", result.stderr)


@unittest.skipUnless(
    (TICKET03_DIR / "context.jsonl").exists()
    and (TICKET04_DIR / "governed-evidence.jsonl").exists()
    and (SNAPSHOT_DIR / "snapshot-manifest.yaml").exists(),
    "real Snapshot v3 Ticket 03/04 outputs are required for the end-to-end test",
)
class AnalysisEndToEndTests(unittest.TestCase):
    def test_real_v3_selection_is_deterministic_and_matches_the_frozen_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs = []
            for name in ("first", "second"):
                output_dir = Path(temp_dir) / name
                result = run_cli(
                    [
                        "select",
                        "--snapshot-dir", str(SNAPSHOT_DIR),
                        "--context-file", str(TICKET03_DIR / "context.jsonl"),
                        "--facts-file", str(TICKET03_DIR / "normalized-facts.jsonl"),
                        "--evidence-file", str(TICKET04_DIR / "governed-evidence.jsonl"),
                        "--rules-file", str(RULES_FILE),
                        "--existing-gaps-file", str(TICKET04_DIR / "gaps.yaml"),
                        "--output-dir", str(output_dir),
                    ]
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                outputs.append(output_dir)
            self.assertEqual(
                (outputs[0] / "analysis-inputs.jsonl").read_bytes(),
                (outputs[1] / "analysis-inputs.jsonl").read_bytes(),
            )
            summary = json.loads(
                (outputs[0] / "analysis-inputs.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()[0]
            )["dimensions"]
            # The real v3 numeric capacity, unchanged from the Ticket 04 measurement.
            self.assertEqual(
                {key: value["numeric_evidence_count"] for key, value in summary.items()},
                {
                    "D1_PROFITABILITY_CHANGE": 74,
                    "D2_UTILIZATION_EFFECT": 10,
                    "D3_MIX_EFFECT": 60,
                    "D4_CAPEX_CONVERSION": 42,
                    "D5_CYCLE_EXPLANATION": 0,
                    "D6_NONCORE_EXPLANATION": 58,
                    "D7_SUSTAINABILITY_EVIDENCE": 18,
                },
            )
            # D2/D5/D7 carry no bearing numeric at all; D3 carries exactly one.
            self.assertEqual(summary["D2_UTILIZATION_EFFECT"]["bearing_numeric_count"], 0)
            self.assertEqual(summary["D5_CYCLE_EXPLANATION"]["bearing_numeric_count"], 0)
            self.assertEqual(summary["D7_SUSTAINABILITY_EVIDENCE"]["bearing_numeric_count"], 0)
            self.assertEqual(summary["D3_MIX_EFFECT"]["bearing_numeric_count"], 1)
            for dimension_id, stats in summary.items():
                self.assertLessEqual(stats["selected_chars"], 60000 * 1.10, dimension_id)
                self.assertGreaterEqual(stats["source_group_count"], 3, dimension_id)


if __name__ == "__main__":
    unittest.main()
