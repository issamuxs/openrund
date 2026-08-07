# Phase 28: Python Contract Kernel - Research

**Researched:** 2026-08-05
**Domain:** Typed Python semantic contracts and exact v1 wire codecs
**Confidence:** HIGH for frozen semantics; MEDIUM for greenfield Python organization

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
No locked decisions were recorded.

### the agent's Discretion
All implementation choices are at the agent's discretion because discuss phase was skipped per user setting. Use the ROADMAP phase goal and success criteria, requirements SEM-01, DX-01, DX-02, DX-03, DX-05, and DX-08, the frozen Phase 27 corpus, normative documentation, and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)
Derived Views, durable storage, Engine authority, coordination, capabilities, providers, Bundles, installed assembly, CLI, and release cutover remain assigned to Phases 29–37.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| SEM-01 | Construct and validate every canonical concept with kind-safe IDs and non-authoritative secondary names. | Concept/ID inventory, frozen values, tagged unions. |
| DX-01 | Use `snake_case` objects and explicit canonical aliases at one codec boundary. | `contracts`/`codec` dependency split and alias registry. |
| DX-02 | Ship frozen typed values, precise unions, complete annotations, and `py.typed`; validate untrusted boundaries. | Dataclass/union rules and strict typing gate. |
| DX-03 | Inject stores, clocks, ID factories, providers, transports, and reporters through structural protocols with deterministic fakes. | Narrow generic protocols and private `_testing` implementations. |
| DX-05 | Accept `os.PathLike` at runtime, workspace, database, Artifact, and Bundle boundaries without weakening sandbox/wire rules. | Separate local and portable path normalization. |
| DX-08 | Provide semantic exceptions for boundary/infrastructure failures while legality remains a result. | Exception tree and `CommandDecision` union. |
</phase_requirements>

## Summary

Phase 28 should create one dependency-free semantic center and one explicit codec package; later layers exchange frozen domain objects, never unvalidated dictionaries. The normative ontology has 17 root concepts, Engine authority stays outside this phase, Events remain immutable facts, and the Phase 27 tree is inert serialized evidence rather than an API design. [VERIFIED: `docs/concepts.md`, `docs/architecture.md`, `28-CONTEXT.md`, `27-VERIFICATION.md`]

