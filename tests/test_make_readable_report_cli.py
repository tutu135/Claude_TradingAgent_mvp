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
        self.assertIn("**证据方向不一致**（`MIXED`）", self.text)

    def test_evidence_card_links_to_both_the_public_source_and_the_frozen_copy(self) -> None:
        self.assertIn("[▶ 公开原文](https://example.invalid/ar2025", self.text)
        self.assertIn("[▶ 本地冻结件](../../single-stock-demo-v3/raw/", self.text)
        # The page anchor makes a PDF link land on the right page.
        self.assertIn("#page=12", self.text)

    def test_evidence_card_carries_the_full_basis_with_chinese_glosses(self) -> None:
        # Identifiers are annotated, never replaced: they must still grep back to the JSONL.
        self.assertIn("`IFRS`（国际财务报告准则，港股口径）", self.text)
        self.assertIn("`CONSOLIDATED`（合并报表，含子公司）", self.text)
        self.assertIn("`AUDITED`（已审计）", self.text)
        self.assertIn("`GROSS_MARGIN`（毛利率）", self.text)
        self.assertIn("`FISCAL_YEAR`（财政年度）　2025-01-01 至 2025-12-31", self.text)
        self.assertIn("EVID_N1", self.text)
        self.assertIn("FACT_N1", self.text)
        self.assertIn("CHUNK_1", self.text)
        self.assertIn("MATERIAL_ANNUAL", self.text)

    def test_omitted_sentences_are_shown_but_marked_as_not_conclusions(self) -> None:
        """The whole point of showing them is to explain the gate, not to restore them."""
        self.assertIn(DROPPED_SENTENCE, self.text)
        self.assertIn("被闸门删掉的句子", self.text)
        self.assertIn("它们不是本报告的结论", self.text)
        self.assertIn("其中的数字未经逐个核验", self.text)
        # Struck through, and never presented as part of the narrative section.
        self.assertIn(f"~~{DROPPED_SENTENCE}~~", self.text)
        narrative = self.text[: self.text.index("被闸门删掉的句子")]
        self.assertNotIn(DROPPED_SENTENCE, narrative)

    def test_kept_narrative_is_reproduced_verbatim(self) -> None:
        self.assertIn(KEPT_SENTENCE, self.text)

    def test_english_source_span_is_never_translated_only_annotated(self) -> None:
        span = "the improvement was driven by the product mix change"
        self.assertIn(f"> {span}", self.text)
        self.assertIn("生词：", self.text)
        self.assertIn("product mix = 产品结构", self.text)

    def test_the_same_token_is_glossed_per_field_not_globally(self) -> None:
        """`UNKNOWN` means different things per field; a flat table would mislabel one."""
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import make_readable_report  # noqa: PLC0415

        self.assertEqual(
            make_readable_report.gloss("UNKNOWN", "audit_status"),
            "`UNKNOWN`（无法确认审计覆盖范围）",
        )
        self.assertEqual(
            make_readable_report.gloss("UNKNOWN", "finding"),
            "`UNKNOWN`（现有证据无法判断方向）",
        )
        self.assertEqual(
            make_readable_report.gloss("UNKNOWN", "accounting_standard"),
            "`UNKNOWN`（原文没有说明用了哪套准则）",
        )

    def test_a_challenged_direction_is_flagged_against_its_stale_statement(self) -> None:
        """The challenge loop moves `finding` but never rewrites the statement, so a
        downgraded dimension reads as self-contradictory unless the revision is shown."""
        import yaml  # noqa: PLC0415

        workspace = build_workspace()
        run_dir = workspace / "single-stock-demo-run"
        revised = yaml.safe_load((run_dir / "findings-revised.yaml").read_text(encoding="utf-8"))
        revised["findings"][0]["finding"] = "UNKNOWN"
        revised["findings"][0]["revised_from_challenge_ids"] = ["CH_001"]
        (run_dir / "findings-revised.yaml").write_text(
            yaml.safe_dump(revised, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )

        self.assertEqual(run(workspace).returncode, 0)
        text = (workspace / OUTPUT).read_text(encoding="utf-8")
        self.assertIn("这个维度被反方质询改过方向", text)
        self.assertIn("`MIXED`（证据方向不一致）→ `UNKNOWN`（现有证据无法判断方向）", text)
        self.assertIn("`CH_001`", text)
        self.assertIn("以上面方框里的结论为准", text)

    def test_unchallenged_dimensions_carry_no_revision_banner(self) -> None:
        self.assertNotIn("这个维度被反方质询改过方向", self.text)

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
