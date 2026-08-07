# External Integrations

**Analysis Date:** 2026-08-06

## Integration Posture

- OpenRund has no mandatory external service. The installed base package is dependency-free and the default local assembly operates with SQLite and the local filesystem.
- Every optional boundary is explicit: provider credentials enter constructors, storage receives a runtime-home path, filesystem access receives named mounts, and process/Git execution receives absolute executable bindings.
- Production provider code does not read ambient credentials, Capability children do not inherit the host environment, and the Engine remains the only authority boundary.
- There is no inbound server, REST API, webhook listener, browser client, GUI, hosted control plane, telemetry backend, or identity provider.

## APIs & External Services

**OpenAI Responses API:**
- `OpenAIResponsesProvider` in `src/openrund/providers/openai.py` sends model requests to `{base_url}/responses`; the default base is `https://api.openai.com/v1`.
  - SDK/Client: No vendor SDK. `StdlibHttpTransport` in `src/openrund/providers/_http.py` uses `asyncio`, TLS from `ssl`, bounded HTTP/1.1 response parsing, and SSE decoding.
  - Auth: Explicit `api_key` constructor argument rendered as `Authorization: Bearer ...`; production code never reads `OPENAI_API_KEY`.
  - Protocol: JSON response or `text/event-stream`, bounded by explicit timeout and response-byte limits.
  - Lifecycle: The provider owns and closes its transport when it creates it; callers can inject an `AsyncHttpTransport` for tests or alternate hosts.

**Anthropic Messages API:**
- `AnthropicMessagesProvider` in `src/openrund/providers/anthropic.py` sends model requests to `{base_url}/messages`; the default base is `https://api.anthropic.com/v1`.
  - SDK/Client: The same direct `StdlibHttpTransport`; no `anthropic` package dependency.
  - Auth: Explicit `api_key` constructor argument in `x-api-key`; `anthropic-version: 2023-06-01` is fixed by the adapter.
  - Protocol: JSON or Anthropic SSE message/content-block events with bounded parsing and safe normalized errors.

**Local OpenAI-compatible endpoint:**
- `LocalOpenAICompatibleProvider` in `src/openrund/providers/openai.py` targets a caller-supplied `base_url` and the `/responses` route for local model servers.
  - SDK/Client: Direct stdlib HTTP, identical normalization boundary to the OpenAI adapter.
  - Auth: None by default; the local provider passes no API key.
  - Configuration: Explicit `base_url`, model, and `LocalModelProfile`; no service discovery or ambient configuration.

**Provider extension point:**
- `ModelProvider` in `src/openrund/ports/providers.py` is the integration protocol consumed by `DurableRunLoop` in `src/openrund/runtime/_loop.py`.
- `LocalAssemblyConfig.provider` in `src/openrund/assembly/_model.py` injects a provider; `own_provider` controls whether the assembled runtime closes it.
- Provider adapters return proposals only. `tests/providers/test_hygiene.py` prevents imports of Event, Artifact, storage, or Capability custody so an external service cannot become a second authority path.

## HTTP Transport

- `src/openrund/providers/_http.py` is the only product network client surface detected.
- It accepts only `http` and `https`, rejects URL credentials and fragments, validates headers against injection, reserves framing headers, supports TLS, limits headers/body/events, and closes sockets/tasks explicitly.
- It opens one connection per request with `asyncio.open_connection`; no connection pool, proxy integration, retry middleware, DNS service discovery, or external cache is present.
- Provider failures expose stable safe codes rather than URLs, response bodies, credentials, or parser exceptions; see `docs/providers.md` and tests under `tests/providers/`.
- Normal tests use injected fake transports or a loopback test server in `tests/providers/test_http.py`; they do not call real providers.

## Data Storage

**SQLite:**
- Local SQLite is the authoritative default store for Events, Artifact metadata, and execution Leases.
  - Connection: A caller supplies `LocalAssemblyConfig.runtime_home`; the database is `<runtime_home>/runtime.sqlite` in `src/openrund/assembly/_model.py` and `src/openrund/assembly/_factory.py`.
  - Default: CLI custody defaults to `~/.openrund` through `default_openrund_home()` in `src/openrund/storage/_layout.py`; `--home PATH` overrides it.
  - Client: Python standard-library `sqlite3`; no ORM or external driver.
  - Schema/migrations: Private versioned schema and transactions in `src/openrund/storage/_database.py`; concrete stores are `src/openrund/storage/_events.py`, `src/openrund/storage/_artifacts.py`, and `src/openrund/storage/_leases.py`.
  - Concurrency: Configurable `busy_timeout_ms`, default 5,000 ms, passed through local assembly.
  - External database service: None. There is no connection URL, network database, or migration CLI.

