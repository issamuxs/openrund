# Codebase Map

**Analysis date:** 2026-05-13  
**Status:** Phase 11 discovery map refreshed from source

## Audit Status

| Requirement | Status | Notes |
|---|---|---|
| `MAP-01` | Complete | Authority owners, append sites, and suspicious paths are mapped with file/function references. |
| `MAP-02` | Complete | Workers/providers/storage/views/CLI/examples/tests boundaries are inventoried and separated from production authority. |
| `MAP-03` | Complete | Competitor comparison notes added using the official-doc summaries already captured in `11-RESEARCH.md`. |

## Runtime Authority Owners

| Area | Key files and symbols | Command owner | Event writer | Legality owner | View mutation | Audit note |
|---|---|---|---|---|---|---|
| Core command and legality types | `packages/core/src/model.ts:76-173` `CommandDecision`, `CommandDecisionTraceEntry`, `CommandEnvelope`, `CommandDecisionRecord`; `packages/core/src/events.ts:144-170` `CommandRecordedPayload` | Type-only | No | Type-only | No | `CommandDecisionRecord` is ontology-facing and still uses banned noun `Record`. |
| Core run and wait contracts | `packages/core/src/run.ts:51-209` `Wait`, `AuthorityGrant`, `DelegationContract`, `RunContract` | Type-only | No | Type-only | No | Canonical contract vocabulary lives here; later phases should check exported noun drift. |
| Engine entry boundary | `packages/runtime/src/runtime-engine.ts:122-144` `bootstrap`, `append`; `146-495` `recordModelOutput`; `754-903` `resolveApproval`, `continueApprovedAction` | Yes | Yes via `RuntimeEventLog.append` | Yes, mostly inline | No | `append` is public and bypasses visible command creation. This is the highest-risk escape hatch. |
| Command decision helpers | `packages/runtime/src/legality-evaluator.ts:14-128` `createModelCommandEnvelope`, `acceptedDecision`, `rejectedDecision`, `deferredDecision` | Helper | No | Helper | No | Thin helper layer; real legality is still concentrated in `RuntimeEngine.recordModelOutput`. |
| Event append wrapper | `packages/runtime/src/event-log.ts:6-27` `RuntimeEventLog.append`, `readAll` | No | Yes | No | No | Central write wrapper is narrow, but `RuntimeEngine.append` exposes it publicly. |
| Action dispatch | `packages/runtime/src/action-dispatcher.ts:53-137` `dispatchAction`; `139-260` `executeAllowedAction`; `263-306` `validateOperationBatch` | No | Returns drafts only | Policy/schema only | No | Good worker boundary: workers return `CapabilityResult`; Engine appends resulting events. |
| Completion and checks | `packages/runtime/src/check-control.ts:35-72` `recordCheckResult`; `74-128` `completionGateFactsFromViews`, `assertRunCanComplete` | `recordCheckResult` helper only | Returns check drafts only | Yes for completion | No | Completion legality is explicit, but tests/examples currently use `runtime.append(...recordCheckResult(...))`. |
| Wait control | `packages/runtime/src/wait-control.ts:29-123` `assertRunCanResolveWait`, `createApprovalResolutionEvents`; `160-258` `assertApprovalAuthorityUnchanged`, `assertApprovedInputRevision` | No | Returns drafts only | Approval revalidation | No | Good legality revalidation, but only `resolveApproval` wraps it in `command.recorded`. |
| Approval wait creation | `packages/runtime/src/wait-approval-control.ts:26-76` `createApprovalWaitEvents` | No | Returns drafts only | Snapshot only | No | Approval requests remain Engine-authored and carry policy snapshot and revision policy. |
| Interaction waits | `packages/runtime/src/interaction-control.ts:35-79` `createInteractionWaitEvents`; `81-145` resolution/cancellation | No | Returns drafts only | Conflict checks only | No | `RuntimeEngine.resolveInteraction/cancelInteraction/expireInteraction` append these drafts without visible commands. |
| Timer waits | `packages/runtime/src/timer-control.ts:33-73` `createTimerWaitEvents`; `75-147` fire/cancel | No | Returns drafts only | Conflict/time checks only | No | `RuntimeEngine.fireTimer/cancelTimer` append wait lifecycle directly. |
| Delegation | `packages/runtime/src/delegation-control.ts:71-160` `createDelegationSpawnEvents`; `193-265` `createDelegationJoinEvents`; `268-345` handoff helpers | Model path for spawn/join only | Returns drafts and bootstrap events | Contract validation for spawn/join | No | Parent handoff methods append `delegation.*` and join resolution without visible commands. |
| Checkpoints | `packages/runtime/src/checkpoint-control.ts:72-156` `createCheckpointEvents` | Model path for model checkpoint only | Returns drafts only | Range/protected-type validation | No | `RuntimeEngine.requestCheckpoint` appends checkpoint or annotation directly, without visible command recording. |
| Reconciliation | `packages/runtime/src/action-reconciliation-control.ts:40-111` `createActionOutcomeUnknownEvents`; `113-209` `createActionOutcomeReconciledEvents` | Unknown path: no; reconcile path: yes | Returns drafts only | Conflict checks only | No | `recordActionOutcomeUnknown` is a raw system append; `reconcileActionOutcome` correctly records an operator command first. |
| Views | `packages/views/src/index.ts:25-41` `ViewBundle`, `rebuildViews`; `run-status-view.ts:62-262`, `wait-queues.ts:94-...`, `action-receipts.ts:63-163`, `delegation-view.ts:68-...` | No | No | No | Yes, derived only | Derived surfaces are deterministic and rebuildable, matching docs. They are not authority owners. |

