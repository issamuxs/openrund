# Phase 27: Frozen Compatibility Oracle - Pattern Map

**Mapped:** 2026-08-04
**Files analyzed:** 37 planned path entries/groups, plus the generated corpus tree
**Analogs found:** 35 / 37 (the versioned corpus layout and decision-ledger schema are new)

## Boundary to Preserve

Phase 27 creates a temporary, predecessor-only executable oracle and a permanent, inert compatibility corpus. The scripts and TypeScript drift tests exist only through the Phase 37 cutover. They must not be exported from any `@openrund/*` package, called by the future Python runtime, or become a service/API. The generator may import existing package surfaces and internal factories, but it must not add a second authority path around `RuntimeEngine`.

This phase has no graphical UI work. Do not add components, routes, browser views, dashboards, HTTP endpoints, or interactive fixture editors. The only human interface is explicit CLI/package scripts plus readable verifier failures.

## File Classification

### Required New Files

| New File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/compatibility/oracle-inventory.ts` | config / utility | transform | `packages/core/src/events.ts`; `tests/core/event-normalization.test.ts` | exact contract inventory, but current test has a duplicate-key flaw |
| `scripts/compatibility/generate-v1-oracle.ts` | utility / temporary developer tool | batch + file-I/O | `tests/runtime/orun-bundle.test.ts#createBundleFixture` | role + flow match |
| `scripts/compatibility/verify-v1-oracle.ts` | utility / temporary developer tool | batch + file-I/O | `packages/runtime/src/orun.ts#verifyBundle`; `scripts/check-hygiene.mjs` | role + flow match |
| `tests/fixtures/compatibility/v1/**` including `manifest.json` | config / immutable fixture data | file-I/O | no repository-wide golden corpus exists | no analog; use `27-RESEARCH.md` manifest schema |
| `docs/archive/compatibility-v1-decisions.md` | config / contract ledger | transform | no existing ambiguity ledger | no analog; use `27-RESEARCH.md` required fields |
| `tests/compatibility/oracle-manifest.test.ts` | test | file-I/O + transform | `tests/core/event-normalization.test.ts`; `scripts/check-hygiene.mjs` | role match |
| `tests/compatibility/oracle-wire.test.ts` | test | transform | `tests/core/event-normalization.test.ts`; `tests/runtime/orun-bundle.test.ts` | role + flow match |
| `tests/compatibility/oracle-views.test.ts` | test | event-driven replay + transform | `tests/runtime/replay.test.ts`; `packages/views/src/index.ts` | exact |
| `tests/compatibility/oracle-providers.test.ts` | test | request-response + transform | `tests/providers/provider-normalization.test.ts`; provider adapter tests | exact |
| `tests/compatibility/oracle-sqlite.test.ts` | test | CRUD + batch + file-I/O | `tests/storage/sqlite-store.test.ts`; `packages/storage-sqlite/src/sqlite-store.ts` | exact |
| `tests/compatibility/oracle-artifacts.test.ts` | test | CRUD + file-I/O | `tests/storage/sqlite-artifact.test.ts`; `.orun` profile test | exact |
| `tests/compatibility/oracle-bundles.test.ts` | test | batch + file-I/O | `tests/runtime/orun-bundle.test.ts` | exact |
| `tests/compatibility/oracle-rejections.test.ts` | test | file-I/O + request-response | `tests/runtime/orun-bundle.test.ts` rejection cases | exact |
| `tests/compatibility/oracle-regeneration.test.ts` | test | batch + file-I/O | `tests/runtime/orun-bundle.test.ts#createBundleFixture`; `scripts/check-hygiene.mjs` | role match |
| `tests/compatibility/oracle-retirement.test.ts` | test | file-I/O + architecture guard | `tests/public-api/exports.test.ts`; `tests/core/contracts.test.ts`; `scripts/check-package-content.mjs` | exact |

### Expected Modifications After Ledger Adjudication