**Artifact file storage:**
- `SqliteArtifactStore` in `src/openrund/storage/_artifacts.py` keeps metadata in SQLite and immutable blobs in `<runtime_home>/artifacts/`.
- Staging, blob, and orphan directories are local, symlink-aware, and published with absent-only/atomic semantics.
- There is no S3, GCS, Azure Blob, NFS, or remote Artifact adapter in the current assembly.

**Run homes:**
- `src/openrund/storage/_layout.py` defines `<root>/runs/<runID>/{runtime,workspace,exports}` and materializes it without following redirected path components.
- Run workspaces and exports are local custody, not a cloud storage integration.

**Portable `.orun` Bundles:**
- `src/openrund/bundles/` exports, verifies, replays, imports, and assesses immutable `.orun` directory trees on the local filesystem.
- Bundle paths, manifests, Event JSONL, Artifacts, capability manifests, audit exports, and action receipts are documented in `docs/bundles.md`.
- Bundles are a file interchange boundary, not a hosted service. Verification precedes replay/import; imports publish atomically beneath a supplied runtime home.

**Caching:**
- No runtime cache service or Redis/Memcached integration.
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, and uv caches are local development artifacts only and do not participate in runtime state.

## Local Capability Integrations

**Filesystem:**
- `FilesystemCapability` in `src/openrund/capabilities/filesystem.py` operates only through explicit `FilesystemMount` roots and the containment logic in `src/openrund/capabilities/_sandbox.py`.
- It is local-only; there is no remote filesystem or object-store adapter.

**Transported Documents worker:**
- `DocumentsCapability` in `src/openrund/capabilities/documents.py` launches the same Python interpreter as an absolute executable with `-m openrund.capabilities.documents_worker`.
- Transport: One-request stdio JSON-RPC through `StdioJsonRpcTransport` in `src/openrund/capabilities/_transports.py`.
- Environment: The parent constructs only `OPENRUND_DOCUMENT_ROOTS`, `OPENRUND_DOCUMENT_MAX_BYTES`, `OPENRUND_DOCUMENT_MAX_DIFF_BYTES`, `PYTHONUTF8`, and optional `PYTHONPATH` for source-tree execution.
- The worker in `src/openrund/capabilities/documents_worker.py` reads those internal variables, handles Markdown, and returns bounded structured results. It receives no ambient credentials or host configuration.
- This subprocess boundary is necessary evidence that rich document work stays outside the in-process runtime core while remaining in the same distribution.

**Bound process execution:**
- `ProcessCapability` and `ProcessBinding` in `src/openrund/capabilities/process.py` execute only configured absolute regular executables whose identity is checked before launch.
- Child environments begin from explicit fixed values plus narrowly allowlisted caller-selectable values; host `PATH`, provider keys, and other ambient variables are not inherited.
- stdin/stdout/stderr, timeouts, byte bounds, digests, cancellation, and process reaping are governed locally.
- There is no shell execution, container runtime, SSH, job scheduler, or arbitrary command lookup.

**Local Git executable:**
- `GitCapability` in `src/openrund/capabilities/git.py` wraps a caller-supplied absolute Git executable and explicit `GitIdentity` values.
- Operations are restricted to verified repositories beneath configured mounts. The Capability permits local status/diff/stage/commit-style work but intentionally excludes remote, fetch, pull, push, submodule, credential, and unsafe config behavior; see `docs/capabilities.md`.
- Git child configuration disables or rejects credential helpers, hooks, aliases, pagers, filters, includes, proxy/SSH commands, and other executable configuration surfaces.
- `create_local_runtime()` in `src/openrund/assembly/_factory.py` registers Git only when both executable and identities are supplied.

**Governed-coding demonstration:**
- `src/openrund/demo.py` and `examples/governed_coding.py` discover/use a local Git executable and local Python process to prove the Capability boundaries.
- The demo requires no provider, network call, or credentials and writes into explicit local runtime/workspace roots.

## Authentication & Identity

