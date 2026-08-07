# Phase 32: Governed Coordination and Recovery — Research

**Researched:** 2026-08-05  
**Scope:** Normative OpenRund documentation, authenticated compatibility evidence, and the implemented Python contract/View/Engine/storage boundaries. External research is unnecessary because this phase implements a repository-defined governance protocol.

## Recommendation

Extend the existing Engine rather than introducing coordinator services. Add immutable runtime operations for Wait terminals, approval resumption, Action uncertainty/reconciliation, Check and Annotation recording, Delegation handoffs, and Authority grant/revoke. Evaluate them from complete replay facts and materialize exact established Event payloads. Keep Capability execution absent: a governed Action may become durable `action.created` work in Phase 32, while dispatch starts in Phase 33.

## Existing Foundations

- The contract kernel already contains exact typed payloads for five Wait kinds and every terminal variant, Action unknown/reconciled outcomes, two Delegation creation variants and terminal handoffs, semantic Check reports, Checkpoint variants, Annotations, and Capability/policy Authority grants and revocations.
- Deterministic Views already reconstruct every pending Wait, current Action outcome, reconciliation queue, active Authority grant/rule, Delegation establishment, terminal handoff, join satisfaction, Check Report, Checkpoint, and completion blocker.
- Atomic stores already support expected-position multi-Run append, which is the correct primitive for parent/child Delegation creation and policy-driven cancellation.
- RuntimeEngine already guarantees complete history, durable Command recovery, one decision path, ordered attempt evidence, and re-evaluation after concurrency conflicts.

## Wait State Machine

Open approval, interaction, timer, join, and reconciliation Waits only while a Run is active. Each terminal operation identifies a Wait ID and expected kind; the Engine locates it in `replay.views.waits.all_pending`. Missing, mismatched, or already terminal Waits are rejected and durably audited.

Resolution branches are kind-specific:

- approval: approved, denied, or cancelled plus optional revised input and validation facts;
- interaction: governed response Content and optional request link;
- timer: injected current timestamp at or after the scheduled time;
- join: the current derived join must satisfy all/any/quorum and outcome policy;
- reconciliation: only the Action reconciliation Command resolves it.

Cancellation applies to any pending concrete Wait. Expiry requires a declared deadline or timer schedule and an injected timestamp at or after that boundary. Aggregate waiting Events remain explanatory compatibility facts; concrete Wait records own legality.

## Approval Is Not Legality

Action evaluation order is fail-closed:

1. Run lifecycle and operation structure;
2. registered Capability and action metadata;
3. declared input schema;
4. active durable Authority and allowed action constraints;
5. resource/workspace scope;
6. Delegation contract and lineage;
7. budget, tenant, and security context;
8. active durable policy rules.

Any hard failure produces rejection and no Wait. Only a valid Operation whose applicable policy explicitly requires approval produces a deferred decision and approval Wait. Approval resolution is a fact, not dispatch permission. `ResumeApprovedActionOperation` reconstructs the stored Action and approved input, then repeats the full current evaluation. Revoked Authority, changed policy, stale schema, or widened roots therefore reject resumption.

Use a small deterministic JSON-schema subset sufficient for current Capability definitions: object type, required keys, property types, arrays/items, enums, numeric/string/array bounds, and `additionalProperties`. Unsupported schema keywords fail closed rather than being ignored. Phase 33 may deepen registration and transport validation without changing the authority path.

## Trusted Governance Context

Durable Authority and policy come from Run history. Capability definitions and host security facts are trusted assembly inputs, not Command metadata. Add an immutable `GovernanceContext` containing validated Capability definitions, bounded workspace roots, and optional tenant/security facts. The evaluator combines that context with replayed grants/rules and emits criterion-by-criterion trace evidence. Registration never overrides a missing grant or another hard invariant.

