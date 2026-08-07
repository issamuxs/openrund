# Governance Reality Audit

**Analysis date:** 2026-05-13
**Status:** Phase 15 complete, audit-only

## Verdict

Governance is partially real.

It is real on the flagship model-originated path: illegal model-proposed filesystem writes are rejected before Action execution, approval defers execution through a Wait, approval resolution and resume are visible Commands, unknown outcomes block completion when required, reconciliation is evidence-linked, completion is runtime-gated, and bundle verification is implemented as fail-closed checks.

Post-Phase-18 rerun: governance is materially stronger. Critical non-model runtime paths now produce visible runtime Commands before state-changing Events, the flagship Check recording path is Command-owned, and terminal fallback Events were closed. The verdict improves from “partially real because non-model paths bypass Commands” to “substantially real, with Phase 19 proof gaps.” Full “governance is real” still requires broader tests for provider/worker non-authority, approval revalidation dimensions, delegated handoff/cancellation Command records, bundle corruption, and fixture-only raw append cleanup.

## Illegal Operation Rejection

| Required proof | Status | Evidence |
|---|---|---|
| Rejected Command exists | Proven | `RuntimeEngine.recordModelOutput` builds rejected decisions at `packages/runtime/src/runtime-engine.ts:183` through `packages/runtime/src/runtime-engine.ts:198`; demo test asserts `decision: "rejected"` at `tests/examples/governed-coding-run.test.ts:68` through `tests/examples/governed-coding-run.test.ts:71`. |
| Decision trace records resource-scope failure | Proven | Runtime uses criterion `resource_scope` at `packages/runtime/src/runtime-engine.ts:184` through `packages/runtime/src/runtime-engine.ts:187`; core command test covers `resource_scope` at `tests/core/commands.test.ts:36` through `tests/core/commands.test.ts:47`. |
| No target Action lifecycle Events emitted | Proven for demo path | Resource-scope rejection returns before `ActionDispatcher.dispatchAction` at `packages/runtime/src/runtime-engine.ts:198`; demo test expects no fake receipt semantics and rejected Command before approval at `tests/examples/governed-coding-run.test.ts:68`. |
| No file written | Proven by demo behavior | Demo attempts `../outside.txt` at `examples/governed-coding-run/run.ts:195`; rejection happens before dispatch at `examples/governed-coding-run/run.ts:201`. |
| CLI explanation derives from Command/Event data | Proven | CLI `commands explain` reads `command.recorded` from `runtime.readEvents` at `packages/cli/src/index.ts:720` through `packages/cli/src/index.ts:757`. |

Status: real for model-originated illegal filesystem writes.

## Deferred Approval

| Required proof | Status | Evidence |
|---|---|---|
| Deferred Command exists | Proven | Demo test asserts approval Command `decision: "deferred"` and `createdWaitIDs` at `tests/examples/governed-coding-run.test.ts:72` through `tests/examples/governed-coding-run.test.ts:75`. |
| Approval Wait exists | Proven | Dispatcher creates approval Wait; demo renders `waits show --kind approval` and test asserts `approvedInputValidation` at `tests/examples/governed-coding-run.test.ts:106` through `tests/examples/governed-coding-run.test.ts:108`. |
| No Action executes before Wait resolution | Strong but indirect | Deferred path creates Wait before resume; `continueApprovedAction` requires approved resolution at `packages/runtime/src/runtime-engine.ts:816` through `packages/runtime/src/runtime-engine.ts:825`. Needs explicit regression asserting no `action.started` before `wait.resolved`. |
| Approved input captured | Proven | CLI approval Wait command reads resolution payload approved input at `packages/cli/src/index.ts:480` through `packages/cli/src/index.ts:503`. |
| Approved input validation recorded | Proven | `approvalInputValidationProof` records schema/authority/resource/workspace pass fields at `packages/runtime/src/wait-control.ts:125` through `packages/runtime/src/wait-control.ts:132`; demo output includes `approvedInputValidation`. |
| Revised input revalidated against schema, Authority, resource scope | Partial | `continueApprovedAction` calls `assertApprovalAuthorityUnchanged` and `assertApprovedInputRevision` at `packages/runtime/src/runtime-engine.ts:827` through `packages/runtime/src/runtime-engine.ts:836`, then dispatcher validates action at `packages/runtime/src/runtime-engine.ts:872` through `packages/runtime/src/runtime-engine.ts:881`. Tests exist in `tests/runtime/wait-approval-revision.test.ts`, including outside-root rejection. Phase 19 should add explicit schema/authority/resource assertions. |

