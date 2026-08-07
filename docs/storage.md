# Storage

Storage preserves durable ordering and content availability. It does not decide
runtime legality.

## Event Store

The Event store appends Events per Run by expected position. A position conflict
means another writer won; the caller must reload and retry from the new
watermark.

SQLite implementation:

- `SqliteRunEventStore`
- `ExpectedPositionConflict`

The canonical SQLite writer stores an Event's optional `commandID` in the
nullable `run_events.command_id` column. A supplied value is persisted and read
back exactly; absence is stored as SQL `NULL`. Opening a database without that
column adds it without rewriting existing rows. A stored `NULL` decodes by
omitting `commandID` from the Event envelope—it is never fabricated or emitted
as JSON `null`.

Raw storage evidence and decoded Event evidence are separate contracts:
`payload_json` retains the exact canonical payload bytes produced by the Python
codec, while the adapter parses those bytes and maps nullable link columns to
optional envelope fields. Causation, correlation, and Command links are
persisted independently.

An empty stream has expected watermark `0`, and its first Event is stored at
position `1`. Append positions remain contiguous. An append result's
`nextPosition` is the current committed watermark; a read result's
`nextPosition` is the cursor after its last returned Event.

## Artifact Store

Artifacts hold immutable content. Events and Reports reference Artifacts by ID.
Large content should not be embedded in Event payloads.

SQLite implementation:

- `SqliteArtifactStore`

An Artifact ID is immutable. Reusing an ID with different metadata or bytes is
an integrity error. Available bytes must match the recorded byte length,
SHA-256 digest, and content type. Writes stage bytes and metadata under runtime
custody and expose explicit recovery for interrupted staging.

Capability execution writes inline Artifact bytes before asking the Engine to
record `artifact.created` and the terminal `action.completed` Event. This order
prevents history from claiming content that never reached the Artifact store.
Large worker output remains in Artifacts; Event payloads carry only compact
identities, hashes, previews, effects, and evidence.

## Lease Store

Leases coordinate execution across workers or processes. A Lease is a
coordination token, not agent semantics.

SQLite implementation:

- `SqliteExecutionLeaseStore`

SQLite Event, Artifact, and Lease adapters are async context managers even
though each operation uses a short-lived configured connection. `aclose` is
idempotent and marks the adapter unavailable; later operations raise
`ResourceClosedError`. Explicit ownership lets a future pooled backend preserve
the same caller lifetime without changing storage contracts.

## OpenRund Home, Run Home, And Workspace Roots

The default OpenRund home is `~/.openrund`. Every Run owns a Run home beneath
that directory:

```text
~/.openrund/runs/<runID>/
  runtime/
  workspace/
  exports/
```

`runtime/` is runtime-owned storage for that Run. `workspace/` is the default
governed work-product root for that Run. `exports/` contains Run-local export
artifacts such as `.orun` Bundles.

Helpers:

- `default_openrund_home()`
- `run_home(root, run_id)`
- `materialize_run_home(layout)`

## Views And Snapshots

Views derive from Events and Artifacts. Storage may cache derived data, but a
cache must be discardable and rebuildable.

## Bundles

Bundle export writes a portable `.orun` directory under the selected output path.
The default Run-local path is:

```text
~/.openrund/runs/<runID>/exports/<runID>.orun
```

Storage preserves imported Bundle content under runtime custody; it does not
make imported history resumable by itself. Import copies only verified regular
files into a private sibling stage, verifies the staged copy again, writes the
import record, fsyncs material, and publishes the import directory absent-only.
An interrupted or colliding import exposes no partial Bundle as runtime custody.
See [Bundles](./bundles.md) for verification, replay, import, and
`ResumeAssessment` semantics.
