# Testing Patterns

**Analysis Date:** 2026-05-15

## Test Framework

**Runner:**
- Vitest `^4.0.7` for TypeScript tests.
- Config: `vitest.config.ts`
- Include pattern: `tests/**/*.test.ts`
- Environment: `node`
- Pytest `>=8.0.0` for the transported Python documents worker.
- Config: `python/openrund_documents_worker/pyproject.toml`

**Assertion Library:**
- Vitest `expect` for TypeScript tests, imported from `vitest`.
- Pytest plain `assert` plus `pytest.raises()` for Python tests.

**Run Commands:**
```bash
pnpm test              # Build all TypeScript packages, then run Vitest once
pnpm typecheck         # TypeScript project-reference typecheck without pretty output
pnpm hygiene           # Repository hygiene and ontology naming checks
pnpm package:check     # Package content check after build output exists
cd python/openrund_documents_worker && python3 -m pytest  # Python worker tests
```

Coverage command: Not detected. There is no configured `coverage`, `c8`, `istanbul`, or Vitest coverage script in `package.json` or `vitest.config.ts`.

## Test File Organization

**Location:**
- TypeScript tests live in top-level `tests/`, grouped by subsystem:
  - `tests/core/`
  - `tests/runtime/`
  - `tests/capabilities/`
  - `tests/storage/`
  - `tests/views/`
  - `tests/providers/`
  - `tests/public-api/`
  - `tests/docs/`
  - `tests/examples/`
- Python worker tests live beside the worker package in `python/openrund_documents_worker/tests/`.

**Naming:**
- TypeScript test files use `<subject>.test.ts`: `tests/runtime/action-dispatcher.test.ts`, `tests/capabilities/filesystem.test.ts`, `tests/storage/sqlite-store.test.ts`.
- Python test files use `test_<subject>.py`: `python/openrund_documents_worker/tests/test_markdown_ops.py`, `python/openrund_documents_worker/tests/test_jsonrpc.py`.

**Structure:**
```text
tests/
├── capabilities/       # Capability definitions, transports, workers, and policy behavior
├── core/               # Core ontology, IDs, commands, event normalization
├── docs/               # Documentation link and sentinel gates
├── examples/           # Flagship demo behavior
├── providers/          # Provider adapters and provider-boundary guards
├── public-api/         # Export and ontology guard tests
├── runtime/            # Runtime engine, waits, delegation, replay, CLI behavior
├── storage/            # SQLite event/artifact/lease stores
└── views/              # Derived view reducers

python/openrund_documents_worker/tests/
├── test_jsonrpc.py     # Worker process protocol smoke tests
└── test_markdown_ops.py # Markdown operation unit tests
```

## Test Structure

**Suite Organization:**
```typescript
import { describe, expect, it } from "vitest";

describe("filesystem capability", () => {
  it("rejects traversal outside authorized roots", async () => {
    const root = mkdtempSync(join(tmpdir(), "openrund-fs-root-"));
    const handlers = createFilesystemHandlers({
      mounts: [{ name: "workspace", root }]
    });

    await expect(
      handlers["filesystem.read"]!(request("read", {
        mount: "workspace",
        path: "../escape.txt"
      }, root))
    ).rejects.toSatisfy(isCapabilityError);
  });
});
```

Source example: `tests/capabilities/filesystem.test.ts`.

