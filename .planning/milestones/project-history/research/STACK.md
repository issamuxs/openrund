# Technology Stack

**Project:** OpenRund — complete idiomatic Python reimplementation
**Researched:** 2026-08-04
**Overall confidence:** MEDIUM

## Recommendation

Ship OpenRund as one pure-Python distribution named `openrund`, requiring Python 3.12 or newer. Keep the authority-bearing core on the standard library: frozen dataclasses and explicit codecs for runtime objects, `asyncio` for orchestration, `sqlite3` for durable local state, `argparse` for the CLI, `json` plus `asyncio.subprocess` for transported workers, and `pathlib`/`hashlib` for directory-based `.orun` bundles and immutable artifacts.

Add only two required runtime dependencies: `jsonschema` for strict validation at untrusted boundaries and `httpx` for provider HTTP/SSE. Keep Markdown document support behind a `documents` extra. Use Hatchling as the build backend and uv as the contributor workflow and lockfile tool; neither is imported by the runtime.

This is intentionally not a one-for-one port of the TypeScript package graph. Preserve the normative event names, JSON field names, `CommandDecision` semantics, persistence rules, capability/provider contracts, and `.orun` formats, while reorganizing implementation code around deep Python modules.

## Supported Runtime Baseline

| Decision | Recommendation | Rationale |
|---|---|---|
| Python requirement | `requires-python = ">=3.12"` | Python 3.12 is supported through October 2028 and supplies the modern `sqlite3.Connection.autocommit` API. It also includes `asyncio.TaskGroup` and `asyncio.timeout`, introduced in 3.11. |
| Current development version | CPython 3.14.6 | Current stable CPython release as of the research date. |
| Required CI matrix | 3.12.13, 3.13.14, and 3.14.6 as of research; always use the latest patch in each minor line | Proves the declared floor and current interpreters without multiplying local compatibility branches. |
| Python 3.15 | Optional allowed-failure prerelease job only | It is prerelease software until October 2026 and must not gate the MVP. |
| Free-threaded CPython | Not a release gate | Python 3.14 supports free-threading, but OpenRund should first validate dependency and SQLite ownership behavior explicitly; normal GIL builds are the supported MVP. |
| SQLite requirement | SQLite 3.24.0 or newer, checked at startup | Existing storage SQL depends on UPSERT, added in SQLite 3.24. Python can be compiled against different SQLite versions, so checking `sqlite3.sqlite_version_info` is more reliable than assuming a CPython-bundled version. |

Do not add an upper Python bound. Test new stable CPython releases before adding them to the required matrix, and never rely on syntax or stdlib behavior newer than 3.12 in shipped code.

## Recommended Stack

### Packaging and Distribution

| Technology | Version | Purpose | Why |
|---|---:|---|---|
| PEP 517/518 and PEP 621 `pyproject.toml` | Current standards | Build isolation and distribution metadata | Standard metadata keeps installation frontend-neutral and avoids tool-specific package declarations. |
| Hatchling | 1.31.0 | Pure-Python wheel and sdist backend | Small, standards-based backend with no runtime coupling. Pin it in `[build-system]` for reproducible isolated builds. |
| uv | 0.11.29 | Environments, dependency groups, lockfile, build, and publish workflow | One fast contributor tool can resolve all supported Python versions, maintain a universal lock, run commands, and build standard artifacts. It remains a development tool, not a runtime dependency. |
| `src/` layout | N/A | Import isolation | Prevents tests from accidentally importing the repository tree instead of the installed package. |
| PEP 735 dependency groups | Current standard | Test, quality, and docs dependencies | Keeps contributor-only tools out of wheel metadata. |

Use one distribution and one import root:

```text
src/openrund/
├── core/          # ontology, immutable values, explicit wire codecs
├── engine/        # legality, CommandDecision, dispatch, terminality
├── views/         # deterministic event reducers
├── storage/       # ports plus SQLite/filesystem adapters and migrations
├── capabilities/  # contracts, registry, policy, transports, built-ins
├── providers/     # provider ports and HTTP adapters
├── bundles/       # .orun export/import/verify/replay/resume assessment
└── cli/           # parser, handlers, renderers, process exit mapping
```

