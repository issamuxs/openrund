# Phase 28: Python Contract Kernel - Pattern Map

**Mapped:** 2026-08-05
**Files analyzed:** 41 proposed new files
**Existing evidence found:** 30 / 41 (5 Python role matches, 25 semantic-only matches)
**Scope:** Phase 28 only — typed semantic values, exact v1 codecs, paths, structural ports, deterministic fakes, and their tests

## Mapping Rules

- The repository has no existing Python runtime package. There is therefore no exact implementation analog for the kernel.
- The documents worker is the only Python style/packaging analog. Copy its small-module and direct-pytest organization, but not its `Any`-heavy dictionaries, mutable dataclass defaults, string-only paths, broad exception serialization, `line.strip()`, or `json.dumps()` wire behavior.
- TypeScript files below are semantic evidence only. Preserve the frozen names, discriminators, associations, and seam boundaries; do not mirror TypeScript interface shapes, camelCase names, optional-field breadth, branded-cast constructors, barrel exports, or predecessor public APIs.
- The Phase 27 manifest and evidence are inert golden inputs. Tests may read and hash them but production code must not import generator/verifier modules or invoke the predecessor.
- Do not add reducers, concrete storage, Engine legality, authority enforcement, provider adapters, capability implementations, Bundle I/O, assembly, CLI, or UI work.

## File Classification

| New File | Role | Data Flow | Closest Existing Evidence | Match Quality |
|---|---|---|---|---|
| `pyproject.toml` | config | batch/package | `python/openrund_documents_worker/pyproject.toml` | role-match |
| `src/openrund/__init__.py` | config | import/export | None; Phase 36 owns final top-level API | none |
| `src/openrund/py.typed` | config | package metadata | None | none |
| `src/openrund/errors.py` | utility | request-response | `python/openrund_documents_worker/openrund_documents_worker/jsonrpc.py` | role-match, stricter design required |
| `src/openrund/contracts/ids.py` | model | transform | `packages/core/src/ids.ts` | semantic-only |
| `src/openrund/contracts/json.py` | model/utility | transform | None; greenfield deep-immutable JSON/presence model | none |
| `src/openrund/contracts/time.py` | model/utility | transform | None; frozen corpus is the behavioral oracle | none |
| `src/openrund/contracts/content.py` | model | transform | `packages/core/src/events.ts` (`Content`, `Mutation`, `EffectEntry`) | semantic-only |
| `src/openrund/contracts/runs.py` | model | event-driven | `packages/core/src/run.ts` | semantic-only |
| `src/openrund/contracts/commands.py` | model | request-response | `packages/core/src/model.ts` (`CommandDecision`) | semantic-only |
| `src/openrund/contracts/events.py` | model | event-driven | `packages/core/src/events.ts` (`EventEnvelope`, `RuntimeEventPayloadMap`) | semantic-only |
| `src/openrund/contracts/capabilities.py` | model | request-response | `packages/core/src/events.ts` capability/action leaf values | semantic-only |
| `src/openrund/contracts/portable.py` | model | transform | Phase 27 Bundle/View fixtures, value envelopes only | semantic-only |
| `src/openrund/codec/__init__.py` | config | import/export | None; expose only the codec boundary | none |
| `src/openrund/codec/_json.py` | utility | transform | `tests/fixtures/compatibility/v1/manifest.json` wire cases | semantic-only |
| `src/openrund/codec/_aliases.py` | utility | transform | `packages/core/src/events.ts` exact camelCase wire fields | semantic-only |
| `src/openrund/codec/_events.py` | utility | event-driven/transform | `packages/core/src/events.ts` payload map | semantic-only |
| `src/openrund/paths.py` | utility/model | transform | `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py` | role-match, stronger PathLike boundary required |
| `src/openrund/ports/events.py` | provider/protocol | event-driven/CRUD | `packages/core/src/storage.ts` (`RunEventStore`) | semantic-only |
| `src/openrund/ports/artifacts.py` | provider/protocol | file-I/O/CRUD | `packages/core/src/storage.ts` (`ArtifactStore`) | semantic-only |
| `src/openrund/ports/leases.py` | provider/protocol | CRUD | `packages/core/src/storage.ts` (`ExecutionLeaseStore`) | semantic-only |
| `src/openrund/ports/providers.py` | provider/protocol | request-response | `packages/core/src/model.ts` (`ModelAdapter`) | semantic-only |
| `src/openrund/ports/capabilities.py` | provider/protocol | request-response | None at the correct Phase 28 abstraction | none |
| `src/openrund/ports/runtime.py` | provider/protocol | request-response | `packages/runtime/src/contracts.ts` (`RuntimeClock`, `RuntimeIdGenerator`) | semantic-only |
| `src/openrund/_testing/memory.py` | store/test utility | event-driven/CRUD | None; later concrete stores are out of scope | none |
| `src/openrund/_testing/fakes.py` | test utility/provider | request-response | None; deterministic Python fakes are greenfield | none |
| `tests/conftest.py` | test/config | file-I/O/batch | `tests/compatibility/oracle-wire.test.ts` fixture/hash assertions | semantic-only |
| `tests/package/test_py_typed.py` | test | file-I/O/batch | None | none |
| `tests/contracts/test_ids.py` | test | transform | `packages/core/src/ids.ts` inventory | semantic-only |
| `tests/contracts/test_values.py` | test | transform | None; deep immutability/presence are greenfield | none |
| `tests/contracts/test_errors.py` | test | request-response | `python/openrund_documents_worker/tests/test_markdown_ops.py` exception assertion | role-match |
| `tests/contracts/test_paths.py` | test | transform/file-I/O | `python/openrund_documents_worker/tests/test_markdown_ops.py` `tmp_path` style | role-match |
| `tests/contracts/test_concepts.py` | test | transform | `packages/core/src/run.ts`, `events.ts`, `model.ts` inventories | semantic-only |
| `tests/contracts/test_commands.py` | test | request-response | `packages/core/src/model.ts` decision branches | semantic-only |
| `tests/contracts/test_event_catalog.py` | test | event-driven | `packages/core/src/events.ts` catalog/map | semantic-only |
| `tests/codec/test_v1_decode.py` | test | transform | Phase 27 manifest/evidence | semantic-only |
| `tests/codec/test_rejections.py` | test | transform | Phase 27 rejection entries | semantic-only |
| `tests/codec/test_v1_encode.py` | test | transform | `tests/compatibility/oracle-wire.test.ts` exact-byte assertions | semantic-only |
| `tests/codec/test_v1_events.py` | test | event-driven/transform | Phase 27 Event entries | semantic-only |
| `tests/codec/test_canonical_json.py` | test | transform | Phase 27 semantic hash entries | semantic-only |
| `tests/ports/test_protocol_conformance.py` | test | request-response/CRUD | None; use strict mypy plus contract tests | none |

