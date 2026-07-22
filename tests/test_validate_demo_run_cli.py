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
CLI = REPO_ROOT / "scripts" / "validate_demo_run.py"
SNAPSHOT_ID = "smic-a283e95e2c9e8068"
ANALYSIS_RULE_VERSION = "smic-v3-analysis-v1"
SELECTION_HASH = "sha256:" + "a" * 64
AS_OF = "2026-05-15T23:59:59+08:00"


def run(workspace: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
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


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def build_workspace() -> Path:
    """A miniature but structurally complete golden-case workspace.

    The frozen inputs are tiny stand-ins; what is exercised is the judge, not the
    research content. Paths inside the CLI are hard-coded constants, so every test
    runs the CLI with this directory as its working directory.
    """
    workspace = Path(tempfile.mkdtemp())

    for name in ("analysis.yaml", "report.yaml", "context-retrieval.yaml",
                 "accounting.yaml", "source-governance.yaml"):
        target = workspace / "rules" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            (REPO_ROOT / "rules" / name).read_text(encoding="utf-8"), encoding="utf-8"
        )

    snapshot = workspace / "single-stock-demo-v3"
    write_yaml(
        snapshot / "case.yaml",
        {"as_of": AS_OF, "research_question": "问题", "distribution_status": "INTERNAL_DEMO_ONLY"},
    )
    write_yaml(snapshot / "snapshot-manifest.yaml", {"snapshot_id": SNAPSHOT_ID, "files": []})
    write_yaml(snapshot / "gaps.yaml", {"snapshot_id": SNAPSHOT_ID, "gaps": []})
    write_yaml(snapshot / "snapshot-inputs.yaml", {"snapshot_id": SNAPSHOT_ID})
    write_jsonl(
        snapshot / "materials.jsonl",
        [
            {
                "material_id": "MATERIAL_A",
                "as_of_eligible": True,
                "publication_time": {"latest": "2025-03-01T00:00:00+08:00"},
            }
        ],
    )

    frozen = workspace / "frozen-analysis-inputs"
    bound = {"snapshot_id": SNAPSHOT_ID, "selection_hash": SELECTION_HASH,
             "analysis_rule_version": ANALYSIS_RULE_VERSION}
    write_yaml(frozen / "findings-attempt-1.yaml", {**bound, "findings": []})
    write_yaml(frozen / "findings-attempt-2.yaml", {**bound, "findings": []})
    write_yaml(frozen / "challenges-model.yaml", {**bound, "challenges": []})
    write_yaml(
        frozen / "analysis-validation.yaml",
        {
            **bound,
            "analysis_run_status": "PASS",
            "rules_hash": sha256_file(workspace / "rules" / "analysis.yaml"),
        },
    )
    write_jsonl(frozen / "analysis-attempts.jsonl", [{"dimension_id": "D1", "attempt": 1}])
    rewrite_inventory(workspace)

    (workspace / "single-stock-demo-run").mkdir()
    return workspace


def rewrite_inventory(workspace: Path) -> None:
    frozen = workspace / "frozen-analysis-inputs"
    names = [
        "findings-attempt-1.yaml",
        "findings-attempt-2.yaml",
        "challenges-model.yaml",
        "analysis-validation.yaml",
        "analysis-attempts.jsonl",
    ]
    write_yaml(
        frozen / "frozen-inventory.yaml",
        {
            "snapshot_id": SNAPSHOT_ID,
            "analysis_rule_version": ANALYSIS_RULE_VERSION,
            "selection_hash": SELECTION_HASH,
            "files": [{"path": n, "sha256": sha256_file(frozen / n)} for n in names],
        },
    )


def stage_outputs(workspace: Path, **overrides: str) -> None:
    """The five stage run statuses a completed run leaves in the run directory."""
    statuses = {
        "retrieval_status": "PASS",
        "normalization_run_status": "WARN",
        "validation_status": "WARN",
        "analysis_run_status": "PASS",
        "challenge_run_status": "WARN",
    }
    statuses.update(overrides)
    run_dir = workspace / "single-stock-demo-run"
    write_yaml(run_dir / "retrieval-validation.yaml",
               {"snapshot_id": SNAPSHOT_ID, "retrieval_status": statuses["retrieval_status"]})
    write_yaml(run_dir / "normalization-validation.yaml",
               {"snapshot_id": SNAPSHOT_ID,
                "normalization_run_status": statuses["normalization_run_status"]})
    write_yaml(run_dir / "evidence-validation.yaml",
               {"snapshot_id": SNAPSHOT_ID, "validation_status": statuses["validation_status"]})
    write_yaml(run_dir / "analysis-validation.yaml",
               {"snapshot_id": SNAPSHOT_ID, "analysis_run_status": statuses["analysis_run_status"],
                "selection_hash": SELECTION_HASH})
    write_yaml(run_dir / "challenges.yaml",
               {"snapshot_id": SNAPSHOT_ID,
                "challenge_run_status": statuses["challenge_run_status"]})


