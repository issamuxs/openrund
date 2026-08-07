# Phase 32: Governed Coordination and Recovery - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via `workflow.skip_discuss`)

<domain>
## Phase Boundary

Runtime hosts coordinate Waits, approval, Action uncertainty, Checks, durable Authority, and bounded Delegation through the existing `RuntimeEngine.submit(Command)` authority path. This phase extends legality and Event materialization; it does not add another mutation boundary or execute capabilities.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion because phase discussion is disabled. Preserve the established architecture, frozen Event contracts, deterministic Views, atomic Event storage, and the Phase 31 authority pipeline. Prefer explicit typed operations and pure replay-based legality over convenience APIs or orchestration abstractions.

</decisions>

<code_context>
## Existing Code Insights

- Phase 28 already defines all Wait, Action recovery, Delegation, Checkpoint, Annotation, and Authority payload variants plus inert Capability, Delegation, Authority, and Check values.
- Phase 29 already derives pending/terminal Wait queues, Action uncertainty and reconciliation, Delegation topology/joins, Check reports, Checkpoints, active Authority, and completion blockers.
- Phase 30 already provides single-Run and multi-Run expected-position atomic append through memory and SQLite stores.
- Phase 31 already provides the sole Command submit path, durable duplicate/idempotency recovery, complete replay, pure legality, and atomic `command.recorded` evidence.

</code_context>

<specifics>
## Specific Ideas

- A Wait is terminal exactly once. Resolution, cancellation, and expiry must validate the pending Wait kind and current clock where applicable.
- Approval follows two Commands: resolve the approval Wait, then resume the approved Action through complete current governance revalidation. Approval never repairs an illegal Operation.
- An unknown Action outcome creates reconciliation state; evidence-backed reconciliation is additive and resolves the matching reconciliation Wait without rewriting uncertainty.
- Delegation establishment uses atomic multi-Run append: parent Command/delegation facts and child Run bootstrap either commit together or not at all.
- Child terminal state is reflected to the parent only through an explicit parent Command; join satisfaction is a replay fact and never advances the parent automatically.
- Capability execution, workers, and built-ins remain Phase 33. Provider loops remain Phase 34. CLI interaction remains normal Phase 36 plans and tests.

</specifics>

<deferred>
## Deferred Ideas

- Capability transports, registration services, Action dispatch, and built-in implementations belong to Phase 33.
- Model-provider execution and the durable async run loop belong to Phase 34.
- Bundle portability belongs to Phase 35; assembly and CLI belong to Phase 36.
- OpenRund has no graphical UI, so no UI workflow or UI specification applies.

</deferred>