Status: mostly real; needs tighter targeted tests.

## Resume Path After Approval

| Required proof | Status | Evidence |
|---|---|---|
| Resolving approval enters Command evaluation | Proven | `resolveApproval` creates runtime `command.recorded` at `packages/runtime/src/runtime-engine.ts:774` through `packages/runtime/src/runtime-engine.ts:800`; demo test checks operation at `tests/examples/governed-coding-run.test.ts:76` through `tests/examples/governed-coding-run.test.ts:81`. |
| Wait resolution recorded | Proven | `resolveApproval` result Event types include `wait.resolved`; demo test checks this. |
| System/non-model Command records accepted resume path | Proven | `continueApprovedAction` creates `operation: "resume_approved_action"` command at `packages/runtime/src/runtime-engine.ts:882` through `packages/runtime/src/runtime-engine.ts:903`; demo test checks it at `tests/examples/governed-coding-run.test.ts:82` through `tests/examples/governed-coding-run.test.ts:87`. |
| Action Events follow from accepted Command | Proven in demo | Resume Command result types include `action.started` and `action.completed`. |
| CLI output shows path clearly | Proven | Demo rendered CLI includes approval resolution and resume Command sections. |

Status: real.

## Unknown Outcome

| Required proof | Status | Evidence |
|---|---|---|
| `action.unknown` Event exists | Proven | `tests/runtime/action-reconciliation.test.ts:21` through `tests/runtime/action-reconciliation.test.ts:31`; demo test expects `action.unknown` at `tests/examples/governed-coding-run.test.ts:60`. |
| Unknown blocks completion when required | Proven | `tests/runtime/check-gate.test.ts:73` through `tests/runtime/check-gate.test.ts:132` uses `requireKnownActionOutcomes()` and expects rejection with `unknown outcome actions`. |
| Reconciliation requires a Command | Proven for reconciliation | `reconcileActionOutcome` creates `command.recorded` at `packages/runtime/src/runtime-engine.ts:722` through `packages/runtime/src/runtime-engine.ts:746`. |
| Reconciliation records evidence/note/operator/linkage | Proven | Demo passes evidence/note/reconciledBy at `examples/governed-coding-run/run.ts:315` through `examples/governed-coding-run/run.ts:329`; receipt renders `unknownEventID`, evidence, note, outcome. |
| `action.reconciled` exists | Proven | `tests/runtime/action-reconciliation.test.ts:61` through `tests/runtime/action-reconciliation.test.ts:73`. |
| Completion legal only after reconciliation | Proven in demo, partial generally | Demo rejects premature completion before reconciliation/checks and accepts final completion after reconciliation at `tests/examples/governed-coding-run.test.ts:88` through `tests/examples/governed-coding-run.test.ts:96`. |

Gap: `recordActionOutcomeUnknown` itself is not Command-owned (`packages/runtime/src/runtime-engine.ts:673` through `packages/runtime/src/runtime-engine.ts:691`). Unknown outcome governance is functionally real but command-path incomplete.

Status: partially real until unknown marking gets a visible Command path.

## Completion Legality

