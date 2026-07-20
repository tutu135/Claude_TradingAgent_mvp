## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context repo: read `CONTEXT.md` and `docs/adr/` when present. See `docs/agents/domain.md`.

### Reference material boundaries

`现有资料/投研资料交付总说明.md`, `现有资料/投研数据交付Prompt.md`, and `现有资料/投研流程与经验交付Prompt.md` are client-facing collection aids written to request data, API documentation, historical reports, and research experience from a commissioned company.

- They are not product requirements.
- They are not client-confirmed business workflows.
- They are not runtime prompts for the Demo.
- Use them only as reference checklists for possible input materials; never let them override the frozen Spec.

### Acquisition and evidence boundaries

- Preserve snapshot v1 `smic-4c110e93f810aa8e` unchanged; any expanded material set must receive a new, self-contained snapshot identity.
- Acquisition maximizes target-related, traceable material published no later than `as_of`; it does not decide truth, credibility, source tier, claim type, conflicts, isolation, or evidence eligibility.
- A frozen material is `ACQUIRED_UNASSESSED`. Only downstream evidence governance may decide whether it can support analysis.
- High-relevance candidates missing acquisition metadata remain outside every snapshot until the missing provenance or time evidence is supplied.

### Demo simplicity

This repository is a bounded, disposable single-stock research demo.

- Implement only what is required to run the confirmed golden case and satisfy a named current acceptance criterion.
- Prefer short, explicit, case-specific files, rules, and scripts that are easy to delete, replace, or rewrite.
- Do not design for hypothetical multi-stock, multi-user, frontend/backend, or production orchestration needs.
- Do not treat the Skills workflow as the future product architecture.
- Do not add an abstraction, service, database, plugin system, DSL, queue, workflow runtime, or dependency solely for robustness, possible future reuse, or hypothetical inputs.
- If a bounded limitation does not prevent the golden case from running reproducibly, meeting hard correctness/traceability constraints, or passing current acceptance, record the limitation or gap instead of building general infrastructure.
- Achieve adjustability through direct code, explicit rules, and fixed data files, not extension frameworks or reserved architecture.
- Simplicity never permits fabricated data, broken provenance, non-reproducible formulas, inaccurate critical locators, or bypassing a frozen hard gate.
- See `docs/product/demo-scope.md` for scope and explicit non-goals.
