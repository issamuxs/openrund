---
phase: "26"
status: complete
created_at: 2026-05-15
---

# v1.3 Coverage Closure

## High-Priority Concern Coverage

| Concern | Requirement | Evidence |
|---------|-------------|----------|
| Stdio JSON-RPC transport inherited parent environment | SEC-01 | `tests/capabilities/documents-stdio.test.ts` verifies parent-only env vars are not inherited by default. |
| Provider HTTP errors could expose sensitive details | SEC-02 | Provider adapter tests verify redaction for OpenAI, Anthropic, and local OpenAI-compatible errors. |
| Bundle manifest paths could escape bundle root | SEC-03 | `tests/runtime/orun-bundle.test.ts` covers unsafe manifest path rejection. |
| Filesystem read-only mount posture was not enforced | SEC-04 | `tests/capabilities/filesystem.test.ts` covers write, update, delete, move source, and move destination rejections. |
| Subscriber failure after commit made append retry semantics ambiguous | DUR-01 | `tests/runtime/event-streaming.test.ts` verifies bootstrap remains resolved and events are persisted when a subscriber throws. |
| Artifact blob/metadata partial failure left orphan risk | DUR-02 | `tests/storage/sqlite-artifact.test.ts` verifies newly written blob cleanup on metadata persistence failure. |
| Delegation parent/child partial failure was not explicit | DUR-03 | `tests/runtime/delegation-spawn.test.ts` verifies parent spawn durability, absent establishment, and absent child events when child bootstrap append fails. |
| Generated source artifacts could shadow TypeScript | HYG-01, HYG-02 | `tests/public-api/hygiene.test.ts` verifies hygiene rejects generated source artifacts; scan confirms none remain. |
| Python documents worker setup was outside root flow | HYG-03 | `pnpm test:python-documents` and docs describe dependency setup and pytest command. |
| Provider normalization duplicated across adapters | MAINT-01 | `tests/providers/provider-normalization.test.ts` covers shared single action, batch action, invalid JSON fallback, and dotted action names. |
| Filesystem duplicate implementations could drift | MAINT-02 | `tests/capabilities/filesystem-parity.test.ts` runs representative behavior against both implementations. |
| RuntimeEngine monolith seam extraction risk | MAINT-03 | Phase 24 explicitly deferred broad authority-boundary extraction; no Engine authority decisions moved. |
| Process/git output buffering was unbounded | PERF-01 | `tests/capabilities/process.test.ts` and `tests/capabilities/git.test.ts` cover bounded retained output with full-stream metadata. |
| View rebuild pressure needs scoped path | PERF-02 | Phase 25 records persisted snapshots as deferred contract work requiring freshness and replay-validation semantics. |
| Bundle import re-read all files after verification | PERF-03 | `tests/runtime/orun-replay-resume.test.ts` verifies import records reuse verified manifest bundle integrity. |

## Provider Drift Path

`pnpm test:providers:live` runs provider test files. Live cases are env-guarded and skipped unless `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENRUND_LOCAL_MODEL_URL` is set. This preserves secret-free normal tests while providing a documented local or CI drift check.

## Testing Pattern Check

New tests follow `.planning/codebase/TESTING.md` patterns:

- Storage and runtime tests use real temporary SQLite stores and event logs.
- Filesystem, process, and git tests use real temporary files, repositories, and child processes.
- Provider tests use deterministic `fetchImpl` mocks for normal runs and env-guarded live smoke cases.
- Runtime authority is not mocked in behavior tests that need real event sequences.
