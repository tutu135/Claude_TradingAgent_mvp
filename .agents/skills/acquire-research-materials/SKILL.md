---
name: acquire-research-materials
description: Build or verify the fixed SMIC frozen research snapshot for the single-stock Demo. Use for SNAPSHOT_BUILD acquisition, source-use and as_of intake checks, PDF/HTML/spreadsheet/text parsing, coverage gaps, or DEMO_RUN verification of the already frozen inputs.
---

# Acquire Research Materials

Use the fixed contracts in `contracts/contract-map.md`, the accepted requirements in `.scratch/single-stock-demo/spec.md`, and ADR-0001. Do not restate or extend their business rules.

## Select the mode

- `SNAPSHOT_BUILD`: prepare a new immutable snapshot from permitted public downloads or user-prepared local files.
- `DEMO_RUN`: verify and read the frozen snapshot only. Do not browse, download, refresh, or accept replacement material.

## Build a snapshot

1. Use the pinned runtime packages in `requirements.txt`, then read `single-stock-demo/case.yaml` and `single-stock-demo/snapshot-inputs.yaml`.
2. Check source terms and `usage_basis` before acquisition. Accept only `USABLE` entries whose publisher, publication time, source entrance, precise locator, and terms entrance are present.
3. Apply the personal, non-commercial, local, non-distributed assumption. If free material requires registration, login, a CAPTCHA, or an authenticated export, stop and ask the user to obtain it manually. Never request or save an account, password, Cookie, Token, header, or session identifier.
4. Reject or restrict disallowed sources before download. Exclude anything published after the case `as_of`.
5. Run:

   ```text
   python scripts/acquire_research_materials.py SNAPSHOT_BUILD --case-file single-stock-demo/case.yaml --intake-file single-stock-demo/snapshot-inputs.yaml --output-dir single-stock-demo --created-at <ISO-8601-with-timezone>
   ```

6. For PDFs, retain page text, line coordinates, tables, section candidates, and footnote candidates. Render selected pages only into `tmp/pdfs/` for visual checking. Never treat renderings as formal sources.
7. Do not OCR image-only/scanned PDFs, transcribe audio, or read values from images/charts. Record affected required coverage as UNKNOWN in `gaps.yaml`.
8. Verify `snapshot-manifest.yaml`, `materials.jsonl`, parsed auxiliary files, coverage statistics, gaps, and hashes. A frozen output directory cannot be rebuilt in place; use a new directory for changed material.

## Run the Demo

Run:

```text
python scripts/acquire_research_materials.py DEMO_RUN --case-file single-stock-demo/case.yaml --snapshot-dir single-stock-demo
```

Treat any missing file, hash mismatch, `as_of` mismatch, late included material, or non-usable included material as a stop. Do not repair a Demo run with Web data.

## Keep the stage boundary

Output research materials and intake metadata only. Do not create context chunks, normalized facts, governed evidence, findings, challenges, or reports, and do not invoke another stage Skill.
