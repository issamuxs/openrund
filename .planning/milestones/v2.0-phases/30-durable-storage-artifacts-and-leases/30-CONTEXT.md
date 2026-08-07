# Phase 30: Durable Storage, Artifacts, and Leases - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Runtime hosts have trustworthy local custody for ordered history, immutable content, execution coordination, and deterministic Run homes.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — discuss phase was skipped per user setting. Use the ROADMAP phase goal, success criteria, normative documentation, frozen compatibility evidence, and established Python codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research. Preserve the typed contract kernel and deterministic View boundaries from Phases 28 and 29.

</code_context>

<specifics>
## Specific Ideas

- Implement normal Python library surfaces and tests only; OpenRund has no graphical UI.
- Keep CLI interaction out of this phase and in the later CLI phase.
- Preserve the Engine as the sole authority boundary: storage and leases provide custody and coordination, never legality decisions.

</specifics>

<deferred>
## Deferred Ideas

- Engine command evaluation and lifecycle legality belong to Phase 31.
- Coordination policy, approvals, Checks, and recovery behavior belong to Phase 32.
- CLI rendering belongs to Phase 36.

</deferred>
