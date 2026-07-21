"""Analyze and score D1-D7 research findings for the fixed SMIC Snapshot v3.

Ticket 05 cannot be a single deterministic script: deciding whether a paragraph supports
a utilization proposition is a semantic judgment. ADR 0004 therefore splits this stage
into three layers, two of which live here:

  select    deterministic, hashable selection of each dimension's closed candidate set
  finalize  deterministic validation of the frozen model judgment, plus every derived
            field (evidence_score, overall_score, reason codes, cross-attribution)

The middle layer -- one bounded model call per dimension -- happens between the two
subcommands and is frozen into a file. The model never emits a score, never emits an
aggregate, and never sees evidence outside its dimension's candidate set.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

SNAPSHOT_ID = "smic-a283e95e2c9e8068"
RULE_VERSION = "smic-v3-analysis-v1"
ORIGIN_STAGE = "analyze-and-score-research-findings"

# The frozen bearing metric whitelist from ticket 05 comment section 3, duplicated here
# on purpose: frozen_rule_binding compares the rules file against this constant item by
# item. Loosening the rules file to make an empty dimension look load-bearing is the
# worst available failure mode, so it is a hard gate rather than a prose constraint.
FROZEN_BEARING_WHITELIST: dict[str, list[str]] = {
    "D1_PROFITABILITY_CHANGE": [
        "GROSS_MARGIN",
        "GROSS_PROFIT",
        "PROFIT_FROM_OPERATIONS",
        "PROFIT_ATTRIBUTABLE_TO_OWNERS",
        "REVENUE",
        "COST_OF_SALES",
    ],
    "D2_UTILIZATION_EFFECT": [],
    "D3_MIX_EFFECT": ["ASP_SOURCE_REPORTED"],
    "D4_CAPEX_CONVERSION": ["CAPITAL_EXPENDITURE_INCURRED", "DEPRECIATION_EXPENSE"],
    "D5_CYCLE_EXPLANATION": [],
    "D6_NONCORE_EXPLANATION": [
        "GOVERNMENT_FUNDING_RECOGNIZED_IN_PNL",
        "OTHER_OPERATING_INCOME",
    ],
    "D7_SUSTAINABILITY_EVIDENCE": [],
}

FINDING_VALUES = {"SUPPORTED", "MIXED", "NOT_SUPPORTED", "UNKNOWN"}
EVIDENCE_ROLES = {"PRIMARY_SUPPORT", "CONTEXT"}

# additionalProperties: false, expressed as fixed key sets. There is no recommendation,
# valuation, or composite-rating field anywhere in this schema, so cross-dimension
# arithmetic has nowhere to land.
FINDING_KEYS = {
    "dimension_id",
    "finding",
    "finding_statement",
    "supporting_evidence",
    "counter_evidence",
    "alternative_explanations",
    "limitations",
    "management_assertions",
    "gaps",
    "watch_indicators",
}
FINDING_REQUIRED_KEYS = {
    "dimension_id",
    "finding",
    "finding_statement",
    "supporting_evidence",
    "counter_evidence",
    "alternative_explanations",
    "limitations",
    "gaps",
}
SUPPORT_KEYS = {"evidence_id", "role", "note", "overlap_note"}
COUNTER_KEYS = {"evidence_id", "note"}
ASSERTION_KEYS = {"evidence_id", "statement"}
WATCH_KEYS = {
    "indicator",
    "judgment_logic",
    "threshold",
    "threshold_basis",
    "basis_evidence_id",
}

# Fields the scripts write onto a finding after the model output has been accepted.
# They are rejected in a model output and permitted once derived.
DERIVED_FINDING_KEYS = {
    "evidence_score",
    "evidence_score_label",
    "evidence_score_basis",
    "finding_reason_code",
    "generation_attempts",
    "bearing_metric_whitelist",
    "revised_from_challenge_ids",
}
DERIVED_ITEM_KEYS = {"fact_id", "proposed_threshold"}

# Model-authored prose that the forbidden-output and causal checks read.
PROSE_FIELDS = ("finding_statement",)
PROSE_LIST_FIELDS = ("alternative_explanations", "limitations", "gaps")

SENTENCE_SEPARATORS = "。！？；\n.!?;"


# ---------------------------------------------------------------------------
# Shared IO / hashing helpers (kept identical in spirit to the Ticket 03/04 scripts).
# ---------------------------------------------------------------------------
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


def canonical_hash(value: Any) -> str:
    return sha256_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def resolve_snapshot_path(snapshot_dir: Path, relative_path: str) -> Path:
    root = snapshot_dir.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"snapshot path escapes input directory: {relative_path}") from error
    return candidate


def require_output_outside_snapshot(snapshot_dir: Path, output_dir: Path) -> None:
    snapshot_root = snapshot_dir.resolve()
    output_root = output_dir.resolve()
    try:
        output_root.relative_to(snapshot_root)
    except ValueError:
        return
    raise ValueError("output directory must remain outside the frozen snapshot")


def verify_snapshot(snapshot_dir: Path) -> dict[str, Any]:
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
    return manifest


def load_rules(rules_file: Path) -> dict[str, Any]:
    rules = yaml.safe_load(rules_file.read_text(encoding="utf-8"))
    if rules.get("snapshot_id") not in {None, SNAPSHOT_ID}:
        raise ValueError("analysis rules are not bound to Snapshot v3")
    if rules.get("rule_version") != RULE_VERSION:
        raise ValueError(f"rule_version must be {RULE_VERSION}")
    return rules


# ---------------------------------------------------------------------------
# Selection layer.
# ---------------------------------------------------------------------------
def dimension_scores(chunk: dict[str, Any]) -> dict[str, float]:
    """Best retrieval score per query family for one chunk.

    query_family_id only means "this dimension's query retrieved it". It does not mean
    the chunk is fit to bear that dimension's finding (ADR 0004).
    """
    best: dict[str, float] = {}
    for hit in chunk.get("retrieval_hits") or []:
        family = hit.get("query_family_id")
        score = float(hit.get("score") or 0.0)
        if family is None:
            continue
        if family not in best or score > best[family]:
            best[family] = score
    return best


def candidate_evidence_row(
    fact: dict[str, Any], evidence: dict[str, Any], dimension_id: str, whitelist: set[str]
) -> dict[str, Any]:
    row = {
        "record_type": "CANDIDATE_EVIDENCE",
        "dimension_id": dimension_id,
        "evidence_id": evidence["evidence_id"],
        "fact_id": fact["fact_id"],
        "chunk_id": fact["chunk_id"],
        "material_id": fact["material_id"],
        "record_kind": fact.get("record_kind"),
        "claim_type": evidence.get("claim_type"),
        "source_tier": evidence.get("source_tier"),
        "source_group_id": evidence.get("source_group_id"),
        "evidence_status": evidence.get("evidence_status"),
        "conflict_status": evidence.get("conflict_status"),
        "source_span_text": fact.get("source_span_text"),
        "content_locator": fact.get("content_locator"),
    }
    if fact.get("record_kind") == "NUMERIC_OBSERVATION":
        metric_id = fact.get("metric_id")
        row.update(
            {
                "metric_id": metric_id,
                "normalized_value": fact.get("normalized_value"),
                "target_unit": fact.get("target_unit"),
                "target_currency": fact.get("target_currency"),
                "period_type": fact.get("period_type"),
                "period_start": fact.get("period_start"),
                "period_end": fact.get("period_end"),
                "accounting_standard": fact.get("accounting_standard"),
                "bearing_whitelisted": metric_id in whitelist,
            }
        )
    return row


def select_candidates(
    chunks: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    rules: dict[str, Any],
    context_rule_version: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build the closed per-dimension candidate set. Fully deterministic and hashable."""
    selection = rules["selection"]
    budget = int(selection["text_budget_chars"])
    ceiling = budget * float(selection["budget_overshoot_ratio"])
    max_chunks = int(selection["max_selected_chunks"])
    seed_groups = int(selection["seed_source_groups"])

    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    fact_by_id = {fact["fact_id"]: fact for fact in facts}
    usable = [row for row in evidence if row.get("evidence_status") == "USABLE"]

    text_by_chunk: dict[str, list[dict[str, Any]]] = defaultdict(list)
    numeric_by_chunk: dict[str, list[dict[str, Any]]] = defaultdict(list)
    group_by_chunk: dict[str, str] = {}
    for row in sorted(usable, key=lambda item: item["evidence_id"]):
        fact = fact_by_id.get(row["fact_id"])
        if fact is None or fact["chunk_id"] not in chunk_by_id:
            continue
        pair = {"fact": fact, "evidence": row}
        if fact.get("record_kind") == "NUMERIC_OBSERVATION":
            numeric_by_chunk[fact["chunk_id"]].append(pair)
        else:
            text_by_chunk[fact["chunk_id"]].append(pair)
        group_by_chunk.setdefault(fact["chunk_id"], row.get("source_group_id") or "")

    scores_by_chunk = {chunk["chunk_id"]: dimension_scores(chunk) for chunk in chunks}

    summary: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    for dimension_id in rules["dimensions"]:
        whitelist = set(rules["bearing_metric_whitelist"].get(dimension_id) or [])

        # Candidates carry at least one usable text proposition; a chunk with only
        # numerics contributes nothing to the text budget.
        candidates = [
            {
                "chunk_id": chunk_id,
                "score": scores[dimension_id],
                "source_group_id": group_by_chunk.get(chunk_id, ""),
                "chars": len(chunk_by_id[chunk_id].get("text") or ""),
            }
            for chunk_id, scores in scores_by_chunk.items()
            if dimension_id in scores and text_by_chunk.get(chunk_id)
        ]
        ordered = sorted(candidates, key=lambda item: (-item["score"], item["chunk_id"]))

        available_groups = {item["source_group_id"] for item in ordered}
        # Seed: the highest-scoring chunk of each of the top source groups, so a single
        # dominant document cannot own the whole candidate set.
        best_by_group: dict[str, dict[str, Any]] = {}
        for item in ordered:
            best_by_group.setdefault(item["source_group_id"], item)
        seeds = sorted(
            best_by_group.values(), key=lambda item: (-item["score"], item["chunk_id"])
        )[: min(seed_groups, len(best_by_group))]

        selected: list[dict[str, Any]] = list(seeds)
        selected_ids = {item["chunk_id"] for item in seeds}
        selected_chars = sum(item["chars"] for item in seeds)

        skipped: list[str] = []
        for index, item in enumerate(ordered):
            if item["chunk_id"] in selected_ids:
                continue
            if len(selected) >= max_chunks or selected_chars + item["chars"] > ceiling:
                # Stop at the budget instead of skipping ahead to shorter, lower-scoring
                # chunks: that would quietly stop meaning "the most relevant N".
                skipped = [
                    other["chunk_id"]
                    for other in ordered[index:]
                    if other["chunk_id"] not in selected_ids
                ]
                break
            selected.append(item)
            selected_ids.add(item["chunk_id"])
            selected_chars += item["chars"]

        selected = sorted(selected, key=lambda item: (-item["score"], item["chunk_id"]))
        for item in selected:
            chunk = chunk_by_id[item["chunk_id"]]
            rows.append(
                {
                    "record_type": "CANDIDATE_CHUNK",
                    "dimension_id": dimension_id,
                    "chunk_id": item["chunk_id"],
                    "score": item["score"],
                    "source_group_id": item["source_group_id"],
                    "material_id": chunk.get("material_id"),
                    "structure_type": chunk.get("structure_type"),
                    "content_locator": chunk.get("content_locator"),
                    "text": chunk.get("text"),
                }
            )

        text_pairs = [
            pair for item in selected for pair in text_by_chunk.get(item["chunk_id"], [])
        ]
        # Numeric evidence does not consume the text budget: every usable numeric the
        # dimension retrieved stays visible, deduplicated by fact_id.
        numeric_pairs = {
            pair["fact"]["fact_id"]: pair
            for chunk_id, scores in scores_by_chunk.items()
            if dimension_id in scores
            for pair in numeric_by_chunk.get(chunk_id, [])
        }
        evidence_rows = [
            candidate_evidence_row(pair["fact"], pair["evidence"], dimension_id, whitelist)
            for pair in [*text_pairs, *numeric_pairs.values()]
        ]
        rows.extend(sorted(evidence_rows, key=lambda row: str(row["evidence_id"])))

        summary[dimension_id] = {
            "candidate_chunks": len(ordered),
            "selected_chunks": len(selected),
            "selected_chars": selected_chars,
            "source_group_count": len({item["source_group_id"] for item in selected}),
            "available_source_group_count": len(available_groups),
            "min_selected_score": min((item["score"] for item in selected), default=None),
            "skipped_due_budget_count": len(skipped),
            "skipped_due_budget": skipped,
            "text_evidence_count": len(text_pairs),
            "numeric_evidence_count": len(numeric_pairs),
            "bearing_numeric_count": sum(
                1
                for pair in numeric_pairs.values()
                if pair["fact"].get("metric_id") in whitelist
            ),
        }

    header = {
        "record_type": "SELECTION_SUMMARY",
        "snapshot_id": SNAPSHOT_ID,
        "analysis_rule_version": RULE_VERSION,
        # Carried on the frozen record so finalize can assert the binding against what
        # actually governed the context, not against the rules file it just read.
        "context_rule_version": context_rule_version,
        "selection_hash_inputs": {
            "text_budget_chars": budget,
            "budget_overshoot_ratio": float(selection["budget_overshoot_ratio"]),
            "max_selected_chunks": max_chunks,
            "seed_source_groups": seed_groups,
        },
        "dimensions": summary,
    }
    return [header, *rows], [
        *build_bearing_capacity_gaps(rules),
        *build_selection_gaps(summary, rules),
    ]


