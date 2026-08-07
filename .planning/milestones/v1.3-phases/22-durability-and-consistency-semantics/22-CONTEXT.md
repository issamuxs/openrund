# Phase 22: Durability And Consistency Semantics - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>

## Phase Boundary

Make persistence-adjacent failure modes explicit, tested, and recoverable where the current local runtime can reasonably support it. This phase covers event subscriber failure semantics after durable append, SQLite artifact blob/metadata partial failure behavior, and delegation parent/child append partial-failure behavior.

</domain>

<decisions>

## Implementation Decisions

### the agent's Discretion

All implementation choices are at the agent's discretion because this is an infrastructure/durability phase. Preserve append-only event ordering, expected-position conflict behavior, and Engine-owned authority semantics. Prefer deterministic, tested local-runtime semantics over broad distributed recovery machinery.

</decisions>

<code_context>

## Existing Code Insights

### Reusable Assets

- Event append and subscriber notification behavior lives in `packages/runtime/src/event-log.ts`.
- Local runtime event subscribers and progress reporting are wired in `packages/runtime/src/local-runtime.ts`.
- SQLite artifact metadata and blob writes live in `packages/storage-sqlite/src/sqlite-artifact-store.ts`.
- Delegation spawn and parent/child event sequencing live in `packages/runtime/src/runtime-engine.ts` and `packages/runtime/src/delegation-control.ts`.

### Established Patterns

- Storage tests use real temporary SQLite databases under `tests/storage/`.
- Runtime tests inspect real event sequences and expected-position behavior under `tests/runtime/`.
- Local-runtime failures should be explicit and caller-visible, but already-persisted facts must not be made ambiguous.

### Integration Points

- Add subscriber failure tests near `tests/runtime/event-streaming.test.ts`.
- Add artifact crash/partial-failure tests near `tests/storage/sqlite-artifact.test.ts`.
- Add delegation partial-failure tests near `tests/runtime/delegation-spawn.test.ts`.

</code_context>

<specifics>

## Specific Ideas

- `DUR-01`: Event subscriber failures cannot make an already-persisted append appear safely retryable without explicit semantics.
- `DUR-02`: SQLite artifact blob and metadata writes have tested cleanup or recovery behavior for partial failures.
- `DUR-03`: Delegation parent/child append sequences have tested partial-failure behavior or repair semantics.

</specifics>

<deferred>

## Deferred Ideas

Server-grade distributed transactions, distributed lease fencing, and multi-host repair loops remain future scaling work.

</deferred>
