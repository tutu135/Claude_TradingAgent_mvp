---
name: generate-research-report
description: Render the internal Markdown report and its validation record for the fixed SMIC golden case. Use when Ticket 06 needs the ten frozen sections, the evidence tables that carry every number, the whole-sentence narrative filter, and the DIAGNOSTIC_ONLY form after an integrity failure.
---

# Generate Research Report

Read `CONTEXT.md`, `.scratch/single-stock-demo/spec.md` (FR-070..FR-073, FR-080), and
`docs/adr/0005-replay-frozen-judgment-and-keep-the-orchestrator-a-validator.md`. Run this
only after `single-stock-research-orchestrator` has produced `run-gate.yaml`. Presentation
rules live in `rules/report.yaml` and nowhere else; no upstream stage reads that file.

## Run

```text
python scripts/generate_research_report.py
```

No arguments. The run directory `single-stock-demo-run/` is a hard-coded constant, and the
form to render (`FULL_REPORT` or `DIAGNOSTIC_ONLY`) is read from `run-gate.yaml` — this
Skill does not decide it. Outputs are `report.md`, `report-validation.yaml`, and one
appended gap in `gaps.yaml` when the government-funding sensitivity has no records.

## What the report may and may not contain

**Numbers live in the evidence table.** Each row carries `fact_id`, `evidence_id`,
`metric_id`, value, base unit value, raw value text, unit, currency, scale, accounting
basis, period, source, publication time, locator, `claim_type` and gap references — so a
single blurred footnote can never cover several numbers of different vintage (FR-071).

**Model prose is filtered by whole sentence.** A sentence carrying a number that is not
bound to a row does not enter the report; the sentence is dropped entire and the paragraph
ends with the fixed notice pointing at the evidence table. Deleting digits instead would
leave "毛利率由上升到" — still a claim, now a false one. The frozen model output on disk is
never modified. D1's statement keeps roughly a fifth of its characters; that is the
accepted price of honesty, not a defect to repair.

**Nothing is manufactured.** Snapshot v3 has zero quarantined records, zero conflict groups
and zero government-funding sensitivity values. Print the zeros with their reason. The
mechanisms behind them are proved by synthetic fixtures in
`tests/test_generate_research_report_cli.py`, never by inventing data.

**Never emitted:** buy/sell/hold, position advice, target price, valuation anchor,
investment-attractiveness judgment, or a system forecast. No PDF, web page, dashboard or
API. No content hash in `report.md` — hashes belong in `manifest.yaml`, so the rendering
layer stays decoupled from the execution mode.

**Never translated:** machine identifiers (`evidence_id`, `fact_id`, `metric_id`) must grep
straight back into the JSONL, and a translated source span is new text with no provenance.
Only the glossary in section 10 explains the enumerations in Chinese.

## Verify

1. `report-validation.yaml` reports
   `narrative_numeric_sanitization.leaked_unbound_numeric_mentions: 0`. Do not settle for
   "the scanner ran" — the assertion is that nothing leaked into the rendered prose.
2. Ten sections in the frozen FR-070 order, preceded by the three separated metadata
   blocks: research question, analysis framework, process status.
3. `governance_status` appears beside — never merged with — `analysis_run_status` and
   `challenge_run_status`.
4. `traceability.unresolved` is empty and every evidence row shows `evidence_id`,
   `fact_id`, `chunk_id` and `material_id`.
5. `forbidden_output_scan.hits` is empty; the refused scope example is labelled but its
   wording is not reproduced.
6. `formula_recomputation` recomputes each IFRS/CAS bridge from its input facts. Four pass
   and three are UNKNOWN on v3; the UNKNOWN ones are basis mismatches, not failures to
   repair. There are no `DERIVATION` records in this pipeline, so never call these
   derivations.
7. `DIAGNOSTIC_ONLY` contains the failure banner, the failed checks, the reason codes and
   the gap references — and no dimension, direction, score or evidence row at all.

## Keep the stage boundary

Render only. Do not re-run a stage, do not recompute a finding or a score, do not decide
the report form, and do not invoke another stage Skill.