## Pattern Assignments

### Packaging: `pyproject.toml`, `src/openrund/__init__.py`, `src/openrund/py.typed`

**Role analog:** `python/openrund_documents_worker/pyproject.toml`

**Existing package/test configuration** (lines 1-17):

```toml
[project]
name = "openrund-documents-worker"
version = "0.0.0"
requires-python = ">=3.9"
dependencies = [
  "markdown-it-py>=3.0.0",
  "python-frontmatter>=1.1.0",
  "mdformat>=0.7.17"
]

[project.optional-dependencies]
test = [
  "pytest>=8.0.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Copy:** one root project table, an explicit Python floor, separated development/test dependencies, and `testpaths = ["tests"]`.

**Phase 28 differences:**

- Set `requires-python = ">=3.12"`; add an explicit build backend and src-layout package discovery.
- Keep runtime dependencies empty unless implementation proves stdlib insufficient. Configure strict mypy, Ruff check/format, pytest strict settings/markers, and package data for `py.typed`.
- `src/openrund/__init__.py` stays intentionally minimal. Export no broad compatibility surface and no predecessor aliases; Phase 36 curates final top-level API.
- The built wheel and sdist must contain `openrund/py.typed`; test the built artifact, not merely the source tree.

---

### Errors: `src/openrund/errors.py`

**Role analog:** `python/openrund_documents_worker/openrund_documents_worker/jsonrpc.py`

**Small semantic exception with structured attributes** (lines 10-15):

```python
class JsonRpcError(Exception):
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data
```

**Boundary validation and narrow handling** (lines 22-47):

```python
def handle(self, request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("id")
    try:
        if request.get("jsonrpc") != "2.0":
            raise JsonRpcError(-32600, "Invalid JSON-RPC version")
        method = request.get("method")
        if not isinstance(method, str):
            raise JsonRpcError(-32600, "Missing method")
        # ...
    except JsonRpcError as error:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": error.code, "message": error.message, "data": error.data},
        }