Use Python 3.12+ frozen, slotted, keyword-only dataclasses; final wrapper classes for runtime- and type-distinct IDs; `StrEnum`/`Literal` discriminators; tuples and frozen ordered JSON containers for deep immutability; and `Protocol` only for static structural seams. Dataclasses do not enforce annotations or deep immutability, `NewType` returns the original value at runtime, and runtime-checkable protocols check presence rather than signatures. [CITED: https://docs.python.org/3.12/library/dataclasses.html] [CITED: https://docs.python.org/3.12/library/typing.html]

The highest-risk work is the codec. Python `json.dumps()` does not reproduce the frozen ECMAScript spellings for `-0`, exponent thresholds, and `1e20`; use `json.loads()` only as a strict tokenizer/parser and implement one small v1 byte renderer driven exhaustively by the frozen number, string, field-order, absence/null, and Event fixtures. [VERIFIED: `docs/events.md`, `tests/fixtures/compatibility/v1/manifest.json`; local Python/fixture comparison]

**Primary recommendation:** land foundations → semantic concepts/unions → Event codecs → ports/fakes → full corpus/type/package gate; do not build reducers, stores, Engine rules, transports, Bundle I/O, or CLI behavior here. [VERIFIED: `ROADMAP.md` Phase 28 boundary]

## Frozen Contract

| Surface | Phase-28 contract |
|---|---|
| Ontology | `Run`, `Command`, `Event`, `Message`, `ModelCall`, `Action`, `Wait`, `Delegation`, `Check`, `Checkpoint`, `Annotation`, `Artifact`, `Capability`, `Authority`, `Lease`, `Bundle`, `View`; secondary names need approved suffixes. [VERIFIED: `docs/concepts.md`] |
| IDs | Distinct Run/Event/Command/ModelCall/Wait/Delegation/Check/Checkpoint/Message/Annotation/Authority/Action/Artifact/Lease/Capability/PolicyRule/Correlation IDs; wire values are strings. [VERIFIED: `packages/core/src/ids.ts`] |
| Event grammar | 37 v1 Event names, exact required envelope keys `id,runID,position,type,version,timestamp,actor,payload`, optional `causationID,correlationID,commandID`, and 65 frozen payload variants. [VERIFIED: `docs/events.md`, frozen manifest] |
| Decisions | `accepted`, `rejected`, `deferred`, `superseded` are a tagged union with traces and result/Wait/replacement linkage; only accepted Commands may yield target lifecycle Events. [VERIFIED: `docs/architecture.md`, frozen manifest] |
| Waits | Exactly `approval`, `interaction`, `timer`, `join`, `reconciliation`; aggregate and concrete payload variants stay distinct. [VERIFIED: `docs/concepts.md`, frozen manifest] |
| Presence | Missing, explicit JSON `null`, and present values are distinct; required fields are present/non-null; unknown envelope/payload fields fail except allowlisted nested extension containers. [VERIFIED: `docs/events.md`, frozen manifest] |
| Bytes | UTF-8 without BOM, compact one-value JSONL, exactly one LF, no Unicode normalization, construction-order raw Event objects, recursively sorted canonical-hash objects, finite numbers, JS-safe integer boundaries, and millisecond UTC `Z` timestamps. [VERIFIED: `docs/events.md`, frozen manifest] |
| Corpus use | Phase 28 must cover 65 Event entries, 4 Command-decision entries, 18 encoding cases, 14 number cases, 6 field-policy cases, and relevant rejection entries without editing or executing the oracle. [VERIFIED: frozen manifest, `27-VERIFICATION.md`] |

The corpus also contains Views, providers, SQLite, Artifacts, and Bundles; Phase 28 may decode shared leaf values but must not implement those later subsystems. [VERIFIED: frozen manifest, `28-CONTEXT.md`]

## Recommended Python Layout

```text
pyproject.toml
src/openrund/
├── __init__.py                 # minimal; Phase 36 owns final top-level API
├── py.typed
├── errors.py                   # public semantic exception hierarchy
├── contracts/
│   ├── ids.py                  # final validated ID wrappers
│   ├── json.py                 # immutable ordered JsonValue containers + MISSING
│   ├── time.py                 # canonical timestamp value
│   ├── content.py              # Content/effect/evidence/Artifact references
│   ├── runs.py                 # Run, Wait, Delegation, Authority, Lease
│   ├── commands.py             # operations, Command, decisions, traces
│   ├── events.py               # generic envelope, 37 names, 65 payload variants
│   ├── capabilities.py         # inert definitions/results only
│   └── portable.py             # minimal Bundle/View value envelopes, no I/O/reducers
├── codec/
│   ├── __init__.py             # decode_event/encode_event/canonical_json_bytes
│   ├── _json.py                # strict parse and exact scalar/container renderer
│   ├── _aliases.py             # snake_case ↔ exact v1 keys
│   └── _events.py              # (type,version,variant) dispatch registry
├── paths.py                    # PathInput, LocalPath, PortablePath normalization
├── ports/
│   ├── events.py               # EventStore contracts only
│   ├── artifacts.py            # ArtifactStore contract only
│   ├── leases.py               # LeaseStore contract only
│   ├── providers.py            # ModelProvider proposal seam
│   ├── capabilities.py         # CapabilityTransport result seam
│   └── runtime.py              # Clock, generic IdFactory, Reporter
└── _testing/                   # private until future DX-07
    ├── memory.py               # deterministic stores
    └── fakes.py                # clocks, IDs, provider/transport/reporter
tests/contracts/  tests/codec/  tests/ports/  tests/package/
```

Dependency rule: `contracts` imports only stdlib; `codec`, `paths`, and `ports` import `contracts`; `_testing` imports contracts/ports; nothing in this phase imports predecessor modules or later `engine`, `views`, concrete storage, capabilities, providers, bundles, assembly, or CLI. [VERIFIED: `docs/architecture.md`; greenfield constraint in `28-CONTEXT.md`]

## Data Model

- Define `@final @dataclass(frozen=True, slots=True, kw_only=True)` values and validate primitive/runtime invariants in `__post_init__`; freeze nested sequences to tuples and JSON objects to an ordered tuple-of-pairs wrapper so callers cannot mutate a frozen object's internals. [CITED: https://docs.python.org/3.12/library/dataclasses.html]
- Make each `RunId`, `EventId`, etc. a distinct final frozen wrapper with `value: str`; reject non-strings/empty values at construction. Do not use aliases or `NewType` alone, because runtime validation must retain the ID kind. [CITED: https://docs.python.org/3.12/library/typing.html]
- Represent optional presence as `T | None | MissingType` with one immutable `MISSING` singleton: default means omitted, `None` means explicit JSON null, and the codec never uses truthiness to decide presence. [VERIFIED: frozen V1-PRESENCE decision]
- Use `StrEnum` for closed vocabularies and a distinct frozen class per tagged branch. `CommandDecision`, Wait payloads, authority grants, delegation creation, message/annotation backward-read forms, and Action outcomes must be precise unions, not one all-optional model. [VERIFIED: `docs/events.md`, frozen manifest]
- Define `Event[TType, TPayload]` where `TType` is a `Literal[...]`; validate the type/version/payload association through a registry. Public factories return precise aliases such as `RunCreatedEvent`, while raw `dict[str, object]` exists only inside `codec`. [VERIFIED: DX-01/DX-02]
- `Bundle` and `View` in this phase are immutable generic value envelopes only; Phase 29 supplies reducers and Phase 35 supplies Bundle layout, verification, import/export, and resumability. [VERIFIED: `28-CONTEXT.md`, `ROADMAP.md`]

## Codec Boundary

- Public boundary: `decode_event(data: bytes | str) -> RuntimeEvent`, `encode_event(event) -> bytes`, `decode_json_value`, `encode_json_value`, and `canonical_json_bytes`; semantic modules expose no `to_dict`, `asdict`, model dump, or alias-aware constructor. [VERIFIED: DX-01 and exact corpus contract]
- Decode strict UTF-8/JSONL; reject BOM, CRLF/surrounding bytes, duplicate object keys via `object_pairs_hook`, non-finite tokens via `parse_constant`, booleans in integer fields, unsafe integers, unknown keys, and unsupported versions before constructing domain values. [CITED: https://docs.python.org/3.12/library/json.html] [VERIFIED: frozen rejection fixtures]
- Render strings/numbers/arrays/objects through one internal v1 writer: preserve explicit ordered fields for raw frames, omit only `MISSING`, retain `None`, use exact aliases, add one LF, and separately recurse/sort for semantic hashes. Never route canonical bytes through `json.dumps`, `dataclasses.asdict`, Pydantic, or a generic serializer. [VERIFIED: frozen encoding/number fixtures]
- Use a deterministic non-locale comparator for canonical object keys and add non-ASCII key vectors before relying on extension-object hashes; the frozen corpus proves current keys but does not close every Unicode-key ordering case. Recommended rule: UTF-16 code-unit order, documented beside the codec. [ASSUMED]
- Backward-read-only message/annotation forms decode to named legacy variants; encoders accept only canonical writer variants. Rejected defects and declaration-only cases never become ordinary writer output. [VERIFIED: frozen decision ledger/manifest]

## Protocols and Deterministic In-Memory Implementations

- Define small async `Protocol`s for Event/Artifact/Lease stores, providers, transports, and reporters; define synchronous `Clock.now() -> Timestamp` and generic `IdFactory[T].new_id() -> T`. Aggregate per-kind `IdFactory` instances in a frozen dependency object rather than one optional-method mega-interface. [CITED: https://docs.python.org/3.12/library/typing.html]
- Do not decorate ports with `runtime_checkable`; prove conformance using typed assignments/explicit inheritance under mypy and behavior contract tests. Boundary registration later must validate metadata and schemas separately. [CITED: https://docs.python.org/3.12/library/typing.html]
- Private `openrund._testing` implementations must preserve insertion order, copy/freeze inputs, expose deterministic call logs, accept seeded clock/ID sequences, and return domain values. They must not decide legality or fabricate authoritative lifecycle Events. [VERIFIED: DX-03, `docs/architecture.md`]
- In-memory stores implement only the port contract needed by later tests; expected-position durability, SQLite behavior, Artifact crash recovery, and Lease custody remain Phase 30. [VERIFIED: `28-CONTEXT.md`, `ROADMAP.md`]

## PathLike Rules

- Public filesystem parameters accept `PathInput = str | os.PathLike[str]`; call `os.fspath()` once, reject bytes-returning PathLike values and NUL, and retain a `pathlib.Path` as the normalized local value. Do not silently call `expanduser()` or serialize `str(Path)` onto portable wire fields. [CITED: https://docs.python.org/3.12/library/os.html#os.fspath]
- Keep `LocalPath` and `PortablePath` distinct. `PortablePath` is a relative `PurePosixPath` with no root, drive, empty/`.`/`..` components, backslash ambiguity, or NUL; only it may encode into Bundle/Artifact wire paths. [VERIFIED: DX-05 and frozen path rejections]
- `Path.resolve()`/symlink containment is an I/O security check performed by later storage/capability adapters against an explicit root, not by the pure contract constructor. Lexical normalization alone never proves sandbox containment. [CITED: https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.resolve]

## Exception and Decision Semantics

```text
OpenRundError
├── ContractError
│   ├── ValidationError(code, pointer, safe_detail)
│   ├── DecodeError / EncodeError
│   └── UnsupportedVersionError
├── ConcurrencyError
│   └── ExpectedPositionConflict(run_id, expected, actual)
├── StorageError
│   └── StorageIntegrityError
├── TransportError
│   ├── ProviderTransportError
│   └── CapabilityTransportError
└── CapabilityProtocolError
```

Exceptions represent invalid caller/boundary data or failed infrastructure contracts and carry stable safe codes without raw provider bodies, credentials, bytes, or absolute private paths. `accepted/rejected/deferred/superseded` remain frozen `CommandDecision` result branches; do not define or raise `LegalityError`. [VERIFIED: DX-08, `docs/architecture.md`]

## Implementation Order

1. Scaffold `pyproject.toml`, `src/openrund`, `py.typed`, strict pytest/mypy/Ruff config, and a read-only manifest/fixture loader. [VERIFIED: DX-02]
2. Implement `errors.py`, ID wrappers, immutable JSON values/MISSING, timestamps, enums, and local/portable paths with focused unit tests. [VERIFIED: SEM-01, DX-05, DX-08]
3. Implement concept dataclasses and tagged unions, then all 65 Event payload variants and type/version association tests. [VERIFIED: frozen manifest]
4. Implement strict decode first, exact encode second, then canonical hashing; gate each slice against manifest pointers and bytes before adding the next. [VERIFIED: frozen manifest]
5. Add ports and deterministic private fakes, with mypy conformance assertions and contract tests. [VERIFIED: DX-03]
6. Run the complete corpus/type/lint/package gate and document the semantic imports; leave top-level API curation to Phase 36. [VERIFIED: DX-02, deferred DX-10]

## Pitfalls

- Generic serialization collapses aliases, omission/null, enums, timestamps, ordering, and float spellings; only the explicit codec may cross the wire. [VERIFIED: frozen corpus]
- Frozen dataclasses containing mutable lists/dicts are still mutable; recursively freeze at construction and never expose mutable internals. [CITED: https://docs.python.org/3.12/library/dataclasses.html]
- `bool` is an `int` subclass in Python; check booleans before integer validation so `version=True` and `position=True` fail. [VERIFIED: `docs/events.md`]
- Broad optional payload models accept ambiguous Wait/Authority/Delegation/legacy shapes; dispatch by discriminator and exact key set. [VERIFIED: frozen variants]
- `asdict()` deep-copies and loses the controlled wire boundary; do not use it for encoding, equality commitments, or hashes. [CITED: https://docs.python.org/3.12/library/dataclasses.html#dataclasses.asdict]
- Path stringification and lexical `..` removal can hide platform or symlink semantics; keep local and portable paths separate. [CITED: https://docs.python.org/3.12/library/pathlib.html]
- Do not turn store conflicts, transport failures, or malformed worker/provider data into rejected Commands; do not turn rejected/deferred/superseded legality into exceptions. [VERIFIED: DX-08]
- Do not expose predecessor-named aliases, executable-oracle calls, raw append, reducer logic, concrete storage, or CLI helpers in this phase. [VERIFIED: `28-CONTEXT.md`, `27-VERIFICATION.md`]

## Validation Architecture

Root Python infrastructure is a Wave 0 gap: the repository has only the separate documents-worker Python package; the observed default `python3` is 3.9.6, below the required 3.12 floor, while `uv` is available and can provision/select the phase interpreter. [VERIFIED: repository/environment audit]

| Property | Value |
|---|---|
| Framework | pytest; strict config and markers |
| Config | root `pyproject.toml` (Wave 0), `testpaths = ["tests"]`, Python `>=3.12` |
| Quick | `uv run --python 3.12 pytest tests/contracts tests/ports -q` |
| Codec | `uv run --python 3.12 pytest tests/codec -q` |
| Full | `uv run --python 3.12 pytest -q` |
| Types | `uv run --python 3.12 mypy --strict src/openrund tests` |
| Lint | `uv run ruff check src tests && uv run ruff format --check src tests` |
| Package | `uv build && uv run --python 3.12 pytest tests/package -q` |

| Requirement | Automated evidence |
|---|---|
| SEM-01 | `tests/contracts/test_concepts.py`, `test_ids.py`, `test_event_catalog.py`: every concept/ID and all 37 names/65 variants. |
| DX-01 | `tests/codec/test_v1_events.py`: decode each Event fixture, assert semantic object, encode exact original bytes; assert no dict-valued Engine-facing API. |
| DX-02 | mutation/deep-freeze tests, union typing fixtures, strict mypy, and `tests/package/test_py_typed.py` against the built wheel. |
| DX-03 | `tests/ports/test_protocol_conformance.py` plus deterministic clock/ID/store/provider/transport/reporter behavior tests. |
| DX-05 | parametrized `str`, `Path`, custom PathLike, bytes/NUL/absolute/drive/parent-segment cases in `tests/contracts/test_paths.py`. |
| DX-08 | exception-tree/code/pointer/redaction tests and assertions that all four decisions return normally. |

Corpus test collection must derive cases from `manifest.json`, verify each fixture hash before use, select only Phase-28 categories, and never rewrite fixtures. Exact gates cover all encoding/number/field cases, all Events and Commands, required/absent/null pointers, malformed JSON/JSONL, versions 0/2, unsafe/non-finite numbers, and unknown fields. [VERIFIED: `27-VERIFICATION.md`, frozen manifest]

Sampling: run focused contract/codec tests per task, full pytest plus strict mypy/Ruff per wave, and build/`py.typed` plus the full Phase-28 corpus before verification. No manual-only acceptance criterion is needed. [VERIFIED: all Phase 28 success criteria are machine-testable]

### Security Domain

ASVS V5 input validation applies: bound input bytes/nesting/collection sizes, reject duplicate/unknown fields, type confusion, unsafe numbers, malformed UTF-8, and invalid paths before domain construction. V2/V3 do not apply; V4 Authority is modeled but enforcement is deferred; V6 uses stdlib SHA-256 and must not hand-roll cryptography. [VERIFIED: phase scope, `docs/events.md`, `docs/architecture.md`]

## Assumptions Log

| # | Claim | Risk if wrong |
|---|---|---|
| A1 | Canonical hash keys should use UTF-16 code-unit order for deterministic non-ASCII behavior. | Non-ASCII extension-object hashes could differ from the predecessor; add vectors and resolve before release. |

## Sources

- `28-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `ROADMAP.md`, `AGENTS.md` — scope and project constraints. [VERIFIED: codebase]
- `docs/concepts.md`, `docs/events.md`, `docs/architecture.md` — normative ontology, wire grammar, and authority boundary. [VERIFIED: codebase]
- `27-VERIFICATION.md`, `tests/fixtures/compatibility/v1/manifest.json`, and referenced evidence — frozen compatibility inventory. [VERIFIED: codebase]
- `packages/core/src/ids.ts`, `events.ts`, `model.ts`, `run.ts`, `storage.ts`; `packages/runtime/src/contracts.ts` — smallest predecessor contract inventory, used as evidence rather than API shape. [VERIFIED: codebase]
- Python 3.12 `dataclasses`, `typing`, `json`, `os`, and `pathlib` documentation — Python runtime behavior. [CITED: https://docs.python.org/3.12/]

## Metadata

**Confidence breakdown:** frozen contract HIGH; module/data model MEDIUM-HIGH; codec HIGH for corpus-covered cases and MEDIUM for non-ASCII key ordering; validation HIGH.
**Valid until:** 2026-09-04; revalidate package/tool versions when Wave 0 creates the lock.