def build_bearing_capacity_gaps(rules: dict[str, Any]) -> list[dict[str, Any]]:
    """One gap per dimension whose bearing metric whitelist is empty.

    Ticket 05 section 3 requires the consequence of an empty whitelist to be registered,
    not merely commented: without this, "this dimension can carry no numeric weight" would
    live only in prose and could be lost the next time the rules are edited.
    """
    notes = rules["bearing_metric_gap_notes"]
    gaps: list[dict[str, Any]] = []
    for dimension_id in rules["dimensions"]:
        if rules["bearing_metric_whitelist"].get(dimension_id):
            continue
        note = notes[dimension_id]
        gaps.append(
            {
                "gap_id": f"GAP_ANALYSIS_NO_BEARING_METRIC_{dimension_id}",
                "origin_stage": ORIGIN_STAGE,
                "gap_kind": "NO_BEARING_METRIC",
                "question": str(note["question"]).strip(),
                "impact_objects": [dimension_id],
                "current_handling": (
                    "Analyze the dimension on text evidence only and cap its score "
                    "accordingly; never widen the whitelist to make it look load-bearing."
                ),
                "confirmation_owner": "user/data_preparer",
                "required_evidence": str(note["required_evidence"]).strip(),
                "priority": "P2",
                "status": "OPEN",
            }
        )
    return gaps


