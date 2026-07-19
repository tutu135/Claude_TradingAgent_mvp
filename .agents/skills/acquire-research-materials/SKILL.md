---
name: acquire-research-materials
description: Build or verify the fixed SMIC frozen research snapshot for the single-stock Demo. Use for SNAPSHOT_BUILD acquisition, source-use and as_of intake checks, PDF/HTML/spreadsheet/text parsing, coverage gaps, or DEMO_RUN verification of the already frozen inputs.
---

# Acquire Research Materials

Use the fixed contracts in `contracts/contract-map.md`, the accepted requirements in `.scratch/single-stock-demo/spec.md`, ADR-0001, and ADR-0002. Do not restate or extend their business rules.

## Select the mode

- `SNAPSHOT_BUILD`: prepare a new immutable snapshot from permitted public downloads or user-prepared local files.
- `DEMO_RUN`: verify and read the frozen snapshot only. Do not browse, download, refresh, or accept replacement material.

## Build a snapshot

1. Use the pinned runtime packages in `requirements.txt`, then read the target snapshot's `case.yaml` and `snapshot-inputs.yaml`.
2. Apply the acquisition boundary in Spec FR-010 through FR-015 and ADR-0002. Keep this Skill as an execution guide; do not copy those business rules here.
3. If material requires registration, login, a CAPTCHA, authenticated export, or other user-managed access, stop and ask the user to obtain it manually outside the Demo. Never request or save an account, password, Cookie, Token, header, or session identifier.
4. Run:

   ```text
   python scripts/acquire_research_materials.py SNAPSHOT_BUILD --case-file single-stock-demo-v2/case.yaml --intake-file single-stock-demo-v2/snapshot-inputs.yaml --output-dir single-stock-demo-v2 --created-at <ISO-8601-with-timezone>
   ```

5. For PDFs, retain the parser outputs needed by the contract. Render selected pages only into `tmp/pdfs/` for visual checking. Never treat renderings as formal sources.
6. Verify `snapshot-manifest.yaml`, `materials.jsonl`, parsed auxiliary files, acquisition target mappings, Candidate Holding Area counts, Search Saturation, gaps, and hashes. A frozen output directory cannot be rebuilt in place; use a new directory for changed material.

## Run the Demo

Run:

```text
python scripts/acquire_research_materials.py DEMO_RUN --case-file single-stock-demo-v2/case.yaml --snapshot-dir single-stock-demo-v2
```

Use the stop conditions in Spec FR-010 through FR-015 and the `materials.jsonl`/`snapshot-manifest.yaml` contracts. Do not repair a Demo run with Web data.

## Keep the stage boundary

Output research materials and intake metadata only. Do not create context chunks, normalized facts, governed evidence, findings, challenges, or reports, and do not invoke another stage Skill.