**Application auth provider:**
- None. OpenRund is a local library/CLI and exposes no multi-user HTTP service, login, session, cookie, JWT, OAuth, or identity database.

**Provider credentials:**
- OpenAI and Anthropic credentials are explicit in-memory constructor arguments.
- Production source does not inspect ambient credential variables; this is enforced by `tests/providers/test_hygiene.py` and `tests/package/test_release_hygiene.py`.
- Safe runtime errors do not contain raw credentials or provider response bodies.

**Git identity:**
- Explicit `GitIdentity(name, author_name, author_email)` values are configuration for local commit authorship, not user authentication.

**Runtime authority:**
- Capability Authority, policy rules, Wait approval, and Delegation contracts are durable runtime concepts enforced by the Engine. They are not delegated to an external identity provider.

## Monitoring & Observability

**Error tracking:**
- No Sentry, Datadog, OpenTelemetry exporter, cloud error tracker, or analytics SDK.

**Logs and reporting:**
- `Reporter` in `src/openrund/ports/runtime.py` is an injectable async reporting protocol.
- `NullReporter` in `src/openrund/assembly/_operator.py` is the default, so local assembly has no implicit telemetry.
- `ReportingEventStore` in `src/openrund/assembly/_events.py` emits compact post-commit `ReportEntry` values to the injected reporter.
- The installed command writes rendered success output to stdout and failure output to stderr in `src/openrund/__main__.py`; it does not configure Python `logging` or an external sink.
- Durable inspection comes from Events, Views, Artifacts, receipts, checks, and `.orun` exports rather than an observability vendor.

## CI/CD & Deployment

**Hosting:**
- None. OpenRund is a pure-Python library and installed console command, not a deployed web service.

**Distribution:**
- Hatchling builds a pure-Python wheel and source distribution from `pyproject.toml`.
- `tests/package/test_py_typed.py` validates exact wheel/sdist contents; `tests/package/test_installed_typing.py` installs and probes the wheel in isolation.
- `README.md` documents `python -m pip install openrund`, implying standard Python package-index distribution, but no publishing service or release-upload configuration is tracked.

**CI Pipeline:**
- No `.github/workflows/`, GitLab CI, CircleCI, Buildkite, Jenkins, tox, or nox configuration is present.
- Release gates are documented local uv commands in `README.md` and `docs/contributing.md`: tests/coverage, strict mypy, Ruff lint/format, lock check, build, and Git whitespace checks.
- Absence of CI is not redundant configuration; it means enforcement currently depends on the release operator running the documented commands.

## Environment Configuration

**Normal development and production:**
- Required environment variables: None for the base runtime, CLI, SQLite custody, filesystem operations, or deterministic example.
- Provider secrets: Passed explicitly to constructors by the embedding application; there is no `.env` loader or tracked `.env.example`.
- Runtime location: Explicit `LocalAssemblyConfig.runtime_home` or CLI `--home`; defaults to `~/.openrund`.
- Capability roots/executables: Explicit Python objects in `LocalAssemblyConfig`, not environment discovery.

**Internal Documents worker variables:**
- `OPENRUND_DOCUMENT_ROOTS` - Encoded allowed mounts constructed by `DocumentsCapability`.
- `OPENRUND_DOCUMENT_MAX_BYTES` - Parent-supplied document byte limit.
- `OPENRUND_DOCUMENT_MAX_DIFF_BYTES` - Parent-supplied diff byte limit.
- These variables are an internal one-process transport contract, not operator secrets or global application configuration.

**Optional live-provider test environment:**
- `OPENRUND_LIVE_OPENAI_API_KEY`
- `OPENRUND_LIVE_OPENAI_MODEL`
- `OPENRUND_LIVE_LOCAL_BASE_URL`
- `OPENRUND_LIVE_LOCAL_MODEL`
- `OPENRUND_LIVE_ANTHROPIC_API_KEY`
- `OPENRUND_LIVE_ANTHROPIC_MODEL`
- Only `tests/providers/test_live.py` reads these names. Tests carry the `live_provider` marker and skip unless configuration is explicitly supplied; normal tests remain deterministic and offline.

**Staging/production profiles:**
- Not detected. No environment-specific config files, secret manager, cloud account, failover service, or deployment tier is defined.

## Webhooks & Callbacks

**Incoming:**
- None. The package does not bind a listening HTTP port or expose callback endpoints.

