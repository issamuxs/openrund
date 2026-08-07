# Phase 31: Engine Authority and Core Run Semantics - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via `workflow.skip_discuss`)

<domain>
## Phase Boundary

Runtime hosts govern the core Run, Message, and ModelCall lifecycle through one Engine-owned Command evaluation path. Every mutation attempt becomes one durable `command.recorded` fact, and only accepted decisions may append target lifecycle Events.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion because phase discussion is disabled. Preserve the established architecture, normative runtime documentation, frozen compatibility contracts, typed Python kernel, deterministic Views, and durable storage ports. Prefer the minimal Engine surface that proves the full authority boundary without pulling later coordination, capability, provider-loop, Bundle, assembly, or CLI responsibilities forward.

</decisions>

<code_context>
## Existing Code Insights

- Phases 28–30 already provide immutable Commands/decisions/Events, exact codecs, injectable runtime ports, deterministic replay Views, atomic Event storage, Artifacts, Leases, and safe errors.
- The Engine must compose those boundaries rather than duplicate serialization, persistence, replay, or legality state.
- Existing runtime behavior and documentation define the architecture; this phase ports core semantics without redesigning them.

</code_context>

<specifics>
## Specific Ideas

- Keep the Engine as the only authority that can turn an attempted Operation into lifecycle Events.
- Persist `command.recorded` and accepted target Events atomically in one Event-store append.
- Rebuild authoritative pre-command facts from complete durable history before deciding legality.
- Model, runtime API, and recovery origins must share one evaluation path; provider outputs remain untrusted proposals.
- Implement normal Python library surfaces and automated tests only. OpenRund has no graphical UI, and CLI interaction belongs to Phase 36 plans/tests.

</specifics>

<deferred>
## Deferred Ideas

- Wait resolution, approval policy, Checks, recovery governance, Delegation, and durable Authority rules belong to Phase 32.
- Capability execution and built-ins belong to Phase 33.
- Provider adapters and the durable model run loop belong to Phase 34.
- Bundle portability belongs to Phase 35; assembly and CLI belong to Phase 36.

</deferred>