These are not blanket refactors. Modify a source only when a resolved ledger item or deterministic predecessor scenario requires it.

| Modified File / Symbol | Role | Data Flow | Closest Pattern | Required Direction |
|---|---|---|---|---|
| `package.json` scripts | config | request-response CLI | existing `hygiene`, `package:check`, and test scripts | add explicit generate/verify commands; normal tests remain read-only |
| `packages/core/src/events.ts` payload interfaces | model | event-driven | `CORE_EVENT_TYPES`, `EventEnvelope`, `RuntimeEventPayloadMap` in the same file | align declarations to adjudicated emitted v1 variants; keep Event names/version stable |
| `packages/core/src/provider-normalization.ts#parseProviderToolArguments` | utility | transform | same file + provider tests | replace malformed/non-object `{}` acceptance with the resolved fail-closed contract; retain old observation only as backward/rejection evidence |
| `packages/storage-sqlite/src/migrations.ts#runMigrations` | migration | CRUD | existing additive `CREATE TABLE/INDEX IF NOT EXISTS` schema | add nullable `command_id` only after ledger closure; preserve legacy rows |
| `packages/storage-sqlite/src/sqlite-store.ts#append/#rowToEvent` | service | CRUD | current explicit column binding and null-to-undefined mapping | persist/read optional `commandID`; raw SQL NULL and decoded absence are separate evidence |
| `packages/storage-sqlite/src/sqlite-artifact-store.ts` ID seam | service | CRUD + file-I/O | `RuntimeEngineDependencies.now`; `BootstrapDependencies.ids` | inject deterministic Artifact IDs for oracle scenarios; do not bless current UPSERT as canonical immutability |
| `packages/runtime/src/runtime-engine.ts#RuntimeEngineDependencies` and Event creation | service / authority boundary | event-driven | existing `now?: () => string` and bootstrap `ids.nextEventID()` | extend dependency injection internally; keep Engine authoritative and defaults unchanged |
| `packages/runtime/src/orun.ts#BundleExportInput/#exportBundle` | service | batch + file-I/O | existing options object | inject/fix `exportedAt` through input/dependency; preserve exact JSONL and hash algorithms |
| `packages/runtime/src/action-lifecycle.ts` and `action-reconciliation-control.ts` | service / event factory | event-driven | `createBootstrapEvents(..., dependencies)` | accept an internal Event-ID source instead of hard-wired `randomUUID()` when needed |
| `packages/runtime/src/artifact-materialization.ts` | service | event-driven + file-I/O | `MaterializeActionResultOptions` options object | thread deterministic Artifact/Event IDs through existing options, not post-generation replacement |
| `packages/runtime/src/check-control.ts`, `checkpoint-control.ts` | service / event factory | event-driven | bootstrap dependency-object pattern | inject fixed time/IDs where scenarios cannot already supply them |
| `packages/runtime/src/delegation-control.ts` | service / event factory | event-driven | bootstrap dependency-object pattern | one scoped internal ID provider must cover parent, child, join, terminal, and annotation links |
| `packages/runtime/src/interaction-control.ts`, `timer-control.ts`, `wait-approval-control.ts`, `wait-control.ts` | service / event factory | event-driven | bootstrap dependency-object pattern | inject Event IDs without changing public Event shapes |
| `docs/events.md` | config / normative contract | transform | `packages/core/src/events.ts` + emitted factories | record required `actor`, optional `commandID`, payload variants, null/absence rules |
| `docs/providers.md` | config / normative contract | request-response | provider normalization/adapters | document fail-closed malformed arguments and safe/redacted failures |
| `docs/storage.md` | config / normative contract | CRUD | SQLite migration/store | document nullable persisted `commandID`, legacy-absent read, and Artifact immutability decision |
| `docs/bundles.md` | config / normative contract | batch + file-I/O | `packages/runtime/src/orun.ts` | keep Bundle v1 commitments/limitations stable; version future incompatible writers |

