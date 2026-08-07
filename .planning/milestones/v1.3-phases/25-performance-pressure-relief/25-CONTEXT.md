---
phase: "25"
title: "Performance Pressure Relief"
status: ready_for_planning
gathered_at: 2026-05-15
requirements:
  - PERF-01
  - PERF-02
  - PERF-03
autonomous: true
---

# Phase 25: Performance Pressure Relief - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>

## Phase Boundary

Address bounded-output and bundle import hashing pressure where the current local runtime can improve safely. View replay pressure should receive a scoped contract note unless a small implementation is clearly safe.

</domain>

<decisions>

## Implementation Decisions

### Minimal Safe Performance Changes

Bound captured process and git output while preserving previews, artifacts, and full-stream hashes. Reuse verified bundle manifest integrity during import rather than re-reading the whole bundle directory. Do not introduce persisted view snapshots in this phase.

</decisions>

<code_context>

## Existing Code Insights

### Reusable Assets

- `ProcessCapability.run` currently stores stdout and stderr chunks in arrays and concatenates full output.
- `GitCapability.runGit` currently stores stdout and stderr chunks in arrays and concatenates full output.
- `importBundle` calls `verifyBundle` and then calls `hashBundleDirectory`, which recursively reads every bundle file again.
- `manifest.integrity.bundle.sha256` is already verified by `verifyBundle`.

### Established Patterns

- Capability tests use real child processes and real temporary git repositories.
- Bundle tests verify `.orun` export, verify, import, replay, and resume behavior.
- Runtime views are rebuilt from event logs as the current source-of-truth behavior.

### Integration Points

- Add bounded output capture in process and git capabilities.
- Add tests that large stdout/diff output is truncated in artifacts while hashes are still present.
- Change bundle import to use verified manifest bundle integrity for `sourceBundleSha256`.
- Record view snapshot work as a deferred contract in phase artifacts.

</code_context>

<specifics>

## Specific Ideas

- `PERF-01`: Add `maxOutputBytes` options to process and git capabilities with deterministic truncation metadata.
- `PERF-02`: Document the scoped view-pressure contract as deferred snapshot/tail-read work.
- `PERF-03`: Use `manifest.integrity.bundle.sha256` after `verifyBundle` rather than recomputing a whole-directory hash during import.

</specifics>

<deferred>

## Deferred Ideas

Persisted view snapshots and targeted read APIs remain future runtime storage work because they change view freshness and replay contracts.

</deferred>
