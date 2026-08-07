# Test Plan

**Analysis date:** 2026-05-13  
**Executed:** 2026-05-14  
**Status:** complete

## Verification Standard

Tests assert Event sequences and payload fields, not only final status. For governance claims, the proof is in `command.recorded`, decision trace entries, Wait/Event linkage, Action lifecycle absence/presence, provider/worker non-authority, CLI rendered fields, and bundle verifier failures.

## Targeted Coverage

| Invariant | Test location | Proof added or confirmed |
|---|---|---|
| Provider cannot append Events. | `tests/providers/openai.test.ts`, `tests/providers/anthropic.test.ts`, `tests/providers/local-openai-compatible.test.ts` | Provider outputs remain `ModelCall` proposals and provider sources do not import `RuntimeEngine` or `RunEventStore`. |
| Worker cannot append Events. | `tests/runtime/action-dispatcher.test.ts`, `tests/capabilities/documents-stdio.test.ts` | Worker result shape contains no Command/Event authority; `ActionDispatcher` materializes `action.created`, `action.started`, and `action.completed`. |
| Approval revised input is revalidated. | `tests/runtime/wait-approval-revision.test.ts` | Outside-root revised input appends no `wait.resolved` or Action lifecycle Events; schema-invalid approved input executes no worker and records `action.failed` after the resume Command. |
| Deferred Command does not emit Action start/completion before resume. | `tests/runtime/wait-approval.test.ts` | Deferred approval path records no `action.started` or `action.completed` until `continueApprovedAction(...)`. |
| Resolve approval creates visible Command path. | `tests/runtime/wait-approval.test.ts` | `resolve_approval` and `resume_approved_action` both emit `command.recorded` with wait/action result linkage. |
| Unknown outcome blocks completion. | `tests/runtime/check-gate.test.ts` | `requireKnownActionOutcomes()` rejects completion with `unknown outcome actions` while unresolved unknowns remain. |
| Reconciliation requires evidence and links to unknown Event. | `tests/runtime/action-reconciliation.test.ts`, `tests/views/action-reconciliation.test.ts` | `reconcile_action` Command records `action.reconciled`; payload/View expose `unknownEventID`, evidence, note, and operator metadata where supplied. |
| Diagnostic Checks do not satisfy semantic contracts. | `tests/runtime/check-gate.test.ts` | Diagnostic-only Check populates diagnostic readiness but completion remains rejected until required semantic `source_coverage` Check passes. |
| Runtime-owned Check recording exists. | `tests/runtime/check-gate.test.ts` | `RuntimeEngine.recordCheckResult(...)` emits `command.recorded` with `operation: "record_check_result"` before `check.recorded`. |
| Bundle verification fails closed on corrupted Event hash chain. | `tests/runtime/orun-bundle.test.ts` | Tampered `events.jsonl` with recomputed file integrity still fails `verifyBundle(...)` on Event hash-chain mismatch. |
| CLI renders no invented fields. | `tests/runtime/cli-phase5.test.ts`, `tests/examples/governed-coding-run.test.ts` | Rendered output excludes `receiptID`, `receiptIdentity`, `gateExplanation`, and `outcomeExplanation`; receipts/readiness render runtime primitives. |
| Non-model mutation paths record Commands. | `tests/runtime/timer-waits.test.ts`, `tests/runtime/interaction-waits.test.ts`, `tests/runtime/checkpoint.test.ts`, `tests/runtime/delegation-cancellation.test.ts`, `tests/runtime/action-reconciliation.test.ts` | Timer cancel/fire, interaction resolve/expire, runtime checkpoint, delegated handoff/cancellation, parent delegation cancellation, unknown marking, and reconciliation emit visible Commands. |

## Verification Results

| Command | Status | Result |
|---|---|---|
| `pnpm exec vitest run tests/runtime/wait-approval.test.ts tests/runtime/wait-approval-revision.test.ts tests/runtime/action-reconciliation.test.ts tests/views/action-reconciliation.test.ts tests/runtime/check-gate.test.ts tests/runtime/timer-waits.test.ts tests/runtime/interaction-waits.test.ts tests/runtime/checkpoint.test.ts tests/runtime/delegation-cancellation.test.ts` | passed | 9 files, 53 tests passed. |
| `pnpm exec vitest run tests/providers/openai.test.ts tests/providers/anthropic.test.ts tests/providers/local-openai-compatible.test.ts tests/runtime/action-dispatcher.test.ts tests/capabilities/documents-stdio.test.ts tests/runtime/cli-phase5.test.ts tests/examples/governed-coding-run.test.ts tests/public-api/ontology-guards.test.ts` | passed | 8 files, 36 tests passed, 2 skipped provider smoke checks. |
| `pnpm exec vitest run tests/runtime/orun-bundle.test.ts` | passed | 1 file, 7 tests passed. |
| `pnpm test -- tests/examples/governed-coding-run.test.ts tests/runtime/cli-phase5.test.ts tests/runtime/orun-bundle.test.ts tests/views/action-reconciliation.test.ts tests/runtime/action-reconciliation.test.ts` | passed | Build passed; Vitest ran the forwarded target set plus configured suite behavior and reported 55 files, 221 tests passed, 2 skipped. |
| `node scripts/check-ontology-canonical.mjs` | passed | OpenRund canonical ontology check passed. |
| `pnpm test` | passed | Build passed; 55 files, 221 tests passed, 2 skipped. |
| `pnpm demo:governed-coding-run` | passed | Build passed; demo completed and rendered runtime/CLI surfaces with rejected illegal write, approval/resume Commands, reconciliation, readiness, and Bundle verification. |
| `pnpm hygiene` | passed | Canonical ontology, secondary-surface naming, and hygiene checks passed. |
| `pnpm package:check` | passed | Package content check passed. |

## Residual Risks

- `RuntimeEngine.append(...)` remains available as a low-level bootstrap/fixture/storage-adjacent escape hatch. Phase 19 tests preserve that distinction rather than removing the API.
- Live provider smoke tests remain skipped unless credentials or local model endpoints are present; provider non-authority is covered structurally and through normalization tests.
- Git reported background GC warnings about unreachable loose objects during commits. This does not affect runtime governance tests but should be cleaned outside the semantic milestone if repository maintenance matters.