```

**Copy:** stable structured error attributes and validation at the untrusted boundary.

**Phase 28 differences:** define the researched `OpenRundError` tree with stable string codes, typed safe fields, and redacted `safe_detail`; avoid `Any`, arbitrary `data`, raw bytes/bodies/credentials/absolute paths, and `str(error)` as a protocol response. `ValidationError` carries code/pointer/safe detail. `DecodeError`, `EncodeError`, and `UnsupportedVersionError` remain contract failures. Infrastructure exceptions remain separate. Never define `LegalityError`: accepted/rejected/deferred/superseded are returned domain values.

---

### Kind-safe IDs: `src/openrund/contracts/ids.py`

**Semantic evidence:** `packages/core/src/ids.ts`

**Complete frozen ID-kind inventory** (lines 5-21):

```typescript
export type RunID = Brand<string, "RunID">;
export type EventID = Brand<string, "EventID">;
export type CommandID = Brand<string, "CommandID">;
export type ModelCallID = Brand<string, "ModelCallID">;
export type WaitID = Brand<string, "WaitID">;
export type DelegationID = Brand<string, "DelegationID">;
export type CheckID = Brand<string, "CheckID">;
export type CheckpointID = Brand<string, "CheckpointID">;
export type MessageID = Brand<string, "MessageID">;
export type AnnotationID = Brand<string, "AnnotationID">;
export type AuthorityID = Brand<string, "AuthorityID">;
export type ActionID = Brand<string, "ActionID">;
export type ArtifactID = Brand<string, "ArtifactID">;
export type LeaseID = Brand<string, "LeaseID">;
export type CapabilityID = Brand<string, "CapabilityID">;
export type PolicyRuleID = Brand<string, "PolicyRuleID">;
export type CorrelationID = Brand<string, "CorrelationID">;
```

**Do not copy the cast factory** (lines 23-25):

```typescript
export function asRunID(value: string): RunID {
  return value as RunID;
}
```

Implement one private validated base/helper and distinct `@final`, frozen, slotted wrapper classes with `value: str`. Reject non-strings and empty values at runtime. The wire codec unwraps/reconstructs IDs; semantic constructors never accept the wrong ID kind. Do not use Python aliases or `NewType` alone, and use Python spellings such as `RunId`, not mechanical `RunID` mirroring.

---

### Immutable leaves: `contracts/json.py`, `time.py`, `content.py`, `capabilities.py`, `portable.py`

**Semantic evidence:** `packages/core/src/events.ts` lines 102-108 and 236-258

```typescript
export interface Content {
  preview?: string;
  data?: Record<string, unknown>;
  artifactRefs?: ArtifactReference[];
  artifactIDs?: ArtifactID[];
  metadata?: Record<string, unknown>;
}

export interface EffectEntry {
  kind: string;
  summary?: string;
  artifactIDs?: ArtifactID[];
  metadata?: Record<string, unknown>;
}
```

Use these fields and the corpus as semantic inventory, then deepen the Python model:

- Every public value is `@final @dataclass(frozen=True, slots=True, kw_only=True)` and validates in `__post_init__`.
- Recursively freeze sequences as tuples and JSON objects as an immutable ordered tuple-of-pairs wrapper. Never leave a `dict` or `list` inside a frozen object.
- Define an immutable `MissingType` singleton. Annotate presence-sensitive fields as `T | None | MissingType`; omit only `MISSING`, retain explicit `None`, and never use truthiness for presence.
- Validate millisecond UTC `Z` timestamps in the timestamp value rather than passing unvalidated strings between layers.
- `Capability`, `Artifact`, `Bundle`, and `View` are inert typed values only here. `portable.py` must not perform Bundle I/O or View reduction.

There is no existing Python analog for deep immutability, presence, or canonical timestamps; use `28-RESEARCH.md` and the frozen cases as the implementation contract.

---

### Runs, decisions, and tagged branches: `contracts/runs.py`, `contracts/commands.py`

**Semantic evidence:** `packages/core/src/model.ts`

**Decision discriminator and exhaustive union** (lines 76 and 97-139):

```typescript
export type CommandDecisionKind = "accepted" | "rejected" | "deferred" | "superseded";