## Boundary Inventory

| Area | Key files and symbols | Writes Events? | Creates Commands? | Decides legality? | Mutates Views? | Risk note |
|---|---|---:|---:|---:|---:|---|
| Capability definitions and registry | `packages/capabilities/src/definition.ts`, `registry.ts:6-36`, `dispatcher.ts:7-25` | No | No | Registration and schema only | No | Correctly descriptive only. No runtime history authority. |
| In-process and stdio transports | `packages/capabilities/src/transports/in-process.ts:9`; `stdio-json-rpc.ts:31-43` `callStdioJsonRpc` | No | No | Transport errors only | No | Good boundary: they execute handlers, not runtime appends. |
| Filesystem capability | `packages/capability-filesystem/src/definition.ts:14`; `filesystem-capability.ts:18-65` `createFilesystemHandlers`, `FilesystemCapability`; `path-sandbox.ts:18-85` `resolveUnderMount`, `rejectSymlinkForMutation` | No | No | Filesystem path safety only | No | Path sandbox is enforcement for handler IO, not Run legality. |
| Documents capability TS client | `packages/capability-documents/src/definition.ts:12`; `documents-client.ts:8-19` `createDocumentsHandlers`, `DocumentsClient` | No | No | No | No | Client only packages JSON-RPC calls. |
| Documents worker Python | `python/openrund_documents_worker/openrund_documents_worker/server.py:22-35` `create_server`; `jsonrpc.py:19` `JsonRpcServer`; `markdown_ops.py:13` `DocumentConflict` | No | No | Document operation conflicts only | No | Strong separation: worker exposes document methods only and cannot append Events. |
| Process capability | `packages/capability-process/src/definition.ts:9`; `process-capability.ts:28-41` `createProcessHandlers`, `ProcessCapability` | No | No | Command execution validation only | No | High real-world side-effect surface; must remain behind Engine policy and approval. |
| Git capability | `packages/capability-git/src/definition.ts:14`; `git-capability.ts:40-53` `createGitHandlers`, `GitCapability`; `git-receipts.ts:8` `gitEffect` | No | No | Repo/path validation only | No | `gitEffect` is receipt/evidence shaping, not authority. |
| Provider adapters | `packages/provider-openai/src/openai-adapter.ts:23-47`, `89-151`; `provider-anthropic/...:21-53`, `78-142`; `provider-local/...:39-82`, `109-154` | No | No | No | No | Adapters normalize provider payloads into `ModelCall` operations only. They do not record commands or events. |
| Storage binding | `packages/storage/src/index.ts:10-17` `sqlite` | No | No | No | No | Convenience binding only. |
| SQLite event store | `packages/storage-sqlite/src/sqlite-store.ts:13-34` `ExpectedPositionConflictError`, `SqliteRunEventStore` | Persists caller-provided events | No | No | No | Correct durability boundary; must never decide acceptance. |
| SQLite artifact and lease stores | `packages/storage-sqlite/src/sqlite-artifact-store.ts:20` `SqliteArtifactStore`; `sqlite-lease-store.ts:11` `SqliteExecutionLeaseStore` | No event semantics | No | No | No | Coordination and artifact durability only. |
| CLI | `packages/cli/src/index.ts:37-74` `executeCli`; `76-254` `renderCliResult`; `699-757` `commands explain`; `787-889` `.orun` commands | Indirect via runtime methods only | No | No | No | Good secondary-surface behavior. CLI reads events/views and calls runtime APIs; it does not synthesize legality. |
| Example demo | `examples/governed-coding-run/run.ts:101-389` `runGovernedCodingDemo` | Yes, indirectly and once directly | Indirect | Should not | No | Audit-critical: line `333` uses `runtime.append(...recordCheckResult(...))`, teaching a raw append pattern in public example code. |
| Tests: runtime/view/public API/example | `tests/runtime/check-gate.test.ts:53,80,243,318`; `wait-approval.test.ts:165,220`; `interaction-waits.test.ts:168`; `timer-waits.test.ts:130`; `orun-bundle.test.ts:231`; `tests/examples/governed-coding-run.test.ts` | Yes, fixture setup | Sometimes via test harness only | Test-only | Test-only | Raw append use exists in tests, but most occurrences are explicit fixture setup rather than public runtime guidance. Keep separate from production risks. |

