from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

from tests.test_analyze_and_score_research_findings_cli import (
    DIMENSIONS,
    RULES_FILE,
    SNAPSHOT_ID,
    default_world,
    legal_finding,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYZE_CLI = REPO_ROOT / "scripts" / "analyze_and_score_research_findings.py"
CHALLENGE_CLI = REPO_ROOT / "scripts" / "challenge_research_findings.py"


def run(cli: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(cli), *args], capture_output=True, text=True, encoding="utf-8"
    )


class ChallengeLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp())
        world = default_world()
        snapshot_dir = self.workspace / "snapshot"
        snapshot_dir.mkdir()
        (snapshot_dir / "snapshot-manifest.yaml").write_text(
            yaml.safe_dump({"snapshot_id": SNAPSHOT_ID, "files": []}), encoding="utf-8"
        )
        for name, rows in (
            ("context.jsonl", world.chunks),
            ("facts.jsonl", world.facts),
            ("evidence.jsonl", world.evidence),
        ):
            (self.workspace / name).write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                encoding="utf-8",
            )
        (self.workspace / "gaps.yaml").write_text(
            yaml.safe_dump({"snapshot_id": SNAPSHOT_ID, "gaps": []}), encoding="utf-8"
        )
        (self.workspace / "rules.yaml").write_text(
            RULES_FILE.read_text(encoding="utf-8"), encoding="utf-8"
        )
        result = run(
            ANALYZE_CLI,
            [
                "select",
                "--snapshot-dir", str(snapshot_dir),
                "--context-file", str(self.workspace / "context.jsonl"),
                "--facts-file", str(self.workspace / "facts.jsonl"),
                "--evidence-file", str(self.workspace / "evidence.jsonl"),
                "--rules-file", str(self.workspace / "rules.yaml"),
                "--existing-gaps-file", str(self.workspace / "gaps.yaml"),
                "--output-dir", str(self.workspace / "inputs"),
            ],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.inputs = self.workspace / "inputs" / "analysis-inputs.jsonl"
        self.rows = [
            json.loads(line)
            for line in self.inputs.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        findings = [
            legal_finding(dimension_id, self.candidates(dimension_id)[:2])
            for dimension_id in DIMENSIONS
        ]
        findings[1]["finding"] = "SUPPORTED"
        (self.workspace / "model-findings.yaml").write_text(
            yaml.safe_dump(
                {"snapshot_id": SNAPSHOT_ID, "findings": findings},
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        result = run(
            ANALYZE_CLI,
            [
                "finalize",
                "--analysis-inputs", str(self.inputs),
                "--model-findings", str(self.workspace / "model-findings.yaml"),
                "--rules-file", str(self.workspace / "rules.yaml"),
                "--existing-gaps-file", str(self.workspace / "gaps.yaml"),
                "--output-dir", str(self.workspace / "analysis"),
            ],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.findings_file = self.workspace / "analysis" / "findings.yaml"

    def candidates(self, dimension_id: str) -> list[str]:
        return [
            row["evidence_id"]
            for row in self.rows
            if row.get("record_type") == "CANDIDATE_EVIDENCE"
            and row["dimension_id"] == dimension_id
            and row["record_kind"] == "TEXT_PROPOSITION"
        ]

    def _challenge(
        self, challenges: list[dict[str, Any]]
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any], dict[str, Any], dict[str, Any]]:
        path = self.workspace / "model-challenges.yaml"
        path.write_text(
            yaml.safe_dump(
                {"snapshot_id": SNAPSHOT_ID, "challenges": challenges},
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        output_dir = self.workspace / "challenge"
        result = run(
            CHALLENGE_CLI,
            [
                "--findings-file", str(self.findings_file),
                "--analysis-inputs", str(self.inputs),
                "--model-challenges", str(path),
                "--rules-file", str(self.workspace / "rules.yaml"),
                "--existing-gaps-file", str(self.workspace / "gaps.yaml"),
                "--output-dir", str(output_dir),
            ],
        )
        challenges_doc: dict[str, Any] = {}
        revised: dict[str, Any] = {}
        gaps: dict[str, Any] = {}
        if (output_dir / "challenges.yaml").exists():
            challenges_doc = yaml.safe_load((output_dir / "challenges.yaml").read_text(encoding="utf-8"))
            revised = yaml.safe_load((output_dir / "findings-revised.yaml").read_text(encoding="utf-8"))
            gaps = yaml.safe_load((output_dir / "gaps.yaml").read_text(encoding="utf-8"))
        return result, challenges_doc, revised, gaps

    @staticmethod
    def base_challenge(**overrides: Any) -> dict[str, Any]:
        challenge = {
            "challenge_id": "CH_001",
            "round": 1,
            "category": "SOURCE_TRACEABILITY",
            "target_kind": "FINDING",
            "target_id": "D1_PROFITABILITY_CHANGE",
            "question": "该维度的承重证据是否全部可定位且不构成伪多源？",
            "disposition": "RESOLVED_NO_CHANGE",
            "reason": "一次定向复核确认承重证据来自两个独立同源组，定位完整。",
        }
        challenge.update(overrides)
        return challenge

    def revised_finding(self, dimension_id: str) -> dict[str, Any]:
        return legal_finding(dimension_id, self.candidates(dimension_id)[:1])

    # ------------------------------------------------------------------
    def test_four_categories_resolved_without_change_pass(self) -> None:
        categories = [
            "SOURCE_TRACEABILITY",
            "ACCOUNTING_COMPARABILITY",
            "ATTRIBUTION_CAUSALITY",
            "FALSIFICATION_MISSING_EVIDENCE",
        ]
        challenges = [
            self.base_challenge(
                challenge_id=f"CH_00{index}",
                category=category,
                target_id=DIMENSIONS[index],
            )
            for index, category in enumerate(categories)
        ]
        result, document, revised, _ = self._challenge(challenges)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(document["challenge_run_status"], "PASS")
        self.assertEqual(document["rounds_used"], [1])
        self.assertTrue(all(record["review_count"] == 1 for record in document["challenges"]))
        self.assertTrue(all(record["schema_errors"] == [] for record in document["challenges"]))
        self.assertEqual(len(document["revised_findings_validation"]), 12)
        self.assertEqual(revised["overall_score"], "NOT_APPLICABLE")
        self.assertEqual(
            [finding["finding"] for finding in revised["findings"]],
            ["MIXED", "SUPPORTED", "MIXED", "MIXED", "MIXED", "MIXED", "MIXED"],
        )

    def test_evidence_targeted_challenge_is_accepted(self) -> None:
        evidence_id = self.candidates("D3_MIX_EFFECT")[0]
        challenges = [
            self.base_challenge(
                category="ACCOUNTING_COMPARABILITY",
                target_kind="EVIDENCE",
                target_id=evidence_id,
                question="该记录的期间与口径是否与本维度其他证据可比？",
            )
        ]
        _, document, _, _ = self._challenge(challenges)
        self.assertEqual(document["challenge_run_status"], "PASS")
        self.assertEqual(document["challenges"][0]["target_id"], evidence_id)

    def test_revision_records_before_and_after_and_is_revalidated(self) -> None:
        after = self.revised_finding("D1_PROFITABILITY_CHANGE")
        after["finding"] = "UNKNOWN"
        after["limitations"] = ["复核后仅剩单一同源组支撑，方向不再可判定。"]
        challenges = [
            self.base_challenge(
                category="FALSIFICATION_MISSING_EVIDENCE",
                disposition="RESOLVED_WITH_REVISION",
                reason="复核发现一条承重证据与另一条同源，方向下调为 UNKNOWN。",
                revision={"dimension_id": "D1_PROFITABILITY_CHANGE", "finding_after": after},
            )
        ]
        _, document, revised, _ = self._challenge(challenges)
        self.assertEqual(document["challenge_run_status"], "PASS")
        record = document["challenges"][0]
        self.assertEqual(record["disposition"], "RESOLVED_WITH_REVISION")
        self.assertEqual(record["finding_before"]["finding"], "MIXED")
        self.assertEqual(record["finding_after"]["finding"], "UNKNOWN")
        self.assertTrue(record["reason"])
        d1 = revised["findings"][0]
        self.assertEqual(d1["finding"], "UNKNOWN")
        self.assertEqual(d1["revised_from_challenge_ids"], ["CH_001"])
        # The revision is re-scored by the script, never carried over from before.
        self.assertEqual(d1["evidence_score"], 1)
        # The original findings.yaml is untouched.
        original = yaml.safe_load(self.findings_file.read_text(encoding="utf-8"))
        self.assertEqual(original["findings"][0]["finding"], "MIXED")

    def test_a_revision_citing_another_dimension_is_blocked_not_applied(self) -> None:
        after = self.revised_finding("D1_PROFITABILITY_CHANGE")
        after["supporting_evidence"] = [
            {
                "evidence_id": self.candidates("D6_NONCORE_EXPLANATION")[0],
                "role": "PRIMARY_SUPPORT",
                "note": "越界引用。",
                "overlap_note": "越界引用。",
            }
        ]
        challenges = [
            self.base_challenge(
                disposition="RESOLVED_WITH_REVISION",
                reason="试图引入候选集之外的证据。",
                revision={"dimension_id": "D1_PROFITABILITY_CHANGE", "finding_after": after},
            )
        ]
        _, document, revised, gaps = self._challenge(challenges)
        record = document["challenges"][0]
        self.assertEqual(record["disposition"], "BLOCKING")
        self.assertIn("EVIDENCE_OUTSIDE_CANDIDATE_SET", record["blocking_triggers"])
        self.assertTrue(record["revision_errors"])
        self.assertEqual(document["challenge_run_status"], "FAIL")
        self.assertEqual(revised["findings"][0]["finding"], "MIXED")  # not applied
        self.assertIn("GAP_CHALLENGE_BLOCKING_CH_001", [gap["gap_id"] for gap in gaps["gaps"]])

    def test_unresolved_challenge_downgrades_along_the_fixed_ladder_and_writes_a_gap(self) -> None:
        challenges = [
            self.base_challenge(
                challenge_id="CH_D2",
                round=2,
                target_id="D2_UTILIZATION_EFFECT",
                disposition="UNRESOLVED_DOWNGRADED",
                reason="两轮内没有独立证据可以确认方向。",
            ),
            self.base_challenge(
                challenge_id="CH_D3",
                round=2,
                target_id="D3_MIX_EFFECT",
                disposition="UNRESOLVED_DOWNGRADED",
                reason="两轮内没有独立证据可以确认方向。",
            ),
        ]
        _, document, revised, gaps = self._challenge(challenges)
        by_id = {finding["dimension_id"]: finding for finding in revised["findings"]}
        self.assertEqual(by_id["D2_UTILIZATION_EFFECT"]["finding"], "MIXED")  # SUPPORTED -> MIXED
        self.assertEqual(by_id["D3_MIX_EFFECT"]["finding"], "UNKNOWN")  # MIXED -> UNKNOWN
        self.assertEqual(document["challenge_run_status"], "WARN")
        self.assertEqual(document["rounds_used"], [2])
        gap_ids = [gap["gap_id"] for gap in gaps["gaps"]]
        self.assertIn("GAP_CHALLENGE_UNRESOLVED_DOWNGRADED_CH_D2", gap_ids)
        self.assertIn("GAP_CHALLENGE_UNRESOLVED_DOWNGRADED_CH_D3", gap_ids)
        for record in document["challenges"]:
            self.assertIsNotNone(record["finding_before"])
            self.assertIsNotNone(record["finding_after"])

    def test_a_third_round_is_rejected(self) -> None:
        _, document, _, _ = self._challenge([self.base_challenge(round=3)])
        record = document["challenges"][0]
        self.assertTrue(any("CHALLENGE_BAD_ROUND" in error for error in record["schema_errors"]))
        self.assertEqual(record["disposition"], "BLOCKING")
        self.assertIn("CHALLENGE_SCHEMA_INVALID", record["blocking_triggers"])
        self.assertEqual(document["challenge_run_status"], "FAIL")

    def test_a_challenge_without_a_real_target_is_rejected(self) -> None:
        _, document, _, _ = self._challenge(
            [self.base_challenge(target_id="D9_NOT_A_DIMENSION")]
        )
        self.assertTrue(
            any(
                "CHALLENGE_UNKNOWN_TARGET" in error
                for error in document["challenges"][0]["schema_errors"]
            )
        )
        self.assertEqual(document["challenge_run_status"], "FAIL")

    def test_a_generic_bull_bear_challenge_with_investment_language_escalates_to_blocking(self) -> None:
        # Escalation is evaluated at the final round; a round-1 unresolved question may
        # still be settled by a round-2 follow-up.
        challenges = [
            self.base_challenge(
                round=2,
                disposition="UNRESOLVED_DOWNGRADED",
                question="当前股价是否已低估，是否应该买入？",
                reason="泛化的看多看空辩论，无法用冻结快照解决。",
            )
        ]
        _, document, _, _ = self._challenge(challenges)
        record = document["challenges"][0]
        self.assertEqual(record["disposition"], "BLOCKING")
        self.assertIn("FORBIDDEN_INVESTMENT_TERM", record["blocking_triggers"])

    def test_duplicate_challenge_ids_are_rejected(self) -> None:
        _, document, _, _ = self._challenge(
            [self.base_challenge(), self.base_challenge(target_id="D2_UTILIZATION_EFFECT")]
        )
        self.assertTrue(
            any(
                "CHALLENGE_DUPLICATE_ID" in error
                for record in document["challenges"]
                for error in record["schema_errors"]
            )
        )
        self.assertEqual(document["challenge_run_status"], "FAIL")

    def test_a_revision_is_not_allowed_on_a_no_change_disposition(self) -> None:
        _, document, _, _ = self._challenge(
            [
                self.base_challenge(
                    revision={
                        "dimension_id": "D1_PROFITABILITY_CHANGE",
                        "finding_after": self.revised_finding("D1_PROFITABILITY_CHANGE"),
                    }
                )
            ]
        )
        self.assertIn(
            "CHALLENGE_REVISION_NOT_ALLOWED", document["challenges"][0]["schema_errors"]
        )


if __name__ == "__main__":
    unittest.main()
