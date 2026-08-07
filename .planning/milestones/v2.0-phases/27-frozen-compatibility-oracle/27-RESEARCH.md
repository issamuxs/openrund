# Phase 27: Frozen Compatibility Oracle - Research

**Researched:** 2026-08-04
**Domain:** Deterministic compatibility corpus generation for canonical Events, Commands, Views, provider normalization, SQLite, Artifacts, and `.orun` Bundles
**Confidence:** HIGH for repository behavior and phase architecture; MEDIUM for the few contract choices that Phase 27 must adjudicate

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

No locked implementation decisions were recorded because discuss phase was skipped.

### The Agent's Discretion

All implementation choices are at the agent's discretion because discuss phase was skipped per user setting. Use the ROADMAP phase goal, success criteria, requirements, normative documentation, and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)

None — discuss phase skipped.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEM-02 | Python users can decode, encode, round-trip, hash, and reject versioned canonical wire data deterministically, preserving Event names, envelope and payload keys, enum strings, missing-versus-null behavior, IDs, timestamps, causation/correlation links, and `.orun` commitments proven by frozen golden fixtures. | The recommended corpus, coverage manifest, decision ledger, byte/meaning verifier, raw SQLite evidence, provider matrix, and three Bundle profiles give later Python phases a complete executable contract. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`] |
</phase_requirements>

## Summary

Phase 27 should produce a versioned, deterministic, predecessor-generated corpus and a verifier that proves the corpus is complete. It should not create a permanent TypeScript API, a compatibility service, or a dual-runtime product. The temporary executable oracle may be used to generate and verify inert evidence; later Python phases consume the evidence without calling TypeScript. [VERIFIED: `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/research/SUMMARY.md`]

The current repository has strong behavioral raw material but not a complete oracle. It defines 37 `CORE_EVENT_TYPES`, four Command decision kinds, nine returned View surfaces, three provider adapters, three `.orun` export profiles, three SQLite tables, and several Artifact availability combinations. Existing tests cover many individual behaviors, but fixtures are dispersed, assertions are mostly semantic rather than byte-exact, entropy is not fully injectable, and one current event-normalization fixture map repeats object keys so later variants overwrite earlier variants. [VERIFIED: `packages/core/src/events.ts`, `packages/core/src/model.ts`, `packages/views/src/index.ts`, `packages/runtime/src/orun.ts`, `packages/storage-sqlite/src/migrations.ts`, `tests/core/event-normalization.test.ts`]

The phase must adjudicate declarations against actual emission and persistence before freezing bytes. Known conflicts include the undocumented required Event `actor`, optional Event `commandID`, SQLite dropping `commandID`, emitted payloads that differ from their TypeScript declarations, policy grants overloaded onto `authority.granted`, permissive malformed provider arguments, timestamp/omission rules, and Bundle hash inputs. The decision log is a prerequisite to corpus promotion, not documentation to add afterward. [VERIFIED: `docs/events.md`, `packages/core/src/events.ts`, `packages/storage-sqlite/src/sqlite-store.ts`, `packages/runtime/src/bootstrap.ts`, `packages/runtime/src/action-lifecycle.ts`, `packages/runtime/src/check-control.ts`, `packages/runtime/src/checkpoint-control.ts`, `packages/core/src/provider-normalization.ts`, `packages/runtime/src/orun.ts`]

**Primary recommendation:** Build one deterministic generator and one read-only verifier around the existing predecessor packages; gate corpus promotion on a closed ambiguity ledger and a manifest that proves every required surface has both byte evidence and decoded-meaning evidence. [VERIFIED: Phase 27 success criteria and repository inventory]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Oracle generation | Developer tooling / temporary predecessor | Filesystem | The generator executes existing packages but writes only versioned inert fixtures; it is not a runtime surface. [VERIFIED: phase boundary] |
| Canonical Event and Command evidence | Core contracts | Runtime Engine | Core declares the grammar; runtime scenarios prove actual decisions and emissions. [VERIFIED: `packages/core/src/events.ts`, `packages/runtime/src/runtime-engine.ts`] |
| View evidence | Views | Core Event streams | `rebuildViews(events)` returns all derived surfaces from ordered Events. [VERIFIED: `packages/views/src/index.ts`] |
| Provider normalization evidence | Provider adapters | Core normalization helpers | Adapters translate provider response shapes into provider-neutral `ModelCall` proposals. [VERIFIED: `packages/provider-*/src/*adapter.ts`] |
| SQLite row evidence | Storage adapter | Core Event/Artifact/Lease contracts | Raw rows and schema belong to storage; decoded Events are checked separately. [VERIFIED: `packages/storage-sqlite/src/*`] |
| Artifact evidence | Artifact store | Bundle exporter / Views | Storage proves metadata/blob/nullability; Views and Bundles prove availability projections. [VERIFIED: `packages/storage-sqlite/src/sqlite-artifact-store.ts`, `packages/views/src/artifact-index.ts`, `packages/runtime/src/orun.ts`] |
| `.orun` evidence | Bundle service | Events, Views, Artifacts | Export owns exact directory/file bytes and commitments while consuming the other canonical surfaces. [VERIFIED: `packages/runtime/src/orun.ts`] |
| Retirement | Phase 37 release gate | Python compatibility tests | Only Python golden, installed-package, and bidirectional Bundle gates may remove the executable oracle. [VERIFIED: `REL-03`, Phase 37 success criteria] |

## Project Constraints (from AGENTS.md)

- Follow the normative runtime documents in `docs/`; runtime contracts outrank implementation convenience. [VERIFIED: `AGENTS.md`]
- Keep Event payloads compact and treat Artifacts as immutable references. [VERIFIED: `AGENTS.md`]
- Preserve the Engine as the only authority boundary. The generator may exercise low-level stores for fixture construction, but must not turn raw append into a public runtime API. [VERIFIED: `AGENTS.md`, `docs/architecture.md`]
- Keep the MVP minimal while proving durability, legality, replayability, waits, authority, and terminal state end to end. [VERIFIED: `AGENTS.md`]
- Rich document behavior stays outside the core runtime; the transported Python documents worker matters here only insofar as it proves generic CapabilityResult, Artifact, effect, and JSON-RPC evidence. [VERIFIED: `AGENTS.md`, `tests/capabilities/documents-stdio.test.ts`]
- This research is already part of the Phase 27 GSD planning flow, satisfying the requirement to start file-changing work through a GSD command. [VERIFIED: phase-research invocation]

## Scope and Coverage Matrix

The manifest must enumerate expected inventory independently from generated inventory and fail on missing, duplicate, unknown, or unreferenced entries. A count alone is insufficient. [VERIFIED: current duplicate-key coverage weakness in `tests/core/event-normalization.test.ts`]

| Surface | Required inventory | Concrete predecessor source | Minimum corpus evidence |
|---------|--------------------|-----------------------------|-------------------------|
| Event grammar | All 37 `CORE_EVENT_TYPES`, every supported version (currently version 1), plus every materially different payload variant sharing a type/version | `packages/core/src/events.ts`; runtime event factories and `runtime-engine.ts` | Exact envelope JSON bytes, decoded object, normalized fact, required/present/null/absent key assertions, source provenance, and at least one ordered stream position. [VERIFIED: codebase] |
| Command decisions | `accepted`, `rejected`, `deferred`, `superseded`; model-origin and runtime-origin `command.recorded` shapes | `packages/core/src/model.ts`, `packages/runtime/src/legality-evaluator.ts`, `packages/runtime/src/runtime-engine.ts` | Exact `command.recorded` bytes, trace entries, reason/link fields, target Event presence/absence, Wait linkage, replacement linkage, and content hash. `superseded` currently lacks a live builder/emission path and must be explicitly adjudicated. [VERIFIED: codebase search] |
| Views | `runStatus`, `timeline`, `actionStatus`, `actionReconciliation`, `actionReceipts`, `artifactIndex`, `checkpoints`, `delegation`, `waits` | `packages/views/src/index.ts` and reducer files | One full `RunViewBundle` fixture plus focused scenarios that reach every status/queue/reconciliation/join/checkpoint/Artifact branch. [VERIFIED: codebase] |
| Provider normalization | OpenAI, Anthropic, local OpenAI-compatible; single tool, multi-tool batch, text, empty text fallback, supplied/fallback IDs, dotted action names, valid/malformed/non-object arguments, redacted HTTP failure | `packages/core/src/provider-normalization.ts`, `packages/provider-*/src/*adapter.ts`, `tests/providers/*` | Exact normalized `ModelCall` JSON or exact safe error record for each outcome; no live calls or credentials. [VERIFIED: codebase] |
| SQLite | `run_events`, `execution_leases`, `artifacts`; table/index definitions; every column with representative non-null and null values | `packages/storage-sqlite/src/migrations.ts`, store implementations | `sqlite_master`, `PRAGMA table_info`, `PRAGMA index_list/index_info`, raw ordered `SELECT *` rows, adapter-decoded values, conflict result, and the generated SQLite database only if byte portability is deliberately not claimed. [VERIFIED: codebase; Node docs] |
| Artifact states | metadata-only, blob-backed, unavailable, missing bytes at Bundle export, included, omitted-by-audit, redacted, and any declared external-reference state | `packages/core/src/storage.ts`, `sqlite-artifact-store.ts`, `artifact-index.ts`, `orun.ts` | Metadata row, blob bytes/hash, `ArtifactIndexEntry`, Bundle manifest entry, explicit state label, and decision-ledger reference for states the exporter cannot currently produce. [VERIFIED: codebase] |
| `.orun` profiles | `complete`, `audit`, `redacted` | `packages/runtime/src/orun.ts`, `tests/runtime/orun-bundle.test.ts` | Entire directory tree, exact bytes for every text/binary file, per-file SHA-256, Event-chain head, Bundle commitment, manifest null/omission assertions, replayed Views, and Artifact availability metadata. [VERIFIED: codebase] |
| Negative wire behavior | Unknown Event/schema versions, malformed JSON/JSONL, missing/unknown critical fields, bad paths, wrong hashes/counts/positions, invalid optional/null states | Bundle verification tests plus new codec-oracle cases | Structured rejection code/path/details with no fixture update and no outside-path access. [VERIFIED: `tests/runtime/orun-bundle.test.ts`, SEM-02] |

### Existing Oracle Source and Test Locations

| Area | Source locations | Existing tests to reuse or consolidate |
|------|------------------|----------------------------------------|
| Event catalog, IDs, normalization | `packages/core/src/events.ts`, `ids.ts`, `id-provider.ts`, `normalization.ts` | `tests/core/event-normalization.test.ts`, `commands.test.ts`, `id-provider.test.ts`, `bootstrap.test.ts` |
| Command decisions and emissions | `packages/runtime/src/legality-evaluator.ts`, `runtime-engine.ts`, `bootstrap.ts`, all `*-control.ts` event factories | `tests/runtime/model-operation-validator.test.ts`, wait/delegation/action/checkpoint/check tests |
| Views | `packages/views/src/*.ts` | `tests/views/*.test.ts`, `tests/runtime/replay.test.ts` |
| Providers | `packages/core/src/provider-normalization.ts`, `packages/provider-*/src/*adapter.ts` | `tests/providers/*.test.ts` |
| SQLite and Artifacts | `packages/storage-sqlite/src/*.ts` | `tests/storage/*.test.ts`, `tests/runtime/artifact-materialization.test.ts` |
| Bundles | `packages/runtime/src/orun.ts` | `tests/runtime/orun-bundle.test.ts`, `orun-replay-resume.test.ts` |
| Transported documents evidence | Python `jsonrpc.py`, `server.py`, `markdown_ops.py`; TS documents client/definition | `tests/capabilities/documents-stdio.test.ts`, Python worker tests |

All paths above are repository-internal evidence. They should be imported by temporary tooling, not re-exported as a public compatibility API. [VERIFIED: phase boundary]

## Standard Stack

### Core

| Technology | Version | Purpose | Why Standard Here |
|------------|---------|---------|-------------------|
| Node.js | Repository requires `>=24`; available `25.2.1` | Execute the temporary predecessor and built-in `node:crypto`, `node:sqlite`, filesystem, and process APIs | This is the existing runtime; adding a second generator runtime would weaken provenance. [VERIFIED: `package.json`, environment probe] |
| TypeScript | `5.9.3` | Type-check generator inputs and fixture inventories against current contracts | Already installed and used by every predecessor package. [VERIFIED: package metadata and `pnpm exec tsc --version`] |
| pnpm | `10.33.3` | Reproducible workspace build and explicit generator/verifier commands | Already pinned by `packageManager`. [VERIFIED: `package.json`, environment probe] |
| Vitest | `4.1.5` installed | Fast manifest, regeneration, drift, and negative tests | Existing repository framework; full baseline passes 58 files and 241 tests with 2 skipped. [VERIFIED: `vitest.config.ts`, `pnpm test` on 2026-08-04] |
| Node `node:crypto` | Built-in | SHA-256 fixture, file, Event-chain, and Bundle commitments | Matches existing ID and Bundle implementations without adding a package. [VERIFIED: `id-provider.ts`, `orun.ts`] |
| Node `node:sqlite` | SQLite `3.51.1` in current Node | Generate real schema/row evidence and raw nullability snapshots | Matches the predecessor adapter exactly. [VERIFIED: environment probe, `packages/storage-sqlite`] |

### Supporting

| Technology | Version | Purpose | When to Use |
|------------|---------|---------|-------------|
| Python documents worker | Python `>=3.9`; available 3.9.6 | Prove one transported CapabilityResult/Artifact/effect scenario | Use only for generic oracle coverage; Markdown semantics are not part of the core wire corpus. [VERIFIED: worker `pyproject.toml`, environment probe] |
| System SQLite CLI | 3.43.2 available | Optional human inspection of generated fixture databases | Do not make it a generator dependency; use `node:sqlite` for authoritative generation. [VERIFIED: environment probe] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Explicit committed files plus hashes | Vitest snapshots | Snapshots are easy to update with `-u`; explicit fixture paths and a separate write command make review and downstream Python consumption clearer. [CITED: https://vitest.dev/guide/learn/snapshots.html] |
| Real predecessor functions | Hand-authored JSON | Hand-authored JSON encodes assumptions and cannot prove emission, persistence, View, or Bundle behavior. [VERIFIED: milestone research] |
| Built-in JSON/crypto | New canonical-JSON dependency | A new package would change the stack and could encode semantics different from the current Bundle contract. [VERIFIED: current implementation] |
| One temporary generator | Permanent TypeScript/Python cross-run matrix | A permanent matrix creates two live products and violates the Phase 37 cutover. [VERIFIED: `REL-03`, roadmap] |

**Installation:** No new external package is needed. Use the checked-in lock and existing `pnpm install` environment. [VERIFIED: repository stack]

## Architecture Patterns

### System Architecture Diagram

```text
explicit maintainer command
        |
        v
temporary predecessor generator
  fixed clock + fixed ID sequence + fixed inputs
        |
        +--> Runtime/Factories --> Event streams + Command decisions
        +--> rebuildViews() ----> all View results
        +--> provider adapters -> normalized proposals / safe errors
        +--> node:sqlite -------> schema + raw rows + decoded rows
        +--> Artifact store ----> metadata + blobs + availability states
        +--> exportBundle() ----> complete / audit / redacted .orun trees
        |
        v
staging corpus + manifest + decision references
        |
        v
coverage complete? -- no --> fail with missing/extra inventory
        |
       yes
        v
byte + semantic + link + hash verification
        |
        +--> explicit promotion to versioned committed corpus
        +--> read-only CI drift test

Phase 28-36 Python tests read frozen corpus only.
Phase 37 gates pass --> remove generator, Node/TS executable, and TS drift tests.
```

### Recommended Project Structure

```text
scripts/
└── compatibility/
    ├── generate-v1-oracle.ts       # temporary; removed in Phase 37
    ├── verify-v1-oracle.ts         # temporary predecessor verifier
    └── oracle-inventory.ts         # independent expected inventory
tests/
├── compatibility/
│   ├── oracle-manifest.test.ts
│   ├── oracle-regeneration.test.ts
│   ├── oracle-wire.test.ts
│   ├── oracle-sqlite.test.ts
│   └── oracle-bundles.test.ts
└── fixtures/
    └── compatibility/
        └── v1/
            ├── manifest.json
            ├── events/
            ├── streams/
            ├── commands/
            ├── views/
            ├── providers/
            ├── sqlite/
            ├── artifacts/
            ├── bundles/
            └── rejection/
docs/
└── archive/
    └── compatibility-v1-decisions.md
```

The committed corpus should remain data-only and language-neutral. TypeScript generator code and predecessor-specific tests are temporary Phase 27–37 assets; Python tests may later relocate the data without changing bytes or manifest identities. [VERIFIED: REL-02/REL-03 constraints]

### Pattern 1: Separate Generate, Promote, and Verify

**What:** The normal test path is read-only. Generation writes to a fresh staging directory. Source and provenance tests are committed first; promotion then captures that clean pre-promotion source commit and refuses to overwrite an existing corpus version. [CITED: https://vitest.dev/guide/learn/snapshots.html]

**When to use:** Always. Tests must never repair their own expected output.

```typescript
// Source: recommended pattern derived from current Vitest and repository scripts
await generateOracle({ output: stagingPath, corpusVersion: "v1", entropy: fixedEntropy });
await verifyOracle({ expected: committedPath, actual: stagingPath, write: false });
// Promotion is a separate maintainer command after source/test commit and decision-log review.
```

### Pattern 2: Deterministic Entropy as an Input

**What:** Inject a fixed clock, exported-at value, ID sequence, temporary root names, provider inputs, and Artifact bytes. Never scrub random output after generation because scrubbing can break causal links and hash inputs. [VERIFIED: random UUID/current-time use throughout runtime factories and `orun.ts`]

**When to use:** Every scenario that produces IDs, timestamps, paths, hashes, or Bundle bytes.

The least invasive seam is an oracle-only dependency object threaded through existing factories: `now()`, `nextEventID()`, `nextCommandID()`, `nextArtifactID()`, `nextLeaseID()`, and `exportedAt`. It must not be exported from public package entry points. [VERIFIED: current dependency injection already supports Engine `now` and bootstrap Event IDs but is incomplete]

### Pattern 3: Bijection Coverage Manifest

**What:** Compute expected keys from independent source inventories, compute actual fixture keys from the staging tree, and require exact set equality. Every entry references content hashes and a decision-ledger ID. [VERIFIED: phase success criterion]

```typescript
// Source: repository-specific recommended verification pattern
const expected = new Set(CORE_EVENT_TYPES.map((type) => `event:${type}:1`));
const actual = new Set(manifest.events.map((entry) => `event:${entry.type}:${entry.version}`));
expect([...actual].sort()).toEqual([...expected].sort());
expect(manifest.commands.map((entry) => entry.decision).sort())
  .toEqual(["accepted", "deferred", "rejected", "superseded"]);
```

### Pattern 4: Assert Bytes and Meaning Separately

**What:** First compare raw UTF-8 bytes and SHA-256. Then parse and assert keys, nullability, link targets, positions, enums, timestamps, and semantic projections. A semantically equal object is not proof of canonical bytes. [VERIFIED: SEM-02]

### Manifest Schema

Use a stable JSON manifest with these top-level fields:

```json
{
  "schemaVersion": 1,
  "corpusVersion": "v1",
  "provenance": {
    "runtime": "openrund",
    "runtimeVersion": "0.0.0",
    "generator": "scripts/compatibility/generate-v1-oracle.ts",
    "sourceRevision": "<git-object-id>",
    "nodeMajor": 24
  },
  "wire": {
    "encoding": "utf-8",
    "bom": false,
    "lineEnding": "lf",
    "jsonlFinalNewline": true,
    "timestampFormat": "utc-rfc3339-milliseconds-z"
  },
  "events": [],
  "commands": [],
  "views": [],
  "providers": [],
  "sqlite": [],
  "artifacts": [],
  "bundles": [],
  "rejections": [],
  "decisions": [],
  "retirementGates": []
}
```

`provenance.sourceRevision` names the clean pre-promotion source commit that contains every `ORACLE_SOURCE_PATHS` input used to generate the bytes. It cannot name the final corpus commit because the revision is itself embedded in corpus bytes and a commit cannot contain its own final object ID. Promotion therefore runs only after source/tests are committed and writes only the absent corpus tree. Post-promotion verification requires the recorded object to exist as a commit and compares the committed `ORACLE_SOURCE_PATHS` tree at current HEAD with that object; HEAD may differ because of the corpus-only commit or later commits outside protected paths. Worktree dirt is ignored by read-only verification, while the pre-write promotion gate still rejects tracked or untracked protected-source dirt.

Each evidence entry should contain:

| Field | Purpose |
|-------|---------|
| `key` | Stable unique identity such as `event:wait.created:1:approval-request`. |
| `path` | Relative corpus path; must be normalized and cannot escape the corpus. |
| `bytesSha256` / `bytes` | Exact file commitment. |
| `semanticSha256` | Hash of the adjudicated canonical semantic value when different from raw file bytes. |
| `sourceKind` | `engine_emitted`, `factory_emitted`, `adapter_normalized`, `store_serialized`, or `declaration_only`. |
| `sourceLocation` | Repository file/function or scenario that produced it. |
| `decisionIDs` | Closed ledger entries governing ambiguous choices. |
| `requiredPointers` | JSON pointers that must be present. |
| `absentPointers` | JSON pointers that must be absent, not null. |
| `nullPointers` | JSON pointers that must exist with JSON null. |
| `links` | IDs/positions/causation/correlation/command relationships to validate. |
| `variants` | Event payload, provider outcome, Artifact state, or profile variant labels. |

`sourceKind = declaration_only` is allowed only when the ledger explains why no live predecessor path emits the declared canonical variant. It must never be silently counted as engine evidence. [VERIFIED: `superseded`, several catalog Events, and declared Artifact states lack normal live emitters]

### Anti-Patterns to Avoid

- **One fixture per Event literal:** A single `wait.created` cannot cover approval, interaction, timer, join, reconciliation, aggregate `waitingOn`, or omission variants. [VERIFIED: control factories]
- **Normalize after random generation:** Replacing UUIDs/paths after the fact can leave hashes, causation, and embedded metadata inconsistent. [VERIFIED: codebase]
- **Self-declared completeness:** If the generator authors both the expected inventory and the actual list from the same scenario list, omissions pass. Keep expected inventory independent. [VERIFIED: current duplicate-key test weakness]
- **Generic snapshots:** `-u` can rewrite them broadly. Keep fixture updates explicit and versioned. [CITED: https://vitest.dev/guide/learn/snapshots.html]
- **Public compatibility exports:** The generator may import internal functions, but no `@openrund/*` package should expose an oracle API. [VERIFIED: phase boundary]

## Declaration-vs-Emission Ambiguity Ledger Inputs

Create the ledger before final corpus generation. Each entry needs: ID, evidence links, conflict statement, canonical resolution, backward-read rule, writer rule, affected fixture keys, and status. Promotion fails if any referenced entry is not `resolved`. [VERIFIED: Phase 27 success criteria]

| Ledger input | Evidence | Recommended resolution for planning |
|--------------|----------|-------------------------------------|
| Event `actor` is required by `EventEnvelope` and emitted/persisted, but omitted from `docs/events.md` envelope list | `events.ts`, all factories, SQLite `actor NOT NULL`, docs | Keep `actor` required in Event v1 and correct the normative docs. [VERIFIED: codebase] |
| Event `commandID` is optional in memory and added to runtime result Events, but SQLite has no `command_id` and drops it on read | `events.ts`, `runtimeCommandEvents`, migrations/store | Keep optional `commandID`; add nullable persistence with a legacy-absent read rule before freezing SQLite rows. Do not freeze silent loss as intended behavior. [VERIFIED: codebase] |
| Missing vs explicit `null` | `JSON.stringify` emitters and SQLite `?? null` binding | Object `undefined` means absent on JSON wire; JSON null must be explicitly supplied; raw SQLite nullable columns use SQL NULL. Record all three states with pointer assertions. [CITED: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/JSON/stringify] |
| Timestamp precision and spelling | `new Date().toISOString()` throughout runtime | Freeze UTC RFC 3339 spelling with exactly millisecond precision and `Z` for v1; generator supplies fixed values. [VERIFIED: codebase] |
| Position semantics and misleading `nextPosition` name | store computes first position 1 and returns current watermark in append result but read returns last+1 | Freeze expected watermark 0, first Event 1, contiguous positions, and document each API result separately. Do not infer semantics from the field name. [VERIFIED: `sqlite-store.ts`, tests] |
| Canonical JSON/hashing | `stableJson` and `hashCanonicalJson` recursively sort keys; `events.jsonl` preserves construction order | Freeze two distinct contracts: raw Event JSONL byte order and recursively sorted canonical hash input. Reject non-finite numbers/BigInt at the canonical boundary instead of accepting JSON coercion. [VERIFIED: `runtime-engine.ts`, `orun.ts`; CITED: MDN JSON.stringify] |
| `command.recorded` model/runtime payload variants | model payload includes `modelCallID`/`kind`; runtime payload includes operation/origin actor; declarations do not cover all emitted fields | Model them as explicit v1 payload variants and freeze both; require `commandID` in canonical emitted records because all normal paths create it. [VERIFIED: `runtime-engine.ts`] |
| `action.failed` declaration vs emission | declaration has `message`/`retryable`; factory emits `error {message, code, retryable}` and Receipt reads `error` | Treat the emitted structured `error` as canonical v1 and align declarations/docs before generation. [VERIFIED: `events.ts`, `action-lifecycle.ts`, `action-receipts.ts`] |
| `message.added`, `annotation.recorded`, `check.recorded`, `checkpoint.created`, `artifact.created` declarations differ from current emitted shapes | core declarations versus Engine/control factories and reducers | Adjudicate each as a named payload variant; prefer the shape consumed by current reducers and emitted by normal Engine paths, then update declarations before freezing. Preserve any already-supported legacy form as a decoder fixture, not as an ambiguous writer. [VERIFIED: codebase] |
| Policy rules overload `authority.granted` | bootstrap emits `{ruleID, rule}` although declaration omits `ruleID`; RunStatus reducer expects it | Freeze capability-grant and policy-rule-grant as two explicit v1 variants under the same Event type; add `ruleID` to the declared union. [VERIFIED: `bootstrap.ts`, `run-status-view.ts`] |
| Wait Events carry several undeclared variants | approval/interaction/timer/join/reconciliation factories plus aggregate wait/resume Events | Freeze tagged variants by `kind` and lifecycle role, including aggregate `waitingOn`/`resumedFrom`; do not let a broad all-optional interface stand in for coverage. [VERIFIED: control factories] |
| Malformed provider arguments become `{}` | `parseProviderToolArguments` catches parse/non-object errors | Normative failure rules favor fail-closed behavior. Record the current observation, adjudicate it as a predecessor defect, and freeze the resolved safe error outcome rather than silently treating malformed input as an empty legal input. [VERIFIED: `provider-normalization.ts`, `docs/providers.md`, milestone pitfalls] |
| Artifact store uses UPSERT despite normative immutability | `sqlite-artifact-store.ts` | Do not bless overwrite behavior. Freeze row/blob/nullability states only; ledger marks conflicting overwrite as noncanonical and Phase 30 supplies immutable enforcement. [VERIFIED: source and `docs/storage.md`] |
| Bundle `requiredProviders` is always empty and `external` Artifact availability is declared but not emitted | `orun.ts` | Freeze exact existing Bundle v1 bytes for cross-read, but mark these as v1 limitations. Any future writer change requires a new Bundle schema/profile decision rather than mutating v1 evidence. [VERIFIED: `orun.ts`] |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Event evidence | Handwritten expected JSON files | Existing runtime/factory output persisted through the real store | Provenance and byte order must come from executable behavior. [VERIFIED: phase goal] |
| View snapshots | Parallel fixture reducers | `rebuildViews(events)` and focused existing reducers | A second reducer could agree with itself while disagreeing with production. [VERIFIED: views architecture] |
| SQLite schema introspection | Regex over migration SQL only | Real generated DB plus `sqlite_master` and PRAGMAs | This captures actual column order, nullability, indexes, and rows. [CITED: https://nodejs.org/download/release/latest-v24.x/docs/api/sqlite.html] |
| Hashing | New crypto/canonicalization library | Existing `node:crypto` SHA-256 and adjudicated `hashCanonicalJson` inputs | Bundle cross-read depends on exact current commitments. [VERIFIED: `orun.ts`] |
| Provider mocks | Live provider calls | Fixed provider response objects and injected `fetchImpl` | Live output is nondeterministic and risks secrets. [VERIFIED: provider tests/docs] |
| Fixture updates | Tests that overwrite expected files | Explicit generate-to-staging plus review/promotion command | Drift must fail visibly. [CITED: Vitest snapshots docs] |

**Key insight:** The value is not a large fixture directory; it is a closed chain from authoritative inventory, through deterministic predecessor execution, to byte commitments, decoded meaning, and retirement gates. [VERIFIED: Phase 27 success criteria]

## Runtime State Inventory

This is a migration-foundation phase, so runtime state outside git matters even though Phase 27 must not mutate it. [VERIFIED: milestone scope]

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `/Users/issam/.openrund` exists with 92 SQLite files, 255 `.orun` directories, and 255 `events.jsonl` files at research time. No SQLite or `.orun` data is checked into the repository. [VERIFIED: read-only filesystem inventory] | Do not copy potentially private/non-deterministic user data into fixtures. Generate a sanitized corpus. Preserve external state untouched for later optional legacy cross-read sampling; any real-data use needs explicit review/redaction. |
| Live service config | No PM2 executable was available; no repository service configuration was found. [VERIFIED: environment/repository inventory] | None for Phase 27. The planner should not assume UI-managed external services contain oracle state. |
| OS-registered state | No OpenRund OS registration was identified in repository evidence, and PM2 is absent. [VERIFIED: repository/environment inventory] | None. Phase 37 should still verify no Node-based scheduled service is required before deletion. |
| Secrets/env vars | Source references provider key variable names and `OPENRUND_LOCAL_MODEL_URL`; values were not read. [VERIFIED: `docs/providers.md`, adapters] | Generator must not read provider credentials, inherit ambient secrets into workers, or run live smoke tests. Use fixed mocked responses. |
| Build artifacts / installed packages | `pnpm test` builds `packages/*/dist`; `node_modules` and TypeScript build outputs are temporary predecessor artifacts. [VERIFIED: `package.json`, executed test command] | Phase 27 may use them. Phase 37 must remove live Node manifests/source/tests/generated outputs and prove Python installed-package gates without Node. |

The canonical question has a non-empty answer: after repository files change, user-home SQLite databases and `.orun` directories remain. Phase 27 freezes sanitized evidence; it does not migrate or delete those records. [VERIFIED: runtime inventory]

## Common Pitfalls

### Pitfall 1: Apparent Coverage with Duplicate or Overwritten Cases

**What goes wrong:** A map or object literal lists many variants but repeated keys overwrite earlier ones, so tests pass without exercising them.

**Why it happens:** Event types such as `wait.created`, `wait.resolved`, `delegation.created`, `message.added`, and `authority.granted` have multiple payload variants.

**How to avoid:** Use arrays keyed by a unique `type:version:variant` ID and reject duplicate manifest keys.

**Warning signs:** Coverage is reported only as `CORE_EVENT_TYPES.length`; the current normalization payload object contains repeated keys. [VERIFIED: `tests/core/event-normalization.test.ts`]

### Pitfall 2: Entropy Makes Regeneration Non-Reproducible

**What goes wrong:** UUIDs, `new Date()`, exported-at timestamps, temporary absolute paths, or iteration order change bytes and hashes.

**How to avoid:** Inject all entropy before execution, use fresh deterministic relative roots, sort only where the contract says ordering is non-semantic, and regenerate twice in separate temp roots as a test.

**Warning signs:** A second generator run changes any committed SHA-256 without a ledger or schema change. [VERIFIED: random/current-time calls in source]

### Pitfall 3: Parsed Equality Hides Wire Drift

**What goes wrong:** Key order, final newline, Unicode escaping, omitted fields, nulls, or timestamp spelling change while parsed objects stay equal.

**How to avoid:** Compare raw bytes first, then semantic values and JSON-pointer presence states.

**Warning signs:** Tests use only `toEqual(JSON.parse(...))`. [VERIFIED: SEM-02 and current tests]

### Pitfall 4: Adapter Views Hide SQLite Contract Loss

**What goes wrong:** SQL NULL becomes `undefined`, `payload_json` key order is ignored, or `commandID` disappears before the fixture is captured.

**How to avoid:** Capture raw schema/rows and adapter-decoded values as separate evidence entries.

**Warning signs:** SQLite coverage calls only `store.read()`. [VERIFIED: current store conversion]

### Pitfall 5: Freezing a Known Bug as Canonical

**What goes wrong:** Permissive provider parsing, Artifact overwrite, or commandID loss becomes a required Python behavior.

**How to avoid:** Decision ledger classifies observations as canonical, backward-read-only, or rejected defect. Only resolved canonical output enters golden writer fixtures.

**Warning signs:** “Current code does it” is the only rationale despite normative contradiction. [VERIFIED: listed ambiguities]

### Pitfall 6: Corpus and Generator Become a Permanent Second Product

**What goes wrong:** New features are implemented in both languages and CI permanently requires Node.

**How to avoid:** Freeze predecessor semantics after Phase 27, prohibit new public surfaces, and encode executable removal gates now.

**Warning signs:** A Python runtime calls the generator, package metadata exports oracle code, or new post-Phase-27 feature scenarios are added to TypeScript instead of Python. [VERIFIED: REL-03]

### Pitfall 7: Stale Files Survive Regeneration

**What goes wrong:** A removed fixture remains in an existing output directory and the manifest still looks complete.

**How to avoid:** Generate into a newly created empty staging root, enumerate every file, require every non-manifest file to be referenced exactly once, then promote atomically after verification.

### Pitfall 8: Secret or Private Runtime Data Enters Git

**What goes wrong:** Provider bodies, credentials, absolute home paths, or user-home Run contents are copied into the corpus.

**How to avoid:** Use synthetic fixed inputs, mocked provider responses, minimal worker environments, relative paths, and a forbidden-pattern scan before promotion. [VERIFIED: provider/worker trust boundaries]

## Code Examples

### Byte and Presence Verification

```typescript
// Source: recommended Phase 27 pattern using Node stdlib
const bytes = await readFile(join(corpusRoot, entry.path));
expect(createHash("sha256").update(bytes).digest("hex")).toBe(entry.bytesSha256);

