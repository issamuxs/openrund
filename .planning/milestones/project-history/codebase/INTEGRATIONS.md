# External Integrations

**Analysis Date:** 2026-05-15

## APIs & External Services

**Model Providers:**
- OpenAI Responses API - Model transport and response parsing through `OpenAIResponsesAdapter` in `packages/provider-openai/src/openai-adapter.ts`.
  - SDK/Client: Native `fetch`; no OpenAI SDK dependency is declared in `package.json` or `packages/provider-openai/package.json`.
  - Endpoint: `https://api.openai.com/v1/responses` by default, overrideable with `baseURL` in `OpenAIResponsesAdapterOptions`.
  - Auth: `OPENAI_API_KEY` env var or explicit `apiKey` option in `packages/provider-openai/src/openai-adapter.ts`.
- Anthropic Messages API - Model transport and response parsing through `AnthropicMessagesAdapter` in `packages/provider-anthropic/src/anthropic-adapter.ts`.
  - SDK/Client: Native `fetch`; no Anthropic SDK dependency is declared in `package.json` or `packages/provider-anthropic/package.json`.
  - Endpoint: `https://api.anthropic.com/v1/messages` by default, overrideable with `baseURL` in `AnthropicAdapterOptions`.
  - Auth: `ANTHROPIC_API_KEY` env var or explicit `apiKey` option in `packages/provider-anthropic/src/anthropic-adapter.ts`.
- Local OpenAI-compatible API - Local model transport through `LocalOpenAICompatibleAdapter` in `packages/provider-local/src/local-openai-compatible-adapter.ts`.
  - SDK/Client: Native `fetch`.
  - Endpoint: caller-provided `baseURL` plus `/responses`.
  - Auth: explicit `apiKey` option or default bearer token value `local` in `packages/provider-local/src/local-openai-compatible-adapter.ts`.

**Worker Transports:**
- Python documents worker - Capability transport over stdio JSON-RPC from TypeScript to Python.
  - SDK/Client: `callStdioJsonRpc` in `packages/capabilities/src/transports/stdio-json-rpc.ts`.
  - Worker: `python/openrund_documents_worker/openrund_documents_worker/server.py`.
  - Methods: `documents.read`, `documents.write`, `documents.patch`, frontmatter methods, and section methods in `python/openrund_documents_worker/openrund_documents_worker/server.py`.
  - Auth: None; process execution is controlled by capability authority and transport options, not an external auth provider.

**Local System Capabilities:**
- Filesystem capability - Governed local file access under authorized mounts in `packages/capability-filesystem/src/filesystem-capability.ts` and `packages/capability-filesystem/src/path-sandbox.ts`.
  - SDK/Client: Node `fs/promises`.
  - Auth: Runtime authority grants and path sandbox checks, not external credentials.
- Process capability - Governed local subprocess execution in `packages/capability-process/src/process-capability.ts`.
  - SDK/Client: Node `child_process.spawn`.
  - Auth: Runtime authority grants and capability policy; environment input is constrained by capability input schema in `packages/capability-process/src/definition.ts`.
- Git capability - Local git patch/stage/commit operations in `packages/capability-git/src/git-capability.ts`.
  - SDK/Client: `git` CLI via Node `child_process.spawn`.
  - Auth: Runtime authority grants and repository sandboxing; excluded operations include `push`, `fetch`, `pull`, `remote`, and `credential` in `packages/capability-git/src/definition.ts`.

## Data Storage

**Databases:**
- SQLite via Node built-in `node:sqlite`.
  - Connection: file paths supplied through `SqliteRuntimeOptions.databasePath` in `packages/storage-sqlite/src/migrations.ts`.
  - Default runtime database: `runtime.sqlite` under `runtimeHome` from `packages/storage/src/index.ts`.
  - Default artifact database: `artifacts.sqlite` under `runtimeHome` from `packages/storage/src/index.ts`.
  - CLI default database: `OPENRUND_HOME` or `~/.openrund`, then `runtime.sqlite`, in `packages/cli/src/index.ts`.
  - Client: `SqliteRunEventStore`, `SqliteArtifactStore`, and `SqliteExecutionLeaseStore` in `packages/storage-sqlite/`.
  - Schema: `run_events`, `execution_leases`, and `artifacts` tables created in `packages/storage-sqlite/src/migrations.ts`.