export interface AcceptedCommandDecision {
  kind: "accepted";
  trace: CommandDecisionTraceEntry[];
  resultEventIDs?: EventID[];
  resultEventTypes?: string[];
  resultEventDrafts?: unknown[];
}

export interface RejectedCommandDecision {
  kind: "rejected";
  reason: string;
  trace: CommandDecisionTraceEntry[];
}

export interface DeferredCommandDecision {
  kind: "deferred";
  reason: string;
  trace: CommandDecisionTraceEntry[];
  waitIDs?: WaitID[];
  waitDrafts?: unknown[];
}

export interface SupersededCommandDecision {
  kind: "superseded";
  reason: string;
  trace: CommandDecisionTraceEntry[];
  supersededByCommandID: CommandID;
}

export type CommandDecision =
  | AcceptedCommandDecision
  | RejectedCommandDecision
  | DeferredCommandDecision
  | SupersededCommandDecision;
```

Copy the discriminator and branch-specific required data, not the arrays/`unknown` types or field spellings. Create a frozen class per branch and a precise Python union. Apply the same pattern to Wait kinds, authority grants, delegation creation, Action outcomes, and legacy-read payloads. Do not create one all-optional `Wait` or decision model. `packages/core/src/run.ts` lines 51-69 prove the five Wait kinds, but its broad optional interface is specifically not the Python pattern.

---

### Event catalog: `contracts/events.py`, `codec/_events.py`

**Semantic evidence:** `packages/core/src/events.ts`

**Closed event vocabulary and envelope association** (lines 32-91):

```typescript
export const CORE_EVENT_TYPES = [
  "run.created",
  "run.started",
  // ... 37 v1 names total ...
  "lease.released",
  "lease.expired"
] as const;

export interface EventEnvelope<TType extends string, TPayload> {
  id: EventID;
  runID: RunID;
  position: number;
  type: TType;
  version: number;
  timestamp: string;
  actor: EventActor;
  causationID?: EventID;
  correlationID?: CorrelationID;
  commandID?: CommandID;
  payload: TPayload;
}
```

**Type-to-payload catalog** (lines 643-689):

```typescript
export interface RuntimeEventPayloadMap {
  "run.created": RunCreatedPayload;
  "run.started": RunStartedPayload;
  // ... one association per event name ...
  "lease.expired": LeaseExpiredPayload;
}

export type RuntimeEvent<TType extends CoreEventType = CoreEventType> =
  EventEnvelope<TType, RuntimeEventPayloadMap[TType]>;
