---
name: normalize-research-facts
description: Normalize candidate context from the fixed SMIC Snapshot v3 into atomic, traceable facts. Use when Ticket 03 needs Decimal-preserving observations, qualified text propositions, fixed-whitelist derivations, IFRS/CAS bridge checks, normalization gaps, or deterministic normalization validation.
---

# Normalize Research Facts

Read `CONTEXT.md`, `.scratch/single-stock-demo/spec.md`, and `contracts/contract-map.md`. Accept only context governed from Snapshot v3 `smic-a283e95e2c9e8068`; never alter the frozen snapshot.

## Run the fixed stage

1. Require `context.jsonl` and `retrieval-validation.yaml` from `govern-research-context`. A global retrieval `FAIL` blocks normalization.
2. Use `rules/accounting.yaml` as the only mapping, accounting, adjustment, and derivation rule source. Do not fuzzy-map labels or execute free-form formulas.
3. Run:

   ```text
   python scripts/normalize_research_facts.py --snapshot-dir single-stock-demo-v3 --context-file <derived-output-dir>/context.jsonl --retrieval-file <derived-output-dir>/retrieval-validation.yaml --rules-file rules/accounting.yaml --existing-gaps-file single-stock-demo-v3/gaps.yaml --output-dir <derived-output-dir>
   ```

4. Verify `normalized-facts.jsonl` contains only `NUMERIC_OBSERVATION`, `TEXT_PROPOSITION`, and `DERIVATION`; every record keeps v3 lineage and `claim_type=UNASSESSED`.
5. Verify source values remain separate from derived values, Decimal strings retain display precision, UNKNOWN/TBD values have gaps, currency conversions remain unavailable without a frozen rate, and government funding adjustments remain parallel sensitivities.
6. Verify `normalization-validation.yaml` reports no duplicate fact IDs and matching clean-rebuild hashes. `PARTIAL` or `BLOCKED` records produce run `WARN`; integrity or determinism failures produce `FAIL`.
7. Preserve acquisition gaps and append normalization gaps in the single derived `gaps.yaml`.

## Keep the stage boundary

Normalize structure and accounting/technical meaning only. Do not decide truth, source tier, evidence eligibility, conflicts, findings, scores, or report language. Do not invoke another stage Skill.