Do not add oracle exports to `packages/core/src/index.ts`, `packages/runtime/src/index.ts`, `packages/*/package.json`, or any public barrel. That absence is part of `oracle-retirement.test.ts`.

## Pattern Assignments

### `scripts/compatibility/oracle-inventory.ts` (config/utility, transform)

**Analogs:** `packages/core/src/events.ts` and `tests/core/event-normalization.test.ts`

Use the core tuple as one independent inventory input:

```typescript
// packages/core/src/events.ts:31-71
export const CORE_EVENT_TYPES = [
  "run.created",
  "run.started",
  // ... 35 more literals ...
  "lease.expired"
] as const;

export type CoreEventType = (typeof CORE_EVENT_TYPES)[number];
```

The existing test demonstrates the import/assertion convention:

```typescript
// tests/core/event-normalization.test.ts:1-10, 215-220
import { describe, expect, it } from "vitest";
import { CORE_EVENT_TYPES, normalizeEvent, type RuntimeEvent } from "@openrund/core";

for (const type of CORE_EVENT_TYPES) {
  expect(() => normalizeEvent(eventOf(type)), type).not.toThrow();
}
```

**Do not copy its `Record<EventType, unknown>` payload map.** Lines 21-205 repeat keys such as `message.added`, `wait.created`, `wait.resolved`, `delegation.created`, and `authority.granted`; JavaScript keeps only the last value. Use an array of entries with a stable unique `type:version:variant` key, run duplicate detection before creating a `Map`, and compare independently-derived expected/actual sets in both directions.

Keep separate inventory constants for four Command decisions (`packages/core/src/model.ts:76`), nine View fields (`packages/views/src/index.ts:25-35`), three Bundle profiles (`packages/runtime/src/orun.ts:27`), provider outcomes, SQLite schema fields, Artifact states, and rejection codes. Do not derive expected inventory from the same scenario array the generator loops over.

### `scripts/compatibility/generate-v1-oracle.ts` (utility, batch/file-I-O)

**Analog:** `tests/runtime/orun-bundle.test.ts#createBundleFixture`

Copy the fixed-input, fresh-root assembly shape:

```typescript
// tests/runtime/orun-bundle.test.ts:243-260, 280-305
const root = mkdtempSync(join(tmpdir(), "openrund-orun-bundle-"));
const eventStore = new SqliteRunEventStore({
  databasePath: join(root, "runtime.sqlite")
});
const runID = asRunID("ses_orun_bundle");

await eventStore.append({
  runID,
  expectedPosition: 0,
  events: [{
    id: "evt_orun_created" as never,
    runID,
    type: "run.created",
    version: 1,
    timestamp: "2026-05-10T12:00:00.000Z",
    actor: "system",
    payload: { rootID: runID, title: "Portable Run", objective: "prove .orun export" }
  }]
});
```

Generation rules:

- Require an explicit empty output/staging root. Refuse a corpus root containing files; never clean or overwrite the committed corpus during tests.
- Supply fixed timestamps, IDs, provider response objects, Artifact bytes, relative logical paths, and Bundle export time before invoking predecessor behavior.
- Generate through real factories/Engine/store/reducers/adapters/exporter. `sourceKind` must say whether evidence is Engine-emitted, factory-emitted, adapter-normalized, store-serialized, or declaration-only.
- Write evidence first and `manifest.json` last. Enumerate every staged file, then have the independent verifier prove exact bijection.
- Close stores in `finally`. Avoid ambient credentials and user-home runtime data. The documents worker pattern passes an explicit minimal `env` (`tests/capabilities/documents-stdio.test.ts:20-25`), and its environment isolation test proves inherited secrets are absent (`:40-80`).
- Never repair nondeterministic bytes by regex/JSON rewriting afterward; this can invalidate IDs, causation, content hashes, and Bundle commitments.

Use existing options/dependency objects as the seam style. Bootstrap already models the desired pattern:

