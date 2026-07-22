"""Judge the fixed SMIC golden-case run. Three verdicts, no orchestration.

ADR 0005 decision two draws the line this file sits on: the seven-stage order is
knowledge and lives in the `single-stock-research-orchestrator` Skill as a Markdown
constant; stopping, degrading and hashing are deterministic judgments and live here.

Consequently this script does not import a stage script, does not spawn one, and holds
no "what runs next" control flow. It answers three questions and writes each answer to a
file the operator reads:

    preflight          is the input trustworthy, and is the run directory clean?
    gate               what are the five stage statuses, and which report form applies?
    finalize-manifest  what exactly was consumed and produced, by hash?

The run directory is a hard-coded constant, not a parameter: with no user-supplied path
there is nothing to validate, and cleaning removes only the names on the fixed inventory
below -- there is no recursive delete anywhere in this file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

SNAPSHOT_ID = "smic-a283e95e2c9e8068"
EXECUTION_MODE = "FROZEN_REPLAY"

SNAPSHOT_DIR = Path("single-stock-demo-v3")
FROZEN_DIR = Path("frozen-analysis-inputs")
RUN_DIR = Path("single-stock-demo-run")
RULES_DIR = Path("rules")

SNAPSHOT_FILES = [
    "case.yaml",
    "snapshot-manifest.yaml",
    "materials.jsonl",
    "snapshot-inputs.yaml",
    "gaps.yaml",
]
FROZEN_INVENTORY = FROZEN_DIR / "frozen-inventory.yaml"
# The three model-authored files. They are the only frozen inputs that carry a binding
# to assert; the other two are the deterministic record of how they were produced.
FROZEN_MODEL_FILES = [
    "findings-attempt-1.yaml",
    "findings-attempt-2.yaml",
    "challenges-model.yaml",
]

# Every file the run directory may hold. Cleaning deletes exactly these names; anything
# else in an authoritative format stops the run before a single input is consumed.
RUN_FILES = [
    "context.jsonl",
    "retrieval-validation.yaml",
    "normalized-facts.jsonl",
    "normalization-validation.yaml",
    "governed-evidence.jsonl",
    "evidence-validation.yaml",
    "analysis-inputs.jsonl",
    "findings.yaml",
    "analysis-attempts.jsonl",
    "analysis-validation.yaml",
    "challenges.yaml",
    "findings-revised.yaml",
    "gaps.yaml",
    "run-integrity.yaml",
    "run-gate.yaml",
    "report.md",
    "report-validation.yaml",
    "manifest.yaml",
]
AUTHORITATIVE_SUFFIXES = {".yaml", ".jsonl", ".md"}

RULE_FILES = {
    "context_retrieval": "context-retrieval.yaml",
    "accounting": "accounting.yaml",
    "source_governance": "source-governance.yaml",
    "analysis": "analysis.yaml",
    "report": "report.yaml",
}

# The five stage statuses, and where each one is written. Names differ per stage on
# purpose (see the contract map); flattening them here would hide which layer spoke.
STAGE_STATUS_FILES = {
    "retrieval_status": "retrieval-validation.yaml",
    "normalization_run_status": "normalization-validation.yaml",
    "validation_status": "evidence-validation.yaml",
    "analysis_run_status": "analysis-validation.yaml",
    "challenge_run_status": "challenges.yaml",
}
INPUT_MISSING = "FROZEN_ANALYSIS_INPUT_MISSING"
HASH_MISMATCH = "FROZEN_ANALYSIS_HASH_MISMATCH"
BINDING_MISMATCH = "FROZEN_ANALYSIS_BINDING_MISMATCH"


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def report_rules() -> dict[str, Any]:
    """`rules/report.yaml` is the single source for these constants.

    The three reason codes, the execution mode, the governance inputs and the severity
    order are frozen there; this script asserts its own literals against that file rather
    than keeping a second copy that can drift silently.
    """
    rules = read_yaml(RULES_DIR / "report.yaml")
    declared = list(rules.get("integrity_reason_codes") or [])
    if sorted(declared) != sorted([INPUT_MISSING, HASH_MISMATCH, BINDING_MISMATCH]):
        raise ValueError("rules/report.yaml integrity_reason_codes drifted from this script")
    if rules.get("execution_mode") != EXECUTION_MODE:
        raise ValueError("rules/report.yaml execution_mode drifted from this script")
    return rules


def check(name: str, ok: bool, detail: str, reason_code: str | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "status": "PASS" if ok else "FAIL",
        "detail": detail,
        "reason_code": None if ok else reason_code,
    }


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------


def stranger_files() -> list[str]:
    """Authoritative-format files the fixed inventory does not know about.

    Limited to the three frozen formats so Windows noise (Thumbs.db, desktop.ini,
    __pycache__/) never trips it, and non-recursive so nothing below the run directory
    is even looked at.
    """
    if not RUN_DIR.exists():
        return []
    return sorted(
        entry.name
        for entry in RUN_DIR.iterdir()
        if entry.is_file()
        and entry.suffix in AUTHORITATIVE_SUFFIXES
        and entry.name not in RUN_FILES
    )


def clean_run_directory() -> list[str]:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    removed = []
    for name in RUN_FILES:
        target = RUN_DIR / name
        if target.is_file():
            target.unlink()
            removed.append(name)
    return removed


def check_frozen_inputs(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    for entry in inventory.get("files") or []:
        name = str(entry["path"])
        path = FROZEN_DIR / name
        if not path.is_file():
            checks.append(check("frozen_input_present", False, f"missing {name}", INPUT_MISSING))
            continue
        actual = sha256_file(path)
        checks.append(
            check(
                "frozen_input_hash",
                actual == entry["sha256"],
                f"{name} {actual}",
                HASH_MISMATCH,
            )
        )
    return checks


def check_bindings(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    """Two gates and one registration (ADR 0005 decision one).

    The gates are `selection_hash` -- which transitively covers snapshot id, context rule
    version and the selection rules -- and `rules_hash` over rules/analysis.yaml. The
    model identity is registered in the manifest but never gated: it cannot be verified,
    and an unverifiable gate is a decorative one.
    """
    checks: list[dict[str, Any]] = []
    analysis_rules = read_yaml(RULES_DIR / "analysis.yaml")
    presentation_rules = read_yaml(RULES_DIR / "report.yaml")
    selection_hash = inventory.get("selection_hash")
    rule_version = inventory.get("analysis_rule_version")

    checks.append(
        check(
            "snapshot_identity",
            inventory.get("snapshot_id") == SNAPSHOT_ID
            and read_yaml(SNAPSHOT_DIR / "snapshot-manifest.yaml").get("snapshot_id")
            == SNAPSHOT_ID,
            f"expected {SNAPSHOT_ID}",
            BINDING_MISMATCH,
        )
    )
    checks.append(
        check(
            "analysis_rule_version",
            analysis_rules.get("rule_version") == rule_version
            and presentation_rules.get("required_analysis_rule_version") == rule_version,
            f"expected {rule_version}",
            BINDING_MISMATCH,
        )
    )

    validation_path = FROZEN_DIR / "analysis-validation.yaml"
    if validation_path.is_file():
        validation = read_yaml(validation_path)
        checks.append(
            check(
                "frozen_rules_hash",
                validation.get("rules_hash") == sha256_file(RULES_DIR / "analysis.yaml"),
                "rules/analysis.yaml differs from the file the analysis stage ran under",
                BINDING_MISMATCH,
            )
        )
        checks.append(
            check(
                "frozen_selection_hash",
                validation.get("selection_hash") == selection_hash,
                f"expected {selection_hash}",
                BINDING_MISMATCH,
            )
        )

    for name in FROZEN_MODEL_FILES:
        path = FROZEN_DIR / name
        if not path.is_file():
            continue
        document = read_yaml(path)
        checks.append(
            check(
                "model_output_binding",
                document.get("snapshot_id") == SNAPSHOT_ID
                and document.get("selection_hash") == selection_hash
                and document.get("analysis_rule_version") == rule_version,
                f"{name} snapshot/selection/rule binding",
                BINDING_MISMATCH,
            )
        )
    return checks


def check_as_of() -> tuple[dict[str, Any], list[str]]:
    """No material later than `as_of` may enter the run. DEMO_RUN never goes online."""
    as_of = datetime.fromisoformat(str(read_yaml(SNAPSHOT_DIR / "case.yaml")["as_of"]))
    violations: list[str] = []
    with (SNAPSHOT_DIR / "materials.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            material = json.loads(line)
            latest = (material.get("publication_time") or {}).get("latest")
            too_late = latest is not None and datetime.fromisoformat(str(latest)) > as_of
            if too_late or not material.get("as_of_eligible"):
                violations.append(str(material["material_id"]))
    return (
        check(
            "as_of_eligibility",
            not violations,
            f"{len(violations)} material(s) published later than {as_of.isoformat()}",
        ),
        sorted(violations),
    )


def build_gap(gap_id: str, question: str, impact: list[str], handling: str) -> dict[str, Any]:
    return {
        "gap_id": gap_id,
        "origin_stage": "single-stock-research-orchestrator",
        "gap_kind": "RUN_INTEGRITY",
        "question": question,
        "impact_objects": impact,
        "current_handling": handling,
        "confirmation_owner": "user/research_owner",
        "required_evidence": "恢复冻结判断输入或清理运行目录后重跑黄金案例。",
        "priority": "P1",
        "status": "OPEN",
    }


def run_preflight() -> int:
    checks: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    removed: list[str] = []
    as_of_violations: list[str] = []

    strangers = stranger_files()
    checks.append(
        check(
            "run_directory_inventory",
            not strangers,
            f"unexpected authoritative files: {strangers}" if strangers else "clean",
        )
    )
    if strangers:
        # Stop before consuming anything and before deleting anything: an unknown
        # authoritative file may be someone's work, and this is not the place to guess.
        gaps.append(
            build_gap(
                "GAP_RUN_UNEXPECTED_FILE",
                "运行目录出现固定清单以外的权威格式文件，无法确定其来源与作用。",
                strangers,
                "在消费任何输入之前停止；文件保留原样，不静默删除。",
            )
        )
    else:
        removed = clean_run_directory()
        if not FROZEN_INVENTORY.is_file():
            checks.append(
                check("frozen_inventory_present", False, str(FROZEN_INVENTORY), INPUT_MISSING)
            )
        else:
            inventory = read_yaml(FROZEN_INVENTORY)
            checks.extend(check_frozen_inputs(inventory))
            checks.extend(check_bindings(inventory))
            as_of_check, as_of_violations = check_as_of()
            checks.append(as_of_check)

    failed = [item for item in checks if item["status"] == "FAIL"]
    reason_codes = sorted({item["reason_code"] for item in failed if item["reason_code"]})
    if as_of_violations:
        gaps.append(
            build_gap(
                "GAP_RUN_AS_OF_INELIGIBLE",
                "快照内存在发布时间晚于 as_of 或采集准入不合格的材料。",
                as_of_violations,
                "整次运行以完整性失败停止，不产出带结论的报告。",
            )
        )

    write_yaml(
        RUN_DIR / "run-integrity.yaml",
        {
            "snapshot_id": SNAPSHOT_ID,
            "execution_mode": EXECUTION_MODE,
            "integrity_status": "FAIL" if failed else "PASS",
            "reason_codes": reason_codes,
            "unexpected_files": strangers,
            "as_of_violations": as_of_violations,
            "removed_files": removed,
            "checks": checks,
            "gaps": gaps,
        },
    )
    return 1 if failed else 0


# ---------------------------------------------------------------------------
# gate
# ---------------------------------------------------------------------------


def read_stage_statuses(severity: dict[str, int]) -> tuple[dict[str, str | None], list[dict[str, Any]]]:
    statuses: dict[str, str | None] = {}
    checks: list[dict[str, Any]] = []
    for key, name in STAGE_STATUS_FILES.items():
        path = RUN_DIR / name
        value = read_yaml(path).get(key) if path.is_file() else None
        statuses[key] = str(value) if value in severity else None
        checks.append(
            check("stage_status_present", statuses[key] is not None, f"{name}:{key}")
        )
    return statuses, checks


def run_gate() -> int:
    integrity_path = RUN_DIR / "run-integrity.yaml"
    integrity = read_yaml(integrity_path) if integrity_path.is_file() else {}
    rules = report_rules()
    severity = rules["status_severity"]
    governance_inputs = list(rules["governance_status_inputs"])
    statuses, checks = read_stage_statuses(severity)

    reason_codes = list(integrity.get("reason_codes") or [])
    integrity_failed = integrity.get("integrity_status") != "PASS"

    # The real FROZEN_REPLAY gate. Preflight can only compare the frozen bundle against
    # itself; only here does the selection this run actually rebuilt exist to compare.
    frozen_selection = read_yaml(FROZEN_INVENTORY).get("selection_hash") if (
        FROZEN_INVENTORY.is_file()
    ) else None
    replayed_path = RUN_DIR / "analysis-validation.yaml"
    replayed = read_yaml(replayed_path).get("selection_hash") if replayed_path.is_file() else None
    replay_ok = replayed is not None and replayed == frozen_selection
    checks.append(
        check(
            "frozen_replay_selection_binding",
            replay_ok,
            f"frozen {frozen_selection} vs replayed {replayed}",
            BINDING_MISMATCH,
        )
    )
    if not replay_ok:
        reason_codes.append(BINDING_MISMATCH)

    governed = [statuses[key] for key in governance_inputs]
    governance_status = (
        max((value for value in governed if value), key=lambda status: severity[status])
        if all(governed)
        else None
    )

    failed_here = any(item["status"] == "FAIL" for item in checks)
    report_form = (
        "DIAGNOSTIC_ONLY" if integrity_failed or failed_here or governance_status is None
        else "FULL_REPORT"
    )

    write_yaml(
        RUN_DIR / "run-gate.yaml",
        {
            "snapshot_id": SNAPSHOT_ID,
            "execution_mode": EXECUTION_MODE,
            "integrity_status": integrity.get("integrity_status"),
            "stage_statuses": statuses,
            # Analysis and challenge status are shown beside governance_status, never
            # folded into it: ADR 0004 put the analysis-layer guarantee on validation
            # rather than governance, so they are different axes.
            "governance_status_inputs": governance_inputs,
            "governance_status": governance_status,
            "report_form": report_form,
            "distribution_status": "INTERNAL_DEMO_ONLY",
            "human_review_status": "PENDING_HUMAN_REVIEW",
            "reason_codes": sorted(set(reason_codes)),
            "checks": checks,
        },
    )
    return 0


# ---------------------------------------------------------------------------
# finalize-manifest
# ---------------------------------------------------------------------------


def hashed(paths: list[Path]) -> list[dict[str, str]]:
    return [
        {"path": path.as_posix(), "sha256": sha256_file(path)}
        for path in paths
        if path.is_file()
    ]


def run_finalize_manifest() -> int:
    gate = read_yaml(RUN_DIR / "run-gate.yaml")
    rules = {
        key: read_yaml(RULES_DIR / name)
        for key, name in RULE_FILES.items()
    }

    write_yaml(
        RUN_DIR / "manifest.yaml",
        {
            "snapshot_id": SNAPSHOT_ID,
            "execution_mode": EXECUTION_MODE,
            # The one field that legitimately differs between two clean replays. Every
            # managed artefact hash below is identical across runs.
            "generated_at": datetime.now().astimezone().isoformat(),
            "governance_status": gate.get("governance_status"),
            "stage_statuses": gate.get("stage_statuses"),
            "distribution_status": "INTERNAL_DEMO_ONLY",
            "human_review_status": "PENDING_HUMAN_REVIEW",
            "report_form": gate.get("report_form"),
            "rule_versions": {
                key: document.get("rule_version") for key, document in rules.items()
            },
            "frozen_inputs": {
                "source_snapshot": {
                    "snapshot_id": SNAPSHOT_ID,
                    "files": hashed([SNAPSHOT_DIR / name for name in SNAPSHOT_FILES]),
                },
                "analysis_inputs": {
                    "execution_mode": EXECUTION_MODE,
                    # Registered, never gated: an unverifiable identity makes a fake gate.
                    "model_identity": read_yaml(FROZEN_INVENTORY).get(
                        "model_identity", "UNRECORDED"
                    ),
                    "files": hashed(
                        [FROZEN_INVENTORY]
                        + [
                            FROZEN_DIR / entry["path"]
                            for entry in read_yaml(FROZEN_INVENTORY).get("files") or []
                        ]
                    ),
                },
                "rules": hashed([RULES_DIR / name for name in RULE_FILES.values()]),
            },
            "generated_outputs": {
                # manifest.yaml lists every other file but never its own hash; two runs
                # are compared by hashing this file from the outside.
                "files": hashed(
                    [RUN_DIR / name for name in RUN_FILES if name != "manifest.yaml"]
                ),
            },
            "tool_versions": {
                "python": sys.version.split()[0],
                "scripts": hashed(sorted(Path("scripts").glob("*.py"))),
            },
        },
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Judge the fixed SMIC golden-case run. This tool decides nothing about what "
            "runs next; the seven-stage order lives in the orchestrator Skill."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight", help="clean the run directory and verify frozen inputs")
    subparsers.add_parser("gate", help="read the five stage statuses and decide the report form")
    subparsers.add_parser("finalize-manifest", help="hash consumed and produced files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    commands = {
        "preflight": run_preflight,
        "gate": run_gate,
        "finalize-manifest": run_finalize_manifest,
    }
    try:
        return commands[args.command]()
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
