# Command Path Audit

**Analysis date:** 2026-05-13
**Status:** Phase 14 complete, audit-only

Preferred authority shape:

```text
origin -> CommandEnvelope -> legality evaluation -> CommandDecision -> Event drafts -> append Events -> Views/Receipts
```

## Verdict

Model-originated paths mostly have visible `command.recorded` Events and decision traces. Non-model runtime APIs are inconsistent: approval resolution, approval resume, and action reconciliation have visible Commands; interactions, timers, checkpoint requests, unknown-outcome marking, delegated handoff, parent delegation cancellation, check recording, and raw append do not.

This is the largest semantic gap found so far. The MVP governance model is partially real, but not uniformly enforced across all mutation origins.

Post-Phase-18 rerun: the critical non-model runtime paths called out above were patched to emit visible runtime `command.recorded` Events before state-changing Events. This includes interaction resolution/cancel/expire, timer fire/cancel, runtime checkpoint requests, unknown-outcome marking, delegated handoff/cancellation, parent delegation cancellation, and runtime-owned Check recording. `RuntimeEngine.append` still exists as a low-level bootstrap/fixture/storage-adjacent escape hatch and remains out of the normal authority path.

## Path Matrix

| Entry point | Origin | Operation type | Creates Command? | Who validates legality | Who appends Events | Events produced | Can bypass Engine authority? | Test coverage | Risk |
|---|---|---|---:|---|---|---|---:|---|---|
| `bootstrap` | runtime/system | initial Run construction | No, documented bootstrap exception | `createBootstrapEvents` shape only | `RuntimeEngine.eventLog.append` at `packages/runtime/src/runtime-engine.ts:134` | `run.created`, `run.started`, initial Authority/contract Events | No if limited to position `0` bootstrap | bootstrap/runtime tests | Acceptable exception; document explicitly. |
| `RuntimeEngine.append` | caller/test/example/API | arbitrary Event append | No | Caller | `RuntimeEngine.append` at `packages/runtime/src/runtime-engine.ts:142` | Any `NewRuntimeEvent[]` | Yes | Many tests and demo use it | Critical. Public raw append is incompatible with Engine-only authority unless narrowed/internalized. |
| `recordModelOutput` invalid model call | model | rejected proposal | Yes | `validateModelCall`, rejection helpers | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:151` through `packages/runtime/src/runtime-engine.ts:168` | `command.recorded`, `model_call.failed` | No | model validator tests | Good. |
| `recordModelOutput` illegal action | model | rejected Action proposal | Yes | resource scope/policy/capability checks | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:171` through `packages/runtime/src/runtime-engine.ts:222` | `command.recorded`, `model_call.failed`; no target Action lifecycle Events | No | governed demo/tests | Good for model action rejection. |
| `recordModelOutput` approval-deferred action | model | deferred Action proposal | Yes | policy outcome | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:224` through `packages/runtime/src/runtime-engine.ts:267` | `command.recorded`, `model_call.completed`, `wait.created`, maybe `action.created` | No for model path | approval/demo tests | Good, pending Phase 15 proof of no execution before Wait resolution. |
| `recordModelOutput` allowed action | model | Action dispatch | Yes | dispatcher schema/policy/resource checks | `RuntimeEngine` + `ActionDispatcher` at `packages/runtime/src/runtime-engine.ts:250` through `packages/runtime/src/runtime-engine.ts:267` | `command.recorded`, `action.started/completed/failed/unknown`, Artifact Events | No if dispatcher is Engine-only | action/capability tests | Good. |
| `operation_batch` | model | Action batch | Yes | dispatcher batch validation | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:270` through `packages/runtime/src/runtime-engine.ts:343` | `command.recorded`, action Events or rejection | No for configured dispatcher path | action group tests | Good, but fallback rejects when not configured. |
| `create_delegation` | model | delegated Run spawn | Yes on parent model command | delegation control | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:346` through `packages/runtime/src/runtime-engine.ts:373` | parent `command.recorded`, `delegation.created`, delegated Run bootstrap Events | Partial | delegation tests | Medium: multi-append sequence and child bootstrap should be explicitly documented as Command-owned side effect. |
| model join Wait | model | open join Wait | Yes | delegation join control | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:376` through `packages/runtime/src/runtime-engine.ts:396` | `command.recorded`, `wait.created` | No | delegation join tests | Good. |
| model checkpoint | model | create Checkpoint | Yes | run lifecycle + checkpoint control | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:399` through `packages/runtime/src/runtime-engine.ts:434` | `command.recorded`, `checkpoint.created` | No | checkpoint tests | Good for model path. |
| model completion | model | complete Run | Yes | `assertRunCanComplete` | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:437` through `packages/runtime/src/runtime-engine.ts:490` | rejected `command.recorded` or accepted `command.recorded` + `run.completed` | No in guarded branch | check-gate/demo tests | Good branch. Fallback remains dangerous. |
| `modelOutputToEvents` fallback | model/internal fallback | add message/action/wait/checkpoint/complete/fail/cancel | Partially, via `modelCallEvents`; but direct terminal/lifecycle drafts happen after main guarded branches | Minimal/fallback-specific | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:1005` through `packages/runtime/src/runtime-engine.ts:1145` | `message.added`, `action.created`, `wait.created`, `run.completed`, `run.failed`, `run.cancelled`, rejection Events | Yes if reachable for terminal/lifecycle operations | limited | Critical for `complete_run` fallback until removed or proven unreachable. |
| `resolveApproval` | operator/CLI | resolve approval Wait | Yes | `assertRunCanResolveWait`, approval lookup/control | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:754` through `packages/runtime/src/runtime-engine.ts:800` | `command.recorded`, `wait.resolved` | No | wait approval/CLI tests | Good. |
| `continueApprovedAction` | system/runtime | resume deferred Action after approval | Yes | run lifecycle, approval presence, authority unchanged, approved input revision, dispatcher validation | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:803` through `packages/runtime/src/runtime-engine.ts:903` | `command.recorded`, `action.started/completed/failed/unknown` | No | approval revision/demo tests | Good; Phase 15 should verify full schema/Authority/resource revalidation. |
| `resolveInteraction` | operator/API | resolve interaction Wait | No | `assertRunCanResolveWait`, interaction control | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:906` through `packages/runtime/src/runtime-engine.ts:922` | `wait.resolved` | Yes | interaction tests | Critical. Needs Command-owned runtime operation. |
| `cancelInteraction` / `expireInteraction` | operator/system | cancel/expire interaction Wait | No | `assertRunCanResolveWait`, interaction control | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:925` through `packages/runtime/src/runtime-engine.ts:964` | `wait.cancelled` | Yes | interaction tests | Critical. Needs Command-owned runtime operation. |
| `fireTimer` | timer/system | fire timer Wait | No | `assertRunCanResolveWait`, timer control | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:967` through `packages/runtime/src/runtime-engine.ts:983` | `wait.resolved` / timer Events | Yes | timer tests | Critical. Timer origin must create a visible Command. |
| `cancelTimer` | operator/system | cancel timer Wait | No | `assertRunCanResolveWait`, timer control | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:986` through `packages/runtime/src/runtime-engine.ts:1002` | `wait.cancelled` | Yes | timer tests | Critical. |
| `requestCheckpoint` | operator/runtime | create runtime Checkpoint | No | checkpoint control | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:654` through `packages/runtime/src/runtime-engine.ts:670` | `checkpoint.created` | Yes | checkpoint tests | High. Runtime checkpoint should be Command-owned or documented as internal maintenance Event. |
| `recordActionOutcomeUnknown` | capability/system/operator | mark unknown outcome | No | reconciliation control validates action status | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:673` through `packages/runtime/src/runtime-engine.ts:691` | `action.unknown`, `wait.created` | Yes | action reconciliation/check-gate tests | Critical. Unknown outcome affects completion legality and must be Command-owned. |
| `reconcileActionOutcome` | operator/CLI | reconcile unknown outcome | Yes | reconciliation control | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:694` through `packages/runtime/src/runtime-engine.ts:747` | `command.recorded`, `action.reconciled`, `wait.resolved` | No | action reconciliation/CLI tests | Good. |
| `recordCheckResult` + `runtime.append` | runtime/operator/example | record Check | No by helper; raw append in callers | helper shapes report; caller appends | `recordCheckResult` at `packages/runtime/src/check-control.ts:35`; demo raw append at `examples/governed-coding-run/run.ts:333` | `check.recorded` | Yes | check-gate/demo tests | Critical. Checks influence completion, so Check recording needs Command path. |
| delegated Run handoff complete/fail/cancel | delegated Run/system | handoff to parent | No | delegation control | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:570` through `packages/runtime/src/runtime-engine.ts:631` | `delegation.completed/failed/cancelled`, Wait resolution | Yes | delegation tests | Critical. Handoff is lifecycle mutation. |
| `cancelParentDelegation` | parent/operator/system | cancel parent delegation | No | delegation control | `RuntimeEngine` at `packages/runtime/src/runtime-engine.ts:633` through `packages/runtime/src/runtime-engine.ts:652` | delegation cancellation Events | Yes | delegation cancellation tests | Critical. |
| CLI `waits resolve --kind approval` | operator CLI | approval resolution | Indirect yes | runtime `resolveApproval` | runtime method | `command.recorded`, `wait.resolved` | No | CLI tests | Good because runtime path is Command-owned. |
| CLI `actions reconcile` | operator CLI | action reconciliation | Indirect yes | runtime `reconcileActionOutcome` | runtime method | `command.recorded`, `action.reconciled` | No | CLI tests | Good because runtime path is Command-owned. |
| CLI read commands | operator CLI | inspect/waits/show/replay/timeline/checks/artifacts/receipt/explain/readiness/orun verify/replay | No mutation | N/A | none or read-only runtime | none | No | CLI tests | Good. |
| bundle export/verify/import/resume assessment | operator/API | portability operations | No Run Events by design | bundle verifier/import/resume assessment | file system only | bundle files, assessment object | No for Run history | orun tests | Acceptable if import never appends Run Events or auto-resumes. |
| provider adapters | provider transport | ModelCall parse/transport | No Commands | provider parsing only | none | none | No direct Event append | provider tests | Good; providers return `ModelCall` only. |
| workers/capabilities | worker transport | CapabilityResult | No Commands | dispatcher/materializer under Engine | none directly | CapabilityResult only | No if ActionDispatcher remains Engine-owned | capability tests | Good; no direct Event append found. |
| storage | storage backend | preserve Event order/content | No Commands | none | store append only | persisted Events | No legality by design, but raw caller matters | storage tests | Storage is not legality owner. |

## Critical Patch Candidates

1. Resolved in Phase 18: public docs no longer promote `RuntimeEngine.append` as a normal mutation path; it is documented as a low-level bootstrap/fixture/storage-adjacent escape hatch.
2. Resolved in Phase 18: interaction resolution/cancel/expire and timer fire/cancel now have runtime Commands.
3. Resolved in Phase 18 for the flagship path: runtime-owned Check recording exists and the demo uses it. Fixture-only raw Check append usage remains Phase 19 cleanup.
4. Resolved in Phase 18: unknown-outcome marking now has a runtime Command.
5. Resolved in Phase 18: runtime checkpoint requests now have a runtime Command.
6. Resolved in Phase 18: delegated handoff/cancellation paths now have runtime Commands.
7. Resolved in Phase 18: direct terminal fallback Events for `complete_run` and `fail_run` were removed.

## Requirement Status

- `CMD-01`: Complete. Required mutation paths are traced with origin, operation, Command status, validator, Event appender, Events, bypass risk, coverage, and risk.
- `CMD-02`: Complete for audit. Material non-model paths that bypass visible Commands are documented as critical Phase 18 patch candidates.
