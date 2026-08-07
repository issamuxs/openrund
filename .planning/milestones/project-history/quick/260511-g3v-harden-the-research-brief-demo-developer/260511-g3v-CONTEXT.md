# Quick Task 260511-g3v: Harden the research-brief demo developer surface - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Task Boundary

Harden the research-brief demo developer surface so it follows the documented runtime-home layout, uses human approval by default, makes reconciliation evidence explicit, streams runtime governance events during execution, produces deterministic audit output, and enriches the fixture source material enough that the final brief demonstrates real synthesis.

The current uncommitted edits to `examples/research-brief/`, `package.json`, `pnpm-lock.yaml`, and `tests/examples/research-brief.test.ts` are draft exploratory work. This quick task must either absorb, correct, or replace them through the plan rather than treating them as already validated.

</domain>

<decisions>
## Implementation Decisions

### Storage Layout
- Use the documented local runtime-home layout: `~/.openrund/runtime.sqlite` plus runtime-owned artifacts under `~/.openrund/artifacts/<sessionID>/`.
- Developer demo runs should use the shared runtime home by default with a unique demo session ID per run.
- Tests and deterministic CI fixture paths may continue to use temporary runtime homes.
- Do not introduce `tries/` or another undocumented subfolder.

### Reconciliation Evidence
- Use both paths: default developer runs require human/operator reconciliation evidence, while explicit automation uses deterministic reconciler evidence for CI and scripted demo runs.
- The runtime records, validates, and gates reconciliation; the runtime must not invent evidence.
- The CLI/demo output should explain what became unknown, why it was uncertain, who supplied evidence, and what event unblocked completion.

### Fixture Richness
- Enrich both the architecture notes and widget code enough that the generated brief synthesizes tradeoffs across docs and code.
- The final brief should feel like a meaningful developer work product, not a paraphrase of two tiny files.

</decisions>

<specifics>
## Specific Ideas

- Keep `pnpm demo:research-brief` as the developer entrypoint.
- Keep explicit automation via `pnpm demo:research-brief:auto`.
- Approval UX should be consistent: `Enter` means default; explicit text changes a default. Avoid accepting `y/yes` as a path answer.
- Stream major invariant/governance steps during execution: session start, child spawn/read/complete/join, approval request/resolution, unknown outcome, reconciliation, validation, completion, `.orun` export/verify.
- Deterministic audit output should be table/fact-oriented and generated from replayed events, not freeform explanatory prose.

</specifics>

<canonical_refs>
## Canonical References

- [docs/storage.md](../../../docs/storage.md) — runtime-home layout and workspace-root boundary.
- [docs/events.md](../../../docs/events.md) — approval, validation, uncertainty, and reconciliation event grammar.
- [docs/capabilities.md](../../../docs/capabilities.md) — capability reliability, approved relocation, and artifact discipline.
- [docs/orun.md](../../../docs/orun.md) — portable bundle layout and deterministic runtime exports.

</canonical_refs>
