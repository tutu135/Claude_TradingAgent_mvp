"""Render the internal Markdown report for the fixed SMIC golden case (FR-070..FR-073).

Two properties shape everything below.

**Numbers live in the evidence table and nowhere else.** Every number the report states
sits on a row that carries its own period, accounting basis, unit, currency, scale,
source, publication time and `evidence_id`, so one blurred footnote can never cover
several numbers of different vintage. The model's prose is filtered by whole sentence:
a sentence holding a number that is not bound to a row does not enter the report at all.
Deleting the digits instead would leave "毛利率由上升到" -- still a claim, now a false one.
The frozen model output on disk is never modified; only the rendering drops the sentence.

**Nothing is manufactured to make a section look complete.** Snapshot v3 really has zero
quarantined records, zero conflict groups and zero government-funding sensitivity values.
Those zeros are printed as zeros, with the reason; the mechanisms behind them are proved
by fixtures in the test suite instead.

Presentation lives here and in `rules/report.yaml` only. No upstream stage reads either,
so changing how the report looks can never reach back into the pipeline.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

SNAPSHOT_DIR = Path("single-stock-demo-v3")
RUN_DIR = Path("single-stock-demo-run")
RULES_DIR = Path("rules")

DIGIT = re.compile(r"[0-9]")
NUMERIC_TOKEN = re.compile(r"[0-9]+(?:[.,][0-9]+)*%?")
DASH = "—"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def iter_jsonl(path: Path):
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


# ---------------------------------------------------------------------------
# Narrative sanitization (FR-071)
# ---------------------------------------------------------------------------


def split_sentences(text: str, terminators: str = "。！？；;!?") -> list[str]:
    sentences: list[str] = []
    buffer = ""
    for character in text:
        buffer += character
        if character in terminators:
            sentences.append(buffer)
            buffer = ""
    if buffer.strip():
        sentences.append(buffer)
    return [sentence for sentence in sentences if sentence.strip()]


# Structural line prefixes in the rendered Markdown. A line starting with one of these is a
# table row, a heading, a block quote or an identifier bullet -- places where a number sits
# on a row that names its own evidence, period and source.
STRUCTURAL_PREFIXES = ("|", "#", ">", "- `", "*")


def scan_rendered_report(text: str, fixed_notes: list[str]) -> list[str]:
    """Read the finished report back and find any number standing in free narrative.

    This deliberately starts from the rendered file rather than from the sanitizer's own
    output: a gate fed only pre-cleaned strings proves nothing about what else reached the
    page. A line escapes only by being structural or by matching a registered fixed note
    exactly -- so a number arriving from an unscanned field, a new render site or a typo
    still shows up here.
    """
    exempt = set(fixed_notes)
    leaked: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(STRUCTURAL_PREFIXES):
            continue
        if not DIGIT.search(stripped) or stripped in exempt:
            continue
        leaked.append(stripped)
    return leaked


# The field paths the render sites below actually put through the sanitizer. Asserted
# equal to `narrative_scan_field_paths` in rules/report.yaml at startup: a path declared in
# the rules with no render site would let the validation record claim a field was scanned
# when nothing scans it, and a render site using a path the rules do not declare would scan
# a field the rules never promised. Whether a given run exercises a path depends on the
# data (a dimension may carry no counter_evidence), so that is recorded, not gated.
RENDER_SITE_FIELD_PATHS = frozenset({
    "findings[].finding_statement",
    "findings[].supporting_evidence[].note",
    "findings[].supporting_evidence[].overlap_note",
    "findings[].counter_evidence[].note",
    "findings[].counter_evidence[].overlap_note",
    "findings[].alternative_explanations[]",
    "findings[].limitations[]",
    "findings[].gaps[]",
    "findings[].management_assertions[].statement",
    "findings[].watch_indicators[].indicator",
    "findings[].watch_indicators[].judgment_logic",
    "cross_attribution[].entries[].overlap_note",
    "challenges[].question",
    "challenges[].reason",
})


def sanitize(
    text: str, dimension_id: str | None, field_path: str, terminators: str = "。！？；;!?"
) -> tuple[str, list[dict[str, Any]]]:
    """Keep whole sentences without numbers; drop whole sentences that carry one."""
    normalized = " ".join(str(text).split())
    kept: list[str] = []
    omitted: list[dict[str, Any]] = []
    for sentence in split_sentences(normalized, terminators):
        if DIGIT.search(sentence):
            omitted.append(
                {
                    "dimension_id": dimension_id,
                    "field_path": field_path,
                    "matched_text": sentence.strip(),
                    "matched_numeric_tokens": NUMERIC_TOKEN.findall(sentence),
                    "action": "OMITTED_WHOLE_SENTENCE",
                }
            )
        else:
            kept.append(sentence.strip())
    return "".join(kept), omitted


# ---------------------------------------------------------------------------
# Scope recognition (ticket item 2). Deterministic; the orchestrator makes no model call.
# ---------------------------------------------------------------------------


def classify_question(
    question: str, report_rules: dict[str, Any], forbidden_terms: list[str] | None = None
) -> dict[str, Any]:
    scope = report_rules["scope_recognition"]
    if forbidden_terms is None:
        forbidden_terms = read_yaml(RULES_DIR / "analysis.yaml")["forbidden_investment_terms"]
    lowered = question.lower()

    hits = [term for term in forbidden_terms if str(term).lower() in lowered]
    if hits:
        # The one rule with teeth. FR-073 is a hard line, so this refuses outright rather
        # than answering with a caveat attached.
        return {"label": "OUT_OF_SCOPE_FORBIDDEN_OUTPUT", "action": "REFUSE", "matched": hits}
    peers = [name for name in scope["peer_entities"] if str(name).lower() in lowered]
    if peers:
        return {"label": "OUT_OF_SCOPE_OTHER_SUBJECT", "action": "DISCLAIM", "matched": peers}
    beyond = [marker for marker in scope["beyond_as_of_markers"] if str(marker) in question]
    if beyond:
        return {"label": "OUT_OF_SCOPE_BEYOND_AS_OF", "action": "DISCLAIM", "matched": beyond}
    return {"label": scope["in_scope_label"], "action": "ANSWER", "matched": []}


# ---------------------------------------------------------------------------
# Rendering primitives
# ---------------------------------------------------------------------------


class Report:
    """A Markdown document that remembers which blocks are free prose.

    Only prose blocks are subject to the unbound-number gate. Headings are structure and
    data blocks carry their numbers on a row that names the evidence behind them.
    """

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.prose: list[str] = []
        self.fixed: list[str] = []
        # Which declared field paths a render site actually put through the sanitizer.
        # Compared against rules/report.yaml at the end, so the validation record cannot
        # claim a field was scanned when no call site scans it.
        self.scanned_field_paths: set[str] = set()

    def sanitized(
        self, text: Any, dimension_id: str | None, field_path: str, terminators: str
    ) -> tuple[str, list[dict[str, Any]]]:
        if field_path not in RENDER_SITE_FIELD_PATHS:
            raise ValueError(f"render site sanitizes an undeclared field path: {field_path}")
        self.scanned_field_paths.add(field_path)
        return sanitize(text, dimension_id, field_path, terminators)

    def heading(self, level: int, text: str) -> None:
        self.lines.append("")
        self.lines.append(f"{'#' * level} {text}")
        self.lines.append("")

    def data(self, text: str = "") -> None:
        self.lines.append(text)

    def table(self, columns: list[str], rows: list[list[str]]) -> None:
        self.lines.append("| " + " | ".join(columns) + " |")
        self.lines.append("|" + "|".join(["---"] * len(columns)) + "|")
        for row in rows:
            self.lines.append("| " + " | ".join(row) + " |")
        self.lines.append("")

    def narrative(self, text: str) -> None:
        """Model-authored prose. Everything passed here is scanned by the final gate."""
        cleaned = " ".join(str(text).split())
        if not cleaned:
            return
        self.prose.append(cleaned)
        self.lines.append(cleaned)
        self.lines.append("")

    def note(self, text: str) -> None:
        """Fixed explanatory text authored in rules/report.yaml or in this renderer.

        Not scanned: it is a version-controlled constant, and the digits it contains are
        identifiers (FR-073, T1, P1, D3, v3), not research values. The gate exists for the
        model's free narrative, where a number would otherwise stand without a source.
        """
        cleaned = " ".join(str(text).split())
        if not cleaned:
            return
        self.fixed.append(cleaned)
        self.lines.append(cleaned)
        self.lines.append("")

    def render(self) -> str:
        text = "\n".join(self.lines).strip() + "\n"
        return re.sub(r"\n{3,}", "\n\n", text)


def cell(value: Any) -> str:
    if value is None or value == "":
        return DASH
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else DASH
    return str(value).replace("|", "\\|").replace("\n", " ")


# ---------------------------------------------------------------------------
# Evidence rows
# ---------------------------------------------------------------------------


def period_of(fact: dict[str, Any]) -> str:
    if fact.get("period_start") and fact.get("period_end"):
        return f"{fact.get('period_type')} {fact['period_start']}~{fact['period_end']}"
    if fact.get("as_of_date"):
        return f"{fact.get('period_type')} @{fact['as_of_date']}"
    return str(fact.get("period_type") or "UNKNOWN")


def basis_of(fact: dict[str, Any]) -> str:
    return "/".join(
        str(fact.get(key) or "UNKNOWN")
        for key in ("accounting_standard", "consolidation_scope", "audit_status", "value_origin")
    )


def locator_of(record: dict[str, Any], fact: dict[str, Any]) -> str:
    locator = fact.get("content_locator") or record.get("content_locator") or {}
    parts = []
    if locator.get("page_number") is not None:
        parts.append(f"p.{locator['page_number']}")
    if locator.get("section"):
        parts.append(str(locator["section"]))
    parts.append(str(record.get("chunk_id") or fact.get("chunk_id")))
    return " ".join(parts)


def source_of(material: dict[str, Any]) -> str:
    """Publisher, title and material_id together: material_id closes the traceability
    chain, and a source name without it cannot be grepped back into materials.jsonl."""
    return (
        f"{material.get('displayed_publisher') or DASH} / {material.get('title') or DASH}"
        f" ({material.get('material_id') or DASH})"
    )


def published_of(material: dict[str, Any]) -> str:
    publication = material.get("publication_time") or {}
    return str(publication.get("latest") or publication.get("raw_text") or "UNKNOWN")


# The four finding fields that may cite evidence, and the two keys a citation can use.
CITING_FIELDS = ("supporting_evidence", "counter_evidence", "management_assertions",
                 "watch_indicators")
CITATION_KEYS = ("evidence_id", "basis_evidence_id")


def cited_evidence_ids(finding: dict[str, Any]) -> list[str]:
    """Every evidence id a finding cites, in render order and without duplicates."""
    found: list[str] = []
    for field in CITING_FIELDS:
        for item in finding.get(field) or []:
            for key in CITATION_KEYS:
                if item.get(key) and str(item[key]) not in found:
                    found.append(str(item[key]))
    return found


def evidence_table(report: Report, columns: list[str], rows: list[dict[str, str]]) -> None:
    """Render rows in the column order `rules/report.yaml` declares.

    Rows are built as mappings and ordered here, so the rule file is the only place the
    evidence-table shape is defined. A column named in the rules that no row builder fills
    raises immediately rather than silently shifting every cell one place left.
    """
    ordered = sorted([row[column] for column in columns] for row in rows)
    report.table(columns, ordered or [[DASH] * len(columns)])


def numeric_row(
    record: dict[str, Any], fact: dict[str, Any], material: dict[str, Any],
    governed: dict[str, Any],
) -> dict[str, str]:
    return {
        "fact_id": cell(fact.get("fact_id")),
        "evidence_id": cell(record.get("evidence_id")),
        "metric_id": cell(fact.get("metric_id")),
        "display_value": cell(fact.get("normalized_value")),
        "base_unit_value": cell(fact.get("base_unit_value")),
        "raw_value_text": cell(fact.get("raw_value_text")),
        "unit": cell(fact.get("target_unit") or fact.get("raw_unit")),
        "currency": cell(fact.get("target_currency") or fact.get("raw_currency")),
        "scale_factor": cell(fact.get("target_scale_factor") or fact.get("raw_scale_factor")),
        "accounting_basis": cell(basis_of(fact)),
        "period": cell(period_of(fact)),
        "source": cell(source_of(material)),
        "published_at": cell(published_of(material)),
        "locator": cell(locator_of(record, fact)),
        "claim_type": cell(record.get("claim_type")),
        "gap_ids": cell(
            sorted({*(fact.get("gap_ids") or []), *(governed.get("gap_ids") or [])})
        ),
    }


def text_row(
    record: dict[str, Any], fact: dict[str, Any], material: dict[str, Any],
    governed: dict[str, Any],
) -> dict[str, str]:
    return {
        "fact_id": cell(fact.get("fact_id")),
        "evidence_id": cell(record.get("evidence_id")),
        "claim_type": cell(record.get("claim_type")),
        "source_tier": cell(record.get("source_tier")),
        "unit": cell(fact.get("target_unit") or fact.get("raw_unit")),
        "currency": cell(fact.get("target_currency") or fact.get("raw_currency")),
        "scale_factor": cell(fact.get("target_scale_factor") or fact.get("raw_scale_factor")),
        "accounting_basis": cell(basis_of(fact)),
        "period": cell(period_of(fact)),
        "source": cell(source_of(material)),
        "published_at": cell(published_of(material)),
        "locator": cell(locator_of(record, fact)),
        # Source spans are reproduced verbatim, English included: translating a source
        # span would manufacture new text with no provenance. Numbers appearing inside a
        # span are the source's own wording, bound to this row's evidence_id, source,
        # publication time and locator; the report never restates them as its own.
        "source_span_text": cell(
            fact.get("source_span_text") or record.get("source_span_text")
        ),
        "gap_ids": cell(
            sorted({*(fact.get("gap_ids") or []), *(governed.get("gap_ids") or [])})
        ),
    }


# ---------------------------------------------------------------------------
# The run's artefacts
# ---------------------------------------------------------------------------


class RunArtifacts:
    """Everything this run left on disk, loaded once and joined by business id."""

    def __init__(self) -> None:
        self.report_rules = read_yaml(RULES_DIR / "report.yaml")
        self.analysis_rules = read_yaml(RULES_DIR / "analysis.yaml")
        self.case = read_yaml(SNAPSHOT_DIR / "case.yaml")
        self.gate = read_yaml(RUN_DIR / "run-gate.yaml")
        self.integrity = read_yaml(RUN_DIR / "run-integrity.yaml")
        self.materials = {
            str(row["material_id"]): row
            for row in iter_jsonl(SNAPSHOT_DIR / "materials.jsonl")
        }

    def load_full(self) -> None:
        self.revised = read_yaml(RUN_DIR / "findings-revised.yaml")
        self.original = read_yaml(RUN_DIR / "findings.yaml")
        self.challenges = read_yaml(RUN_DIR / "challenges.yaml")
        self.gaps = read_yaml(RUN_DIR / "gaps.yaml")
        self.evidence_validation = read_yaml(RUN_DIR / "evidence-validation.yaml")
        self.analysis_validation = read_yaml(RUN_DIR / "analysis-validation.yaml")

        self.candidates = {
            str(row["evidence_id"]): row
            for row in iter_jsonl(RUN_DIR / "analysis-inputs.jsonl")
            if row.get("record_type") == "CANDIDATE_EVIDENCE"
        }
        self.governed = {
            str(row["evidence_id"]): row
            for row in iter_jsonl(RUN_DIR / "governed-evidence.jsonl")
        }
        self.evidence_by_fact: dict[str, dict[str, Any]] = {}
        for record in self.governed.values():
            self.evidence_by_fact.setdefault(str(record.get("fact_id")), record)

        cited: set[str] = set()
        for finding in self.revised.get("findings") or []:
            cited.update(cited_evidence_ids(finding))
        self.cited = cited

        needed = {
            str(self.candidates[evidence_id]["fact_id"])
            for evidence_id in cited
            if evidence_id in self.candidates
        }
        self.facts: dict[str, dict[str, Any]] = {}
        self.reconciliations: list[tuple[str, dict[str, Any]]] = []
        self.record_kinds: Counter[str] = Counter()
        self.extraction_suspects = 0
        self.numeric_total = 0
        gov_funding: set[str] = set()
        self.sensitivity_records = 0

        for fact in iter_jsonl(RUN_DIR / "normalized-facts.jsonl"):
            kind = str(fact.get("record_kind"))
            self.record_kinds[kind] += 1
            fact_id = str(fact.get("fact_id"))
            if kind == "NUMERIC_OBSERVATION":
                self.numeric_total += 1
            metric_id = fact.get("metric_id")
            if metric_id == "GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL":
                gov_funding.add(fact_id)
            if metric_id == "SENSITIVITY_EX_GOVERNMENT_FUNDING" or (
                fact.get("derivation_type") == "SENSITIVITY_EX_GOVERNMENT_FUNDING"
            ):
                self.sensitivity_records += 1
            # DEMO-KNOWN-ISSUES A1, re-measured on this run rather than quoted from memory.
            if fact.get("raw_unit") == "MONEY" and "百分点" in str(
                fact.get("source_span_text") or ""
            ):
                self.extraction_suspects += 1
            if fact.get("reconciliation_check"):
                self.reconciliations.append((fact_id, fact["reconciliation_check"]))
            if fact_id in needed:
                self.facts[fact_id] = fact

        extra = set(gov_funding)
        for fact_id, check in self.reconciliations:
            extra.add(fact_id)
            extra.update(str(item) for item in check.get("input_fact_ids") or [])
        extra -= set(self.facts)
        if extra:
            for fact in iter_jsonl(RUN_DIR / "normalized-facts.jsonl"):
                fact_id = str(fact.get("fact_id"))
                if fact_id in extra:
                    self.facts[fact_id] = fact
        self.government_funding_facts = sorted(gov_funding)

    def material_of(self, record: dict[str, Any], fact: dict[str, Any]) -> dict[str, Any]:
        material_id = str(record.get("material_id") or fact.get("material_id"))
        return self.materials.get(material_id, {"material_id": material_id})


# ---------------------------------------------------------------------------
# FULL_REPORT
# ---------------------------------------------------------------------------


def dimension_evidence_tables(
    world: RunArtifacts, report: Report, finding: dict[str, Any], validation: dict[str, Any]
) -> None:
    dimension_id = str(finding["dimension_id"])
    numeric_rows: list[dict[str, str]] = []
    text_rows: list[dict[str, str]] = []
    for evidence_id in cited_evidence_ids(finding):
        record = world.candidates.get(evidence_id)
        if record is None:
            validation["traceability"]["unresolved"].append(
                {"evidence_id": evidence_id, "reason": "NOT_IN_CANDIDATE_SET"}
            )
            continue
        governed = world.governed.get(evidence_id, {})
        # FR-072: quarantined data may never support a finding, so it never gets a row
        # here. It is named in section 9 instead.
        if governed.get("evidence_status") == "QUARANTINED":
            validation["conflict_and_quarantine"]["quarantined_in_evidence_tables"] += 1
            continue
        fact = world.facts.get(str(record["fact_id"]))
        if fact is None:
            validation["traceability"]["unresolved"].append(
                {"evidence_id": evidence_id, "reason": "FACT_NOT_FOUND"}
            )
            continue
        material = world.material_of(record, fact)
        validation["traceability"]["rows_checked"] += 1
        if not material.get("material_id") or not (
            record.get("chunk_id") or fact.get("chunk_id")
        ):
            validation["traceability"]["unresolved"].append(
                {"evidence_id": evidence_id, "reason": "CHAIN_INCOMPLETE"}
            )
        if record.get("record_kind") == "NUMERIC_OBSERVATION":
            numeric_rows.append(numeric_row(record, fact, material, governed))
        else:
            text_rows.append(text_row(record, fact, material, governed))

    counts = validation["evidence_tables"].setdefault(dimension_id, {})
    counts["numeric_rows"] = len(numeric_rows)
    counts["text_rows"] = len(text_rows)

    rules = world.report_rules
    report.data(f"**{dimension_id} 数值证据表**（本维度所有数字的唯一出处）")
    report.data("")
    evidence_table(report, rules["evidence_table_columns"], numeric_rows)
    report.data(f"**{dimension_id} 文本证据表**（原文跨度按 Ticket 05 规则未删减保留）")
    report.data("")
    evidence_table(report, rules["text_evidence_table_columns"], text_rows)


def render_dimension(
    world: RunArtifacts, report: Report, finding: dict[str, Any], validation: dict[str, Any]
) -> None:
    dimension_id = str(finding["dimension_id"])
    omitted = validation["narrative_numeric_sanitization"]["omitted_sentences"]
    notice = world.report_rules["omission_notice"]
    terminators = world.report_rules["narrative_sentence_terminators"]

    def prose(value: Any, field_path: str) -> None:
        kept, dropped = report.sanitized(value, dimension_id, field_path, terminators)
        omitted.extend(dropped)
        report.narrative(f"{kept}{notice if dropped else ''}")

    report.heading(4, f"{dimension_id} — {finding.get('finding')}")
    report.table(
        ["finding", "evidence_score", "evidence_score_label", "finding_reason_code",
         "generation_attempts", "bearing_metric_whitelist", "revised_from_challenge_ids"],
        [[
            cell(finding.get("finding")),
            cell(finding.get("evidence_score")),
            cell(finding.get("evidence_score_label")),
            cell(finding.get("finding_reason_code")),
            cell(finding.get("generation_attempts")),
            cell(finding.get("bearing_metric_whitelist")),
            cell(finding.get("revised_from_challenge_ids")),
        ]],
    )
    prose(finding.get("finding_statement") or "", "findings[].finding_statement")

    for field, path in (
        ("supporting_evidence", "findings[].supporting_evidence[].note"),
        ("counter_evidence", "findings[].counter_evidence[].note"),
    ):
        items = finding.get(field) or []
        if not items:
            continue
        report.data(f"*{field}*")
        report.data("")
        for item in items:
            report.data(f"- `{item.get('evidence_id')}` role={cell(item.get('role'))}")
            prose(item.get("note") or "", path)
            if item.get("overlap_note"):
                prose(item["overlap_note"], path.replace("note", "overlap_note"))

    for field, path in (
        ("alternative_explanations", "findings[].alternative_explanations[]"),
        ("limitations", "findings[].limitations[]"),
        ("gaps", "findings[].gaps[]"),
    ):
        items = finding.get(field) or []
        if not items:
            continue
        report.data(f"*{field}*")
        report.data("")
        for item in items:
            prose(item, path)

    if finding.get("management_assertions"):
        report.data("*management_assertions*（来源观点，claim_type 见证据表）")
        report.data("")
        for item in finding["management_assertions"]:
            report.data(f"- `{item.get('evidence_id')}`")
            prose(item.get("statement") or "",
                  "findings[].management_assertions[].statement")

    if finding.get("watch_indicators"):
        report.data("*watch_indicators*")
        report.data("")
        rows = []
        for item in finding["watch_indicators"]:
            kept_indicator, dropped = report.sanitized(
                item.get("indicator") or "", dimension_id,
                "findings[].watch_indicators[].indicator", terminators
            )
            omitted.extend(dropped)
            rows.append([
                cell(kept_indicator or notice),
                cell(item.get("threshold")),
                cell(item.get("threshold_basis")),
                cell(item.get("basis_evidence_id")),
                cell(item.get("proposed_threshold")),
            ])
            prose(item.get("judgment_logic") or "",
                  "findings[].watch_indicators[].judgment_logic")
        report.table(
            ["indicator", "threshold", "threshold_basis", "basis_evidence_id",
             "proposed_threshold"],
            rows,
        )

    dimension_evidence_tables(world, report, finding, validation)


def render_full_report(world: RunArtifacts, report: Report, validation: dict[str, Any]) -> None:
    rules = world.report_rules
    case = world.case
    gate = world.gate
    findings = {str(item["dimension_id"]): item for item in world.revised.get("findings") or []}

    report.heading(1, "中芯国际单股票投研 Demo 内部报告")
    report.data(
        "> 本报告为内部演示产物，`distribution_status=INTERNAL_DEMO_ONLY`，"
        "`human_review_status=PENDING_HUMAN_REVIEW`，不构成任何投资建议。"
    )
    report.data("")

    # --- three separated metadata blocks (ticket item 3) -------------------
    report.heading(2, "研究问题")
    report.data(f"> {case.get('research_question')}")
    report.data("")
    report.table(
        ["case_origin", "company", "security", "as_of", "来源"],
        [[
            cell(case.get("case_origin")),
            cell((case.get("company") or {}).get("legal_name_zh")),
            cell((case.get("security") or {}).get("code")),
            cell(case.get("as_of")),
            "single-stock-demo-v3/case.yaml",
        ]],
    )
    report.data("**范围识别**（确定性规则，不使用模型判断）")
    report.data("")
    scope_rows = []
    for example in rules["scope_recognition"]["examples"]:
        question = (
            str(case.get("research_question"))
            if example.get("use_case_research_question")
            else str(example["question"])
        )
        verdict = classify_question(
            question, rules, world.analysis_rules["forbidden_investment_terms"]
        )
        refused = verdict["action"] == "REFUSE"
        validation["scope_recognition"]["examples"].append(
            {
                "id": example["id"],
                "label": verdict["label"],
                "action": verdict["action"],
                # A refused question is not repeated: repeating it would put the forbidden
                # wording back into the report the rule exists to keep it out of.
                "reproduced_in_report": not refused,
            }
        )
        scope_rows.append([
            cell(example["id"]),
            "（命中禁止输出词表，问题原文不复述）" if refused else cell(question),
            cell(verdict["label"]),
            cell(verdict["action"]),
        ])
    report.table(["id", "问题", "label", "action"], scope_rows)
    report.note(rules["scope_recognition"]["out_of_scope_notice"])
    report.note(rules["scope_recognition"]["refusal_notice"])

    report.heading(2, "分析框架")
    report.table(
        ["dimension_id", "bearing_metric_whitelist", "finding", "evidence_score"],
        [[
            cell(dimension_id),
            cell(world.analysis_rules["bearing_metric_whitelist"].get(dimension_id) or []),
            cell((findings.get(dimension_id) or {}).get("finding")),
            cell((findings.get(dimension_id) or {}).get("evidence_score")),
        ] for dimension_id in world.analysis_rules["dimensions"]],
    )
    report.data("来源：`rules/analysis.yaml`。评分口径见第十章术语对照表。")
    report.data("")

    report.heading(2, "流程状态")
    statuses = gate.get("stage_statuses") or {}
    report.table(
        ["项", "值"],
        [
            ["retrieval_status", cell(statuses.get("retrieval_status"))],
            ["normalization_run_status", cell(statuses.get("normalization_run_status"))],
            ["validation_status", cell(statuses.get("validation_status"))],
            ["analysis_run_status", cell(statuses.get("analysis_run_status"))],
            ["challenge_run_status", cell(statuses.get("challenge_run_status"))],
            ["governance_status", cell(gate.get("governance_status"))],
            ["execution_mode", cell(gate.get("execution_mode"))],
            ["report_form", cell(gate.get("report_form"))],
            ["distribution_status", cell(gate.get("distribution_status"))],
            ["human_review_status", cell(gate.get("human_review_status"))],
        ],
    )
    report.note(
        "governance_status 只由检索、规整与证据治理三个状态按最坏值合成；分析与质询状态属于"
        "另一条概念轴，不并入其中，在上表中原样并列展示。"
    )

    sections = {section["id"]: section for section in rules["sections"]}
    dimension_map = rules["section_dimensions"]

    # --- S1 ---------------------------------------------------------------
    report.heading(2, f"一、{sections['S1']['title']}")
    report.table(
        ["项", "值"],
        [
            ["snapshot_id", cell(world.revised.get("snapshot_id"))],
            ["as_of", cell(case.get("as_of"))],
            ["governance_status", cell(gate.get("governance_status"))],
            ["distribution_status", cell(gate.get("distribution_status"))],
            ["human_review_status", cell(gate.get("human_review_status"))],
            ["execution_mode", cell(gate.get("execution_mode"))],
            ["analysis_rule_version", cell(world.revised.get("analysis_rule_version"))],
            ["context_rule_version", cell(world.revised.get("context_rule_version"))],
            ["report_rule_version", cell(rules["rule_version"])],
            ["overall_score", cell(world.revised.get("overall_score"))],
        ],
    )
    if gate.get("governance_status") == "FAIL":
        report.note(
            "**治理状态为 FAIL**：受影响数据不得支撑任何研究发现，本报告中相关维度的方向"
            "一律按 UNKNOWN 阅读。"
        )

    # --- S2 ---------------------------------------------------------------
    report.heading(2, f"二、{sections['S2']['title']}")
    targets: Counter[str] = Counter()
    for material in world.materials.values():
        for target in material.get("acquisition_targets") or []:
            targets[str(target)] += 1
    report.table(
        ["required_coverage", "已取得材料数"],
        [[cell(item), cell(targets.get(str(item), 0))]
         for item in case.get("required_coverage") or []],
    )
    status_counts = Counter(
        str(record.get("evidence_status")) for record in world.governed.values()
    )
    tier_counts = Counter(str(record.get("source_tier")) for record in world.governed.values())
    report.table(
        ["统计项", "值"],
        [
            ["材料数", cell(len(world.materials))],
            ["同源组数", cell(len({str(r.get("source_group_id")) for r in world.governed.values()}))],
            ["证据总数", cell(len(world.governed))],
            *[[f"evidence_status={key}", cell(value)]
              for key, value in sorted(status_counts.items())],
            *[[f"source_tier={key}", cell(value)] for key, value in sorted(tier_counts.items())],
            *[[f"record_kind={key}", cell(value)]
              for key, value in sorted(world.record_kinds.items())],
        ],
    )
    report.note(
        "同源转载不增加独立证据：同一次原始披露的多个入口共享一个 source_group_id，"
        "证据分只按独立同源组计。"
    )

    # --- S3..S6 -----------------------------------------------------------
    for section_id, title_index in (("S3", "三"), ("S4", "四"), ("S5", "五"), ("S6", "六")):
        report.heading(2, f"{title_index}、{sections[section_id]['title']}")
        for dimension_id in dimension_map[section_id]:
            finding = findings.get(dimension_id)
            if finding is None:
                continue
            render_dimension(world, report, finding, validation)
        if section_id == "S5":
            render_government_funding(world, report, validation)

    # --- S7 ---------------------------------------------------------------
    report.heading(2, f"七、{sections['S7']['title']}")
    report.table(
        ["dimension_id", "finding", "evidence_score", "evidence_score_label",
         "support_count", "numeric_support_count", "independent_source_groups",
         "bearing_cross_period_metrics", "finding_reason_code"],
        [[
            cell(item.get("dimension_id")),
            cell(item.get("finding")),
            cell(item.get("evidence_score")),
            cell(item.get("evidence_score_label")),
            cell((item.get("evidence_score_basis") or {}).get("support_count")),
            cell((item.get("evidence_score_basis") or {}).get("numeric_support_count")),
            cell(len((item.get("evidence_score_basis") or {}).get("source_group_ids") or [])),
            cell((item.get("evidence_score_basis") or {}).get("bearing_cross_period_metrics")),
            cell(item.get("finding_reason_code")),
        ] for item in world.revised.get("findings") or []],
    )
    report.note(
        "证据分表示证据强度，不表示公司质量，也不表示投资吸引力；总分固定为不适用。"
    )
    cross = world.revised.get("cross_attribution") or []
    if cross:
        report.data("**跨维度重复承重**")
        report.data("")
        report.table(
            ["fact_id", "dimensions", "evidence_id"],
            sorted(
                [cell(entry.get("fact_id")), cell(item.get("dimension_id")),
                 cell(item.get("evidence_id"))]
                for entry in cross for item in entry.get("entries") or []
            ),
        )
        for entry in cross:
            for item in entry.get("entries") or []:
                kept, dropped = report.sanitized(
                    item.get("overlap_note") or "", str(item.get("dimension_id")),
                    "cross_attribution[].entries[].overlap_note",
                    rules["narrative_sentence_terminators"],
                )
                validation["narrative_numeric_sanitization"]["omitted_sentences"].extend(dropped)
                report.narrative(kept)

    # --- S8 ---------------------------------------------------------------
    report.heading(2, f"八、{sections['S8']['title']}")
    challenges = world.challenges.get("challenges") or []
    report.table(
        ["challenge_id", "round", "category", "target_kind", "target_id", "disposition",
         "review_count", "blocking_triggers"],
        [[
            cell(item.get("challenge_id")), cell(item.get("round")), cell(item.get("category")),
            cell(item.get("target_kind")), cell(item.get("target_id")),
            cell(item.get("disposition")), cell(item.get("review_count")),
            cell(item.get("blocking_triggers")),
        ] for item in challenges],
    )
    report.table(
        ["项", "值"],
        [
            ["max_rounds", cell(world.challenges.get("max_rounds"))],
            ["rounds_used", cell(world.challenges.get("rounds_used"))],
            ["challenge_run_status", cell(world.challenges.get("challenge_run_status"))],
        ],
    )
    original = {str(item["dimension_id"]): item for item in world.original.get("findings") or []}
    changed = [
        [cell(key), cell(value.get("finding")), cell(findings[key].get("finding")),
         cell(findings[key].get("evidence_score")),
         cell(findings[key].get("revised_from_challenge_ids"))]
        for key, value in sorted(original.items())
        if key in findings and value.get("finding") != findings[key].get("finding")
    ]
    report.data("**质询导致的方向变化**")
    report.data("")
    report.table(
        ["dimension_id", "finding_before", "finding_after", "evidence_score_after",
         "revised_from_challenge_ids"],
        changed or [[DASH] * 5],
    )
    for item in challenges:
        report.data(f"- `{item.get('challenge_id')}` → {cell(item.get('disposition'))}")
        for field, path in (("question", "challenges[].question"),
                            ("reason", "challenges[].reason")):
            kept, dropped = report.sanitized(
                item.get(field) or "", str(item.get("target_id")), path,
                rules["narrative_sentence_terminators"],
            )
            validation["narrative_numeric_sanitization"]["omitted_sentences"].extend(dropped)
            report.narrative(f"{kept}{rules['omission_notice'] if dropped else ''}")

    # --- S9 ---------------------------------------------------------------
    report.heading(2, f"九、{sections['S9']['title']}")
    render_conflicts_and_gaps(world, report, validation)

    # --- S10 --------------------------------------------------------------
    report.heading(2, f"十、{sections['S10']['title']}")
    render_appendix(world, report, validation)


def render_government_funding(world: RunArtifacts, report: Report, validation: dict[str, Any]) -> None:
    """Both bases, side by side -- including the one that has no values."""
    report.heading(3, "政府补助双口径")
    rows = []
    for fact_id in world.government_funding_facts:
        fact = world.facts.get(fact_id)
        if fact is None:
            continue
        governed = world.evidence_by_fact.get(fact_id, {})
        record = world.candidates.get(str(governed.get("evidence_id")), governed) or {}
        material = world.material_of(record or fact, fact)
        rows.append(numeric_row({**record, "evidence_id": governed.get("evidence_id"),
                                 "claim_type": governed.get("claim_type"),
                                 "chunk_id": fact.get("chunk_id")}, fact, material, governed))
    report.data("**报告口径**：来源披露的、已计入损益的政府资金记录。")
    report.data("")
    evidence_table(report, world.report_rules["evidence_table_columns"], rows)
    report.table(
        ["口径", "记录数"],
        [
            ["GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL（报告口径）", cell(len(rows))],
            ["SENSITIVITY_EX_GOVERNMENT_FUNDING（敏感性口径）",
             cell(world.sensitivity_records)],
        ],
    )
    validation["government_funding_dual_basis"] = {
        "reported_basis_records": len(rows),
        "sensitivity_records": world.sensitivity_records,
        "gap_id": None,
    }
    if world.sensitivity_records == 0:
        validation["government_funding_dual_basis"]["gap_id"] = (
            "GAP_REPORT_GOVERNMENT_FUNDING_SENSITIVITY_ABSENT"
        )
        report.note(
            "第二口径没有任何记录。政府资金记录存在，但无一满足「金额可分离、可追溯，且能证明"
            "已计入同期间同口径 profit from operations」的全部条件，因此固定公式不被触发，"
            "敏感性值保持 UNKNOWN。这里不硬算一个数：按会计规则，不可分离的金额被扣减出来的"
            "利润不是任何一种真实口径。该缺口已登记为 "
            "`GAP_REPORT_GOVERNMENT_FUNDING_SENSITIVITY_ABSENT`。"
        )


def render_conflicts_and_gaps(world: RunArtifacts, report: Report, validation: dict[str, Any]) -> None:
    quarantined = sorted(
        str(record["evidence_id"]) for record in world.governed.values()
        if record.get("evidence_status") == "QUARANTINED"
    )
    conflict_groups = {
        str(record.get("conflict_group_id"))
        for record in world.governed.values()
        if record.get("conflict_group_id")
    }
    unresolved_groups = {
        str(record.get("conflict_group_id"))
        for record in world.governed.values()
        if record.get("conflict_status") == "CONFLICT_UNRESOLVED" and record.get("conflict_group_id")
    }
    validation["conflict_and_quarantine"].update(
        {
            "quarantined_count": len(quarantined),
            "detected_conflict_groups": len(conflict_groups),
            "unresolved_conflict_groups": len(unresolved_groups),
        }
    )
    report.table(
        ["项", "值"],
        [
            ["quarantined_count", cell(len(quarantined))],
            ["detected_conflict_group_count", cell(len(conflict_groups))],
            ["unresolved_conflict_group_count", cell(len(unresolved_groups))],
        ],
    )
    if quarantined:
        report.data("**隔离证据**（不支撑任何发现，不进入任何维度证据表）")
        report.data("")
        report.table(
            ["evidence_id", "quarantine_reason_codes", "conflict_status", "gap_ids"],
            [[
                cell(evidence_id),
                cell(world.governed[evidence_id].get("quarantine_reason_codes")),
                cell(world.governed[evidence_id].get("conflict_status")),
                cell(world.governed[evidence_id].get("gap_ids")),
            ] for evidence_id in quarantined],
        )
    else:
        report.note(
            "本次运行没有任何被隔离的证据，也没有检出冲突组。这是 Snapshot v3 的真实承载力，"
            "不是机制缺席：隔离与冲突降级的机制由测试中的合成 fixtures 覆盖，此处如实记录零值。"
        )

    gaps = world.gaps.get("gaps") or []
    aggregate_kinds = set(world.report_rules["gap_aggregation"]["aggregate_only_gap_kinds"])
    grouped = Counter((str(gap.get("origin_stage")), str(gap.get("gap_kind"))) for gap in gaps)
    report.data("**gap 聚合（origin_stage × gap_kind）**")
    report.data("")
    report.table(
        ["origin_stage", "gap_kind", "条数"],
        [[cell(stage), cell(kind), cell(count)]
         for (stage, kind), count in sorted(grouped.items())],
    )
    priorities = Counter(str(gap.get("priority")) for gap in gaps)
    report.table(
        ["priority", "条数"],
        [[cell(key), cell(value)] for key, value in sorted(priorities.items())],
    )
    report.note(world.report_rules["gap_aggregation"]["priority_filter_note"])
    report.note(world.report_rules["gap_aggregation"]["aggregate_caption"])

    detailed = [gap for gap in gaps if str(gap.get("gap_kind")) not in aggregate_kinds]
    report.data("**逐条展开的 gap**（聚合类别之外的全部条目）")
    report.data("")
    report.table(
        ["gap_id", "origin_stage", "gap_kind", "priority", "status", "impact_objects"],
        [[
            cell(gap.get("gap_id")), cell(gap.get("origin_stage")), cell(gap.get("gap_kind")),
            cell(gap.get("priority")), cell(gap.get("status")), cell(gap.get("impact_objects")),
        ] for gap in sorted(detailed, key=lambda item: str(item.get("gap_id")))],
    )
    validation["gap_summary"] = {
        "total": len(gaps),
        "detailed": len(detailed),
        "aggregated": len(gaps) - len(detailed),
        "by_priority": dict(sorted(priorities.items())),
    }

    report.heading(3, "数据限制")
    for disclosure in world.report_rules["disclosures"]:
        report.heading(4, disclosure["title"])
        report.note(disclosure["text"])
        render_disclosure_data(
            world, report, str(disclosure["id"]), disclosure.get("related_gap_id")
        )


def render_disclosure_data(
    world: RunArtifacts, report: Report, disclosure_id: str, related_gap_id: str | None = None
) -> None:
    if disclosure_id == "EXTRACTION_SEMANTIC_ERROR":
        report.table(
            ["启发式筛查项", "值"],
            [
                ["数值事实总数", cell(world.numeric_total)],
                ["金额单位且原文含「个百分点」的记录数", cell(world.extraction_suspects)],
            ],
        )
    elif disclosure_id == "D3_PERIOD_MISLABEL":
        rows = []
        for finding in world.revised.get("findings") or []:
            if str(finding["dimension_id"]) != "D3_MIX_EFFECT":
                continue
            for item in finding.get("supporting_evidence") or []:
                record = world.candidates.get(str(item.get("evidence_id")))
                if record is None or record.get("record_kind") != "NUMERIC_OBSERVATION":
                    continue
                fact = world.facts.get(str(record["fact_id"])) or {}
                governed = world.governed.get(str(item["evidence_id"]), {})
                rows.append([
                    cell(item.get("evidence_id")), cell(record.get("metric_id")),
                    cell(period_of(fact)),
                    cell(sorted({*(fact.get("gap_ids") or []),
                                 *(governed.get("gap_ids") or [])})),
                    cell(related_gap_id),
                ])
        report.table(
            ["evidence_id", "metric_id", "period（链路原样，未改写）", "记录自带 gap_ids",
             "阶段层 gap（由报告规则接上）"],
            sorted(rows) or [[DASH] * 5],
        )


def render_appendix(world: RunArtifacts, report: Report, validation: dict[str, Any]) -> None:
    report.heading(3, "调节桥接公式与复算")
    rows = []
    checked = 0
    matched = 0
    unknown = 0
    mismatched: list[str] = []
    for fact_id, check in sorted(world.reconciliations):
        checked += 1
        status = str(check.get("reconciliation_status"))
        recomputed = recompute_bridge(world, check)
        if status == "UNKNOWN":
            unknown += 1
        elif recomputed is not None and str(check.get("recomputed_ifrs_target")) == str(recomputed):
            matched += 1
        elif status == "PASS":
            mismatched.append(fact_id)
        rows.append([
            cell(fact_id), cell(check.get("rule_id")), cell(check.get("direction")),
            cell(check.get("formula")), cell(check.get("input_fact_ids")),
            cell(check.get("recomputed_ifrs_target")),
            cell(recomputed if recomputed is not None else DASH),
            cell(check.get("source_reported_ifrs_target")), cell(check.get("difference")),
            cell(check.get("tolerance")), cell(status), cell(check.get("reason")),
        ])
    report.table(
        ["target_fact_id", "rule_id", "direction", "formula", "input_fact_ids",
         "recomputed（链路记录）", "recomputed（本报告复算）", "source_reported",
         "difference", "tolerance", "status", "reason"],
        rows or [[DASH] * 12],
    )
    report.note(
        "本 Demo 的规整链路上没有任何 DERIVATION 记录，因此这里展示的不是派生值，而是"
        "调节桥接的复算核验：每条都给出公式、输入事实、复算值、披露值、差异与状态。"
        "状态为 UNKNOWN 的条目是输入口径不匹配或披露精度缺失，按规则不猜测容差。"
    )
    validation["formula_recomputation"] = {
        "checked": checked,
        "recomputed_match": matched,
        "unknown": unknown,
        "mismatched": mismatched,
    }

    report.heading(3, "溯源链")
    report.note(
        "报告中每个数字都可沿 evidence_id → fact_id → chunk_id → material_id 逐级回查；"
        "上述四个标识符在证据表中原样出现，可直接检索本次运行目录内的权威文件。"
    )
    report.heading(3, "术语与口径对照表")
    for group, entries in world.report_rules["glossary"].items():
        report.data(f"**{group}**")
        report.data("")
        report.table(
            ["取值", "中文说明"],
            [[cell(key), cell(value)] for key, value in entries.items()],
        )
    report.note(
        "机器标识符与来源原文跨度一律原样保留、不翻译：翻译标识符会切断溯源，"
        "翻译来源原文等于制造一段没有出处的新文本。"
    )


def recompute_bridge(world: RunArtifacts, check: dict[str, Any]) -> str | None:
    """Recompute IFRS_TARGET = CAS_BASE + sum(ADJUSTMENT_DETAIL) from the input facts."""
    total = Decimal(0)
    try:
        for row in check.get("rows") or []:
            fact = world.facts.get(str(row.get("fact_id")))
            if fact is None:
                return None
            if row.get("row_role") == "BASE":
                total += Decimal(str(fact["base_unit_value"]))
            elif row.get("row_role") == "ADJUSTMENT_DETAIL":
                amount = row.get("normalized_signed_amount")
                if amount is None:
                    return None
                total += Decimal(str(amount))
    except (InvalidOperation, KeyError, TypeError):
        return None
    return str(total)


# ---------------------------------------------------------------------------
# DIAGNOSTIC_ONLY
# ---------------------------------------------------------------------------


def render_diagnostic_report(world: RunArtifacts, report: Report) -> None:
    integrity = world.integrity
    report.heading(1, "完整性失败：内部诊断报告")
    report.data("> **本次黄金案例运行因完整性失败停止。**")
    report.data(
        "> 输入不可信，因此本文件不包含任何研究发现、方向、证据分或证据表；"
        "`distribution_status=INTERNAL_DEMO_ONLY`，`human_review_status=PENDING_HUMAN_REVIEW`。"
    )
    report.data("")
    report.heading(2, "失败原因")
    # Reason codes come from run-integrity.yaml first: on the documented failure path a
    # failed preflight has already deleted run-gate.yaml, so reading only the gate would
    # blank out this table on exactly the run it exists for.
    codes = sorted(
        {*(integrity.get("reason_codes") or []), *(world.gate.get("reason_codes") or [])}
    )
    report.table(["reason_code"], [[cell(code)] for code in codes] or [[DASH]])
    report.heading(2, "失败诊断")
    report.table(
        ["check", "status", "reason_code"],
        [[cell(item.get("name")), cell(item.get("status")), cell(item.get("reason_code"))]
         for item in integrity.get("checks") or [] if item.get("status") != "PASS"]
        or [[DASH] * 3],
    )
    report.table(
        ["项", "值"],
        [
            ["integrity_status", cell(integrity.get("integrity_status"))],
            ["execution_mode", cell(integrity.get("execution_mode"))],
            ["unexpected_files", cell(integrity.get("unexpected_files"))],
            ["as_of_violations", cell(integrity.get("as_of_violations"))],
        ],
    )
    report.heading(2, "gap 引用")
    report.table(
        ["gap_id"],
        [[cell(gap.get("gap_id"))] for gap in integrity.get("gaps") or []] or [[DASH]],
    )
    report.note(
        "完整性检查发生在消费任何输入之前，此时尚无产出，停止的代价为零。"
        "带结论的报告在此处输出会产生一份自我矛盾的文件：声明自己不可信，却通篇陈述发现。"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def append_gap(gap_id: str) -> None:
    path = RUN_DIR / "gaps.yaml"
    document = read_yaml(path)
    gaps = document.get("gaps") or []
    if any(str(gap.get("gap_id")) == gap_id for gap in gaps):
        return
    gaps.append(
        {
            "gap_id": gap_id,
            "origin_stage": "generate-research-report",
            "gap_kind": "SENSITIVITY_NOT_GENERATED",
            "question": (
                "政府补助第二口径（剔除政府资金的敏感性营业利润/率）没有任何记录："
                "已计入损益的政府资金记录存在，但无一被证明可分离且已计入同口径 "
                "profit from operations。"
            ),
            "impact_objects": ["D6_NONCORE_EXPLANATION", "SENSITIVITY_EX_GOVERNMENT_FUNDING"],
            "current_handling": "报告如实展示第二口径为零并说明原因，不硬算敏感性值。",
            "confirmation_owner": "user/research_owner",
            "required_evidence": (
                "as_of 前材料中可分离、可追溯，且能证明已计入同期间同口径 profit from "
                "operations 的政府资金金额。"
            ),
            "priority": "P2",
            "status": "OPEN",
        }
    )
    document["gaps"] = gaps
    write_yaml(path, document)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render report.md and report-validation.yaml for the fixed SMIC golden case. "
            "Takes no arguments: the run directory is a hard-coded constant and the report "
            "form is read from run-gate.yaml, not chosen here."
        )
    )
    return parser.parse_args()


def main() -> int:
    parse_args()
    try:
        world = RunArtifacts()
        rules = world.report_rules
        report_form = str(world.gate.get("report_form") or "DIAGNOSTIC_ONLY")
        report = Report()
        validation: dict[str, Any] = {
            "snapshot_id": world.gate.get("snapshot_id"),
            "report_rule_version": rules["rule_version"],
            "report_form": report_form,
            "execution_mode": world.gate.get("execution_mode"),
            "narrative_numeric_sanitization": {
                "scanned_field_paths": rules["narrative_scan_field_paths"],
                "scanned_fields": len(rules["narrative_scan_field_paths"]),
                "detected_mentions": 0,
                "omitted_sentences": [],
                "leaked_unbound_numeric_mentions": 0,
                "status": "PASS",
            },
            "evidence_tables": {},
            "traceability": {"rows_checked": 0, "unresolved": []},
            "conflict_and_quarantine": {"quarantined_in_evidence_tables": 0},
            "scope_recognition": {"examples": []},
            "forbidden_output_scan": {"terms_checked": 0, "hits": []},
            "prohibited_external_artifacts": {
                "pdf": "NOT_GENERATED", "html": "NOT_GENERATED",
                "dashboard": "NOT_GENERATED", "api": "NOT_GENERATED",
            },
        }

        if report_form == "FULL_REPORT":
            world.load_full()
            # Registered before rendering, so the gap tables the report prints already
            # include it and a second clean replay renders byte-identical output.
            if world.sensitivity_records == 0:
                append_gap("GAP_REPORT_GOVERNMENT_FUNDING_SENSITIVITY_ABSENT")
                world.gaps = read_yaml(RUN_DIR / "gaps.yaml")
            render_full_report(world, report, validation)
        else:
            render_diagnostic_report(world, report)

        text = report.render()
        (RUN_DIR / "report.md").write_text(text, encoding="utf-8")

        sanitization = validation["narrative_numeric_sanitization"]
        sanitization["detected_mentions"] = sum(
            len(item["matched_numeric_tokens"]) for item in sanitization["omitted_sentences"]
        )
        # The gate that matters. It starts from the rendered file, not from the strings the
        # sanitizer already cleaned -- scanning those would only ever prove that the
        # sanitizer returns what it returns, and would miss a number arriving in the report
        # through any other path.
        leaked = scan_rendered_report(text, report.fixed)
        sanitization["leaked_unbound_numeric_mentions"] = sum(
            len(NUMERIC_TOKEN.findall(line)) for line in leaked
        )
        sanitization["leaked_samples"] = leaked[:5]
        sanitization["scanned_prose_blocks"] = len(report.prose)
        # Fixed explanatory text from rules/report.yaml is exempted by exact match only: a
        # line escapes the gate solely by being one of these version-controlled constants,
        # whose digits are identifiers (FR-073, T1, D3) rather than research values.
        sanitization["fixed_text_blocks"] = len(report.fixed)
        declared = set(rules["narrative_scan_field_paths"])
        sanitization["declared_paths_match_render_sites"] = declared == RENDER_SITE_FIELD_PATHS
        sanitization["declared_paths_without_render_site"] = sorted(
            declared - RENDER_SITE_FIELD_PATHS
        )
        # Observational, not a gate: whether a path is exercised depends on the data.
        sanitization["field_paths_exercised_this_run"] = sorted(report.scanned_field_paths)
        sanitization["status"] = (
            "PASS"
            if not leaked and sanitization["declared_paths_match_render_sites"]
            else "FAIL"
        )

        forbidden = world.analysis_rules["forbidden_investment_terms"]
        validation["forbidden_output_scan"] = {
            "terms_checked": len(forbidden),
            "hits": sorted(term for term in forbidden if str(term).lower() in text.lower()),
        }
        validation["report_validation_status"] = (
            "FAIL"
            if sanitization["status"] == "FAIL"
            or validation["forbidden_output_scan"]["hits"]
            or validation["traceability"]["unresolved"]
            else "PASS"
        )
        write_yaml(RUN_DIR / "report-validation.yaml", validation)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
