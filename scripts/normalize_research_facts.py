from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml


SNAPSHOT_ID = "smic-a283e95e2c9e8068"
NUMBER_PATTERN = re.compile(
    r"(?P<currency>US\$|\$|USD|RMB|CNY)?\s*"
    r"(?P<open>\()?"
    r"(?P<number>\d[\d,]*(?:\.\d+)?)"
    r"(?P<close>\))?\s*"
    r"(?P<scale>billion|million|thousand|bn|mn)?\s*"
    r"(?P<unit>%|percentage\s+points?|percentage\s+point|pp)?",
    flags=re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize candidate context from the fixed SMIC Snapshot v3"
    )
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--context-file", type=Path, required=True)
    parser.add_argument("--retrieval-file", type=Path, required=True)
    parser.add_argument("--rules-file", type=Path, required=True)
    parser.add_argument("--existing-gaps-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return f"sha256:{digest.hexdigest()}"


def sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def resolve_snapshot_path(snapshot_dir: Path, relative_path: str) -> Path:
    root = snapshot_dir.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"snapshot path escapes input directory: {relative_path}") from error
    return candidate


def verify_snapshot(snapshot_dir: Path) -> None:
    manifest = yaml.safe_load(
        (snapshot_dir / "snapshot-manifest.yaml").read_text(encoding="utf-8")
    )
    if manifest.get("snapshot_id") != SNAPSHOT_ID:
        raise ValueError(f"{SNAPSHOT_ID} is the only accepted input")
    for item in manifest.get("files", []):
        relative_path = str(item["path"])
        path = resolve_snapshot_path(snapshot_dir, relative_path)
        if not path.is_file() or sha256_file(path) != str(item["hash"]):
            raise ValueError(f"snapshot hash mismatch for {relative_path}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def canonical_jsonl_hash(rows: list[dict[str, Any]]) -> str:
    return sha256_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        )
    )


def matching_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[\s\u00a0]+", " ", normalized).strip()
    for source, target in (("：", ":"), ("，", ","), ("（", "("), ("）", ")")):
        normalized = normalized.replace(source, target)
    return normalized


def sentence_spans(text: str) -> list[str]:
    return [
        value.strip()
        for value in re.split(r"(?<=[.!?。！？])\s+|\n+", text)
        if value.strip()
    ]


def quarter_dates(year: int, quarter: int) -> tuple[str, str]:
    starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
    ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    return (
        date(year, *starts[quarter]).isoformat(),
        date(year, *ends[quarter]).isoformat(),
    )


def periods_in_text(text: str) -> list[dict[str, Any]]:
    periods: list[dict[str, Any]] = []
    month_numbers = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    month_words = {"three": 3, "six": 6, "nine": 9}
    for match in re.finditer(
        r"\b(three|six|nine|\d+)\s+months?\s+ended\s+"
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+"
        r"(\d{1,2}),?\s+(20\d{2})\b",
        text,
        flags=re.IGNORECASE,
    ):
        months_text = match.group(1).casefold()
        months = month_words.get(months_text, int(months_text) if months_text.isdigit() else 0)
        month = month_numbers[match.group(2).casefold()]
        day = int(match.group(3))
        year = int(match.group(4))
        end_date = date(year, month, day)
        quarter = month // 3 if month in {3, 6, 9, 12} else None
        periods.append(
            {
                "start_index": match.start(),
                "end_index": match.end(),
                "source_text": match.group(0),
                "period_mapping_status": "MAPPED" if quarter else "AMBIGUOUS",
                "period_nature": "DURATION" if quarter else None,
                "period_type": "YEAR_TO_DATE" if quarter else None,
                "period_start": date(year, 1, 1).isoformat() if quarter else None,
                "period_end": end_date.isoformat() if quarter else None,
                "as_of_date": None,
                "fiscal_quarter": None,
                "ytd_through_quarter": quarter,
                "duration_days": (end_date - date(year, 1, 1)).days + 1 if quarter else None,
                "stated_duration_months": months,
            }
        )
    patterns = (
        (r"\bq([1-4])\s*(20\d{2})\b", lambda match: (int(match.group(2)), int(match.group(1)))),
        (r"\b(20\d{2})\s*q([1-4])\b", lambda match: (int(match.group(1)), int(match.group(2)))),
        (r"\b([1-4])q(\d{2})\b", lambda match: (2000 + int(match.group(2)), int(match.group(1)))),
    )
    for pattern, values in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            year, quarter = values(match)
            start, end = quarter_dates(year, quarter)
            periods.append(
                {
                    "start_index": match.start(),
                    "end_index": match.end(),
                    "source_text": match.group(0),
                    "period_mapping_status": "MAPPED",
                    "period_nature": "DURATION",
                    "period_type": "SINGLE_QUARTER",
                    "period_start": start,
                    "period_end": end,
                    "as_of_date": None,
                    "fiscal_quarter": quarter,
                    "ytd_through_quarter": None,
                    "duration_days": (date.fromisoformat(end) - date.fromisoformat(start)).days + 1,
                }
            )
    unique: dict[tuple[int, int], dict[str, Any]] = {}
    for period in periods:
        unique[(period["start_index"], period["end_index"])] = period
    return sorted(unique.values(), key=lambda item: item["start_index"])


def periods_from_chunk_context(chunk: dict[str, Any]) -> list[dict[str, Any]]:
    periods: list[dict[str, Any]] = []
    for value in (chunk.get("numeric_context") or {}).get("periods", []):
        text = str(value).strip()
        parsed = periods_in_text(text)
        if parsed:
            periods.extend(parsed)
            continue
        if re.fullmatch(r"20\d{2}", text):
            year = int(text)
            periods.append(
                {
                    "start_index": 0,
                    "end_index": len(text),
                    "source_text": text,
                    "period_mapping_status": "MAPPED",
                    "period_nature": "DURATION",
                    "period_type": "FISCAL_YEAR",
                    "period_start": date(year, 1, 1).isoformat(),
                    "period_end": date(year, 12, 31).isoformat(),
                    "as_of_date": None,
                    "fiscal_quarter": None,
                    "ytd_through_quarter": None,
                    "duration_days": (date(year, 12, 31) - date(year, 1, 1)).days + 1,
                }
            )
    return periods


def period_for_position(periods: list[dict[str, Any]], position: int) -> dict[str, Any]:
    if not periods:
        return {
            "source_period_text": None,
            "period_mapping_status": "UNKNOWN",
            "period_nature": None,
            "period_type": None,
            "period_start": None,
            "period_end": None,
            "as_of_date": None,
            "fiscal_quarter": None,
            "ytd_through_quarter": None,
            "duration_days": None,
        }
    nearest = min(
        periods,
        key=lambda item: min(
            abs(position - item["start_index"]), abs(position - item["end_index"])
        ),
    )
    return {
        "source_period_text": nearest["source_text"],
        **{
            key: nearest[key]
            for key in (
                "period_mapping_status",
                "period_nature",
                "period_type",
                "period_start",
                "period_end",
                "as_of_date",
                "fiscal_quarter",
                "ytd_through_quarter",
                "duration_days",
            )
        },
    }


def entity_mapping(material_id: str, rules: dict[str, Any]) -> dict[str, Any]:
    for mapping in rules.get("entity_mappings", []):
        prefix = str(mapping.get("material_prefix") or "")
        if prefix and material_id.startswith(prefix):
            return {
                "source_entity_label": mapping["source_label"],
                "entity_id": mapping["entity_id"],
                "entity_mapping_status": "MAPPED",
                "entity_mapping_rule_id": mapping["rule_id"],
            }
    return {
        "source_entity_label": None,
        "entity_id": None,
        "entity_mapping_status": "UNMAPPED",
        "entity_mapping_rule_id": None,
    }


def metric_mapping(sentence: str, position: int, rules: dict[str, Any]) -> dict[str, Any]:
    normalized = matching_key(sentence)
    candidates: list[tuple[int, int, int, dict[str, Any], str]] = []
    for mapping in rules.get("metric_mappings", []):
        for alias in mapping.get("aliases", []):
            normalized_alias = matching_key(str(alias))
            for match in re.finditer(re.escape(normalized_alias), normalized):
                distance = position - match.start()
                before_penalty = 0 if distance >= 0 else 1
                candidates.append(
                    (before_penalty, abs(distance), match.start(), mapping, str(alias))
                )
    if not candidates:
        return {
            "source_metric_label": None,
            "metric_id": None,
            "metric_mapping_status": "UNMAPPED",
            "metric_mapping_rule_id": None,
        }
    clause_start = max(
        normalized.rfind(separator, 0, position)
        for separator in ("\t", ",", ";", " and ", "，", "；")
    )
    preceding_in_clause = [
        candidate
        for candidate in candidates
        if candidate[0] == 0 and candidate[2] > clause_start
    ]
    if preceding_in_clause:
        _, _, _, mapping, alias = min(
            preceding_in_clause,
            key=lambda item: (item[2], -len(matching_key(item[4])), item[4]),
        )
    else:
        _, _, _, mapping, alias = min(
            candidates, key=lambda item: (item[0], item[1], item[4])
        )
    return {
        "source_metric_label": alias,
        "metric_id": mapping["metric_id"],
        "metric_mapping_status": "MAPPED",
        "metric_mapping_rule_id": mapping["rule_id"],
    }