Policy rules remain data, not executable code. Support a closed set of rule kinds needed by the runtime contract: deny a Capability/action, require approval for a Capability/action or mutation, and constrain tenant/security metadata. Unknown active policy kinds reject as unsupported rather than silently allowing work.

## Action Uncertainty And Recovery

An Action can become unknown only after it was durably created/started and before any terminal outcome. The accepted Command appends `action.unknown` and a concrete reconciliation `wait.created` fact. Completion remains blocked through both Action and Wait Views.

Reconciliation requires the current pending unknown Event ID, one of completed/failed/cancelled, and non-empty governed evidence Content. It appends `action.reconciled` plus the matching reconciliation `wait.resolved` in one batch. It never deletes the unknown fact or retries the external effect. Duplicate or mismatched reconciliation is rejected.

Semantic Checks use `check.recorded` and continue feeding completion rules. Diagnostic Checks use the same fact but do not satisfy a semantic requirement unless their result contains the named passed check. Checkpoints and Annotations remain compact, Artifact-linked explanatory facts. Their presence never grants Authority or makes completion legal independently.

## Delegation Establishment

Validate before any append:

- the parent is active;
- objective and result kind are non-empty and compatible with the requested contract;
- every delegated Capability/action is a subset of current parent Authority;
- budgets are positive and bounded by any parent Delegation budget;
- worker Runs cannot allow nesting and delegated parents respect their own nesting policy;
- child ID differs from parent, is absent, and lineage does not cycle;
- required Artifact kinds and late-handoff/cancellation policies are explicit.

Preallocate the parent decision/delegation Events, child Run creation/start and delegated Authority Events, then call `AtomicEventStore.append_many` once with parent and child expected positions. The parent batch begins with `command.recorded`; the child batch begins at position one. Any expected-position conflict restarts complete replay and validation.

## Delegation Handoffs And Joins

Child completion does not write the parent stream. A trusted host observes the child terminal state and submits an explicit complete/fail/cancel Delegation Command to the parent. Legality verifies the child relationship, current parent state, result kind, required Artifacts, duplicate terminal state, and late-handoff policy before recording the handoff.

A join Wait references established child Runs. The Delegation View derives completed, failed, cancelled, pending, and satisfied sets. A separate resolve-join Command may commit only when current all/any/quorum and outcome filters are satisfied. This preserves the invariant that View calculation never advances a Run.

Parent cancellation applies each Delegation contract deterministically. `cancel` contracts atomically append child cancellation and parent handoff facts; `detach` and `allow_completion` retain child autonomy and record no false terminal outcome.

## Security And Failure Modes

| Failure mode | Required control |
|---|---|
| Approval of illegal work | Run every hard invariant before policy defer |
| Stale approval | Full current revalidation on resume |
| Wait double terminal | Pending exact-kind lookup before materialization |
| Early timer | Compare injected now with scheduled/deadline timestamp |
| Blind Action retry | Unknown + reconciliation Wait; evidence-backed additive resolution |
| Authority escalation | Delegated grants must be a subset of current parent grants |
| Policy code injection | Closed data rule kinds; no evaluation or imports |
| Resource escape | Lexical root constraints plus fail-closed schema/scope checks |
| Parent/child split | One multi-Run expected-position transaction |
| Child auto-advancement | Explicit parent Command required for handoff/join resolution |
| Stale join | Rebuild and re-evaluate on every conflict |
| Explanation as authority | Checks, Views, Reports, and Annotations never create permission |

## Verification Strategy

Every operation needs focused legality and exact appended-Event tests. Wait tests cover every kind and terminal branch. Approval tests must distinguish rejection from defer and prove stale revalidation. Delegation tests use both memory and SQLite atomic stores and deterministic conflicts. Compatibility uses an explicit authenticated allowlist for Phase 32 Event variants without fixture generation. The release gate remains full pytest, strict mypy, Ruff, lock, build, installed-wheel typing, code review, security, and Nyquist validation.
