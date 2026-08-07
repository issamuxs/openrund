# Phase 21: Security Boundary Hardening - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>

## Phase Boundary

Close the high-priority security gaps identified in the codebase map without weakening the Engine authority model or capability boundary. This phase covers stdio worker environment isolation, provider error redaction, bundle manifest path validation before filesystem access, and filesystem read-only mount posture enforcement.

</domain>

<decisions>

## Implementation Decisions

### the agent's Discretion

All implementation choices are at the agent's discretion because this is an infrastructure/security hardening phase. Preserve the mapped architecture: `RuntimeEngine` remains the authority boundary; provider adapters, capability workers, views, CLI, and storage must not decide runtime legality. Prefer narrow changes with focused tests over broad rewrites.

</decisions>

<code_context>

## Existing Code Insights

### Reusable Assets

- Stdio JSON-RPC transport lives in `packages/capabilities/src/transports/stdio-json-rpc.ts`.
- Documents worker client uses the stdio transport from `packages/capability-documents/src/documents-client.ts`.
- Provider adapters live in `packages/provider-openai/src/openai-adapter.ts`, `packages/provider-anthropic/src/anthropic-adapter.ts`, and `packages/provider-local/src/local-openai-compatible-adapter.ts`.
- Bundle verification and import/export logic lives in `packages/runtime/src/orun.ts`.
- Filesystem path sandbox and handlers live in `packages/capability-filesystem/src/path-sandbox.ts` and `packages/capability-filesystem/src/filesystem-capability.ts`.

### Established Patterns

- TypeScript source uses NodeNext ESM imports with explicit `.js` suffixes for relative imports.
- Boundary failures should use structured `capabilityError()` where they originate in capability code, and focused runtime errors where bundle verification rejects malformed inputs.
- Tests should use real temporary files/directories for filesystem and bundle behavior, and injected `fetchImpl` mocks for provider behavior.
- Runtime and capability changes must keep event payloads compact and preserve Engine-owned authority semantics.

### Integration Points

- Add stdio environment tests under `tests/capabilities/` near documents stdio coverage.
- Add provider redaction tests under `tests/providers/`.
- Add bundle traversal tests under `tests/runtime/orun-bundle.test.ts` or a focused runtime bundle test.
- Add read-only mount mutation tests under `tests/capabilities/filesystem.test.ts`.

</code_context>

<specifics>

## Specific Ideas

No specific user-facing behavior. Implement the four mapped security requirements exactly:

- `SEC-01`: Stdio JSON-RPC workers receive a minimal explicit environment by default.
- `SEC-02`: Provider HTTP error reporting redacts authorization-looking values and sensitive response details.
- `SEC-03`: Bundle verification rejects absolute, parent-traversal, and platform-escape manifest paths before filesystem access.
- `SEC-04`: Filesystem read-only mount posture blocks write, update, delete, and move inside the capability itself.

</specifics>

<deferred>

## Deferred Ideas

Broader runtime refactors, performance work, and durability semantics belong to later v1.3 phases.

</deferred>
