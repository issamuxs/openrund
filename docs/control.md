# Control

This document is the normative owner of OpenRund's authority loop.
`RuntimeEngine` is the sole procedural mutation-authority boundary: it is the
only component that decides and materializes authoritative Run mutations.
`CommandDecision` is the authoritative result of one attempted mutation.

```text
Operation -> Command -> CommandDecision -> Events -> Views
```

Providers produce Operations. Runtime APIs, timers, Capability results,
operators, and recovery procedures may construct Commands directly. Every
mutation then follows the same path.

## Decision outcomes

Each Command produces one decision:

| Decision | Meaning | Durable result |
|---|---|---|
| `accepted` | The mutation is legal now. | `command.recorded`, followed by target Events in the same append. |
| `rejected` | The mutation is illegal. | `command.recorded` only. |
| `deferred` | The mutation is legal but lacks a required condition such as approval. | `command.recorded` and, when required, a Wait. |
| `superseded` | Another durable Command owns the idempotent attempt. | `command.recorded` linked to that Command. |

Rejected, deferred, and superseded attempts do not produce the requested target
lifecycle transition. A decision records an attempted mutation; it does not
rewrite earlier history.

## Legality

The Engine evaluates a Command against:

- current Run and entity lifecycle;
- Operation schema and hard invariants;
- Authority and Delegation lineage;
- contracts, budgets, and required Checks;
- Capability metadata and resource constraints;
- tenant and security context;
- policy;
- pending Waits and unknown outcomes.

Hard failures are rejected. Examples include malformed input, missing or revoked
Authority, an unknown Capability, an escaping resource path, an exhausted
budget, or invalid Delegation lineage.

Policy may defer an otherwise legal Action for approval. Approval cannot
override a hard failure. When an approval is resolved, the Engine evaluates the
Action again against current facts before creating it.

## Command attempt

`RuntimeEngine.submit(Command)` performs one authoritative attempt:

1. Read the complete Run Event history from position 1.
2. Validate continuity and the observed watermark.
3. Rebuild deterministic Views at that watermark.
4. Return the durable result if the Command ID already exists.
5. Load the facts needed by the Operation and evaluate legality.
6. Materialize one `command.recorded` Event and any allowed target Events.
7. Append the ordered batch at the observed position.

Delegation creation and some cancellation paths append parent and child batches
atomically. All streams commit or none do.

An expected-position conflict restarts the entire attempt from durable history.
The stable Command ID survives the retry; uncommitted Event IDs do not.
Infrastructure failure is not a rejection and must not be recorded as one.

## Authority and reach

Visibility, registration, and Authority are separate:

- Visibility determines what a caller can see.
- Registration determines what a host can dispatch.
- Authority determines what a Run may use under specific constraints.

A registered or model-visible Capability is not automatically authorized.
Model, API, timer, Capability, and delegated-Run origins cannot grant or revoke
Authority. Only operator, system, or recovery Commands may attempt those
mutations, and the Engine still evaluates them.

## Waits

A Wait records a missing condition that currently blocks advancement. Opening,
resolving, cancelling, and expiring a Wait are governed mutations.

An approval decision records authorization; it does not create an Action.
`ResumeApprovedActionOperation` reconstructs the persisted request and repeats
schema, Capability, Authority, resource, lineage, budget, tenant, security, and
policy checks before `action.created` may be appended.

See [Concepts](./concepts.md#wait-kinds) for the five Wait kinds.

## External effects

`action.created` authorizes an Action to exist. It does not prove that work
started.

1. `ActionRunner` resolves the Capability route and validates the input.
2. The runner submits a start Command.
3. The Engine commits `action.started`.
4. The runner dispatches the invocation.
5. The worker returns `CapabilityResult` data.
6. The runner stores and verifies inline Artifact bytes.
7. The runner submits a terminal Action Command.
8. The Engine records completed, failed, cancelled, or unknown outcome Events.

A known worker rejection becomes `action.failed`. Confirmed cancellation
becomes `action.cancelled`. A crash, timeout, malformed result, or lost
transport after dispatch becomes `action.unknown` because the effect may have
occurred.

Reconciliation is a separate operator or recovery Command tied to the exact
unknown Event and supporting evidence. It adds history; it never rewrites the
unknown outcome. A model cannot reconcile its own Action.

See [Capabilities](./capabilities.md) for transports and built-in operations.

## Explanations

Operator APIs and the CLI derive explanations from Command decisions, trace
entries, Events, Artifacts, Views, Receipts, Reports, and Bundles. They can
explain why a mutation was accepted, rejected, deferred, superseded, or blocked
from completion. They do not decide legality.
