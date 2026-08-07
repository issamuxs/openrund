# Phase 31: Engine Authority and Core Run Semantics — Research

**Researched:** 2026-08-05  
**Scope:** Normative OpenRund documentation, frozen compatibility corpus, and the implemented Python contract/View/storage boundaries. External research is unnecessary because this phase implements a repository-defined authority protocol rather than selecting a changing third-party technology.

## Recommendation

Build a small Engine module around one public asynchronous `submit(Command) -> CommandResult` method. The method must read a complete Run history, rebuild authoritative Views, evaluate hard legality, construct one durable command decision, and atomically append `command.recorded` plus any accepted lifecycle Events at the observed position. All convenience methods and model-proposal adapters must create a Command and call this method.

This is a semantic port, not a line-for-line port. The previous implementation's publicly reachable append paths must not survive: the architecture and Phase 31 success criteria make the Engine the only lifecycle authority.

## Existing Foundations

- Phase 28 provides final frozen IDs, Content, Commands, decision traces/records, all lifecycle payloads, explicit Event codecs, clock/ID protocols, and the provider-proposal seam.
- Phase 29 provides deterministic complete-history rebuilding, current Run state, pending Waits, Action uncertainty, Artifact availability, semantic Check results, and exhaustive completion blockers.
- Phase 30 provides expected-position atomic Event append, deterministic gap-free reads, duplicate Event protection, and durable SQLite custody.
- The frozen corpus authenticates exact `command.recorded`, Run, Message, and ModelCall wire shapes.

## Authority Pipeline

1. Validate the Command and capture its stable identity.
2. Read the Run from position 1 to the current end and prove the slice complete and contiguous.
3. If the same `CommandId` is already recorded, reconstruct and return its durable decision.
4. If a different prior Command owns the same explicit idempotency key, record a superseded attempt linked to that Command.
5. Rebuild Views at the exact observed watermark.
6. Evaluate lifecycle, operation schema, Wait state, required evidence, and known-outcome invariants in deterministic order.
7. Preallocate target Event IDs for an accepted decision and record every result ID in the decision.
8. Build one `command.recorded` Event followed by accepted target lifecycle Events carrying the Command ID.
9. Append the ordered batch at the observed position.
10. On expected-position conflict, repeat from step 2 with the same Command identity and a bounded retry budget.

Any storage failure is an infrastructure error, not a durable rejection. If no append commits, there is no `command.recorded` fact. A host may safely retry the same Command ID.

## Operation Surface for Phase 31

The semantic kernel already models provider operations but lacks typed runtime lifecycle operations even though `RuntimeOperationKind` declares them. Add the minimal inert operation values needed by this phase:

- `BootstrapRunOperation`
- `StartRunOperation`
- `MessageDeltaOperation`
- `StartModelCallOperation`
- `CompleteModelCallOperation`
- `FailModelCallOperation`
- `CancelModelCallOperation`

Existing `AddMessageOperation`, `CompleteRunOperation`, `FailRunOperation`, and `CancelRunOperation` remain shared. Coordination, Actions, Authority, Checks, and other declared runtime operations remain deferred to later phases and must receive an explicit unsupported-operation rejection during Phase 31.

Bootstrap is one Command whose accepted batch is `command.recorded`, `run.created`, and `run.started`. This preserves a complete attempt audit from the first durable mutation. Its input owns root/parent/title/objective/metadata and completion requirements; the accepted Event sequence remains compatible with the established payloads.

## Legality Rules

Evaluation is pure over `(Command, Views)` and yields a typed decision plus an explicit Event intent. It does not allocate IDs, read clocks, append Events, call providers, or perform effects.

Minimum lifecycle matrix:

| State | Legal operations |
|---|---|
| no Run | bootstrap only |
| created | start, fail, cancel |
| running/waiting | message/model lifecycle and Run terminal operations subject to entity state and blockers |
| completed/failed/cancelled | none; every later mutation attempt is durably rejected |