def bridge_row_metadata(sentence: str, rules: dict[str, Any]) -> dict[str, Any]:
    normalized = matching_key(sentence)
    for row_rule in rules.get("bridge_row_rules", []):
        if matching_key(str(row_rule["match_text"])) in normalized:
            return {
                "bridge_row_role": row_rule["row_role"],
                "bridge_row_rule_id": row_rule["rule_id"],
                "bridge_operation": row_rule.get("bridge_operation"),
                "bridge_accounting_role": row_rule["accounting_role"],
                "equity_attribution": row_rule["equity_attribution"],
            }
    return {
        "bridge_row_role": None,
        "bridge_row_rule_id": None,
        "bridge_operation": None,
        "bridge_accounting_role": None,
        "equity_attribution": None,
    }


def fact_id(payload: dict[str, Any]) -> str:
    identity = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return f"FACT_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"


def field_source(chunk: dict[str, Any], rule_id: str) -> dict[str, Any]:
    return {
        "chunk_id": chunk["chunk_id"],
        "content_locator": chunk["content_locator"],
        "rule_id": rule_id,
    }


def detected_fields(chunk: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    text = matching_key(str(chunk["text"]))
    detected: dict[str, tuple[str, dict[str, Any]]] = {}
    if "international financial reporting standards" in text or re.search(r"\bifrs\b", text):
        detected["accounting_standard"] = (
            "IFRS",
            field_source(chunk, "FIELD_ACCOUNTING_IFRS_EXPLICIT_V1"),
        )
    if "企业会计准则" in text or "prc accounting standards" in text or re.search(r"\bcas\b", text):
        detected["accounting_standard"] = (
            "CAS",
            field_source(chunk, "FIELD_ACCOUNTING_CAS_EXPLICIT_V1"),
        )
    if "consolidated" in text or "合并" in text:
        detected["consolidation_scope"] = (
            "CONSOLIDATED",
            field_source(chunk, "FIELD_SCOPE_CONSOLIDATED_EXPLICIT_V1"),
        )
    if "unaudited" in text or "未经审计" in text:
        detected["audit_status"] = (
            "UNAUDITED",
            field_source(chunk, "FIELD_AUDIT_UNAUDITED_EXPLICIT_V1"),
        )
    elif "reviewed" in text or "审阅" in text:
        detected["audit_status"] = (
            "REVIEWED",
            field_source(chunk, "FIELD_AUDIT_REVIEWED_EXPLICIT_V1"),
        )
    elif "independent auditor" in text or "audited financial statements" in text:
        detected["audit_status"] = (
            "AUDITED",
            field_source(chunk, "FIELD_AUDIT_AUDITED_STATEMENTS_ONLY_V1"),
        )
    if "us dollars" in text or "u.s. dollars" in text or re.search(r"\busd\b", text):
        detected["currency"] = (
            "USD",
            field_source(chunk, "FIELD_CURRENCY_USD_EXPLICIT_V1"),
        )
    elif "人民币" in text or re.search(r"\b(?:cny|rmb)\b", text):
        detected["currency"] = (
            "CNY",
            field_source(chunk, "FIELD_CURRENCY_CNY_EXPLICIT_V1"),
        )
    return detected


def resolve_material_fields(
    target: dict[str, Any],
    material_chunks: list[dict[str, Any]],
    detections: dict[str, dict[str, tuple[str, dict[str, Any]]]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in ("accounting_standard", "consolidation_scope", "audit_status", "currency"):
        candidates: list[tuple[int, str, dict[str, Any]]] = []
        target_section = target["content_locator"].get("section")
        for chunk in material_chunks:
            detection = detections[chunk["chunk_id"]].get(field)
            if not detection:
                continue
            value, source = detection
            if chunk["chunk_id"] == target["chunk_id"]:
                priority = 0
                source_level = "LOCAL"
            elif target_section and chunk["content_locator"].get("section") == target_section:
                priority = 1
                source_level = "SECTION"
            else:
                priority = 2
                source_level = "DOCUMENT"
            candidates.append((priority, value, {**source, "source_level": source_level}))
        if not candidates:
            result[field] = "UNKNOWN"
            result[f"{field}_source"] = None
            continue
        best_priority = min(candidate[0] for candidate in candidates)
        best = [candidate for candidate in candidates if candidate[0] == best_priority]
        values = {candidate[1] for candidate in best}
        if len(values) != 1:
            result[field] = "AMBIGUOUS"
            result[f"{field}_source"] = None
            continue
        value = best[0][1]
        source = best[0][2]
        if field == "audit_status" and value == "AUDITED":
            section = matching_key(str(target_section or ""))
            if not any(
                phrase in section
                for phrase in ("financial statements", "notes to", "auditor", "财务报表", "附注")
            ):
                result[field] = "UNKNOWN"
                result[f"{field}_source"] = None
                continue
        result[field] = value
        result[f"{field}_source"] = source
    return result


def gap_for_fact(fact_id_value: str, missing_fields: list[str]) -> dict[str, Any]:
    gap_identity = f"{fact_id_value}|{'|'.join(sorted(missing_fields))}"
    gap_id = f"GAP_NORMALIZE_{hashlib.sha256(gap_identity.encode('utf-8')).hexdigest()[:16]}"
    return {
        "gap_id": gap_id,
        "origin_stage": "normalize-research-facts",
        "gap_kind": "NORMALIZATION_UNKNOWN",
        "question": "Required normalization attributes are unknown: "
        + ", ".join(sorted(missing_fields)),
        "impact_objects": [fact_id_value],
        "current_handling": "Preserve the source atom without guessing the missing attributes.",
        "confirmation_owner": "user/data_preparer",
        "required_evidence": "A traceable locator or approved fixed mapping for the missing attributes.",
        "priority": "P1",
        "status": "OPEN",
    }


def common_record(
    chunk: dict[str, Any],
    sentence: str,
    source_span_index: int,
    record_kind: str,
    material_fields: dict[str, Any],
) -> dict[str, Any]:
    return {
        "snapshot_id": SNAPSHOT_ID,
        "record_kind": record_kind,
        "chunk_id": chunk["chunk_id"],
        "material_id": chunk["material_id"],
        "content_locator": chunk["content_locator"],
        "source_span_text": sentence,
        "source_span_index": source_span_index,
        "source_chunk_text_hash": chunk.get("text_hash"),
        "claim_type": "UNASSESSED",
        "accounting_standard": material_fields["accounting_standard"],
        "accounting_standard_source": material_fields["accounting_standard_source"],
        "consolidation_scope": material_fields["consolidation_scope"],
        "consolidation_scope_source": material_fields["consolidation_scope_source"],
        "audit_status": material_fields["audit_status"],
        "audit_status_source": material_fields["audit_status_source"],
        "report_type": "TRANSCRIPT"
        if chunk.get("structure_type") == "TRANSCRIPT_SPEAKER_TURN"
        else "UNKNOWN",
        "comparability_status": "NOT_ASSESSED",
        "comparison_basis_id": None,
        "comparability_reason_codes": [],
        "report_version_id": str(chunk["material_id"]),
        "restatement_status": "ORIGINAL",
        "restates_fact_id": None,
        "comparison_preferred": False,
    }


def text_record(
    chunk: dict[str, Any],
    sentence: str,
    source_span_index: int,
    entity: dict[str, Any],
    period: dict[str, Any],
    material_fields: dict[str, Any],
) -> dict[str, Any]:
    condition_match = re.search(
        r"^(?:if|unless|provided that|based on)\b[^,;，；]*",
        sentence,
        flags=re.IGNORECASE,
    )
    uncertainty_matches = re.findall(
        r"\b(?:may|might|could|expected|expects|approximately|about)\b|可能|预计|大约",
        sentence,
        flags=re.IGNORECASE,
    )
    negated = bool(
        re.search(r"\b(?:not|no|never|without)\b|不|未|无", sentence, flags=re.IGNORECASE)
    )
    record = {
        **common_record(
            chunk, sentence, source_span_index, "TEXT_PROPOSITION", material_fields
        ),
        **entity,
        **period,
        "speaker_or_publisher": chunk.get("speaker_label"),
        "section": chunk["content_locator"].get("section"),
        "statement_at": None,
        "target_period": period.get("source_period_text"),
        "polarity": "NEGATED" if negated else "AFFIRMATIVE",
        "condition_text": condition_match.group(0) if condition_match else None,
        "uncertainty_text": ", ".join(uncertainty_matches) if uncertainty_matches else None,
        "applicability_scope": period.get("source_period_text"),
        "content_type_hint": {
            "value": "AI_SUMMARY"
            if str(chunk["content_locator"].get("section", "")).startswith("AI Summary")
            else "SOURCE_WORDING",
            "authoritative": False,
        },
        "normalization_status": "PASS",
        "gap_ids": [],
    }
    record["fact_id"] = fact_id(
        {
            "chunk_id": chunk["chunk_id"],
            "record_kind": "TEXT_PROPOSITION",
            "source_span_text": sentence,
            "source_span_index": source_span_index,
        }
    )
    return record


def numeric_context_defaults(chunk: dict[str, Any]) -> dict[str, Any]:
    context = chunk.get("numeric_context") or {}
    text = " ".join(str(value) for value in context.get("units", []))
    normalized = matching_key(text)
    currency = None
    if re.search(r"\b(?:usd|us\$)\b", normalized):
        currency = "USD"
    elif re.search(r"\b(?:cny|rmb)\b", normalized):
        currency = "CNY"
    scale_factor = Decimal("1")
    if "billion" in normalized:
        scale_factor = Decimal("1000000000")
    elif "million" in normalized:
        scale_factor = Decimal("1000000")
    elif "thousand" in normalized:
        scale_factor = Decimal("1000")
    unit = None
    if "percentage point" in normalized or re.search(r"\bpp\b", normalized):
        unit = "PERCENTAGE_POINT"
    elif "%" in normalized or "percent" in normalized:
        unit = "PERCENT"
    elif re.search(r"\b(?:wafers?|pieces?)\b", normalized) or "片" in normalized:
        unit = "COUNT"
    elif currency or scale_factor != 1:
        unit = "MONEY"
    return {
        "currency": currency,
        "scale_factor": scale_factor,
        "unit": unit,
        "source": text or None,
    }


def parse_numeric_match(
    match: re.Match[str], context_defaults: dict[str, Any]
) -> dict[str, Any] | None:
    currency_text = match.group("currency")
    scale_text = match.group("scale")
    unit_text = match.group("unit")
    if not any((currency_text, scale_text, unit_text, context_defaults.get("unit"))):
        return None
    raw_number = match.group("number").replace(",", "")
    try:
        numeric = Decimal(raw_number)
    except InvalidOperation:
        return None
    if match.group("open") and match.group("close"):
        numeric = -numeric
    scale_factors = {
        None: Decimal("1"),
        "thousand": Decimal("1000"),
        "million": Decimal("1000000"),
        "mn": Decimal("1000000"),
        "billion": Decimal("1000000000"),
        "bn": Decimal("1000000000"),
    }
    scale_key = scale_text.casefold() if scale_text else None
    scale_factor = (
        scale_factors[scale_key]
        if scale_key is not None
        else context_defaults.get("scale_factor", Decimal("1"))
    )
    currency_map = {"$": "USD", "us$": "USD", "usd": "USD", "rmb": "CNY", "cny": "CNY"}
    currency = (
        currency_map.get(currency_text.casefold())
        if currency_text
        else context_defaults.get("currency")
    )
    normalized_unit = str(context_defaults.get("unit") or "MONEY")
    if unit_text:
        normalized_unit = (
            "PERCENTAGE_POINT" if "point" in unit_text.casefold() or unit_text.casefold() == "pp" else "PERCENT"
        )
    raw_value_text = match.group(0).strip()
    decimals = len(raw_number.partition(".")[2]) if "." in raw_number else 0
    base_unit_value = None
    trace: list[dict[str, Any]] = []
    if normalized_unit in {"MONEY", "COUNT"}:
        base_value = numeric * scale_factor
        base_unit_value = format(base_value, "f")
        trace.append(
            {
                "rule_id": "DECIMAL_SCALE_V1"
                if normalized_unit == "MONEY"
                else "COUNT_SCALE_V1",
                "before": format(numeric, "f"),
                "after": base_unit_value,
                "formula": "base_unit_value = raw_numeric_value * raw_scale_factor",
                "exact": True,
            }
        )
    else:
        trace.append(
            {
                "rule_id": "PRESERVE_REPORTED_PERCENT_V1",
                "before": format(numeric, "f"),
                "after": format(numeric, "f"),
                "formula": "normalized_value = raw_numeric_value",
                "exact": True,
            }
        )
    return {
        "raw_value_text": raw_value_text,
        "raw_numeric_value": format(numeric, "f"),
        "value_status": "EXPLICIT_ZERO" if numeric == 0 else "PRESENT",
        "raw_unit": normalized_unit,
        "raw_currency": currency,
        "raw_scale_factor": format(scale_factor, "f"),
        "normalized_value": format(numeric, "f"),
        "target_unit": normalized_unit,
        "target_currency": currency,
        "target_scale_factor": format(scale_factor, "f"),
        "base_unit_value": base_unit_value,
        "reported_precision": {"decimal_places": decimals},
        "rounding_increment": format(Decimal(1).scaleb(-decimals) * scale_factor, "f"),
        "technical_conversion_trace": trace,
        "value_origin": "SOURCE_REPORTED",
        "currency_conversion_status": "NOT_REQUIRED",
        "numeric_context_source": context_defaults.get("source"),
    }


def technical_measurement_metadata(
    sentence: str,
    chunk: dict[str, Any],
    metric: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, Any]:
    context = chunk.get("numeric_context") or {}
    searchable = matching_key(
        " ".join(
            [
                sentence,
                *(str(value) for value in context.get("headers", [])),
                *(str(value) for value in context.get("units", [])),
                *(str(value) for value in context.get("footnotes", [])),
            ]
        )
    )
    wafer_basis = None
    wafer_basis_rule_id = None
    for rule in rules.get("wafer_basis_rules", []):
        if matching_key(str(rule["match_text"])) in searchable:
            wafer_basis = rule["wafer_basis"]
            wafer_basis_rule_id = rule["rule_id"]
            break
    metric_id = metric.get("metric_id")
    measurement_by_metric = {
        "MONTHLY_CAPACITY_EIGHT_INCH_EQUIVALENT": "MONTHLY_CAPACITY",
        "PERIOD_END_CAPACITY": "PERIOD_END_CAPACITY",
        "WAFER_SHIPMENTS": "PERIOD_SHIPMENTS",
        "CAPACITY_UTILIZATION_RATE_SOURCE_REPORTED": "SOURCE_REPORTED_RATE",
        "ASP_SOURCE_REPORTED": "SOURCE_REPORTED_ASP",
    }
    composition_set_id = None
    composition_denominator_id = None
    composition_taxonomy_version = None
    if metric_id == "APPLICATION_REVENUE_SHARE":
        composition_set_id = "SMIC_APPLICATION_REVENUE_MIX"
        composition_denominator_id = "WAFER_REVENUE"
        composition_taxonomy_version = "SOURCE_REPORTED_APPLICATION_TAXONOMY_V1"
    elif metric_id == "WAFER_SIZE_REVENUE_SHARE":
        composition_set_id = "SMIC_WAFER_SIZE_REVENUE_MIX"
        composition_denominator_id = "WAFER_REVENUE"
        composition_taxonomy_version = "SOURCE_REPORTED_WAFER_SIZE_TAXONOMY_V1"
    return {
        "wafer_basis": wafer_basis,
        "wafer_basis_rule_id": wafer_basis_rule_id,
        "measurement_basis": (
            measurement_by_metric.get(str(metric_id)) if metric_id is not None else None
        ),
        "composition_set_id": composition_set_id,
        "composition_denominator_id": composition_denominator_id,
        "composition_taxonomy_version": composition_taxonomy_version,
    }


def missing_value_records(
    chunk: dict[str, Any],
    sentence: str,
    source_span_index: int,
    entity: dict[str, Any],
    periods: list[dict[str, Any]],
    rules: dict[str, Any],
    material_fields: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    defaults = numeric_context_defaults(chunk)
    pattern = re.compile(r"(?<![A-Za-z])N/?A(?![A-Za-z])|(?<!\w)[—–](?!\w)|(?<!\w)-(?!\w)", re.IGNORECASE)
    for index, match in enumerate(pattern.finditer(sentence)):
        raw = match.group(0)
        status = "NOT_APPLICABLE" if raw.casefold() in {"n/a", "na"} else "UNKNOWN"
        metric = metric_mapping(sentence, match.start(), rules)
        technical_metadata = technical_measurement_metadata(
            sentence, chunk, metric, rules
        )
        period = period_for_position(periods, match.start())
        record = {
            **common_record(
                chunk,
                sentence,
                source_span_index,
                "NUMERIC_OBSERVATION",
                material_fields,
            ),
            **entity,
            **metric,
            **period,
            "raw_value_text": raw,
            "raw_numeric_value": None,
            "value_status": status,
            "raw_unit": defaults.get("unit"),
            "raw_currency": defaults.get("currency"),
            "raw_scale_factor": format(defaults.get("scale_factor", Decimal("1")), "f"),
            "normalized_value": None,
            "target_unit": defaults.get("unit"),
            "target_currency": defaults.get("currency"),
            "target_scale_factor": format(defaults.get("scale_factor", Decimal("1")), "f"),
            "base_unit_value": None,
            "reported_precision": None,
            "rounding_increment": None,
            "technical_conversion_trace": [],
            "value_origin": "SOURCE_REPORTED",
            "currency_conversion_status": "NOT_REQUIRED",
            "currency_source": (
                {
                    "chunk_id": chunk["chunk_id"],
                    "content_locator": chunk["content_locator"],
                    "rule_id": "FIELD_CURRENCY_TABLE_CONTEXT_V1",
                    "source_level": "LOCAL",
                }
                if defaults.get("currency")
                else material_fields.get("currency_source")
            ),
            "numeric_context_source": defaults.get("source"),
            **technical_metadata,
            "normalization_status": "PASS" if status == "NOT_APPLICABLE" else "PARTIAL",
            "gap_ids": [],
        }
        record["fact_id"] = fact_id(
            {
                "chunk_id": chunk["chunk_id"],
                "record_kind": "NUMERIC_OBSERVATION",
                "source_span_text": sentence,
                "source_span_index": source_span_index,
                "missing_index": index,
                "raw_value_text": raw,
                "metric_id": metric["metric_id"],
            }
        )
        records.append(record)
    return records


def numeric_records(
    chunk: dict[str, Any],
    sentence: str,
    source_span_index: int,
    entity: dict[str, Any],
    periods: list[dict[str, Any]],
    rules: dict[str, Any],
    material_fields: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    context_defaults = numeric_context_defaults(chunk)
    bridge_metadata = bridge_row_metadata(sentence, rules)
    for index, match in enumerate(NUMBER_PATTERN.finditer(sentence)):
        number = parse_numeric_match(match, context_defaults)
        if number is None:
            continue
        metric = metric_mapping(sentence, match.start(), rules)
        technical_metadata = technical_measurement_metadata(
            sentence, chunk, metric, rules
        )
        period = period_for_position(periods, match.start())
        if number["raw_currency"] is None and material_fields.get("currency") not in {
            None,
            "UNKNOWN",
            "AMBIGUOUS",
        }:
            number["raw_currency"] = material_fields["currency"]
            number["target_currency"] = material_fields["currency"]
        currency_source: dict[str, Any] | None
        if match.group("currency"):
            currency_source = {
                "chunk_id": chunk["chunk_id"],
                "content_locator": chunk["content_locator"],
                "rule_id": "FIELD_CURRENCY_VALUE_SYMBOL_V1",
                "source_level": "LOCAL",
            }
        elif context_defaults.get("currency"):
            currency_source = {
                "chunk_id": chunk["chunk_id"],
                "content_locator": chunk["content_locator"],
                "rule_id": "FIELD_CURRENCY_TABLE_CONTEXT_V1",
                "source_level": "LOCAL",
            }
        else:
            currency_source = material_fields.get("currency_source")
        record = {
            **common_record(
                chunk,
                sentence,
                source_span_index,
                "NUMERIC_OBSERVATION",
                material_fields,
            ),
            **entity,
            **metric,
            **period,
            **number,
            **bridge_metadata,
            "currency_source": currency_source,
            **technical_metadata,
            "normalization_status": "PASS",
            "gap_ids": [],
        }
        if bridge_metadata["bridge_row_role"] == "ADJUSTMENT_DETAIL":
            source_amount = Decimal(str(record["base_unit_value"]))
            record["source_display_sign"] = (
                "NEGATIVE" if source_amount < 0 else "POSITIVE"
            )
            record["normalized_signed_amount"] = format(
                abs(source_amount)
                if bridge_metadata["bridge_operation"] == "ADD"
                else -abs(source_amount),
                "f",
            )
        else:
            record["source_display_sign"] = None
            record["normalized_signed_amount"] = None
        record["fact_id"] = fact_id(
            {
                "chunk_id": chunk["chunk_id"],
                "record_kind": "NUMERIC_OBSERVATION",
                "source_span_text": sentence,
                "source_span_index": source_span_index,
                "numeric_index": index,
                "raw_value_text": number["raw_value_text"],
                "metric_id": metric["metric_id"],
            }
        )
        records.append(record)
    return records


def normalize_chunks(
    chunks: list[dict[str, Any]], rules: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    chunks_by_material: dict[str, list[dict[str, Any]]] = {}
    detections: dict[str, dict[str, tuple[str, dict[str, Any]]]] = {}
    for chunk in chunks:
        chunks_by_material.setdefault(str(chunk["material_id"]), []).append(chunk)
        detections[str(chunk["chunk_id"])] = detected_fields(chunk)
    for chunk in chunks:
        if not chunk.get("candidate_context"):
            continue
        entity = entity_mapping(str(chunk["material_id"]), rules)
        material_fields = resolve_material_fields(
            chunk,
            chunks_by_material[str(chunk["material_id"])],
            detections,
        )
        for source_span_index, sentence in enumerate(sentence_spans(str(chunk["text"]))):
            periods = periods_in_text(sentence)
            if not periods:
                periods = periods_from_chunk_context(chunk)
            text_period = period_for_position(periods, 0)
            sentence_records = [
                text_record(
                    chunk,
                    sentence,
                    source_span_index,
                    entity,
                    text_period,
                    material_fields,
                )
            ]
            sentence_records.extend(
                numeric_records(
                    chunk,
                    sentence,
                    source_span_index,
                    entity,
                    periods,
                    rules,
                    material_fields,
                )
            )
            sentence_records.extend(
                missing_value_records(
                    chunk,
                    sentence,
                    source_span_index,
                    entity,
                    periods,
                    rules,
                    material_fields,
                )
            )
            for record in sentence_records:
                missing_fields: list[str] = []
                if record.get("entity_mapping_status") != "MAPPED":
                    missing_fields.append("entity")
                if record["record_kind"] == "NUMERIC_OBSERVATION":
                    if record.get("metric_mapping_status") != "MAPPED":
                        missing_fields.append("metric")
                    if record.get("period_mapping_status") != "MAPPED":
                        missing_fields.append("period")
                    if record.get("raw_unit") == "MONEY" and not record.get("raw_currency"):
                        missing_fields.append("currency")
                for field in ("accounting_standard", "consolidation_scope", "audit_status"):
                    if record.get(field) == "UNKNOWN":
                        missing_fields.append(field)
                if missing_fields:
                    gap = gap_for_fact(record["fact_id"], missing_fields)
                    record["normalization_status"] = "PARTIAL"
                    record["gap_ids"] = [gap["gap_id"]]
                    gaps.append(gap)
                records.append(record)
    ytd_records, ytd_gaps = derive_ytd_differences(records, rules)
    ttm_records = derive_ttm_sums(records, rules)
    ratio_records = derive_fixed_margins(records, rules)
    change_records = derive_period_changes(records, rules)
    sensitivity_records = derive_government_funding_sensitivity(records, rules)
    records.extend(
        [
            *ytd_records,
            *ttm_records,
            *ratio_records,
            *change_records,
            *sensitivity_records,
        ]
    )
    gaps.extend(ytd_gaps)
    gaps.extend(reconcile_cas_to_ifrs(records))
    return records, gaps


def fixed_derivation_record(
    *,
    derivation_type: str,
    derivation_rule_id: str,
    inputs: list[dict[str, Any]],
    metric_id: str,
    formula: str,
    normalized_value: Decimal,
    base_unit_value: Decimal | None,
    target_unit: str,
    target_currency: str | None,
    target_scale_factor: Decimal,
    period_type: str,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    current = inputs[-1]
    input_fact_ids = [str(item["fact_id"]) for item in inputs]
    payload = {
        "record_kind": "DERIVATION",
        "derivation_type": derivation_type,
        "input_fact_ids": input_fact_ids,
        "period_start": period_start,
        "period_end": period_end,
        "metric_id": metric_id,
    }
    return {
        "fact_id": fact_id(payload),
        "snapshot_id": SNAPSHOT_ID,
        "record_kind": "DERIVATION",
        "chunk_id": current["chunk_id"],
        "material_id": current["material_id"],
        "content_locator": current["content_locator"],
        "source_span_text": None,
        "source_span_index": None,
        "claim_type": "UNASSESSED",
        "derivation_type": derivation_type,
        "derivation_rule_id": derivation_rule_id,
        "derivation_status": "PASS",
        "input_fact_ids": input_fact_ids,
        "formula": formula,
        "derived_value": format(normalized_value, "f"),
        "normalized_value": format(normalized_value, "f"),
        "base_unit_value": (
            format(base_unit_value, "f") if base_unit_value is not None else None
        ),
        "value_status": "EXPLICIT_ZERO" if normalized_value == 0 else "PRESENT",
        "target_unit": target_unit,
        "target_currency": target_currency,
        "target_scale_factor": format(target_scale_factor, "f"),
        "reported_precision": None,
        "rounding_increment": None,
        "input_precision_effect": "ROUNDED"
        if any(item.get("rounding_increment") != "1" for item in inputs)
        else "UNROUNDED",
        "technical_conversion_trace": [
            {
                "rule_id": derivation_rule_id,
                "formula": formula,
                "inputs": [item.get("base_unit_value") for item in inputs],
                "after": (
                    format(base_unit_value, "f")
                    if base_unit_value is not None
                    else format(normalized_value, "f")
                ),
                "exact": True,
            }
        ],
        "value_origin": "SYSTEM_DERIVED",
        "currency_conversion_status": "NOT_REQUIRED",
        "metric_id": metric_id,
        "source_metric_label": None,
        "metric_mapping_status": "MAPPED",
        "metric_mapping_rule_id": derivation_rule_id,
        "entity_id": current.get("entity_id"),
        "source_entity_label": current.get("source_entity_label"),
        "entity_mapping_status": current.get("entity_mapping_status"),
        "entity_mapping_rule_id": current.get("entity_mapping_rule_id"),
        "accounting_standard": current.get("accounting_standard"),
        "accounting_standard_source": current.get("accounting_standard_source"),
        "consolidation_scope": current.get("consolidation_scope"),
        "consolidation_scope_source": current.get("consolidation_scope_source"),
        "audit_status": "OUTSIDE_AUDIT_SCOPE",
        "audit_status_source": None,
        "report_type": current.get("report_type"),
        "period_mapping_status": "MAPPED",
        "period_nature": "DURATION",
        "period_type": period_type,
        "period_start": period_start,
        "period_end": period_end,
        "as_of_date": None,
        "fiscal_quarter": None,
        "ytd_through_quarter": None,
        "duration_days": (
            date.fromisoformat(period_end) - date.fromisoformat(period_start)
        ).days
        + 1,
        "comparability_status": "COMPARABLE",
        "comparison_basis_id": "COMPARISON_"
        + hashlib.sha256("|".join(input_fact_ids).encode("utf-8")).hexdigest()[:20],
        "comparability_reason_codes": [],
        "normalization_status": "PASS",
        "gap_ids": [],
        "report_version_id": current.get("report_version_id"),
        "restatement_status": current.get("restatement_status"),
        "restates_fact_id": None,
        "comparison_preferred": False,
    }


def comparable_quarter_observations(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if record["record_kind"] == "NUMERIC_OBSERVATION"
        and record.get("period_type") == "SINGLE_QUARTER"
        and record.get("period_start")
        and record.get("period_end")
        and record.get("base_unit_value") is not None
        and record.get("value_status") in {"PRESENT", "EXPLICIT_ZERO"}
        and record.get("metric_mapping_status") == "MAPPED"
        and record.get("entity_mapping_status") == "MAPPED"
        and record.get("accounting_standard") not in {None, "UNKNOWN", "AMBIGUOUS"}
        and record.get("consolidation_scope") not in {None, "UNKNOWN", "AMBIGUOUS"}
        and record.get("raw_currency") not in {None, "UNKNOWN", "AMBIGUOUS"}
    ]


def quarter_group_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("material_id"),
        record.get("metric_id"),
        record.get("entity_id"),
        record.get("accounting_standard"),
        record.get("consolidation_scope"),
        record.get("raw_currency"),
        record.get("raw_unit"),
        record.get("raw_scale_factor"),
        record.get("audit_status"),
        record.get("report_version_id"),
        record.get("restatement_status"),
    )


def consecutive_quarters(rows: list[dict[str, Any]]) -> bool:
    return all(
        date.fromisoformat(str(right["period_start"]))
        == date.fromisoformat(str(left["period_end"])) + timedelta(days=1)
        for left, right in zip(rows, rows[1:])
    )


def derive_ttm_sums(
    records: list[dict[str, Any]], rules: dict[str, Any]
) -> list[dict[str, Any]]:
    if "TTM_SUM" not in (rules.get("allowed_derivations") or []):
        return []
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for record in comparable_quarter_observations(records):
        groups.setdefault(quarter_group_key(record), []).append(record)
    derived: list[dict[str, Any]] = []
    for rows in groups.values():
        by_period: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_period.setdefault(str(row["period_start"]), []).append(row)
        if any(len(period_rows) != 1 for period_rows in by_period.values()):
            continue
        ordered = [period_rows[0] for _, period_rows in sorted(by_period.items())]
        for index in range(len(ordered) - 3):
            window = ordered[index : index + 4]
            if not consecutive_quarters(window):
                continue
            total = sum(
                (Decimal(str(item["base_unit_value"])) for item in window),
                start=Decimal("0"),
            )
            scale = Decimal(str(window[-1]["raw_scale_factor"]))
            derived.append(
                fixed_derivation_record(
                    derivation_type="TTM_SUM",
                    derivation_rule_id="DERIVE_TTM_SUM_FOUR_QUARTERS_V1",
                    inputs=window,
                    metric_id=str(window[-1]["metric_id"]),
                    formula="sum(base_unit_value of four consecutive comparable single quarters)",
                    normalized_value=total / scale,
                    base_unit_value=total,
                    target_unit=str(window[-1]["target_unit"]),
                    target_currency=str(window[-1]["target_currency"]),
                    target_scale_factor=scale,
                    period_type="TTM",
                    period_start=str(window[0]["period_start"]),
                    period_end=str(window[-1]["period_end"]),
                )
            )
    return derived


def derive_fixed_margins(
    records: list[dict[str, Any]], rules: dict[str, Any]
) -> list[dict[str, Any]]:
    definitions = (
        ("GROSS_MARGIN", "GROSS_PROFIT", "DERIVE_GROSS_MARGIN_V1"),
        ("OPERATING_MARGIN", "PROFIT_FROM_OPERATIONS", "DERIVE_OPERATING_MARGIN_V1"),
        (
            "OPERATING_CASH_FLOW_MARGIN",
            "NET_CASH_FROM_OPERATING_ACTIVITIES",
            "DERIVE_OPERATING_CASH_FLOW_MARGIN_V1",
        ),
    )
    allowed = set(rules.get("allowed_derivations") or [])
    observations = comparable_quarter_observations(records)
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for record in observations:
        key = (
            record.get("chunk_id"),
            record.get("source_span_index"),
            record.get("period_start"),
            record.get("period_end"),
            record.get("entity_id"),
            record.get("accounting_standard"),
            record.get("consolidation_scope"),
            record.get("raw_currency"),
        )
        groups.setdefault(key, []).append(record)
    derived: list[dict[str, Any]] = []
    for rows in groups.values():
        revenues = [row for row in rows if row.get("metric_id") == "REVENUE"]
        if len(revenues) != 1:
            continue
        revenue = revenues[0]
        revenue_base = Decimal(str(revenue["base_unit_value"]))
        if revenue_base <= 0:
            continue
        for output_metric, numerator_metric, rule_id in definitions:
            if output_metric not in allowed:
                continue
            numerators = [row for row in rows if row.get("metric_id") == numerator_metric]
            if len(numerators) != 1:
                continue
            numerator = numerators[0]
            if (
                numerator.get("raw_currency") != revenue.get("raw_currency")
                or numerator.get("raw_unit") != revenue.get("raw_unit")
            ):
                continue
            ratio = Decimal(str(numerator["base_unit_value"])) / revenue_base * Decimal("100")
            derived.append(
                fixed_derivation_record(
                    derivation_type=output_metric,
                    derivation_rule_id=rule_id,
                    inputs=[numerator, revenue],
                    metric_id=output_metric,
                    formula=f"{numerator_metric}.base_unit_value / REVENUE.base_unit_value * 100",
                    normalized_value=ratio,
                    base_unit_value=None,
                    target_unit="PERCENT",
                    target_currency=None,
                    target_scale_factor=Decimal("1"),
                    period_type=str(revenue["period_type"]),
                    period_start=str(revenue["period_start"]),
                    period_end=str(revenue["period_end"]),
                )
            )
    return derived


def derive_period_changes(
    records: list[dict[str, Any]], rules: dict[str, Any]
) -> list[dict[str, Any]]:
    if "PERIOD_CHANGE_PERCENT" not in (rules.get("allowed_derivations") or []):
        return []
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for record in comparable_quarter_observations(records):
        groups.setdefault(quarter_group_key(record), []).append(record)
    derived: list[dict[str, Any]] = []
    for rows in groups.values():
        by_period: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_period.setdefault(str(row["period_start"]), []).append(row)
        if any(len(period_rows) != 1 for period_rows in by_period.values()):
            continue
        ordered = [period_rows[0] for _, period_rows in sorted(by_period.items())]
        for previous, current in zip(ordered, ordered[1:]):
            if not consecutive_quarters([previous, current]):
                continue
            previous_value = Decimal(str(previous["base_unit_value"]))
            current_value = Decimal(str(current["base_unit_value"]))
            if previous_value <= 0 or current_value < 0:
                continue
            change = (current_value - previous_value) / previous_value * Decimal("100")
            derived.append(
                fixed_derivation_record(
                    derivation_type="PERIOD_CHANGE_PERCENT",
                    derivation_rule_id="DERIVE_PERIOD_CHANGE_PERCENT_POSITIVE_BASE_V1",
                    inputs=[previous, current],
                    metric_id=str(current["metric_id"]),
                    formula="(current_base_unit_value - previous_base_unit_value) / previous_base_unit_value * 100",
                    normalized_value=change,
                    base_unit_value=None,
                    target_unit="PERCENT",
                    target_currency=None,
                    target_scale_factor=Decimal("1"),
                    period_type="PERIOD_CHANGE",
                    period_start=str(previous["period_start"]),
                    period_end=str(current["period_end"]),
                )
            )
    return derived


def derive_government_funding_sensitivity(
    records: list[dict[str, Any]], rules: dict[str, Any]
) -> list[dict[str, Any]]:
    if "SENSITIVITY_EX_GOVERNMENT_FUNDING" not in (
        rules.get("allowed_derivations") or []
    ):
        return []
    whitelist = {
        item.get("adjustment_id")
        for item in (rules.get("adjustment_whitelist") or [])
        if item.get("formula_id") == "SENSITIVITY_EX_GOVERNMENT_FUNDING"
    }
    if "GOVERNMENT_FUNDING_RECOGNIZED_IN_OPERATING_PROFIT" not in whitelist:
        return []
    observations = comparable_quarter_observations(records)
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for record in observations:
        key = (
            record.get("chunk_id"),
            record.get("source_span_index"),
            record.get("period_start"),
            record.get("period_end"),
            record.get("entity_id"),
            record.get("accounting_standard"),
            record.get("consolidation_scope"),
            record.get("raw_currency"),
            record.get("raw_unit"),
        )
        groups.setdefault(key, []).append(record)
    derived: list[dict[str, Any]] = []
    for rows in groups.values():
        profits = [row for row in rows if row.get("metric_id") == "PROFIT_FROM_OPERATIONS"]
        funding = [
            row
            for row in rows
            if row.get("metric_id") == "GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL"
            and "government funding recognized in profit from operations"
            in matching_key(str(row.get("source_span_text") or ""))
        ]
        revenues = [row for row in rows if row.get("metric_id") == "REVENUE"]
        if len(profits) != 1 or len(funding) != 1:
            continue
        profit = profits[0]
        adjustment = funding[0]
        profit_base = Decimal(str(profit["base_unit_value"]))
        adjustment_base = Decimal(str(adjustment["base_unit_value"]))
        sensitivity_base = profit_base - adjustment_base
        scale = Decimal(str(profit["raw_scale_factor"]))
        profit_record = fixed_derivation_record(
            derivation_type="SENSITIVITY_EX_GOVERNMENT_FUNDING",
            derivation_rule_id="DERIVE_GOVERNMENT_FUNDING_SENSITIVITY_V1",
            inputs=[profit, adjustment],
            metric_id="PROFIT_FROM_OPERATIONS_EX_GOVERNMENT_FUNDING_SENSITIVITY",
            formula="PROFIT_FROM_OPERATIONS - GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL",
            normalized_value=sensitivity_base / scale,
            base_unit_value=sensitivity_base,
            target_unit=str(profit["target_unit"]),
            target_currency=str(profit["target_currency"]),
            target_scale_factor=scale,
            period_type=str(profit["period_type"]),
            period_start=str(profit["period_start"]),
            period_end=str(profit["period_end"]),
        )
        profit_record["sensitivity_label"] = "政府资金剔除敏感性营业利润"
        profit_record["adjustment_bridge"] = [
            {
                "role": "REPORTED_BASE",
                "fact_id": profit["fact_id"],
                "base_unit_value": profit["base_unit_value"],
            },
            {
                "role": "ADJUSTMENT_SUBTRACT",
                "fact_id": adjustment["fact_id"],
                "base_unit_value": adjustment["base_unit_value"],
                "adjustment_id": "GOVERNMENT_FUNDING_RECOGNIZED_IN_OPERATING_PROFIT",
            },
            {
                "role": "SENSITIVITY_RESULT",
                "fact_id": profit_record["fact_id"],
                "base_unit_value": profit_record["base_unit_value"],
            },
        ]
        derived.append(profit_record)
        if len(revenues) != 1:
            continue
        revenue = revenues[0]
        revenue_base = Decimal(str(revenue["base_unit_value"]))
        if revenue_base <= 0:
            continue
        margin_record = fixed_derivation_record(
            derivation_type="SENSITIVITY_EX_GOVERNMENT_FUNDING",
            derivation_rule_id="DERIVE_GOVERNMENT_FUNDING_MARGIN_SENSITIVITY_V1",
            inputs=[profit, adjustment, revenue],
            metric_id="OPERATING_MARGIN_EX_GOVERNMENT_FUNDING_SENSITIVITY",
            formula="(PROFIT_FROM_OPERATIONS - GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL) / REVENUE * 100",
            normalized_value=sensitivity_base / revenue_base * Decimal("100"),
            base_unit_value=None,
            target_unit="PERCENT",
            target_currency=None,
            target_scale_factor=Decimal("1"),
            period_type=str(revenue["period_type"]),
            period_start=str(revenue["period_start"]),
            period_end=str(revenue["period_end"]),
        )
        margin_record["sensitivity_label"] = "政府资金剔除敏感性营业利润率"
        margin_record["adjustment_bridge"] = [
            *profit_record["adjustment_bridge"][:2],
            {
                "role": "SENSITIVITY_MARGIN_RESULT",
                "fact_id": margin_record["fact_id"],
                "normalized_value": margin_record["normalized_value"],
                "revenue_fact_id": revenue["fact_id"],
            },
        ]
        derived.append(margin_record)
    return derived


def reconcile_cas_to_ifrs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bridge_rows = [
        record
        for record in records
        if record["record_kind"] == "NUMERIC_OBSERVATION"
        and record.get("bridge_row_role") is not None
        and record.get("base_unit_value") is not None
    ]
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in bridge_rows:
        key = (
            row.get("material_id"),
            row.get("metric_id"),
            row.get("entity_id"),
            row.get("period_type"),
            row.get("period_start"),
            row.get("period_end"),
            row.get("as_of_date"),
        )
        groups.setdefault(key, []).append(row)
    gaps: list[dict[str, Any]] = []
    comparability_fields = (
        "metric_id",
        "entity_id",
        "equity_attribution",
        "consolidation_scope",
        "raw_currency",
        "raw_unit",
        "raw_scale_factor",
        "report_version_id",
        "restatement_status",
        "period_type",
        "period_start",
        "period_end",
        "as_of_date",
    )
    for rows in groups.values():
        bases = [row for row in rows if row["bridge_row_role"] == "BASE"]
        details = [
            row for row in rows if row["bridge_row_role"] == "ADJUSTMENT_DETAIL"
        ]
        targets = [row for row in rows if row["bridge_row_role"] == "TARGET"]
        if len(bases) != 1 or len(targets) != 1 or not details:
            continue
        base = bases[0]
        target = targets[0]
        required = [base, *details, target]
        mismatch_fields = [
            field
            for field in comparability_fields
            if any(row.get(field) != base.get(field) for row in required[1:])
        ]
        accounting_roles_valid = (
            base.get("bridge_accounting_role") == "CAS"
            and target.get("bridge_accounting_role") == "IFRS"
            and all(
                detail.get("bridge_accounting_role") == "BRIDGE_ADJUSTMENT"
                for detail in details
            )
        )
        input_fact_ids = [base["fact_id"], *(detail["fact_id"] for detail in details), target["fact_id"]]
        check_rows = [
            {
                "fact_id": row["fact_id"],
                "row_role": row["bridge_row_role"],
                "bridge_operation": row.get("bridge_operation"),
                "source_display_sign": row.get("source_display_sign"),
                "normalized_signed_amount": row.get("normalized_signed_amount"),
                "included_in_sum": row["bridge_row_role"] in {"BASE", "ADJUSTMENT_DETAIL"},
            }
            for row in rows
        ]
        if mismatch_fields or not accounting_roles_valid:
            target["reconciliation_check"] = {
                "direction": "CAS_TO_IFRS",
                "rule_id": "RECONCILE_CAS_TO_IFRS_V1",
                "input_fact_ids": input_fact_ids,
                "rows": check_rows,
                "formula": "IFRS_TARGET = CAS_BASE + sum(normalized_signed_amount of ADJUSTMENT_DETAIL)",
                "recomputed_ifrs_target": None,
                "source_reported_ifrs_target": target["base_unit_value"],
                "difference": None,
                "tolerance": None,
                "reconciliation_status": "UNKNOWN",
                "reason": "COMPARABILITY_MISMATCH",
                "mismatch_fields": mismatch_fields,
            }
            continue
        recomputed = Decimal(str(base["base_unit_value"])) + sum(
            (Decimal(str(detail["normalized_signed_amount"])) for detail in details),
            start=Decimal("0"),
        )
        reported_target = Decimal(str(target["base_unit_value"]))
        difference = recomputed - reported_target
        increments = [row.get("rounding_increment") for row in required]
        tolerance: Decimal | None = None
        if all(increment is not None for increment in increments):
            tolerance = Decimal("0.5") * sum(
                (Decimal(str(increment)) for increment in increments),
                start=Decimal("0"),
            )
        if difference == 0:
            status = "PASS"
            reason = "EXACT_RECONCILIATION"
        elif tolerance is None:
            status = "UNKNOWN"
            reason = "DISCLOSURE_PRECISION_MISSING"
        elif abs(difference) <= tolerance:
            status = "WARN"
            reason = "ROUNDING_DIFFERENCE"
        else:
            status = "FAIL"
            reason = "FORMULA_MISMATCH"
        target["reconciliation_check"] = {
            "direction": "CAS_TO_IFRS",
            "rule_id": "RECONCILE_CAS_TO_IFRS_V1",
            "input_fact_ids": input_fact_ids,
            "rows": check_rows,
            "formula": "IFRS_TARGET = CAS_BASE + sum(normalized_signed_amount of ADJUSTMENT_DETAIL)",
            "recomputed_ifrs_target": format(recomputed, "f"),
            "source_reported_ifrs_target": format(reported_target, "f"),
            "difference": format(difference, "f"),
            "tolerance": format(tolerance, "f") if tolerance is not None else None,
            "reconciliation_status": status,
            "reason": reason,
            "mismatch_fields": [],
        }
        if status == "FAIL":
            gap_id = (
                "GAP_NORMALIZE_"
                + hashlib.sha256(
                    f"{target['fact_id']}|FORMULA_MISMATCH".encode("utf-8")
                ).hexdigest()[:16]
            )
            target["normalization_status"] = "BLOCKED"
            target["gap_ids"] = sorted({*target.get("gap_ids", []), gap_id})
            gaps.append(
                {
                    "gap_id": gap_id,
                    "origin_stage": "normalize-research-facts",
                    "gap_kind": "RECONCILIATION_FORMULA_MISMATCH",
                    "question": "The fixed CAS_TO_IFRS bridge does not reproduce the source IFRS target.",
                    "impact_objects": [target["fact_id"], *input_fact_ids],
                    "current_handling": "Block only this reconciliation; preserve every source observation.",
                    "confirmation_owner": "user/data_preparer",
                    "required_evidence": "A corrected bridge disclosure or matching row-role interpretation.",
                    "priority": "P1",
                    "status": "OPEN",
                }
            )
    return gaps


def derive_ytd_differences(
    records: list[dict[str, Any]], rules: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if "YTD_DIFFERENCE" not in (rules.get("allowed_derivations") or []):
        return [], []
    observations = [
        record
        for record in records
        if record["record_kind"] == "NUMERIC_OBSERVATION"
        and record.get("period_type") == "YEAR_TO_DATE"
        and record.get("value_status") in {"PRESENT", "EXPLICIT_ZERO"}
        and record.get("base_unit_value") is not None
    ]
    derived: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    match_fields = (
        "metric_id",
        "entity_id",
        "accounting_standard",
        "consolidation_scope",
        "raw_currency",
        "raw_unit",
        "raw_scale_factor",
        "audit_status",
        "report_version_id",
        "restatement_status",
    )
    for current in observations:
        current_quarter = current.get("ytd_through_quarter")
        if not isinstance(current_quarter, int) or current_quarter <= 1:
            continue
        structural_candidates = [
            previous
            for previous in observations
            if previous.get("ytd_through_quarter") == current_quarter - 1
            and previous.get("period_start") == current.get("period_start")
            and previous.get("metric_id") == current.get("metric_id")
            and previous.get("entity_id") == current.get("entity_id")
        ]
        if len(structural_candidates) != 1:
            continue
        previous = structural_candidates[0]
        comparison_identity = {
            "type": "YTD_DIFFERENCE",
            "current": current["fact_id"],
            "previous": previous["fact_id"],
        }
        comparison_basis_id = (
            "COMPARISON_"
            + hashlib.sha256(
                json.dumps(comparison_identity, sort_keys=True).encode("utf-8")
            ).hexdigest()[:20]
        )
        missing_required = [
            field
            for field in match_fields
            if current.get(field) in {None, "UNKNOWN", "AMBIGUOUS"}
            or previous.get(field) in {None, "UNKNOWN", "AMBIGUOUS"}
        ]
        reason_by_field = {
            "metric_id": "METRIC_DEFINITION_MISMATCH",
            "entity_id": "ENTITY_SCOPE_MISMATCH",
            "accounting_standard": "ACCOUNTING_STANDARD_MISMATCH",
            "consolidation_scope": "CONSOLIDATION_SCOPE_MISMATCH",
            "raw_currency": "CURRENCY_MISMATCH",
            "raw_unit": "UNIT_MISMATCH",
            "raw_scale_factor": "UNIT_SCALE_MISMATCH",
            "audit_status": "AUDIT_STATUS_MISMATCH",
            "report_version_id": "REPORT_VERSION_MISMATCH",
            "restatement_status": "RESTATEMENT_BASIS_MISMATCH",
        }
        mismatch_fields = [
            field
            for field in match_fields
            if previous.get(field) != current.get(field)
        ]
        if missing_required or mismatch_fields:
            reason_codes = sorted(
                {
                    "REQUIRED_COMPARABILITY_FIELD_UNKNOWN"
                    if missing_required
                    else "",
                    *(reason_by_field[field] for field in mismatch_fields),
                }
                - {""}
            )
            for source in (current, previous):
                source["comparability_status"] = "COMPARABILITY_BREAK"
                source["comparison_basis_id"] = comparison_basis_id
                source["comparability_reason_codes"] = reason_codes
            previous_end = date.fromisoformat(str(previous["period_end"]))
            current_end = date.fromisoformat(str(current["period_end"]))
            quarter_start = previous_end + timedelta(days=1)
            blocked_payload = {
                "record_kind": "DERIVATION",
                "derivation_type": "YTD_DIFFERENCE",
                "input_fact_ids": [current["fact_id"], previous["fact_id"]],
                "blocked_reasons": reason_codes,
            }
            blocked_fact_id = fact_id(blocked_payload)
            gap_id = (
                "GAP_NORMALIZE_"
                + hashlib.sha256(
                    f"{blocked_fact_id}|{'|'.join(reason_codes)}".encode("utf-8")
                ).hexdigest()[:16]
            )
            blocked = {
                "fact_id": blocked_fact_id,
                "snapshot_id": SNAPSHOT_ID,
                "record_kind": "DERIVATION",
                "chunk_id": current["chunk_id"],
                "material_id": current["material_id"],
                "content_locator": current["content_locator"],
                "source_span_text": None,
                "claim_type": "UNASSESSED",
                "derivation_type": "YTD_DIFFERENCE",
                "derivation_rule_id": "DERIVE_YTD_DIFFERENCE_SMIC_CALENDAR_V1",
                "derivation_status": "BLOCKED",
                "input_fact_ids": [current["fact_id"], previous["fact_id"]],
                "formula": "current_ytd_base_unit_value - previous_ytd_base_unit_value",
                "derived_value": None,
                "normalized_value": None,
                "base_unit_value": None,
                "value_status": "UNKNOWN",
                "target_unit": None,
                "target_currency": None,
                "target_scale_factor": None,
                "reported_precision": None,
                "rounding_increment": None,
                "input_precision_effect": "UNKNOWN",
                "technical_conversion_trace": [],
                "value_origin": "SYSTEM_DERIVED",
                "currency_conversion_status": "UNAVAILABLE"
                if "CURRENCY_MISMATCH" in reason_codes
                else "NOT_REQUIRED",
                "metric_id": current["metric_id"],
                "source_metric_label": current["source_metric_label"],
                "metric_mapping_status": current["metric_mapping_status"],
                "metric_mapping_rule_id": current["metric_mapping_rule_id"],
                "entity_id": current["entity_id"],
                "source_entity_label": current["source_entity_label"],
                "entity_mapping_status": current["entity_mapping_status"],
                "entity_mapping_rule_id": current["entity_mapping_rule_id"],
                "accounting_standard": current["accounting_standard"],
                "accounting_standard_source": current["accounting_standard_source"],
                "consolidation_scope": current["consolidation_scope"],
                "consolidation_scope_source": current["consolidation_scope_source"],
                "audit_status": "OUTSIDE_AUDIT_SCOPE",
                "audit_status_source": None,
                "report_type": current["report_type"],
                "period_mapping_status": "MAPPED",
                "period_nature": "DURATION",
                "period_type": "SINGLE_QUARTER",
                "period_start": quarter_start.isoformat(),
                "period_end": current_end.isoformat(),
                "as_of_date": None,
                "fiscal_quarter": current_quarter,
                "ytd_through_quarter": None,
                "duration_days": (current_end - quarter_start).days + 1,
                "comparability_status": "COMPARABILITY_BREAK",
                "comparison_basis_id": comparison_basis_id,
                "comparability_reason_codes": reason_codes,
                "normalization_status": "BLOCKED",
                "gap_ids": [gap_id],
                "report_version_id": current["report_version_id"],
                "restatement_status": current["restatement_status"],
                "restates_fact_id": None,
                "comparison_preferred": False,
            }
            derived.append(blocked)
            gaps.append(
                {
                    "gap_id": gap_id,
                    "origin_stage": "normalize-research-facts",
                    "gap_kind": "COMPARABILITY_BREAK",
                    "question": "YTD difference is blocked by: " + ", ".join(reason_codes),
                    "impact_objects": [blocked_fact_id, current["fact_id"], previous["fact_id"]],
                    "current_handling": "Preserve both source observations and do not calculate the quarter.",
                    "confirmation_owner": "user/data_preparer",
                    "required_evidence": "Comparable YTD inputs with matching accounting and technical scope.",
                    "priority": "P1",
                    "status": "OPEN",
                }
            )
            continue
        if any(
            current.get(field) in {None, "UNKNOWN", "AMBIGUOUS"}
            for field in match_fields
        ):
            continue
        for source in (current, previous):
            source["comparability_status"] = "COMPARABLE"
            source["comparison_basis_id"] = comparison_basis_id
        current_base = Decimal(str(current["base_unit_value"]))
        previous_base = Decimal(str(previous["base_unit_value"]))
        base_difference = current_base - previous_base
        scale_factor = Decimal(str(current["raw_scale_factor"]))
        displayed_difference = base_difference / scale_factor
        previous_end = date.fromisoformat(str(previous["period_end"]))
        current_end = date.fromisoformat(str(current["period_end"]))
        quarter_start = previous_end + timedelta(days=1)
        decimals = max(
            int(current["reported_precision"]["decimal_places"]),
            int(previous["reported_precision"]["decimal_places"]),
        )
        precision_effect = (
            "ROUNDED"
            if scale_factor != Decimal("1")
            or current.get("rounding_increment") != "1"
            or previous.get("rounding_increment") != "1"
            else "UNROUNDED"
        )
        payload = {
            "record_kind": "DERIVATION",
            "derivation_type": "YTD_DIFFERENCE",
            "input_fact_ids": [current["fact_id"], previous["fact_id"]],
            "period_start": quarter_start.isoformat(),
            "period_end": current_end.isoformat(),
        }
        derived_record = {
            "fact_id": fact_id(payload),
            "snapshot_id": SNAPSHOT_ID,
            "record_kind": "DERIVATION",
            "chunk_id": current["chunk_id"],
            "material_id": current["material_id"],
            "content_locator": current["content_locator"],
            "source_span_text": None,
            "claim_type": "UNASSESSED",
            "derivation_type": "YTD_DIFFERENCE",
            "derivation_rule_id": "DERIVE_YTD_DIFFERENCE_SMIC_CALENDAR_V1",
            "derivation_status": "PASS",
            "input_fact_ids": [current["fact_id"], previous["fact_id"]],
            "formula": "current_ytd_base_unit_value - previous_ytd_base_unit_value",
            "derived_value": format(displayed_difference, "f"),
            "normalized_value": format(displayed_difference, "f"),
            "base_unit_value": format(base_difference, "f"),
            "value_status": "EXPLICIT_ZERO" if base_difference == 0 else "PRESENT",
            "target_unit": current["target_unit"],
            "target_currency": current["target_currency"],
            "target_scale_factor": current["target_scale_factor"],
            "reported_precision": {"decimal_places": decimals},
            "rounding_increment": max(
                Decimal(str(current["rounding_increment"])),
                Decimal(str(previous["rounding_increment"])),
            ).to_eng_string(),
            "input_precision_effect": precision_effect,
            "technical_conversion_trace": [
                {
                    "rule_id": "DERIVE_YTD_DIFFERENCE_SMIC_CALENDAR_V1",
                    "formula": "current_ytd_base_unit_value - previous_ytd_base_unit_value",
                    "inputs": [
                        current["base_unit_value"],
                        previous["base_unit_value"],
                    ],
                    "after": format(base_difference, "f"),
                    "exact": True,
                }
            ],
            "value_origin": "SYSTEM_DERIVED",
            "currency_conversion_status": "NOT_REQUIRED",
            "metric_id": current["metric_id"],
            "source_metric_label": current["source_metric_label"],
            "metric_mapping_status": current["metric_mapping_status"],
            "metric_mapping_rule_id": current["metric_mapping_rule_id"],
            "entity_id": current["entity_id"],
            "source_entity_label": current["source_entity_label"],
            "entity_mapping_status": current["entity_mapping_status"],
            "entity_mapping_rule_id": current["entity_mapping_rule_id"],
            "accounting_standard": current["accounting_standard"],
            "accounting_standard_source": current["accounting_standard_source"],
            "consolidation_scope": current["consolidation_scope"],
            "consolidation_scope_source": current["consolidation_scope_source"],
            "audit_status": "OUTSIDE_AUDIT_SCOPE",
            "audit_status_source": None,
            "report_type": current["report_type"],
            "period_mapping_status": "MAPPED",
            "period_nature": "DURATION",
            "period_type": "SINGLE_QUARTER",
            "period_start": quarter_start.isoformat(),
            "period_end": current_end.isoformat(),
            "as_of_date": None,
            "fiscal_quarter": current_quarter,
            "ytd_through_quarter": None,
            "duration_days": (current_end - quarter_start).days + 1,
            "comparability_status": "COMPARABLE",
            "comparison_basis_id": comparison_basis_id,
            "comparability_reason_codes": [],
            "normalization_status": "PASS",
            "gap_ids": [],
            "report_version_id": current["report_version_id"],
            "restatement_status": current["restatement_status"],
            "restates_fact_id": None,
            "comparison_preferred": False,
        }
        derived.append(derived_record)
    return derived, gaps


def main() -> int:
    args = parse_args()
    try:
        verify_snapshot(args.snapshot_dir)
        retrieval = yaml.safe_load(args.retrieval_file.read_text(encoding="utf-8"))
        if retrieval.get("snapshot_id") != SNAPSHOT_ID:
            raise ValueError("retrieval result is not bound to Snapshot v3")
        if retrieval.get("retrieval_status") == "FAIL":
            raise ValueError("global retrieval FAIL blocks normalization")
        rules = yaml.safe_load(args.rules_file.read_text(encoding="utf-8"))
        if rules.get("snapshot_id") not in {None, SNAPSHOT_ID}:
            raise ValueError("normalization rules are not bound to Snapshot v3")
        chunks = read_jsonl(args.context_file)
        if any(chunk.get("snapshot_id") != SNAPSHOT_ID for chunk in chunks):
            raise ValueError("every context record must carry the exact Snapshot v3 identity")
        records, new_gaps = normalize_chunks(chunks, rules)
        rebuilt_records, rebuilt_gaps = normalize_chunks(chunks, rules)
        first_records_hash = canonical_jsonl_hash(records)
        rebuilt_records_hash = canonical_jsonl_hash(rebuilt_records)
        first_gaps_hash = sha256_text(
            json.dumps(new_gaps, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        rebuilt_gaps_hash = sha256_text(
            json.dumps(rebuilt_gaps, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        clean_rebuild_hashes_match = (
            first_records_hash == rebuilt_records_hash
            and first_gaps_hash == rebuilt_gaps_hash
        )
        fact_id_counts: dict[str, int] = {}
        for record in records:
            identifier = str(record["fact_id"])
            fact_id_counts[identifier] = fact_id_counts.get(identifier, 0) + 1
        duplicate_fact_ids = sorted(
            identifier for identifier, count in fact_id_counts.items() if count > 1
        )
        existing_gaps = yaml.safe_load(
            args.existing_gaps_file.read_text(encoding="utf-8")
        )
        if existing_gaps.get("snapshot_id") != SNAPSHOT_ID:
            raise ValueError("existing gap registry is not bound to Snapshot v3")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(args.output_dir / "normalized-facts.jsonl", records)
        write_yaml(
            args.output_dir / "gaps.yaml",
            {
                "snapshot_id": SNAPSHOT_ID,
                "gaps": [*(existing_gaps.get("gaps") or []), *new_gaps],
            },
        )
        if duplicate_fact_ids or not clean_rebuild_hashes_match:
            status = "FAIL"
        elif any(record["normalization_status"] != "PASS" for record in records):
            status = "WARN"
        else:
            status = "PASS"
        write_yaml(
            args.output_dir / "normalization-validation.yaml",
            {
                "snapshot_id": SNAPSHOT_ID,
                "normalization_rule_version": rules.get("rule_version"),
                "mapping_version": rules.get("mapping_version"),
                "normalization_run_status": status,
                "duplicate_fact_ids": duplicate_fact_ids,
                "clean_rebuild_hashes_match": clean_rebuild_hashes_match,
                "clean_rebuild_hashes": {
                    "first_records": first_records_hash,
                    "rebuilt_records": rebuilt_records_hash,
                    "first_gaps": first_gaps_hash,
                    "rebuilt_gaps": rebuilt_gaps_hash,
                },
                "statistics": {
                    "candidate_chunks": sum(1 for chunk in chunks if chunk.get("candidate_context")),
                    "facts": len(records),
                    "pass": sum(1 for record in records if record["normalization_status"] == "PASS"),
                    "partial": sum(1 for record in records if record["normalization_status"] == "PARTIAL"),
                    "blocked": sum(1 for record in records if record["normalization_status"] == "BLOCKED"),
                    "normalization_gaps": len(new_gaps),
                },
                "rules_hash": sha256_file(args.rules_file),
                "context_hash": sha256_file(args.context_file),
                "facts_hash": sha256_file(args.output_dir / "normalized-facts.jsonl"),
            },
        )
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