def build_selection_gaps(
    summary: dict[str, Any], rules: dict[str, Any]
) -> list[dict[str, Any]]:
    """Only three situations are gaps. Per-chunk budget truncation is not one."""
    seed_groups = int(rules["selection"]["seed_source_groups"])
    gaps: list[dict[str, Any]] = []
    for dimension_id in rules["dimensions"]:
        stats = summary[dimension_id]
        reasons: list[str] = []
        expected_groups = min(seed_groups, stats["available_source_group_count"])
        if stats["source_group_count"] < expected_groups:
            reasons.append("SOURCE_GROUP_SEEDING_INCOMPLETE")
        if stats["text_evidence_count"] == 0:
            reasons.append("NO_USABLE_TEXT_EVIDENCE")
        if stats["text_evidence_count"] == 0 and stats["numeric_evidence_count"] == 0:
            reasons.append("NO_USABLE_EVIDENCE")
        if not reasons:
            continue
        gaps.append(
            {
                "gap_id": f"GAP_ANALYSIS_SELECTION_{dimension_id}",
                "origin_stage": ORIGIN_STAGE,
                "gap_kind": "ANALYSIS_CANDIDATE_SET_THIN",
                "question": (
                    f"{dimension_id} candidate set is incomplete: {', '.join(reasons)}."
                ),
                "impact_objects": [dimension_id],
                "current_handling": (
                    "Analyze the dimension on whatever usable evidence exists and disclose "
                    "the thin candidate set; never widen the frozen retrieval families to "
                    "make the dimension look better supported."
                ),
                "confirmation_owner": "user/data_preparer",
                "required_evidence": (
                    "Additional as_of-eligible material, or an upstream normalization fix "
                    "that turns restricted records into usable ones."
                ),
                "priority": "P2",
                "status": "OPEN",
            }
        )
    return gaps


# ---------------------------------------------------------------------------
# Finalize layer: schema and reference checks on one model-produced finding.
# ---------------------------------------------------------------------------
def sentences(text: str) -> list[str]:
    parts: list[str] = []
    current = ""
    for character in text:
        if character in SENTENCE_SEPARATORS:
            parts.append(current)
            current = ""
        else:
            current += character
    parts.append(current)
    return [part.strip() for part in parts if part.strip()]


def prose_of(finding: dict[str, Any]) -> list[tuple[str, str]]:
    """Every model-authored string, tagged with the field it came from."""
    items: list[tuple[str, str]] = []
    for field in PROSE_FIELDS:
        value = finding.get(field)
        if isinstance(value, str):
            items.append((field, value))
    for field in PROSE_LIST_FIELDS:
        for value in finding.get(field) or []:
            if isinstance(value, str):
                items.append((field, value))
    for field, key in (
        ("supporting_evidence", "note"),
        ("supporting_evidence", "overlap_note"),
        ("counter_evidence", "note"),
        ("management_assertions", "statement"),
    ):
        for item in finding.get(field) or []:
            if isinstance(item, dict) and isinstance(item.get(key), str):
                items.append((f"{field}.{key}", item[key]))
    for item in finding.get("watch_indicators") or []:
        if not isinstance(item, dict):
            continue
        for key in ("indicator", "judgment_logic"):
            if isinstance(item.get(key), str):
                items.append((f"watch_indicators.{key}", item[key]))
    return items


def check_schema(
    finding: dict[str, Any], dimension_id: str, derived: bool = False
) -> list[str]:
    allowed = FINDING_KEYS | DERIVED_FINDING_KEYS if derived else FINDING_KEYS
    item_extra = DERIVED_ITEM_KEYS if derived else set()
    errors: list[str] = []
    extra = set(finding) - allowed
    if extra:
        errors.append(f"SCHEMA_UNKNOWN_FIELDS:{','.join(sorted(extra))}")
    missing = FINDING_REQUIRED_KEYS - set(finding)
    if missing:
        errors.append(f"SCHEMA_MISSING_FIELDS:{','.join(sorted(missing))}")
    if finding.get("dimension_id") != dimension_id:
        errors.append("SCHEMA_DIMENSION_MISMATCH")
    if finding.get("finding") not in FINDING_VALUES:
        errors.append(f"SCHEMA_BAD_FINDING:{finding.get('finding')}")
    if not str(finding.get("finding_statement") or "").strip():
        errors.append("SCHEMA_EMPTY_STATEMENT")
    for field, keys in (
        ("supporting_evidence", SUPPORT_KEYS),
        ("counter_evidence", COUNTER_KEYS),
        ("management_assertions", ASSERTION_KEYS),
        ("watch_indicators", WATCH_KEYS),
    ):
        for item in finding.get(field) or []:
            if not isinstance(item, dict):
                errors.append(f"SCHEMA_BAD_ITEM:{field}")
                continue
            unknown = set(item) - keys - item_extra
            if unknown:
                errors.append(f"SCHEMA_UNKNOWN_FIELDS:{field}.{','.join(sorted(unknown))}")
    for item in finding.get("supporting_evidence") or []:
        if isinstance(item, dict) and item.get("role") not in EVIDENCE_ROLES:
            errors.append(f"SCHEMA_BAD_ROLE:{item.get('role')}")
    if (
        dimension_id == "D7_SUSTAINABILITY_EVIDENCE"
        and not finding.get("watch_indicators")
        and finding.get("finding_reason_code") != "ANALYSIS_VALIDATION_FAILED"
    ):
        errors.append("SCHEMA_D7_WATCH_INDICATORS_REQUIRED")
    return sorted(set(errors))