**Patterns:**
- Group tests by public behavior or subsystem with one `describe()` per file. Examples: `describe("RuntimeEngine replay", ...)` in `tests/runtime/replay.test.ts`, `describe("SqliteRunEventStore", ...)` in `tests/storage/sqlite-store.test.ts`.
- Name `it()` cases as behavior statements: "rejects stale expected-position appends", "creates a durable approval wait when policy requires approval", "fails closed on unsuccessful provider HTTP responses".
- Build minimal real objects instead of broad mocks. Examples: `RuntimeEngine` with `SqliteRunEventStore` in `tests/runtime/cli-smoke.test.ts`; `ActionDispatcher` with `InProcessCapabilityTransport` in `tests/capabilities/filesystem.test.ts`.
- Assert event sequences with `events.map((event) => event.type)` when behavior is event-log oriented. Examples: `tests/runtime/action-dispatcher.test.ts`, `tests/capabilities/documents-stdio.test.ts`.
- Assert compact payload shape with `toMatchObject()` rather than exact full payloads unless ordering/positions are part of the contract. Examples: `tests/runtime/action-dispatcher.test.ts`, `tests/runtime/cli-phase5.test.ts`.
- Use fixed timestamps in runtime tests for deterministic event output: `"2026-05-09T20:40:00.000Z"` in `tests/runtime/action-dispatcher.test.ts`, `"2026-05-09T18:00:00.000Z"` in `tests/runtime/cli-smoke.test.ts`.
- Use `it.skipIf(!process.env.<VAR>)` for optional live-provider smoke checks. Examples: `tests/providers/openai.test.ts`, `tests/providers/anthropic.test.ts`, `tests/providers/local-openai-compatible.test.ts`.

## Mocking

**Framework:** Vitest `vi`

**Patterns:**
```typescript
import { vi } from "vitest";

function runtimeStub() {
  return {
    bootstrap: vi.fn(),
    replay: vi.fn(),
    readEvents: vi.fn(),
    resolveApproval: vi.fn(),
    reconcileActionOutcome: vi.fn(),
    exportBundle: vi.fn(),
    verifyBundle: vi.fn(),
    importBundle: vi.fn(),
    replayBundle: vi.fn(),
    assessImportedResume: vi.fn()
  };
}
```

Source example: `tests/runtime/cli-phase5.test.ts`.

**What to Mock:**
- Mock CLI runtime dependencies when verifying CLI argument mapping, result shape, and delegation to runtime APIs. Use the `runtimeStub()` style from `tests/runtime/cli-phase5.test.ts`.
- Mock provider network calls by injecting `fetchImpl` into provider adapters. Example: `tests/providers/openai.test.ts`.
- Use in-process capability handlers as lightweight fakes for capability behavior. Examples: `tests/runtime/action-dispatcher.test.ts`, `tests/capabilities/filesystem.test.ts`.
- For process boundary tests, spawn the real built/process entrypoint when the contract is the binary or stdio protocol. Examples: `tests/runtime/cli-smoke.test.ts`, `tests/capabilities/documents-stdio.test.ts`, `python/openrund_documents_worker/tests/test_jsonrpc.py`.

**What NOT to Mock:**
- Do not mock event reducers when testing runtime behavior; rebuild or inspect real events. Examples: `tests/runtime/replay.test.ts`, `tests/runtime/check-gate.test.ts`.
- Do not mock SQLite stores in storage tests; use temporary real SQLite databases. Examples: `tests/storage/sqlite-store.test.ts`, `tests/storage/sqlite-artifact.test.ts`, `tests/storage/sqlite-lease.test.ts`.
- Do not mock filesystem/path sandbox behavior in filesystem capability tests; use real temporary roots, files, and symlinks. Example: `tests/capabilities/filesystem.test.ts`.
- Do not give providers Event append authority in adapter tests; source sentinel tests enforce that provider adapters do not import `RuntimeEngine`, `RunEventStore`, or event append terminology. Examples: `tests/providers/openai.test.ts`, `tests/providers/anthropic.test.ts`, `tests/providers/local-openai-compatible.test.ts`.

## Fixtures and Factories

**Test Data:**
```typescript
function makeEvent(index: number): NewRuntimeEvent {
  return {
    id: asEventID(`evt_${index}`),
    runID: asRunID("ses_sqlite"),
    type: "run.created",
    version: 1,
    timestamp: `2026-05-09T18:00:0${index}.000Z`,
    actor: "system",
    payload: {
      rootID: asRunID("ses_sqlite"),
      initialStatus: "created"
    }
  };
}
```

Source example: `tests/storage/sqlite-store.test.ts`.

**Location:**
- Factories usually live at the bottom or top of the same test file that uses them. Examples: `request()` in `tests/capabilities/filesystem.test.ts`, `setupDispatcher()` in `tests/capabilities/documents-stdio.test.ts`, `createStore()` and `makeEvent()` in `tests/storage/sqlite-store.test.ts`.
- Shared static demo fixtures live under `examples/governed-coding-run/fixtures/`.
- Expected demo output lives under `examples/governed-coding-run/expected/`.
- Python tests use pytest `tmp_path` instead of shared fixture files for document mutations: `python/openrund_documents_worker/tests/test_markdown_ops.py`.