These are internal cohesion boundaries, not independently published packages. Export only the supported SDK surface from `openrund`; keep engine internals and wire implementation details private.

Recommended metadata skeleton:

```toml
[build-system]
requires = ["hatchling==1.31.0"]
build-backend = "hatchling.build"

[project]
name = "openrund"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.28.1,<1",
  "jsonschema>=4.26,<5",
]

[project.optional-dependencies]
documents = [
  "markdown-it-py>=4.2,<5",
  "python-frontmatter>=1.3,<2",
  "mdformat>=1.0,<2",
]

[project.scripts]
openrund = "openrund.cli:main"
openrund-documents-worker = "openrund.capabilities.documents.worker:main"
```

Keep a checked-in `uv.lock` that resolves for Python 3.12–3.14. Published libraries should use compatible direct-dependency ranges as above; contributor and CI environments should use exact versions from the lock. Build release artifacts with `uv build --no-sources`, then install the wheel into a clean environment and smoke-test the CLI and public imports. This prevents workspace/source references from masking broken distributions.

### Runtime Type and Schema Strategy

| Layer | Technology | Rule |
|---|---|---|
| Domain values and events | `dataclasses.dataclass(frozen=True, slots=True)`, `enum.StrEnum`, `typing.Protocol`, `Literal` | Model runtime facts as immutable values. Protocols define ports without base-class coupling. |
| Boundary-shaped static types | `TypedDict` sparingly | Use only where a dictionary is genuinely the wire shape, not as the domain model. |
| Wire conversion | Explicit per-type codecs using stdlib `json` | Keep Python attribute names separate from frozen JSON names such as `runID`; reject unknown fields and wrong primitive types explicitly. |
| JSON Schema validation | `jsonschema` 4.26.0, Draft 2020-12 | Validate capability inputs/results, provider parsed output, manifests, and other untrusted envelopes. Compile validated schemas when registering them, not on every call. |
| Static checking | mypy 2.3.0 in strict mode | Enforce complete annotations across `src/` and tests, including no implicit optional values and no untyped definitions. |

The engine must not use framework-generated serializers for canonical records. Central codecs should encode JSON with explicit, stable settings such as `ensure_ascii=False`, `allow_nan=False`, deterministic key ordering where canonical bytes are required, and compact separators. Timestamps, identifiers, enum values, optional fields, and omission-versus-null rules must be copied from existing compatibility fixtures rather than inferred from Python conventions.

For schemas:

- Call `Draft202012Validator.check_schema()` once when a schema enters the registry, then retain the validator.
- Forbid network resolution and uncontrolled remote `$ref`; bundle all authoritative schemas and resolve by stable local identifiers.
- Use `iter_errors()` and normalize/sort paths before returning diagnostics so error ordering is deterministic.
- Enable format checking only for formats OpenRund explicitly commits to; JSON Schema formats are otherwise annotations.
- Schema success never authorizes an operation. It only establishes shape before the engine evaluates legality and emits an authoritative decision.

Do not add Pydantic, attrs, or msgspec to the authority-bearing core. Their coercion, alias, default, and serialization conventions would create a second semantic system around the existing wire contract. Plain dataclasses plus explicit codecs are smaller and make compatibility decisions reviewable.

### Async and Concurrency

Use stdlib `asyncio` directly.

- Provider calls, transported capability calls, waits, worker supervision, and the engine run loop are async.
- Event reducers, legality evaluation, codecs, policy evaluation, and `CommandDecision` construction remain synchronous and deterministic.
- Use `asyncio.TaskGroup` for owned concurrent work and `asyncio.timeout` for bounded operations.
- Treat cancellation as control flow: clean up owned resources and re-raise `CancelledError`; never turn it into an ordinary provider or capability result.
- Do not create unreferenced background tasks. Every task belongs to a run, transport, or host lifecycle and is awaited during shutdown.
- Do not hold a SQLite transaction or thread lock across `await`.
- External side effects remain serialized by engine authority, expected positions, leases, and recorded decisions—not by ad hoc `asyncio.Lock` calls that bypass the event model.

