from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


SNAPSHOT_ID = "smic-a283e95e2c9e8068"
CHUNKING_VERSION = "smic-structure-atoms-v1"


def sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return f"sha256:{digest.hexdigest()}"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def resolve_snapshot_path(snapshot_dir: Path, relative_path: str) -> Path:
    snapshot_root = snapshot_dir.resolve()
    candidate = (snapshot_root / relative_path).resolve()
    try:
        candidate.relative_to(snapshot_root)
    except ValueError as error:
        raise ValueError(f"snapshot path escapes input directory: {relative_path}") from error
    return candidate


def verify_manifest_files(snapshot_dir: Path, manifest: dict[str, Any]) -> None:
    for item in manifest.get("files", []):
        relative_path = str(item["path"])
        path = resolve_snapshot_path(snapshot_dir, relative_path)
        expected_hash = str(item["hash"])
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise ValueError(f"snapshot hash mismatch for {relative_path}")


def stable_chunk_id(material_id: str, locator: dict[str, Any], text: str) -> str:
    identity = json.dumps(
        {"material_id": material_id, "locator": locator, "text_hash": sha256_text(text)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"CHUNK_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"


def table_text(section: str, rows: list[list[Any]]) -> str:
    rendered_rows = [
        "\t".join("" if cell is None else str(cell) for cell in row).rstrip()
        for row in rows
    ]
    return "\n".join([section, *rendered_rows]).strip()


def numeric_context(rows: list[list[Any]]) -> dict[str, Any]:
    headers: list[str] = []
    if rows:
        headers = [str(cell) for cell in rows[0] if cell not in (None, "")]
    flattened = " ".join(
        str(cell) for row in rows for cell in row if cell not in (None, "")
    )
    periods = sorted(
        set(
            re.findall(
                r"\b(?:20\d{2}\s*Q[1-4]|Q[1-4]\s*20\d{2}|[1-4]Q\d{2}|20\d{2})\b",
                flattened,
                flags=re.IGNORECASE,
            )
        )
    )
    units = sorted(
        set(
            match.group(0)
            for match in re.finditer(
                r"\b(?:USD|CNY|RMB|US\$|HKD)?\s*(?:million|billion|thousand|%)\b",
                flattened,
                flags=re.IGNORECASE,
            )
        )
    )
    return {"headers": headers, "units": units, "periods": periods, "footnotes": []}


def base_chunk(
    material_id: str,
    structure_type: str,
    locator: dict[str, Any],
    text: str,
    number_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "snapshot_id": SNAPSHOT_ID,
        "chunk_id": stable_chunk_id(material_id, locator, text),
        "material_id": material_id,
        "structure_type": structure_type,
        "content_locator": locator,
        "text": text,
        "text_hash": sha256_text(text),
        "chunking_method": "STRUCTURE_ATOM",
        "chunking_version": CHUNKING_VERSION,
        "numeric_context": number_context
        or {"headers": [], "units": [], "periods": [], "footnotes": []},
        "candidate_context": False,
        "retrieval_keywords": [],
        "matched_query_ids": [],
        "selection_reasons": [],
        "retrieval_hits": [],
        "filter_reason": None,
    }


def chunks_from_html(material_id: str, parsed: dict[str, Any]) -> list[dict[str, Any]]:
    headings = [
        heading
        for heading in parsed.get("headings", [])
        if int(heading.get("level", 9)) < 4
    ]
    primary_heading = headings[-1] if headings else {"text": "UNTITLED", "locator": None}
    section = str(primary_heading.get("text") or "UNTITLED")
    paragraphs = [
        paragraph
        for paragraph in parsed.get("paragraphs", [])
        if str(paragraph.get("text") or "").strip()
    ]
    chunks: list[dict[str, Any]] = []
    if paragraphs:
        locator = {
            "section": section,
            "heading_locator": primary_heading.get("locator"),
            "paragraph_locators": [paragraph.get("locator") for paragraph in paragraphs],
        }
        text = "\n".join(
            [section, *(str(paragraph["text"]).strip() for paragraph in paragraphs)]
        )
        chunks.append(base_chunk(material_id, "HTML_SECTION", locator, text))
    for table in parsed.get("tables", []):
        rows = table.get("rows") or []
        if not rows:
            continue
        locator = {
            "section": section,
            "heading_locator": primary_heading.get("locator"),
            "table_number": table.get("table_number"),
            "table_locator": table.get("locator"),
        }
        text = table_text(section, rows)
        chunks.append(
            base_chunk(
                material_id,
                "HTML_TABLE",
                locator,
                text,
                numeric_context(rows),
            )
        )
    return chunks


def chunks_from_transcript(material_id: str, parsed: dict[str, Any]) -> list[dict[str, Any]]:
    headings = parsed.get("headings", [])
    ai_summary_heading = next(
        (
            str(heading.get("text"))
            for heading in headings
            if str(heading.get("text") or "").startswith("AI Summary")
        ),
        "AI Summary",
    )
    transcript_heading = next(
        (
            str(heading.get("text"))
            for heading in headings
            if str(heading.get("text") or "") == "Earnings Call Transcript"
        ),
        "Earnings Call Transcript",
    )
    transcript_started = False
    footer_started = False
    chunks: list[dict[str, Any]] = []
    for paragraph in parsed.get("paragraphs", []):
        text = str(paragraph.get("text") or "").strip()
        if not text:
            continue
        if text.startswith("©"):
            footer_started = True
        if re.search(
            r"welcome to .*(?:webcast|conference call|earnings call)",
            text,
            flags=re.IGNORECASE,
        ):
            transcript_started = True
        if footer_started:
            section = "SITE_FOOTER"
            structure_type = "HTML_STRUCTURAL_BLOCK"
        elif transcript_started:
            section = transcript_heading
            structure_type = "TRANSCRIPT_SPEAKER_TURN"
        elif re.search(r"comfortable buying|stay ready", text, flags=re.IGNORECASE):
            section = "PAGE_CHROME"
            structure_type = "HTML_STRUCTURAL_BLOCK"
        else:
            section = ai_summary_heading
            structure_type = "HTML_SECTION_ENTRY"
        locator = {
            "section": section,
            "paragraph_locator": paragraph.get("locator"),
        }
        chunk = base_chunk(material_id, structure_type, locator, text)
        if structure_type == "TRANSCRIPT_SPEAKER_TURN":
            if "operator instructions" in text.casefold():
                chunk["speaker_label"] = "OPERATOR"
                chunk["speaker_mapping_status"] = "MAPPED"
            else:
                chunk["speaker_label"] = None
                chunk["speaker_mapping_status"] = "UNKNOWN"
        chunks.append(chunk)
    return chunks


def chunks_from_pdf(material_id: str, parsed: dict[str, Any]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current_section = "DOCUMENT_BODY"
    for page in parsed.get("pages", []):
        page_number = page.get("page_number")
        section_candidates = [
            str(value).strip()
            for value in page.get("section_candidates", [])
            if str(value).strip()
        ]
        if section_candidates:
            current_section = section_candidates[0]
        page_text = str(page.get("text") or "").strip()
        if page_text:
            locator = {
                "page_number": page_number,
                "section": current_section,
                "paragraph_group": "page_text",
            }
            chunks.append(
                base_chunk(
                    material_id,
                    "PDF_PARAGRAPH_GROUP",
                    locator,
                    page_text,
                )
            )
        footnotes = [
            str(item.get("text") or "").strip()
            for item in page.get("footnote_candidates", [])
            if str(item.get("text") or "").strip()
        ]
        for table in page.get("tables", []):
            rows = table.get("rows") or []
            if not rows:
                continue
            locator = {
                "page_number": page_number,
                "section": current_section,
                "table_number": table.get("table_number"),
                "bbox": table.get("bbox"),
            }
            number_context = numeric_context(rows)
            page_units = re.findall(
                r"(?:US\$|USD|CNY|RMB|HKD)\s*(?:in\s+)?(?:thousands?|millions?|billions?)",
                page_text,
                flags=re.IGNORECASE,
            )
            page_periods = re.findall(
                r"\b(?:20\d{2}\s*Q[1-4]|Q[1-4]\s*20\d{2}|[1-4]Q\d{2}|20\d{2})\b",
                page_text,
                flags=re.IGNORECASE,
            )
            number_context["units"] = sorted(
                {*number_context["units"], *page_units}
            )
            number_context["periods"] = sorted(
                {*number_context["periods"], *page_periods}
            )
            number_context["footnotes"] = footnotes
            text = table_text(current_section, rows)
            if footnotes:
                text = "\n".join([text, *footnotes])
            chunks.append(
                base_chunk(
                    material_id,
                    "PDF_TABLE",
                    locator,
                    text,
                    number_context,
                )
            )
    return chunks


def build_chunks(snapshot_dir: Path) -> list[dict[str, Any]]:
    materials = read_jsonl(snapshot_dir / "materials.jsonl")
    chunks: list[dict[str, Any]] = []
    for material in sorted(materials, key=lambda item: str(item.get("material_id"))):
        if material.get("acquisition_status") != "ACQUIRED_UNASSESSED":
            continue
        if material.get("parse_status") != "PARSED":
            continue
        if not material.get("acquisition_targets"):
            continue
        parsed_path = material.get("parsed_path")
        if not parsed_path:
            continue
        parsed = json.loads(
            resolve_snapshot_path(snapshot_dir, str(parsed_path)).read_text(encoding="utf-8")
        )
        material_id = str(material["material_id"])
        parser_name = str(parsed.get("parser") or "")
        if parser_name.startswith("html-parser"):
            if "EARNINGS_CALL_TRANSCRIPT" in material_id:
                chunks.extend(chunks_from_transcript(material_id, parsed))
            else:
                chunks.extend(chunks_from_html(material_id, parsed))
        elif parser_name.startswith("pdfplumber"):
            if not parsed.get("reliable_text_layer", False):
                continue
            chunks.extend(chunks_from_pdf(material_id, parsed))
    return chunks


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def normalized_period_tokens(value: str) -> list[str]:
    tokens: set[str] = set()
    patterns = (
        (r"\bq([1-4])\s*(20\d{2})\b", lambda match: (match.group(2), match.group(1))),
        (r"\b(20\d{2})\s*q([1-4])\b", lambda match: (match.group(1), match.group(2))),
        (r"\b([1-4])q(\d{2})\b", lambda match: (f"20{match.group(2)}", match.group(1))),
    )
    for pattern, values in patterns:
        for match in re.finditer(pattern, value, flags=re.IGNORECASE):
            year, quarter = values(match)
            tokens.add(f"period:{year}q{quarter}")
    return sorted(tokens)


def chinese_tokens(value: str, lexicon: list[str]) -> list[str]:
    terms = sorted({term for term in lexicon if term}, key=lambda term: (-len(term), term))
    tokens: list[str] = []
    index = 0
    while index < len(value):
        matched = next((term for term in terms if value.startswith(term, index)), None)
        if matched:
            tokens.append(matched)
            index += len(matched)
            continue
        end = index + 1
        while end < len(value) and not any(value.startswith(term, end) for term in terms):
            end += 1
        unmatched = value[index:end]
        if len(unmatched) == 1:
            tokens.append(unmatched)
        else:
            tokens.extend(unmatched[offset : offset + 2] for offset in range(len(unmatched) - 1))
        index = end
    return tokens


def tokenize(value: str, tokenizer_rules: dict[str, Any]) -> list[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    tokens = normalized_period_tokens(normalized)
    lexicon = [
        unicodedata.normalize("NFKC", str(term)).casefold()
        for term in tokenizer_rules.get("chinese_lexicon", [])
    ]
    pieces = re.findall(
        r"r&d|[a-z]+(?:[-/][a-z0-9]+)+|[a-z]+|\d+(?:\.\d+)?%?|[\u4e00-\u9fff]+",
        normalized,
    )
    for piece in pieces:
        if re.fullmatch(r"[\u4e00-\u9fff]+", piece):
            tokens.extend(chinese_tokens(piece, lexicon))
        else:
            tokens.append(piece)
            if "-" in piece or "/" in piece:
                tokens.extend(part for part in re.split(r"[-/]", piece) if part)
    stopwords = {
        unicodedata.normalize("NFKC", str(term)).casefold()
        for term in tokenizer_rules.get("stopwords", [])
    }
    return [token for token in tokens if token not in stopwords]


def bm25_scores(documents: list[list[str]], query_tokens: list[str]) -> list[float]:
    if not documents:
        return []
    document_frequencies: Counter[str] = Counter()
    for document in documents:
        document_frequencies.update(set(document))
    average_length = sum(len(document) for document in documents) / len(documents)
    average_length = average_length or 1.0
    query_terms = set(query_tokens)
    scores: list[float] = []
    for document in documents:
        frequencies = Counter(document)
        score = 0.0
        for token in query_terms:
            frequency = frequencies[token]
            if not frequency:
                continue
            document_frequency = document_frequencies[token]
            inverse_document_frequency = math.log(
                1.0
                + (len(documents) - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            denominator = frequency + 1.5 * (
                1.0 - 0.75 + 0.75 * len(document) / average_length
            )
            score += inverse_document_frequency * frequency * 2.5 / denominator
        scores.append(score)
    return scores


def is_structural_boilerplate(chunk: dict[str, Any]) -> bool:
    if chunk["structure_type"] == "HTML_STRUCTURAL_BLOCK":
        return True
    text = str(chunk["text"]).casefold()
    boilerplate_patterns = (
        "cookie policy",
        "all rights reserved",
        "terms of service",
        "privacy policy",
        "recommendation to buy or sell",
        "comfortable buying",
    )
    return any(pattern in text for pattern in boilerplate_patterns)


def capped_top_hits(scored: list[tuple[float, dict[str, Any]]]) -> list[tuple[float, dict[str, Any]]]:
    material_counts: Counter[str] = Counter()
    capped: list[tuple[float, dict[str, Any]]] = []
    for score, chunk in scored:
        material_id = str(chunk["material_id"])
        if material_counts[material_id] >= 5:
            continue
        material_counts[material_id] += 1
        capped.append((score, chunk))
    if len(capped) <= 20:
        return capped
    boundary_score = capped[19][0]
    return [item for item in capped if item[0] >= boundary_score]


def append_once(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def apply_retrieval(
    chunks: list[dict[str, Any]], rules: dict[str, Any]
) -> list[dict[str, Any]]:
    tokenizer_rules = rules.get("tokenizer") or {}
    document_tokens = [tokenize(str(chunk["text"]), tokenizer_rules) for chunk in chunks]
    for chunk in chunks:
        if is_structural_boilerplate(chunk):
            chunk["filter_reason"] = "STRUCTURAL_BOILERPLATE"
    query_results: list[dict[str, Any]] = []
    for family in rules.get("query_families", []):
        family_id = str(family["family_id"])
        responsibility = str(family["responsibility"])
        for query in family.get("queries", []):
            query_id = str(query["query_id"])
            query_tokens = tokenize(str(query["text"]), tokenizer_rules)
            anchor_tokens = {
                unicodedata.normalize("NFKC", str(token)).casefold()
                for token in query.get("anchor_tokens", [])
            }
            scores = bm25_scores(document_tokens, query_tokens)
            scored = [
                (score, chunk)
                for score, chunk, tokens in zip(scores, chunks, document_tokens)
                if score > 0 and anchor_tokens.intersection(tokens)
            ]
            scored.sort(key=lambda item: (-item[0], str(item[1]["chunk_id"])))
            selected = capped_top_hits(scored)
            hits: list[dict[str, Any]] = []
            direct_chunk_ids: list[str] = []
            for rank, (score, chunk) in enumerate(selected, start=1):
                filtered = chunk["filter_reason"] == "STRUCTURAL_BOILERPLATE"
                reason = "STRUCTURAL_BOILERPLATE" if filtered else "DIRECT_HIT"
                rounded_score = float(f"{score:.12f}")
                hit = {
                    "chunk_id": chunk["chunk_id"],
                    "material_id": chunk["material_id"],
                    "rank": rank,
                    "score": rounded_score,
                    "selection_reason": reason,
                }
                hits.append(hit)
                chunk["retrieval_hits"].append(
                    {
                        "query_id": query_id,
                        "query_family_id": family_id,
                        "responsibility": responsibility,
                        "rank": rank,
                        "score": rounded_score,
                        "selection_reason": reason,
                    }
                )
                append_once(chunk["matched_query_ids"], query_id)
                for token in query_tokens:
                    append_once(chunk["retrieval_keywords"], token)
                if not filtered:
                    chunk["candidate_context"] = True
                    append_once(chunk["selection_reasons"], "DIRECT_HIT")
                    direct_chunk_ids.append(str(chunk["chunk_id"]))
            for chunk_id in direct_chunk_ids:
                direct_index = next(
                    index for index, chunk in enumerate(chunks) if chunk["chunk_id"] == chunk_id
                )
                direct_chunk = chunks[direct_index]
                if direct_chunk["structure_type"] in {"PDF_TABLE", "HTML_TABLE"}:
                    continue
                direct_locator = direct_chunk["content_locator"]
                for adjacent_index in (direct_index - 1, direct_index + 1):
                    if adjacent_index < 0 or adjacent_index >= len(chunks):
                        continue
                    adjacent = chunks[adjacent_index]
                    if adjacent["material_id"] != direct_chunk["material_id"]:
                        continue
                    if adjacent["content_locator"].get("section") != direct_locator.get("section"):
                        continue
                    if adjacent["structure_type"] in {"PDF_TABLE", "HTML_TABLE"}:
                        continue
                    if adjacent["filter_reason"] == "STRUCTURAL_BOILERPLATE":
                        continue
                    adjacent["candidate_context"] = True
                    append_once(adjacent["matched_query_ids"], query_id)
                    for token in query_tokens:
                        append_once(adjacent["retrieval_keywords"], token)
                    append_once(adjacent["selection_reasons"], "ADJACENT_CONTEXT")
            query_results.append(
                {
                    "query_family_id": family_id,
                    "responsibility": responsibility,
                    "query_id": query_id,
                    "language": query.get("language"),
                    "raw_query": query["text"],
                    "tokens": query_tokens,
                    "anchor_tokens": sorted(anchor_tokens),
                    "hits": hits,
                }
            )
    return query_results


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def locator_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())


def resolve_labeled_chunks(
    chunks: list[dict[str, Any]], material_id: str, locator: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        chunk
        for chunk in chunks
        if chunk["material_id"] == material_id
        and locator_matches(chunk["content_locator"], locator)
    ]


def is_family_direct_hit(chunk: dict[str, Any], family_id: str) -> bool:
    return any(
        hit["query_family_id"] == family_id
        and hit["selection_reason"] == "DIRECT_HIT"
        for hit in chunk["retrieval_hits"]
    )


def ratio(numerator: int, denominator: int, empty_value: float = 1.0) -> float:
    return numerator / denominator if denominator else empty_value


def canonical_hash(value: Any) -> str:
    serialized = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return sha256_text(serialized)


def context_hash(chunks: list[dict[str, Any]]) -> str:
    serialized = "".join(
        json.dumps(chunk, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for chunk in chunks
    )
    return sha256_text(serialized)


def evaluate_acceptance(
    chunks: list[dict[str, Any]],
    query_results: list[dict[str, Any]],
    acceptance: dict[str, Any],
    second_context_hash: str,
    second_retrieval_hash: str,
) -> tuple[str, dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    labels = acceptance.get("labels") or []
    label_results: list[dict[str, Any]] = []
    must_total = 0
    must_hit = 0
    should_total = 0
    should_hit = 0
    negative_total = 0
    negative_candidates = 0
    must_locator_resolved = 0
    numeric_total = 0
    numeric_complete = 0
    family_should: dict[str, list[int]] = {}
    for label in labels:
        level = str(label["level"])
        family_id = str(label["query_family_id"])
        matches = resolve_labeled_chunks(
            chunks, str(label["material_id"]), label.get("locator") or {}
        )
        resolved = len(matches) == 1
        chunk = matches[0] if resolved else None
        direct_hit = bool(chunk and is_family_direct_hit(chunk, family_id))
        candidate_context = bool(chunk and chunk["candidate_context"])
        required_numeric_context = label.get("required_numeric_context") or []
        numeric_ok = True
        if required_numeric_context:
            numeric_total += 1
            numeric_ok = bool(
                chunk
                and all(chunk["numeric_context"].get(field) for field in required_numeric_context)
            )
            if numeric_ok:
                numeric_complete += 1
        if level == "MUST_HIT":
            must_total += 1
            must_hit += int(direct_hit)
            must_locator_resolved += int(resolved)
        elif level == "SHOULD_HIT":
            should_total += 1
            should_hit += int(direct_hit)
            family_counts = family_should.setdefault(family_id, [0, 0])
            family_counts[1] += 1
            family_counts[0] += int(direct_hit)
        elif level == "NEGATIVE_CONTROL":
            negative_total += 1
            negative_candidates += int(candidate_context)
        else:
            raise ValueError(f"unknown retrieval acceptance label level: {level}")
        label_results.append(
            {
                "label_id": label.get("label_id"),
                "level": level,
                "query_family_id": family_id,
                "resolved_chunk_ids": [match["chunk_id"] for match in matches],
                "direct_hit": direct_hit,
                "candidate_context": candidate_context,
                "numeric_context_complete": numeric_ok,
            }
        )
    precision_judgments = acceptance.get("precision_judgments") or []
    precision_by_query: dict[str, float] = {}
    precision_annotation_complete = True
    precision_details: list[dict[str, Any]] = []
    for query_result in query_results:
        query_id = str(query_result["query_id"])
        qualified_hits = [
            hit
            for hit in query_result["hits"]
            if hit["selection_reason"] == "DIRECT_HIT"
        ]
        evaluated_hits = qualified_hits[: min(5, len(qualified_hits))]
        relevant_count = 0
        judged_count = 0
        for hit in evaluated_hits:
            hit_chunk = next(
                chunk for chunk in chunks if chunk["chunk_id"] == hit["chunk_id"]
            )
            judgments = [
                judgment
                for judgment in precision_judgments
                if judgment.get("query_id") == query_id
                and judgment.get("material_id") == hit_chunk["material_id"]
                and locator_matches(
                    hit_chunk["content_locator"], judgment.get("locator") or {}
                )
            ]
            if len(judgments) != 1:
                precision_annotation_complete = False
                continue
            judged_count += 1
            relevant_count += int(bool(judgments[0].get("relevant")))
        denominator = len(evaluated_hits)
        precision = relevant_count / denominator if denominator else 0.0
        precision_by_query[query_id] = precision
        precision_details.append(
            {
                "query_id": query_id,
                "qualified_direct_hits": len(qualified_hits),
                "evaluated_count": denominator,
                "judged_count": judged_count,
                "relevant_count": relevant_count,
                "precision_at_min_5_n": precision,
            }
        )
    first_context_hash = context_hash(chunks)
    first_retrieval_hash = canonical_hash(query_results)
    clean_rebuild_match = (
        first_context_hash == second_context_hash
        and first_retrieval_hash == second_retrieval_hash
    )
    family_should_recall = {
        family_id: ratio(counts[0], counts[1])
        for family_id, counts in sorted(family_should.items())
    }
    must_hit_recall = ratio(must_hit, must_total)
    should_hit_recall_overall = ratio(should_hit, should_total)
    negative_control_candidate_rate = ratio(
        negative_candidates, negative_total, empty_value=0.0
    )
    locator_accuracy = ratio(must_locator_resolved, must_total)
    numeric_context_completeness = ratio(numeric_complete, numeric_total)
    metrics = {
        "must_hit_recall": must_hit_recall,
        "should_hit_recall_overall": should_hit_recall_overall,
        "should_hit_recall_by_family": family_should_recall,
        "precision_by_query": precision_by_query,
        "precision_annotation_complete": precision_annotation_complete,
        "negative_control_candidate_rate": negative_control_candidate_rate,
        "locator_accuracy": locator_accuracy,
        "numeric_context_completeness": numeric_context_completeness,
        "clean_rebuild_hashes_match": clean_rebuild_match,
    }
    hard_failures: list[str] = []
    if must_total and must_hit_recall < 1.0:
        hard_failures.append("MUST_HIT_RECALL")
    if negative_total and negative_control_candidate_rate != 0.0:
        hard_failures.append("NEGATIVE_CONTROL_CANDIDATE")
    if must_total and locator_accuracy < 1.0:
        hard_failures.append("MUST_HIT_LOCATOR_ACCURACY")
    if numeric_total and numeric_context_completeness < 1.0:
        hard_failures.append("NUMERIC_CONTEXT_COMPLETENESS")
    if not precision_annotation_complete:
        hard_failures.append("PRECISION_ANNOTATION_INCOMPLETE")
    if not clean_rebuild_match:
        hard_failures.append("CLEAN_REBUILD_MISMATCH")
    warnings: list[str] = []
    if should_total and should_hit_recall_overall < 0.8:
        warnings.append("SHOULD_HIT_RECALL_OVERALL")
    if any(value < 0.6 for value in family_should_recall.values()):
        warnings.append("SHOULD_HIT_RECALL_BY_FAMILY")
    if any(value < 0.6 for value in precision_by_query.values()):
        warnings.append("PRECISION_BY_QUERY")
    status = "FAIL" if hard_failures else "WARN" if warnings else "PASS"
    diagnostics = {
        "hard_failures": hard_failures,
        "warnings": warnings,
        "precision_details": precision_details,
    }
    clean_rebuild = {
        "first": {
            "context_hash": first_context_hash,
            "retrieval_hash": first_retrieval_hash,
        },
        "second": {
            "context_hash": second_context_hash,
            "retrieval_hash": second_retrieval_hash,
        },
    }
    return status, metrics, label_results, {**diagnostics, "clean_rebuild": clean_rebuild}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build deterministic context for the fixed SMIC Snapshot v3"
    )
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--rules-file", type=Path, required=True)
    parser.add_argument("--acceptance-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest_path = args.snapshot_dir / "snapshot-manifest.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("snapshot_id") != SNAPSHOT_ID:
            raise ValueError(f"{SNAPSHOT_ID} is the only accepted input")
        verify_manifest_files(args.snapshot_dir, manifest)
        rules = yaml.safe_load(args.rules_file.read_text(encoding="utf-8"))
        acceptance = yaml.safe_load(args.acceptance_file.read_text(encoding="utf-8"))
        if acceptance.get("snapshot_id") != SNAPSHOT_ID:
            raise ValueError("retrieval acceptance set is not bound to Snapshot v3")
        if acceptance.get("query_rule_version") != rules.get("rule_version"):
            raise ValueError("retrieval acceptance set and query rules have different versions")
        chunks = build_chunks(args.snapshot_dir)
        query_results = apply_retrieval(chunks, rules)
        second_chunks = build_chunks(args.snapshot_dir)
        second_query_results = apply_retrieval(second_chunks, rules)
        retrieval_status, metrics, label_results, diagnostics = evaluate_acceptance(
            chunks,
            query_results,
            acceptance,
            context_hash(second_chunks),
            canonical_hash(second_query_results),
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(args.output_dir / "context.jsonl", chunks)
        tokenizer_rules = rules.get("tokenizer") or {}
        write_yaml(
            args.output_dir / "retrieval-validation.yaml",
            {
                "snapshot_id": SNAPSHOT_ID,
                "query_rule_version": rules.get("rule_version"),
                "acceptance_version": acceptance.get("acceptance_version"),
                "tokenizer_version": tokenizer_rules.get("version"),
                "lexicon_version": tokenizer_rules.get("lexicon_version"),
                "stopwords_version": tokenizer_rules.get("stopwords_version"),
                "retrieval_status": retrieval_status,
                "metrics": metrics,
                "label_results": label_results,
                "diagnostics": {
                    "hard_failures": diagnostics["hard_failures"],
                    "warnings": diagnostics["warnings"],
                    "precision_details": diagnostics["precision_details"],
                },
                "clean_rebuild": diagnostics["clean_rebuild"],
                "queries": query_results,
            },
        )
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
