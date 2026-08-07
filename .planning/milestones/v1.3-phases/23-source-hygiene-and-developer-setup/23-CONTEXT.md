---
phase: "23"
title: "Source Hygiene And Developer Setup"
status: ready_for_planning
gathered_at: 2026-05-15
requirements:
  - HYG-01
  - HYG-02
  - HYG-03
autonomous: true
---

# Phase 23: Source Hygiene And Developer Setup - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>

## Phase Boundary

Remove generated-source drift from package source directories and make the normal developer verification flow explicit enough for a fresh workspace, including the transported Python documents worker.

</domain>

<decisions>

## Implementation Decisions

### the agent's Discretion

Implementation choices are at the agent's discretion. Keep this phase narrow: do not restructure package outputs or Python packaging beyond the minimum needed to make source hygiene and verification paths explicit.

</decisions>

<code_context>

## Existing Code Insights

### Reusable Assets

- `scripts/check-hygiene.mjs` already checks tracked and untracked project-controlled paths for `.DS_Store`, `.tsbuildinfo`, and `packages/*/dist`.
- `package.json` already exposes `pnpm hygiene`, `pnpm test`, `pnpm typecheck`, and `pnpm package:check`.
- Python documents worker tests live under `python/openrund_documents_worker/tests/` and are run with `python3 -m pytest` from that package directory.
- Root and docs verification guidance currently mentions TypeScript checks but not the Python worker setup or test command.

### Established Patterns

- Repository hygiene checks are script-based and run through `pnpm hygiene`.
- Public guard tests live under `tests/public-api/` and can execute repository scripts as subprocesses.
- Developer setup documentation belongs in `README.md`, `docs/README.md`, and `docs/contributing.md` when it affects normal verification.

### Integration Points

- Add a filesystem scan to `scripts/check-hygiene.mjs` for generated files under `packages/*/src`.
- Add a focused regression test under `tests/public-api/` that creates a temporary source-side generated artifact and verifies `scripts/check-hygiene.mjs` rejects it.
- Add a root npm script and documentation for the Python documents worker verification path.

</code_context>

<specifics>

## Specific Ideas

- `HYG-01`: Remove stale generated `.js`, `.d.ts`, and source map files from `packages/storage-sqlite/src` if present in the working tree.
- `HYG-02`: Make hygiene reject future `packages/*/src/**/*.js`, `*.js.map`, `*.d.ts`, and `*.d.ts.map` artifacts, including ignored files that `git ls-files --others --exclude-standard` would miss.
- `HYG-03`: Expose `test:python-documents` and document the Python dependency setup plus verification command.

</specifics>

<deferred>

## Deferred Ideas

Do not add full Python virtualenv management or CI provider-contract jobs in this phase. Those belong to release-readiness verification or operations work.

</deferred>