```typescript
// packages/runtime/src/bootstrap.ts:12-17, 25-33
export interface BootstrapDependencies {
  clock?: { now(): string };
  ids?: RuntimeIdGenerator;
}

export function createBootstrapEvents(input, dependencies: BootstrapDependencies = {}) {
  const timestamp = input.timestamp ?? dependencies.clock?.now() ?? new Date().toISOString();
  const runCreatedID = dependencies.ids?.nextEventID() ?? createFallbackEventID(1);
  // ...
}
```

Do not copy hard-wired entropy such as `action-lifecycle.ts:205-206` (`evt_${randomUUID()}`), `sqlite-artifact-store.ts:32-34`, or `orun.ts:281-286`. Extend an existing dependency/options object with internal defaults so production behavior is unchanged.

### `scripts/compatibility/verify-v1-oracle.ts` (utility, batch/file-I-O)

**Analogs:** `packages/runtime/src/orun.ts#verifyBundle`, `scripts/check-hygiene.mjs`

Follow the scripts' collect-all-failures style, then exit nonzero:

```javascript
// scripts/check-hygiene.mjs:27-49
const violations = [];
// collect violations
if (violations.length > 0) {
  console.error("OpenRund hygiene check failed.");
  for (const violation of violations) console.error(`- ${violation.rule}: ${violation.path}`);
  process.exit(1);
}
```

Follow Bundle verification's structured failure style:

```typescript
// packages/runtime/src/orun.ts:68-85
export interface BundleRuntimeError {
  name: "BundleRuntimeError";
  code: string;
  message: string;
  path?: string;
  details?: Record<string, unknown>;
  cause?: unknown;
}
```

Verifier order should be: validate manifest/version and safe normalized relative paths; reject symlinks; enumerate tree; prove expected/actual bijection; verify byte length and SHA-256; parse; verify required/absent/null pointers; resolve IDs/positions/causation/correlation/command/wait links; verify semantic commitments; verify retirement gates. It is strictly read-only.

### `tests/compatibility/oracle-manifest.test.ts` (test, file-I-O/transform)

**Analogs:** `tests/core/event-normalization.test.ts`, `scripts/check-hygiene.mjs`

Use direct Vitest imports and package aliases (`vitest.config.ts:4-38`). Assert exact sorted key sets, not only `length === 37`. Assert:

- no duplicate manifest key;
- no unknown or missing expected key;
- each non-manifest file is referenced exactly once;
- each manifest path is normalized, relative, contained, non-NUL, and non-symlink;
- every referenced ledger decision exists and is `resolved`;
- `sourceKind: declaration_only` is explicit and ledger-backed;
- every file hash and byte count matches.

The corpus directory itself is new; there is no existing golden-fixture tree to imitate. Use the manifest schema in `27-RESEARCH.md`, not Vitest snapshots or `-u`.

### `tests/compatibility/oracle-wire.test.ts` (test, transform)

**Analogs:** Event normalization test and `.orun` byte tests

The Event envelope that must be checked is concrete:

```typescript
// packages/core/src/events.ts:75-90
export interface EventEnvelope<TType extends string = string, TPayload = Record<string, unknown>> {
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

Compare raw `Buffer`/UTF-8 bytes and SHA-256 first, then parse and assert meaning. Preserve construction-order JSONL bytes separately from canonical-hash bytes. Existing `.orun` code makes the distinction:

```typescript
// packages/runtime/src/orun.ts:919-933, 957-959
for (const event of events) {
  head = hashCanonicalJson({ previous: head, event: canonicalEventForHash(event) });
}