const value = JSON.parse(bytes.toString("utf8"));
for (const pointer of entry.requiredPointers) expect(hasPointer(value, pointer)).toBe(true);
for (const pointer of entry.absentPointers) expect(hasPointer(value, pointer)).toBe(false);
for (const pointer of entry.nullPointers) expect(readPointer(value, pointer)).toBeNull();
```

### Raw SQLite Evidence

```typescript
// Source: Node node:sqlite and existing storage adapter pattern
const schema = db.prepare(
  "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY type, name"
).all();
const columns = db.prepare("PRAGMA table_info(run_events)").all();
const rows = db.prepare("SELECT * FROM run_events ORDER BY run_id, position").all();
// Serialize this raw evidence before adapter null-to-undefined conversion.
```

### Regeneration Drift Test

```typescript
// Source: recommended repository test pattern
const first = await generateToFreshTemp("first");
const second = await generateToFreshTemp("second");
expect(await hashTree(first)).toEqual(await hashTree(second));
expect(await diffTrees(committedCorpus, first)).toEqual([]);
```

## Retirement Gates

Encode these as manifest entries and as Phase 37 checklist/test names now. The generator may be removed only when all gates are true. [VERIFIED: REL-03 and Phase 37]

| Gate ID | Required evidence before removal |
|---------|----------------------------------|
| `RET-01-python-golden-read` | Python decodes every frozen positive fixture and rejects every frozen negative fixture with mapped stable errors. |
| `RET-02-python-golden-write` | Python re-encodes every canonical writer fixture to exact bytes or exact adjudicated canonical commitments. |
| `RET-03-event-view-parity` | Python rebuilds every frozen View result from frozen streams at the same watermark. |
| `RET-04-sqlite-cross-read` | Python reads the frozen SQLite schema/rows, including legacy null/absent command linkage, and writes the adjudicated current schema. |
| `RET-05-artifact-cross-read` | Python preserves every frozen Artifact metadata/blob/availability state and immutable identity rule. |
| `RET-06-bundle-bidirectional` | Python reads all predecessor-produced complete/audit/redacted Bundles; before predecessor deletion, the predecessor reads Python-produced v1 Bundles or an explicit version decision records why not. |
| `RET-07-installed-wheel` | A clean wheel/sdist environment passes public import, CLI, demo, golden, and Bundle tests with Node absent. |
| `RET-08-source-surface-clean` | No live Node, pnpm, JavaScript, TypeScript, temporary generator, predecessor CI, or predecessor-facing docs/examples remain outside archived historical evidence. |
| `RET-09-provenance-preserved` | Frozen data, manifest, hashes, decision ledger, and Git history remain inspectable after executable removal. |
| `RET-10-no-dual-development` | No feature after Phase 27 depends on adding behavior to the predecessor; the oracle is frozen except for explicit corpus-version corrections. |

## Recommended Plan Decomposition

### Plan 27-01: Contract Inventory and Adjudication

- Establish independent inventories for 37 Events/versions/variants, four decisions, nine Views, provider outcomes, SQLite tables/columns, Artifact states, and three Bundle profiles. [VERIFIED: codebase inventory]
- Create the versioned ambiguity ledger and resolve every item that affects bytes or meaning.
- Align normative docs and TypeScript declarations with the chosen v1 writer contract where emission is authoritative; encode backward-read-only shapes separately.
- Add explicit constants/registries only when needed for machine inventory; keep them internal and avoid a public compatibility API.

### Plan 27-02: Deterministic Generator and Corpus

- Add oracle-only deterministic clock/ID/export timestamp seams.
- Generate Event/Command streams, all Views, provider outcomes, real SQLite raw rows, Artifact states, and complete/audit/redacted Bundles into a fresh staging tree.
- Write the manifest last from the actual tree, then run independent completeness, reference, byte, semantic, and security checks.
- Commit the finalized source/tests first, then promote `v1` only after two clean generations are byte-identical; the promotion task writes only the absent corpus tree and records the pre-promotion source commit.

### Plan 27-03: Drift Verification and Retirement Contract

- Add read-only fast tests for manifest bijection, file hashes, exact bytes, null/absence pointers, links, rows, hashes, and profile commitments.
- Add a regeneration test that writes only to temporary directories and produces a readable recursive diff.
- Add Phase 37 retirement gate documentation/test metadata and a source guard proving the oracle is not exported or packaged.
- Run full TypeScript and Python-documents baselines; do not commit generator outputs produced from live provider/user data.

The three plans are sequential: ambiguous contracts must be closed before deterministic output is promoted, and drift/retirement tests depend on the promoted corpus. [VERIFIED: phase dependency]

## State of the Art

| Old Approach | Current Phase 27 Approach | When Changed | Impact |
|--------------|---------------------------|--------------|--------|
| Dispersed unit expectations | One versioned corpus with a coverage manifest | Phase 27 | Completeness is machine-checkable. |
| Parsed-object assertions | Raw bytes plus decoded meaning and presence states | Phase 27 | Key order, omission, nulls, timestamps, and newlines cannot drift silently. |
| Hand-built test Events | Deterministic predecessor execution with provenance labels | Phase 27 | Fixtures prove actual factories, stores, reducers, and exporters. |
| Type declarations treated as truth | Closed declaration-vs-emission ledger | Phase 27 | Known contradictions become explicit compatibility decisions. |
| Open-ended dual runtime | Frozen evidence and predefined Phase 37 removal gates | Phase 27 | Python can become the only live product. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|

All material repository claims in this research were verified from the current codebase, planning artifacts, executed baseline, or cited official documentation. Recommendations remain planner discretion rather than hidden factual assumptions.

## Open Questions (RESOLVED)

1. **Historical data policy — synthetic evidence only.**
   - Decision: the v1 corpus contains no historical user data, including redacted samples. All Events, SQLite rows, Artifacts, provider responses, and Bundles are generated from fixed synthetic inputs. User-home runtime state remains untouched and outside every generator input/path allowlist.
   - Consequence: a future historical-shape investigation requires a separately authorized corpus version and cannot alter the v1 promotion path.

2. **Declaration-only state policy — retain only normatively required states.**
   - Decision: a non-emitted declared state remains in the canonical v1 inventory only when normative semantics or an existing reducer requires it. Every retained case is labeled `declaration_only`, cites a resolved ledger decision, and cannot count as Engine/factory evidence. Declarations with neither normative nor reducer support are excluded from the v1 writer inventory and recorded only as non-canonical observations in the decision ledger.
   - Consequence: promotion tests prove both that every retained declaration-only entry is justified and that non-canonical observations are not silently promoted.

3. **Trusted source revision policy — record the clean pre-promotion source commit.**
   - Decision: source and provenance tests are committed before corpus promotion. Promotion then captures `sourceRevision` from `git rev-parse --verify HEAD^{commit}` and checks tracked plus untracked `ORACLE_SOURCE_PATHS` inputs before any corpus write; callers cannot supply or override it. The promotion task writes only the absent corpus tree, so the later corpus commit does not create a self-referential provenance claim. Read-only verification requires sourceRevision to exist as a commit and requires the committed `ORACLE_SOURCE_PATHS` tree at current HEAD to match it, but permits the corpus commit and later commits outside those paths. It ignores worktree dirt and never attempts promotion.
   - Consequence: nonexistent/non-commit objects, an existing source-tree-mismatched commit, dirty protected promotion inputs, and later committed protected-source drift have explicit negative tests. Corpus-only/unrelated later commits and ordinary dirty read-only verification have positive tests.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js | Temporary predecessor generator | ✓ | 25.2.1; repo minimum 24 | Use CI Node 24 to prove minimum compatibility before promotion. |
| pnpm | Build/test/generator scripts | ✓ | 10.33.3 | None needed. |
| TypeScript | Generator and predecessor build | ✓ | 5.9.3 | None needed. |
| Vitest | Oracle verification | ✓ | 4.1.5 | None needed. |
| Node SQLite | Raw schema/row generation | ✓ | SQLite 3.51.1 | System sqlite CLI is inspection-only, not authoritative. |
| Python | Documents transported scenario | ✓ | 3.9.6 | Skip only that supplemental scenario if worker dependencies are unavailable; core oracle remains Node-generated. |
| System sqlite3 | Optional inspection | ✓ | 3.43.2 | `node:sqlite`. |

**Missing dependencies with no fallback:** None for Phase 27. [VERIFIED: environment audit]

**Missing dependencies with fallback:** None required. The future Python product's 3.12 floor is not a Phase 27 generator dependency. [VERIFIED: phase scope]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.5 for predecessor/oracle verification; existing pytest only for the supplemental documents worker |
| Config file | `vitest.config.ts`; Python worker config in `python/openrund_documents_worker/pyproject.toml` |
| Quick run command | `pnpm exec vitest run tests/compatibility/oracle-manifest.test.ts tests/compatibility/oracle-wire.test.ts` |
| Regeneration check | `pnpm exec vitest run tests/compatibility/oracle-regeneration.test.ts` — writes only to temporary directories |
| Full suite command | `pnpm test` |
| Supplemental worker command | `pnpm test:python-documents` |

The baseline full suite passed on 2026-08-04: 58 test files, 241 passed tests, and 2 credential/environment-gated skips. [VERIFIED: executed `pnpm test`]

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| SEM-02 | Manifest exactly covers all 37 Event type/version keys and all payload variants without duplicates | unit/contract | `pnpm exec vitest run tests/compatibility/oracle-manifest.test.ts -t "event inventory"` | ❌ Wave 0 |
| SEM-02 | Manifest covers accepted/rejected/deferred/superseded Command decisions and target Event presence/absence | unit/contract | `pnpm exec vitest run tests/compatibility/oracle-manifest.test.ts -t "command decisions"` | ❌ Wave 0 |
| SEM-02 | Every fixture hash, byte length, path reference, and tree entry matches; no orphan/stale files | integrity | `pnpm exec vitest run tests/compatibility/oracle-manifest.test.ts -t "tree integrity"` | ❌ Wave 0 |
| SEM-02 | JSON bytes preserve key order, LF/final newline, enum strings, IDs, timestamps, and absent-vs-null pointers | unit/golden | `pnpm exec vitest run tests/compatibility/oracle-wire.test.ts` | ❌ Wave 0 |
| SEM-02 | Positions start at 1, remain contiguous, and all causation/correlation/command/result/Wait links resolve | invariant | `pnpm exec vitest run tests/compatibility/oracle-wire.test.ts -t "links and positions"` | ❌ Wave 0 |
| SEM-02 | Every Event stream rebuilds exact Run/View bundle results across all nine surfaces | replay/contract | `pnpm exec vitest run tests/compatibility/oracle-views.test.ts` | ❌ Wave 0 |
| SEM-02 | All provider adapter outcome cases normalize to exact proposals or safe errors without secrets | unit/contract | `pnpm exec vitest run tests/compatibility/oracle-providers.test.ts` | ❌ Wave 0 |
| SEM-02 | SQLite schema, indexes, raw rows, SQL NULL, payload JSON, and adapter round-trip match fixtures | integration | `pnpm exec vitest run tests/compatibility/oracle-sqlite.test.ts` | ❌ Wave 0 |
| SEM-02 | Artifact metadata-only/blob/unavailable/omitted/redacted states and hashes match | integration | `pnpm exec vitest run tests/compatibility/oracle-artifacts.test.ts` | ❌ Wave 0 |
| SEM-02 | Complete/audit/redacted `.orun` trees, file hashes, Event chain, Bundle commitment, and replay match | integration/golden | `pnpm exec vitest run tests/compatibility/oracle-bundles.test.ts` | ❌ Wave 0 |
| SEM-02 | Unknown versions, malformed JSON, invalid paths, bad hashes, and invalid presence states fail closed | negative/security | `pnpm exec vitest run tests/compatibility/oracle-rejections.test.ts` | ❌ Wave 0 |
| SEM-02 | Source/tests commit first; two clean generations equal the corpus; sourceRevision survives corpus-only/unrelated commits but rejects protected-tree drift; normal tests never write corpus | determinism/provenance | `pnpm exec vitest run tests/compatibility/oracle-regeneration.test.ts` | ❌ Wave 0 |
| SEM-02 / REL-03 | Temporary generator is not exported/packaged and every Phase 37 retirement gate is represented | architecture/release | `pnpm exec vitest run tests/compatibility/oracle-retirement.test.ts` | ❌ Wave 0 |

### Test Design Details

1. **Manifest tests are independent of generator scenarios.** Expected Event keys come from `CORE_EVENT_TYPES` plus an explicit variant registry; expected decisions/profiles/Views come from separate constants. Actual entries come from the committed manifest. Exact set equality catches additions and removals. [VERIFIED: current architecture]
2. **Regeneration uses two fresh temporary roots.** It compares tree path sets, file bytes, hashes, and manifest content. Absolute staging paths are forbidden in output. [VERIFIED: determinism requirement]
3. **Wire tests inspect property presence before applying defaults.** They assert JSON pointers in three categories: present with value, present as null, and absent. [CITED: MDN JSON.stringify]
4. **Semantic tests resolve links.** Every ID is validated for expected spelling; positions and Event counts are exact; each causation/correlation/command/result/Wait link points to a valid fixture entity or an explicitly external correlation value.
5. **SQLite tests capture raw and decoded layers.** Raw SQL rows retain null; adapter results may omit optional fields. Schema evidence includes tables, indexes, columns, defaults, primary keys, and unique constraints. [CITED: Node 24 sqlite docs]
6. **Bundle tests verify the whole tree.** They recompute per-file SHA-256, `sha256-chain-v1`, and `sha256-canonical-json-v1`; they also replay Views and inspect Artifact omission reasons for all three profiles. [VERIFIED: `orun.ts`]
7. **Negative tests never run update mode.** They mutate only temporary copies and assert structured codes, paths, and no writes outside staging. [VERIFIED: current Bundle tests]
8. **Provider cases use fixed response objects/fetch mocks.** No environment credential enables a live branch in the oracle suite. [VERIFIED: provider tests]

### Sampling Rate

- **Per task commit:** Run the focused file(s) in the table plus `pnpm typecheck` when source/types change.
- **Per wave merge:** Run `pnpm test` and `pnpm test:python-documents` if the transported-documents scenario changed.
- **Phase gate:** Full suite green; source/test finalization committed before promotion; two independent generations byte-identical; committed corpus diff empty; sourceRevision object exists and protected source tree matches despite the later corpus commit; manifest completeness 100%; ambiguity ledger has zero unresolved entries; forbidden-secret/path scan clean.

### Wave 0 Gaps

- [ ] `scripts/compatibility/oracle-inventory.ts` — independent expected inventories and duplicate detection.
- [ ] `scripts/compatibility/generate-v1-oracle.ts` — deterministic generator with explicit output root.
- [ ] `scripts/compatibility/verify-v1-oracle.ts` — read-only recursive verifier and human-readable diff.
- [ ] `tests/compatibility/oracle-manifest.test.ts` — completeness, uniqueness, references, and tree integrity.
- [ ] `tests/compatibility/oracle-wire.test.ts` — byte, pointer presence, IDs, timestamps, positions, and links.
- [ ] `tests/compatibility/oracle-views.test.ts` — nine View surfaces.
- [ ] `tests/compatibility/oracle-providers.test.ts` — provider outcome matrix.
- [ ] `tests/compatibility/oracle-sqlite.test.ts` — schema/raw/decoded evidence.
- [ ] `tests/compatibility/oracle-artifacts.test.ts` — Artifact state matrix.
- [ ] `tests/compatibility/oracle-bundles.test.ts` — three profiles and commitments.
- [ ] `tests/compatibility/oracle-rejections.test.ts` — malformed/unsupported inputs.
- [ ] `tests/compatibility/oracle-regeneration.test.ts` — two-run determinism and committed drift.
- [ ] `tests/compatibility/oracle-retirement.test.ts` — packaging/public-surface guard and Phase 37 gates.
- [ ] `tests/fixtures/compatibility/v1/manifest.json` and corpus tree — generated after ledger closure.
- [ ] `docs/archive/compatibility-v1-decisions.md` — versioned decision ledger.

No new test framework installation is required. [VERIFIED: existing Vitest/pytest infrastructure]

## Security Domain

Security enforcement is enabled at ASVS level 1. The corpus generator handles untrusted-shaped provider, Bundle, JSON, SQLite, path, and worker data, so validation and file-safety controls apply even though it is developer tooling. [VERIFIED: `.planning/config.json`]

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No authenticated service or user identity is added. |
| V3 Session Management | no | No web/session surface is added. |
| V4 Access Control | yes, architectural | Generator cannot append through a new public authority path; it uses internal tooling only and package export tests enforce this. [VERIFIED: Engine authority contract] |
| V5 Input Validation | yes | Validate manifest shape, unique keys, relative normalized paths, JSON pointer assertions, supported versions, SQLite evidence shape, and provider envelopes before promotion. |
| V6 Cryptography | yes | Use `node:crypto` SHA-256 and the frozen existing commitment algorithms; never invent a new digest or compare only decoded values. [VERIFIED: `orun.ts`] |
| V12 Files and Resources | yes | Generate only under an explicit fresh staging root; reject absolute paths, drive paths, `..`, NUL, symlinks, and unreferenced files; never traverse user-home data during normal generation. [VERIFIED: Bundle path threat model] |

### Known Threat Patterns for the Oracle

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Manifest path escape or symlink | Tampering / Elevation | Validate normalized relative paths before filesystem access and reject symlinks. |
| Fixture self-update in tests | Tampering | Verification is read-only; promotion is a separate explicit command. |
| Provider secret/body captured in corpus | Information disclosure | Fixed mocked responses, no credential reads, redaction/forbidden-pattern scan. |
| User-home runtime data copied into git | Information disclosure | Synthetic corpus only by default; explicit review/redaction for any historical sample. |
| Hash-valid but incomplete manifest | Tampering | Independent expected inventory and exact bijection checks. |
| Random/path-dependent output | Repudiation / Tampering | Inject entropy and require two-run reproducibility. |
| Executable oracle retained indefinitely | Spoofing / architectural drift | Phase 37 retirement tests and no public/package export. |

## Sources

### Primary (HIGH confidence)

- `AGENTS.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`, and `27-CONTEXT.md` — phase constraints and retirement boundary.
- `docs/concepts.md`, `control.md`, `architecture.md`, `events.md`, `providers.md`, `storage.md`, `capabilities.md`, `bundles.md`, `delegation.md`, and `api.md` — normative contracts.
- `packages/core/src/events.ts`, `model.ts`, `run.ts`, `ids.ts`, `id-provider.ts`, `normalization.ts`, `provider-normalization.ts`, and `storage.ts` — declared canonical surfaces.
- `packages/runtime/src/runtime-engine.ts`, `bootstrap.ts`, `action-lifecycle.ts`, all Wait/Delegation/Check/Checkpoint/Artifact control modules, and `orun.ts` — emitted and transported behavior.
- `packages/views/src/*.ts`, `packages/storage-sqlite/src/*.ts`, and `packages/provider-*/src/*.ts` — derived, persisted, and normalized behavior.
- Existing `tests/core`, `tests/runtime`, `tests/views`, `tests/storage`, `tests/providers`, and `tests/capabilities/documents-stdio.test.ts` — predecessor behavioral evidence.
- `.planning/research/SUMMARY.md`, `STACK.md`, `ARCHITECTURE.md`, `FEATURES.md`, and `PITFALLS.md` — milestone sequencing and known compatibility hazards.

### Secondary (MEDIUM confidence)

- [MDN `JSON.stringify`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/JSON/stringify) — stable property traversal, omission/null conversion, date serialization, and invalid values.
- [Node.js 24 `node:sqlite`](https://nodejs.org/download/release/latest-v24.x/docs/api/sqlite.html) — synchronous DatabaseSync, row APIs, and SQLite/JavaScript null/type conversion.
- [Vitest snapshot guide](https://vitest.dev/guide/learn/snapshots.html) — explicit snapshot update behavior and CI mismatch failure.

### Tertiary (LOW confidence)

- None. No LOW-confidence finding is used as a planning decision.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing installed repository stack was inspected and executed.
- Architecture: HIGH — derived directly from phase success criteria and current package boundaries.
- Coverage inventory: HIGH for named surfaces and counts; MEDIUM for final payload-variant membership until the decision ledger closes.
- Pitfalls: HIGH — directly observed in source/tests or required by SEM-02.
- External JSON/SQLite/Vitest behavior: MEDIUM — official documentation fetched through the research seam.

**Research date:** 2026-08-04
**Valid until:** 2026-09-03 for repository behavior; re-run source inventory if predecessor code changes before corpus promotion.
