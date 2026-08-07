# Secondary Surface Audit

**Analysis date:** 2026-05-13
**Status:** Phase 13 complete, audit-only

## Verdict

Secondary surfaces are mostly real derived surfaces, not accidental authority. Views rebuild from Events, CLI commands render runtime/replay data, and the governed-coding-run demo now prints CLI/runtime surfaces rather than independent demo-only explanations.

Post-Phase-18 rerun: the previous secondary-surface naming debts (`retainedFacts`, `EffectRecord`) are resolved in current code as `retainedContext` and `EffectEntry`. The governed demo now records Checks through `RuntimeEngine.recordCheckResult(...)` instead of raw append. Secondary-surface derivation remains intact, and the main residual risk moved from surface naming to Phase 19 proof coverage.

## Surface Matrix

| Surface | Source object/View | Canonical concepts | Derived? | Invented fields? | Decides legality? | Findings |
|---|---|---|---:|---:|---:|---|
| `ActionReceipt` View | `packages/views/src/action-receipts.ts:10`, reducer at `packages/views/src/action-receipts.ts:63` | Action, Event, Artifact, Capability | Yes | No fake receipt ID | No | Uses `receiptType: "ActionReceipt"`, `derived: true`, `subject.actionID`, and lifecycle fields from `action.*` Events. Naming debt remains through `EffectRecord` from core. |
| Action receipt CLI | `packages/cli/src/index.ts:654` through `packages/cli/src/index.ts:695` | Action, View, Artifact | Yes | No | No | Reads `replay.actionReceipts[actionID]` and renders receipt fields. Does not decide status. |
| Command explanation CLI | `packages/cli/src/index.ts:707` through `packages/cli/src/index.ts:757` | Command, Event, Wait | Yes | No | No | Reads `command.recorded` Events and renders `decision`, `decisionTrace`, result Event IDs/types, created/resolved/causal Wait IDs. |
| Approval Wait CLI | `packages/cli/src/index.ts:461` through `packages/cli/src/index.ts:505`; resolve path at `packages/cli/src/index.ts:508` through `packages/cli/src/index.ts:553` | Wait, Command, Event, Action | Yes for display; mutation delegates to runtime | No | No | `waits show` reads replayed pending approval Waits. `waits resolve` calls runtime `resolveApproval`; legality belongs to runtime. |
| Run readiness CLI | `packages/cli/src/index.ts:768` through `packages/cli/src/index.ts:784` | Run, Check, Action, Wait, Artifact, View | Yes | No | No | Renders `replay.runStatus.completionReadiness`; completion gate itself is runtime code, not CLI. |
| RunStatusView readiness | `packages/views/src/run-status-view.ts`; completion helpers in `packages/runtime/src/check-control.ts` | Run, Check, Action, Artifact, Wait | Yes | No | View does not decide; runtime consumes it | `completionReadiness` is a derived diagnostic/explanation surface. Phase 15 must prove runtime completion legality uses it correctly. |
| Timeline View/CLI | `packages/views/src/timeline.ts`; `packages/cli/src/index.ts:444` through `packages/cli/src/index.ts:454` | Event, Run, Action, Wait, Delegation, Check | Yes | No | No | Timeline entries are Event-derived. Labels are display summaries, not lifecycle concepts. |
| WaitQueueView | `packages/views/src/wait-queues.ts`; CLI `waits` at `packages/cli/src/index.ts:400` through `packages/cli/src/index.ts:424` | Wait, Run | Yes | No | No | `pendingApprovalWaits`, `pendingInteractions`, `pendingTimers`, and `pendingWaits` are acceptable derived display fields. |
| ArtifactIndexView and artifacts CLI | `packages/views/src/artifact-index-view.ts`; `packages/cli/src/index.ts:557` through `packages/cli/src/index.ts:579` | Artifact, Event | Yes | No | No | Artifact index derives from `artifact.*` Events. CLI lists/shows replayed index entries. |
| Check report CLI | `packages/cli/src/index.ts:583` through `packages/cli/src/index.ts:599`; helpers in `packages/runtime/src/check-control.ts` | Check, Artifact | Yes | No | No | Exports latest Check content as JSON/Markdown. Phase 15 must keep diagnostic Checks separate from semantic completion contracts. |
| CheckpointView | `packages/views/src/checkpoint-view.ts:9` through `packages/views/src/checkpoint-view.ts:63` | Checkpoint, Event | Yes | `retainedFacts` naming debt | No | Rebuilds from `checkpoint.created`; `retainedFacts` is a Phase 12 naming violation and should become `retainedContext`. |
| DelegationView | `packages/views/src/delegation-view.ts:62` through `packages/views/src/delegation-view.ts:68` | Delegation, Run, Wait | Yes | No | No | Derived from delegation Events and join/handoff Events. Handoff command ownership is Phase 14. |
| Bundle manifest | `packages/runtime/src/orun.ts`; runtime wrappers at `packages/runtime/src/runtime-engine.ts:515` through `packages/runtime/src/runtime-engine.ts:568` | Bundle, Event, Artifact, View, Authority | Yes | No | No | Manifest transports history and metadata; verification, not resume, is the authority-adjacent operation. |
| Bundle verification result | `packages/cli/src/index.ts:809` through `packages/cli/src/index.ts:817` | Bundle, Event, Artifact | Yes | No | No | CLI renders runtime verification checks (`manifest`, `layout`, `fileIntegrity`, `eventHashChain`, `bundleIntegrity`, `artifactManifest`, `schemaVersion`). |
| ResumeAssessment | `packages/runtime/src/orun.ts`; CLI at `packages/cli/src/index.ts:848` through `packages/cli/src/index.ts:865` | Bundle, Capability, Provider, Wait, Artifact, Authority | Yes | No | No | Reports portability/resume blockers; import does not auto-resume. |
| Governed coding demo printout | `examples/governed-coding-run/run.ts:365` through `examples/governed-coding-run/run.ts:429` and final print at `examples/governed-coding-run/run.ts:765` through `examples/governed-coding-run/run.ts:774` | Run, Command, Action, Wait, Check, Bundle | Yes | No banned fake fields found | No | Demo renders CLI results via `renderCliResult(...)`; it does not create separate fake receipt identities or explanation objects. |

