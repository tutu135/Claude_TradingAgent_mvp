---
name: analyze-and-score-research-findings
description: Form and score the D1-D7 research findings for the fixed SMIC Snapshot v3. Use when Ticket 05 needs the deterministic candidate-set selection, the bounded per-dimension model judgment, and the derived evidence scores, reason codes and analysis validation.
---

# Analyze and Score Research Findings

Read `CONTEXT.md`, `.scratch/single-stock-demo/spec.md`, and `docs/adr/0004-layer-analysis-into-deterministic-selection-and-bounded-model-judgment.md`. Accept only governed evidence from Snapshot v3 `smic-a283e95e2c9e8068`; never alter the frozen snapshot. This stage forms findings only — it does not challenge them and does not write the report.

## The three layers

Selection and validation are deterministic scripts. The judgment between them is a model call, so the findings are **not** bit-reproducible; the guarantee comes from `analysis-validation.yaml` plus the full attempt trail, not from matching hashes.

### 1. Select (deterministic, hashable)

```text
python scripts/analyze_and_score_research_findings.py select \
  --snapshot-dir single-stock-demo-v3 \
  --context-file <ticket03-out>/context.jsonl \
  --facts-file <ticket03-out>/normalized-facts.jsonl \
  --evidence-file <ticket04-out>/governed-evidence.jsonl \
  --rules-file rules/analysis.yaml \
  --existing-gaps-file <ticket04-out>/gaps.yaml \
  --output-dir tmp/ticket05-inputs
```

The selection unit is the chunk, not the proposition: retrieval scores live on chunks, so a plain top-N over propositions collapses into one chunk and one source group. Each dimension seeds up to three source groups, then fills by score until the 60,000-character budget (10% overshoot allowed) or 64 chunks. All usable numerics of the dimension are kept and do not consume the budget. `SELECTION_SUMMARY` is the first record of `analysis-inputs.jsonl` and the only audit record for this step — there is no separate summary file to keep in sync.

### 2. Judge (model, one bounded call per dimension)

Build the prompts from the frozen candidate set — never hand the model anything else:

```text
python scripts/analyze_and_score_research_findings.py prompt \
  --analysis-inputs tmp/ticket05-inputs/analysis-inputs.jsonl \
  --rules-file rules/analysis.yaml --output-dir tmp/ticket05-prompts
```

One dimension per call, no cross-dimension context. The model returns `finding`, `finding_statement`, `supporting_evidence` (role `PRIMARY_SUPPORT`/`CONTEXT`), `counter_evidence`, `alternative_explanations`, `limitations`, `gaps`, `management_assertions`, and for D7 `watch_indicators`. It **never** returns a score, an aggregate, or a field outside that list. Freeze the outputs into one YAML file per attempt (`snapshot_id` + `findings:`); they are inputs to the next step, not regenerated on every run.

Tell the model plainly: a `MANAGEMENT_ASSERTION` claim type may only appear under `management_assertions`; causal wording needs a named source in the same sentence; an honest `UNKNOWN` is a correct answer.

### 3. Finalize (deterministic)

```text
python scripts/analyze_and_score_research_findings.py finalize \
  --analysis-inputs tmp/ticket05-inputs/analysis-inputs.jsonl \
  --model-findings tmp/ticket05-model/findings-attempt-1.yaml \
  --rules-file rules/analysis.yaml \
  --existing-gaps-file tmp/ticket05-inputs/gaps.yaml \
  --output-dir tmp/ticket05-final
```

The script recomputes `evidence_score` from the selected evidence, writes the constant `overall_score: NOT_APPLICABLE`, and runs the twelve declared checks. Pass `--model-findings` a second time for the one permitted regeneration; only the failing dimension is re-read from it, and the second file needs only the failing dimensions.

## Verify

1. Seven findings, ids and order matching `rules/analysis.yaml`. Scores are 0-3 and derived, never copied from the model; `evidence_score_basis` shows the source groups and cross-period metrics behind each one.
2. Score 0 forces `UNKNOWN`. The reverse does not hold — `UNKNOWN` at 1-2 is legal when the evidence is present but directionless.
3. Every cited `evidence_id` is inside that dimension's candidate set and `USABLE`. A rejected attempt is summarised in `rejected_attempts` and kept in full in `analysis-attempts.jsonl`; it never reaches `findings.yaml`. Reference legality, forbidden terms, causal attribution, management-assertion placement and the score-0 binding are all part of that per-attempt gate, so any of them can trigger the one regeneration.
4. `frozen_rule_binding` PASSes — the bearing metric whitelist matches ticket 05 section 3 item by item and the context is `smic-v3-context-retrieval-v3`. This is the gate against making an empty dimension look load-bearing by editing rules.
5. D2/D5/D7 carry no bearing numeric and D3 carries exactly one. That is v3's real capacity; disclose it, never repair it. Each empty whitelist emits `GAP_ANALYSIS_NO_BEARING_METRIC_<dimension>` — including the D7 one recording that operating-cash-flow records exist in the snapshot but no frozen D7 query retrieves them.
6. Unfounded D7 thresholds survive as `proposed_threshold` with `threshold_basis: REJECTED_NO_BASIS` and a gap — not deleted, not invented.
7. Two failed attempts force `finding=UNKNOWN`, `evidence_score=0`, `finding_reason_code=ANALYSIS_VALIDATION_FAILED` and `analysis_run_status=FAIL`. That code exists so a forced zero is not misread as `NO_BEARING_EVIDENCE`.

## Keep the stage boundary

Form and score findings only. Do not run the challenge loop, do not write `report.md`, and do not invoke another stage Skill. No buy/sell/hold, position, target price, valuation anchor, investment-attractiveness judgment or system forecast may appear in any output — the schema has no field for it and the term list is a hard gate.