## Coverage

**Requirements:** None enforced by tooling.

**View Coverage:**
```bash
# Not detected
```

**Effective Coverage Gates:**
- `pnpm test` gates TypeScript behavior through build plus Vitest.
- `tests/docs/docs-links.test.ts` gates live docs existence, local links, and sentinel strings.
- `tests/public-api/exports.test.ts` gates package-level public exports.
- `tests/public-api/ontology-guards.test.ts` and `scripts/check-secondary-surface-names.mjs` gate ontology-facing naming.
- `tests/examples/governed-coding-run.test.ts` gates the flagship demo path.
- `python/openrund_documents_worker/tests/test_markdown_ops.py` and `python/openrund_documents_worker/tests/test_jsonrpc.py` gate Python worker behavior, but these are not invoked by root `pnpm test`.

## Test Types

**Unit Tests:**
- Core pure contracts and reducers: `tests/core/contracts.test.ts`, `tests/core/event-normalization.test.ts`, `tests/views/views.test.ts`, `tests/views/wait-queues.test.ts`.
- Capability schema/registry/tool mapping: `tests/capabilities/registry.test.ts`, `tests/capabilities/tool-schema.test.ts`.
- Python markdown operations: `python/openrund_documents_worker/tests/test_markdown_ops.py`.

**Integration Tests:**
- Runtime engine with real event store and replay flows: `tests/runtime/local-runtime.test.ts`, `tests/runtime/replay.test.ts`, `tests/runtime/orun-bundle.test.ts`, `tests/runtime/orun-replay-resume.test.ts`.
- Capability dispatch through registry/transports/artifact stores: `tests/capabilities/filesystem.test.ts`, `tests/capabilities/documents-stdio.test.ts`, `tests/capabilities/process.test.ts`, `tests/capabilities/git.test.ts`.
- SQLite storage behavior with real temporary databases: `tests/storage/sqlite-store.test.ts`, `tests/storage/sqlite-artifact.test.ts`, `tests/storage/sqlite-lease.test.ts`.
- CLI library and built binary smoke paths: `tests/runtime/cli-smoke.test.ts`, `tests/runtime/cli-phase5.test.ts`.

**E2E Tests:**
- No browser or Playwright E2E framework is detected.
- The closest E2E-style coverage is the governed coding demo test in `tests/examples/governed-coding-run.test.ts` and CLI process smoke tests in `tests/runtime/cli-smoke.test.ts`.

## Common Patterns

**Async Testing:**
```typescript
await expect(
  store.append({
    runID: asRunID("ses_sqlite"),
    expectedPosition: 0,
    events: [makeEvent(2)]
  })
).rejects.toBeInstanceOf(ExpectedPositionConflictError);
```

Source example: `tests/storage/sqlite-store.test.ts`.

**Error Testing:**
```typescript
await expect(
  handlers["filesystem.update"]!(request("update", {
    mount: "workspace",
    path: "docs/a.md",
    content: "# B",
    expectedHash: "stale"
  }, root))
).rejects.toSatisfy(isCapabilityError);
```

Source example: `tests/capabilities/filesystem.test.ts`.

**Process Testing:**
```typescript
const output = execFileSync(process.execPath, [
  "packages/cli/dist/bin.js",
  "create",
  "run_cli_process"
], {
  cwd: process.cwd(),
  env: {
    ...process.env,
    OPENRUND_HOME: root
  },
  encoding: "utf8"
});
```

Source example: `tests/runtime/cli-smoke.test.ts`.

**Python Error Testing:**
```python
with pytest.raises(markdown_ops.DocumentConflict):
    markdown_ops.write_document(
        {"path": str(doc), "content": "# Intro\nBye\n", "expectedHash": "stale"}
    )
```

Source example: `python/openrund_documents_worker/tests/test_markdown_ops.py`.

---

*Testing analysis: 2026-05-15*