**File Storage:**
- Local filesystem only.
  - Runtime home and run directories are resolved by `packages/runtime/src/workspace-root.ts`.
  - Artifact blobs can be written under runtime custody by `packages/storage-sqlite/src/sqlite-artifact-store.ts`.
  - Bundle export writes `.orun` directories through runtime bundle APIs documented in `docs/storage.md` and implemented under `packages/runtime/src/orun.ts`.

**Caching:**
- No external cache detected.
- SQLite enables WAL and `busy_timeout` pragmas in `packages/storage-sqlite/src/migrations.ts`.
- Views are derived from events and artifacts through `@openrund/views` in `packages/views/`; `docs/storage.md` says caches must be discardable and rebuildable.

## Authentication & Identity

**Auth Provider:**
- No application auth provider detected.
  - Runtime authority is internal engine state, not identity-provider auth, as documented in `docs/capabilities.md`, `docs/providers.md`, and implemented by `packages/runtime/`.
  - Provider API keys are read at adapter boundaries in `packages/provider-openai/src/openai-adapter.ts` and `packages/provider-anthropic/src/anthropic-adapter.ts`.
  - Local CLI commands in `packages/cli/src/index.ts` do not authenticate users; they operate on local runtime storage selected by `OPENRUND_HOME` or defaults.

## Monitoring & Observability

**Error Tracking:**
- None detected; no Sentry, OpenTelemetry, Datadog, or similar package appears in `package.json`, `packages/*/package.json`, or Python `pyproject.toml`.

**Logs:**
- CLI returns structured command results and deterministic rendered terminal output through `executeCli`, `renderCliResult`, and `runCli` in `packages/cli/src/index.ts`.
- Provider HTTP errors include status and a bounded response body preview in `packages/provider-openai/src/openai-adapter.ts`, `packages/provider-anthropic/src/anthropic-adapter.ts`, and `packages/provider-local/src/local-openai-compatible-adapter.ts`.
- Stdio worker transport captures stderr as bounded remediation context in `packages/capabilities/src/transports/stdio-json-rpc.ts`.
- Python documents worker writes readiness text to stderr in `python/openrund_documents_worker/openrund_documents_worker/server.py`.

## CI/CD & Deployment

**Hosting:**
- Not detected; no Dockerfile, deployment manifest, or hosting-specific config was found in the repo scan.

**CI Pipeline:**
- None detected; no `.github/` workflow files were found.
- Verification commands are local scripts in `package.json`: `pnpm build`, `pnpm typecheck`, `pnpm test`, `pnpm hygiene`, and `pnpm package:check`.

## Environment Configuration

**Required env vars:**
- `OPENAI_API_KEY` - Needed only when using `OpenAIResponsesAdapter` without an explicit `apiKey`, in `packages/provider-openai/src/openai-adapter.ts`.
- `ANTHROPIC_API_KEY` - Needed only when using `AnthropicMessagesAdapter` without an explicit `apiKey`, in `packages/provider-anthropic/src/anthropic-adapter.ts`.
- `OPENRUND_HOME` - Optional override for local CLI runtime storage in `packages/cli/src/index.ts`.

**Secrets location:**
- Not detected in repository; no `.env`, `.env.*`, or `*.env` files were present during the scan.
- Store provider keys outside tracked files and pass them through the environment or explicit adapter options.

## Webhooks & Callbacks

**Incoming:**
- None detected; there is no HTTP server framework, route layer, webhook endpoint, or listener package in `packages/`, `examples/`, or root manifests.
- Runtime APIs expose control methods such as approval resolution, interaction resolution, timers, checks, reconciliation, and bundle operations in `docs/api.md` and `packages/runtime/`, but these are TypeScript APIs rather than network callbacks.

**Outgoing:**
- OpenAI and Anthropic provider HTTP calls through native `fetch` in `packages/provider-openai/src/openai-adapter.ts` and `packages/provider-anthropic/src/anthropic-adapter.ts`.
- Local OpenAI-compatible HTTP calls through native `fetch` in `packages/provider-local/src/local-openai-compatible-adapter.ts`.
- Local subprocess calls for process, git, and stdio JSON-RPC worker integration in `packages/capability-process/src/process-capability.ts`, `packages/capability-git/src/git-capability.ts`, and `packages/capabilities/src/transports/stdio-json-rpc.ts`.

---

*Integration audit: 2026-05-15*
