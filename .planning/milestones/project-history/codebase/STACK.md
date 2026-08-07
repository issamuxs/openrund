# Technology Stack

**Analysis Date:** 2026-05-15

## Languages

**Primary:**
- TypeScript 5.9.x - Core runtime, packages, CLI, model providers, capabilities, views, storage, examples, and tests under `packages/`, `examples/`, and `tests/`; configured by `tsconfig.base.json` and per-package `packages/*/tsconfig.json`.

**Secondary:**
- Python >=3.9 - Transported documents worker under `python/openrund_documents_worker/`, configured by `python/openrund_documents_worker/pyproject.toml`.
- Markdown - Normative runtime documentation in `docs/` and example documentation in `examples/governed-coding-run/README.md`.

## Runtime

**Environment:**
- Node.js >=24.0.0 - Required by `package.json`; used for ESM packages, built-in `fetch`, built-in `node:sqlite`, CLI execution, filesystem/process/git capabilities, and tests.
- Python >=3.9 - Required by `python/openrund_documents_worker/pyproject.toml` for the stdio JSON-RPC documents worker.

**Package Manager:**
- pnpm 10.33.3 - Declared in `package.json` as `packageManager`.
- Lockfile: present at `pnpm-lock.yaml`.
- Workspace: `pnpm-workspace.yaml` includes `packages/*`.

## Frameworks

**Core:**
- TypeScript project references - `package.json` builds each package with `tsc -b`; package outputs are `dist/index.js` and `dist/index.d.ts` per `packages/*/package.json`.
- Node ESM - Root and packages set `"type": "module"` in `package.json` and `packages/*/package.json`; TypeScript uses `module: "NodeNext"` in `tsconfig.base.json`.
- OpenRund runtime packages - Workspace packages include `@openrund/core`, `@openrund/runtime`, `@openrund/capabilities`, `@openrund/views`, `@openrund/storage`, provider packages, and capability packages under `packages/`.

**Testing:**
- Vitest ^4.0.7 - Node test runner configured by `vitest.config.ts`; tests live under `tests/**/*.test.ts`.
- pytest >=8.0.0 - Optional Python test dependency in `python/openrund_documents_worker/pyproject.toml`; Python tests live under `python/openrund_documents_worker/tests/`.

**Build/Dev:**
- TypeScript ^5.9.3 - Build and typecheck tool declared in `package.json`.
- Node `--experimental-strip-types` - Used by `package.json` demo script `demo:governed-coding-run` to run `examples/governed-coding-run/run.ts`.
- Custom hygiene scripts - `package.json` defines `hygiene` via `scripts/check-hygiene.mjs` and `package:check` via `scripts/check-package-content.mjs`.

## Key Dependencies

**Critical:**
- `@openrund/core` workspace package - Canonical runtime types, event contracts, IDs, model operations, and storage interfaces under `packages/core/`.
- `@openrund/runtime` workspace package - Engine, command legality evaluation, waits, action lifecycle, delegation, checkpointing, bundle operations, and local runtime assembly under `packages/runtime/`.
- `@openrund/capabilities` workspace package - Capability definitions, schema helpers, dispatcher contracts, errors, and stdio JSON-RPC transport under `packages/capabilities/`.
- `@openrund/storage-sqlite` workspace package - SQLite event, artifact, and lease stores under `packages/storage-sqlite/`.
- `@openrund/provider-openai`, `@openrund/provider-anthropic`, `@openrund/provider-local` workspace packages - Model API adapters under `packages/provider-openai/`, `packages/provider-anthropic/`, and `packages/provider-local/`.
- `zod` ^4.1.12 - Capability schema construction and validation in `packages/capabilities/src/schema.ts` and capability definitions such as `packages/capability-filesystem/src/definition.ts`.

**Infrastructure:**
- Node built-in `node:sqlite` - Synchronous SQLite database access in `packages/storage-sqlite/src/migrations.ts`, `packages/storage-sqlite/src/sqlite-store.ts`, `packages/storage-sqlite/src/sqlite-artifact-store.ts`, and `packages/storage-sqlite/src/sqlite-lease-store.ts`.
- Node built-in `fetch` - HTTP transport for provider adapters in `packages/provider-openai/src/openai-adapter.ts`, `packages/provider-anthropic/src/anthropic-adapter.ts`, and `packages/provider-local/src/local-openai-compatible-adapter.ts`.
- Node built-in `child_process` - Process capability in `packages/capability-process/src/process-capability.ts`, git capability in `packages/capability-git/src/git-capability.ts`, and stdio worker transport in `packages/capabilities/src/transports/stdio-json-rpc.ts`.
- Python `markdown-it-py` >=3.0.0 - Markdown parsing for the documents worker in `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py`.
- Python `python-frontmatter` >=1.1.0 - Frontmatter handling for the documents worker in `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py`.
- Python `mdformat` >=0.7.17 - Markdown formatting for the documents worker in `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py`.

## Configuration

**Environment:**
- `OPENRUND_HOME` overrides the default runtime home in `packages/cli/src/index.ts`; default home is `~/.openrund` from `packages/runtime/src/workspace-root.ts`.
- `OPENAI_API_KEY` is read by `packages/provider-openai/src/openai-adapter.ts` when an adapter option `apiKey` is not provided.
- `ANTHROPIC_API_KEY` is read by `packages/provider-anthropic/src/anthropic-adapter.ts` when an adapter option `apiKey` is not provided.
- No `.env`, `.env.*`, or `*.env` files detected in the repo root scan; do not add secrets to tracked files.

**Build:**
- Root build/typecheck entrypoint: `package.json`.
- Workspace package list: `pnpm-workspace.yaml`.
- TypeScript base config: `tsconfig.base.json`.
- Per-package TypeScript configs: `packages/*/tsconfig.json`.
- Vitest config and path aliases: `vitest.config.ts`.
- Python worker packaging and pytest config: `python/openrund_documents_worker/pyproject.toml`.

## Platform Requirements

**Development:**
- Install dependencies with `pnpm install` from `package.json` and `pnpm-lock.yaml`.
- Use Node >=24 because `packages/storage-sqlite/src/migrations.ts` imports `node:sqlite` and provider adapters rely on global `fetch`.
- Use Python >=3.9 for `python/openrund_documents_worker/`.
- Use `git` on PATH for `packages/capability-git/src/git-capability.ts`.

**Production:**
- Deployment target not detected; there is no Dockerfile, `.github/` workflow, hosting config, or cloud deployment manifest in the scanned repo.
- Current runtime shape is local library/CLI execution using `@openrund/cli` in `packages/cli/`, SQLite files under `OPENRUND_HOME`/`~/.openrund`, and optional HTTP model provider adapters.

---

*Stack analysis: 2026-05-15*
