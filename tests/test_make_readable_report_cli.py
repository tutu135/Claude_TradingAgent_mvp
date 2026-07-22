from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from tests.test_generate_research_report_cli import (
    DIMENSIONS,
    DROPPED_SENTENCE,
    KEPT_SENTENCE,
    build_workspace,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "scripts" / "make_readable_report.py"
OUTPUT = Path("docs") / "briefing" / "04-报告导读.md"


def run(workspace: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=workspace,
    )


class ReadableReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = build_workspace()
        result = run(self.workspace)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.text = (self.workspace / OUTPUT).read_text(encoding="utf-8")

    def test_writes_outside_the_run_directory(self) -> None:
        """A stray .md inside the run directory would halt the next preflight."""
        run_dir = self.workspace / "single-stock-demo-run"
        self.assertFalse((run_dir / OUTPUT.name).exists())
        self.assertEqual([path.name for path in run_dir.glob("*.md")], [])
        self.assertTrue((self.workspace / OUTPUT).is_file())

    def test_every_dimension_gets_a_section_with_its_verdict(self) -> None:
        for dimension_id in DIMENSIONS:
            self.assertIn(dimension_id, self.text)
        self.assertIn("证据方向不一致（MIXED）", self.text)

    def test_evidence_card_links_to_both_the_public_source_and_the_frozen_copy(self) -> None:
        self.assertIn("[公开原文](https://example.invalid/ar2025", self.text)
        self.assertIn("[本地冻结件](../../single-stock-demo-v3/raw/", self.text)
        # The page anchor makes a PDF link land on the right page.
        self.assertIn("#page=12", self.text)

    def test_evidence_card_carries_the_full_basis(self) -> None:
        self.assertIn("IFRS/CONSOLIDATED/AUDITED/SOURCE_REPORTED", self.text)
        self.assertIn("FISCAL_YEAR 2025-01-01~2025-12-31", self.text)
        self.assertIn("EVID_N1", self.text)
        self.assertIn("FACT_N1", self.text)
        self.assertIn("CHUNK_1", self.text)
        self.assertIn("MATERIAL_ANNUAL", self.text)

    def test_omitted_sentences_are_shown_but_marked_as_not_conclusions(self) -> None:
        """The whole point of showing them is to explain the gate, not to restore them."""
        self.assertIn(DROPPED_SENTENCE, self.text)
        self.assertIn("被闸门排除的句子", self.text)
        self.assertIn("它们不是本报告的结论", self.text)
        self.assertIn("其中的数字未经逐个核验", self.text)
        # Struck through, and never presented as part of the narrative section.
        self.assertIn(f"~~{DROPPED_SENTENCE}~~", self.text)
        narrative = self.text[: self.text.index("被闸门排除的句子")]
        self.assertNotIn(DROPPED_SENTENCE, narrative)

    def test_kept_narrative_is_reproduced_verbatim(self) -> None:
        self.assertIn(KEPT_SENTENCE, self.text)

    def test_states_it_is_not_the_authoritative_report(self) -> None:
        self.assertIn("这不是第二份报告", self.text)
        self.assertIn("single-stock-demo-run/report.md", self.text)

    def test_refuses_to_run_without_a_full_report(self) -> None:
        workspace = build_workspace(report_form="DIAGNOSTIC_ONLY")
        result = run(workspace)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FULL_REPORT", result.stderr)
        self.assertFalse((workspace / OUTPUT).exists())


if __name__ == "__main__":
    unittest.main()
