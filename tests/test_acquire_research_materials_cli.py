from __future__ import annotations

import json
import functools
import hashlib
import http.server
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any

import yaml
from openpyxl import Workbook
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table
from reportlab.pdfgen import canvas


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "scripts" / "acquire_research_materials.py"


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def read_single_jsonl(path: Path) -> dict[str, Any]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 1:
        raise AssertionError(f"expected one JSONL line, got {len(lines)}")
    return json.loads(lines[0])


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def write_case(path: Path, required_targets: list[str] | None = None) -> None:
    write_yaml(
        path,
        {
            "case_origin": "fixture",
            "company": "Fixture Semiconductor",
            "security": "FIXTURE.SH",
            "as_of": "2026-05-15T23:59:59+08:00",
            "timezone": "Asia/Shanghai",
            "required_coverage": required_targets or ["company_security_master"],
            "source_use_assumption": {
                "purpose": "personal_non_commercial_local_demo",
            },
            "rule_versions": {"frozen_spec": "2026-07-19"},
        },
    )


def base_material(material_id: str, local_path: str, targets: list[str] | None = None) -> dict[str, Any]:
    return {
        "material_id": material_id,
        "source_id": f"SOURCE_{material_id}",
        "title": f"Fixture material {material_id}",
        "displayed_publisher": "Fixture Publisher",
        "published_at": "2026-05-14T09:00:00+08:00",
        "publication_precision": "MINUTE",
        "source_class": "NAMED_INSTITUTION",
        "acquisition_source": {
            "type": "url",
            "url": f"https://example.invalid/{material_id}",
        },
        "canonical_material_locator": {
            "source_page": f"https://example.invalid/{material_id}",
            "location": "full material",
        },
        "media_type": "text/plain",
        "local_path": local_path,
        "acquisition_targets": targets or ["company_security_master"],
    }


def build_snapshot(workspace: Path, intake: dict[str, Any]) -> tuple[subprocess.CompletedProcess[str], Path]:
    case_path = workspace / "case.yaml"
    intake_path = workspace / "snapshot-inputs.yaml"
    write_case(case_path)
    write_yaml(intake_path, intake)
    output_dir = workspace / "snapshot"
    result = run_cli(
        [
            "SNAPSHOT_BUILD",
            "--case-file",
            str(case_path),
            "--intake-file",
            str(intake_path),
            "--output-dir",
            str(output_dir),
            "--created-at",
            "2026-07-19T10:00:00+08:00",
        ]
    )
    return result, output_dir


