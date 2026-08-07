# Events

Events are immutable facts in a Run's ordered log. This page defines their
envelope, wire encoding, catalog, and payload rules. [Control](./control.md)
defines which Command decisions may materialize them.

## Envelope

Every persisted Event has:

- required `id`
- required `runID`
- required `position`
- required `type`
- required `version`
- required `timestamp`
- required `actor`
- required `payload`
- optional `causationID`
- optional `correlationID`
- optional `commandID`

`causationID` links an Event to the runtime transition or Event that directly
caused it. `correlationID` groups related runtime activity across Commands,
Actions, Waits, Delegations, and reconciliation flows.

The envelope allowlist is exact. A v1 reader rejects an unexpected envelope
member with `event_unknown_envelope_field`; an Event-specific payload decoder
rejects an unexpected payload member with `event_unknown_payload_field`.
Extensions require a new Event version rather than an unregistered field.

## Version, Presence, And Position

The only supported Event version is the JSON number `1`. Version `0` is
rejected with `event_version_invalid`; a positive unsupported version is
rejected with `event_version_unsupported`. Boolean values never satisfy a
numeric field, even in hosts where booleans are integer subtypes.

Required fields must be present and non-null. Optional semantic fields whose
value is `MISSING` are omitted. An explicit Python `None` encodes as JSON
`null`, remains present, and is distinct from omission. It is accepted only
where that Event/version schema declares a nullable value and is never silently
converted to absence.

`position` is a one-based, contiguous sequence local to one Run. The first
persisted Event has position `1`; therefore the expected watermark is `0` for
an empty Run. A writer advances the watermark by exactly one for every append.

## Canonical Wire Encoding

Event frames use UTF-8 without BOM, contain one compact JSON value per line,
and end with exactly one LF byte. CRLF, extra surrounding whitespace, and
multiple trailing newlines are non-canonical. The codec emits the exact v1 JSON
string escaping and compact number spelling; there is no implicit Unicode
normalization before encoding or hashing.

Hashes serve two different contracts:

- A raw-frame hash covers the exact persisted bytes, including the final LF.
- A canonical JSON value hash sorts object keys recursively, preserves array
  order, emits compact JSON, and hashes the resulting UTF-8 bytes without a
  trailing LF.

Writers accept only finite JSON numbers. Integer-valued versions, positions,
counters, quotas, and millisecond durations must also fit the v1 safe-integer
range; booleans, `NaN`, infinities, and out-of-range integers are rejected at
typed boundaries. The v1 renderer uses shortest-round-trip finite fraction
spelling and emits signed zero as `0` in raw bytes and canonical preimages.

Timestamps use UTC RFC 3339 with exactly three millisecond digits and a `Z`
suffix, for example `2026-08-04T17:42:36.000Z`. Offset timestamps, missing or
additional fractional digits, leap-second spellings, and non-canonical dates
are rejected.

## Grammar

Canonical Event names use:

```text
<subject>.<verb>
```

Canonical subjects:

- `run`
- `command`
- `message`
- `model_call`
- `action`
- `wait`
- `delegation`
- `check`
- `checkpoint`
- `annotation`
- `artifact`
- `authority`
- `lease`

## Current Event Catalog

| Subject | Event types |
|---|---|
| Run | `run.created`, `run.started`, `run.completed`, `run.failed`, `run.cancelled` |
| Command | `command.recorded` |
| Message | `message.added`, `message.delta` |
| ModelCall | `model_call.started`, `model_call.completed`, `model_call.failed`, `model_call.cancelled` |
| Action | `action.created`, `action.started`, `action.completed`, `action.failed`, `action.cancelled`, `action.unknown`, `action.reconciled` |
| Wait | `wait.created`, `wait.resolved`, `wait.cancelled`, `wait.expired` |
| Delegation | `delegation.created`, `delegation.completed`, `delegation.failed`, `delegation.cancelled` |
| Check | `check.recorded` |
| Checkpoint | `checkpoint.created` |
| Annotation | `annotation.recorded` |
| Artifact | `artifact.created`, `artifact.unavailable` |
| Authority | `authority.granted`, `authority.revoked` |
| Lease | `lease.acquired`, `lease.released`, `lease.expired` |

## Payload Variants