## Suspicious Authority Paths

| Severity | File and function | Why it is suspicious | Evidence already present |
|---|---|---|---|
| Critical | `packages/runtime/src/runtime-engine.ts:142` `RuntimeEngine.append` | Public raw append surface can write arbitrary `NewRuntimeEvent[]` with no visible `command.recorded` or legality decision. | Used directly by example demo at `examples/governed-coding-run/run.ts:333` and many tests for setup. |
| Critical | `packages/runtime/src/runtime-engine.ts:906` `resolveInteraction`; `925` `cancelInteraction`; `944` `expireInteraction` | Operator/system wait mutation appends `wait.resolved` / `wait.cancelled` directly. Docs require non-model mutations to enter a Command path. | Exercised by `tests/runtime/interaction-waits.test.ts:73-78`, `104-106`. |
| Critical | `packages/runtime/src/runtime-engine.ts:967` `fireTimer`; `986` `cancelTimer` | Timer/system mutations append directly without adjacent command event. | Exercised by `tests/runtime/timer-waits.test.ts:53-57`, `105-108`. |
| Critical | `packages/runtime/src/runtime-engine.ts:570` `recordDelegatedRunCompleted`; `591` `recordDelegatedRunFailed`; `612` `recordDelegatedRunCancelled`; `633` `cancelParentDelegation` | Delegated handoff and parent cancellation are non-model state changes that bypass visible command recording. | Exercised by `tests/runtime/delegation-joins.test.ts:157-167`, `200-203`, `234-242`. |
| High | `packages/runtime/src/runtime-engine.ts:654` `requestCheckpoint` | Trusted runtime/operator checkpoint path appends `checkpoint.created` or `annotation.recorded` without visible command envelope. | Exercised by `tests/runtime/checkpoint.test.ts:133-139`, `165-171`. |
| High | `packages/runtime/src/runtime-engine.ts:673` `recordActionOutcomeUnknown` | Unknown outcome and reconciliation wait creation are system mutations that append directly. | Exercised by `tests/runtime/action-reconciliation.test.ts` and `tests/runtime/check-gate.test.ts:111-119`. |
| High | `packages/runtime/src/runtime-engine.ts:1005-1127` `modelOutputToEvents` fallback `complete_run` case | Fallback still emits `run.completed` directly. The guarded branch at `437-490` handles legality; later audit must prove the fallback is unreachable or unsafe. | No direct negative proof found in current tests. |
| Medium | `packages/runtime/src/action-dispatcher.ts:110-117` and `120-133` | Denied/unsupported actions can still emit `action.failed` after `action.created`. This may be semantically valid, but later phases should check it against “rejected Commands produce no target lifecycle Events.” | Covered indirectly by action lifecycle tests, not audited here. |
| Medium | `examples/governed-coding-run/run.ts:333` | Public example normalizes a raw append pattern for `check.recorded`. Even if intentional, it weakens the “runtime APIs only” teaching surface. | Example is part of milestone evidence surface. |

