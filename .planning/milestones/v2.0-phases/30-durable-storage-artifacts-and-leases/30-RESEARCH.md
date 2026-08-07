---
phase: 30-durable-storage-artifacts-and-leases
status: complete
created: 2026-08-05
sources: [normative-docs, frozen-corpus, phase-28-python-contracts, phase-29-views, official-sqlite, official-python]
---

# Phase 30 Research — Durable Storage, Artifacts, and Leases

## Recommendation

Implement one pure-Python `openrund.storage` package using the standard-library `sqlite3` module and local filesystem primitives. Keep the async public ports, but execute each whole database operation on a worker thread with a fresh, short-lived connection. Own every write transaction entirely inside that worker operation: configure the connection, issue `BEGIN IMMEDIATE`, validate current state, mutate, commit, close, then return domain values. No `await` occurs while a transaction or connection is open.

Use an additive, versioned schema shared by Events, Artifact metadata, and Leases. Preserve the authenticated v1 table and index names, retain nullable compatibility columns, and add only the integrity metadata required by the Python implementation. Store Artifact bytes outside SQLite under a configurable local root through a stage → sync → absent-only publish → metadata-commit protocol, followed by explicit recovery for every mismatch the protocol can leave behind.

## Normative Constraints

- Events are immutable, one-based, contiguous facts per Run; empty history has watermark zero.
- An append succeeds only when its expected position equals the committed Run watermark.
- A stale expected position is a distinct concurrency outcome, not a generic storage failure.
- Delegation later requires one transaction capable of appending to multiple Run streams; sequential best-effort writes are not atomic.
- Post-commit observers are advisory. Their failure cannot roll back, conceal, or make a successful commit appear unsuccessful.
- Artifact metadata is immutable and bytes are content-addressed by declared length and SHA-256 integrity.
- Large output remains outside Event payloads; Events carry Artifact references and lifecycle facts.
- Leases coordinate executors but never grant runtime Authority or decide legality.
- Every Run has deterministic configurable `runtime/`, `workspace/`, and `exports/` locations.
- This phase exposes Python library contracts and tests only. It creates no graphical or command-line interface.

## SQLite Execution Model