function renderEventsJsonl(events: RuntimeEvent[]): string {
  return `${events.map((event) => JSON.stringify(event)).join("\n")}\n`;
}
```

Presence assertions must distinguish absent, explicit JSON `null`, and a value. Positions start at 1, are contiguous, and each link resolves. Do not use truthiness for pointer presence.

### `tests/compatibility/oracle-views.test.ts` (test, event replay/transform)

**Analogs:** `tests/runtime/replay.test.ts`, `packages/views/src/index.ts`

Copy fixed clock + real store + Engine replay setup:

```typescript
// tests/runtime/replay.test.ts:11-19, 36-40
const root = mkdtempSync(join(tmpdir(), "openrund-replay-"));
const eventStore = new SqliteRunEventStore({ databasePath: join(root, "runtime.sqlite") });
const runtime = new RuntimeEngine({
  eventStore,
  now: () => "2026-05-09T18:00:00.000Z"
});
const replay = await runtime.replay(runID);
expect(replay.eventCount).toBe(6);
```

Use the one production aggregator, not parallel reducers:

```typescript
// packages/views/src/index.ts:41-57
export function rebuildViews(events: RuntimeEvent[]): RunViewBundle {
  return {
    runStatus: reduceRunStatusView(events),
    timeline: reduceTimelineView(events),
    actionStatus: reduceActionStatusView(events),
    actionReconciliation: reduceActionReconciliation(events),
    actionReceipts: reduceActionReceipts(events),
    artifactIndex: reduceArtifactIndex(events),
    checkpoints: reduceCheckpointView(events),
    delegation: reduceDelegationView(events),
    waits: reduceWaitQueueView(events)
  };
}
```

Assert all nine keys explicitly and compare the full frozen bundle plus focused branch fixtures. Keep these as JSON/data projections; do not create graphical views.

### `tests/compatibility/oracle-providers.test.ts` (test, request-response/transform)

**Analogs:** `tests/providers/provider-normalization.test.ts`, OpenAI/Anthropic/local adapter tests

Copy fixed response-object normalization and injected `fetchImpl`; never enable an environment-gated live branch. The common operation pattern is:

```typescript
// packages/core/src/provider-normalization.ts:41-52
const [capabilityID, actionName] = splitProviderQualifiedName(action.name);
return {
  kind: "create_action",
  actionID: (action.actionID ?? action.fallbackActionID) as ActionID,
  capabilityID: capabilityID as CapabilityID,
  actionName,
  input: action.input ?? {}
};
```

Preserve dotted action suffixes (`tests/providers/provider-normalization.test.ts:10-15`), supplied/fallback model and action IDs, single/batch calls, text/empty fallback, and safe redacted failures. The adapter tests show the boundary guard:

```typescript
// tests/providers/openai.test.ts:33-39
const source = readFileSync("packages/provider-openai/src/openai-adapter.ts", "utf8");
expect(source).not.toContain("RuntimeEngine");
expect(source).not.toContain("RunEventStore");
expect(source).not.toContain("command.recorded");
```

Landmine: current `parseProviderToolArguments` returns `{}` for invalid JSON and arrays (`provider-normalization.ts:28-38`; current test lines 18-24). Record this as a predecessor defect, resolve it in the ledger, and freeze the chosen safe-error outcome rather than empty legal input.

### `tests/compatibility/oracle-sqlite.test.ts` (test, CRUD/batch/file-I-O)

**Analogs:** `tests/storage/sqlite-store.test.ts`, migrations and store implementation

Use a fresh real database and fixed Events:

```typescript
// tests/storage/sqlite-store.test.ts:8-29
const root = mkdtempSync(join(tmpdir(), "openrund-store-"));
const store = new SqliteRunEventStore({
  databasePath: join(root, "runtime.sqlite"),
  busyTimeoutMs: 2_500
});
// makeEvent uses fixed ID, runID, version, timestamp, actor, and payload.
```

Capture `sqlite_master`, `PRAGMA table_info`, `PRAGMA index_list/index_info`, and ordered raw `SELECT *` results before adapter conversion. Then separately capture `store.read()` decoded Events and conflict errors.

The adapter conventions to preserve are explicit transaction/rollback and SQL-null mapping:

```typescript
// packages/storage-sqlite/src/sqlite-store.ts:43-50, 80-82, 100-110
this.database.exec("BEGIN IMMEDIATE;");
try {
  if (currentPosition !== input.expectedPosition) {
    throw new ExpectedPositionConflictError(input.expectedPosition, currentPosition);
  }
  // causation/correlation optional fields bind as SQL NULL
  this.database.exec("COMMIT;");
} catch (error) {
  this.database.exec("ROLLBACK;");
  throw error;
}
```

Current schema lines `migrations.ts:25-37` omit `command_id`, and `sqlite-store.ts:53-83` does not bind it. Do not freeze that silent loss. After an additive nullable migration, capture both legacy SQL NULL/decoded absence and new non-null/decoded `commandID`.

### `tests/compatibility/oracle-artifacts.test.ts` (test, CRUD/file-I-O)

**Analogs:** `tests/storage/sqlite-artifact.test.ts` and Bundle profile assertions

Copy explicit metadata/blob fixtures:

```typescript
// tests/storage/sqlite-artifact.test.ts:20-39
const first = await store.createArtifact({
  kind: "text/markdown",
  createdAt: "2026-05-09T18:00:00.000Z",
  metadata: { title: "First artifact" },
  blob: { bytes: new TextEncoder().encode("# One"), contentType: "text/markdown" }
});
const second = await store.createArtifact({
  kind: "text/plain",
  createdAt: "2026-05-09T18:00:01.000Z",
  metadata: { title: "Second artifact" }
});
```

Cover metadata-only, blob-backed, unavailable, missing bytes, included, audit-omitted, redacted, and adjudicated external-reference states. Cross-link metadata row, bytes/hash, Artifact View entry, and Bundle manifest entry.

Landmine: `sqlite-artifact-store.ts:70-78` uses `ON CONFLICT ... DO UPDATE`. Normative Artifacts are immutable. Do not turn overwrite into golden writer behavior; the ledger should classify it noncanonical while the corpus freezes identity/nullability/availability states.

### `tests/compatibility/oracle-bundles.test.ts` and `oracle-rejections.test.ts`

**Analog:** `tests/runtime/orun-bundle.test.ts`

Reuse the profile fixture helper shape and exact manifest assertions. The existing test covers layout and commitments (`:10-44`), read-after-export verification (`:49-57`), incompatible schemas (`:59-77`), unsafe Unix/Windows paths (`:79-102`), tampering/malformed JSONL/rejected Artifact metadata (`:104-144`), recomputed file hash with a bad Event chain (`:146-168`), and audit/redacted omission metadata (`:170-199`).

Copy structured rejection expectations:

```typescript
// tests/runtime/orun-bundle.test.ts:79-87
mutateManifest(bundlePath, (manifest) => {
  manifest.exports.runtimeAuditJsonPath = "../outside.json";
});
await expect(verifyBundle({ bundlePath })).rejects.toMatchObject({
  code: "invalid_manifest_path",
  path: "../outside.json"
});
```

Generate and freeze all three `BundleExportProfile` values. Verify every file's raw bytes, Bundle file table, Event chain head, canonical Bundle commitment, replayed Views, and Artifact availability. Mutations occur only in temporary copies. Add explicit symlink, NUL, unknown version, wrong count/position, null-vs-absent, orphan file, and outside-write cases beyond the current Bundle suite.

### `tests/compatibility/oracle-regeneration.test.ts` (test, batch/file-I-O)

**Analog:** fresh temporary setup used throughout runtime/storage tests

Call the generator twice into two different `mkdtempSync` roots, enumerate sorted relative paths, and compare bytes for every file. Then compare one generated tree to the committed corpus without writing the committed path. A readable diff should report added, removed, and changed files plus first meaningful byte/JSON-pointer mismatch.

Do not use snapshots, update flags, ambient absolute paths, Git dirty-state text, random temp names inside output, or current time. The test itself owns cleanup; generator/verification code must never traverse `~/.openrund`.

### `tests/compatibility/oracle-retirement.test.ts` (test, file-I-O/architecture guard)

**Analogs:** `tests/public-api/exports.test.ts`, `tests/core/contracts.test.ts`, `scripts/check-package-content.mjs`

Use source/package inspection for negative architectural guarantees:

```typescript
// tests/core/contracts.test.ts:16-27
const runtimeContracts = readFileSync(
  new URL("../../packages/runtime/src/contracts.ts", import.meta.url),
  "utf8"
);
const runtimePackage = readFileSync(
  new URL("../../packages/runtime/package.json", import.meta.url),
  "utf8"
);
expect(runtimeContracts).not.toMatch(/sqlite|anthropic|openai|llama/i);
expect(runtimePackage).not.toMatch(/sqlite|anthropic|openai|llama/i);
```

Assert no compatibility/oracle export from package barrels or export maps, no production import of `scripts/compatibility`, and no Python runtime invocation of Node/oracle scripts. Assert all `RET-01` through `RET-10` IDs exist in the manifest/ledger. This test protects temporary/internal-only status; it does not imply the oracle is a supported CLI product.

### `package.json` (config, request-response CLI)

Copy the existing short, explicit script style (`package.json:13-22`). Add separate commands for generating into an explicit staging path and verifying the committed corpus. Do not make `pnpm test` regenerate fixtures. Direct TypeScript scripts should follow the repository's existing Node 24 strip-types precedent (`demo:governed-coding-run` at line 15) unless planning adds a dedicated compilation target; no new dependency is required.

### Contract and Entropy-Seam Modifications

The source modifications should imitate existing dependency objects, optional inputs, branded IDs, and default fallbacks. For example, `RuntimeEngineDependencies` already accepts a clock (`runtime-engine.ts:103-112`), while `bootstrap()` explicitly supplies clock and Event ID dependencies (`:124-134`). Extend that shape rather than introducing oracle globals or environment variables.

Keep canonical hash behavior distinct from wire rendering:

```typescript
// packages/runtime/src/orun.ts:1217-1219
export function hashCanonicalJson(value: unknown): string {
  return hashBytes(Buffer.from(JSON.stringify(canonicalize(value))));
}
```

Do not export new internal dependency types unless production callers truly require them. Do not reimplement Engine legality in the generator. Do not make raw store append a public compatibility API.

## Shared Patterns

### Imports and Modules

- Tests import Node built-ins with `node:` specifiers, then Vitest, then `@openrund/*` package aliases.
- Package source uses `.js` suffixes for relative imports under `NodeNext` (`tsconfig.base.json:4-6`).
- Root tests are discovered by `tests/**/*.test.ts` and run in Node (`vitest.config.ts:36-39`).
- The root is ESM (`package.json:4`) and requires Node 24+ (`:8-10`).

### Deterministic Fixture Setup

- Use fixed branded IDs and millisecond-precision UTC `...000Z` timestamps.
- Create fresh roots with `mkdtempSync(join(tmpdir(), "openrund-...-"))`.
- Pass fixed clocks and ID sequences into factories before Events are created.
- Keep output path-independent and sort only inventories/tree traversal/canonical hashes where ordering is non-semantic. Preserve emitted JSON property order and stream order.

### Error Handling

- Library/service code throws structured errors with stable code, message, optional path/details/cause (Bundle pattern).
- SQLite writes use `BEGIN IMMEDIATE`, `COMMIT`, and rollback/rethrow.
- Tests use `rejects.toMatchObject({ code, path })` for stable rejection semantics rather than entire message matching.
- CLI verifier aggregates actionable failures and exits once with nonzero status.

### Authority and Isolation

- Provider adapters and compatibility tooling do not append Events or import Runtime Engine authority casually. Scenarios needing legal emissions go through `RuntimeEngine`; low-level stores are used only to capture persistence behavior and declared provenance.
- Provider evidence uses fixed mocks only. Never branch on provider credential environment variables.
- The transported documents scenario supplies a minimal explicit child environment and proves parent secrets are absent.

### Bytes, JSON, and Hashes

- JSONL uses one `JSON.stringify(event)` per line with a final LF.
- File integrity is SHA-256 over exact bytes.
- Event and Bundle semantic commitments use the existing recursively canonicalized JSON algorithm.
- Manifest pointers distinguish present value, present null, and absent.
- Reject non-finite numbers and `BigInt` at the oracle canonical boundary instead of inheriting lossy/coercive `JSON.stringify` behavior.

### Cleanup and Immutability

- Close SQLite stores after each scenario and in failure-safe cleanup.
- Generate only into fresh temporary/staging roots; normal tests never write expected files.
- Treat committed fixture bytes and Artifact identities as immutable. Promotion is a separate maintainer action after ledger and verification success.

## Landmines for Planning

1. `tests/core/event-normalization.test.ts` appears exhaustive but repeated object keys overwrite variants. Never copy this representation.
2. `EventEnvelope.commandID` exists (`events.ts:88`), but SQLite has no column/binding. Do not freeze silent loss; add a nullable migration and legacy-absent read rule first.
3. Event declarations and actual emissions conflict for `action.failed`, message/annotation/check/checkpoint/Artifact payloads, authority variants, and Wait variants. Close ledger entries before promotion; don't let the generator decide implicitly.
4. `superseded` is declared but lacks a normal live emission path. Mark it `declaration_only` only with a resolved decision; do not mislabel it Engine-emitted.
5. Multiple factories call `randomUUID()` directly and Bundle export calls `new Date()`. Inject entropy before execution, not by scrubbing output.
6. `parseProviderToolArguments` currently maps malformed/non-object input to `{}`. Freeze the adjudicated fail-closed result, not the defect as canonical writer behavior.
7. Artifact UPSERT conflicts with normative immutability. Do not encode overwrite as required Python behavior.
8. Bundle `requiredProviders` is currently empty and `external` Artifact availability is declared but not emitted. Keep exact predecessor v1 cross-read evidence and label limitations; don't mutate Bundle v1 silently.
9. Adapter-decoded SQLite Events hide raw SQL NULL and payload byte order. Capture raw and decoded evidence separately.
10. A passing count is not completeness. Require unique keys, exact set equality, and every filesystem entry referenced exactly once.
11. Never import private data from `~/.openrund`, inherit secrets, call live providers, or include absolute temporary paths.
12. The oracle is frozen after Phase 27 except for explicit corpus-version corrections. New feature development belongs in Python, and Phase 37 removes the executable predecessor after all retirement gates pass.

## No Analog Found

| File | Role | Data Flow | Reason / Planner Direction |
|---|---|---|---|
| `tests/fixtures/compatibility/v1/**` | immutable config/data | file-I/O | No repository-wide, versioned, language-neutral byte corpus exists. Implement the research manifest schema and exact tree-bijection rules; do not use snapshots. |
| `docs/archive/compatibility-v1-decisions.md` | contract ledger | transform | No existing ambiguity-ledger format exists. Include ID, evidence links, conflict, canonical resolution, backward-read rule, writer rule, affected fixture keys, and resolved status. |

## Metadata

**Analog search scope:** `packages/core/src`, `packages/runtime/src`, `packages/views/src`, `packages/storage-sqlite/src`, provider adapter packages, `scripts`, and existing core/runtime/view/storage/provider/capability/public-API tests.

**Primary analogs read:** `tests/core/event-normalization.test.ts`, `tests/runtime/orun-bundle.test.ts`, `tests/runtime/replay.test.ts`, `tests/storage/sqlite-store.test.ts`, `tests/storage/sqlite-artifact.test.ts`, provider normalization/adapter tests, `tests/capabilities/documents-stdio.test.ts`, `tests/public-api/exports.test.ts`, and their relevant source implementations.

**Pattern extraction date:** 2026-08-04