def load(workspace: Path, name: str) -> dict[str, Any]:
    return yaml.safe_load(
        (workspace / "single-stock-demo-run" / name).read_text(encoding="utf-8")
    )


class PreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = build_workspace()

    def test_clean_workspace_passes(self) -> None:
        result = run(self.workspace, ["preflight"])
        self.assertEqual(result.returncode, 0, result.stderr)
        integrity = load(self.workspace, "run-integrity.yaml")
        self.assertEqual(integrity["integrity_status"], "PASS")
        self.assertEqual(integrity["reason_codes"], [])
        self.assertEqual(integrity["execution_mode"], "FROZEN_REPLAY")
        self.assertTrue(all(check["status"] == "PASS" for check in integrity["checks"]))

    def test_removes_only_the_fixed_inventory_and_never_recurses(self) -> None:
        run_dir = self.workspace / "single-stock-demo-run"
        (run_dir / "report.md").write_text("stale", encoding="utf-8")
        (run_dir / "Thumbs.db").write_text("noise", encoding="utf-8")
        nested = run_dir / "__pycache__"
        nested.mkdir()
        (nested / "x.pyc").write_text("noise", encoding="utf-8")

        result = run(self.workspace, ["preflight"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((run_dir / "report.md").exists())
        self.assertTrue((run_dir / "Thumbs.db").exists())
        self.assertTrue((nested / "x.pyc").exists())

    def test_stranger_authoritative_file_stops_before_cleaning(self) -> None:
        run_dir = self.workspace / "single-stock-demo-run"
        (run_dir / "report.md").write_text("stale", encoding="utf-8")
        (run_dir / "handwritten-notes.yaml").write_text("a: 1", encoding="utf-8")

        result = run(self.workspace, ["preflight"])
        self.assertEqual(result.returncode, 1)
        integrity = load(self.workspace, "run-integrity.yaml")
        self.assertEqual(integrity["integrity_status"], "FAIL")
        self.assertEqual(integrity["unexpected_files"], ["handwritten-notes.yaml"])
        self.assertTrue(integrity["gaps"])
        # Not silently deleted, and the listed files were not cleaned either.
        self.assertTrue((run_dir / "handwritten-notes.yaml").exists())
        self.assertTrue((run_dir / "report.md").exists())

    def test_missing_frozen_input(self) -> None:
        (self.workspace / "frozen-analysis-inputs" / "challenges-model.yaml").unlink()
        result = run(self.workspace, ["preflight"])
        self.assertEqual(result.returncode, 1)
        integrity = load(self.workspace, "run-integrity.yaml")
        self.assertEqual(integrity["reason_codes"], ["FROZEN_ANALYSIS_INPUT_MISSING"])

    def test_tampered_frozen_input(self) -> None:
        path = self.workspace / "frozen-analysis-inputs" / "findings-attempt-1.yaml"
        path.write_text(path.read_text(encoding="utf-8") + "\nextra: 1\n", encoding="utf-8")
        result = run(self.workspace, ["preflight"])
        self.assertEqual(result.returncode, 1)
        integrity = load(self.workspace, "run-integrity.yaml")
        self.assertEqual(integrity["reason_codes"], ["FROZEN_ANALYSIS_HASH_MISMATCH"])

    def test_selection_hash_binding_mismatch(self) -> None:
        path = self.workspace / "frozen-analysis-inputs" / "challenges-model.yaml"
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        document["selection_hash"] = "sha256:" + "b" * 64
        write_yaml(path, document)
        rewrite_inventory(self.workspace)

        result = run(self.workspace, ["preflight"])
        self.assertEqual(result.returncode, 1)
        integrity = load(self.workspace, "run-integrity.yaml")
        self.assertEqual(integrity["reason_codes"], ["FROZEN_ANALYSIS_BINDING_MISMATCH"])

    def test_rules_hash_binding_mismatch(self) -> None:
        rules = self.workspace / "rules" / "analysis.yaml"
        rules.write_text(rules.read_text(encoding="utf-8") + "\n# drifted\n", encoding="utf-8")
        result = run(self.workspace, ["preflight"])
        self.assertEqual(result.returncode, 1)
        integrity = load(self.workspace, "run-integrity.yaml")
        self.assertEqual(integrity["reason_codes"], ["FROZEN_ANALYSIS_BINDING_MISMATCH"])

    def test_snapshot_identity_mismatch_is_a_binding_mismatch(self) -> None:
        write_yaml(
            self.workspace / "single-stock-demo-v3" / "snapshot-manifest.yaml",
            {"snapshot_id": "smic-someothersnapshot", "files": []},
        )
        result = run(self.workspace, ["preflight"])
        self.assertEqual(result.returncode, 1)
        integrity = load(self.workspace, "run-integrity.yaml")
        self.assertEqual(integrity["reason_codes"], ["FROZEN_ANALYSIS_BINDING_MISMATCH"])

    def test_material_published_after_as_of_is_rejected(self) -> None:
        write_jsonl(
            self.workspace / "single-stock-demo-v3" / "materials.jsonl",
            [
                {
                    "material_id": "MATERIAL_A",
                    "as_of_eligible": True,
                    "publication_time": {"latest": "2025-03-01T00:00:00+08:00"},
                },
                {
                    "material_id": "MATERIAL_LATE",
                    "as_of_eligible": True,
                    "publication_time": {"latest": "2026-06-01T00:00:00+08:00"},
                },
            ],
        )
        result = run(self.workspace, ["preflight"])
        self.assertEqual(result.returncode, 1)
        integrity = load(self.workspace, "run-integrity.yaml")
        self.assertEqual(integrity["integrity_status"], "FAIL")
        self.assertEqual(integrity["as_of_violations"], ["MATERIAL_LATE"])


class GateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = build_workspace()
        self.assertEqual(run(self.workspace, ["preflight"]).returncode, 0)

    def test_governance_status_is_the_worst_of_three_and_excludes_analysis(self) -> None:
        stage_outputs(self.workspace)
        result = run(self.workspace, ["gate"])
        self.assertEqual(result.returncode, 0, result.stderr)
        gate = load(self.workspace, "run-gate.yaml")
        self.assertEqual(gate["governance_status"], "WARN")
        self.assertEqual(gate["report_form"], "FULL_REPORT")
        self.assertEqual(gate["stage_statuses"]["analysis_run_status"], "PASS")
        self.assertEqual(gate["stage_statuses"]["challenge_run_status"], "WARN")
        self.assertEqual(gate["governance_status_inputs"],
                         ["retrieval_status", "normalization_run_status", "validation_status"])

    def test_analysis_fail_does_not_reach_governance_status(self) -> None:
        stage_outputs(self.workspace, analysis_run_status="FAIL")
        run(self.workspace, ["gate"])
        gate = load(self.workspace, "run-gate.yaml")
        self.assertEqual(gate["governance_status"], "WARN")
        self.assertEqual(gate["stage_statuses"]["analysis_run_status"], "FAIL")

    def test_governance_fail_still_yields_a_full_report(self) -> None:
        stage_outputs(self.workspace, validation_status="FAIL")
        run(self.workspace, ["gate"])
        gate = load(self.workspace, "run-gate.yaml")
        self.assertEqual(gate["governance_status"], "FAIL")
        self.assertEqual(gate["report_form"], "FULL_REPORT")

    def test_integrity_failure_forces_diagnostic_only(self) -> None:
        stage_outputs(self.workspace)
        integrity = load(self.workspace, "run-integrity.yaml")
        integrity["integrity_status"] = "FAIL"
        integrity["reason_codes"] = ["FROZEN_ANALYSIS_HASH_MISMATCH"]
        write_yaml(self.workspace / "single-stock-demo-run" / "run-integrity.yaml", integrity)
        run(self.workspace, ["gate"])
        gate = load(self.workspace, "run-gate.yaml")
        self.assertEqual(gate["report_form"], "DIAGNOSTIC_ONLY")
        self.assertIn("FROZEN_ANALYSIS_HASH_MISMATCH", gate["reason_codes"])

    def test_replayed_selection_hash_must_match_the_frozen_one(self) -> None:
        stage_outputs(self.workspace)
        write_yaml(
            self.workspace / "single-stock-demo-run" / "analysis-validation.yaml",
            {"snapshot_id": SNAPSHOT_ID, "analysis_run_status": "PASS",
             "selection_hash": "sha256:" + "c" * 64},
        )
        run(self.workspace, ["gate"])
        gate = load(self.workspace, "run-gate.yaml")
        self.assertEqual(gate["report_form"], "DIAGNOSTIC_ONLY")
        self.assertIn("FROZEN_ANALYSIS_BINDING_MISMATCH", gate["reason_codes"])

    def test_missing_stage_status_forces_diagnostic_only(self) -> None:
        stage_outputs(self.workspace)
        (self.workspace / "single-stock-demo-run" / "challenges.yaml").unlink()
        run(self.workspace, ["gate"])
        gate = load(self.workspace, "run-gate.yaml")
        self.assertEqual(gate["report_form"], "DIAGNOSTIC_ONLY")
        self.assertIsNone(gate["stage_statuses"]["challenge_run_status"])


class FinalizeManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = build_workspace()
        self.run_dir = self.workspace / "single-stock-demo-run"
        self.assertEqual(run(self.workspace, ["preflight"]).returncode, 0)
        stage_outputs(self.workspace)
        self.assertEqual(run(self.workspace, ["gate"]).returncode, 0)
        (self.run_dir / "report.md").write_text("# 报告\n", encoding="utf-8")
        write_yaml(self.run_dir / "report-validation.yaml", {"snapshot_id": SNAPSHOT_ID})

    def test_manifest_partitions_inputs_and_outputs(self) -> None:
        result = run(self.workspace, ["finalize-manifest"])
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = load(self.workspace, "manifest.yaml")

        self.assertEqual(manifest["snapshot_id"], SNAPSHOT_ID)
        self.assertEqual(manifest["distribution_status"], "INTERNAL_DEMO_ONLY")
        self.assertEqual(manifest["human_review_status"], "PENDING_HUMAN_REVIEW")
        self.assertEqual(manifest["governance_status"], "WARN")
        self.assertEqual(manifest["report_form"], "FULL_REPORT")
        self.assertEqual(
            manifest["frozen_inputs"]["analysis_inputs"]["execution_mode"], "FROZEN_REPLAY"
        )
        self.assertIn("generated_at", manifest)
        self.assertIn("python", manifest["tool_versions"])
        self.assertEqual(manifest["rule_versions"]["report"], "smic-v3-report-v1")

        inputs = {entry["path"] for entry in
                  manifest["frozen_inputs"]["analysis_inputs"]["files"]}
        outputs = {entry["path"] for entry in manifest["generated_outputs"]["files"]}
        self.assertIn("frozen-analysis-inputs/challenges-model.yaml", inputs)
        self.assertIn("single-stock-demo-run/report.md", outputs)
        self.assertFalse(inputs & outputs)

    def test_manifest_never_records_its_own_hash(self) -> None:
        run(self.workspace, ["finalize-manifest"])
        manifest = load(self.workspace, "manifest.yaml")
        listed = {entry["path"] for group in
                  (manifest["frozen_inputs"]["source_snapshot"]["files"],
                   manifest["frozen_inputs"]["analysis_inputs"]["files"],
                   manifest["generated_outputs"]["files"])
                  for entry in group}
        self.assertNotIn("single-stock-demo-run/manifest.yaml", listed)
        self.assertNotIn("manifest.yaml", listed)

    def test_recorded_hashes_match_the_files_on_disk(self) -> None:
        run(self.workspace, ["finalize-manifest"])
        manifest = load(self.workspace, "manifest.yaml")
        for entry in manifest["generated_outputs"]["files"]:
            self.assertEqual(entry["sha256"], sha256_file(self.workspace / entry["path"]))


class JudgeBoundaryTests(unittest.TestCase):
    """ADR 0005 decision two: the script is a judge, never a step executor."""

    def test_no_stage_script_import_and_no_subprocess(self) -> None:
        source = CLI.read_text(encoding="utf-8")
        for forbidden in ("subprocess", "importlib", "exec(", "eval("):
            self.assertNotIn(forbidden, source)
        for stage in (
            "acquire_research_materials",
            "govern_research_context",
            "normalize_research_facts",
            "govern_validate_research_evidence",
            "analyze_and_score_research_findings",
            "challenge_research_findings",
            "generate_research_report",
        ):
            self.assertNotIn(stage, source)

    def test_only_three_subcommands(self) -> None:
        result = run(self.workspace_root(), ["--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("preflight", result.stdout)
        self.assertIn("gate", result.stdout)
        self.assertIn("finalize-manifest", result.stdout)

    def test_run_directory_is_not_a_parameter(self) -> None:
        result = run(self.workspace_root(), ["preflight", "--run-dir", "/tmp/elsewhere"])
        self.assertNotEqual(result.returncode, 0)

    def workspace_root(self) -> Path:
        return REPO_ROOT


if __name__ == "__main__":
    unittest.main()