## Flow Map

### Approval flow

- Model path enters `RuntimeEngine.recordModelOutput` at `packages/runtime/src/runtime-engine.ts:171-268`.
- Policy check happens through `evaluateCapabilityPolicy` and `ActionDispatcher.dispatchAction`.
- Approval waits are created by `packages/runtime/src/wait-approval-control.ts:26-76`.
- Operator resolution goes through `RuntimeEngine.resolveApproval` at `754-800`, which does create `command.recorded`.
- Approved continuation goes through `continueApprovedAction` at `803-903`, also with `command.recorded`.
- Strong existing proof: `tests/runtime/wait-approval.test.ts:25-100`, `104-145`, `200-249`.
- Remaining gap: the initial deferred action path emits `action.created` before approval, so later phases should verify this matches the intended Command semantics.

### Reconciliation flow

- Unknown outcome drafts come from `packages/runtime/src/action-reconciliation-control.ts:40-111`.
- Runtime entry `recordActionOutcomeUnknown` at `673-691` appends those drafts without visible command recording.
- Operator reconciliation goes through `reconcileActionOutcome` at `694-746` and correctly records `command.recorded` first.
- Strong proof points: `tests/runtime/check-gate.test.ts:73-135` for completion blocking; `tests/views/action-reconciliation.test.ts` for derived view stability.

### Completion legality flow

- `complete_run` legality gate lives in `packages/runtime/src/runtime-engine.ts:437-490`.
- Gate logic delegates to `packages/runtime/src/check-control.ts:74-128`.
- Rejected completion emits rejected `command.recorded` plus `model_call.failed`, not `run.completed`.
- Strong proof: `tests/runtime/check-gate.test.ts:19-39`, `44-68`, `73-132`, `300-350`.
- Gap: fallback `modelOutputToEvents(...complete_run...)` at `1113-1126` still exists and should be challenged in Phase 14.

### Delegation flow

- Model-created delegation spawn is guarded through `recordModelOutput` at `346-374` and `createDelegationSpawnEvents` at `71-160`.
- Join waits are guarded through `recordModelOutput` at `376-397` and `createDelegationJoinEvents` at `193-265`.
- Child handoff completion/failure/cancellation is appended by runtime methods at `570-652` without visible command recording.
- Strong proof: `tests/runtime/delegation-joins.test.ts:127-176`, `181-210`, `213-253`.

### Checkpoint flow

- Model checkpoints are guarded through `recordModelOutput` at `399-435`.
- Trusted runtime/operator checkpoints go through `requestCheckpoint` at `654-670` and `createCheckpointEvents` at `72-156`.
- Protected event type validation is explicit in `checkpoint-control.ts:158-181`.
- Strong proof: `tests/runtime/checkpoint.test.ts:89-118`, `120-145`, `148-200`.
- Gap: trusted runtime/operator checkpoint path still bypasses visible command recording.

### Bundle export / verify / replay / import / resume flow

- Runtime API forwards through `packages/runtime/src/runtime-engine.ts:515-567`.
- Bundle implementation lives in `packages/runtime/src/orun.ts:281+` `exportBundle`, with verify/replay/import/resume helpers further down the same file.
- Views are rebuilt from canonical facts via `rebuildViews` in `packages/views/src/index.ts:41`.
- Strong proof: `tests/runtime/orun-bundle.test.ts:10-184` and `tests/runtime/orun-replay-resume.test.ts:14-139`.
- This surface is secondary and portability-focused; it does not append live Run events.

### Raw append flow