def referenced_ids(finding: dict[str, Any]) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for field in ("supporting_evidence", "counter_evidence", "management_assertions"):
        for item in finding.get(field) or []:
            if isinstance(item, dict) and item.get("evidence_id"):
                refs.append((field, str(item["evidence_id"])))
    for item in finding.get("watch_indicators") or []:
        if isinstance(item, dict) and item.get("basis_evidence_id"):
            refs.append(("watch_indicators", str(item["basis_evidence_id"])))
    return refs


def check_references(
    finding: dict[str, Any],
    candidates: dict[str, dict[str, Any]],
    all_candidates: dict[str, dict[str, Any]],
) -> list[str]:
    """Closure and usability. The candidate set is closed: nothing else may be cited."""
    errors: list[str] = []
    for field, evidence_id in referenced_ids(finding):
        record = candidates.get(evidence_id)
        if record is None:
            code = (
                "EVIDENCE_OUTSIDE_CANDIDATE_SET"
                if evidence_id in all_candidates
                else "EVIDENCE_UNKNOWN_ID"
            )
            errors.append(f"{code}:{field}:{evidence_id}")
        elif record.get("evidence_status") != "USABLE":
            errors.append(f"EVIDENCE_NOT_USABLE:{field}:{evidence_id}")
    return sorted(set(errors))


def forbidden_terms_in(text: str, rules: dict[str, Any]) -> list[str]:
    """Every forbidden investment term the text contains, in rule order."""
    lowered = text.lower()
    return [
        str(term)
        for term in rules["forbidden_investment_terms"]
        if str(term).lower() in lowered
    ]


def check_forbidden_terms(finding: dict[str, Any], rules: dict[str, Any]) -> list[str]:
    return sorted(
        {
            f"FORBIDDEN_INVESTMENT_TERM:{field}:{term}"
            for field, text in prose_of(finding)
            for term in forbidden_terms_in(text, rules)
        }
    )


def check_causal_attribution(finding: dict[str, Any], rules: dict[str, Any]) -> list[str]:
    """A causal claim needs a named source. Numbers prove correlation, not causation."""
    errors: list[str] = []
    markers = [str(marker).lower() for marker in rules["causal_markers"]]
    attributions = [str(marker).lower() for marker in rules["attribution_markers"]]
    for field, text in prose_of(finding):
        if field.startswith("management_assertions"):
            continue  # a named, sourced attribution by construction
        for sentence in sentences(text):
            lowered = sentence.lower()
            hit = next((marker for marker in markers if marker in lowered), None)
            if hit is None:
                continue
            if any(attribution in lowered for attribution in attributions):
                continue
            errors.append(f"UNATTRIBUTED_CAUSAL_CLAIM:{field}:{hit}")
    return sorted(set(errors))


def check_management_assertions(
    finding: dict[str, Any], candidates: dict[str, dict[str, Any]], rules: dict[str, Any]
) -> list[str]:
    assertion_types = set(rules["management_assertion_claim_types"])
    errors: list[str] = []
    for item in finding.get("supporting_evidence") or []:
        if not isinstance(item, dict):
            continue
        record = candidates.get(str(item.get("evidence_id")))
        if record and record.get("claim_type") in assertion_types:
            errors.append(f"MANAGEMENT_ASSERTION_AS_SUPPORT:{item.get('evidence_id')}")
    return sorted(set(errors))


def check_score_status_binding(
    finding: dict[str, Any], candidates: dict[str, dict[str, Any]], whitelist: set[str]
) -> list[str]:
    """Score 0 forces UNKNOWN. The reverse is deliberately free: conflicting or
    directionless evidence still leaves the direction unknown at 1-2."""
    score, _ = derive_evidence_score(finding, candidates, whitelist)
    if score == 0 and finding.get("finding") != "UNKNOWN":
        return ["SCORE_ZERO_REQUIRES_UNKNOWN"]
    return []


def validate_finding(
    finding: dict[str, Any],
    dimension_id: str,
    candidates: dict[str, dict[str, Any]],
    all_candidates: dict[str, dict[str, Any]],
    rules: dict[str, Any],
) -> list[str]:
    whitelist = set(rules["bearing_metric_whitelist"].get(dimension_id) or [])
    errors = check_schema(finding, dimension_id)
    errors += check_references(finding, candidates, all_candidates)
    errors += check_forbidden_terms(finding, rules)
    errors += check_causal_attribution(finding, rules)
    errors += check_management_assertions(finding, candidates, rules)
    errors += check_score_status_binding(finding, candidates, whitelist)
    return sorted(set(errors))


# ---------------------------------------------------------------------------
# Derived fields. None of these ever come from the model.
# ---------------------------------------------------------------------------
def derive_evidence_score(
    finding: dict[str, Any], candidates: dict[str, dict[str, Any]], whitelist: set[str]
) -> tuple[int, dict[str, Any]]:
    supports = [
        candidates[str(item["evidence_id"])]
        for item in finding.get("supporting_evidence") or []
        if isinstance(item, dict) and str(item.get("evidence_id")) in candidates
    ]
    numeric = [row for row in supports if row.get("record_kind") == "NUMERIC_OBSERVATION"]
    groups = sorted({str(row.get("source_group_id")) for row in supports})
    unresolved = any(row.get("conflict_status") == "CONFLICT_UNRESOLVED" for row in supports)

    periods_by_metric: dict[str, set[str]] = defaultdict(set)
    for row in numeric:
        if row.get("metric_id") and row.get("period_end"):
            periods_by_metric[str(row["metric_id"])].add(str(row["period_end"]))
    cross_period_metrics = sorted(
        metric for metric, periods in periods_by_metric.items() if len(periods) >= 2
    )
    bearing_cross_period = sorted(
        metric for metric in cross_period_metrics if metric in whitelist
    )

    if not supports:
        score = 0
    elif bearing_cross_period and len(groups) >= 2 and not unresolved:
        score = 3
    elif len(groups) >= 2 or cross_period_metrics:
        score = 2
    else:
        score = 1
    basis = {
        "support_count": len(supports),
        "numeric_support_count": len(numeric),
        "source_group_ids": groups,
        "cross_period_metrics": cross_period_metrics,
        "bearing_cross_period_metrics": bearing_cross_period,
        "has_unresolved_conflict": unresolved,
    }
    return score, basis


