from __future__ import annotations

import json
import functools
import http.server
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import yaml
from PIL import Image
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table
from reportlab.pdfgen import canvas


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "scripts" / "acquire_research_materials.py"


class AcquireResearchMaterialsCliTests(unittest.TestCase):
    def test_snapshot_build_freezes_an_eligible_located_material(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            material_path = workspace / "issuer-report.txt"
            material_path.write_bytes(b"Issuer report\n")
            case_path = workspace / "case.yaml"
            case_path.write_text(
                """
case_origin: fixture
company: Fixture Semiconductor
security: FIXTURE.SH
as_of: '2026-05-15T23:59:59+08:00'
required_coverage:
  - company_security_master
""".lstrip(),
                encoding="utf-8",
            )
            intake_path = workspace / "snapshot-inputs.yaml"
            intake_path.write_text(
                """
materials:
  - material_id: MATERIAL_FIXTURE_001
    source_id: SOURCE_FIXTURE_ISSUER
    title: Fixture issuer report
    publisher: Fixture Semiconductor
    published_at: '2026-05-14T09:00:00+08:00'
    locator:
      source_url: https://example.invalid/issuer-report.txt
      location: issuer-report.txt
    source_url: https://example.invalid/issuer-report.txt
    terms_url: https://example.invalid/terms
    usage_basis: Test fixture for local non-commercial verification.
    restriction_status: USABLE
    media_type: text/plain
    local_path: issuer-report.txt
    coverage:
      company_security_master: COVERED
""".lstrip(),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "SNAPSHOT_BUILD",
                    "--case-file",
                    str(case_path),
                    "--intake-file",
                    str(intake_path),
                    "--output-dir",
                    str(output_dir),
                    "--created-at",
                    "2026-07-19T10:00:00+08:00",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = yaml.safe_load(
                (output_dir / "snapshot-manifest.yaml").read_text(encoding="utf-8")
            )
            material = json.loads(
                (output_dir / "materials.jsonl").read_text(encoding="utf-8")
            )

            self.assertTrue(manifest["snapshot_id"].startswith("fixture-"))
            self.assertTrue(manifest["test_fixture"])
            self.assertEqual(manifest["statistics"]["included"], 1)
            self.assertEqual(material["material_id"], "MATERIAL_FIXTURE_001")
            self.assertEqual(material["intake_status"], "INCLUDED")
            self.assertEqual(
                material["content_hash"],
                "sha256:988d149fdd5d5b83d374015b6845e266dd3bc6ea0c201fbb12a2b31214c93016",
            )

    def test_snapshot_build_excludes_material_published_after_as_of(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "future.txt").write_bytes(b"Future material\n")
            (workspace / "case.yaml").write_text(
                "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage: []\n",
                encoding="utf-8",
            )
            (workspace / "snapshot-inputs.yaml").write_text(
                """
materials:
  - material_id: MATERIAL_FIXTURE_FUTURE
    source_id: SOURCE_FIXTURE_ISSUER
    title: Future fixture
    publisher: Fixture Semiconductor
    published_at: '2026-05-16T00:00:00+08:00'
    locator:
      source_url: https://example.invalid/future.txt
      location: future.txt
    source_url: https://example.invalid/future.txt
    terms_url: https://example.invalid/terms
    usage_basis: Test fixture.
    restriction_status: USABLE
    media_type: text/plain
    local_path: future.txt
""".lstrip(),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "SNAPSHOT_BUILD",
                    "--case-file",
                    str(workspace / "case.yaml"),
                    "--intake-file",
                    str(workspace / "snapshot-inputs.yaml"),
                    "--output-dir",
                    str(output_dir),
                    "--created-at",
                    "2026-07-19T10:00:00+08:00",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            material = json.loads(
                (output_dir / "materials.jsonl").read_text(encoding="utf-8")
            )
            manifest = yaml.safe_load(
                (output_dir / "snapshot-manifest.yaml").read_text(encoding="utf-8")
            )
            self.assertFalse(material["as_of_eligible"])
            self.assertEqual(material["intake_status"], "EXCLUDED")
            self.assertEqual(material["parse_status"], "NOT_PARSED")
            self.assertNotIn("frozen_path", material)
            self.assertEqual(manifest["statistics"]["excluded"], 1)

    def test_snapshot_build_does_not_fetch_or_parse_restricted_material(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "case.yaml").write_text(
                "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage: []\n",
                encoding="utf-8",
            )
            (workspace / "snapshot-inputs.yaml").write_text(
                """
materials:
  - material_id: MATERIAL_FIXTURE_RESTRICTED
    source_id: SOURCE_FIXTURE_RESTRICTED
    title: Restricted fixture
    publisher: Fixture Publisher
    published_at: '2026-05-14T09:00:00+08:00'
    locator:
      source_url: https://example.invalid/restricted.pdf
      location: restricted.pdf
    source_url: https://example.invalid/restricted.pdf
    terms_url: https://example.invalid/restrictive-terms
    usage_basis: Terms prohibit the intended processing.
    restriction_status: RESTRICTED
    restriction_reason: AUTOMATED_PROCESSING_PROHIBITED
    media_type: application/pdf
""".lstrip(),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "SNAPSHOT_BUILD",
                    "--case-file",
                    str(workspace / "case.yaml"),
                    "--intake-file",
                    str(workspace / "snapshot-inputs.yaml"),
                    "--output-dir",
                    str(output_dir),
                    "--created-at",
                    "2026-07-19T10:00:00+08:00",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            material = json.loads(
                (output_dir / "materials.jsonl").read_text(encoding="utf-8")
            )
            manifest = yaml.safe_load(
                (output_dir / "snapshot-manifest.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(material["restriction_status"], "RESTRICTED")
            self.assertEqual(material["intake_status"], "RESTRICTED")
            self.assertEqual(material["parse_status"], "NOT_PARSED")
            self.assertEqual(
                material["restriction_reason"], "AUTOMATED_PROCESSING_PROHIBITED"
            )
            self.assertNotIn("frozen_path", material)
            self.assertEqual(manifest["statistics"]["restricted"], 1)

    def test_snapshot_build_rejects_nested_session_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "issuer.txt").write_bytes(b"Issuer material\n")
            (workspace / "case.yaml").write_text(
                "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage: []\n",
                encoding="utf-8",
            )
            (workspace / "snapshot-inputs.yaml").write_text(
                """
materials:
  - material_id: MATERIAL_FIXTURE_SESSION
    source_id: SOURCE_FIXTURE_ISSUER
    title: Credential-bearing fixture
    publisher: Fixture Publisher
    published_at: '2026-05-14T09:00:00+08:00'
    locator:
      source_url: https://example.invalid/issuer.txt
      location: full text
    source_url: https://example.invalid/issuer.txt
    terms_url: https://example.invalid/terms
    usage_basis: Test fixture.
    restriction_status: USABLE
    media_type: text/plain
    local_path: issuer.txt
    request:
      headers:
        Cookie: session=must-not-be-stored
""".lstrip(),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "SNAPSHOT_BUILD",
                    "--case-file",
                    str(workspace / "case.yaml"),
                    "--intake-file",
                    str(workspace / "snapshot-inputs.yaml"),
                    "--output-dir",
                    str(workspace / "output"),
                    "--created-at",
                    "2026-07-19T10:00:00+08:00",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("credentials or session data", result.stderr)
            self.assertFalse((workspace / "output" / "snapshot-manifest.yaml").exists())

    def test_snapshot_build_rejects_material_id_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "issuer.txt").write_bytes(b"Issuer material\n")
            (workspace / "case.yaml").write_text(
                "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage: []\n",
                encoding="utf-8",
            )
            (workspace / "snapshot-inputs.yaml").write_text(
                """
materials:
  - material_id: ../../outside
    source_id: SOURCE_FIXTURE_ISSUER
    title: Unsafe material id fixture
    publisher: Fixture Publisher
    published_at: '2026-05-14T09:00:00+08:00'
    locator:
      source_url: https://example.invalid/issuer.txt
      location: full text
    source_url: https://example.invalid/issuer.txt
    terms_url: https://example.invalid/terms
    usage_basis: Test fixture.
    restriction_status: USABLE
    media_type: text/plain
    local_path: issuer.txt
""".lstrip(),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "SNAPSHOT_BUILD",
                    "--case-file",
                    str(workspace / "case.yaml"),
                    "--intake-file",
                    str(workspace / "snapshot-inputs.yaml"),
                    "--output-dir",
                    str(workspace / "output"),
                    "--created-at",
                    "2026-07-19T10:00:00+08:00",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("material_id", result.stderr)
            self.assertFalse((workspace / "outside.txt").exists())
            self.assertFalse((workspace / "outside.json").exists())

    def test_snapshot_build_rejects_material_without_an_original_locator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "case.yaml").write_text(
                "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage: []\n",
                encoding="utf-8",
            )
            (workspace / "snapshot-inputs.yaml").write_text(
                """
materials:
  - material_id: MATERIAL_FIXTURE_UNLOCATED
    source_id: SOURCE_FIXTURE_ISSUER
    title: Unlocated fixture
    publisher: Fixture Publisher
    published_at: '2026-05-14T09:00:00+08:00'
    source_url: https://example.invalid/page
    terms_url: https://example.invalid/terms
    usage_basis: Test fixture.
    restriction_status: USABLE
    media_type: text/plain
""".lstrip(),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "SNAPSHOT_BUILD",
                    "--case-file",
                    str(workspace / "case.yaml"),
                    "--intake-file",
                    str(workspace / "snapshot-inputs.yaml"),
                    "--output-dir",
                    str(output_dir),
                    "--created-at",
                    "2026-07-19T10:00:00+08:00",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            material = json.loads(
                (output_dir / "materials.jsonl").read_text(encoding="utf-8")
            )
            manifest = yaml.safe_load(
                (output_dir / "snapshot-manifest.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(material["intake_status"], "REJECTED")
            self.assertEqual(material["rejection_reason"], "SOURCE_OR_LOCATOR_MISSING")
            self.assertEqual(material["parse_status"], "NOT_PARSED")
            self.assertNotEqual(material["restriction_status"], "USABLE")
            self.assertEqual(manifest["statistics"]["rejected"], 1)
            self.assertEqual(manifest["statistics"]["excluded"], 1)

    def test_snapshot_build_preserves_pdf_pages_tables_and_footnote_location(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            pdf_path = workspace / "text-layer.pdf"
            styles = getSampleStyleSheet()
            document = SimpleDocTemplate(str(pdf_path), pagesize=letter)
            document.build(
                [
                    Paragraph("SECTION 1 FINANCIAL RESULTS", styles["Heading1"]),
                    Table(
                        [["Metric", "2025"], ["Revenue", "100"]],
                        colWidths=[2 * inch, inch],
                        style=[
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                        ],
                    ),
                    Spacer(1, 5.8 * inch),
                    Paragraph("1 Amounts in USD millions.", styles["Normal"]),
                    PageBreak(),
                    Paragraph("SECTION 2 OPERATING DATA", styles["Heading1"]),
                    Paragraph("Utilization rate was reported.", styles["BodyText"]),
                ]
            )
            (workspace / "case.yaml").write_text(
                "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage: []\n",
                encoding="utf-8",
            )
            (workspace / "snapshot-inputs.yaml").write_text(
                """
materials:
  - material_id: MATERIAL_FIXTURE_PDF
    source_id: SOURCE_FIXTURE_ISSUER
    title: Text-layer PDF fixture
    publisher: Fixture Publisher
    published_at: '2026-05-14T09:00:00+08:00'
    locator:
      source_url: https://example.invalid/text-layer.pdf
      location: pages 1-2
    source_url: https://example.invalid/text-layer.pdf
    terms_url: https://example.invalid/terms
    usage_basis: Test fixture.
    restriction_status: USABLE
    media_type: application/pdf
    local_path: text-layer.pdf
""".lstrip(),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "SNAPSHOT_BUILD",
                    "--case-file",
                    str(workspace / "case.yaml"),
                    "--intake-file",
                    str(workspace / "snapshot-inputs.yaml"),
                    "--output-dir",
                    str(output_dir),
                    "--created-at",
                    "2026-07-19T10:00:00+08:00",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            parsed = json.loads(
                (output_dir / "parsed" / "MATERIAL_FIXTURE_PDF.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(parsed["page_count"], 2)
            self.assertTrue(parsed["reliable_text_layer"])
            self.assertEqual(parsed["pages"][0]["page_number"], 1)
            self.assertEqual(
                parsed["pages"][0]["tables"][0]["rows"],
                [["Metric", "2025"], ["Revenue", "100"]],
            )
            self.assertIn(
                "1 Amounts in USD millions.",
                [item["text"] for item in parsed["pages"][0]["footnote_candidates"]],
            )
            self.assertIn(
                "SECTION 2 OPERATING DATA", parsed["pages"][1]["section_candidates"]
            )

    def test_snapshot_build_does_not_ocr_an_image_only_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            pdf_path = workspace / "image-only.pdf"
            image = Image.new("RGB", (200, 60), color="white")
            image_pdf = canvas.Canvas(str(pdf_path), pagesize=letter)
            image_pdf.drawInlineImage(image, 72, 650, width=200, height=60)
            image_pdf.save()
            (workspace / "case.yaml").write_text(
                "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage:\n  - capacity\n",
                encoding="utf-8",
            )
            (workspace / "snapshot-inputs.yaml").write_text(
                """
materials:
  - material_id: MATERIAL_FIXTURE_IMAGE_PDF
    source_id: SOURCE_FIXTURE_ISSUER
    title: Image-only PDF fixture
    publisher: Fixture Publisher
    published_at: '2026-05-14T09:00:00+08:00'
    locator:
      source_url: https://example.invalid/image-only.pdf
      location: page 1
    source_url: https://example.invalid/image-only.pdf
    terms_url: https://example.invalid/terms
    usage_basis: Test fixture.
    restriction_status: USABLE
    media_type: application/pdf
    local_path: image-only.pdf
    coverage:
      capacity: COVERED
""".lstrip(),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "SNAPSHOT_BUILD",
                    "--case-file",
                    str(workspace / "case.yaml"),
                    "--intake-file",
                    str(workspace / "snapshot-inputs.yaml"),
                    "--output-dir",
                    str(output_dir),
                    "--created-at",
                    "2026-07-19T10:00:00+08:00",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            material = json.loads(
                (output_dir / "materials.jsonl").read_text(encoding="utf-8")
            )
            parsed = json.loads(
                (output_dir / "parsed" / "MATERIAL_FIXTURE_IMAGE_PDF.json").read_text(
                    encoding="utf-8"
                )
            )
            gaps = yaml.safe_load(
                (output_dir / "gaps.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(material["parse_status"], "UNSUPPORTED_IMAGE_ONLY_PDF")
            self.assertFalse(parsed["reliable_text_layer"])
            self.assertNotIn("ocr", parsed)
            self.assertEqual(gaps["gaps"][0]["gap_id"], "GAP_ACQUIRE_CAPACITY")
            self.assertEqual(gaps["gaps"][0]["type"], "UNKNOWN")

    def test_snapshot_build_preserves_html_headings_paragraphs_and_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "release.html").write_text(
                """
<!doctype html>
<html><body>
<h1>Industry cycle release</h1>
<p>Sales increased in the period.</p>
<table><tr><th>Period</th><th>Sales</th></tr><tr><td>2025</td><td>100</td></tr></table>
</body></html>
""".lstrip(),
                encoding="utf-8",
            )
            (workspace / "case.yaml").write_text(
                "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage: []\n",
                encoding="utf-8",
            )
            (workspace / "snapshot-inputs.yaml").write_text(
                """
materials:
  - material_id: MATERIAL_FIXTURE_HTML
    source_id: SOURCE_FIXTURE_INDUSTRY
    title: HTML fixture
    publisher: Fixture Association
    published_at: '2026-05-14T09:00:00+08:00'
    locator:
      source_url: https://example.invalid/release
      location: full HTML page
    source_url: https://example.invalid/release
    terms_url: https://example.invalid/terms
    usage_basis: Test fixture.
    restriction_status: USABLE
    media_type: text/html
    local_path: release.html
""".lstrip(),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "SNAPSHOT_BUILD",
                    "--case-file",
                    str(workspace / "case.yaml"),
                    "--intake-file",
                    str(workspace / "snapshot-inputs.yaml"),
                    "--output-dir",
                    str(output_dir),
                    "--created-at",
                    "2026-07-19T10:00:00+08:00",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            parsed = json.loads(
                (output_dir / "parsed" / "MATERIAL_FIXTURE_HTML.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                parsed["headings"],
                [{"level": 1, "locator": "heading:h1[1]", "text": "Industry cycle release"}],
            )
            self.assertEqual(
                parsed["paragraphs"][0],
                {
                    "locator": "paragraph:p[1]",
                    "text": "Sales increased in the period.",
                },
            )
            self.assertEqual(
                parsed["tables"][0]["rows"],
                [["Period", "Sales"], ["2025", "100"]],
            )

    def test_snapshot_build_preserves_spreadsheet_sheets_rows_and_formulas(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Income Statement"
            sheet.append(["Metric", "2025", "2024"])
            sheet.append(["Revenue", 100, 80])
            sheet.append(["Growth", "=(B2/C2)-1", None])
            workbook.save(workspace / "financials.xlsx")
            (workspace / "case.yaml").write_text(
                "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage: []\n",
                encoding="utf-8",
            )
            (workspace / "snapshot-inputs.yaml").write_text(
                """
materials:
  - material_id: MATERIAL_FIXTURE_XLSX
    source_id: SOURCE_FIXTURE_ISSUER
    title: Spreadsheet fixture
    publisher: Fixture Publisher
    published_at: '2026-05-14T09:00:00+08:00'
    locator:
      source_url: https://example.invalid/financials.xlsx
      location: workbook
    source_url: https://example.invalid/financials.xlsx
    terms_url: https://example.invalid/terms
    usage_basis: Test fixture.
    restriction_status: USABLE
    media_type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    local_path: financials.xlsx
""".lstrip(),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "SNAPSHOT_BUILD",
                    "--case-file",
                    str(workspace / "case.yaml"),
                    "--intake-file",
                    str(workspace / "snapshot-inputs.yaml"),
                    "--output-dir",
                    str(output_dir),
                    "--created-at",
                    "2026-07-19T10:00:00+08:00",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            parsed = json.loads(
                (output_dir / "parsed" / "MATERIAL_FIXTURE_XLSX.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(parsed["sheets"][0]["name"], "Income Statement")
            self.assertEqual(
                parsed["sheets"][0]["rows"][1],
                {"row_number": 2, "values": ["Revenue", 100, 80]},
            )
            self.assertEqual(
                parsed["sheets"][0]["rows"][2]["values"][1], "=(B2/C2)-1"
            )

    def test_demo_run_uses_only_the_frozen_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            material_path = workspace / "issuer.txt"
            material_path.write_bytes(b"Frozen issuer material\n")
            case_path = workspace / "case.yaml"
            case_path.write_text(
                "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage: []\n",
                encoding="utf-8",
            )
            intake_path = workspace / "snapshot-inputs.yaml"
            intake_path.write_text(
                """
materials:
  - material_id: MATERIAL_FIXTURE_DEMO_RUN
    source_id: SOURCE_FIXTURE_ISSUER
    title: Frozen fixture
    publisher: Fixture Publisher
    published_at: '2026-05-14T09:00:00+08:00'
    locator:
      source_url: https://unreachable.invalid/issuer.txt
      location: full text
    source_url: https://unreachable.invalid/issuer.txt
    terms_url: https://unreachable.invalid/terms
    usage_basis: Test fixture.
    restriction_status: USABLE
    media_type: text/plain
    local_path: issuer.txt
""".lstrip(),
                encoding="utf-8",
            )
            snapshot_dir = workspace / "snapshot"
            build = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "SNAPSHOT_BUILD",
                    "--case-file",
                    str(case_path),
                    "--intake-file",
                    str(intake_path),
                    "--output-dir",
                    str(snapshot_dir),
                    "--created-at",
                    "2026-07-19T10:00:00+08:00",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            expected_snapshot_id = build.stdout.strip()
            material_path.unlink()
            intake_path.unlink()

            demo = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "DEMO_RUN",
                    "--case-file",
                    str(case_path),
                    "--snapshot-dir",
                    str(snapshot_dir),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(demo.returncode, 0, demo.stderr)
            self.assertEqual(demo.stdout.strip(), expected_snapshot_id)

    def test_changed_material_requires_a_new_snapshot_directory_and_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            material_path = workspace / "issuer.txt"
            material_path.write_bytes(b"Version one\n")
            case_path = workspace / "case.yaml"
            case_path.write_text(
                "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage: []\n",
                encoding="utf-8",
            )
            intake_path = workspace / "snapshot-inputs.yaml"
            intake_path.write_text(
                """
materials:
  - material_id: MATERIAL_FIXTURE_VERSIONED
    source_id: SOURCE_FIXTURE_ISSUER
    title: Versioned fixture
    publisher: Fixture Publisher
    published_at: '2026-05-14T09:00:00+08:00'
    locator:
      source_url: https://example.invalid/issuer.txt
      location: full text
    source_url: https://example.invalid/issuer.txt
    terms_url: https://example.invalid/terms
    usage_basis: Test fixture.
    restriction_status: USABLE
    media_type: text/plain
    local_path: issuer.txt
""".lstrip(),
                encoding="utf-8",
            )

            def build(output_dir: Path) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [
                        sys.executable,
                        str(CLI),
                        "SNAPSHOT_BUILD",
                        "--case-file",
                        str(case_path),
                        "--intake-file",
                        str(intake_path),
                        "--output-dir",
                        str(output_dir),
                        "--created-at",
                        "2026-07-19T10:00:00+08:00",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )

            first_dir = workspace / "snapshot-v1"
            first = build(first_dir)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_id = first.stdout.strip()
            material_path.write_bytes(b"Version two\n")

            overwrite = build(first_dir)

            self.assertEqual(overwrite.returncode, 2)
            unchanged_manifest = yaml.safe_load(
                (first_dir / "snapshot-manifest.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(unchanged_manifest["snapshot_id"], first_id)
            second = build(workspace / "snapshot-v2")
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertNotEqual(second.stdout.strip(), first_id)

    def test_changed_source_metadata_changes_identity_and_demo_verifies_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "issuer.txt").write_bytes(b"Stable content\n")
            case_path = workspace / "case.yaml"
            case_path.write_text(
                "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage: []\n",
                encoding="utf-8",
            )
            intake_path = workspace / "snapshot-inputs.yaml"

            def write_intake(usage_basis: str) -> None:
                intake_path.write_text(
                    f"""
materials:
  - material_id: MATERIAL_FIXTURE_METADATA
    source_id: SOURCE_FIXTURE_ISSUER
    title: Metadata identity fixture
    publisher: Fixture Publisher
    published_at: '2026-05-14T09:00:00+08:00'
    locator:
      source_url: https://example.invalid/issuer.txt
      location: full text
    source_url: https://example.invalid/issuer.txt
    terms_url: https://example.invalid/terms
    usage_basis: {usage_basis}
    restriction_status: USABLE
    media_type: text/plain
    local_path: issuer.txt
""".lstrip(),
                    encoding="utf-8",
                )

            def build(output_dir: Path) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [
                        sys.executable,
                        str(CLI),
                        "SNAPSHOT_BUILD",
                        "--case-file",
                        str(case_path),
                        "--intake-file",
                        str(intake_path),
                        "--output-dir",
                        str(output_dir),
                        "--created-at",
                        "2026-07-19T10:00:00+08:00",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )

            write_intake("Initial permitted use.")
            first = build(workspace / "snapshot-v1")
            self.assertEqual(first.returncode, 0, first.stderr)
            write_intake("Updated permitted use.")
            second_dir = workspace / "snapshot-v2"
            second = build(second_dir)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertNotEqual(second.stdout.strip(), first.stdout.strip())

            manifest_path = second_dir / "snapshot-manifest.yaml"
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            manifest["snapshot_id"] = first.stdout.strip()
            manifest_path.write_text(
                yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
            )
            demo = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "DEMO_RUN",
                    "--case-file",
                    str(case_path),
                    "--snapshot-dir",
                    str(second_dir),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(demo.returncode, 2)
            self.assertIn("snapshot_id", demo.stderr)

    def test_snapshot_build_downloads_an_approved_public_material_without_auth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            served_dir = workspace / "served"
            served_dir.mkdir()
            (served_dir / "release.txt").write_bytes(b"Public release\n")

            class SilentHandler(http.server.SimpleHTTPRequestHandler):
                def log_message(self, format: str, *args: object) -> None:
                    del format, args

            handler = functools.partial(SilentHandler, directory=str(served_dir))
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                download_url = f"http://127.0.0.1:{server.server_port}/release.txt"
                (workspace / "case.yaml").write_text(
                    "case_origin: fixture\nas_of: '2026-05-15T23:59:59+08:00'\nrequired_coverage: []\n",
                    encoding="utf-8",
                )
                (workspace / "snapshot-inputs.yaml").write_text(
                    f"""
materials:
  - material_id: MATERIAL_FIXTURE_DOWNLOAD
    source_id: SOURCE_FIXTURE_ISSUER
    title: Public download fixture
    publisher: Fixture Publisher
    published_at: '2026-05-14T09:00:00+08:00'
    locator:
      source_url: {download_url}
      location: full text
    source_url: {download_url}
    download_url: {download_url}
    terms_url: https://example.invalid/terms
    usage_basis: Public download approved for this test fixture.
    restriction_status: USABLE
    media_type: text/plain
""".lstrip(),
                    encoding="utf-8",
                )
                output_dir = workspace / "output"

                result = subprocess.run(
                    [
                        sys.executable,
                        str(CLI),
                        "SNAPSHOT_BUILD",
                        "--case-file",
                        str(workspace / "case.yaml"),
                        "--intake-file",
                        str(workspace / "snapshot-inputs.yaml"),
                        "--output-dir",
                        str(output_dir),
                        "--created-at",
                        "2026-07-19T10:00:00+08:00",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

            self.assertEqual(result.returncode, 0, result.stderr)
            material = json.loads(
                (output_dir / "materials.jsonl").read_text(encoding="utf-8")
            )
            self.assertEqual(material["acquisition_method"], "DIRECT_PUBLIC_DOWNLOAD")
            self.assertEqual(
                (output_dir / material["frozen_path"]).read_bytes(), b"Public release\n"
            )


if __name__ == "__main__":
    unittest.main()