```

Implement a generic frozen `Event[TType, TPayload]`, precise aliases/factories, and one internal registry keyed by `(type, version, variant)`. The registry is the single association used by decoder, encoder, and catalog tests. It must cover all 37 event names and all 65 frozen payload variants. Unknown names/versions/key sets reject before construction.

**Variant pattern** (lines 358-408): aggregate and concrete Wait payloads are separate types. Mirror that precision with separate frozen dataclasses; do not port `WaitCreatedPayloadFields` as a broad optional base.

Legacy message/annotation forms at lines 174-211 are named read-only variants. Decoders accept frozen legacy forms; encoders accept only canonical writer variants.

---

### Exact codec: `codec/__init__.py`, `codec/_json.py`, `codec/_aliases.py`, `codec/_events.py`

**Golden evidence:** `tests/fixtures/compatibility/v1/manifest.json`

**Manifest entry contract** (lines 1-39):

```json
{
  "schemaVersion": 1,
  "corpusVersion": "v1",
  "wire": {
    "encoding": [{
      "key": "wire:escape-backspace",
      "relativePath": "evidence/wire-escape-backspace.jsonl",
      "byteLength": 5,
      "sha256": "...",
      "semanticSha256": "...",
      "decodedMeaning": {"value": "\b", "json": "\"\\b\""},
      "requiredPointers": ["", "/value", "/json"],
      "absentPointers": [],
      "nullPointers": []
    }]
  }
}
```

**Existing exact-byte assertions:** `tests/compatibility/oracle-wire.test.ts` lines 93-119

```typescript
expect(text(root, byKey, "wire:jsonl-final-newline").endsWith("\n")).toBe(true);
expect(text(root, byKey, "number:negative-zero")).toBe("0\n");
expect(text(root, byKey, "number:exponent-threshold-1e-7")).toBe("1e-7\n");
expect(text(root, byKey, "number:exponent-threshold-1e+21")).toBe("1e+21\n");
```

Public `codec/__init__.py` should expose only `decode_event`, `encode_event`, JSON-value decode/encode, and `canonical_json_bytes`. Domain modules expose no `to_dict`, `asdict`, model-dump, or alias-aware constructors.

`_json.py` may use `json.loads()` as a strict tokenizer/parser with duplicate-key and non-finite hooks, but must use a dedicated v1 renderer for bytes. Bound input size/depth/collection length; reject BOM, CRLF/surrounding bytes, malformed UTF-8/JSONL, duplicate/unknown keys, booleans in integer slots, unsafe integers, and unsupported versions. Preserve insertion-order raw Event frames; recursively sort canonical-hash objects with the documented comparator; add one LF only to JSONL outputs.

`_aliases.py` is an explicit, exhaustive registry from snake_case semantic fields to exact v1 keys such as `runID`, `causationID`, and `commandID`. It must not perform generic camelization.

Do not copy the worker codec behavior in `jsonrpc.py` lines 59-74: `line.strip()` destroys framing distinctions and `json.dumps()` cannot reproduce the frozen number spellings.

---

### Paths: `src/openrund/paths.py`

**Role analog:** `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py`

**Existing pathlib-at-use-site pattern** (lines 31-38):

```python
def write_document(params: dict[str, Any]) -> dict[str, Any]:
    path = Path(params["path"])
    before = path.read_text(encoding="utf-8") if path.exists() else ""
    # ...
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
```

Copy only the use of `pathlib.Path` as the normalized local value. Phase 28 requires `PathInput = str | os.PathLike[str]`, one `os.fspath()` call, explicit rejection of bytes-returning PathLike and NUL, and no `expanduser()` or filesystem access during normalization.

Keep `LocalPath` and `PortablePath` distinct. `PortablePath` wraps a relative `PurePosixPath` and rejects roots, drives, empty/`.`/`..` components, backslashes, and NUL. It alone may cross portable Artifact/Bundle wire fields. Do not use lexical normalization as a sandbox-containment claim; symlink/`resolve()` enforcement belongs to later adapters.

---

### Structural ports: `ports/events.py`, `artifacts.py`, `leases.py`, `providers.py`, `capabilities.py`, `runtime.py`

**Semantic evidence:** `packages/core/src/storage.ts`

**Small async event-store seam** (lines 15-31):

```typescript
export interface AppendEventsInput {
  runID: RunID;
  expectedPosition: number;
  events: NewRuntimeEvent[];
}

export interface RunEventStore {
  append(input: AppendEventsInput): Promise<AppendEventsResult>;
  read(runID: RunID, fromPosition?: number): Promise<RunEventSlice>;
  hasEvent(eventID: EventID): Promise<boolean>;
}
```

**Narrow artifact seam** (lines 79-84):

```typescript
export interface ArtifactStore {
  put(record: ArtifactEntry, blob?: ArtifactBlob): Promise<void>;
  get(artifactID: ArtifactID): Promise<ArtifactEntry | null>;
  getBlob(artifactID: ArtifactID): Promise<ArtifactBlob | null>;
  markUnavailable(artifactID: ArtifactID, unavailableAt: string): Promise<void>;
}
```

Copy the small capability-focused seams and domain-valued inputs/results. Define async Python `Protocol`s for I/O-facing seams. Do not implement durability, transactions, SQLite, custody, conflict resolution, or authoritative Event fabrication in Phase 28.

**Clock/ID semantic evidence:** `packages/runtime/src/contracts.ts` lines 32-53

```typescript
export interface RuntimeClock {
  now(): string;
}

