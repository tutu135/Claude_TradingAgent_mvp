"""Govern and validate research evidence for the fixed SMIC Snapshot v3.

This stage turns every normalized fact from Ticket 03 into exactly one governed
evidence record (fact_id : evidence_id is 1:1, deterministically derived) and runs the
FR-043 deterministic validation. Source tier, claim type, source group, evidence status,
and permitted use are assigned to every record; conflict detection runs only on the
manually verified record-level whitelist (see docs/adr/0003). It never writes back to the
frozen snapshot and never fabricates data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

SNAPSHOT_ID = "smic-a283e95e2c9e8068"
RULE_VERSION = "smic-v3-source-governance-v1"
ORIGIN_STAGE = "govern-and-validate-research-evidence"


def candidate_metrics(rules: dict[str, Any]) -> set[str]:
    """The core metrics whose fiscal-year present values form the conflict candidate pool.

    Derived from the single rules definition (conflict.metric_class) so the candidate set
    has one source of truth instead of a duplicated constant.
    """
    return set(rules["conflict"]["metric_class"])


# ---------------------------------------------------------------------------
# Shared IO / hashing helpers (kept identical in spirit to the Ticket 03 scripts).
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Govern and validate research evidence for the fixed SMIC Snapshot v3"
    )
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--facts-file", type=Path, required=True)
    parser.add_argument("--context-file", type=Path, required=True)
    parser.add_argument("--rules-file", type=Path, required=True)
    parser.add_argument("--existing-gaps-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


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
        raise ValueError(
            f"snapshot path escapes input directory: {relative_path}"
        ) from error
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


# ---------------------------------------------------------------------------
# Deterministic id derivations.
# ---------------------------------------------------------------------------
def evidence_id_for(fact_id: str) -> str:
    return "EVID_" + hashlib.sha256(fact_id.encode("utf-8")).hexdigest()[:24]


def comparable_group_id(key: tuple[Any, ...]) -> str:
    identity = "|".join("" if part is None else str(part) for part in key)
    return "CMP_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def span_hash_for(fact: dict[str, Any]) -> str:
    return sha256_text(fact.get("source_span_text") or "")


def is_interim_material(material_id: str) -> bool:
    """A half-year or quarterly material, which cannot carry a true fiscal-year value."""
    upper = material_id.upper()
    if "ANNUAL" in upper:
        return False
    return any(token in upper for token in ("_H1", "_Q1", "_Q2", "_Q3", "_Q4", "QUARTER"))


# ---------------------------------------------------------------------------
# Input maps.
# ---------------------------------------------------------------------------
def load_material_metadata(snapshot_dir: Path) -> dict[str, dict[str, Any]]:
    materials: dict[str, dict[str, Any]] = {}
    for line in read_jsonl(snapshot_dir / "materials.jsonl"):
        materials[line["material_id"]] = line
    return materials


def build_chunk_index(chunks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        locator = chunk.get("content_locator") or {}
        index[chunk["chunk_id"]] = {
            "text_hash": chunk.get("text_hash"),
            "material_id": chunk.get("material_id"),
            "speaker_label": chunk.get("speaker_label"),
            "section": locator.get("section"),
        }
    return index


def material_governance_index(rules: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["material_id"]: row for row in rules.get("material_governance", [])}


# ---------------------------------------------------------------------------
# Field assignment.
# ---------------------------------------------------------------------------
def is_ai_summary(speaker: Any, section: Any, rules: dict[str, Any]) -> bool:
    override = rules.get("record_tier_overrides", {}).get("ai_summary_downgrade", {})
    speakers = set(override.get("applies_when_speaker_in", []))
    prefix = override.get("applies_when_section_startswith", "")
    if speaker in speakers:
        return True
    if prefix and isinstance(section, str) and section.startswith(prefix):
        return True
    return False


def is_forward_looking(fact: dict[str, Any], rules: dict[str, Any]) -> bool:
    if fact.get("target_period") is not None:
        return True
    if fact.get("period_nature") == "FUTURE":
        return True
    if fact.get("uncertainty_text") is not None:
        return True
    markers = rules["claim_type_rules"].get("forward_looking_markers", [])
    haystack = " ".join(
        str(fact.get(field) or "")
        for field in ("source_span_text", "uncertainty_text", "condition_text")
    ).lower()
    return any(str(marker).lower() in haystack for marker in markers)


def resolve_tier(
    fact: dict[str, Any],
    governance: dict[str, Any],
    chunk: dict[str, Any],
    rules: dict[str, Any],
) -> tuple[str, Any, bool]:
    tier = governance["source_tier"]
    rationale = governance.get("tier_rationale")
    speaker = (chunk or {}).get("speaker_label") or fact.get("speaker_or_publisher")
    section = (chunk or {}).get("section") or (
        fact.get("content_locator") or {}
    ).get("section")
    ai_summary = (
        governance["material_category"] == "THIRD_PARTY_TRANSCRIPT"
        and is_ai_summary(speaker, section, rules)
    )
    if ai_summary:
        tier = rules["record_tier_overrides"]["ai_summary_downgrade"]["to_tier"]
    return tier, rationale, ai_summary


def resolve_claim_type(
    fact: dict[str, Any],
    governance: dict[str, Any],
    chunk: dict[str, Any],
    ai_summary: bool,
    rules: dict[str, Any],
) -> str:
    category = governance["material_category"]
    ctr = rules["claim_type_rules"]
    if category == "THIRD_PARTY_TRANSCRIPT":
        if ai_summary:
            return ctr["transcript"]["ai_summary"]
        speaker = (chunk or {}).get("speaker_label") or fact.get("speaker_or_publisher")
        if speaker in set(ctr["transcript"].get("host_operator_speakers", [])):
            return ctr["transcript"]["host_operator"]
        if is_forward_looking(fact, rules):
            return ctr["transcript"]["management_forward_looking"]
        return ctr["transcript"]["management_other"]
    if category == "INDUSTRY_ASSOCIATION":
        return ctr["industry_association"]
    if category == "DESIGNATED_MEDIA_FULL_TEXT":
        return ctr["designated_media_full_text"]
    # ISSUER_STATUTORY_DISCLOSURE: numeric and text both REPORTED_FACT in v3. A computed
    # derivation (value_origin other than SOURCE_REPORTED) is a DERIVED_METRIC; Ticket 03
    # produced no such records in v3, so this branch is inert but keeps the enum reachable.
    if fact.get("record_kind") == "NUMERIC_OBSERVATION":
        if fact.get("value_origin") not in (None, "SOURCE_REPORTED"):
            return ctr["issuer_statutory_disclosure"]["derived"]
        return ctr["issuer_statutory_disclosure"]["numeric"]
    return ctr["issuer_statutory_disclosure"]["text"]


def source_use_note_status(material: dict[str, Any], rules: dict[str, Any]) -> str:
    note = material.get("source_use_note") or {}
    limitation_keys = rules["source_use_note"]["limitation_note_keys"]
    if any(note.get(key) for key in limitation_keys):
        return "RECORDED_WITH_LIMITATIONS"
    return "RECORDED"


def locator_resolvable(fact: dict[str, Any], material: dict[str, Any]) -> bool:
    locator = fact.get("content_locator")
    if not isinstance(locator, dict) or not locator:
        return False
    if material.get("parse_status") != "PARSED":
        return False
    return True


# ---------------------------------------------------------------------------
# Conflict eligibility + detection.
# ---------------------------------------------------------------------------
def whitelist_index(rules: dict[str, Any]) -> dict[str, dict[str, Any]]:
    overrides = rules.get("snapshot_conflict_eligibility_overrides", {})
    return {
        item["fact_id"]: item
        for item in overrides.get("verified_facts", [])
        if item.get("eligibility") == "INCLUDE"
    }


def whitelist_signature_matches(fact: dict[str, Any], entry: dict[str, Any]) -> bool:
    signature = entry.get("signature", {})
    for field, expected in signature.items():
        if field == "span_hash":
            if span_hash_for(fact) != expected:
                return False
        elif fact.get(field) != expected:
            return False
    return True


def required_comparability_fields(metric_id: Any, rules: dict[str, Any]) -> list[str]:
    metric_class = rules["conflict"]["metric_class"].get(metric_id)
    return rules["conflict"]["metric_class_required_fields"].get(metric_class or "", [])


def missing_comparability_fields(fact: dict[str, Any], rules: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in rules["conflict"]["comparable_key_fields"]:
        if field in {"target_currency", "target_unit"}:
            continue  # handled per metric class below
        if fact.get(field) in (None, ""):
            missing.append(field)
    for field in required_comparability_fields(fact.get("metric_id"), rules):
        if fact.get(field) in (None, ""):
            missing.append(field)
    return sorted(set(missing))


def comparable_key(fact: dict[str, Any], rules: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(fact.get(field) for field in rules["conflict"]["comparable_key_fields"])


def classify_exclusion(fact: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    """Coarse conflict fields for records outside the whitelist. Never leaves fields empty."""
    codes = rules["conflict"]["exclusion_reason_codes"]
    if fact.get("record_kind") == "TEXT_PROPOSITION":
        return {
            "conflict_eligibility": "EXCLUDED",
            "conflict_status": "NOT_APPLICABLE",
            "conflict_exclusion_reason": codes["text_proposition"],
            "conflict_missing_fields": [],
        }
    if not fact.get("metric_id"):
        return {
            "conflict_eligibility": "EXCLUDED",
            "conflict_status": "NOT_EVALUATED",
            "conflict_exclusion_reason": codes["missing_metric_id"],
            "conflict_missing_fields": ["metric_id"],
        }
    missing = missing_comparability_fields(fact, rules)
    if missing:
        return {
            "conflict_eligibility": "EXCLUDED",
            "conflict_status": "NOT_EVALUATED",
            "conflict_exclusion_reason": codes["missing_comparability_key"],
            "conflict_missing_fields": missing,
        }
    return {
        "conflict_eligibility": "EXCLUDED",
        "conflict_status": "NOT_EVALUATED",
        "conflict_exclusion_reason": codes["not_in_whitelist"],
        "conflict_missing_fields": [],
    }


def decimal_value(fact: dict[str, Any]) -> Decimal | None:
    raw = fact.get("normalized_value")
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None


def resolve_conflict_group(
    members: list[dict[str, Any]], rules: dict[str, Any]
) -> dict[str, Any]:
    """Apply the fixed FR-042 resolution order to one comparable group with >1 distinct value.

    Never averages or silently selects. Returns the winning evidence id and rule id when a
    single winner survives, otherwise marks the group CONFLICT_UNRESOLVED.
    """
    audit_priority = {
        status: index for index, status in enumerate(rules["conflict"]["audit_priority"])
    }
    tier_order = {tier: index for index, tier in enumerate(["T1", "T2", "T3", "T4"])}

    def audit_rank(record: dict[str, Any]) -> int:
        status = record["fact"].get("audit_status")
        if status == "AMBIGUOUS":
            status = "UNKNOWN"  # AMBIGUOUS is treated as UNKNOWN
        return audit_priority.get(status, len(audit_priority))

    def statutory_rank(record: dict[str, Any]) -> int:
        return 0 if record["governance"]["material_category"] == "ISSUER_STATUTORY_DISCLOSURE" else 1

    def tier_rank(record: dict[str, Any]) -> int:
        return tier_order.get(record["evidence"]["source_tier"], len(tier_order))

    # SAME_SOURCE_DEDUP: collapse each source group to a single representative so reprints
    # cannot vote. The representative is the earliest evidence id for determinism.
    by_group: dict[str, dict[str, Any]] = {}
    for record in sorted(members, key=lambda item: item["evidence"]["evidence_id"]):
        by_group.setdefault(record["evidence"]["source_group_id"], record)
    representatives = list(by_group.values())

    distinct_values = {str(decimal_value(record["fact"])) for record in representatives}
    if len(distinct_values) <= 1:
        return {"status": "NO_CONFLICT"}

    ranked = sorted(
        representatives,
        key=lambda record: (
            audit_rank(record),
            statutory_rank(record),
            tier_rank(record),
            record["evidence"]["evidence_id"],
        ),
    )
    best = ranked[0]
    tie = [
        record
        for record in ranked
        if (audit_rank(record), statutory_rank(record), tier_rank(record))
        == (audit_rank(best), statutory_rank(best), tier_rank(best))
        and str(decimal_value(record["fact"])) != str(decimal_value(best["fact"]))
    ]
    if tie:
        return {"status": "CONFLICT_UNRESOLVED"}
    return {
        "status": "RESOLVED",
        "winner_evidence_id": best["evidence"]["evidence_id"],
        "resolution_rule_id": rules["conflict"]["resolution_rule_id"],
    }


# ---------------------------------------------------------------------------
# Build governed evidence.
# ---------------------------------------------------------------------------
def build_evidence(
    facts: list[dict[str, Any]],
    materials: dict[str, dict[str, Any]],
    chunk_index: dict[str, dict[str, Any]],
    rules: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    governance_index = material_governance_index(rules)
    whitelist = whitelist_index(rules)
    codes = rules["conflict"]["exclusion_reason_codes"]

    records: list[dict[str, Any]] = []
    eligible_records: list[dict[str, Any]] = []
    signature_failures: list[str] = []

    for fact in facts:
        fact_id = fact["fact_id"]
        material_id = fact["material_id"]
        material = materials.get(material_id, {})
        governance = governance_index.get(material_id)
        if governance is None:
            raise ValueError(f"material without governance row: {material_id}")
        chunk = chunk_index.get(fact["chunk_id"], {})

        tier, tier_rationale, ai_summary = resolve_tier(fact, governance, chunk, rules)
        claim_type = resolve_claim_type(fact, governance, chunk, ai_summary, rules)

        evidence: dict[str, Any] = {
            "evidence_id": evidence_id_for(fact_id),
            "fact_id": fact_id,
            "chunk_id": fact["chunk_id"],
            "material_id": material_id,
            "snapshot_id": SNAPSHOT_ID,
            "record_kind": fact.get("record_kind"),
            "source_tier": tier,
            "source_tier_rule_id": "MATERIAL_TIER_TABLE_V1",
            "tier_rationale": tier_rationale,
            "source_group_id": governance["source_group_id"],
            "claim_type": claim_type,
            "claim_type_rule_id": "CLAIM_TYPE_MATERIAL_CATEGORY_FIRST_V1",
            "source_use_note_status": source_use_note_status(material, rules),
            "governance_rule_version": RULE_VERSION,
            "source_chunk_text_hash": fact.get("source_chunk_text_hash"),
            "normalization_status": fact.get("normalization_status"),
            "gap_ids": list(fact.get("gap_ids") or []),
        }

        # Conflict eligibility.
        entry = whitelist.get(fact_id)
        if entry is not None and whitelist_signature_matches(fact, entry):
            evidence.update(
                {
                    "conflict_eligibility": "INCLUDED",
                    "conflict_status": "PENDING",
                    "conflict_exclusion_reason": None,
                    "conflict_missing_fields": [],
                    "conflict_review_reason": entry.get("review_reason"),
                }
            )
            eligible_records.append({"fact": fact, "evidence": evidence, "governance": governance})
        else:
            if entry is not None:
                signature_failures.append(fact_id)  # whitelisted but signature drift -> fail closed
            evidence.update(classify_exclusion(fact, rules))
            evidence["conflict_review_reason"] = None

        records.append({"fact": fact, "evidence": evidence, "governance": governance})

    # Detect conflicts on eligible records only.
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in eligible_records:
        key = comparable_key(record["fact"], rules)
        record["evidence"]["comparable_group_id"] = comparable_group_id(key)
        groups[record["evidence"]["comparable_group_id"]].append(record)

    comparison_pair_count = 0
    detected_conflict_groups = 0
    unresolved_conflict_groups = 0
    for group_id, members in groups.items():
        # cross-source comparison pairs (after same-source dedup) within this group
        source_groups = {m["evidence"]["source_group_id"] for m in members}
        pair_count = len(source_groups) * (len(source_groups) - 1) // 2
        comparison_pair_count += pair_count
        outcome = resolve_conflict_group(members, rules)
        if outcome["status"] == "NO_CONFLICT":
            for member in members:
                member["evidence"]["conflict_status"] = "NO_CONFLICT"
                member["evidence"]["conflict_group_id"] = None
                member["evidence"]["conflict_winner_evidence_id"] = None
                member["evidence"]["conflict_resolution_rule_id"] = None
            continue
        detected_conflict_groups += 1
        conflict_group_id = "CONFLICT_" + group_id.split("_", 1)[1]
        resolved = outcome["status"] == "RESOLVED"
        if not resolved:
            unresolved_conflict_groups += 1
        for member in members:
            member["evidence"]["conflict_status"] = (
                "RESOLVED" if resolved else "CONFLICT_UNRESOLVED"
            )
            member["evidence"]["conflict_group_id"] = conflict_group_id
            member["evidence"]["conflict_winner_evidence_id"] = outcome.get("winner_evidence_id")
            member["evidence"]["conflict_resolution_rule_id"] = outcome.get("resolution_rule_id")

    # Fill conflict lineage fields for excluded records so nothing is left empty.
    for record in records:
        record["evidence"].setdefault("comparable_group_id", None)
        record["evidence"].setdefault("conflict_group_id", None)
        record["evidence"].setdefault("conflict_winner_evidence_id", None)
        record["evidence"].setdefault("conflict_resolution_rule_id", None)
        if record["evidence"].get("conflict_status") == "PENDING":
            # eligible but its group never resolved (should not happen); fail-safe
            record["evidence"]["conflict_status"] = "NO_CONFLICT"

    # Evidence status (needs conflict_status), permitted use, quarantine reasons.
    for record in records:
        fact = record["fact"]
        evidence = record["evidence"]
        material = materials.get(fact["material_id"], {})
        quarantine_reasons: list[str] = []
        if not material.get("as_of_eligible", False):
            quarantine_reasons.append("MATERIAL_AS_OF_INELIGIBLE")
        if not locator_resolvable(fact, material):
            quarantine_reasons.append("CONTENT_LOCATOR_UNRESOLVABLE")
        if fact.get("normalization_status") == "BLOCKED":
            quarantine_reasons.append("NORMALIZATION_BLOCKED")

        restricted_reasons: list[str] = []
        if fact.get("normalization_status") == "PARTIAL":
            restricted_reasons.append("NORMALIZATION_PARTIAL")
        if evidence["source_tier"] in {"T3", "T4"}:
            restricted_reasons.append("LOW_SOURCE_TIER")
        if evidence.get("conflict_status") == "CONFLICT_UNRESOLVED":
            restricted_reasons.append("CONFLICT_UNRESOLVED")

        if quarantine_reasons:
            status = "QUARANTINED"
        elif restricted_reasons:
            status = "RESTRICTED"
        else:
            status = "USABLE"
        evidence["evidence_status"] = status
        evidence["evidence_status_reason_codes"] = (
            sorted(set(quarantine_reasons)) if status == "QUARANTINED"
            else sorted(set(restricted_reasons)) if status == "RESTRICTED"
            else []
        )
        evidence["quarantine_reason_codes"] = sorted(set(quarantine_reasons))
        evidence["permitted_use"] = rules["evidence_status"]["permitted_use"][status]

    stats = {
        "comparison_pair_count": comparison_pair_count,
        "detected_conflict_group_count": detected_conflict_groups,
        "unresolved_conflict_group_count": unresolved_conflict_groups,
        "comparable_group_count": len(groups),
        "eligible_fact_count": len(eligible_records),
        "signature_failures": sorted(signature_failures),
    }
    evidence_rows = [record["evidence"] for record in records]
    return evidence_rows, {"records": records, "stats": stats}


# ---------------------------------------------------------------------------
# Gaps.
# ---------------------------------------------------------------------------
def build_gaps(
    facts: list[dict[str, Any]], rules: dict[str, Any]
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []

    # 1. One aggregate gap for numeric facts missing metric_id (not one gap per record).
    missing = [
        fact
        for fact in facts
        if fact.get("record_kind") == "NUMERIC_OBSERVATION" and not fact.get("metric_id")
    ]
    numeric_total = sum(
        1 for fact in facts if fact.get("record_kind") == "NUMERIC_OBSERVATION"
    )
    if missing:
        by_label = Counter(str(fact.get("source_metric_label")) for fact in missing)
        by_material = Counter(fact["material_id"] for fact in missing)
        by_unit = Counter(str(fact.get("raw_unit")) for fact in missing)
        top_labels = [
            {"source_metric_label": label, "count": count}
            for label, count in sorted(
                by_label.items(), key=lambda item: (-item[1], item[0])
            )[:8]
        ]
        top_materials = [
            {"material_id": material_id, "count": count}
            for material_id, count in sorted(
                by_material.items(), key=lambda item: (-item[1], item[0])
            )[:8]
        ]
        breakdown_identity = json.dumps(
            {
                "missing": len(missing),
                "numeric_total": numeric_total,
                "by_source_metric_label": {k: v for k, v in sorted(by_label.items())},
                "by_material": {k: v for k, v in sorted(by_material.items())},
                "by_raw_unit": {k: v for k, v in sorted(by_unit.items())},
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        gap_id = "GAP_EVIDENCE_" + hashlib.sha256(
            breakdown_identity.encode("utf-8")
        ).hexdigest()[:16]
        gaps.append(
            {
                "gap_id": gap_id,
                "origin_stage": ORIGIN_STAGE,
                "gap_kind": "EVIDENCE_METRIC_ID_MISSING",
                "question": (
                    f"{len(missing)}/{numeric_total} numeric observations carry no metric_id, so "
                    "they cannot enter metric conflict detection and stay conflict_eligibility=EXCLUDED."
                ),
                "impact_objects": ["metric_conflict_detection"],
                "aggregate": {
                    "missing_metric_id": len(missing),
                    "numeric_total": numeric_total,
                    # Spec-mandated dimension. In v3 every such record has a null
                    # source_metric_label, so the table also carries material breakdown.
                    "top_source_metric_labels": top_labels,
                    "top_materials": top_materials,
                    "by_raw_unit": {k: v for k, v in sorted(by_unit.items())},
                },
                "current_handling": (
                    "Record one aggregate gap; keep every record governed with a coarse "
                    "exclusion reason instead of expanding into hundreds of per-record gaps."
                ),
                "confirmation_owner": "user/data_preparer",
                "required_evidence": "Upstream metric mapping that assigns a metric_id to these observations.",
                "priority": "P2",
                "status": "OPEN",
            }
        )

    # 2. One upstream defect gap pointing back to Ticket 03 period mislabelling, registered
    # only when the pollution signature is present: candidate-pool FISCAL_YEAR values sourced
    # from half-year / quarterly materials (which cannot truly be fiscal-year values).
    core_metrics = candidate_metrics(rules)
    polluted = [
        fact
        for fact in facts
        if fact.get("period_type") == "FISCAL_YEAR"
        and fact.get("metric_id") in core_metrics
        and fact.get("value_status") == "PRESENT"
        and is_interim_material(fact.get("material_id", ""))
    ]
    if not polluted:
        return gaps
    gaps.append(
        {
            "gap_id": "GAP_EVIDENCE_UPSTREAM_PERIOD_MISLABEL",
            "origin_stage": ORIGIN_STAGE,
            "gap_kind": "UPSTREAM_DEFECT",
            "question": (
                "Ticket 03 normalization labelled half-year and third-quarter cumulative "
                "values as period_type=FISCAL_YEAR, polluting the conflict candidate pool."
            ),
            "impact_objects": ["normalize-research-facts", "conflict_candidate_pool"],
            "current_handling": (
                "Use the manually verified record-level conflict whitelist as a v3 compatibility "
                "measure; the root cause must be fixed in normalization by deriving period fields "
                "from each material's reporting period, table headers, and cumulative window."
            ),
            "confirmation_owner": "user/data_preparer",
            "required_evidence": "A normalization fix that assigns correct period_type/period bounds upstream.",
            "priority": "P1",
            "status": "OPEN",
        }
    )
    return gaps


# ---------------------------------------------------------------------------
# FR-043 validation: 13 named checks.
# ---------------------------------------------------------------------------
def run_validation(
    records: list[dict[str, Any]],
    materials: dict[str, dict[str, Any]],
    chunk_index: dict[str, dict[str, Any]],
    facts: list[dict[str, Any]],
    rules: dict[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    governance_index = material_governance_index(rules)
    fact_by_id = {fact["fact_id"]: fact for fact in facts}

    def add(name: str, status: str, reason: str, **details: Any) -> None:
        checks.append({"check": name, "status": status, "reason": reason, **details})

    # 1. hash_integrity
    hash_mismatch = 0
    for record in records:
        chunk = chunk_index.get(record["evidence"]["chunk_id"])
        if chunk is None or record["evidence"]["source_chunk_text_hash"] != chunk.get("text_hash"):
            hash_mismatch += 1
    add(
        "hash_integrity",
        "FAIL" if hash_mismatch else "PASS",
        f"{hash_mismatch} evidence rows whose source_chunk_text_hash does not match the chunk text hash.",
        mismatch_count=hash_mismatch,
    )

    # 2. as_of_eligibility
    ineligible = sum(
        1
        for record in records
        if not materials.get(record["evidence"]["material_id"], {}).get("as_of_eligible", False)
    )
    add(
        "as_of_eligibility",
        "WARN" if ineligible else "PASS",
        f"{ineligible} evidence rows come from as_of-ineligible materials and are quarantined.",
        ineligible_count=ineligible,
    )

    # 3. content_locator_resolvable
    unresolvable = sum(
        1
        for record in records
        if not locator_resolvable(record["fact"], materials.get(record["evidence"]["material_id"], {}))
    )
    add(
        "content_locator_resolvable",
        "WARN" if unresolvable else "PASS",
        f"{unresolvable} evidence rows have an unresolvable content locator and are quarantined.",
        unresolvable_count=unresolvable,
    )

    # 4. required_fields
    required = rules["required_evidence_fields"]
    missing_field_rows = 0
    for record in records:
        evidence = record["evidence"]
        if any(evidence.get(field) in (None, "") for field in required):
            missing_field_rows += 1
    add(
        "required_fields",
        "FAIL" if missing_field_rows else "PASS",
        f"{missing_field_rows} evidence rows are missing a required field.",
        missing_count=missing_field_rows,
    )

    # 5. unit_currency_period (on conflict-eligible numeric records)
    field_state_violations = 0
    checked = 0
    for record in records:
        if record["evidence"].get("conflict_eligibility") != "INCLUDED":
            continue
        checked += 1
        fact = record["fact"]
        metric_class = rules["conflict"]["metric_class"].get(fact.get("metric_id"))
        required_fields = rules["conflict"]["metric_class_required_fields"].get(metric_class or "", [])
        if any(fact.get(field) in (None, "") for field in required_fields):
            field_state_violations += 1
        if metric_class == "RATIO" and (
            fact.get("target_currency") not in (None, "NOT_APPLICABLE")
            or fact.get("target_unit") not in (None, "NOT_APPLICABLE")
        ):
            field_state_violations += 1
        if fact.get("period_start") in (None, "") or fact.get("period_end") in (None, ""):
            field_state_violations += 1
    add(
        "unit_currency_period",
        "FAIL" if field_state_violations else "PASS",
        f"{field_state_violations} eligible numeric records violate metric-class unit/currency/period requirements.",
        checked=checked,
        violations=field_state_violations,
    )

    # 6. formula_recomputation (reconciliations Ticket 03 asserted determinate)
    recompute_mismatch = 0
    recomputed = 0
    recomputable_statuses = set(rules["formula_recomputation"]["reconciliation_recomputable_statuses"])
    tolerance = Decimal(str(rules["formula_recomputation"]["amount_tolerance"]))
    for fact in facts:
        check = fact.get("reconciliation_check")
        if not check or check.get("reconciliation_status") not in recomputable_statuses:
            continue
        recomputed += 1
        total = Decimal("0")
        ok = True
        for row in check.get("rows", []):
            if not row.get("included_in_sum"):
                continue
            amount = row.get("normalized_signed_amount")
            if amount is None:
                base = fact_by_id.get(row.get("fact_id"), {})
                amount = base.get("base_unit_value")
            if amount is None:
                ok = False
                break
            total += Decimal(str(amount))
        reported = check.get("source_reported_ifrs_target")
        if not ok or reported is None or abs(total - Decimal(str(reported))) > tolerance:
            recompute_mismatch += 1
    add(
        "formula_recomputation",
        "FAIL" if recompute_mismatch else "PASS",
        f"{recompute_mismatch} of {recomputed} recomputable IFRS/CAS reconciliations disagree with Ticket 03.",
        recomputed=recomputed,
        mismatch=recompute_mismatch,
    )

    # 7. source_group_consistency
    group_issues = 0
    for record in records:
        governance = governance_index.get(record["evidence"]["material_id"])
        if governance is None or governance.get("source_group_id") != record["evidence"]["source_group_id"]:
            group_issues += 1
    add(
        "source_group_consistency",
        "FAIL" if group_issues else "PASS",
        f"{group_issues} evidence rows disagree with the fixed material source-group table.",
        issue_count=group_issues,
    )

    # 8. conflict_detection
    unresolved = sum(
        1 for record in records if record["evidence"].get("conflict_status") == "CONFLICT_UNRESOLVED"
    )
    non_whitelist_conflicts = sum(
        1
        for record in records
        if record["evidence"].get("conflict_group_id")
        and record["evidence"].get("conflict_eligibility") != "INCLUDED"
    )
    if non_whitelist_conflicts:
        conflict_status = "FAIL"
    elif unresolved:
        conflict_status = "WARN"
    else:
        conflict_status = "PASS"
    add(
        "conflict_detection",
        conflict_status,
        f"{unresolved} records in unresolved conflicts; conflicts only formed on whitelisted records.",
        unresolved_records=unresolved,
        non_whitelist_conflict_records=non_whitelist_conflicts,
    )

    # 9. isolation_quarantine
    quarantined = [r for r in records if r["evidence"]["evidence_status"] == "QUARANTINED"]
    isolation_bad = sum(
        1 for r in quarantined if r["evidence"]["permitted_use"] != "NOT_USABLE"
    )
    if isolation_bad:
        isolation_status = "FAIL"
    elif quarantined:
        isolation_status = "WARN"
    else:
        isolation_status = "PASS"
    add(
        "isolation_quarantine",
        isolation_status,
        f"{len(quarantined)} quarantined rows; {isolation_bad} incorrectly remain usable.",
        quarantined_count=len(quarantined),
        wrongly_usable=isolation_bad,
    )

    # 10. id_reference_integrity
    evidence_ids = [r["evidence"]["evidence_id"] for r in records]
    duplicate_evidence = len(evidence_ids) - len(set(evidence_ids))
    dangling = 0
    for record in records:
        evidence = record["evidence"]
        if evidence["chunk_id"] not in chunk_index:
            dangling += 1
        if evidence["material_id"] not in materials:
            dangling += 1
        if evidence["evidence_id"] != evidence_id_for(evidence["fact_id"]):
            dangling += 1
    add(
        "id_reference_integrity",
        "FAIL" if duplicate_evidence or dangling else "PASS",
        f"{duplicate_evidence} duplicate evidence ids; {dangling} dangling references.",
        duplicate_evidence_ids=duplicate_evidence,
        dangling_references=dangling,
    )

    # 11. locator_chain_consistency (RAG check: references + chunk hash, not locator accuracy)
    chain_broken = 0
    for record in records:
        evidence = record["evidence"]
        chunk = chunk_index.get(evidence["chunk_id"])
        if chunk is None:
            chain_broken += 1
            continue
        if chunk.get("material_id") != evidence["material_id"]:
            chain_broken += 1
        if evidence["source_chunk_text_hash"] != chunk.get("text_hash"):
            chain_broken += 1
    add(
        "locator_chain_consistency",
        "FAIL" if chain_broken else "PASS",
        f"{chain_broken} broken fact->chunk->material chains or chunk-hash mismatches. "
        + rules["inherited_guarantees"]["locator_accuracy"],
        broken_count=chain_broken,
    )

    # 12. state_combination_legality
    combos = rules["legal_state_combinations"]
    illegal = 0
    for record in records:
        evidence = record["evidence"]
        status = evidence["evidence_status"]
        if status == "QUARANTINED":
            if combos.get("quarantined_requires_reason") and not evidence["quarantine_reason_codes"]:
                illegal += 1
            if evidence["permitted_use"] != combos.get("quarantined_permitted_use"):
                illegal += 1
        if combos.get("conflict_unresolved_not_usable") and (
            evidence.get("conflict_status") == "CONFLICT_UNRESOLVED" and status == "USABLE"
        ):
            illegal += 1
        if combos.get("tier_t3_t4_not_usable") and (
            evidence["source_tier"] in {"T3", "T4"} and status == "USABLE"
        ):
            illegal += 1
        if combos.get("t4_only_for_ai_summary") and evidence["source_tier"] == "T4" and (
            evidence["claim_type"] != "THIRD_PARTY_VIEW"
        ):
            illegal += 1
        if combos.get("included_requires_whitelist") and (
            evidence.get("conflict_eligibility") == "INCLUDED"
            and evidence.get("record_kind") != "NUMERIC_OBSERVATION"
        ):
            illegal += 1
        if combos.get("text_conflict_status") and evidence["record_kind"] == "TEXT_PROPOSITION" and (
            evidence.get("conflict_status") != combos["text_conflict_status"]
        ):
            illegal += 1
        if combos.get("analytic_inference_forbidden") and evidence["claim_type"] == "ANALYTIC_INFERENCE":
            illegal += 1
    add(
        "state_combination_legality",
        "FAIL" if illegal else "PASS",
        f"{illegal} evidence rows use an illegal state combination.",
        illegal_count=illegal,
    )

    # 13. whitelist_signature (fail closed on any drift)
    whitelist = rules.get("snapshot_conflict_eligibility_overrides", {}).get("verified_facts", [])
    signature_failures = 0
    for entry in whitelist:
        fact = fact_by_id.get(entry["fact_id"])
        if fact is None or not whitelist_signature_matches(fact, entry):
            signature_failures += 1
    add(
        "whitelist_signature",
        "FAIL" if signature_failures else "PASS",
        f"{signature_failures} whitelisted records are missing or fail full-signature verification.",
        signature_failures=signature_failures,
        whitelist_size=len(whitelist),
    )

    # Fail closed if the emitted checks drift from the declared FR-043 list in the rules.
    declared = list(rules.get("validation_checks", []))
    emitted = [check["check"] for check in checks]
    if declared and emitted != declared:
        raise ValueError(
            "emitted validation checks do not match the declared FR-043 validation_checks list"
        )

    return checks


def summarize_status(
    checks: list[dict[str, Any]], clean_rebuild_match: bool, new_gaps: list[dict[str, Any]]
) -> str:
    if any(check["status"] == "FAIL" for check in checks) or not clean_rebuild_match:
        return "FAIL"
    if any(check["status"] == "WARN" for check in checks) or new_gaps:
        return "WARN"
    return "PASS"


# ---------------------------------------------------------------------------
# Statistics for the run report.
# ---------------------------------------------------------------------------
def candidate_pool_count(facts: list[dict[str, Any]], rules: dict[str, Any]) -> int:
    core_metrics = candidate_metrics(rules)
    return sum(
        1
        for fact in facts
        if fact.get("record_kind") == "NUMERIC_OBSERVATION"
        and fact.get("metric_id") in core_metrics
        and fact.get("period_type") == "FISCAL_YEAR"
        and fact.get("value_status") == "PRESENT"
    )


def build_statistics(
    evidence_rows: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    conflict_stats: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, Any]:
    excluded_by_reason = Counter(
        row["conflict_exclusion_reason"]
        for row in evidence_rows
        if row.get("conflict_eligibility") == "EXCLUDED"
    )
    return {
        # Seven conflict-run statistics required by ADR 0003 to prove zero != not-run.
        "candidate_fact_count": candidate_pool_count(facts, rules),
        "eligible_fact_count": conflict_stats["eligible_fact_count"],
        "excluded_fact_count_by_reason": {k: v for k, v in sorted(excluded_by_reason.items())},
        "comparable_group_count": conflict_stats["comparable_group_count"],
        "comparison_pair_count": conflict_stats["comparison_pair_count"],
        "detected_conflict_group_count": conflict_stats["detected_conflict_group_count"],
        "unresolved_conflict_group_count": conflict_stats["unresolved_conflict_group_count"],
        # Governance coverage distributions.
        "evidence_count": len(evidence_rows),
        "evidence_status_counts": {
            k: v for k, v in sorted(Counter(row["evidence_status"] for row in evidence_rows).items())
        },
        "source_tier_counts": {
            k: v for k, v in sorted(Counter(row["source_tier"] for row in evidence_rows).items())
        },
        "claim_type_counts": {
            k: v for k, v in sorted(Counter(row["claim_type"] for row in evidence_rows).items())
        },
        "source_group_count": len({row["source_group_id"] for row in evidence_rows}),
    }


# ---------------------------------------------------------------------------
# Orchestration.
# ---------------------------------------------------------------------------
def govern(
    facts: list[dict[str, Any]],
    materials: dict[str, dict[str, Any]],
    chunk_index: dict[str, dict[str, Any]],
    rules: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    evidence_rows, build = build_evidence(facts, materials, chunk_index, rules)
    new_gaps = build_gaps(facts, rules)
    return evidence_rows, build, new_gaps


def main() -> int:
    args = parse_args()
    try:
        require_output_outside_snapshot(args.snapshot_dir, args.output_dir)
        verify_snapshot(args.snapshot_dir)

        rules = yaml.safe_load(args.rules_file.read_text(encoding="utf-8"))
        if rules.get("snapshot_id") not in {None, SNAPSHOT_ID}:
            raise ValueError("source-governance rules are not bound to Snapshot v3")
        if rules.get("rule_version") != RULE_VERSION:
            raise ValueError(f"rule_version must be {RULE_VERSION}")

        facts = read_jsonl(args.facts_file)
        if any(fact.get("snapshot_id") != SNAPSHOT_ID for fact in facts):
            raise ValueError("every fact must carry the exact Snapshot v3 identity")
        chunks = read_jsonl(args.context_file)
        if any(chunk.get("snapshot_id") != SNAPSHOT_ID for chunk in chunks):
            raise ValueError("every context chunk must carry the exact Snapshot v3 identity")

        materials = load_material_metadata(args.snapshot_dir)
        chunk_index = build_chunk_index(chunks)

        evidence_rows, build, new_gaps = govern(facts, materials, chunk_index, rules)
        rebuilt_rows, _, rebuilt_gaps = govern(facts, materials, chunk_index, rules)
        clean_rebuild_match = (
            canonical_jsonl_hash(evidence_rows) == canonical_jsonl_hash(rebuilt_rows)
            and canonical_hash(new_gaps) == canonical_hash(rebuilt_gaps)
        )

        checks = run_validation(
            build["records"], materials, chunk_index, facts, rules
        )
        status = summarize_status(checks, clean_rebuild_match, new_gaps)
        statistics = build_statistics(evidence_rows, facts, build["stats"], rules)

        existing_gaps = yaml.safe_load(args.existing_gaps_file.read_text(encoding="utf-8"))
        if existing_gaps.get("snapshot_id") != SNAPSHOT_ID:
            raise ValueError("existing gap registry is not bound to Snapshot v3")

        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(args.output_dir / "governed-evidence.jsonl", evidence_rows)
        write_yaml(
            args.output_dir / "gaps.yaml",
            {
                "snapshot_id": SNAPSHOT_ID,
                "gaps": [*(existing_gaps.get("gaps") or []), *new_gaps],
            },
        )
        write_yaml(
            args.output_dir / "evidence-validation.yaml",
            {
                "snapshot_id": SNAPSHOT_ID,
                "governance_rule_version": rules.get("rule_version"),
                "validation_status": status,
                "clean_rebuild_hashes_match": clean_rebuild_match,
                "clean_rebuild_hashes": {
                    "first_evidence": canonical_jsonl_hash(evidence_rows),
                    "rebuilt_evidence": canonical_jsonl_hash(rebuilt_rows),
                    "first_gaps": canonical_hash(new_gaps),
                    "rebuilt_gaps": canonical_hash(rebuilt_gaps),
                },
                "inherited_guarantees": rules.get("inherited_guarantees", {}),
                "checks": checks,
                "statistics": statistics,
                "new_gap_ids": [gap["gap_id"] for gap in new_gaps],
                "rules_hash": sha256_file(args.rules_file),
                "facts_hash": sha256_file(args.facts_file),
                "evidence_hash": sha256_file(args.output_dir / "governed-evidence.jsonl"),
            },
        )
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