def apply_threshold_basis(finding: dict[str, Any], rules: dict[str, Any]) -> list[str]:
    """Keep unfounded thresholds visible instead of deleting them (ticket 05 section 7)."""
    accepted = {"SOURCE_DISCLOSED_THRESHOLD", "FROZEN_RECOMPUTABLE_FORMULA"}
    rejected: list[str] = []
    for item in finding.get("watch_indicators") or []:
        if not isinstance(item, dict):
            continue
        item.setdefault("basis_evidence_id", None)
        item.setdefault("proposed_threshold", None)
        threshold = item.get("threshold")
        basis = item.get("threshold_basis")
        if threshold in (None, "", "UNKNOWN", "TBD"):
            item["threshold"] = "UNKNOWN"
            if basis not in rules["threshold_basis_values"]:
                item["threshold_basis"] = "UNKNOWN"
            continue
        if basis in accepted and item.get("basis_evidence_id"):
            continue
        item["proposed_threshold"] = threshold
        item["threshold"] = "UNKNOWN"
        item["threshold_basis"] = "REJECTED_NO_BASIS"
        rejected.append(str(item.get("indicator")))
    return rejected


def forced_unknown_finding(dimension_id: str) -> dict[str, Any]:
    return {
        "dimension_id": dimension_id,
        "finding": "UNKNOWN",
        "finding_statement": (
            "该维度的模型判断两次均未通过确定性校验，按 ticket 05 第 8 节强制归零，"
            "不代表该维度无证据。"
        ),
        "supporting_evidence": [],
        "counter_evidence": [],
        "alternative_explanations": [],
        "limitations": [
            "Analysis validation failed twice; see analysis-attempts.jsonl for both "
            "model outputs and both error lists."
        ],
        "gaps": [f"GAP_ANALYSIS_VALIDATION_FAILED_{dimension_id}"],
        "management_assertions": [],
        "watch_indicators": [],
    }


