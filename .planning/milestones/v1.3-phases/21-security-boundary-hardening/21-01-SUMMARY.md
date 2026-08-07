---
phase: "21"
plan: "21-01"
status: complete
completed_at: 2026-05-15
requirements:
  - SEC-01
  - SEC-02
  - SEC-03
  - SEC-04
---

# Phase 21 Plan 21-01 Summary

## One-Liner

Implemented security boundary hardening for stdio worker environments, provider error redaction, bundle manifest path validation, and filesystem read-only mount posture enforcement.

## Completed Work

- Changed `packages/capabilities/src/transports/stdio-json-rpc.ts` so stdio JSON-RPC workers receive only `options.env` by default instead of inheriting the full parent environment.
- Added provider HTTP error redaction in `packages/provider-openai/src/openai-adapter.ts`, `packages/provider-anthropic/src/anthropic-adapter.ts`, and `packages/provider-local/src/local-openai-compatible-adapter.ts`.
- Added bundle manifest path validation in `packages/runtime/src/orun.ts` before manifest-declared paths are used for layout checks or integrity reads.
- Enforced filesystem read-only mount posture inside `packages/capability-filesystem/src/filesystem-capability.ts` for write, update, delete, move source, and move destination paths.
- Updated `tests/public-api/ontology-guards.test.ts` to guard current public/production surfaces instead of removed active planning files from a previous milestone.

## Tests Added

- `tests/capabilities/documents-stdio.test.ts` verifies parent-only environment variables are not inherited by stdio workers.
- `tests/providers/openai.test.ts`, `tests/providers/anthropic.test.ts`, and `tests/providers/local-openai-compatible.test.ts` verify sensitive provider error details are redacted.
- `tests/runtime/orun-bundle.test.ts` verifies unsafe manifest paths are rejected with `invalid_manifest_path`.
- `tests/capabilities/filesystem.test.ts` verifies read-only mounts reject mutating operations, including move into a read-only destination.

## Verification

- `pnpm test` passed: 55 test files, 227 tests passed, 2 skipped.
- `pnpm hygiene` passed: canonical ontology, secondary surface naming, and hygiene checks passed.

## Notes

- No provider, worker, CLI, or view was given runtime legality authority.
- Bundle path validation is scoped to manifest-declared file paths used during verification, matching the codebase-map security concern.
