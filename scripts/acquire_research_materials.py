from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import yaml
import pdfplumber
from openpyxl import load_workbook


MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
MATERIAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
PROHIBITED_SESSION_FIELDS = {
    "account",
    "authorization",
    "cookie",
    "cookies",
    "password",
    "session",
    "session_id",
    "token",
    "username",
}


def sha256_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_timestamp(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO 8601 timestamp: {value}") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone: {value}")
    return parsed


def write_yaml(path: Path, value: Any) -> None:
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def require_fields(item: dict[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if not item.get(field)]
    if missing:
        raise ValueError(f"material is missing required fields: {', '.join(missing)}")


def validate_material_id(material_id: str, seen_material_ids: set[str]) -> None:
    if not MATERIAL_ID_PATTERN.fullmatch(material_id):
        raise ValueError(
            "material_id must contain only letters, digits, underscores, or hyphens "
            "and must not exceed 128 characters"
        )
    if material_id in seen_material_ids:
        raise ValueError(f"duplicate material_id: {material_id}")
    seen_material_ids.add(material_id)


def find_session_fields(value: Any) -> set[str]:
    prohibited: set[str] = set()
    if isinstance(value, dict):
        for key, nested_value in value.items():
            normalized_key = str(key).strip().casefold().replace("-", "_")
            if normalized_key in PROHIBITED_SESSION_FIELDS:
                prohibited.add(str(key))
            prohibited.update(find_session_fields(nested_value))
    elif isinstance(value, list):
        for nested_value in value:
            prohibited.update(find_session_fields(nested_value))
    return prohibited


def reject_session_fields(source: dict[str, Any]) -> None:
    prohibited = sorted(find_session_fields(source), key=str.casefold)
    if prohibited:
        raise ValueError(
            "snapshot intake must not contain credentials or session data: "
            + ", ".join(prohibited)
        )


def material_base_record(
    source: dict[str, Any],
    material_id: str,
    published_at: datetime,
    as_of: datetime,
    created_at: datetime,
    intake_file: Path,
) -> dict[str, Any]:
    local_value = source.get("local_path")
    local_path = (
        (intake_file.parent / str(local_value)).resolve() if local_value else None
    )
    as_of_eligible = published_at <= as_of
    return {
        "material_id": material_id,
        "source_id": source["source_id"],
        "title": source["title"],
        "publisher": source["publisher"],
        "published_at": source["published_at"],
        "publication_precision": source.get("publication_precision", "SECOND"),
        "acquired_at": created_at.isoformat(),
        "locator": source.get("locator"),
        "media_type": source["media_type"],
        "content_hash": (
            sha256_file(local_path)
            if local_path is not None and local_path.is_file()
            else None
        ),
        "source_url": source.get("source_url"),
        "terms_url": source["terms_url"],
        "usage_basis": source["usage_basis"],
        "restriction_status": source["restriction_status"],
        "as_of_eligible": as_of_eligible,
        "as_of_reason": (
            "published_at is not later than case as_of"
            if as_of_eligible
            else "published_at is later than case as_of"
        ),
        "coverage": source.get("coverage", {}),
        "coverage_notes": source.get("coverage_notes", {}),
    }


def suffix_for_material(source: dict[str, Any]) -> str:
    download_url = source.get("download_url")
    if download_url:
        suffix = Path(urllib.parse.urlparse(str(download_url)).path).suffix.lower()
        if suffix:
            return suffix
    media_type = str(source["media_type"])
    return {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "text/html": ".html",
        "text/plain": ".txt",
    }.get(media_type, ".bin")


def download_public_material(download_url: str, destination: Path) -> None:
    parsed_url = urllib.parse.urlparse(download_url)
    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError("download_url must use http or https")
    if parsed_url.username or parsed_url.password:
        raise ValueError("download_url must not contain credentials")
    request = urllib.request.Request(
        download_url,
        headers={"User-Agent": "TradingAgent-mvp-snapshot-builder/1.0"},
    )
    partial_path = destination.with_suffix(destination.suffix + ".partial")
    downloaded = 0
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            final_url = urllib.parse.urlparse(response.geturl())
            if final_url.scheme not in {"http", "https"}:
                raise ValueError("download redirected to a non-http(s) URL")
            with partial_path.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > MAX_DOWNLOAD_BYTES:
                        raise ValueError("download exceeds the 100 MiB snapshot limit")
                    output.write(chunk)
        partial_path.replace(destination)
    finally:
        if partial_path.exists():
            partial_path.unlink()


def extract_text(path: Path, material_id: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {
        "material_id": material_id,
        "parser": "plain-text-v1",
        "lines": [
            {"line_number": number, "text": line}
            for number, line in enumerate(text.splitlines(), start=1)
        ],
    }


def extract_pdf(path: Path, material_id: str) -> dict[str, Any]:
    parsed_pages: list[dict[str, Any]] = []
    extracted_character_count = 0
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            extracted_character_count += len(re.sub(r"\s+", "", text))
            text_lines: list[dict[str, Any]] = []
            for line in page.extract_text_lines(return_chars=False):
                text_lines.append(
                    {
                        "text": line["text"],
                        "bbox": [line["x0"], line["top"], line["x1"], line["bottom"]],
                    }
                )
            tables: list[dict[str, Any]] = []
            for table_number, table in enumerate(page.find_tables(), start=1):
                tables.append(
                    {
                        "table_number": table_number,
                        "bbox": list(table.bbox),
                        "rows": table.extract(),
                    }
                )
            section_candidates = [
                line["text"].strip()
                for line in text_lines
                if line["text"].strip().isupper()
                and 2 <= len(line["text"].strip()) <= 160
            ]
            footnote_candidates = [
                line
                for line in text_lines
                if line["bbox"][1] >= page.height * 0.65
                or re.match(r"^\s*(?:\d+|\*+)\s+", line["text"])
            ]
            parsed_pages.append(
                {
                    "page_number": page_number,
                    "width": page.width,
                    "height": page.height,
                    "text": text,
                    "text_lines": text_lines,
                    "tables": tables,
                    "section_candidates": section_candidates,
                    "footnote_candidates": footnote_candidates,
                }
            )
    reliable_text_layer = bool(parsed_pages) and extracted_character_count >= (
        20 * len(parsed_pages)
    )
    return {
        "material_id": material_id,
        "parser": "pdfplumber-v1",
        "page_count": len(parsed_pages),
        "reliable_text_layer": reliable_text_layer,
        "pages": parsed_pages,
    }


def normalize_html_text(parts: list[str]) -> str:
    return re.sub(r"\s+", " ", "".join(parts)).strip()


class ResearchHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[dict[str, Any]] = []
        self.paragraphs: list[dict[str, Any]] = []
        self.tables: list[dict[str, Any]] = []
        self._block_tag: str | None = None
        self._block_parts: list[str] = []
        self._table_rows: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p"}:
            self._block_tag = tag
            self._block_parts = []
        elif tag == "table":
            self._table_rows = []
        elif tag == "tr" and self._table_rows is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._block_tag is not None:
            self._block_parts.append(data)
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell_parts is not None:
            if self._row is not None:
                self._row.append(normalize_html_text(self._cell_parts))
            self._cell_parts = None
        elif tag == "tr" and self._row is not None:
            if self._table_rows is not None:
                self._table_rows.append(self._row)
            self._row = None
        elif tag == "table" and self._table_rows is not None:
            table_number = len(self.tables) + 1
            self.tables.append(
                {
                    "table_number": table_number,
                    "locator": f"table[{table_number}]",
                    "rows": self._table_rows,
                }
            )
            self._table_rows = None
        elif tag == self._block_tag:
            text = normalize_html_text(self._block_parts)
            if text:
                if tag == "p":
                    index = len(self.paragraphs) + 1
                    self.paragraphs.append(
                        {"locator": f"paragraph:p[{index}]", "text": text}
                    )
                else:
                    level = int(tag[1])
                    index = sum(
                        heading["level"] == level for heading in self.headings
                    ) + 1
                    self.headings.append(
                        {
                            "level": level,
                            "locator": f"heading:{tag}[{index}]",
                            "text": text,
                        }
                    )
            self._block_tag = None
            self._block_parts = []


def extract_html(path: Path, material_id: str) -> dict[str, Any]:
    parser = ResearchHtmlParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return {
        "material_id": material_id,
        "parser": "html-parser-v1",
        "headings": parser.headings,
        "paragraphs": parser.paragraphs,
        "tables": parser.tables,
    }


def normalize_spreadsheet_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def extract_xlsx(path: Path, material_id: str) -> dict[str, Any]:
    workbook = load_workbook(path, read_only=True, data_only=False)
    sheets: list[dict[str, Any]] = []
    try:
        for worksheet in workbook.worksheets:
            rows: list[dict[str, Any]] = []
            for row_number, row in enumerate(worksheet.iter_rows(values_only=True), start=1):
                values = [normalize_spreadsheet_value(value) for value in row]
                if any(value is not None for value in values):
                    rows.append({"row_number": row_number, "values": values})
            sheets.append({"name": worksheet.title, "rows": rows})
    finally:
        workbook.close()
    return {
        "material_id": material_id,
        "parser": "openpyxl-v1",
        "sheets": sheets,
    }


def extract_material(path: Path, material_id: str, media_type: str) -> dict[str, Any]:
    if media_type == "application/pdf" or path.suffix.lower() == ".pdf":
        return extract_pdf(path, material_id)
    if media_type == "text/html" or path.suffix.lower() in {".html", ".htm"}:
        return extract_html(path, material_id)
    if (
        media_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        or path.suffix.lower() == ".xlsx"
    ):
        return extract_xlsx(path, material_id)
    if media_type.startswith("text/") or path.suffix.lower() in {".txt", ".md"}:
        return extract_text(path, material_id)
    raise ValueError(f"unsupported media type: {media_type}")


def canonical_snapshot_id(
    case: dict[str, Any], materials: list[dict[str, Any]], test_fixture: bool
) -> str:
    volatile_material_fields = {"acquired_at", "frozen_path", "parsed_path"}
    identity = {
        "case": {
            field: case.get(field)
            for field in (
                "case_origin",
                "company",
                "security",
                "as_of",
                "timezone",
                "required_coverage",
                "source_use_assumption",
            )
        },
        "materials": [
            {
                key: value
                for key, value in material.items()
                if key not in volatile_material_fields
            }
            for material in sorted(materials, key=lambda item: item["material_id"])
        ],
    }
    digest = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"{'fixture' if test_fixture else 'smic'}-{digest}"


def assess_coverage(
    case: dict[str, Any], material_records: list[dict[str, Any]], snapshot_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    coverage_summary: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    usable_records = [
        record
        for record in material_records
        if record["intake_status"] == "INCLUDED"
        and record["parse_status"] == "PARSED"
    ]
    for category in case.get("required_coverage", []):
        statuses = [
            record.get("coverage", {}).get(category)
            for record in usable_records
            if record.get("coverage", {}).get(category)
        ]
        if "COVERED" in statuses:
            status = "COVERED"
        elif "PARTIAL" in statuses:
            status = "PARTIAL"
        else:
            status = "MISSING"
        material_ids = [
            record["material_id"]
            for record in usable_records
            if record.get("coverage", {}).get(category) in {"COVERED", "PARTIAL"}
        ]
        coverage_summary.append(
            {
                "category": category,
                "status": status,
                "material_ids": material_ids,
            }
        )
        if status != "COVERED":
            gaps.append(
                {
                    "gap_id": f"GAP_ACQUIRE_{str(category).upper()}",
                    "type": "UNKNOWN",
                    "question": f"Required snapshot coverage is {status.lower()}: {category}",
                    "impact_objects": [str(category), snapshot_id],
                    "current_handling": "Do not estimate or infer missing facts.",
                    "confirmation_owner": "user/manual_reviewer",
                    "required_evidence": (
                        "An as_of-eligible, precisely located, permitted source with a reliable "
                        "text or table representation."
                    ),
                    "priority": "P1",
                    "status": "OPEN",
                }
            )
    return coverage_summary, gaps


def snapshot_build(args: argparse.Namespace) -> int:
    case_file = Path(args.case_file).resolve()
    intake_file = Path(args.intake_file).resolve()
    output_dir = Path(args.output_dir).resolve()
    case = yaml.safe_load(case_file.read_text(encoding="utf-8"))
    intake = yaml.safe_load(intake_file.read_text(encoding="utf-8"))
    if not isinstance(case, dict) or not isinstance(intake, dict):
        raise ValueError("case and intake files must contain YAML mappings")
    if not case.get("as_of"):
        raise ValueError("case.yaml is missing as_of")
    as_of = parse_timestamp(str(case["as_of"]), "as_of")
    created_at = parse_timestamp(args.created_at, "created_at")

    if (output_dir / "snapshot-manifest.yaml").exists():
        raise ValueError(
            "snapshot directory is already frozen; use a new output directory for changed materials"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    parsed_dir = output_dir / "parsed"
    raw_dir.mkdir(exist_ok=True)
    parsed_dir.mkdir(exist_ok=True)

    material_records: list[dict[str, Any]] = []
    seen_material_ids: set[str] = set()
    for source in intake.get("materials", []):
        if not isinstance(source, dict):
            raise ValueError("each material entry must be a YAML mapping")
        reject_session_fields(source)
        require_fields(
            source,
            (
                "material_id",
                "source_id",
                "title",
                "publisher",
                "published_at",
                "terms_url",
                "usage_basis",
                "restriction_status",
                "media_type",
            ),
        )
        material_id = str(source["material_id"])
        validate_material_id(material_id, seen_material_ids)
        published_at = parse_timestamp(str(source["published_at"]), "published_at")
        base_record = material_base_record(
            source, material_id, published_at, as_of, created_at, intake_file
        )
        if not source.get("locator") or not source.get("source_url"):
            material_records.append(
                {
                    **base_record,
                    "restriction_status": "EXCLUDED",
                    "intake_status": "REJECTED",
                    "rejection_reason": "SOURCE_OR_LOCATOR_MISSING",
                    "parse_status": "NOT_PARSED",
                }
            )
            continue
        if published_at > as_of:
            material_records.append(
                {
                    **base_record,
                    "intake_status": "EXCLUDED",
                    "exclusion_reason": "AS_OF_EXCEEDED",
                    "parse_status": "NOT_PARSED",
                }
            )
            continue

        restriction_status = str(source["restriction_status"])
        allowed_restrictions = {"USABLE", "RESTRICTED", "EXCLUDED", "UNKNOWN"}
        if restriction_status not in allowed_restrictions:
            raise ValueError(
                f"material {material_id} has invalid restriction_status: {restriction_status}"
            )
        if restriction_status != "USABLE":
            material_records.append(
                {
                    **base_record,
                    "restriction_status": restriction_status,
                    "restriction_reason": source.get(
                        "restriction_reason", "SOURCE_USE_NOT_CONFIRMED"
                    ),
                    "intake_status": (
                        "EXCLUDED" if restriction_status == "EXCLUDED" else "RESTRICTED"
                    ),
                    "parse_status": "NOT_PARSED",
                }
            )
            continue

        has_local_path = bool(source.get("local_path"))
        has_download_url = bool(source.get("download_url"))
        if has_local_path == has_download_url:
            raise ValueError(
                f"eligible material {material_id} must have exactly one of local_path or download_url"
            )
        frozen_path = raw_dir / f"{material_id}{suffix_for_material(source)}"
        if has_local_path:
            local_path = (intake_file.parent / str(source["local_path"])).resolve()
            if not local_path.is_file():
                raise ValueError(f"material file does not exist: {local_path}")
            shutil.copyfile(local_path, frozen_path)
            acquisition_method = "LOCAL_PREPARED"
        else:
            download_public_material(str(source["download_url"]), frozen_path)
            acquisition_method = "DIRECT_PUBLIC_DOWNLOAD"
        parsed_path = parsed_dir / f"{material_id}.json"
        parsed_material = extract_material(
            frozen_path, material_id, str(source["media_type"])
        )
        write_json(parsed_path, parsed_material)
        parse_status = "PARSED"
        if (
            str(source["media_type"]) == "application/pdf"
            and not parsed_material["reliable_text_layer"]
        ):
            parse_status = "UNSUPPORTED_IMAGE_ONLY_PDF"
        record = {
            **base_record,
            "content_hash": sha256_file(frozen_path),
            "intake_status": "INCLUDED",
            "parse_status": parse_status,
            "acquisition_method": acquisition_method,
            "frozen_path": frozen_path.relative_to(output_dir).as_posix(),
            "parsed_path": parsed_path.relative_to(output_dir).as_posix(),
        }
        material_records.append(record)

    materials_path = output_dir / "materials.jsonl"
    materials_path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            for record in material_records
        ),
        encoding="utf-8",
    )
    test_fixture = case.get("case_origin") == "fixture"
    snapshot_id = canonical_snapshot_id(case, material_records, test_fixture)
    coverage_summary, gaps = assess_coverage(case, material_records, snapshot_id)
    gaps_path = output_dir / "gaps.yaml"
    write_yaml(gaps_path, {"snapshot_id": snapshot_id, "gaps": gaps})
    manifest = {
        "snapshot_id": snapshot_id,
        "created_at": created_at.isoformat(),
        "as_of": case["as_of"],
        "build_mode": "SNAPSHOT_BUILD",
        "test_fixture": test_fixture,
        "usage_assumption": "personal, non-commercial, local, not for redistribution or model training",
        "statistics": {
            "total": len(material_records),
            "included": sum(
                record["intake_status"] == "INCLUDED" for record in material_records
            ),
            "excluded": sum(
                record["intake_status"] in {"EXCLUDED", "REJECTED"}
                for record in material_records
            ),
            "rejected": sum(
                record["intake_status"] == "REJECTED" for record in material_records
            ),
            "restricted": sum(
                record["intake_status"] == "RESTRICTED" for record in material_records
            ),
            "unsupported": sum(
                record["parse_status"] == "UNSUPPORTED_IMAGE_ONLY_PDF"
                for record in material_records
            ),
        },
        "coverage": coverage_summary,
        "files": [
            {
                "path": "materials.jsonl",
                "hash": sha256_file(materials_path),
            },
            {
                "path": "gaps.yaml",
                "hash": sha256_file(gaps_path),
            },
            *[
                {"path": record["frozen_path"], "hash": record["content_hash"]}
                for record in material_records
                if "frozen_path" in record
            ],
            *[
                {
                    "path": record["parsed_path"],
                    "hash": sha256_file(output_dir / record["parsed_path"]),
                }
                for record in material_records
                if "parsed_path" in record
            ],
        ],
    }
    write_yaml(output_dir / "snapshot-manifest.yaml", manifest)
    print(snapshot_id)
    return 0


def demo_run(args: argparse.Namespace) -> int:
    case_file = Path(args.case_file).resolve()
    snapshot_dir = Path(args.snapshot_dir).resolve()
    case = yaml.safe_load(case_file.read_text(encoding="utf-8"))
    manifest = yaml.safe_load(
        (snapshot_dir / "snapshot-manifest.yaml").read_text(encoding="utf-8")
    )
    if not isinstance(case, dict) or not isinstance(manifest, dict):
        raise ValueError("case and snapshot manifest must contain YAML mappings")
    if manifest.get("as_of") != case.get("as_of"):
        raise ValueError("snapshot as_of does not match case as_of")
    as_of = parse_timestamp(str(case["as_of"]), "as_of")

    for file_entry in manifest.get("files", []):
        relative_path = Path(str(file_entry["path"]))
        if relative_path.is_absolute():
            raise ValueError(f"snapshot file path must be relative: {relative_path}")
        frozen_file = (snapshot_dir / relative_path).resolve()
        if not frozen_file.is_relative_to(snapshot_dir):
            raise ValueError(f"snapshot file path escapes snapshot directory: {relative_path}")
        if not frozen_file.is_file():
            raise ValueError(f"snapshot file is missing: {relative_path.as_posix()}")
        actual_hash = sha256_file(frozen_file)
        if actual_hash != file_entry["hash"]:
            raise ValueError(f"snapshot file hash mismatch: {relative_path.as_posix()}")

    materials_path = snapshot_dir / "materials.jsonl"
    material_records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        materials_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        material = json.loads(line)
        if not isinstance(material, dict):
            raise ValueError(f"snapshot material is not an object at line {line_number}")
        material_records.append(material)
        if material["intake_status"] != "INCLUDED":
            continue
        published_at = parse_timestamp(material["published_at"], "published_at")
        if published_at > as_of or not material["as_of_eligible"]:
            raise ValueError(f"included material exceeds as_of at line {line_number}")
        if material["restriction_status"] != "USABLE":
            raise ValueError(f"included material is not usable at line {line_number}")

    expected_snapshot_id = canonical_snapshot_id(
        case, material_records, case.get("case_origin") == "fixture"
    )
    if manifest.get("snapshot_id") != expected_snapshot_id:
        raise ValueError("snapshot_id does not match the frozen case and material identity")

    print(manifest["snapshot_id"])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Freeze the single-stock Demo research snapshot")
    subparsers = parser.add_subparsers(dest="mode", required=True)
    build = subparsers.add_parser("SNAPSHOT_BUILD")
    build.add_argument("--case-file", required=True)
    build.add_argument("--intake-file", required=True)
    build.add_argument("--output-dir", required=True)
    build.add_argument("--created-at", required=True)
    demo = subparsers.add_parser("DEMO_RUN")
    demo.add_argument("--case-file", required=True)
    demo.add_argument("--snapshot-dir", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.mode == "SNAPSHOT_BUILD":
            return snapshot_build(args)
        if args.mode == "DEMO_RUN":
            return demo_run(args)
        raise ValueError(f"unsupported mode: {args.mode}")
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
