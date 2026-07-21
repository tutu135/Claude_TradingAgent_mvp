---
name: challenge-research-findings
description: Run the bounded adversarial challenge loop over the D1-D7 findings for the fixed SMIC Snapshot v3. Use when Ticket 05 needs the four challenge categories, the four dispositions, one targeted review per question, at most two rounds, and the re-validated revised findings.
---

# Challenge Research Findings

Read `CONTEXT.md`, `.scratch/single-stock-demo/spec.md` (FR-060/FR-061), and `docs/adr/0004-layer-analysis-into-deterministic-selection-and-bounded-model-judgment.md`. Run this only after `analyze-and-score-research-findings` has produced `findings.yaml`. The challenged side may use only the frozen snapshot `smic-a283e95e2c9e8068` and material published no later than `as_of`.

## Write the challenges

The model writes the questions and the disposition reasoning; every loop control is script logic. Each challenge is one mapping:

```yaml
challenge_id: CH_001
round: 1                      # 1 or 2, never more
category: SOURCE_TRACEABILITY | ACCOUNTING_COMPARABILITY | ATTRIBUTION_CAUSALITY | FALSIFICATION_MISSING_EVIDENCE
target_kind: FINDING | EVIDENCE
target_id: D1_PROFITABILITY_CHANGE   # a dimension id, or an evidence_id in the candidate set
question: ...
disposition: RESOLVED_NO_CHANGE | RESOLVED_WITH_REVISION | UNRESOLVED_DOWNGRADED | BLOCKING
reason: ...                   # what the one targeted review established
follow_up_of: CH_001          # optional, round 2 only
revision:                     # RESOLVED_WITH_REVISION only
  dimension_id: ...
  finding_after: {...}        # a full model-authored finding, no derived fields
```

Every question must name a real `finding_id` or `evidence_id`. A generic bull/bear argument is not a challenge; if it carries investment language it escalates straight to `BLOCKING`.

Build `finding_after` by copying the current finding, stripping the script-derived fields, and editing it — do not retype it. The challenge itself never rewrites a finding: the script applies the revision and re-validates it against exactly the checks the first version faced.

## Run

```text
python scripts/challenge_research_findings.py \
  --findings-file tmp/ticket05-final/findings.yaml \
  --analysis-inputs tmp/ticket05-inputs/analysis-inputs.jsonl \
  --model-challenges tmp/ticket05-model/challenges-model.yaml \
  --rules-file rules/analysis.yaml \
  --existing-gaps-file tmp/ticket05-final/gaps.yaml \
  --output-dir tmp/ticket05-final
```

`findings.yaml` is preserved untouched; the result lands in `findings-revised.yaml`.

## Verify

1. Every record carries `review_count: 1` — one targeted review per question — and `rounds_used` never exceeds two.
2. `RESOLVED_WITH_REVISION` keeps `finding_before`, `finding_after` and `reason`; the revised dimension lists the triggering `challenge_id` in `revised_from_challenge_ids`, and its score is recomputed, never carried over.
3. An invalid revision is not applied and not silently dropped: the disposition becomes `BLOCKING`, `revision_errors` holds the reasons, and the run status is `FAIL`.
4. `UNRESOLVED_DOWNGRADED` moves the finding one step down the fixed ladder (SUPPORTED/NOT_SUPPORTED -> MIXED -> UNKNOWN) and writes a gap. Escalation against the fixed trigger list is evaluated at the final round — a round-1 question may still be settled by a round-2 follow-up — except for a schema or revision failure, which blocks immediately. There is no `severity` field: `BLOCKING` is already a disposition.
5. `revised_findings_validation` reports all twelve analysis checks over the revised findings.
6. Unresolved and blocking challenges both reach `gaps.yaml`. Nothing loops a third time.

## Keep the stage boundary

Challenge existing findings only. Do not re-select candidate evidence, do not re-run the analysis model layer, do not write `report.md`, and do not invoke another stage Skill.
