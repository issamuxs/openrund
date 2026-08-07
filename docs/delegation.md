# Delegation

Delegation creates contract-bound child Runs. This page defines creation,
Authority narrowing, joins, handoff, cancellation, and replay.

## Concepts

- Parent Run: the Run that delegates.
- Delegated Run: a Run with `parentRunID`.
- Delegation: parent/delegated Run relationship and contract.
- Join Wait: `Wait(kind = join)` over one or more delegated Run IDs.

Delegated Run lifecycle, Delegation lifecycle, and join Wait lifecycle are
separate.

Delegated Runs operate only under Authority explicitly granted through the
Delegation contract. A delegated Run cannot silently inherit or expand parent
Authority, and delegated terminal Events do not automatically become parent
terminal Events.

Creation, join resolution, cancellation, and handoff use the mutation path
defined in [Control](./control.md).

## Creation

Before accepting `create_delegation`, the Engine validates the requested child
lineage, delegated Run kind, active parent Authority, action and policy subsets,
resource constraints, budget, nested-delegation permission, worker nesting, and
input Artifact references. A requested grant must be a narrowing of a current
parent grant; omitted constraints do not mean unbounded Authority.

Establishment is a single expected-position transaction across the parent and
child streams. It commits:

- parent `command.recorded` and `delegation.created` Events;
- child `run.created` and `run.started` Events;
- the child's bounded `authority.granted` Events.

The transaction preallocates all Event and relationship identities. Any
position conflict or storage failure commits none of the streams, after which
the stable Command may be retried from newly replayed history.

## Contract

A Delegation contract defines:

- delegated Run kind;
- objective;
- Authority grants;
- budget policy;
- result schema;
- nested delegation policy;
- parent cancellation behavior;
- late handoff behavior.

It also declares the expected result kind and required result Artifact kinds.
The delegated Run cannot complete with a different result kind or omit a
required Artifact kind.

Late handoff behavior defines how delegated results are treated when the parent
Run has already advanced, failed, cancelled, or completed.

## Joining

A parent waits for delegated Runs through `Wait(kind = join)`.

Join Waits can use:

- `all`
- `any`
- `quorum`

A delegated Run completing does not automatically resolve a join Wait unless
the join condition is satisfied. Even after satisfaction, resolution is an
explicit parent Command and durable `wait.resolved` Event.

A delegated Run reaching a terminal state does not itself authorize parent
advancement or completion. Parent legality remains governed by the join Wait,
Delegation contract, Checks, and completion rules.

Pending join Waits may block parent completion legality. Delegated Runs may
produce unknown outcomes or reconciliation Waits; parent advancement and
completion legality may depend on those delegated runtime states.

The `all`, `any`, and `quorum` modes evaluate only the target child Runs and the
configured outcome filter. Duplicate targets, invalid quorum values, unknown
children, and mismatched Delegation identities fail closed.

## Handoff

Child completion, failure, or cancellation is observed by the parent only
through an explicit handoff Command. The Engine reads complete child history
and verifies the established relationship, exact child identity, terminal
state, result kind, and required Artifacts before recording
`delegation.completed`, `delegation.failed`, or `delegation.cancelled` on the
parent.

Duplicate handoff and wrong-child attempts are rejected. If the parent is
already terminal, the contract's late handoff policy is applied durably:
`ignore` records the rejected attempt, `surface` records the terminal
Delegation fact, and `add_to_context` records that fact plus a canonical
Annotation. None changes the parent's terminal state.

## Cancellation

Parent cancellation applies every active Delegation contract. `cancel` commits
the parent cancellation, parent `delegation.cancelled`, and child
`run.cancelled` facts atomically across streams. `detach` and `allow` leave the
child Run untouched. A missing child or cross-stream position conflict fails
closed instead of partially cancelling the topology.

## Replay

Delegation topology, Delegation contracts, join Waits, handoff Events, and
Delegation lifecycle Events are replayable through canonical runtime history and
Bundles. Replay reconstructs Delegation state from Events; it does not decide
new legality or resume delegated work by itself.
