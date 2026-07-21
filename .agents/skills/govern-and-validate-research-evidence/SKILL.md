---
name: govern-and-validate-research-evidence
description: Govern and validate research evidence for the fixed SMIC Snapshot v3. Use when Ticket 04 needs to turn normalized facts into governed evidence with source tier, claim type, source group, evidence status, whitelisted conflict handling, and the FR-043 deterministic validation.
---

# Govern and Validate Research Evidence

Read `CONTEXT.md`, `.scratch/single-stock-demo/spec.md`, and `docs/adr/0003-scope-conflict-detection-to-whitelisted-metric-facts.md`. Accept only normalized facts and context governed from Snapshot v3 `smic-a283e95e2c9e8068`; never alter the frozen snapshot.

## Run the fixed stage

1. Require `normalized-facts.jsonl`, `context.jsonl`, and the appended `gaps.yaml` from Ticket 03. `context.jsonl` is mandatory because `locator_chain_consistency` re-checks each `source_chunk_text_hash`.
2. Use `rules/source-governance.yaml` (`rule_version: smic-v3-source-governance-v1`) as the only source, conflict, and validation rule source. Do not copy these rules elsewhere or add a rule DSL/plugin.
3. Run:

   ```text
   python scripts/govern_validate_research_evidence.py --snapshot-dir single-stock-demo-v3 --facts-file <derived-output-dir>/normalized-facts.jsonl --context-file <derived-output-dir>/context.jsonl --rules-file rules/source-governance.yaml --existing-gaps-file <derived-output-dir>/gaps.yaml --output-dir tmp/ticket04-final
   ```

4. Verify `governed-evidence.jsonl` has one record per fact (`fact_id : evidence_id` 1:1, deterministic), every record carries source tier, claim type, source group, evidence status, permitted use, and non-empty conflict fields, and lineage `fact_id -> chunk_id -> material_id` is intact.
5. Verify conflict detection ran only on the manually verified record-level whitelist, that the seven conflict run statistics are reported (candidate/eligible/excluded-by-reason/comparable-group/comparison-pair/detected/unresolved), and that any unresolved conflict is `CONFLICT_UNRESOLVED` with each version preserved.
6. Verify `evidence-validation.yaml` reports all 13 FR-043 named checks with PASS/WARN/FAIL and reasons. `FAIL` (integrity/determinism) keeps diagnostics but bars affected data from the usable set; `QUARANTINED`/`CONFLICT_UNRESOLVED`/new gaps produce `WARN`; the expected real-run status is `WARN` with two matching clean-rebuild hashes.
7. Preserve prior gaps and append the aggregate missing-`metric_id` gap plus the upstream Ticket 03 period-mislabel gap in the single derived `gaps.yaml`.

## Keep the stage boundary

Govern source tier, claim type, source group, evidence status, permitted use, and whitelisted conflicts only. Source tier reflects originality and traceability, not truth; `locator_chain_consistency` does not re-verify locator accuracy (inherited from Ticket 03 retrieval acceptance); no new formulas are introduced. Do not decide findings, scores, or report language, and do not invoke another stage Skill.