Each row in the frozen compatibility inventory is a distinct v1 payload
variant. Python uses separate final frozen payload classes for variants that
share an Event type, including aggregate, approval, interaction, timer, join,
and reconciliation Waits; delegation contract and handoff records; capability
and policy authority grants; and canonical versus backward-read message and
annotation forms.

Current writers emit preview-shaped `message.added` and
`annotation.recorded` payloads, a structured `action.failed.error` object,
flat checkpoint positions, and explicit capability or policy authority grant
payloads. Historical content-shaped messages and annotations are accepted only
by backward readers. They are not alternate writer forms.

Payload extension data is accepted only at pointers allowlisted for the exact
Event name and version, including `/payload/content/data`,
`/payload/content/metadata`, and explicitly open metadata containers. Allowed
extension values are preserved and hashed; every other payload key fails with
`event_unknown_payload_field` and its offending JSON pointer. A missing
required payload or envelope field fails with `event_missing_required_field`.

## Command Events

`command.recorded` persists the attempted mutation together with its origin,
associated CommandDecision, decision trace data, result Event IDs, Wait
linkage, and replacement linkage. This is the primary Event for explaining why
runtime transitions were accepted, rejected, deferred, or superseded.

Every successful Engine attempt append contains exactly one
`command.recorded`. Accepted target Events follow it atomically, list their IDs
in the decision record, carry the Command ID in their envelopes, and use the
command Event as direct causation. Rejected, deferred, and superseded decisions
have an absent target and no result Event IDs. A superseded decision is writer
eligible only as a complete `command.recorded` Event with an explicit
replacement Command link; an isolated declaration is read-only evidence.

## Wait Payloads

`wait.created` includes `waitID`, `kind`, target information, reason, optional
deadline, and payload. Approval Waits may include action input preview and
policy snapshot data.

`wait.resolved` includes `waitID`, `kind`, decision/result data, and optional
`approvedInput` when an approval Wait authorizes a revised input inside allowed
workspace roots.

Approval Wait resolution does not itself authorize execution. Approved input is
revalidated through Command evaluation before Action lifecycle Events are
materialized.

Every concrete Wait request carries a stable `waitID` and explicit `kind`.
Exactly one matching `wait.resolved`, `wait.cancelled`, or `wait.expired` Event
may terminate it. Terminal Events with a mismatched kind, duplicate terminal
attempts, timer fires before their deadline, and joins before satisfaction are
rejected without target lifecycle Events.

## Action Outcome Events

`action.unknown` records epistemic uncertainty about whether a consequential
side effect occurred. `action.reconciled` records evidence-backed runtime
resolution of that uncertainty. Reconciliation is additive; it does not rewrite
the original unknown outcome.

Marking an Action unknown atomically creates its reconciliation Wait. A
reconciliation Command must name the exact unknown Event and provide valid
evidence; acceptance atomically appends `action.reconciled` and resolves that
Wait. Known, failed, and cancelled outcomes remain distinct branches.

## Delegation Events

Delegation Events record the lifecycle of governed delegated sub-work under
explicit Delegation contracts. Delegated terminal Events do not themselves
authorize parent advancement or parent completion legality.

The contract-form and handoff-form `delegation.created` Events are paired parent
facts: one records the bounded contract and the other commits the exact child
Run relationship and first position. Creation also commits the child's Run
lifecycle and bounded Authority Events in the same cross-stream transaction.
Parent terminal Delegation Events occur only after explicit, validated handoff
Commands.

## Authority And Lease Events

Authority Events record runtime-granted constrained Capability use for a Run.
Authority is scoped and may be bounded by policy, Delegation contracts,
resource constraints, or lifecycle conditions.

Lease Events coordinate execution ownership and operational concurrency. They
do not themselves authorize runtime legality transitions.

## Check Payloads

`check.recorded` records semantic validation. The payload includes check
identity, subject, result, message, and Artifact-backed evidence when present.
Only Checks named by a completion contract affect terminal legality. Diagnostic
Checks, Checkpoints, and Annotations are explanatory history and cannot certify
their own Authority or bypass a semantic requirement.

## Bundles

Bundles transport canonical Event history together with Artifacts and derived
runtime surfaces required for replay and legality explanation.

## Event Rules

- Events are append-only.
- Event order is authoritative per Run.
- Payloads should stay compact.
- Large or durable content belongs in Artifacts.
- Views must be rebuildable from Events and Artifacts.