**Outgoing:**
- No webhooks. Optional outbound traffic is limited to caller-invoked model-provider HTTP requests.

**In-process callbacks:**
- Reporter, Clock, ID factories, provider protocols, Capability handlers, and Operator input are injected Python protocols/callables. These are extension points inside the host process, not network callbacks.

## Integration File Necessity Audit

| Files | Integration role | Necessity / simplification assessment |
|---|---|---|
| `src/openrund/providers/_http.py` | Shared bounded HTTP/SSE transport | Necessary to keep provider adapters dependency-free. A vendor SDK or second HTTP client would duplicate this boundary. |
| `src/openrund/providers/openai.py` | OpenAI Responses and local OpenAI-compatible adapters | Necessary optional adapters sharing one normalization/wire path. Keep local and hosted classes together while both use `/responses`. |
| `src/openrund/providers/anthropic.py` | Anthropic Messages adapter | Necessary because its request/stream protocol differs materially from OpenAI. |
| `src/openrund/providers/_normalization.py` | Provider-neutral tool/text normalization | Necessary to prevent provider-specific proposals from leaking into runtime semantics. |
| `src/openrund/ports/providers.py` | Host/provider protocol boundary | Necessary inversion point for fake, local, and remote providers. |
| `src/openrund/runtime/_loop.py` | Provider-to-Engine proposal loop | Necessary; hygiene tests ensure it does not append Events or import storage directly. |
| `src/openrund/storage/_database.py` | Shared SQLite migration/transaction boundary | Necessary centralization; do not create per-store connection implementations. |
| `src/openrund/storage/_events.py`, `_artifacts.py`, `_leases.py` | Concrete local custody | Necessary distinct store responsibilities over the same SQLite lifecycle. |
| `src/openrund/storage/_layout.py` | Default home and Run path layout | Necessary host convention kept separate from authority/configuration. |
| `src/openrund/assembly/_model.py`, `_factory.py` | Explicit integration composition root | Necessary single place to wire storage, providers, Capabilities, Engine, and Operator. |
| `src/openrund/capabilities/_transports.py` | In-process and stdio JSON-RPC transport | Necessary shared framing/lifetime layer; keep protocol code out of individual Capabilities. |
| `src/openrund/capabilities/documents.py`, `documents_worker.py` | Transported Markdown integration | Both are necessary halves of the subprocess boundary; merging them would erase the transport proof. |
| `src/openrund/capabilities/process.py` | Explicit executable integration | Necessary governed process boundary; no generic shell wrapper should be added. |
| `src/openrund/capabilities/git.py` | Restricted local Git integration | Necessary for governed Git work and intentionally local-only; remote Git features would be a new integration, not a simplification. |
| `src/openrund/bundles/` | Local portable interchange | Necessary for cross-run portability and recovery; it is not redundant with live SQLite custody. |
| `tests/providers/` | Fake, loopback, normalization, hygiene, and opt-in live checks | Necessary to separate deterministic protocol verification from explicit external drift checks. |
| `docs/providers.md`, `docs/storage.md`, `docs/capabilities.md`, `docs/bundles.md` | Normative external-boundary contracts | Necessary planning/consumer references; paths correspond directly to the implementation boundaries above. |

## Safe Simplification Guidance

- Keep provider credentials explicit. Adding an environment loader would create a second configuration path and weaken the tested no-ambient-credential contract.
- Keep one shared stdlib HTTP transport. Do not add `requests`, `httpx`, OpenAI, or Anthropic SDKs unless a missing protocol requirement justifies the runtime dependency and duplicate lifecycle surface.
- Keep SQLite and Artifact blobs local in the default assembly. Remote database/object-store adapters, if ever added, should implement ports and remain optional rather than changing the dependency-free base.
- Keep the Documents worker environment private and narrowly enumerated; it is the only production environment-variable surface and is generated by its parent.
- Keep Git local-only unless remote operations are explicitly designed with credential, network, and authority semantics. Current config hardening deliberately excludes them.
- No cache, auth provider, webhook, analytics, or monitoring integration exists to remove. Avoid adding placeholders or configuration for services that are not implemented.
- Normal provider tests should remain fake/loopback and offline; isolate real-service drift checks behind the existing marker and explicit `OPENRUND_LIVE_*` variables.

---

*Integration audit: 2026-08-06*
*Update when adding/removing providers, storage adapters, process boundaries, CI, or hosted services*
