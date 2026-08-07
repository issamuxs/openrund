# Phase 33: Capability Runtime, Actions, and Built-ins - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning
**Mode:** Auto-generated (discussion skipped via `workflow.skip_discuss`)

<domain>
## Phase Boundary

Extension authors and runtime hosts execute external work only after the Engine has durably accepted an Action. This phase adds validated Capability registration, in-process and strict stdio transports, Action dispatch, Artifact materialization, and the filesystem, Markdown, bounded process, and local git built-ins. It does not add provider loops, Bundles, assembly, a CLI, or any graphical interface.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
Discussion is disabled and the architecture is already fixed. Preserve `RuntimeEngine.submit(Command)` as the only lifecycle authority, use frozen typed values and structural protocols, keep worker responses non-authoritative, and prefer the standard library. Capability execution may store Artifact bytes, but only the Engine may append Action and Artifact facts.

</decisions>

<code_context>
## Existing Code Insights

- Phase 28 defines Capability, Action, result, transport, Artifact, error, and JSON contracts.
- Phase 29 replays Action receipts and Artifact references; Phase 30 owns immutable Artifact bytes and recovery.
- Phase 31 provides the sole Command evaluation path; Phase 32 durably creates governed Actions and handles unknown outcomes.
- Existing Event contracts already define `action.started`, terminal Action payloads, and `artifact.created`; Phase 33 must connect them to executable work without changing wire semantics.

</code_context>

<specifics>
## Specific Ideas

- Capability registration validates unique definitions, closed schemas, declared batching/cancellation/Artifact behavior, and one explicit transport binding.
- Dispatch records `action.started` before invoking a worker. Ambiguous post-dispatch transport loss becomes `action.unknown`; it is never reported as a safe failure.
- Inline worker Artifact material is stored first, then represented by compact immutable Artifact facts and references in the terminal Action Command.
- Filesystem and Markdown paths are portable relative paths resolved under explicit roots with lexical and real-path symlink defenses.
- Process execution uses explicit executable bindings, scrubbed allowlisted environment, disabled shell by default, bounded input/output/time, and cancellation cleanup.
- Git exposes only status, diff, head, apply, stage, and commit under a verified local repository root. Remote and credential operations do not exist.
- CLI interaction remains ordinary Phase 36 code and tests. No `UI-SPEC.md` or UI workflow applies.

</specifics>

<deferred>
## Deferred Ideas

- Provider adapters and the durable model/run loop belong to Phase 34.
- Bundle export/import belongs to Phase 35.
- Public assembly, console commands, and the installed demonstration belong to Phase 36.

</deferred>
