---
name: govern-research-context
description: Build and validate the fixed deterministic research context for the single-stock SMIC Demo. Use when Ticket 03 needs to verify Snapshot v3, create structure-atomic PDF/HTML/transcript chunks, run the frozen BM25 query families, or reproduce the locator-level RAG acceptance result.
---

# Govern Research Context

Read `CONTEXT.md`, `.scratch/single-stock-demo/spec.md`, and `contracts/contract-map.md`. Treat Snapshot v3 `smic-a283e95e2c9e8068` as the only runtime input and keep the frozen snapshot unchanged.

## Run the fixed stage

1. Use `single-stock-demo-v3/` only. Do not browse, refresh, merge v1/v2, or read a compatibility CSV as a source.
2. Use `rules/context-retrieval.yaml` and `tests/fixtures/retrieval-acceptance-smic-v3.yaml` without runtime query rewriting.
3. Write derived artifacts outside the frozen snapshot:

   ```text
   python scripts/govern_research_context.py --snapshot-dir single-stock-demo-v3 --rules-file rules/context-retrieval.yaml --acceptance-file tests/fixtures/retrieval-acceptance-smic-v3.yaml --output-dir <derived-output-dir>
   ```

4. Verify `context.jsonl` contains every governed structure atom, stable locators and chunk IDs, structural-filter records, query tokens, ranks, scores, and selection reasons.
5. Verify `retrieval-validation.yaml` is bound to the v3 snapshot, query-rule version, and acceptance version. Require the recorded MUST/SHOULD recall, per-query precision, negative control, locator, numeric-context, and clean-rebuild checks.
6. If the status is `FAIL`, stop this stage and preserve the diagnostics. If it is `WARN`, preserve the scoped retrieval gaps; do not silently add Embeddings or change the frozen annotations.

## Keep the stage boundary

Judge retrieval relevance only. Do not assign source tiers, claim types, credibility, truth, evidence eligibility, conflicts, findings, scores, or report conclusions. Do not invoke another stage Skill.
