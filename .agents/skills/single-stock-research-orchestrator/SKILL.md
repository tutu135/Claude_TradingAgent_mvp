---
name: single-stock-research-orchestrator
description: Run the fixed SMIC golden case end to end in FROZEN_REPLAY mode. Use when Ticket 06 needs the seven stages executed in their frozen order, the integrity preflight, the governance gate, the report form decision and the final manifest.
---

# Single Stock Research Orchestrator

Read `CONTEXT.md`, `.scratch/single-stock-demo/spec.md`, and
`docs/adr/0005-replay-frozen-judgment-and-keep-the-orchestrator-a-validator.md`.

This Skill **is** the orchestrator. The seven-stage order below is a text constant in this
file, not a configurable DAG: there is no workflow engine, no queue, no scheduler, no
database, no model router and no plugin system anywhere in this repository, and none may be
added. `scripts/validate_demo_run.py` is only a judge — three subcommands, no stage import,
no subprocess call, no "what runs next" control flow. Every stage below is invoked
explicitly, here, by a human or an agent reading this list.

## Execution mode: `FROZEN_REPLAY`

The judgment layer is **not** re-executed. `frozen-analysis-inputs/` holds the frozen model
outputs — read-only, version-controlled, hash- and binding-checked — and no model call
happens during a run. What the end-to-end run proves is the deterministic replay from
frozen inputs to final artefacts: two clean runs produce a byte-identical `report.md` and a
`manifest.yaml` identical except for `generated_at`.

The judgment layer's own credibility is carried by `analysis-validation.yaml` plus the full
attempt trail in `analysis-attempts.jsonl` (ADR 0004). Ticket 06 does not reopen that.

## The seven stages, in this order

Run from the repository root. `$R` is `single-stock-demo-run/`, the only writable
destination; the snapshot and the frozen analysis inputs stay read-only.

**0. Preflight** — clean the run directory, verify the frozen inputs and the bindings.

```text
python scripts/validate_demo_run.py preflight
```

If this exits non-zero the run stops here: **skip stages 1–6 entirely**, then run the
closing three commands anyway — `gate`, `generate_research_report.py`,
`finalize-manifest`. `gate` handles absent stage statuses and sets
`report_form: DIAGNOSTIC_ONLY`; running it keeps the manifest and the report reading the
same verdict. An integrity failure means the inputs are untrustworthy, so no report may
carry a conclusion.

**1. Acquire (verify only)** — the snapshot is already frozen; `DEMO_RUN` re-verifies its
identity, hashes, `as_of` and file completeness. It never goes online and never refreshes.

```text
python scripts/acquire_research_materials.py DEMO_RUN --case-file single-stock-demo-v3/case.yaml --snapshot-dir single-stock-demo-v3
```

**2. Govern research context**

```text
python scripts/govern_research_context.py --snapshot-dir single-stock-demo-v3 --rules-file rules/context-retrieval.yaml --acceptance-file tests/fixtures/retrieval-acceptance-smic-v3.yaml --output-dir $R
```

**3. Normalize research facts**

```text
python scripts/normalize_research_facts.py --snapshot-dir single-stock-demo-v3 --context-file $R/context.jsonl --retrieval-file $R/retrieval-validation.yaml --rules-file rules/accounting.yaml --existing-gaps-file single-stock-demo-v3/gaps.yaml --output-dir $R
```

**4. Govern and validate research evidence**

```text
python scripts/govern_validate_research_evidence.py --snapshot-dir single-stock-demo-v3 --facts-file $R/normalized-facts.jsonl --context-file $R/context.jsonl --rules-file rules/source-governance.yaml --existing-gaps-file $R/gaps.yaml --output-dir $R
```

**5. Analyze and score findings** — `select` rebuilds the candidate sets deterministically;
`finalize` consumes the frozen model outputs. The `prompt` step and the model call are
**not** part of a run.

```text
python scripts/analyze_and_score_research_findings.py select --snapshot-dir single-stock-demo-v3 --context-file $R/context.jsonl --facts-file $R/normalized-facts.jsonl --evidence-file $R/governed-evidence.jsonl --rules-file rules/analysis.yaml --existing-gaps-file $R/gaps.yaml --output-dir $R
python scripts/analyze_and_score_research_findings.py finalize --analysis-inputs $R/analysis-inputs.jsonl --model-findings frozen-analysis-inputs/findings-attempt-1.yaml --model-findings frozen-analysis-inputs/findings-attempt-2.yaml --rules-file rules/analysis.yaml --existing-gaps-file $R/gaps.yaml --output-dir $R
```