- Production raw append API is `RuntimeEngine.append` at `packages/runtime/src/runtime-engine.ts:142-143`.
- Storage-level append is `RuntimeEventLog.append` at `packages/runtime/src/event-log.ts:12-24`, then `SqliteRunEventStore` in `packages/storage-sqlite/src/sqlite-store.ts:34+`.
- Public/example evidence of raw append:
  - `examples/governed-coding-run/run.ts:333`
  - `tests/runtime/check-gate.test.ts:53`, `80`, `243`, `318`
  - `tests/runtime/wait-approval.test.ts:165`, `220`
  - `tests/runtime/interaction-waits.test.ts:168`
  - `tests/runtime/timer-waits.test.ts:130`
- Later phases should decide whether raw append is an internal fixture/admin API, or a semantic bug.

## Competitor Comparison

| System | Primary claim from official docs already captured in `11-RESEARCH.md` | Overlap with OpenRund | What OpenRund must prove differently |
|---|---|---|---|
| Temporal | Durable execution and replay across crashes/outages. | Persistence, replay, long-running recovery. | Durable execution alone is insufficient; OpenRund must prove Engine-owned legality before proposed operations become history. |
| Kitaru | Long-running Python agent runtime with checkpoints, replay, waits, isolated execution, versioned deployments. | Agent runtime durability, waits, replay. | OpenRund must prove that governed side effects are first-class runtime semantics, not just long-running execution features. |
| Microsoft Agent Framework / AGT | Enterprise agent framework with agents, graph workflows, conversation state, middleware, telemetry, integrations, checkpointing, HITL. | Broad orchestration and governance-adjacent features. | OpenRund’s narrower claim is persisted Command/Event legality proof, not general enterprise agent orchestration breadth. |
| OpenAI Agents SDK | Agents, tools, handoffs, tracing, conversation state, guardrails. | Tooling, handoffs, tracing, guardrails. | OpenRund must prove guardrail-like decisions are runtime-authoritative and replayable from canonical artifacts, not app-layer checks. |
| LangChain Deep Agents | Planning harness with filesystem, subagents, memory, runtime features. | Deep-agent ergonomics, subagents, context plumbing. | OpenRund must prove governance of consequential side effects, not planning depth or harness flexibility. |

## Most Important Existing Tests For Later Phases

- `tests/runtime/check-gate.test.ts`: best current proof for completion legality and blocked completion.
- `tests/runtime/wait-approval.test.ts`: strongest approval defer/resolve/continue coverage.
- `tests/runtime/interaction-waits.test.ts` and `tests/runtime/timer-waits.test.ts`: show current naked non-model wait mutation paths.
- `tests/runtime/delegation-joins.test.ts`: shows delegated handoff semantics and current non-model append path.
- `tests/runtime/checkpoint.test.ts`: shows trusted checkpoint behavior and protected-event fail-closed checks.
- `tests/runtime/orun-bundle.test.ts` and `tests/runtime/orun-replay-resume.test.ts`: strongest bundle and resume-safety proof.
- `tests/examples/governed-coding-run.test.ts`: important because the public demo shapes operator expectations.

## Actionable Work For Phases 12-14

- Phase 12 ontology audit should inspect exported semantic nouns starting with:
  - `packages/core/src/model.ts::CommandDecisionRecord`
  - `packages/runtime/src/checkpoint-control.ts::RuntimeCheckpointRequest.retainedFacts`
- Phase 14 command-path audit should start with:
  - `packages/runtime/src/runtime-engine.ts::append`
  - `packages/runtime/src/runtime-engine.ts::resolveInteraction`
  - `packages/runtime/src/runtime-engine.ts::fireTimer`
  - `packages/runtime/src/runtime-engine.ts::recordDelegatedRunCompleted`
  - `packages/runtime/src/runtime-engine.ts::requestCheckpoint`
  - `packages/runtime/src/runtime-engine.ts::recordActionOutcomeUnknown`
  - `packages/runtime/src/runtime-engine.ts::modelOutputToEvents`
- Example/demo audit should decide whether `examples/governed-coding-run/run.ts::runGovernedCodingDemo` may keep direct check append behavior.
- CLI audit can treat `packages/cli/src/index.ts::commandsCommand`, `::runsCommand`, and `::orunCommand` as secondary-surface readers, not authority candidates.
