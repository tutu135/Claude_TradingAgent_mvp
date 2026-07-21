"""Run the bounded adversarial challenge loop over the D1-D7 findings (FR-060/FR-061).

The model writes the four categories of question and its disposition reasoning; every
loop control is deterministic script logic here: round cap, one targeted review per
question, the four legal dispositions, the before/after record, the fixed BLOCKING
trigger list, and re-running the full analysis validation over the revised findings.

A challenge never rewrites a finding by itself: the revision it triggers is applied by
this script and then re-validated with exactly the same checks the first version faced.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze_and_score_research_findings import (  # noqa: E402
    DERIVED_FINDING_KEYS,
    DERIVED_ITEM_KEYS,
    SNAPSHOT_ID,
    build_cross_attribution,
    build_summary,
    check_forbidden_terms,
    enrich_findings,
    forbidden_terms_in,
    load_candidate_index,
    load_rules,
    read_jsonl,
    run_validation,
    sha256_file,
    validate_finding,
    write_yaml,
)

ORIGIN_STAGE = "challenge-research-findings"

CHALLENGE_KEYS = {
    "challenge_id",
    "round",
    "category",
    "target_kind",
    "target_id",
    "question",
    "disposition",
    "reason",
    "follow_up_of",
    "revision",
}
CHALLENGE_REQUIRED = {
    "challenge_id",
    "round",
    "category",
    "target_kind",
    "target_id",
    "question",
    "disposition",
    "reason",
}
REVISION_KEYS = {"dimension_id", "finding_after"}
TARGET_KINDS = {"FINDING", "EVIDENCE"}


def load_model_challenges(path: Path) -> list[dict[str, Any]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if document.get("snapshot_id") != SNAPSHOT_ID:
        raise ValueError(f"{path.name} is not bound to Snapshot v3")
    return list(document.get("challenges") or [])


def check_challenge_schema(
    challenge: dict[str, Any],
    seen: set[str],
    dimension_ids: set[str],
    everything: dict[str, dict[str, Any]],
    rules: dict[str, Any],
) -> list[str]:
    settings = rules["challenge"]
    errors: list[str] = []
    unknown = set(challenge) - CHALLENGE_KEYS
    if unknown:
        errors.append(f"CHALLENGE_UNKNOWN_FIELDS:{','.join(sorted(unknown))}")
    missing = CHALLENGE_REQUIRED - set(challenge)
    if missing:
        errors.append(f"CHALLENGE_MISSING_FIELDS:{','.join(sorted(missing))}")
    challenge_id = str(challenge.get("challenge_id"))
    if challenge_id in seen:
        errors.append(f"CHALLENGE_DUPLICATE_ID:{challenge_id}")
    if challenge.get("category") not in settings["categories"]:
        errors.append(f"CHALLENGE_BAD_CATEGORY:{challenge.get('category')}")
    if challenge.get("disposition") not in settings["dispositions"]:
        errors.append(f"CHALLENGE_BAD_DISPOSITION:{challenge.get('disposition')}")
    round_number = challenge.get("round")
    if not isinstance(round_number, int) or not 1 <= round_number <= settings["max_rounds"]:
        errors.append(f"CHALLENGE_BAD_ROUND:{round_number}")
    if challenge.get("target_kind") not in TARGET_KINDS:
        errors.append(f"CHALLENGE_BAD_TARGET_KIND:{challenge.get('target_kind')}")
    target_id = str(challenge.get("target_id"))
    if challenge.get("target_kind") == "FINDING" and target_id not in dimension_ids:
        errors.append(f"CHALLENGE_UNKNOWN_TARGET:{target_id}")
    if challenge.get("target_kind") == "EVIDENCE" and target_id not in everything:
        errors.append(f"CHALLENGE_UNKNOWN_TARGET:{target_id}")
    if not str(challenge.get("question") or "").strip():
        errors.append("CHALLENGE_EMPTY_QUESTION")
    if not str(challenge.get("reason") or "").strip():
        errors.append("CHALLENGE_EMPTY_REASON")

    revision = challenge.get("revision")
    if challenge.get("disposition") == "RESOLVED_WITH_REVISION":
        if not isinstance(revision, dict):
            errors.append("CHALLENGE_REVISION_REQUIRED")
        else:
            if set(revision) - REVISION_KEYS:
                errors.append("CHALLENGE_REVISION_UNKNOWN_FIELDS")
            if revision.get("dimension_id") not in dimension_ids:
                errors.append(f"CHALLENGE_REVISION_BAD_DIMENSION:{revision.get('dimension_id')}")
            if not isinstance(revision.get("finding_after"), dict):
                errors.append("CHALLENGE_REVISION_MISSING_FINDING_AFTER")
    elif revision is not None:
        errors.append("CHALLENGE_REVISION_NOT_ALLOWED")
    return sorted(set(errors))


def dimension_of(
    challenge: dict[str, Any], everything: dict[str, dict[str, Any]]
) -> str | None:
    target_id = str(challenge.get("target_id"))
    if challenge.get("target_kind") == "FINDING":
        return target_id
    record = everything.get(target_id)
    return str(record["dimension_id"]) if record else None


def blocking_triggers(
    challenge_record: dict[str, Any],
    findings_by_id: dict[str, dict[str, Any]],
    everything: dict[str, dict[str, Any]],
    rules: dict[str, Any],
) -> list[str]:
    """The fixed escalation list. No separate severity axis: BLOCKING is a disposition.

    Triggers come from three places: the rejected revision's own validation errors, the
    challenged evidence record, and the state of the dimension after every revision.
    """
    triggers: list[str] = []
    for error in challenge_record.get("revision_errors") or []:
        code = str(error).split(":", 1)[0]
        if code in rules["challenge"]["blocking_triggers"]:
            triggers.append(code)
        else:
            triggers.append("REVISION_VALIDATION_FAILED")
    dimension_id = dimension_of(challenge_record, everything)
    target_id = str(challenge_record.get("target_id"))
    if challenge_record.get("target_kind") == "EVIDENCE":
        evidence = everything.get(target_id)
        if evidence is not None:
            if evidence.get("evidence_status") != "USABLE":
                triggers.append("EVIDENCE_NOT_USABLE")
            if evidence.get("conflict_status") == "CONFLICT_UNRESOLVED":
                triggers.append("CONFLICT_UNRESOLVED")
    finding = findings_by_id.get(dimension_id or "")
    if finding is not None:
        if check_forbidden_terms(finding, rules):
            triggers.append("FORBIDDEN_INVESTMENT_TERM")
        if finding.get("evidence_score") == 0 and finding.get("revised_from_challenge_ids"):
            triggers.append("NO_BEARING_EVIDENCE_AFTER_REVISION")
    if forbidden_terms_in(str(challenge_record.get("question") or ""), rules):
        triggers.append("FORBIDDEN_INVESTMENT_TERM")
    return sorted(set(triggers))


def model_authored(finding: dict[str, Any]) -> dict[str, Any]:
    """Strip every script-derived field so a revision is compared like for like."""
    stripped = {
        key: value for key, value in finding.items() if key not in DERIVED_FINDING_KEYS
    }
    for field in (
        "supporting_evidence",
        "counter_evidence",
        "management_assertions",
        "watch_indicators",
    ):
        stripped[field] = [
            {key: value for key, value in item.items() if key not in DERIVED_ITEM_KEYS}
            for item in stripped.get(field) or []
            if isinstance(item, dict)
        ]
    return json.loads(json.dumps(stripped))


def apply_challenges(
    challenges: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    by_dimension: dict[str, dict[str, dict[str, Any]]],
    everything: dict[str, dict[str, Any]],
    rules: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    settings = rules["challenge"]
    ladder = settings["downgrade_ladder"]
    revised = json.loads(json.dumps(findings))
    findings_by_id = {str(finding["dimension_id"]): finding for finding in revised}
    dimension_ids = set(findings_by_id)

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for challenge in sorted(
        challenges, key=lambda item: (item.get("round", 0), str(item.get("challenge_id")))
    ):
        errors = check_challenge_schema(challenge, seen, dimension_ids, everything, rules)
        seen.add(str(challenge.get("challenge_id")))
        record = {
            "challenge_id": challenge.get("challenge_id"),
            "round": challenge.get("round"),
            "category": challenge.get("category"),
            "target_kind": challenge.get("target_kind"),
            "target_id": challenge.get("target_id"),
            "question": challenge.get("question"),
            "follow_up_of": challenge.get("follow_up_of"),
            # FR-061: exactly one targeted review per question, written by the script.
            "review_count": 1,
            "disposition": challenge.get("disposition"),
            "reason": challenge.get("reason"),
            "schema_errors": errors,
            "blocking_triggers": [],
            "finding_before": None,
            "finding_after": None,
            "revision_errors": [],
        }
        if errors:
            record["disposition"] = "BLOCKING"
            record["blocking_triggers"] = ["CHALLENGE_SCHEMA_INVALID"]
            records.append(record)
            continue

        dimension_id = dimension_of(challenge, everything)
        disposition = str(challenge["disposition"])

        if disposition == "RESOLVED_WITH_REVISION":
            revision = challenge["revision"]
            target_dimension = str(revision["dimension_id"])
            current = findings_by_id[target_dimension]
            candidate = json.loads(json.dumps(revision["finding_after"]))
            revision_errors = validate_finding(
                candidate,
                target_dimension,
                by_dimension.get(target_dimension, {}),
                everything,
                rules,
            )
            record["finding_before"] = model_authored(current)
            if revision_errors:
                # An illegal revision is not silently dropped and never applied.
                record["revision_errors"] = revision_errors
                record["disposition"] = "BLOCKING"
                records.append(record)
                continue
            candidate["generation_attempts"] = current.get("generation_attempts", 1)
            candidate["revised_from_challenge_ids"] = sorted(
                {*(current.get("revised_from_challenge_ids") or []), str(challenge["challenge_id"])}
            )
            findings_by_id[target_dimension] = candidate
            revised = [
                candidate if str(item["dimension_id"]) == target_dimension else item
                for item in revised
            ]
            record["finding_after"] = model_authored(candidate)
        elif disposition == "UNRESOLVED_DOWNGRADED" and dimension_id in findings_by_id:
            current = findings_by_id[dimension_id]
            record["finding_before"] = model_authored(current)
            current["finding"] = ladder[str(current["finding"])]
            current["revised_from_challenge_ids"] = sorted(
                {*(current.get("revised_from_challenge_ids") or []), str(challenge["challenge_id"])}
            )
            record["finding_after"] = model_authored(current)

        records.append(record)

    # Escalate unresolved dispositions against the fixed trigger list, after every
    # revision has been applied, so NO_BEARING_EVIDENCE_AFTER_REVISION can be seen.
    # Only the final round escalates: an unresolved round-1 question may still be
    # settled by a round-2 follow-up, and the loop cannot run past max_rounds anyway.
    rejected_thresholds = enrich_findings(revised, by_dimension, rules)
    for record in records:
        if record["disposition"] not in {"UNRESOLVED_DOWNGRADED", "BLOCKING"}:
            continue
        hard_failure = bool(record["schema_errors"] or record["revision_errors"])
        if int(record["round"] or 0) < settings["max_rounds"] and not hard_failure:
            continue
        triggers = blocking_triggers(record, findings_by_id, everything, rules)
        record["blocking_triggers"] = sorted(set(record["blocking_triggers"]) | set(triggers))
        if record["blocking_triggers"]:
            record["disposition"] = "BLOCKING"
    return records, revised, rejected_thresholds


def build_challenge_gaps(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for record in records:
        if record["disposition"] not in {"UNRESOLVED_DOWNGRADED", "BLOCKING"}:
            continue
        challenge_id = str(record["challenge_id"])
        gaps.append(
            {
                "gap_id": f"GAP_CHALLENGE_{record['disposition']}_{challenge_id}",
                "origin_stage": ORIGIN_STAGE,
                "gap_kind": "CHALLENGE_UNRESOLVED",
                "question": str(record["question"]),
                "impact_objects": [str(record["target_id"])],
                "current_handling": (
                    f"Disposition {record['disposition']} after one targeted review; "
                    f"blocking triggers: {record['blocking_triggers'] or 'none'}."
                ),
                "confirmation_owner": "user/research_owner",
                "required_evidence": (
                    "Evidence inside the frozen snapshot and no later than as_of that would "
                    "settle the question."
                ),
                "priority": "P1" if record["disposition"] == "BLOCKING" else "P2",
                "status": "OPEN",
            }
        )
    return gaps


def summarize_status(
    records: list[dict[str, Any]], checks: list[dict[str, Any]]
) -> str:
    if any(record["schema_errors"] or record["revision_errors"] for record in records):
        return "FAIL"
    if any(check["status"] == "FAIL" for check in checks):
        return "FAIL"
    if any(
        record["disposition"] in {"UNRESOLVED_DOWNGRADED", "BLOCKING"} for record in records
    ) or any(check["status"] == "WARN" for check in checks):
        return "WARN"
    return "PASS"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the bounded FR-060/FR-061 challenge loop over the D1-D7 findings"
    )
    parser.add_argument("--findings-file", type=Path, required=True)
    parser.add_argument("--analysis-inputs", type=Path, required=True)
    parser.add_argument("--model-challenges", type=Path, required=True)
    parser.add_argument("--rules-file", type=Path, required=True)
    parser.add_argument("--existing-gaps-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        rules = load_rules(args.rules_file)
        rows = read_jsonl(args.analysis_inputs)
        _, by_dimension, everything = load_candidate_index(rows)

        document = yaml.safe_load(args.findings_file.read_text(encoding="utf-8"))
        if document.get("snapshot_id") != SNAPSHOT_ID:
            raise ValueError("findings file is not bound to Snapshot v3")
        findings = list(document.get("findings") or [])
        challenges = load_model_challenges(args.model_challenges)

        records, revised, rejected_thresholds = apply_challenges(
            challenges, findings, by_dimension, everything, rules
        )
        cross_attribution = build_cross_attribution(revised)
        checks = run_validation(
            revised,
            by_dimension,
            everything,
            cross_attribution,
            rejected_thresholds,
            document.get("context_rule_version"),
            rules,
        )
        new_gaps = build_challenge_gaps(records)
        status = summarize_status(records, checks)

        existing = yaml.safe_load(args.existing_gaps_file.read_text(encoding="utf-8"))
        if existing.get("snapshot_id") != SNAPSHOT_ID:
            raise ValueError("existing gap registry is not bound to Snapshot v3")

        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_yaml(
            args.output_dir / "findings-revised.yaml",
            {
                "snapshot_id": SNAPSHOT_ID,
                "analysis_rule_version": document.get("analysis_rule_version"),
                "context_rule_version": document.get("context_rule_version"),
                "distribution_status": rules["distribution_status"],
                "human_review_status": rules["human_review_status"],
                "overall_score": rules["summary_vector"]["overall_score"],
                "summary": build_summary(revised, rules),
                "findings": revised,
                "cross_attribution": cross_attribution,
            },
        )
        write_yaml(
            args.output_dir / "challenges.yaml",
            {
                "snapshot_id": SNAPSHOT_ID,
                "analysis_rule_version": rules["rule_version"],
                "challenge_run_status": status,
                "max_rounds": rules["challenge"]["max_rounds"],
                "rounds_used": sorted({int(record["round"] or 0) for record in records}),
                "challenges": records,
                "revised_findings_validation": checks,
                "new_gap_ids": [gap["gap_id"] for gap in new_gaps],
                "rules_hash": sha256_file(args.rules_file),
                "findings_hash": sha256_file(args.findings_file),
            },
        )
        write_yaml(
            args.output_dir / "gaps.yaml",
            {
                "snapshot_id": SNAPSHOT_ID,
                "gaps": [*(existing.get("gaps") or []), *new_gaps],
            },
        )
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