Completion must reject when the Run View reports any pending Wait (including joins), missing required Artifact, unsatisfied semantic Check, or unknown Action outcome. The trace names every blocker with stable related entity IDs; it must not collapse them into one opaque reason. A derived `ready` value is explanatory input only—the Engine owns the actual accept/reject decision.

Message and ModelCall transitions require existing IDs to be consistent: delta needs an existing Message; complete/fail/cancel needs a currently active ModelCall; duplicate terminal outcomes are rejected. Provider, transport, and parse failures are ModelCall failure Events produced by runtime Commands. A well-formed provider proposal becomes a model-origin Command and may independently be rejected by legality.

## Command Evidence

Use the existing record branches exactly:

- accepted: non-empty result Event IDs and a present target Event;
- rejected: empty results, stable rejection code, absent target;
- deferred: empty results, one linked Wait record, absent target;
- superseded: empty results, replacement Command link, absent target.

The runtime decision type may carry richer reason/Wait arrays while the frozen Event record retains the exact v1 branch. Phase 31 should use one Wait for a deferred record and keep additional blocker IDs in the trace/metadata. Supersession is declaration-only in its wire contract; use it only for an explicit idempotency-key collision, never to erase or replace a committed Command.

The command content hash must be SHA-256 of the canonical encoded `Content`. Add a public codec-boundary helper if necessary; never duplicate private wire aliases in the Engine.

The frozen payload distinguishes only model and runtime origins. Preserve the full `CommandOrigin` in compact metadata and use `origin_actor`, provider, and ModelCall fields where applicable. This retains exact v1 serialization while keeping user/client/operator/timer/capability/recovery attempts inspectable.

## Concurrency and Recovery

Expected-position conflicts are normal optimistic concurrency. The Engine must re-read and re-evaluate because an intervening terminal Event, Wait, completion blocker, duplicate Command, or idempotency owner can change legality. Retry count must be finite and validated; exhaustion raises the stable concurrency error without fabricating a decision.

The duplicate-Command fast path must be based on durable `command.recorded` history, not a process-local cache. It reconstructs the public `CommandResult` from the recorded branch. If a malformed historical record cannot be reconstructed, fail closed as corrupt history.

Because the EventStore protocol is public infrastructure, direct store use cannot be made impossible for a malicious host. The architectural guarantee is that no runtime/provider/worker facade exposes or invokes append and every supported mutation surface routes through Engine. Hygiene tests should enforce this dependency boundary.

## Security and Failure Modes

| Failure mode | Required control |
|---|---|
| Authority bypass | No public Engine append/store property; architectural import tests |
| Audit gap | Exactly one `command.recorded` in every successful attempt append |
| Target without accepted evidence | Single atomic ordered append batch |
| Stale legality after race | Re-read and re-evaluate after expected-position conflict |
| Incomplete/corrupt history | Require contiguous complete replay; fail closed before decision |
| Provider output escalation | Proposal adapter creates model Command only |
| Terminal resurrection | Terminal status rejects every later mutation |
| Hidden completion blocker | Exhaustively map View blockers into decision trace |
| Sensitive failure leakage | Stable codes/messages; provider evidence stored only as governed Content |
| Non-deterministic replay | Inject clock/IDs; explicit exhaustive event construction |

## Implementation Guidance

- Keep `_legality.py` independent and synchronously testable.
- Keep Event materialization explicit per operation; use an exhaustiveness assertion for unknown branches.
- Keep Engine dependencies narrower than the full future `RuntimeDependencies`: EventStore, clock, and only Phase 31 ID factories.
- Use complete paged reads if the store is limited; never infer completeness from a short arbitrary page.
- Return immutable `CommandResult`; inspection continues through replay Views and Events.
- Do not add assembly, CLI prompts, capability execution, provider loops, Bundle I/O, or UI artifacts in this phase.

## Verification Strategy

Focused tests must prove decisions and exact appended Events, not implementation call counts alone. Concurrency tests must coordinate two writers at the same observed position and verify one re-evaluates. Compatibility tests must encode new records and compare against authenticated frozen shapes. The final gate includes full pytest, strict mypy, Ruff, lock, build, and installed-wheel typing.