def build_cross_attribution(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Report which facts bear weight in more than one dimension. It does not judge
    whether the same business change was double counted; it forces that to be stated."""
    by_fact: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        for item in finding.get("supporting_evidence") or []:
            if not isinstance(item, dict) or item.get("role") != "PRIMARY_SUPPORT":
                continue
            fact_id = item.get("fact_id")
            if not fact_id:
                continue
            by_fact[str(fact_id)].append(
                {
                    "dimension_id": finding["dimension_id"],
                    "evidence_id": item.get("evidence_id"),
                    "overlap_note": item.get("overlap_note"),
                }
            )
    return [
        {
            "fact_id": fact_id,
            "dimensions": sorted(entry["dimension_id"] for entry in entries),
            "entries": sorted(entries, key=lambda entry: str(entry["dimension_id"])),
        }
        for fact_id, entries in sorted(by_fact.items())
        if len({entry["dimension_id"] for entry in entries}) > 1
    ]


# ---------------------------------------------------------------------------
# Finalize orchestration.
# ---------------------------------------------------------------------------
def load_candidate_index(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, dict[str, Any]]], dict[str, dict[str, Any]]]:
    if not rows or rows[0].get("record_type") != "SELECTION_SUMMARY":
        raise ValueError("analysis inputs must start with the SELECTION_SUMMARY record")
    header = rows[0]
    if header.get("snapshot_id") != SNAPSHOT_ID:
        raise ValueError("analysis inputs are not bound to Snapshot v3")
    by_dimension: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    everything: dict[str, dict[str, Any]] = {}
    for row in rows[1:]:
        if row.get("record_type") != "CANDIDATE_EVIDENCE":
            continue
        by_dimension[str(row["dimension_id"])][str(row["evidence_id"])] = row
        everything[str(row["evidence_id"])] = row
    return header, by_dimension, everything


def resolve_findings(
    attempts: list[dict[str, Any]],
    by_dimension: dict[str, dict[str, dict[str, Any]]],
    everything: dict[str, dict[str, Any]],
    rules: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Take the first attempt that validates. At most max_attempts_per_dimension."""
    max_attempts = int(rules["generation"]["max_attempts_per_dimension"])
    accepted: list[dict[str, Any]] = []
    log: list[dict[str, Any]] = []
    for dimension_id in rules["dimensions"]:
        candidates = by_dimension.get(dimension_id, {})
        chosen: dict[str, Any] | None = None
        last_errors: list[str] = []
        used = 0
        for index, attempt in enumerate(attempts[:max_attempts]):
            finding = attempt.get(dimension_id)
            if finding is None:
                continue
            used = index + 1
            finding = json.loads(json.dumps(finding))  # never mutate the frozen input
            errors = validate_finding(finding, dimension_id, candidates, everything, rules)
            log.append(
                {
                    "dimension_id": dimension_id,
                    "attempt": used,
                    "accepted": not errors,
                    "errors": errors,
                    "model_output": finding,
                }
            )
            if not errors:
                chosen = finding
                break
            last_errors = errors
        if chosen is None:
            record = forced_unknown_finding(dimension_id)
            record["generation_attempts"] = used
            record["finding_reason_code"] = "ANALYSIS_VALIDATION_FAILED"
            accepted.append(record)
            continue
        chosen["generation_attempts"] = used
        accepted.append(chosen)
    return accepted, log


def enrich_findings(
    findings: list[dict[str, Any]],
    by_dimension: dict[str, dict[str, dict[str, Any]]],
    rules: dict[str, Any],
) -> list[str]:
    """Attach every derived field. Scores and reason codes are written here, not read."""
    labels = {int(key): value for key, value in rules["evidence_score_levels"].items()}
    rejected_thresholds: list[str] = []
    for finding in findings:
        dimension_id = str(finding["dimension_id"])
        candidates = by_dimension.get(dimension_id, {})
        whitelist = set(rules["bearing_metric_whitelist"].get(dimension_id) or [])
        for field in ("supporting_evidence", "counter_evidence", "management_assertions"):
            for item in finding.get(field) or []:
                if isinstance(item, dict):
                    record = candidates.get(str(item.get("evidence_id")))
                    item["fact_id"] = record.get("fact_id") if record else None
        rejected_thresholds.extend(
            f"{dimension_id}:{indicator}"
            for indicator in apply_threshold_basis(finding, rules)
        )
        score, basis = derive_evidence_score(finding, candidates, whitelist)
        finding["evidence_score"] = score
        finding["evidence_score_label"] = labels[score]
        finding["evidence_score_basis"] = basis
        finding.setdefault(
            "finding_reason_code",
            "NO_BEARING_EVIDENCE" if score == 0 else "MODEL_JUDGMENT",
        )
        finding["bearing_metric_whitelist"] = sorted(whitelist)
    return sorted(rejected_thresholds)


def run_validation(
    findings: list[dict[str, Any]],
    by_dimension: dict[str, dict[str, dict[str, Any]]],
    everything: dict[str, dict[str, Any]],
    cross_attribution: list[dict[str, Any]],
    rejected_thresholds: list[str],
    context_rule_version: str | None,
    rules: dict[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, status: str, reason: str, **details: Any) -> None:
        checks.append({"check": name, "status": status, "reason": reason, **details})

    by_id = {str(finding["dimension_id"]): finding for finding in findings}

    # 1. dimension_coverage
    expected = list(rules["dimensions"])
    actual = [str(finding["dimension_id"]) for finding in findings]
    add(
        "dimension_coverage",
        "PASS" if actual == expected else "FAIL",
        f"{len(actual)} findings emitted for {len(expected)} declared dimensions.",
        missing=sorted(set(expected) - set(actual)),
        unexpected=sorted(set(actual) - set(expected)),
    )

    # 2-4, 6-8. Re-run the per-finding checks over the final set.
    def tally(name: str, fn: Any) -> list[str]:
        hits: list[str] = []
        for finding in findings:
            dimension_id = str(finding["dimension_id"])
            hits.extend(
                f"{dimension_id}:{error}"
                for error in fn(finding, by_dimension.get(dimension_id, {}))
            )
        add(
            name,
            "FAIL" if hits else "PASS",
            f"{len(hits)} violations in the accepted findings.",
            violations=hits[:20],
            violation_count=len(hits),
        )
        return hits

    tally(
        "schema_conformance",
        lambda finding, _: check_schema(finding, str(finding["dimension_id"]), derived=True),
    )
    tally(
        "evidence_reference_legality",
        lambda finding, candidates: [
            error
            for error in check_references(finding, candidates, everything)
            if not error.startswith("EVIDENCE_OUTSIDE_CANDIDATE_SET")
        ],
    )
    tally(
        "candidate_set_closure",
        lambda finding, candidates: [
            error
            for error in check_references(finding, candidates, everything)
            if error.startswith("EVIDENCE_OUTSIDE_CANDIDATE_SET")
        ],
    )

    # 5. score_status_binding: score 0 forces UNKNOWN; the reverse is deliberately free.
    binding_errors = [
        f"{finding['dimension_id']}:SCORE_ZERO_REQUIRES_UNKNOWN"
        for finding in findings
        if finding.get("evidence_score") == 0 and finding.get("finding") != "UNKNOWN"
    ]
    binding_errors += [
        f"{finding['dimension_id']}:SCORE_OUT_OF_RANGE"
        for finding in findings
        if finding.get("evidence_score") not in {0, 1, 2, 3}
    ]
    add(
        "score_status_binding",
        "FAIL" if binding_errors else "PASS",
        f"{len(binding_errors)} findings violate the score/status binding.",
        violations=binding_errors,
    )

    tally("forbidden_output_terms", lambda finding, _: check_forbidden_terms(finding, rules))
    tally("causal_attribution", lambda finding, _: check_causal_attribution(finding, rules))
    tally(
        "management_assertion_placement",
        lambda finding, candidates: check_management_assertions(finding, candidates, rules),
    )

    # 9. cross_dimension_attribution
    missing_notes = [
        entry["fact_id"]
        for entry in cross_attribution
        if any(not item.get("overlap_note") for item in entry["entries"])
    ]
    add(
        "cross_dimension_attribution",
        "FAIL" if missing_notes else "PASS",
        f"{len(cross_attribution)} facts bear primary support in more than one dimension; "
        f"{len(missing_notes)} of them lack an overlap_note.",
        cross_dimension_fact_count=len(cross_attribution),
        missing_overlap_note=missing_notes,
    )

    # 10. d7_threshold_basis
    d7 = by_id.get("D7_SUSTAINABILITY_EVIDENCE", {})
    indicators = d7.get("watch_indicators") or []
    incomplete = [
        str(item.get("indicator"))
        for item in indicators
        if not str(item.get("judgment_logic") or "").strip()
        or item.get("threshold") in (None, "")
        or item.get("threshold_basis") not in rules["threshold_basis_values"]
    ]
    if incomplete:
        threshold_status = "FAIL"
    elif rejected_thresholds:
        threshold_status = "WARN"
    else:
        threshold_status = "PASS"
    add(
        "d7_threshold_basis",
        threshold_status,
        f"{len(indicators)} watch indicators; {len(rejected_thresholds)} numeric thresholds "
        "lacked a source-disclosed or recomputable basis and were kept as proposed_threshold.",
        indicator_count=len(indicators),
        rejected_thresholds=rejected_thresholds,
        incomplete_indicators=incomplete,
    )

    # 11. generation_attempts_bounded
    max_attempts = int(rules["generation"]["max_attempts_per_dimension"])
    over_budget = [
        str(finding["dimension_id"])
        for finding in findings
        if int(finding.get("generation_attempts") or 0) > max_attempts
    ]
    forced = [
        str(finding["dimension_id"])
        for finding in findings
        if finding.get("finding_reason_code") == "ANALYSIS_VALIDATION_FAILED"
    ]
    add(
        "generation_attempts_bounded",
        "FAIL" if forced or over_budget else "PASS",
        f"{len(forced)} dimensions were forced to UNKNOWN after {max_attempts} attempts; "
        f"{len(over_budget)} exceeded the attempt budget.",
        forced_dimensions=forced,
        over_budget_dimensions=over_budget,
    )

    # 12. frozen_rule_binding
    binding_issues: list[str] = []
    configured = rules["bearing_metric_whitelist"]
    for dimension_id, metrics in FROZEN_BEARING_WHITELIST.items():
        if sorted(configured.get(dimension_id) or []) != sorted(metrics):
            binding_issues.append(f"BEARING_WHITELIST_DRIFT:{dimension_id}")
    if sorted(configured) != sorted(FROZEN_BEARING_WHITELIST):
        binding_issues.append("BEARING_WHITELIST_DIMENSION_SET_DRIFT")
    required_context = rules["required_context_rule_version"]
    if context_rule_version != required_context:
        binding_issues.append(f"CONTEXT_RULE_VERSION:{context_rule_version}")
    add(
        "frozen_rule_binding",
        "FAIL" if binding_issues else "PASS",
        f"{len(binding_issues)} frozen-rule bindings drifted from ticket 05 section 3.",
        issues=binding_issues,
        required_context_rule_version=required_context,
    )

    declared = list(rules.get("validation_checks", []))
    emitted = [check["check"] for check in checks]
    if declared and emitted != declared:
        raise ValueError(
            "emitted validation checks do not match the declared validation_checks list"
        )
    return checks


def summarize_status(checks: list[dict[str, Any]], new_gaps: list[dict[str, Any]]) -> str:
    if any(check["status"] == "FAIL" for check in checks):
        return "FAIL"
    if any(check["status"] == "WARN" for check in checks) or new_gaps:
        return "WARN"
    return "PASS"


def build_summary(findings: list[dict[str, Any]], rules: dict[str, Any]) -> dict[str, Any]:
    """FR-051 report vector. overall_score is a written constant, not an aggregate."""
    by_id = {str(finding["dimension_id"]): finding for finding in findings}

    def entry(dimension_id: str) -> dict[str, Any]:
        finding = by_id.get(dimension_id, {})
        return {
            "dimension_id": dimension_id,
            "finding": finding.get("finding"),
            "evidence_score": finding.get("evidence_score"),
        }

    vector = rules["summary_vector"]
    return {
        "profitability_change": entry(vector["profitability_change"]),
        "sustainability_support": entry(vector["sustainability_support"]),
        "driver_attribution": [entry(item) for item in vector["driver_attribution"]],
        "alternative_explanations": [
            entry(item) for item in vector["alternative_explanations"]
        ],
        "overall_score": vector["overall_score"],
    }


def build_finalize_gaps(
    findings: list[dict[str, Any]], rejected_thresholds: list[str]
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for finding in findings:
        if finding.get("finding_reason_code") != "ANALYSIS_VALIDATION_FAILED":
            continue
        dimension_id = str(finding["dimension_id"])
        gaps.append(
            {
                "gap_id": f"GAP_ANALYSIS_VALIDATION_FAILED_{dimension_id}",
                "origin_stage": ORIGIN_STAGE,
                "gap_kind": "ANALYSIS_VALIDATION_FAILED",
                "question": (
                    f"{dimension_id} failed deterministic validation twice and was forced to "
                    "UNKNOWN with evidence_score 0."
                ),
                "impact_objects": [dimension_id],
                "current_handling": (
                    "Keep both model outputs and both error lists in analysis-attempts.jsonl; "
                    "the forced UNKNOWN carries finding_reason_code=ANALYSIS_VALIDATION_FAILED "
                    "so it is not read as an evidence shortage."
                ),
                "confirmation_owner": "user/data_preparer",
                "required_evidence": "A model judgment that satisfies the frozen validation.",
                "priority": "P1",
                "status": "OPEN",
            }
        )
    if rejected_thresholds:
        gaps.append(
            {
                "gap_id": "GAP_ANALYSIS_D7_THRESHOLD_NO_BASIS",
                "origin_stage": ORIGIN_STAGE,
                "gap_kind": "THRESHOLD_BASIS_MISSING",
                "question": (
                    f"{len(rejected_thresholds)} D7 numeric thresholds had no source-disclosed "
                    "threshold and no frozen recomputable formula."
                ),
                "impact_objects": ["D7_SUSTAINABILITY_EVIDENCE"],
                "rejected_thresholds": rejected_thresholds,
                "current_handling": (
                    "Keep the number as proposed_threshold, set threshold=UNKNOWN and "
                    "threshold_basis=REJECTED_NO_BASIS; never invent a threshold to make D7 "
                    "look complete."
                ),
                "confirmation_owner": "user/research_owner",
                "required_evidence": "A disclosed threshold or a recomputable formula from Ticket 04.",
                "priority": "P2",
                "status": "OPEN",
            }
        )
    return gaps


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------
def load_existing_gaps(path: Path) -> list[dict[str, Any]]:
    existing = yaml.safe_load(path.read_text(encoding="utf-8"))
    if existing.get("snapshot_id") != SNAPSHOT_ID:
        raise ValueError("existing gap registry is not bound to Snapshot v3")
    return list(existing.get("gaps") or [])


def load_model_attempts(paths: list[Path]) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for path in paths:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if document.get("snapshot_id") != SNAPSHOT_ID:
            raise ValueError(f"{path.name} is not bound to Snapshot v3")
        findings = document.get("findings") or []
        by_dimension: dict[str, Any] = {}
        for finding in findings:
            dimension_id = str(finding.get("dimension_id"))
            if dimension_id in by_dimension:
                raise ValueError(f"{path.name} repeats dimension {dimension_id}")
            by_dimension[dimension_id] = finding
        attempts.append(by_dimension)
    return attempts


def run_select(args: argparse.Namespace) -> None:
    require_output_outside_snapshot(args.snapshot_dir, args.output_dir)
    verify_snapshot(args.snapshot_dir)
    rules = load_rules(args.rules_file)

    chunks = read_jsonl(args.context_file)
    facts = read_jsonl(args.facts_file)
    evidence = read_jsonl(args.evidence_file)
    for rows, label in ((chunks, "context"), (facts, "fact"), (evidence, "evidence")):
        if any(row.get("snapshot_id") != SNAPSHOT_ID for row in rows):
            raise ValueError(f"every {label} record must carry the exact Snapshot v3 identity")
    versions = {str(chunk.get("query_rule_version")) for chunk in chunks}
    required = str(rules["required_context_rule_version"])
    if versions and versions != {required}:
        raise ValueError(f"context must be governed by {required}, found {sorted(versions)}")

    observed = sorted(versions)[0] if versions else required
    rows, gaps = select_candidates(chunks, facts, evidence, rules, observed)
    rebuilt, rebuilt_gaps = select_candidates(chunks, facts, evidence, rules, observed)
    if canonical_jsonl_hash(rows) != canonical_jsonl_hash(rebuilt) or canonical_hash(
        gaps
    ) != canonical_hash(rebuilt_gaps):
        raise ValueError("candidate selection is not deterministic")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "analysis-inputs.jsonl", rows)
    write_yaml(
        args.output_dir / "gaps.yaml",
        {
            "snapshot_id": SNAPSHOT_ID,
            "gaps": [*load_existing_gaps(args.existing_gaps_file), *gaps],
        },
    )


def build_prompt(
    dimension_id: str,
    rows: list[dict[str, Any]],
    rules: dict[str, Any],
) -> str:
    """Assemble one dimension's model prompt from the frozen candidate set.

    analysis-inputs.jsonl is the frozen record, not the prompt; the prompt is derived
    from it here so the model can never be handed evidence the selection layer excluded.
    """
    chunks = [
        row
        for row in rows
        if row.get("record_type") == "CANDIDATE_CHUNK" and row["dimension_id"] == dimension_id
    ]
    evidence = [
        row
        for row in rows
        if row.get("record_type") == "CANDIDATE_EVIDENCE"
        and row["dimension_id"] == dimension_id
    ]
    by_chunk: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in evidence:
        if row.get("record_kind") == "TEXT_PROPOSITION":
            by_chunk[str(row["chunk_id"])].append(row)
    numerics = [row for row in evidence if row.get("record_kind") == "NUMERIC_OBSERVATION"]
    whitelist = sorted(rules["bearing_metric_whitelist"].get(dimension_id) or [])

    lines = [
        f"# {dimension_id} candidate set",
        "",
        f"snapshot_id: {SNAPSHOT_ID}",
        f"bearing_metric_whitelist: {whitelist or 'EMPTY'}",
        "",
        "## Numeric evidence (USABLE)",
        "",
    ]
    if not numerics:
        lines.append("(none)")
    for row in sorted(numerics, key=lambda row: str(row["evidence_id"])):
        lines.append(
            f"- {row['evidence_id']} | {row.get('metric_id')} = {row.get('normalized_value')} "
            f"{row.get('target_unit')} {row.get('target_currency') or ''} | "
            f"{row.get('period_type')} {row.get('period_start')}..{row.get('period_end')} | "
            f"{row.get('accounting_standard')} | {row.get('source_group_id')} | "
            f"claim_type={row.get('claim_type')} | "
            f"bearing={'YES' if row.get('bearing_whitelisted') else 'NO'}"
        )
    lines += ["", "## Text evidence (USABLE), grouped by chunk", ""]
    for chunk in chunks:
        lines.append(
            f"### {chunk['chunk_id']} | score={chunk['score']} | "
            f"{chunk.get('material_id')} | {chunk.get('source_group_id')}"
        )
        for row in sorted(by_chunk.get(str(chunk["chunk_id"]), []), key=lambda r: str(r["evidence_id"])):
            text = " ".join(str(row.get("source_span_text") or "").split())
            lines.append(f"- {row['evidence_id']} | claim_type={row.get('claim_type')} | {text}")
        lines.append("")
    return "\n".join(lines)


def run_prompt(args: argparse.Namespace) -> None:
    rules = load_rules(args.rules_file)
    rows = read_jsonl(args.analysis_inputs)
    load_candidate_index(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for dimension_id in rules["dimensions"]:
        (args.output_dir / f"prompt-{dimension_id}.md").write_text(
            build_prompt(dimension_id, rows, rules), encoding="utf-8"
        )


def run_finalize(args: argparse.Namespace) -> None:
    rules = load_rules(args.rules_file)
    rows = read_jsonl(args.analysis_inputs)
    header, by_dimension, everything = load_candidate_index(rows)
    attempts = load_model_attempts(args.model_findings)

    findings, log = resolve_findings(attempts, by_dimension, everything, rules)
    rejected_thresholds = enrich_findings(findings, by_dimension, rules)
    cross_attribution = build_cross_attribution(findings)
    checks = run_validation(
        findings,
        by_dimension,
        everything,
        cross_attribution,
        rejected_thresholds,
        header.get("context_rule_version"),
        rules,
    )
    new_gaps = build_finalize_gaps(findings, rejected_thresholds)
    status = summarize_status(checks, new_gaps)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    document = {
        "snapshot_id": SNAPSHOT_ID,
        "analysis_rule_version": RULE_VERSION,
        "context_rule_version": rules["required_context_rule_version"],
        "distribution_status": rules["distribution_status"],
        "human_review_status": rules["human_review_status"],
        "overall_score": rules["summary_vector"]["overall_score"],
        "summary": build_summary(findings, rules),
        "findings": findings,
        "cross_attribution": cross_attribution,
    }
    write_yaml(args.output_dir / "findings.yaml", document)
    write_jsonl(args.output_dir / "analysis-attempts.jsonl", log)
    write_yaml(
        args.output_dir / "gaps.yaml",
        {
            "snapshot_id": SNAPSHOT_ID,
            "gaps": [*load_existing_gaps(args.existing_gaps_file), *new_gaps],
        },
    )
    write_yaml(
        args.output_dir / "analysis-validation.yaml",
        {
            "snapshot_id": SNAPSHOT_ID,
            "analysis_rule_version": RULE_VERSION,
            "analysis_run_status": status,
            "selection_hash": canonical_jsonl_hash(rows),
            "selection_summary": header["dimensions"],
            "checks": checks,
            # Checks describe the accepted findings. A model output that was rejected and
            # regenerated is not silently dropped: its errors are summarised here and kept
            # in full, with the output itself, in analysis-attempts.jsonl.
            "rejected_attempts": [
                {
                    "dimension_id": entry["dimension_id"],
                    "attempt": entry["attempt"],
                    "errors": entry["errors"],
                }
                for entry in log
                if not entry["accepted"]
            ],
            "new_gap_ids": [gap["gap_id"] for gap in new_gaps],
            "rules_hash": sha256_file(args.rules_file),
            "findings_hash": sha256_file(args.output_dir / "findings.yaml"),
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze and score D1-D7 research findings for the fixed SMIC Snapshot v3"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    select = sub.add_parser("select", help="build each dimension's closed candidate set")
    select.add_argument("--snapshot-dir", type=Path, required=True)
    select.add_argument("--context-file", type=Path, required=True)
    select.add_argument("--facts-file", type=Path, required=True)
    select.add_argument("--evidence-file", type=Path, required=True)
    select.add_argument("--rules-file", type=Path, required=True)
    select.add_argument("--existing-gaps-file", type=Path, required=True)
    select.add_argument("--output-dir", type=Path, required=True)
    select.set_defaults(handler=run_select)

    prompt = sub.add_parser("prompt", help="assemble one prompt file per dimension")
    prompt.add_argument("--analysis-inputs", type=Path, required=True)
    prompt.add_argument("--rules-file", type=Path, required=True)
    prompt.add_argument("--output-dir", type=Path, required=True)
    prompt.set_defaults(handler=run_prompt)

    finalize = sub.add_parser("finalize", help="validate the frozen model judgment and derive")
    finalize.add_argument("--analysis-inputs", type=Path, required=True)
    finalize.add_argument("--model-findings", type=Path, required=True, action="append")
    finalize.add_argument("--rules-file", type=Path, required=True)
    finalize.add_argument("--existing-gaps-file", type=Path, required=True)
    finalize.add_argument("--output-dir", type=Path, required=True)
    finalize.set_defaults(handler=run_finalize)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        args.handler(args)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
