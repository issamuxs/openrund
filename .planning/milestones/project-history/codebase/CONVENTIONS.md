# Coding Conventions

**Analysis Date:** 2026-05-15

## Naming Patterns

**Files:**
- Use lowercase kebab-case for TypeScript implementation files: `packages/runtime/src/runtime-engine.ts`, `packages/runtime/src/action-dispatcher.ts`, `packages/capability-filesystem/src/filesystem-capability.ts`.
- Use `index.ts` as the package public barrel: `packages/core/src/index.ts`, `packages/runtime/src/index.ts`, `packages/capability-filesystem/src/index.ts`.
- Use `definition.ts` for capability metadata and schema declarations: `packages/capability-filesystem/src/definition.ts`, `packages/capability-documents/src/definition.ts`, `packages/capability-process/src/definition.ts`.
- Use `.test.ts` under `tests/<area>/` for TypeScript tests: `tests/runtime/action-dispatcher.test.ts`, `tests/capabilities/filesystem.test.ts`, `tests/storage/sqlite-store.test.ts`.
- Use snake_case for Python files and pytest tests: `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py`, `python/openrund_documents_worker/tests/test_markdown_ops.py`.

**Functions:**
- Use camelCase verbs for runtime and library functions: `createCapabilityRegistry()` in `packages/capabilities/src/registry.ts`, `resolveUnderMount()` in `packages/capability-filesystem/src/path-sandbox.ts`, `rebuildViews()` in `packages/views/src/index.ts`.
- Use `create*` for factories that produce handlers, events, registries, or runtime artifacts: `createFilesystemHandlers()` in `packages/capability-filesystem/src/filesystem-capability.ts`, `createBootstrapEvents()` in `packages/runtime/src/bootstrap.ts`, `createModelCallID()` in `packages/core/src/ids.ts`.
- Use `reduce*` for view reducers: `reduceRunStatusView()` in `packages/views/src/run-status-view.ts`, `reduceWaitQueueView()` in `packages/views/src/wait-queues.ts`, `reduceActionReceipts()` in `packages/views/src/action-receipts.ts`.
- Use `as*` for branded ID coercion helpers: `asRunID()`, `asCapabilityID()`, and `asEventID()` from `packages/core/src/ids.ts`.
- Use private helper functions after exported API functions in the same file: `validateActions()` and `rejectedRegistration()` in `packages/capabilities/src/registry.ts`; `readExistingHash()`, `assertExpectedHash()`, `sha256()`, and `cap()` in `packages/capability-filesystem/src/filesystem-capability.ts`.
- Python functions use snake_case: `sha256_text()`, `read_document()`, `patch_document()`, and `assert_expected()` in `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py`.

**Variables:**
- Use camelCase for local values and object properties: `policyOutcome`, `artifactStore`, `expectedPosition`, `runtimeHome` in `packages/runtime/src/runtime-engine.ts` and `packages/cli/src/index.ts`.
- Use `ID` suffix casing for branded identifiers and payload fields: `runID`, `waitID`, `actionID`, `capabilityID` across `packages/core/src/events.ts`, `packages/runtime/src/runtime-engine.ts`, and tests.
- Use descriptive booleans and status flags: `executed` in `tests/runtime/action-dispatcher.test.ts`, `retryable` in `packages/capabilities/src/errors.ts`, `resumable` in CLI result tests.
- Use `before` / `after` names for guarded mutations and hash comparisons: `packages/capability-filesystem/src/filesystem-capability.ts`, `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py`, `tests/capabilities/filesystem.test.ts`.

**Types:**
- Use PascalCase for exported interfaces, classes, and type aliases: `RuntimeEngine`, `RuntimeEngineDependencies`, `CapabilityRegistry`, `CapabilityError`, `SqliteRunEventStore`.
- Use domain suffixes deliberately:
  - `*Input` for command/action inputs: `FilesystemWriteInput` in `packages/capability-filesystem/src/filesystem-capability.ts`, `ResolveApprovalInput` in `packages/runtime/src/wait-control.ts`.
  - `*Options` for constructor/factory configuration: `FilesystemCapabilityOptions`, `OpenAIResponsesAdapterOptions`, `SqliteRuntimeOptions`.
  - `*Payload` for event payload interfaces: `RunCreatedPayload`, `ActionCompletedPayload`, `WaitResolvedPayload` in `packages/core/src/events.ts`.
  - `*View`, `*Entry`, `*Summary`, and `*Assessment` for derived or explanatory surfaces, following `docs/contributing.md`.