export interface RuntimeIdGenerator {
  nextEventID(): EventID;
  nextRunID?(): RunID;
  // ... many optional methods ...
}
```

Keep `Clock.now() -> Timestamp` synchronous. Improve the broad predecessor ID interface into `IdFactory[T].new_id() -> T`, with one required per-kind factory in a frozen dependencies value. Do not decorate protocols `runtime_checkable`; verify typed assignments/explicit implementation with strict mypy and behavior contract tests. `CapabilityTransport` returns typed proposal/result values and never grants authority or emits authoritative lifecycle Events.

---

### Deterministic test implementations: `_testing/memory.py`, `_testing/fakes.py`

There is no close implementation analog. Follow the port signatures above and these constraints:

- `memory.py` preserves insertion order, copies/freezes every accepted input, and returns domain objects. It implements only the minimal Event/Artifact/Lease behavior required by later tests.
- `fakes.py` accepts seeded timestamp/ID/provider/transport sequences, exposes immutable or copied deterministic call logs, and fails clearly when a seed sequence is exhausted.
- Fakes propose data and record calls; they do not decide legality, assign authority, or fabricate authoritative Events.
- Keep all helpers private under `openrund._testing`; DX-07/public testing helpers belong later.

---

### Test organization: all `tests/contracts`, `tests/codec`, `tests/ports`, and `tests/package` files

**Python role analog:** `python/openrund_documents_worker/tests/test_markdown_ops.py`

**Direct pytest setup and exception assertion** (lines 1-5 and 40-47):

```python
from pathlib import Path

import pytest

from openrund_documents_worker import markdown_ops

