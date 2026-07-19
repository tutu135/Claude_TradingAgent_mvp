from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "scripts" / "govern_research_context.py"


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class GovernResearchContextCliTests(unittest.TestCase):
    def test_rejects_every_snapshot_except_frozen_v3(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-95dcd12eba2fe17c",
                        "files": [],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--rules-file",
                    str(workspace / "rules.yaml"),
                    "--acceptance-file",
                    str(workspace / "acceptance.yaml"),
                    "--output-dir",
                    str(workspace / "output"),
                ]
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("smic-a283e95e2c9e8068 is the only accepted input", result.stderr)

    def test_rejects_tampered_file_declared_by_snapshot_v3_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            snapshot_dir.mkdir()
            (snapshot_dir / "declared.txt").write_text("tampered", encoding="utf-8")
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "files": [
                            {
                                "path": "declared.txt",
                                "hash": "sha256:" + "0" * 64,
                            }
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--rules-file",
                    str(workspace / "rules.yaml"),
                    "--acceptance-file",
                    str(workspace / "acceptance.yaml"),
                    "--output-dir",
                    str(workspace / "output"),
                ]
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("snapshot hash mismatch for declared.txt", result.stderr)

    def test_writes_all_html_section_and_table_structure_atoms_with_locators(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            parsed_dir = snapshot_dir / "parsed"
            parsed_dir.mkdir(parents=True)
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "files": [],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            material = {
                "material_id": "MATERIAL_FIXTURE_HTML",
                "acquisition_status": "ACQUIRED_UNASSESSED",
                "acquisition_targets": ["industry_cycle"],
                "parse_status": "PARSED",
                "parsed_path": "parsed/MATERIAL_FIXTURE_HTML.json",
            }
            (snapshot_dir / "materials.jsonl").write_text(
                json.dumps(material) + "\n",
                encoding="utf-8",
            )
            parsed = {
                "material_id": "MATERIAL_FIXTURE_HTML",
                "parser": "html-parser-v1",
                "headings": [
                    {"level": 1, "locator": "heading:h1[1]", "text": "Industry cycle"}
                ],
                "paragraphs": [
                    {"locator": "paragraph:p[1]", "text": "Sales improved in 2026."},
                    {"locator": "paragraph:p[2]", "text": "Demand remained mixed."},
                ],
                "tables": [
                    {
                        "table_number": 1,
                        "locator": "table[1]",
                        "rows": [["Period", "Sales (USD million)"], ["2026 Q1", "10.5"]],
                    }
                ],
            }
            (parsed_dir / "MATERIAL_FIXTURE_HTML.json").write_text(
                json.dumps(parsed),
                encoding="utf-8",
            )
            rules_file = workspace / "rules.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "rule_version": "context-fixture-v1",
                        "tokenizer": {"version": "fixture-v1"},
                        "query_families": [],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            acceptance_file = workspace / "acceptance.yaml"
            acceptance_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "query_rule_version": "context-fixture-v1",
                        "acceptance_version": "fixture-v1",
                        "labels": [],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--rules-file",
                    str(rules_file),
                    "--acceptance-file",
                    str(acceptance_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            chunks = [
                json.loads(line)
                for line in (output_dir / "context.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual([chunk["structure_type"] for chunk in chunks], ["HTML_SECTION", "HTML_TABLE"])
            self.assertEqual(
                chunks[0]["content_locator"],
                {
                    "section": "Industry cycle",
                    "heading_locator": "heading:h1[1]",
                    "paragraph_locators": ["paragraph:p[1]", "paragraph:p[2]"],
                },
            )
            self.assertEqual(chunks[1]["numeric_context"]["headers"], ["Period", "Sales (USD million)"])
            self.assertEqual(chunks[1]["numeric_context"]["periods"], ["2026 Q1"])
            self.assertTrue(all(chunk["chunk_id"].startswith("CHUNK_") for chunk in chunks))
            self.assertTrue(all(chunk["candidate_context"] is False for chunk in chunks))

    def test_pdf_table_is_separate_from_paragraph_group_and_keeps_numeric_explanation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            parsed_dir = snapshot_dir / "parsed"
            parsed_dir.mkdir(parents=True)
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            material = {
                "material_id": "MATERIAL_FIXTURE_PDF",
                "acquisition_status": "ACQUIRED_UNASSESSED",
                "acquisition_targets": ["quarterly_materials_2026_q1"],
                "parse_status": "PARSED",
                "parsed_path": "parsed/MATERIAL_FIXTURE_PDF.json",
            }
            (snapshot_dir / "materials.jsonl").write_text(
                json.dumps(material) + "\n", encoding="utf-8"
            )
            parsed = {
                "material_id": "MATERIAL_FIXTURE_PDF",
                "parser": "pdfplumber-v1",
                "reliable_text_layer": True,
                "pages": [
                    {
                        "page_number": 4,
                        "text": "Quarterly results\nRevenue table follows.",
                        "section_candidates": ["Quarterly results"],
                        "footnote_candidates": [
                            {"text": "* Amounts are unaudited.", "bbox": [1, 2, 3, 4]}
                        ],
                        "tables": [
                            {
                                "table_number": 1,
                                "bbox": [10, 20, 30, 40],
                                "rows": [
                                    ["USD million", "2026 Q1"],
                                    ["Revenue", "2,505.5"],
                                ],
                            }
                        ],
                    }
                ],
            }
            (parsed_dir / "MATERIAL_FIXTURE_PDF.json").write_text(
                json.dumps(parsed), encoding="utf-8"
            )
            rules_file = workspace / "rules.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "rule_version": "context-fixture-v1",
                        "tokenizer": {"version": "fixture-v1"},
                        "query_families": [],
                    }
                ),
                encoding="utf-8",
            )
            acceptance_file = workspace / "acceptance.yaml"
            acceptance_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "query_rule_version": "context-fixture-v1",
                        "acceptance_version": "fixture-v1",
                        "labels": [],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--rules-file",
                    str(rules_file),
                    "--acceptance-file",
                    str(acceptance_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            chunks = [
                json.loads(line)
                for line in (output_dir / "context.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                [chunk["structure_type"] for chunk in chunks],
                ["PDF_PARAGRAPH_GROUP", "PDF_TABLE"],
            )
            self.assertEqual(chunks[0]["content_locator"]["page_number"], 4)
            self.assertEqual(chunks[0]["content_locator"]["section"], "Quarterly results")
            self.assertEqual(chunks[1]["numeric_context"]["headers"], ["USD million", "2026 Q1"])
            self.assertEqual(chunks[1]["numeric_context"]["periods"], ["2026 Q1"])
            self.assertEqual(chunks[1]["numeric_context"]["footnotes"], ["* Amounts are unaudited."])

    def test_transcript_keeps_ai_summary_separate_and_chunks_each_speaker_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            parsed_dir = snapshot_dir / "parsed"
            parsed_dir.mkdir(parents=True)
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            material_id = "MATERIAL_SMIC_2026_Q1_EARNINGS_CALL_TRANSCRIPT_ALPHASPREAD"
            material = {
                "material_id": material_id,
                "acquisition_status": "ACQUIRED_UNASSESSED",
                "acquisition_targets": ["quarterly_materials_2026_q1"],
                "parse_status": "PARSED",
                "parsed_path": f"parsed/{material_id}.json",
            }
            (snapshot_dir / "materials.jsonl").write_text(
                json.dumps(material) + "\n", encoding="utf-8"
            )
            parsed = {
                "material_id": material_id,
                "parser": "html-parser-v1",
                "headings": [
                    {"level": 3, "locator": "heading:h3[1]", "text": "AI Summary Earnings Call on May 15, 2026"},
                    {"level": 2, "locator": "heading:h2[2]", "text": "Earnings Call Transcript"},
                ],
                "paragraphs": [
                    {"locator": "paragraph:p[1]", "text": "Decide at what price you'd be comfortable buying."},
                    {"locator": "paragraph:p[2]", "text": "Margins: Gross margin improved to 20.1%."},
                    {"locator": "paragraph:p[3]", "text": "[Interpreted] Welcome to SMIC's first quarter webcast conference call."},
                    {"locator": "paragraph:p[4]", "text": "© 2026 Alpha Spread Limited. All Rights Reserved."},
                ],
                "tables": [],
            }
            (parsed_dir / f"{material_id}.json").write_text(
                json.dumps(parsed), encoding="utf-8"
            )
            rules_file = workspace / "rules.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "rule_version": "context-fixture-v1",
                        "tokenizer": {"version": "fixture-v1"},
                        "query_families": [],
                    }
                ),
                encoding="utf-8",
            )
            acceptance_file = workspace / "acceptance.yaml"
            acceptance_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "query_rule_version": "context-fixture-v1",
                        "acceptance_version": "fixture-v1",
                        "labels": [],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--rules-file",
                    str(rules_file),
                    "--acceptance-file",
                    str(acceptance_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            chunks = [
                json.loads(line)
                for line in (output_dir / "context.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(chunks), 4)
            self.assertEqual(
                [chunk["content_locator"]["section"] for chunk in chunks],
                [
                    "PAGE_CHROME",
                    "AI Summary Earnings Call on May 15, 2026",
                    "Earnings Call Transcript",
                    "SITE_FOOTER",
                ],
            )
            self.assertEqual(chunks[1]["structure_type"], "HTML_SECTION_ENTRY")
            self.assertEqual(chunks[2]["structure_type"], "TRANSCRIPT_SPEAKER_TURN")
            self.assertEqual(chunks[2]["speaker_mapping_status"], "UNKNOWN")
            self.assertEqual(chunks[2]["content_locator"]["paragraph_locator"], "paragraph:p[3]")

    def test_bm25_records_query_tokens_and_selects_direct_plus_same_section_adjacent_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            parsed_dir = snapshot_dir / "parsed"
            parsed_dir.mkdir(parents=True)
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            material_id = "MATERIAL_SMIC_2026_Q1_EARNINGS_CALL_TRANSCRIPT_ALPHASPREAD"
            (snapshot_dir / "materials.jsonl").write_text(
                json.dumps(
                    {
                        "material_id": material_id,
                        "acquisition_status": "ACQUIRED_UNASSESSED",
                        "acquisition_targets": ["quarterly_materials_2026_q1"],
                        "parse_status": "PARSED",
                        "parsed_path": f"parsed/{material_id}.json",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (parsed_dir / f"{material_id}.json").write_text(
                json.dumps(
                    {
                        "material_id": material_id,
                        "parser": "html-parser-v1",
                        "headings": [
                            {"level": 3, "locator": "heading:h3[1]", "text": "AI Summary Earnings Call on May 15, 2026"},
                            {"level": 2, "locator": "heading:h2[2]", "text": "Earnings Call Transcript"},
                        ],
                        "paragraphs": [
                            {"locator": "paragraph:p[1]", "text": "Margins: Gross margin improved to 20.1% in Q1 2026."},
                            {"locator": "paragraph:p[2]", "text": "Demand remained mixed across applications."},
                            {"locator": "paragraph:p[3]", "text": "© 2026 Alpha Spread Limited. All Rights Reserved."},
                        ],
                        "tables": [],
                    }
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "rules.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "rule_version": "context-fixture-v2",
                        "tokenizer": {
                            "version": "mixed-tokenizer-fixture-v1",
                            "lexicon_version": "lexicon-fixture-v1",
                            "stopwords_version": "stopwords-fixture-v1",
                            "chinese_lexicon": ["毛利率"],
                            "stopwords": ["the", "in"],
                        },
                        "query_families": [
                            {
                                "family_id": "D1_PROFITABILITY_CHANGE",
                                "responsibility": "RESEARCH",
                                "queries": [
                                    {
                                        "query_id": "D1_EN_MARGIN",
                                        "language": "en",
                                        "text": "gross margin in Q1 2026",
                                        "anchor_tokens": ["gross", "margin"],
                                    }
                                ],
                            }
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            acceptance_file = workspace / "acceptance.yaml"
            acceptance_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "query_rule_version": "context-fixture-v2",
                        "acceptance_version": "fixture-v2",
                        "labels": [],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--rules-file",
                    str(rules_file),
                    "--acceptance-file",
                    str(acceptance_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            chunks = [
                json.loads(line)
                for line in (output_dir / "context.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            direct = next(chunk for chunk in chunks if "DIRECT_HIT" in chunk["selection_reasons"])
            adjacent = next(chunk for chunk in chunks if "ADJACENT_CONTEXT" in chunk["selection_reasons"])
            footer = next(chunk for chunk in chunks if chunk["content_locator"]["section"] == "SITE_FOOTER")
            self.assertEqual(direct["matched_query_ids"], ["D1_EN_MARGIN"])
            self.assertIn("gross", direct["retrieval_keywords"])
            self.assertEqual(direct["retrieval_hits"][0]["rank"], 1)
            self.assertGreater(direct["retrieval_hits"][0]["score"], 0)
            self.assertTrue(adjacent["candidate_context"])
            self.assertEqual(adjacent["matched_query_ids"], ["D1_EN_MARGIN"])
            self.assertIn("margin", adjacent["retrieval_keywords"])
            self.assertFalse(footer["candidate_context"])
            retrieval = yaml.safe_load(
                (output_dir / "retrieval-validation.yaml").read_text(encoding="utf-8")
            )
            query = retrieval["queries"][0]
            self.assertEqual(query["query_id"], "D1_EN_MARGIN")
            self.assertIn("period:2026q1", query["tokens"])
            self.assertEqual(query["hits"][0]["selection_reason"], "DIRECT_HIT")

    def test_retrieval_acceptance_passes_must_should_precision_negative_and_clean_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            snapshot_dir = workspace / "snapshot"
            parsed_dir = snapshot_dir / "parsed"
            parsed_dir.mkdir(parents=True)
            (snapshot_dir / "snapshot-manifest.yaml").write_text(
                yaml.safe_dump({"snapshot_id": "smic-a283e95e2c9e8068", "files": []}),
                encoding="utf-8",
            )
            material_id = "MATERIAL_SMIC_2026_Q1_EARNINGS_CALL_TRANSCRIPT_ALPHASPREAD"
            (snapshot_dir / "materials.jsonl").write_text(
                json.dumps(
                    {
                        "material_id": material_id,
                        "acquisition_status": "ACQUIRED_UNASSESSED",
                        "acquisition_targets": ["quarterly_materials_2026_q1"],
                        "parse_status": "PARSED",
                        "parsed_path": f"parsed/{material_id}.json",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (parsed_dir / f"{material_id}.json").write_text(
                json.dumps(
                    {
                        "material_id": material_id,
                        "parser": "html-parser-v1",
                        "headings": [
                            {"level": 3, "locator": "heading:h3[1]", "text": "AI Summary Earnings Call on May 15, 2026"},
                            {"level": 2, "locator": "heading:h2[2]", "text": "Earnings Call Transcript"},
                        ],
                        "paragraphs": [
                            {"locator": "paragraph:p[1]", "text": "Gross margin improved to 20.1% in Q1 2026."},
                            {"locator": "paragraph:p[2]", "text": "Gross profit also improved in the quarter."},
                            {"locator": "paragraph:p[3]", "text": "© 2026 gross margin site footer. All Rights Reserved."},
                        ],
                        "tables": [],
                    }
                ),
                encoding="utf-8",
            )
            rules_file = workspace / "rules.yaml"
            rules_file.write_text(
                yaml.safe_dump(
                    {
                        "rule_version": "context-acceptance-v1",
                        "tokenizer": {
                            "version": "mixed-tokenizer-fixture-v1",
                            "lexicon_version": "lexicon-fixture-v1",
                            "stopwords_version": "stopwords-fixture-v1",
                            "chinese_lexicon": ["毛利率"],
                            "stopwords": ["the", "in"],
                        },
                        "query_families": [
                            {
                                "family_id": "D1_PROFITABILITY_CHANGE",
                                "responsibility": "RESEARCH",
                                "queries": [
                                    {
                                        "query_id": "D1_EN_MARGIN",
                                        "language": "en",
                                        "text": "gross margin Q1 2026",
                                        "anchor_tokens": ["gross", "margin"],
                                    }
                                ],
                            }
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            acceptance_file = workspace / "acceptance.yaml"
            acceptance_file.write_text(
                yaml.safe_dump(
                    {
                        "snapshot_id": "smic-a283e95e2c9e8068",
                        "query_rule_version": "context-acceptance-v1",
                        "acceptance_version": "fixture-acceptance-v1",
                        "labels": [
                            {
                                "label_id": "LABEL_MUST_MARGIN",
                                "level": "MUST_HIT",
                                "query_family_id": "D1_PROFITABILITY_CHANGE",
                                "material_id": material_id,
                                "locator": {"paragraph_locator": "paragraph:p[1]"},
                                "reason": "Quarter margin result",
                            },
                            {
                                "label_id": "LABEL_SHOULD_PROFIT",
                                "level": "SHOULD_HIT",
                                "query_family_id": "D1_PROFITABILITY_CHANGE",
                                "material_id": material_id,
                                "locator": {"paragraph_locator": "paragraph:p[2]"},
                                "reason": "Related profitability result",
                            },
                            {
                                "label_id": "LABEL_NEGATIVE_FOOTER",
                                "level": "NEGATIVE_CONTROL",
                                "query_family_id": "D1_PROFITABILITY_CHANGE",
                                "material_id": material_id,
                                "locator": {"paragraph_locator": "paragraph:p[3]"},
                                "reason": "Site footer is structural noise",
                            },
                        ],
                        "precision_judgments": [
                            {
                                "query_id": "D1_EN_MARGIN",
                                "material_id": material_id,
                                "locator": {"paragraph_locator": "paragraph:p[1]"},
                                "relevant": True,
                                "reason": "Direct quarter margin result",
                            },
                            {
                                "query_id": "D1_EN_MARGIN",
                                "material_id": material_id,
                                "locator": {"paragraph_locator": "paragraph:p[2]"},
                                "relevant": True,
                                "reason": "Direct profitability result",
                            },
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            output_dir = workspace / "output"

            result = run_cli(
                [
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--rules-file",
                    str(rules_file),
                    "--acceptance-file",
                    str(acceptance_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            retrieval = yaml.safe_load(
                (output_dir / "retrieval-validation.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(retrieval["retrieval_status"], "PASS")
            self.assertEqual(retrieval["metrics"]["must_hit_recall"], 1.0)
            self.assertEqual(retrieval["metrics"]["should_hit_recall_overall"], 1.0)
            self.assertEqual(retrieval["metrics"]["negative_control_candidate_rate"], 0.0)
            self.assertEqual(retrieval["metrics"]["locator_accuracy"], 1.0)
            self.assertEqual(retrieval["metrics"]["precision_by_query"]["D1_EN_MARGIN"], 1.0)
            self.assertTrue(retrieval["metrics"]["clean_rebuild_hashes_match"])
            self.assertEqual(
                retrieval["clean_rebuild"]["first"]["context_hash"],
                retrieval["clean_rebuild"]["second"]["context_hash"],
            )
            chunks = [
                json.loads(line)
                for line in (output_dir / "context.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            negative = next(
                chunk
                for chunk in chunks
                if chunk["content_locator"].get("paragraph_locator") == "paragraph:p[3]"
            )
            self.assertEqual(negative["filter_reason"], "STRUCTURAL_BOILERPLATE")
            self.assertFalse(negative["candidate_context"])


if __name__ == "__main__":
    unittest.main()