- Do not introduce exported ontology-facing bare nouns unless they are canonical runtime concepts. `docs/contributing.md` reserves terms such as `Run`, `Command`, `Event`, `Action`, `Wait`, `Capability`, `Bundle`, and `View` for the ontology.

## Code Style

**Formatting:**
- No Prettier, ESLint, or Biome config is detected at repo root. Use the existing TypeScript formatting style.
- TypeScript uses two-space indentation, double quotes, semicolons, trailing commas only where TypeScript formatting already emits them, and multiline object literals for structured payloads. Examples: `packages/runtime/src/runtime-engine.ts`, `packages/capabilities/src/registry.ts`, `tests/capabilities/filesystem.test.ts`.
- Keep line length pragmatic. Long generic signatures and object literals are wrapped across lines, as in `createFilesystemHandlers()` in `packages/capability-filesystem/src/filesystem-capability.ts` and `validateModelCall()` imports in `packages/runtime/src/runtime-engine.ts`.
- Python uses four-space indentation, double quotes for strings in current worker code, standard-library imports before third-party imports, and type hints for public functions. Examples: `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py`, `python/openrund_documents_worker/openrund_documents_worker/jsonrpc.py`.
- Markdown docs and fixtures use fenced code blocks and concise headings; live contribution rules are in `docs/contributing.md`.

**Linting:**
- No ESLint/Prettier/Biome config is detected.
- Use TypeScript strict mode as the primary static quality gate. `tsconfig.base.json` sets `strict: true`, `module: "NodeNext"`, `moduleResolution: "NodeNext"`, `target: "ES2022"`, `composite: true`, and declaration output.
- Run `pnpm typecheck` before considering TypeScript changes complete. The command is defined in `package.json`.
- Run `pnpm hygiene` for repository-specific cleanliness and ontology checks. It executes `scripts/check-hygiene.mjs`, `scripts/check-ontology-canonical.mjs`, and `scripts/check-secondary-surface-names.mjs`.
- Run `pnpm package:check` after `pnpm build` when package content changes. The check lives in `scripts/check-package-content.mjs`.

## Import Organization

**Order:**
1. Node built-ins first, using `node:` specifiers: `import { createHash } from "node:crypto";`, `import { readFile } from "node:fs/promises";`.
2. Test framework imports next in test files: `import { describe, expect, it } from "vitest";`.
3. Workspace package imports next via `@openrund/*` aliases: `@openrund/core`, `@openrund/capabilities`, `@openrund/runtime`.
4. Relative module imports last with explicit `.js` extension for TypeScript source imports: `import { ActionDispatcher } from "./action-dispatcher.js";`.
5. Type-only imports use `import type` or inline `type` specifiers. Examples: `packages/runtime/src/runtime-engine.ts`, `packages/views/src/index.ts`, `packages/capability-filesystem/src/filesystem-capability.ts`.

**Path Aliases:**
- Use `@openrund/*` package aliases for cross-package imports. Aliases are configured in `tsconfig.base.json` and `vitest.config.ts`.
- Current aliases include `@openrund/core`, `@openrund/capabilities`, `@openrund/capability-filesystem`, `@openrund/capability-documents`, `@openrund/views`, `@openrund/runtime`, `@openrund/storage-sqlite`, `@openrund/provider-openai`, `@openrund/provider-anthropic`, `@openrund/provider-local`, `@openrund/providers`, `@openrund/storage`, and `@openrund/cli`.
- Use relative imports within a package and include `.js` in TypeScript source paths because the project uses NodeNext ESM: `packages/core/src/index.ts`, `packages/capabilities/src/index.ts`, `packages/runtime/src/runtime-engine.ts`.

## Error Handling

**Patterns:**
- Capability and controlled runtime failures should use structured `capabilityError()` from `packages/capabilities/src/errors.ts` with `category`, `message`, `retryable`, `component`, and optional IDs/evidence.
- Use `isCapabilityError()` in tests and callers when the exact message is less important than the structured error contract. Example: `tests/capabilities/filesystem.test.ts`.
- Keep capability error messages bounded. `packages/capabilities/src/errors.ts` caps messages, remediation, and nested causes.
- Use explicit domain error classes for storage conflicts where consumers need `instanceof`: `ExpectedPositionConflictError` and `DuplicateEventIDError` in `packages/storage-sqlite/src/sqlite-store.ts`.
- Use `throw new Error(...)` for internal invariant violations, programmer errors, and impossible runtime continuations. Examples: approval continuation invariants in `packages/runtime/src/runtime-engine.ts` and checkpoint range checks in `packages/runtime/src/checkpoint-control.ts`.
- Preserve unknown external errors unless mapping at a boundary. Helpers such as `readExistingHash()` and `exists()` in `packages/capability-filesystem/src/filesystem-capability.ts` catch `ENOENT` but rethrow other errors.
- Python worker domain conflicts use custom exceptions such as `DocumentConflict` in `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py`; JSON-RPC/server boundaries map worker failures to structured responses consumed by `packages/capability-documents/src/documents-client.ts`.

