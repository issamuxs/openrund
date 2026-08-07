---
phase: "24"
title: "Duplication And Maintainability Reduction"
status: ready_for_planning
gathered_at: 2026-05-15
requirements:
  - MAINT-01
  - MAINT-02
  - MAINT-03
autonomous: true
---

# Phase 24: Duplication And Maintainability Reduction - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>

## Phase Boundary

Reduce drift-prone duplication in provider normalization and filesystem capability behavior while preserving public package exports and the Engine authority facade.

</domain>

<decisions>

## Implementation Decisions

### Narrow Refactor

Provider action normalization can move into a shared core helper because it only constructs `ModelCall` operations and does not grant runtime authority. Filesystem duplication is safer to cover with parity tests and targeted alignment in this phase than to invert package dependencies. `RuntimeEngine` monolith splitting is deferred because this milestone should not rewire the authority boundary.

</decisions>

<code_context>

## Existing Code Insights

### Reusable Assets

- OpenAI, Anthropic, and local OpenAI-compatible adapters each split qualified tool names and construct `create_action` / `operation_batch` model operations.
- OpenAI and local adapters each parse JSON argument strings with local `safeParseArguments`.
- Built-in filesystem handlers in `@openrund/capabilities` and package filesystem handlers in `@openrund/capability-filesystem` have overlapping implementations.
- The package filesystem implementation already has stricter symlink and read-only posture behavior.

### Established Patterns

- Provider tests inject `fetchImpl` and assert adapters do not import runtime Event append authority.
- Filesystem tests use real temporary directories and assert real filesystem effects.
- Public package exports are guarded by tests and should remain stable.

### Integration Points

- Add provider normalization helpers in `packages/core/src/` and export them through `@openrund/core`.
- Refactor provider adapters to use the shared helper for action construction and JSON argument parsing.
- Add explicit parity tests covering built-in and package filesystem behavior for representative read/write plus read-only rejection.

</code_context>

<specifics>

## Specific Ideas

- `MAINT-01`: Shared provider operation helper for qualified name splitting, JSON argument parsing, single action, and action batches.
- `MAINT-02`: Filesystem built-in and package implementations should be covered by parity tests, with built-in behavior aligned for read-only posture.
- `MAINT-03`: Document that `RuntimeEngine` seam extraction is intentionally deferred because preserving the authority facade matters more than forcing a broad refactor.

</specifics>

<deferred>

## Deferred Ideas

Do not create a new provider-common package or restructure `RuntimeEngine` command handlers in this phase. Those are larger dependency and authority-boundary moves.

</deferred>