## Explicit Fake Field Check

`rg` found no production occurrences of:

- `receiptID`
- `receiptIdentity`
- `gateExplanation`
- `outcomeExplanation`
- demo-only authoritative summary fields

The only matches are negative assertions in `tests/examples/governed-coding-run.test.ts:103` through `tests/examples/governed-coding-run.test.ts:126`.

## Demo Verification

Command run:

```text
pnpm demo:governed-coding-run
```

Result: passed on 2026-05-13.

The rendered output used:

- `Command Explanation` with canonical `commandID`, origin, operation, decision, decision trace, Event IDs/types, and Wait IDs.
- `Action Receipt` with `receiptType`, `derived`, `subject`, `actionID`, status, mutation, effects, Artifact IDs, unknown outcome, and reconciliation.
- `Run Completion Readiness` with semantic Checks, diagnostic Checks, unknown outcomes, output Artifact requirements, pending Waits, `ready`, and issues.
- `Bundle Verification` with runtime verification checks.

No banned fake fields were present in the demo output.

## Findings For Later Phases

| Severity | Finding | Why it matters | Follow-up |
|---|---|---|---|
| Resolved | `CheckpointView.retainedFacts` repeated the Phase 12 `Facts` violation. | A View field can imply authoritative facts even if derived. | Renamed to `retainedContext` in Phase 18. |
| Resolved | `EffectRecord` leaked through Action receipt effect rendering. | It was exported core vocabulary using banned `Record`; the rendered effect objects were valid but the type name was not. | Renamed to `EffectEntry` in Phase 18. |
| Reduced | Surface derivation depends on Events being authoritative. | Derived surfaces faithfully display Events; Phase 18 made critical non-model runtime mutations Command-owned. | Phase 19 should broaden tests for every non-model path. |
| Medium | CLI `waits resolve` and `actions reconcile` are mutation commands. | CLI does not decide legality, but it invokes runtime mutations and must remain a thin caller. | Continue guarding CLI as a runtime caller in Phase 19 tests. |

## Requirement Status

- `SURF-01`: Complete. Required secondary surfaces are mapped to Events, Artifacts, Views, runtime methods, or CLI renderers.
- `SURF-02`: Complete for audit. No banned fake fields were found in production/demo output; remaining issues are naming debt and command-path proof.