SQLite permits multiple readers but only one writer. `BEGIN IMMEDIATE` acquires the write transaction at the boundary where OpenRund wants to compare the expected watermark, so a competing writer either waits within the configured bound or returns `SQLITE_BUSY`; it cannot both read a stale watermark and then mutate it. This matches the [SQLite transaction semantics](https://www.sqlite.org/lang_transaction.html).

Each operation should:

1. open a connection with explicit transaction control;
2. apply `foreign_keys=ON`, a bounded `busy_timeout`, and verify `journal_mode=WAL`;
3. use `synchronous=FULL` for durable commits;
4. run migrations before the adapter becomes available;
5. execute a complete synchronous operation through `asyncio.to_thread`;
6. explicitly roll back on every exceptional path and close the connection.

WAL allows readers and a writer to overlap, but still has one writer and requires all participants to share one host; it is not a network-filesystem design. Checkpoint starvation can grow the WAL when reads are held open, which reinforces short connections and bounded transactions. These constraints come directly from the [SQLite WAL documentation](https://www.sqlite.org/wal.html). Busy waiting is configured through [`PRAGMA busy_timeout`](https://www.sqlite.org/pragma.html#pragma_busy_timeout), not unbounded retry loops. Python 3.12 exposes the required explicit connection and transaction controls in the [`sqlite3` module](https://docs.python.org/3.12/library/sqlite3.html).

Connections are never shared across arbitrary tasks or threads. The adapter does not keep a cursor or read transaction alive across an `await`. SQLite exceptions are translated at the storage boundary into safe OpenRund errors; no SQL text, filesystem path, or raw payload appears in caller-visible error detail.

## Migration and Schema Contract

Use embedded, ordered migrations guarded by `PRAGMA user_version`. Migration runs within an exclusive setup transaction before normal operations. Reopening at the current version is idempotent; an unknown newer version fails closed.

Authenticated v1 schema surface:

| Table | Required columns and constraints |
|---|---|
| `run_events` | `event_id` primary key; `run_id`; `position`; `type`; `version`; `timestamp`; `actor`; nullable `causation_id`, `correlation_id`, `command_id`; canonical `payload_json`; unique `(run_id, position)` |
| `artifacts` | `artifact_id` primary key; `kind`; `created_at`; nullable `content_type`, `byte_length`, `blob_path`, `unavailable_at`; canonical `metadata_json` |
| `execution_leases` | `lease_id` primary key; unique `run_id`; `holder`; `token`; `acquired_at`; `expires_at` |

Retain `idx_run_events_stream` and `idx_execution_leases_active`. Add a nullable `sha256` Artifact column through a later migration so newly stored bytes can be verified while pre-existing metadata-only rows remain readable. Migrations must inspect schema state rather than assuming a pristine database, specifically supporting a pre-`command_id` `run_events` table.

## Event Custody

### Port corrections

- `AppendEventsResult.next_position` is the committed watermark, matching the final appended Event position.
- `EventSlice.next_position` is a read cursor: one greater than the last returned Event position; when no Event is returned it remains the requested `from_position`.
- Add an atomic `append_many` input/result protocol for distinct Run batches. Validate all batches before opening the transaction, lock once, verify every watermark, reject duplicate Event IDs across both storage and input, insert all rows, then commit once.

### Encoding and reading

Serialize only through the public Event codec boundary. Persist compact canonical JSON fields; decode rows back into validated `RuntimeEvent` values. Never use generic dataclass dumping or reflection.

Reads order by numeric `position`, apply a positive optional limit, and verify the returned positions are contiguous from the requested cursor. A gap, duplicate, wrong Run, or decode mismatch is `StorageIntegrityError`, never a partial trusted slice. Legacy SQL `NULL` values for optional envelope links decode as omitted fields.

### Conflicts and busy outcomes

- expected watermark mismatch → `ExpectedPositionConflict` with safe Run ID and positions;
- duplicate global Event ID or impossible unique-position failure after the checked watermark → storage integrity failure;
- exhausted configured busy timeout → distinct storage-busy concurrency failure;
- invalid encoded row or gap → storage integrity failure.

### Post-commit delivery

Provide a narrow post-commit Event log wrapper. It calls the durable store first and receives the committed result. Subscribers then receive the immutable appended tuple in registration order. Subscriber exceptions are caught and reported through an injectable failure sink; they never cause append retry, rollback, or a false failure result. Cancellation and process-level exceptions are not silently swallowed.

## Artifact Custody

### Storage value

The persistence port needs an `ArtifactEntry` distinct from the replay-oriented Artifact View value. It carries:

- Artifact ID, kind, created timestamp;
- optional content type, byte length, and SHA-256;
- immutable JSON metadata;
- optional unavailable timestamp.

`ArtifactBlob` remains an immutable bytes value. When bytes are present, the adapter computes their length and SHA-256 and requires exact agreement with declared metadata. A metadata-only Artifact has no blob path. Marking unavailable is an explicit state transition that preserves the immutable identity metadata.

### Publication protocol

1. Validate the Artifact ID as a safe single path component and resolve every internal directory beneath the configured Artifact root.
2. Write bytes with exclusive creation to a private staging file.
3. Flush and `fsync` the staged file and staging directory.
4. Publish to the final absent-only path. On supported local filesystems, an absent-only hard link is suitable; Python exposes this through [`os.link`](https://docs.python.org/3/library/os.html#os.link). A pre-existing destination is verified rather than overwritten.
5. Insert immutable metadata and the relative blob path in one SQLite transaction.
6. Remove the staging name and sync affected directories.

Never use overwrite-capable rename as the immutability primitive. Reject symlinks and ensure resolved paths remain under the configured root.

### Idempotency and recovery

Reusing an Artifact ID with byte-for-byte and metadata-for-metadata identical content may return the existing entry. Any differing field or byte digest raises `artifact_immutable`.

Fault injection points cover after staging, after publication, before metadata commit, and after metadata commit. Recovery scans only known internal directories and deterministically classifies:

- abandoned staging file → remove/quarantine;
- published blob without metadata → verify name/content, then quarantine as orphan;
- metadata referring to a missing or corrupt blob → preserve metadata and mark content unavailable;
- matching committed pair → leave untouched;
- metadata-only entry → leave readable without inventing bytes.

`get_blob` rechecks size and SHA-256 before returning bytes. Integrity failure marks or reports unavailable content explicitly; it does not return corrupt bytes.

## Lease Coordination

The persisted schema already includes a fencing `token`; the semantic Lease and ports must retain it. A lease contains ID, Run ID, holder, token, acquisition time, and expiry. The token is an opaque non-empty value generated through an injectable source.

- `acquire`: inside `BEGIN IMMEDIATE`, delete/replace only an expired lease for that Run; return `None` while an unexpired lease exists.
- `renew`: require lease ID, Run ID, holder, and token to match an unexpired row; extend from supplied `now`, not from a stale prior expiry.
- `release`: require lease ID and token; stale owners or stale tokens cannot release a replacement lease.
- `get_active`: return only when `expires_at > now`; expired custody is not active and may be pruned.

All time enters as validated `Timestamp` values. Storage does not call wall-clock time internally, grant Authority, append lifecycle Events, or decide whether an executor may mutate a Run.

## Deterministic Run Homes

Add a frozen `RunHome` layout value and one pure constructor accepting a configurable root plus a typed `RunId`. Validate the ID as exactly one safe local component even though typed IDs are non-empty: reject separators, dot components, NUL, drive prefixes, and platform alternate separators. Return lexical paths:

```text
<root>/runs/<run-id>/
├── runtime/
├── workspace/
└── exports/
```

Construction is pure and deterministic. Directory creation is an explicit separate operation that rejects symlinks and verifies containment. The layout never implies that `workspace/` or `exports/` is writable Authority; it is only a custody location.

## Compatibility Evidence

The frozen SQLite evidence authenticates 29 schema objects and representative rows across the three tables. Tests must verify fixture containment, size, and SHA-256 before using it, then prove:

- exact table, column, index, and constraint preservation;
- row decode with nullable envelope links;
- migration from the earlier schema shape;
- reopen without data mutation;
- no writes to the evidence tree.

Compatibility tests consume copied databases in temporary directories. They never rewrite or regenerate the frozen evidence.

## Validation Architecture

### Test layers

| Layer | Coverage |
|---|---|
| Contract unit | ArtifactEntry, fenced Lease inputs, Event cursor semantics, invalid path components |
| SQLite unit | migrations, exact schema, append/read, duplicate IDs, Artifact CRUD, Lease conditional writes |
| Concurrency | competing expected-position writers, atomic multi-Run writers, Lease acquisition, bounded busy |
| Crash injection | rollback, stage/publish/metadata boundaries, reopen recovery, missing/corrupt bytes |
| Compatibility | authenticated v1 schema/row evidence, nullable fields, earlier migration shape |
| Post-commit | subscriber ordering, failure isolation, no retry, committed result returned |
| Architecture | no Authority/Engine/CLI/UI imports or methods; no SQLite values escape ports |
| Release | full pytest, strict mypy, Ruff, lock, build, installed typing |

### Sampling

- After each task: the named focused storage file plus strict mypy/Ruff on touched files.
- After each wave: all `tests/storage` and `tests/ports` tests.
- Final gate: frozen compatibility set, concurrency/crash tests, complete project suite, typing, lint, format, lock, and build.

### Edge coverage

- EVT-01: empty watermark, first append, stale append, duplicate ID, input duplicate, gaps, limit boundaries, empty pages, competing writers, subscriber exception.
- ART-01: metadata-only, empty bytes, large bytes, identical reuse, conflicting reuse, unavailable transition, missing file, corrupt file, each injected crash point.
- STO-01: pristine migration, additive migration, repeated reopen, newer-version rejection, busy timeout, transaction rollback, read corruption.
- STO-02: active/expired boundary, stale fencing token, renewal at expiry, concurrent acquire, unsafe Run IDs, symlinked layout components.

All Phase 30 success criteria are machine-testable; no manual or visual validation is required.

## Security and Failure Model

| Threat | Required control |
|---|---|
| T-30-PATH | Single-component IDs, root containment, no symlink traversal, relative persisted blob paths |
| T-30-OVERWRITE | Absent-only publication, immutable equality checks, exclusive staging creation |
| T-30-CORRUPT | Length/hash verification on write, reopen, recovery, and read |
| T-30-RACE | `BEGIN IMMEDIATE`, SQL uniqueness, fencing tokens, atomic multi-stream transaction |
| T-30-BUSY | Configured finite timeout and a typed safe error; no infinite retries |
| T-30-PARTIAL | Explicit rollback, fault injection, deterministic recovery classification |
| T-30-LEAK | Safe stable error codes without SQL, local paths, raw metadata, or blob bytes |
| T-30-AUTHORITY | Import and surface tests prove storage/leases expose custody only |

## Prohibition Probe

No bespoke values, fairness, privacy, or product prohibitions apply to these local custody utilities. Path traversal, overwrite resistance, data integrity, and secret-safe errors are canonical security concerns and are covered by the Phase 30 threat model plus the later security audit; no separate judgment-only prohibition is minted.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Async cancellation leaves an in-flight thread operation | Treat the synchronous operation as indivisible; connection owns rollback/commit and closes independently of the awaiting task. |
| `asyncio.to_thread` creates many simultaneous writers | SQLite serializes writers; finite busy timeout produces a typed outcome. Later optimization may use a dedicated executor without changing ports. |
| Filesystem and SQLite cannot share one transaction | Stage and publish bytes before metadata commit, make each step idempotent, and recover every mismatch. |
| Legacy row lacks new digest | Keep the column nullable; bytes without a trusted digest are unavailable until explicitly verified/materialized. |
| Lease mistaken for permission | No Authority types or legality methods in storage; fenced token only coordinates ownership. |
| Cursor/watermark ambiguity | Encode write watermark and read cursor semantics in constructors and memory/SQLite conformance tests. |
| WAL used on unsupported filesystem | Verify returned journal mode and fail setup; document local-host custody boundary in API docstrings. |

## Implementation Boundaries

Phase 30 may change storage ports, the semantic Lease value, memory substitutes, path layout helpers, and package exports required for these adapters. It must not implement Engine command evaluation, Wait policy, Capability execution, provider behavior, Bundles, CLI rendering, or any UI artifact.