class AcquireResearchMaterialsCliTests(unittest.TestCase):
    def test_snapshot_build_freezes_acquired_unassessed_without_source_use_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "issuer-report.txt").write_bytes(b"Issuer report\n")
            intake = {
                "search_saturation": {"status": "SATURATED"},
                "acquisition_targets": [
                    {
                        "target_id": "company_security_master",
                        "label": "Company and security master",
                        "search_channels": ["issuer", "regulator_exchange", "extended_web"],
                        "search_status": "SATURATED",
                    }
                ],
                "materials": [
                    base_material("MATERIAL_FIXTURE_001", "issuer-report.txt"),
                ],
            }

            result, output_dir = build_snapshot(workspace, intake)

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = yaml.safe_load(
                (output_dir / "snapshot-manifest.yaml").read_text(encoding="utf-8")
            )
            material = read_single_jsonl(output_dir / "materials.jsonl")
            self.assertTrue(result.stdout.strip().startswith("fixture-"))
            self.assertEqual(manifest["statistics"]["unique_materials"], 1)
            self.assertEqual(manifest["acquisition_status"], "ACQUIRED_UNASSESSED")
            self.assertEqual(material["material_id"], "MATERIAL_FIXTURE_001")
            self.assertEqual(material["acquisition_status"], "ACQUIRED_UNASSESSED")
            self.assertEqual(material["parse_status"], "PARSED")
            self.assertEqual(material["acquisition_targets"], ["company_security_master"])
            self.assertNotIn("coverage", manifest)
            self.assertNotIn("intake_status", material)
            self.assertEqual(material["source_use_note"], {})

    def test_snapshot_build_excludes_material_published_after_as_of(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "future.txt").write_bytes(b"Future material\n")
            future = base_material("MATERIAL_FIXTURE_FUTURE", "future.txt")
            future["published_at"] = "2026-05-16T00:00:00+08:00"
            intake = {"materials": [future]}

            result, output_dir = build_snapshot(workspace, intake)

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = yaml.safe_load(
                (output_dir / "snapshot-manifest.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual((output_dir / "materials.jsonl").read_text(encoding="utf-8"), "")
            self.assertEqual(manifest["statistics"]["unique_materials"], 0)
            self.assertEqual(manifest["statistics"]["excluded_after_as_of"], 1)
            self.assertEqual(
                manifest["excluded_materials"][0]["exclusion_reason"], "AS_OF_EXCEEDED"
            )
            self.assertFalse(any((output_dir / "raw").iterdir()))

    def test_snapshot_build_accepts_date_precision_on_as_of_date(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "as-of-date.txt").write_bytes(b"As-of date material\n")
            material = base_material("MATERIAL_FIXTURE_AS_OF_DATE", "as-of-date.txt")
            material["published_at"] = "2026-05-15T00:00:00+08:00"
            material["publication_precision"] = "DATE"

            result, output_dir = build_snapshot(workspace, {"materials": [material]})

            self.assertEqual(result.returncode, 0, result.stderr)
            material_record = read_single_jsonl(output_dir / "materials.jsonl")
            self.assertTrue(material_record["as_of_eligible"])
            self.assertEqual(
                material_record["publication_time"]["latest"],
                "2026-05-15T23:59:59+08:00",
            )

    def test_cross_boundary_or_missing_metadata_goes_to_candidate_holding_area(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "crossing.txt").write_bytes(b"Crossing candidate\n")
            crossing = base_material("MATERIAL_FIXTURE_CROSSING", "crossing.txt")
            crossing["publication_time_window"] = {
                "raw_text": "May 15-16, 2026",
                "precision": "DATE_RANGE",
                "earliest": "2026-05-15T00:00:00+08:00",
                "latest": "2026-05-16T23:59:59+08:00",
                "basis": "fixture page date range",
            }
            missing = base_material("MATERIAL_FIXTURE_MISSING", "crossing.txt")
            del missing["displayed_publisher"]
            intake = {"materials": [crossing, missing]}

            result, output_dir = build_snapshot(workspace, intake)

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = yaml.safe_load(
                (output_dir / "snapshot-manifest.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["statistics"]["candidate_holding"], 2)
            holding_path = output_dir.parent / manifest["candidate_holding_area"]["path"]
            holding = yaml.safe_load(holding_path.read_text(encoding="utf-8"))
            self.assertEqual(holding["snapshot_membership"], "OUTSIDE_ALL_SNAPSHOTS")
            self.assertEqual(len(holding["candidates"]), 2)
            self.assertEqual((output_dir / "materials.jsonl").read_text(encoding="utf-8"), "")
            gaps = yaml.safe_load((output_dir / "gaps.yaml").read_text(encoding="utf-8"))
            self.assertEqual(
                {gap["gap_kind"] for gap in gaps["gaps"]},
                {"CANDIDATE_HOLDING_PENDING_METADATA"},
            )

    def test_declared_candidate_holding_area_records_acquisition_gap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            intake = {
                "candidate_holding_area": [
                    {
                        "candidate_key": "CANDIDATE_TRANSCRIPT",
                        "title": "Transcript candidate",
                        "displayed_publisher": "Fixture Publisher",
                        "acquisition_source": {
                            "type": "url",
                            "url": "https://example.invalid/transcript",
                        },
                        "canonical_material_locator": {
                            "source_page": "https://example.invalid/transcript",
                            "location": "transcript page",
                        },
                        "acquisition_targets": ["quarterly_materials_2026_q1"],
                    }
                ]
            }

            result, output_dir = build_snapshot(workspace, intake)

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = yaml.safe_load(
                (output_dir / "snapshot-manifest.yaml").read_text(encoding="utf-8")
            )
            gaps = yaml.safe_load((output_dir / "gaps.yaml").read_text(encoding="utf-8"))
            holding_path = output_dir.parent / manifest["candidate_holding_area"]["path"]
            holding = yaml.safe_load(holding_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["statistics"]["candidate_holding"], 1)
            self.assertEqual(holding["candidates"][0]["candidate_key"], "CANDIDATE_TRANSCRIPT")
            self.assertEqual(
                gaps["gaps"][0]["gap_kind"],
                "CANDIDATE_HOLDING_PENDING_METADATA",
            )

    def test_snapshot_build_deduplicates_identical_content_and_keeps_better_canonical_locator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "copy-a.txt").write_bytes(b"Same content\n")
            (workspace / "copy-b.txt").write_bytes(b"Same content\n")
            other = base_material("MATERIAL_WEB_COPY", "copy-a.txt", ["industry_cycle"])
            other.update(
                {
                    "source_id": "SOURCE_STABLE_WEB",
                    "displayed_publisher": "Stable Web Archive",
                    "source_class": "STABLE_WEB",
                    "canonical_material_locator": {
                        "source_page": "https://mirror.example.invalid/material",
                        "location": "reposted copy",
                    },
                }
            )
            issuer = base_material("MATERIAL_ISSUER_COPY", "copy-b.txt", ["capital_expenditure"])
            issuer.update(
                {
                    "source_id": "SOURCE_ISSUER",
                    "displayed_publisher": "Fixture Semiconductor",
                    "source_class": "ISSUER",
                    "canonical_material_locator": {
                        "source_page": "https://issuer.example.invalid/material",
                        "location": "issuer original",
                    },
                }
            )
            intake = {"materials": [other, issuer]}

            result, output_dir = build_snapshot(workspace, intake)

            self.assertEqual(result.returncode, 0, result.stderr)
            material = read_single_jsonl(output_dir / "materials.jsonl")
            raw_files = list((output_dir / "raw").iterdir())
            self.assertEqual(len(raw_files), 1)
            self.assertEqual(material["material_id"], "MATERIAL_WEB_COPY")
            self.assertEqual(material["source_id"], "SOURCE_ISSUER")
            self.assertEqual(
                material["canonical_material_locator"]["source_page"],
                "https://issuer.example.invalid/material",
            )
            self.assertEqual(
                material["acquisition_targets"],
                ["capital_expenditure", "industry_cycle"],
            )
            self.assertEqual(len(material["alternate_material_locators"]), 1)

    def test_snapshot_build_preserves_unsupported_material_with_acquisition_gap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "audio.bin").write_bytes(b"not parsed by this demo\n")
            material = base_material("MATERIAL_FIXTURE_AUDIO", "audio.bin", ["industry_cycle"])
            material["media_type"] = "audio/mpeg"
            intake = {"materials": [material]}

            result, output_dir = build_snapshot(workspace, intake)

            self.assertEqual(result.returncode, 0, result.stderr)
            material_record = read_single_jsonl(output_dir / "materials.jsonl")
            gaps = yaml.safe_load((output_dir / "gaps.yaml").read_text(encoding="utf-8"))
            self.assertEqual(material_record["parse_status"], "UNSUPPORTED")
            self.assertNotIn("parsed_path", material_record)
            self.assertEqual(gaps["gaps"][0]["gap_kind"], "MATERIAL_UNPARSEABLE")

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
            material = base_material("MATERIAL_FIXTURE_PDF", "text-layer.pdf")
            material["media_type"] = "application/pdf"
            intake = {"materials": [material]}

            result, output_dir = build_snapshot(workspace, intake)

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
            material = base_material("MATERIAL_FIXTURE_IMAGE_PDF", "image-only.pdf", ["capacity"])
            material["media_type"] = "application/pdf"
            intake = {"materials": [material]}

            result, output_dir = build_snapshot(workspace, intake)

            self.assertEqual(result.returncode, 0, result.stderr)
            material_record = read_single_jsonl(output_dir / "materials.jsonl")
            parsed = json.loads(
                (output_dir / "parsed" / "MATERIAL_FIXTURE_IMAGE_PDF.json").read_text(
                    encoding="utf-8"
                )
            )
            gaps = yaml.safe_load((output_dir / "gaps.yaml").read_text(encoding="utf-8"))
            self.assertEqual(material_record["parse_status"], "UNSUPPORTED")
            self.assertFalse(parsed["reliable_text_layer"])
            self.assertNotIn("ocr", parsed)
            self.assertEqual(gaps["gaps"][0]["gap_kind"], "MATERIAL_UNPARSEABLE")

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
            material = base_material("MATERIAL_FIXTURE_HTML", "release.html")
            material["media_type"] = "text/html"
            intake = {"materials": [material]}

            result, output_dir = build_snapshot(workspace, intake)

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
            material = base_material("MATERIAL_FIXTURE_XLSX", "financials.xlsx")
            material["media_type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            intake = {"materials": [material]}

            result, output_dir = build_snapshot(workspace, intake)

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

    def test_search_saturation_records_targets_without_coverage_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "issuer.txt").write_bytes(b"Issuer material\n")
            material = base_material("MATERIAL_FIXTURE_TARGET", "issuer.txt", ["capacity", "utilization"])
            intake = {
                "search_saturation": {
                    "status": "SATURATED",
                    "target_list_processed": True,
                    "official_round_completed": True,
                    "extended_round_completed": True,
                    "supplemental_round_no_new_unique_material": True,
                },
                "acquisition_targets": [
                    {
                        "target_id": "capacity",
                        "label": "Capacity",
                        "search_channels": ["issuer", "regulator_exchange"],
                        "search_status": "SATURATED",
                    },
                    {
                        "target_id": "utilization",
                        "label": "Utilization",
                        "search_channels": ["issuer", "extended_web"],
                        "search_status": "SATURATED",
                    },
                ],
                "materials": [material],
            }

            result, output_dir = build_snapshot(workspace, intake)

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = yaml.safe_load(
                (output_dir / "snapshot-manifest.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["search_saturation"]["status"], "SATURATED")
            self.assertNotIn("coverage", manifest)
            target_summary = {target["target_id"]: target for target in manifest["acquisition_targets"]}
            self.assertEqual(
                target_summary["capacity"]["material_ids"], ["MATERIAL_FIXTURE_TARGET"]
            )
            self.assertEqual(target_summary["capacity"]["search_status"], "SATURATED")
            self.assertNotIn("status", target_summary["capacity"])

    def test_demo_run_accepts_acquired_unassessed_and_uses_only_the_frozen_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            material_path = workspace / "issuer.txt"
            material_path.write_bytes(b"Frozen issuer material\n")
            case_path = workspace / "case.yaml"
            intake_path = workspace / "snapshot-inputs.yaml"
            write_case(case_path)
            material = base_material("MATERIAL_FIXTURE_DEMO_RUN", "issuer.txt")
            material["acquisition_source"] = {
                "type": "url",
                "url": "https://unreachable.invalid/issuer.txt",
            }
            material["canonical_material_locator"] = {
                "source_page": "https://unreachable.invalid/issuer.txt",
                "location": "full text",
            }
            write_yaml(intake_path, {"materials": [material]})
            snapshot_dir = workspace / "snapshot"
            build = run_cli(
                [
                    "SNAPSHOT_BUILD",
                    "--case-file",
                    str(case_path),
                    "--intake-file",
                    str(intake_path),
                    "--output-dir",
                    str(snapshot_dir),
                    "--created-at",
                    "2026-07-19T10:00:00+08:00",
                ]
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            expected_snapshot_id = build.stdout.strip()
            material_path.unlink()
            intake_path.unlink()

            demo = run_cli(
                [
                    "DEMO_RUN",
                    "--case-file",
                    str(case_path),
                    "--snapshot-dir",
                    str(snapshot_dir),
                ]
            )

            self.assertEqual(demo.returncode, 0, demo.stderr)
            self.assertEqual(demo.stdout.strip(), expected_snapshot_id)

    def test_demo_run_rejects_as_of_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "issuer.txt").write_bytes(b"Issuer material\n")
            result, output_dir = build_snapshot(
                workspace,
                {"materials": [base_material("MATERIAL_FIXTURE_TAMPER", "issuer.txt")]},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            materials_path = output_dir / "materials.jsonl"
            material = read_single_jsonl(materials_path)
            material["publication_time"]["latest"] = "2026-05-16T00:00:00+08:00"
            materials_path.write_text(json.dumps(material, ensure_ascii=False) + "\n", encoding="utf-8")

            demo = run_cli(
                [
                    "DEMO_RUN",
                    "--case-file",
                    str(output_dir / "case.yaml"),
                    "--snapshot-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(demo.returncode, 2)
            self.assertIn("hash mismatch", demo.stderr)

    def test_demo_run_rejects_missing_publication_time_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "issuer.txt").write_bytes(b"Issuer material\n")
            result, output_dir = build_snapshot(
                workspace,
                {"materials": [base_material("MATERIAL_FIXTURE_PUBLICATION_META", "issuer.txt")]},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            materials_path = output_dir / "materials.jsonl"
            material = read_single_jsonl(materials_path)
            del material["publication_time"]["basis"]
            materials_path.write_text(json.dumps(material, ensure_ascii=False) + "\n", encoding="utf-8")
            manifest_path = output_dir / "snapshot-manifest.yaml"
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            for file_entry in manifest["files"]:
                if file_entry["path"] == "materials.jsonl":
                    file_entry["hash"] = "sha256:" + hashlib.sha256(materials_path.read_bytes()).hexdigest()
            manifest_path.write_text(
                yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

            demo = run_cli(
                [
                    "DEMO_RUN",
                    "--case-file",
                    str(output_dir / "case.yaml"),
                    "--snapshot-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(demo.returncode, 2)
            self.assertIn("publication_time", demo.stderr)

    def test_changed_material_requires_a_new_snapshot_directory_and_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            material_path = workspace / "issuer.txt"
            material_path.write_bytes(b"Version one\n")
            case_path = workspace / "case.yaml"
            intake_path = workspace / "snapshot-inputs.yaml"
            write_case(case_path)
            write_yaml(
                intake_path,
                {"materials": [base_material("MATERIAL_FIXTURE_VERSIONED", "issuer.txt")]},
            )

            def build(output_dir: Path) -> subprocess.CompletedProcess[str]:
                return run_cli(
                    [
                        "SNAPSHOT_BUILD",
                        "--case-file",
                        str(case_path),
                        "--intake-file",
                        str(intake_path),
                        "--output-dir",
                        str(output_dir),
                        "--created-at",
                        "2026-07-19T10:00:00+08:00",
                    ]
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
            intake_path = workspace / "snapshot-inputs.yaml"
            write_case(case_path)

            def write_intake(title: str) -> None:
                material = base_material("MATERIAL_FIXTURE_METADATA", "issuer.txt")
                material["title"] = title
                write_yaml(intake_path, {"materials": [material]})

            def build(output_dir: Path) -> subprocess.CompletedProcess[str]:
                return run_cli(
                    [
                        "SNAPSHOT_BUILD",
                        "--case-file",
                        str(case_path),
                        "--intake-file",
                        str(intake_path),
                        "--output-dir",
                        str(output_dir),
                        "--created-at",
                        "2026-07-19T10:00:00+08:00",
                    ]
                )

            write_intake("Initial metadata")
            first = build(workspace / "snapshot-v1")
            self.assertEqual(first.returncode, 0, first.stderr)
            write_intake("Updated metadata")
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
            demo = run_cli(
                [
                    "DEMO_RUN",
                    "--case-file",
                    str(case_path),
                    "--snapshot-dir",
                    str(second_dir),
                ]
            )
            self.assertEqual(demo.returncode, 2)
            self.assertIn("snapshot_id", demo.stderr)

    def test_snapshot_build_rejects_nested_session_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "issuer.txt").write_bytes(b"Issuer material\n")
            material = base_material("MATERIAL_FIXTURE_SESSION", "issuer.txt")
            material["request"] = {"headers": {"Cookie": "session=must-not-be-stored"}}

            result, output_dir = build_snapshot(workspace, {"materials": [material]})

            self.assertEqual(result.returncode, 2)
            self.assertIn("credentials or session data", result.stderr)
            self.assertFalse((output_dir / "snapshot-manifest.yaml").exists())

    def test_snapshot_build_rejects_material_id_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "issuer.txt").write_bytes(b"Issuer material\n")
            material = base_material("../../outside", "issuer.txt")

            result, _output_dir = build_snapshot(workspace, {"materials": [material]})

            self.assertEqual(result.returncode, 2)
            self.assertIn("material_id", result.stderr)
            self.assertFalse((workspace / "outside.txt").exists())
            self.assertFalse((workspace / "outside.json").exists())

    def test_snapshot_build_downloads_public_material_without_auth(self) -> None:
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
                material = base_material("MATERIAL_FIXTURE_DOWNLOAD", "unused.txt")
                del material["local_path"]
                material["download_url"] = download_url
                material["acquisition_source"] = {"type": "url", "url": download_url}
                material["canonical_material_locator"] = {
                    "source_page": download_url,
                    "location": "full text",
                }
                result, output_dir = build_snapshot(workspace, {"materials": [material]})
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

            self.assertEqual(result.returncode, 0, result.stderr)
            material_record = read_single_jsonl(output_dir / "materials.jsonl")
            self.assertEqual(material_record["acquisition_method"], "DIRECT_PUBLIC_DOWNLOAD")
            self.assertEqual(
                (output_dir / material_record["frozen_path"]).read_bytes(), b"Public release\n"
            )


if __name__ == "__main__":
    unittest.main()