**6. Challenge findings** — at most two rounds, one targeted review per question. Both caps
are enforced inside the challenge script, not here.

```text
python scripts/challenge_research_findings.py --findings-file $R/findings.yaml --analysis-inputs $R/analysis-inputs.jsonl --model-challenges frozen-analysis-inputs/challenges-model.yaml --rules-file rules/analysis.yaml --existing-gaps-file $R/gaps.yaml --output-dir $R
```

**Gate** — read the five stage statuses, compose `governance_status`, decide the form.

```text
python scripts/validate_demo_run.py gate
```

**7. Generate the report**, then seal the run.

```text
python scripts/generate_research_report.py
python scripts/validate_demo_run.py finalize-manifest
```

Stage Skills never call each other. Each stage reads the previous stage's file from `$R`.

## Stop and degrade

There is no such thing as a silent stop: `report.md` is always produced, in exactly one of
two forms recorded in `manifest.yaml`.

| Failure | Form | Content |
|---|---|---|
| **Integrity** — frozen input missing / hash mismatch / binding mismatch, snapshot identity mismatch, a file outside the fixed inventory in the run directory, or a material published after `as_of` | `DIAGNOSTIC_ONLY` | Failure banner, failed checks, reason code, gap references. **No D1–D7 conclusion.** |
| **Content** — any run status `WARN`/`FAIL`, or `governance_status=FAIL` | `FULL_REPORT` | The ten frozen sections, prominently flagged; quarantined data excluded, failed dimensions `UNKNOWN`. |

The distinction is the nature of the failure, not its severity: untrustworthy input yields
diagnostics only, while an unsatisfactory conclusion yields a report that says so. Reason
codes are exactly three: `FROZEN_ANALYSIS_INPUT_MISSING`, `FROZEN_ANALYSIS_HASH_MISMATCH`,
`FROZEN_ANALYSIS_BINDING_MISMATCH`. Content-level failures use the existing per-stage run
statuses and get no code of their own.

`governance_status` is the worst of `retrieval_status`, `normalization_run_status` and
`validation_status`. Analysis and challenge status are shown beside it, never folded in.

## Scope recognition

Deterministic, because the orchestrator makes no model call. Three rules, applied in order,
against constants frozen in `rules/report.yaml` and `rules/analysis.yaml`:

- **R1** hits the forbidden-output term list → `OUT_OF_SCOPE_FORBIDDEN_OUTPUT`. This one has
  teeth: refuse, and do not repeat the wording.
- **R2** names an entity outside the fixed subject → `OUT_OF_SCOPE_OTHER_SUBJECT`, disclaim.
- **R3** targets a period later than `as_of` → `OUT_OF_SCOPE_BEYOND_AS_OF`, disclaim.

An out-of-scope question does not cancel the run: the golden case is executed as usual and
the report opens with the fixed statement that this Demo studies only its own research
question and answers nothing beyond it. Six frozen example questions — three in scope,
three not — are classified at render time and printed in the report.

## Verify a completed run

1. `run-integrity.yaml` is `PASS` and `run-gate.yaml` shows the expected five statuses,
   `governance_status`, and `report_form`.
2. `report-validation.yaml` shows `leaked_unbound_numeric_mentions: 0`,
   `forbidden_output_scan.hits: []` and an empty `traceability.unresolved`.
3. `manifest.yaml` partitions `frozen_inputs` from `generated_outputs`, records rule
   versions, statuses, `distribution_status: INTERNAL_DEMO_ONLY`,
   `human_review_status: PENDING_HUMAN_REVIEW` and the report form — and never its own hash.
4. Run it a second time from the same clean directory: `report.md` is byte-identical and
   every hash in `manifest.yaml` matches. Only `generated_at` differs.

## Keep the boundary

Sequence and stop/degrade decisions only. Do not add a stage, do not put the order into a
script, do not call a model, do not write research content, and do not build a generic
runner around any of this.