Short local SQLite operations can remain synchronous at the storage boundary for the MVP. If measurement shows meaningful event-loop stalls, move an entire storage operation—not individual statements—onto an adapter-owned single-thread executor with a connection created and used in that thread. Do not introduce `aiosqlite` merely to hide synchronous calls: its per-connection worker thread and request queue obscure transaction ownership without changing SQLite's single-writer constraint.

Do not depend directly on AnyIO or support multiple async backends. HTTPX may use AnyIO internally, but OpenRund's public lifecycle and cancellation contract should be `asyncio`-native.

### SQLite Persistence

Use the stdlib `sqlite3` module. Do not add SQLAlchemy, Alembic, or another ORM/migration layer.

Each opened database must explicitly configure and verify:

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = FULL;
```

`FULL` is the correct durability default for an authoritative event history. `NORMAL` improves write throughput but can lose the most recent committed WAL transaction after power loss, which conflicts with OpenRund's durability claim.

Use `sqlite3.connect(..., autocommit=True)` on Python 3.12+ and delimit mutations with explicit SQL `BEGIN IMMEDIATE`, `COMMIT`, and `ROLLBACK`. This avoids the changing legacy transaction-control default and acquires the sole writer before calculating and appending the next position. Keep `check_same_thread=True`, make connection ownership explicit, and never share a connection across arbitrary async tasks or threads.

Storage rules:

- Preserve unique `(run_id, position)` and event identity constraints in SQL as well as in the engine.
- Use a short, deliberate transaction for each store's atomic mutation; derived views remain replayable projections rather than a second authority.
- Use versioned embedded SQL migrations plus `PRAGMA user_version`; an MVP does not need a general migration framework.
- Keep large artifact bytes in the immutable artifact store and store compact references in events.
- Use SQLite backup and integrity-check APIs for maintenance and export verification.
- WAL requires all processes to share a local host filesystem; reject or clearly warn on unsupported network filesystems and if `PRAGMA journal_mode` does not return `wal`.
- Bound readers and checkpoint during maintenance/bundle boundaries so long-lived read transactions cannot starve WAL checkpoints.

### CLI

Use stdlib `argparse`, not Typer/Click/Rich. The current nested command surface maps directly to subparsers, and a thin deterministic CLI benefits more from explicit control than decorator ergonomics.

Implement `main(argv: Sequence[str] | None = None, runtime_factory: RuntimeFactory = ...) -> int`. Parsing should be pure, command handlers should return structured results, and a separate renderer should produce stable plain text or JSON. Set `allow_abbrev=False`, define explicit exit-code meanings, avoid terminal-width-dependent output, and inject clocks, stores, providers, and streams in tests. Do not rely on Python 3.14-only `argparse` color or suggestion behavior while Python 3.12 is supported.

### Provider HTTP

| Library | Version policy | Purpose |
|---|---|---|
| HTTPX | `>=0.28.1,<1` | Async HTTP, connection pooling, streaming responses, test transports |

HTTPX 0.28.1 is the current stable line; 1.0 releases visible during research are development prereleases and should not enter the supported range.

The local assembly should construct and inject one long-lived `httpx.AsyncClient` per host/provider configuration. Configure all timeout phases (`connect`, `read`, `write`, and pool acquisition), connection limits, `follow_redirects=False`, and an explicit `trust_env` choice. Bound response bodies and diagnostic previews. Parse provider SSE incrementally from the byte/line stream, including comments, multi-line `data` fields, blank-line event termination, and unknown event types. Do not buffer an unbounded stream.

Implement the OpenAI Responses, Anthropic Messages, and local OpenAI-compatible adapters directly over HTTPX. Keep provider wire models private, normalize responses into OpenRund `ModelCall` data, and schema-validate proposed operations before engine evaluation. Use `httpx.MockTransport` for adapter tests.

Do not enable hidden general retries. Retry eligibility, attempt count, delay, and terminal failure must be deliberate host policy and observable in run history. A provider or transport success never means an operation was accepted; only the engine can emit the authoritative `CommandDecision`.

Do not add the OpenAI or Anthropic SDKs for the MVP. Direct HTTP adapters keep a narrow uniform transport, avoid importing provider-specific model types and retry behavior, and make local OpenAI-compatible endpoints use the same boundary.

### JSON-RPC and Process Isolation

Implement the required JSON-RPC 2.0 subset with stdlib `json`; no JSON-RPC framework is warranted. Define the transport separately as UTF-8 newline-delimited JSON over stdio, one complete object per line.

MVP protocol constraints should be stricter than the full JSON-RPC surface:

- Require exactly `"jsonrpc": "2.0"`, a string request ID, a known method, and exactly one of `result` or `error` in a response.
- Reject duplicate IDs, unexpected messages, malformed UTF-8/JSON, oversized lines, batches, and notifications unless a later protocol version adds them.
- Reserve stdout exclusively for protocol frames; collect bounded diagnostics from stderr.
- Version the OpenRund worker handshake and capability metadata independently from JSON-RPC's protocol version.

Launch workers with `asyncio.create_subprocess_exec`, an argv sequence, and `stdin`, `stdout`, and `stderr` pipes—never through a shell. Supply an allowlisted environment and explicit working directory rather than inheriting ambient credentials. Use dedicated readers for persistent workers so stdout and stderr cannot deadlock. On timeout or cancellation, close stdin, terminate, wait for a short grace period, kill if necessary, and always reap the process. Use a new process session/group where supported so descendants can be cleaned up.

OS resource limits are optional defense in depth. Python's `resource` module is Unix-only, and a subprocess is a fault/transport boundary, not a hardened security sandbox. Strong isolation should later use an OS sandbox or container with an explicit threat model; do not imply that JSON-RPC or a child process supplies authority containment by itself.

### Documents Capability

Keep document support optional in the same distribution:

| Library | Version policy | Purpose |
|---|---|---|
| markdown-it-py | `>=4.2,<5` | Parse Markdown into a token stream for structural operations |
| python-frontmatter | `>=1.3,<2` | Read and write Markdown front matter |
| mdformat | `>=1.0,<2` | Deterministic Markdown formatting |

Install these through `openrund[documents]`. The default local assembly still includes `filesystem`; the documents worker remains transported, which proves the same capability boundary without forcing Markdown dependencies on every runtime installation. Do not declare PyYAML directly unless OpenRund itself imports its API rather than receiving it transitively.

## Testing and Quality Toolchain

Pin these exact versions in `uv.lock` and CI:

| Tool | Version | Purpose and configuration |
|---|---:|---|
| pytest | 9.1.1 | Unit, contract, integration, process, CLI, and compatibility tests. Use native TOML configuration, strict config/markers, and explicit test paths. |
| pytest-asyncio | 1.4.0 | Async tests with `asyncio_mode = "strict"` and function-scoped loops by default. It requires pytest 8.4+, satisfied by pytest 9.1.1. |
| Hypothesis | 6.165.0 | Stateful and property tests for event grammar, reducers, legality, idempotency, waits, delegation, codec round trips, and `.orun` verification. |
| coverage.py | 7.15.2 | Branch coverage engine. Treat coverage as gap detection, not proof of semantic correctness. |
| pytest-cov | 7.1.0 | pytest integration. Configure subprocess measurement with coverage's `patch = ["subprocess"]`; the old pytest-cov `.pth` mechanism is gone. |
| Ruff | 0.16.1 | Linting, import sorting, and formatting. Set `required-version = "==0.16.1"`, target Python 3.12, and keep preview rules disabled in release gates. |
| mypy | 2.3.0 | Strict static checking across `src/` and tests; enable unused-config and unused-ignore warnings. |
| pip-audit | 2.10.1 | Locked-environment dependency audit in CI/release workflow; not a runtime dependency. |

Required test layers:

1. **Compatibility fixtures:** Golden JSON for every event, command envelope, decision variant, provider/capability result, and `.orun` manifest. Decode existing TypeScript fixtures and re-encode byte-for-byte where the format is canonical.
2. **Pure semantic tests:** Reducer and engine transition matrices, including rejected/deferred/superseded decisions and terminal-state immutability.
3. **Property/state-machine tests:** Generate legal and illegal histories and assert monotonic positions, deterministic views, idempotency, and replay equivalence.
4. **Real adapter tests:** Temporary SQLite databases and filesystems, real subprocess workers, and CLI subprocess smoke tests. Mock only external HTTP with `httpx.MockTransport`.
5. **Failure and recovery tests:** Cancellation at every await boundary, process crash/timeout, SQLite busy/rollback behavior, truncated/corrupt bundles, lease expiry, and resume assessment.
6. **Wheel tests:** Install the built wheel in a clean Python 3.12–3.14 environment, run public import and CLI smoke tests, and verify optional `documents` installation separately.

Inject clocks, ID generators, provider transports, process launchers, and streams instead of patching globals. Do not use `pytest-xdist` initially: parallel execution can obscure ordering defects and manufacture SQLite contention before test isolation is proven. Add it only after the serial suite is deterministic.

## Documentation Toolchain

| Tool | Version | Purpose |
|---|---:|---|
| MkDocs | 1.6.1 | Static documentation build and strict link/reference checks |
| Material for MkDocs | 9.7.7 | Navigation, search, and readable site theme |
| mkdocstrings | 1.0.6 | API reference integration |
| mkdocstrings-python | 2.0.5 | Python signature and docstring extraction |

Put these in a `docs` dependency group and run `uv run mkdocs build --strict`. Keep normative runtime semantics, event grammar, authority rules, and compatibility guarantees handwritten; generate API pages only for supported public Python objects. Test code examples where practical. This produces the site without Node. Do not add Sphinx unless a future documentation requirement needs multi-format publishing or cross-project inventories that MkDocs cannot satisfy.

## Installation and Verification

Contributor workflow:

```bash
# Install uv 0.11.29 using an official uv installation method, then:
uv sync --all-groups --all-extras
uv run pytest
uv run mypy src tests
uv run ruff check .
uv run ruff format --check .
uv run mkdocs build --strict
uv build --no-sources
```

Published-user workflow:

```bash
python -m pip install openrund
python -m pip install "openrund[documents]"
openrund --help
```

Use uv only for repository automation; the built wheel must install correctly with standard Python installers. Do not require Node, npm, pnpm, or uv at runtime.

## Compatibility Matrix

| Component | Selected version/range | Compatibility note |
|---|---|---|
| OpenRund | Python `>=3.12` | Required CI on 3.12, 3.13, 3.14. |
| Hatchling | 1.31.0 | Requires Python 3.10+, compatible with the OpenRund floor. |
| jsonschema | `>=4.26,<5` | Version 4.26.0 requires Python 3.10+ and supports Draft 2020-12. |
| HTTPX | `>=0.28.1,<1` | 0.28.1 supports the OpenRund floor; exclude 1.0 development releases. |
| Markdown libraries | Major-bounded ranges above | Selected releases require Python 3.10+, compatible with the OpenRund floor. |
| pytest / pytest-asyncio | 9.1.1 / 1.4.0 | pytest-asyncio 1.4.0 requires pytest 8.4+, so this pair is compatible. |
| Ruff / mypy | 0.16.1 / 2.3.0 | Both support the OpenRund Python range; Ruff analyzes as Python 3.12. |
| SQLite | `>=3.24.0` | Runtime startup check; local filesystem required for WAL. |

Add a separate lowest-direct-dependency CI job so permissive published ranges do not silently depend on features introduced only by the newest lock. The normal test matrix should continue using the exact checked-in lock.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Now |
|---|---|---|---|
| Domain modeling | Dataclasses plus explicit codecs | Pydantic, attrs, msgspec | Adds coercion/serialization semantics or binary-wheel concerns to the authority boundary; explicit codecs make compatibility visible. |
| Database | stdlib `sqlite3` | SQLAlchemy/Alembic | ORM/unit-of-work behavior obscures append transaction ownership; embedded SQL is smaller and matches the existing schema. |
| Async SQLite | Short sync operations, optional owned executor after measurement | aiosqlite | Adds a hidden thread and request queue per connection without removing SQLite's one-writer constraint. |
| Async abstraction | `asyncio` | Direct AnyIO/Trio support | No multi-backend requirement; another cancellation/lifecycle vocabulary increases core surface. |
| CLI | `argparse` | Typer/Click/Rich | Decorators and rich rendering add dependencies and output variability to a deliberately thin CLI. |
| Provider clients | HTTPX adapters | OpenAI and Anthropic SDKs | SDK types, retry defaults, and release cadence would leak into the stable provider boundary. |
| Worker protocol | Small stdlib JSON-RPC codec over stdio | JSON-RPC package, gRPC, Celery, MCP broker | The local request/response protocol is small; frameworks add deployment and semantic surface without improving engine authority. |
| JSON encoding | stdlib `json` | orjson/ujson | Compatibility and special-value behavior matter more than throughput for compact events. |
| Project tooling | uv plus standards metadata | Poetry, PDM, pip-tools, requirements files as source of truth | Duplicates environment/lock/build responsibilities and risks competing dependency authorities. |
| Test execution | Serial pytest matrix | pytest-xdist | Parallelism can hide ordering and lifecycle bugs before isolation is mature. |
| Docs | MkDocs | Sphinx | MkDocs is sufficient for one project site and has lower configuration overhead. |

## Do Not Add to the MVP

- No web framework: OpenRund is a runtime and SDK; a daemon/API surface should be a later host adapter.
- No ORM, general migration framework, message broker, workflow engine, or distributed lock service.
- No Pydantic-based second object model around normative events and commands.
- No separate distributions mirroring the TypeScript monorepo packages.
- No provider SDKs, generic retry library, or automatic retry middleware.
- No third-party JSON-RPC/SSE framework unless interoperability tests expose a protocol case the small codec cannot safely handle.
- No direct AnyIO/Trio public contract, greenlets, or free-threaded-only behavior.
- No Rich-based CLI formatting in canonical output and no shell-completion dependency in the core install.
- No Node-based documentation or build step.
- No direct transitive dependency declarations unless OpenRund imports their APIs.
- No plugin discovery framework before static registration and entry-point requirements are concrete; capability metadata and engine authority remain the real extension boundary.

## Sources

The GSD confidence seam classifies verified `websearch` findings as **MEDIUM**, even when the fetched sources are official primary documentation. Versions and behavior below were cross-checked against official project or standards sources; no LOW-confidence claim is treated as authoritative.

### Python and Packaging

- [Python source releases](https://www.python.org/downloads/source/) — release versions and dates. **MEDIUM**
- [Python versions and maintenance status](https://devguide.python.org/versions/) — supported branches and end-of-life dates. **MEDIUM**
- [Python Packaging User Guide: writing `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — PEP 517/518 and PEP 621 configuration. **MEDIUM**
- [PyPA dependency-groups specification](https://packaging.python.org/en/latest/specifications/dependency-groups/) — PEP 735 groups. **MEDIUM**
- [uv project dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/) and [uv lock and sync](https://docs.astral.sh/uv/concepts/projects/sync/) — project and universal-lock behavior. **MEDIUM**
- [uv build documentation](https://docs.astral.sh/uv/concepts/projects/build/) and [uv package guide](https://docs.astral.sh/uv/guides/package/) — standards builds and `src` layout. **MEDIUM**
- [uv 0.11.29 on PyPI](https://pypi.org/project/uv/) and [Hatchling 1.31.0 on PyPI](https://pypi.org/project/hatchling/) — current versions and Python requirements. **MEDIUM**

### Runtime Libraries and Protocols

- [Python `asyncio` tasks and task groups](https://docs.python.org/3.14/library/asyncio-task.html) — structured concurrency, timeouts, and cancellation. **MEDIUM**
- [Python `sqlite3`](https://docs.python.org/3.14/library/sqlite3.html) — autocommit, transactions, backup, and thread behavior. **MEDIUM**
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html), [isolation](https://www.sqlite.org/isolation.html), [WAL](https://www.sqlite.org/wal.html), and [PRAGMAs](https://www.sqlite.org/pragma.html) — writer serialization, snapshot isolation, filesystem constraints, and durability controls. **MEDIUM**
- [Python `argparse`](https://docs.python.org/3.14/library/argparse.html) — subcommands and parser behavior. **MEDIUM**
- [Python asyncio subprocesses](https://docs.python.org/3/library/asyncio-subprocess.html) — safe process launch, pipes, and deadlock guidance. **MEDIUM**
- [JSON-RPC 2.0 specification](https://www.jsonrpc.org/specification) — request, response, identifier, and error rules. **MEDIUM**
- [jsonschema 4.26.0](https://pypi.org/project/jsonschema/), [validator creation](https://python-jsonschema.readthedocs.io/en/stable/creating/), and [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) — current release and validation model. **MEDIUM**
- [HTTPX 0.28.1](https://pypi.org/project/httpx/), [client pooling](https://www.python-httpx.org/advanced/clients/), [async clients](https://www.python-httpx.org/async/), [timeouts](https://www.python-httpx.org/advanced/timeouts/), [resource limits](https://www.python-httpx.org/advanced/resource-limits/), and [test transports](https://www.python-httpx.org/advanced/transports/) — selected HTTP stack and configuration. **MEDIUM**
- [OpenAI Responses streaming reference](https://platform.openai.com/docs/api-reference/responses-streaming/response/content_part) and [Anthropic Messages streaming](https://platform.claude.com/docs/en/build-with-claude/streaming) — official provider streaming protocols. **MEDIUM**
- [markdown-it-py 4.2.0](https://pypi.org/project/markdown-it-py/), [python-frontmatter 1.3.0](https://pypi.org/project/python-frontmatter/), and [mdformat 1.0.0](https://pypi.org/project/mdformat/) — optional documents stack. **MEDIUM**

### Testing, Quality, and Documentation

- [pytest 9.1.1](https://pypi.org/project/pytest/) and [pytest configuration](https://docs.pytest.org/en/stable/reference/customize.html) — current runner and TOML configuration. **MEDIUM**
- [pytest-asyncio 1.4.0](https://pypi.org/project/pytest-asyncio/) and [pytest-asyncio changelog](https://pytest-asyncio.readthedocs.io/en/stable/reference/changelog.html) — version compatibility and strict mode. **MEDIUM**
- [Hypothesis 6.165.0](https://pypi.org/project/hypothesis/), [coverage.py 7.15.2](https://pypi.org/project/coverage/), and [pytest-cov 7.1.0](https://pypi.org/project/pytest-cov/) — property/state-machine testing and coverage. **MEDIUM**
- [Ruff 0.16.1](https://pypi.org/project/ruff/), [Ruff configuration](https://docs.astral.sh/ruff/configuration/), [mypy 2.3.0](https://pypi.org/project/mypy/), and [pip-audit 2.10.1](https://pypi.org/project/pip-audit/) — quality and dependency-audit tool versions. **MEDIUM**
- [MkDocs 1.6.1](https://pypi.org/project/mkdocs/), [Material for MkDocs 9.7.7](https://pypi.org/project/mkdocs-material/), [mkdocstrings 1.0.6](https://pypi.org/project/mkdocstrings/), and [mkdocstrings-python 2.0.5](https://pypi.org/project/mkdocstrings-python/) — no-Node documentation stack. **MEDIUM**