def test_stale_document_hash_rejects_edit(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Intro\nHello\n", encoding="utf-8")

    with pytest.raises(markdown_ops.DocumentConflict):
        markdown_ops.write_document(
            {"path": str(doc), "content": "# Intro\nBye\n", "expectedHash": "stale"}
        )
```

Copy direct imports, focused behavior names, built-in `tmp_path`, and `pytest.raises`. Add explicit return annotations and strict typed fixtures for Phase 28.

`tests/conftest.py` should load the manifest read-only, resolve evidence paths beneath the fixed corpus root, reject symlinks/escape, verify byte length and SHA-256 before parsing, and select only Phase 28 categories. The pattern to preserve is the existing hash-before-meaning check in `tests/compatibility/oracle-wire.test.ts` lines 31-42:

```typescript
for (const entry of generated.entries) {
  const bytes = readFileSync(join(root, entry.relativePath));
  expect(bytes.byteLength, entry.key).toBe(entry.byteLength);
  expect(createHash("sha256").update(bytes).digest("hex"), entry.key).toBe(entry.sha256);
  // only then inspect provenance/meaning
}
```

The Python loader must read committed fixtures rather than call `generateEventAndCommandEvidence` or any verifier/generator script.

Use parametrized tests derived from manifest entries:

- `test_ids.py`, `test_values.py`, `test_errors.py`, `test_paths.py`: invalid runtime types, deep mutation attempts, omission/null distinction, timestamp/path boundaries, safe error details.
- `test_concepts.py`, `test_commands.py`, `test_event_catalog.py`: all canonical concepts/ID kinds, four decision branches, five Wait kinds, 37 names, and 65 type/version/payload variants.
- `test_v1_decode.py`, `test_rejections.py`: strict boundaries and every scoped rejection fixture.
- `test_v1_encode.py`, `test_v1_events.py`: semantic object to exact original bytes and decode→encode identity for all Phase 28 Event cases.
- `test_canonical_json.py`: exact preimage/hash cases plus a documented non-ASCII key-order vector; never update snapshots or corpus.
- `test_protocol_conformance.py`: strict-mypy assignments plus shared behavioral contract tests for deterministic fakes.
- `test_py_typed.py`: inspect wheel contents and import/type-discovery behavior from an isolated built-artifact environment.

## Shared Patterns

### Imports and Dependency Direction

The worker consistently begins library modules with `from __future__ import annotations` (`jsonrpc.py` and `markdown_ops.py`, line 1), then stdlib imports, then third-party imports. Apply that convention.

Enforce this dependency graph:

```text
contracts + errors       stdlib only
        ↓
codec / paths / ports    depend on contracts
        ↓
_testing                 depends on contracts + ports
```

No Phase 28 module imports TypeScript/predecessor code, `engine`, `views`, concrete storage, provider adapters, capabilities, bundles, assembly, or CLI modules. Add a source/import hygiene test similar in intent to `tests/core/contracts.test.ts` lines 16-27, which asserts contracts do not mention SQLite/provider SDKs.

### Naming and Wire Aliases

- Python objects and constructor parameters use `snake_case`.
- Exact canonical aliases exist only in `codec/_aliases.py`.
- Keep concept names canonical and secondary names suffix-qualified; do not create broad convenience aliases.
- Do not re-export every contract from the root package.

### Validation

- Validate primitive and cross-field invariants before a domain object exists.
- Check `bool` before `int`; enforce finite numbers and JS-safe integer bounds where the v1 wire requires them.
- Dispatch tagged branches by discriminator and exact key set; reject unknown/missing fields except documented nested extension containers.
- Bound codec input bytes, nesting depth, and collection sizes.

### Error and Decision Separation

- Invalid caller/wire data and failed infrastructure contracts raise typed semantic exceptions.
- Legality outcomes are `AcceptedCommandDecision | RejectedCommandDecision | DeferredCommandDecision | SupersededCommandDecision` values.
- Never translate transport/storage failure into a rejected Command, and never raise an exception merely because a Command is rejected/deferred/superseded.

### Exact Corpus Use

- Read `tests/fixtures/compatibility/v1/manifest.json` and referenced evidence without mutation.
- Verify path containment, file kind, byte length, and SHA-256 before interpreting content.
- Cover all Phase 28 Event, Command-decision, encoding, number, presence/field-policy, and relevant rejection entries.
- Exclude View reduction, SQLite/Artifact custody, providers, Bundle I/O, Engine behavior, and CLI categories even though the manifest contains them.

## No Analog Found

These files need greenfield Python implementation guided by research/stdlib/frozen evidence rather than copied repository code:

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `src/openrund/__init__.py` | config | import/export | Final public surface is explicitly deferred; keep minimal. |
| `src/openrund/py.typed` | config | package metadata | No existing PEP 561 package marker. |
| `src/openrund/contracts/json.py` | model/utility | transform | No deep-immutable ordered JSON/presence model exists. |
| `src/openrund/contracts/time.py` | model/utility | transform | Existing code uses raw timestamp strings. |
| `src/openrund/codec/__init__.py` | config | import/export | Exact Python codec boundary is new. |
| `src/openrund/ports/capabilities.py` | protocol | request-response | Existing capability code is a concrete TypeScript subsystem, not the desired proposal seam. |
| `src/openrund/_testing/memory.py` | test store | CRUD/event-driven | Existing stores are concrete later-phase implementations. |
| `src/openrund/_testing/fakes.py` | test provider | request-response | No deterministic typed Python fakes exist. |
| `tests/package/test_py_typed.py` | test | file-I/O/batch | No existing built-wheel typing-marker test. |
| `tests/contracts/test_values.py` | test | transform | Deep immutability/presence behavior is new. |
| `tests/ports/test_protocol_conformance.py` | test | request-response/CRUD | Structural protocol + strict-mypy conformance is new. |

## Planner Guardrails

1. Build foundations first: package config, errors, IDs, immutable JSON/presence, timestamps, and paths.
2. Add concept dataclasses and precise unions before the event registry; no raw dictionaries beyond codec internals and manifest test loading.
3. Decode strictly before encoding; then add canonical JSON hashing. Every codec task names the exact fixture categories it turns green.
4. Add ports and private deterministic fakes only after domain values are stable.
5. Finish with the full frozen-corpus, strict mypy, Ruff, wheel/sdist, `py.typed`, and import-hygiene gates.
6. Do not add UI-SPEC, UI, CLI, top-level API curation, or mechanical predecessor compatibility shims.

## Metadata

**Analog search scope:** `python/openrund_documents_worker`, `packages/core/src`, `packages/runtime/src/contracts.ts`, `tests/compatibility`, `tests/core`, and `tests/fixtures/compatibility/v1/manifest.json`

**Python analogs read:**

- `python/openrund_documents_worker/pyproject.toml`
- `python/openrund_documents_worker/openrund_documents_worker/jsonrpc.py`
- `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py`
- `python/openrund_documents_worker/tests/test_jsonrpc.py`
- `python/openrund_documents_worker/tests/test_markdown_ops.py`

**Semantic evidence read:**

- `packages/core/src/ids.ts`
- `packages/core/src/run.ts`
- `packages/core/src/model.ts`
- `packages/core/src/events.ts`
- `packages/core/src/storage.ts`
- `packages/runtime/src/contracts.ts`
- `tests/compatibility/oracle-wire.test.ts`
- `tests/core/contracts.test.ts`
- targeted manifest lines 1-39 after field-location search

**Pattern extraction date:** 2026-08-05