## Logging

**Framework:** console

**Patterns:**
- Runtime/library packages avoid ambient console logging. Return structured results, events, artifacts, and effects instead. Examples: `packages/runtime/src/runtime-engine.ts`, `packages/capabilities/src/dispatcher.ts`, `packages/views/src/index.ts`.
- CLI rendering is explicit and separated from runtime authority. `packages/cli/src/index.ts` returns `CliCommandResult`; `packages/cli/src/bin.ts` sets `process.exitCode` from rendered execution.
- Repository scripts log only pass/fail diagnostics and exit non-zero on violation: `scripts/check-hygiene.mjs`, `scripts/check-package-content.mjs`, `scripts/check-ontology-canonical.mjs`.
- Python stdio worker writes protocol responses to stdout and readiness/diagnostics to stderr, verified by `python/openrund_documents_worker/tests/test_jsonrpc.py`.

## Comments

**When to Comment:**
- Prefer descriptive names and explicit event/payload structures over comments.
- Add comments only for intentional contract boundaries or non-obvious policy behavior. Current source code uses sparse comments; follow that pattern.
- Tests use assertion messages sparingly where a loop needs context, such as docs link checks in `tests/docs/docs-links.test.ts`.

**JSDoc/TSDoc:**
- Not generally used. Public contracts are expressed through exported TypeScript interfaces/types and normative documentation under `docs/`.
- Keep API semantics in `docs/architecture.md`, `docs/concepts.md`, `docs/events.md`, `docs/capabilities.md`, and `docs/contributing.md` aligned with exported code.

## Function Design

**Size:** Keep helpers focused on one contract boundary or transformation. Larger orchestration methods exist in `packages/runtime/src/runtime-engine.ts`; new code should prefer small helpers like `createCapabilityRegistry()` in `packages/capabilities/src/registry.ts`, `completionGateFactsFromViews()` in `packages/runtime/src/check-control.ts`, and `reduceRunStatusView()` in `packages/views/src/run-status-view.ts`.

**Parameters:** Prefer a single typed input object for operations with multiple fields or long-lived API contracts. Examples: `RuntimeEngineDependencies` in `packages/runtime/src/runtime-engine.ts`, `FilesystemCapabilityOptions` and `FilesystemWriteInput` in `packages/capability-filesystem/src/filesystem-capability.ts`, `SqliteRuntimeOptions` in `packages/storage-sqlite/src/migrations.ts`.

**Return Values:** Return structured objects instead of booleans or free-form strings when results cross module boundaries. Examples: `CapabilityResult` from capability handlers, `CliCommandResult` from `packages/cli/src/index.ts`, `RunViewBundle` from `packages/views/src/index.ts`, and bundle verification results from `packages/runtime/src/orun.ts`.

## Module Design

**Exports:** 
- Package `src/index.ts` files are the public surface and primarily re-export implementation modules. Examples: `packages/core/src/index.ts`, `packages/capabilities/src/index.ts`, `packages/capability-documents/src/index.ts`.
- Keep package exports aligned with `package.json` `exports` fields and generated declarations. Example package manifests: `packages/runtime/package.json`, `packages/cli/package.json`, `packages/storage-sqlite/package.json`.
- Avoid exposing implementation-only helpers unless tests or public API require them. Internal helpers are file-local in `packages/capabilities/src/registry.ts`, `packages/capability-filesystem/src/filesystem-capability.ts`, and `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py`.

**Barrel Files:** 
- Use package-level barrels for public APIs, not deep import shortcuts across packages.
- Existing barrels re-export concrete modules with `.js` suffixes: `packages/capabilities/src/index.ts`, `packages/views/src/index.ts`, `packages/runtime/src/index.ts`.
- Public API tests in `tests/public-api/exports.test.ts` and `tests/public-api/ontology-guards.test.ts` protect the intended exported surface.

---

*Convention analysis: 2026-05-15*