| Required proof | Status | Evidence |
|---|---|---|
| Premature completion rejected before required Checks/Artifacts/known outcomes | Proven | `RuntimeEngine.recordModelOutput` calls `assertRunCanComplete` at `packages/runtime/src/runtime-engine.ts:437` through `packages/runtime/src/runtime-engine.ts:459`; tests cover missing Checks and unknown outcomes at `tests/runtime/check-gate.test.ts:19` through `tests/runtime/check-gate.test.ts:132`. |
| Final completion accepted only after requirements satisfied | Proven in demo | Demo final completion Command accepted with `run.completed` at `tests/examples/governed-coding-run.test.ts:92` through `tests/examples/governed-coding-run.test.ts:96`. |
| Semantic and diagnostic Checks separated | Proven in View/CLI output | Demo asserts `semanticChecks` and `diagnosticChecks`, and hides lower-level fields at `tests/examples/governed-coding-run.test.ts:117` through `tests/examples/governed-coding-run.test.ts:126`. |
| Diagnostic Checks do not make completion legal | Partial | `completionGateFactsFromViews` only checks contract-required Checks and unknown outcomes at `packages/runtime/src/check-control.ts:74` through `packages/runtime/src/check-control.ts:128`; tests should explicitly prove diagnostic-only Checks do not satisfy semantic contracts. |
| CLI readiness derived from runtime/View data | Proven | `runs readiness` renders `replay.runStatus.completionReadiness` at `packages/cli/src/index.ts:768` through `packages/cli/src/index.ts:784`. |

Gap: `modelOutputToEvents` fallback has direct `complete_run` -> `run.completed` at `packages/runtime/src/runtime-engine.ts:1113` through `packages/runtime/src/runtime-engine.ts:1127`. It must be removed or proven unreachable.

Status: real on guarded path, incomplete globally.

## Bundle Verification

| Required proof | Status | Evidence |
|---|---|---|
| Manifest check | Implemented | `readManifest` and `validateManifest` at `packages/runtime/src/orun.ts:997` through `packages/runtime/src/orun.ts:1070`. |
| Layout check | Implemented | `validateLayout` at `packages/runtime/src/orun.ts:1117` through `packages/runtime/src/orun.ts:1135`. |
| File integrity check | Implemented | file integrity collection and verification paths around `packages/runtime/src/orun.ts:867` through `packages/runtime/src/orun.ts:881`; demo verifies rendered `fileIntegrity`. |
| Event hash-chain check | Implemented | `collectEventIntegrity` at `packages/runtime/src/orun.ts:897` through `packages/runtime/src/orun.ts:912`; demo test asserts `eventHashChain` at `tests/examples/governed-coding-run.test.ts:130`. |
| Artifact manifest consistency | Implemented | `validateArtifactManifest` at `packages/runtime/src/orun.ts:1137` through `packages/runtime/src/orun.ts:1185`; demo test asserts `artifactManifest` at `tests/examples/governed-coding-run.test.ts:131`. |
| Malformed/unsupported metadata fails closed | Implemented | unsupported schema, compatibility, critical fields throw bundle errors at `packages/runtime/src/orun.ts:1051` through `packages/runtime/src/orun.ts:1115`; `tests/runtime/orun-bundle.test.ts` covers `unknown_critical_field`. |
| Import does not auto-resume | Implemented | CLI import calls `importBundle` and `assessImportedResume`, not run continuation, at `packages/cli/src/index.ts:821` through `packages/cli/src/index.ts:846`. |
| Resume assessment reports missing roots/capabilities/providers/policy/pending waits/artifacts/schema issues | Implemented | resume assessment issue generation at `packages/runtime/src/orun.ts:730` through `packages/runtime/src/orun.ts:822`. |

Status: real in implementation; Phase 19 should add corruption tests for every claimed verifier path.

## Overall Finding

The runtime is past demo theater on core model-path governance. The remaining gap is consistency: non-model paths still bypass visible Commands, and some proof is indirect or under-tested. Phase 18 must prioritize command-path fixes before naming-only cleanup.

## Requirement Status

- `GOV-01`: Complete for audit; illegal rejection is real on model path.
- `GOV-02`: Complete for audit; approval is mostly real, with test gaps.
- `GOV-03`: Complete for audit; unknown outcome enforcement is partial until unknown marking is Command-owned.
- `GOV-04`: Complete for audit; completion legality is real on guarded path, incomplete until fallback is removed/proven unreachable.
- `GOV-05`: Complete for audit; bundle verification appears real, with test-hardening needed.
