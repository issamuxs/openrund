# Technology Stack

**Analysis Date:** 2026-08-06

## Languages

**Primary:**
- Python 3.12+ - All executable product code under `src/openrund/`, the installed command, examples, and tests. The package metadata in `pyproject.toml` declares `>=3.12` and classifiers for 3.12, 3.13, and 3.14.
- The source uses Python 3.12 syntax, including PEP 695 type-parameter syntax in files such as `src/openrund/storage/_artifacts.py`; do not lower the runtime floor without a source migration.

**Secondary and declarative:**
- SQLite SQL - Embedded schema, migration, and query strings in `src/openrund/storage/_database.py`, `src/openrund/storage/_events.py`, `src/openrund/storage/_artifacts.py`, and `src/openrund/storage/_leases.py`.
- TOML - The single tracked project/build/tool configuration is `pyproject.toml`; the resolved development graph is `uv.lock`.
- JSON and JSONL - Canonical wire data, `.orun` manifests, and the committed compatibility corpus under `tests/fixtures/compatibility/v1/`.
- Markdown - Public documentation in `README.md`, `SECURITY.md`, `CHANGELOG.md`, `docs/`, and `examples/README.md`; Markdown is also the built-in transported Documents Capability format.
- The tracked product source is Python-only; no secondary implementation language or generated extension source is present. `tests/package/test_python_only_cutover.py` enforces this boundary.

## Runtime

**Environment:**
- CPython 3.12 or newer - Required by `pyproject.toml`, `README.md`, and `docs/quickstart.md`.
- Supported release matrix - Python 3.12, 3.13, and 3.14 according to `pyproject.toml` classifiers and the release verification commands documented in `docs/contributing.md`.
- Async model - Standard-library `asyncio` for Engine/runtime lifetimes, provider HTTP, Capability transports, and local storage offloading.
- Production runtime dependencies - None. `[project].dependencies = []` in `pyproject.toml`, and product imports resolve only to the Python standard library, relative modules, or `openrund.*` modules.
- Local development environment - `.venv/pyvenv.cfg` currently records CPython 3.12.11 created by uv 0.11.8, but `.venv/` is ignored and is not a repository contract.

**Package Manager:**
- uv - Canonical development resolver, environment runner, lock checker, and builder. Commands are documented in `README.md`, `docs/README.md`, and `docs/contributing.md`.
- Repository-pinned uv version - Not detected. The local installation reports uv 0.11.8, while the repository relies on the lock format and documented commands rather than a `.tool-versions` or installer pin.
- Lockfile - `uv.lock` is tracked, uses lock format version 1, requires Python `>=3.12`, and resolves 15 packages across the project, test extra, and dev group.
- pip compatibility - End users install the dependency-free wheel with `python -m pip install openrund`; contributors use uv.

## Frameworks

**Core:**
- No application framework or ORM. OpenRund is a typed library plus console adapter built directly on dataclasses, protocols, `asyncio`, `sqlite3`, filesystem APIs, and sockets.
- SQLite - Python's `sqlite3` module provides local Event, Artifact metadata, and Lease custody. SQL lifecycle and transactions stay private to `src/openrund/storage/_database.py`.
- Direct HTTP/1.1 + SSE - `src/openrund/providers/_http.py` implements bounded async HTTP and server-sent events using `asyncio`, `ssl`, and `urllib.parse`; no vendor SDK or general HTTP package is installed.
- Console entry point - `[project.scripts]` maps `openrund` to `openrund.__main__:main` in `pyproject.toml`; `src/openrund/__main__.py` delegates to `src/openrund/cli.py`.

**Testing:**
- pytest 9.1.1 locked, minimum 8.4 declared - Unit, integration, compatibility, package, installed-wheel, documentation, and optional live-provider tests under `tests/`.
- coverage.py 7.15.3 locked, minimum 7.6 declared - Branch coverage for `openrund`, with `fail_under = 79` in `pyproject.toml`.
- The test runner configuration is centralized under `[tool.pytest.ini_options]` in `pyproject.toml`: strict config, strict markers, strict xfail behavior, `tests/` discovery, and `src/` import path.
- Compatibility fixtures under `tests/fixtures/compatibility/v1/` are tracked golden evidence, not disposable generated test output.

**Build/Dev:**
- Hatchling `>=1.28` - PEP 517 build backend declared in `pyproject.toml`. It builds the `src/openrund` wheel and an explicitly scoped source distribution.
- mypy 2.3.0 locked, minimum 1.18 declared - Strict static typing over `src/openrund`, `tests`, and `examples`.
- Ruff 0.16.1 locked, minimum 0.12 declared - Formatting plus lint families `ANN`, `B`, `E`, `F`, `I`, `RUF`, `SIM`, and `UP`, targeting Python 3.12 with a 100-column line length.
- uv 0.11.8 locally - `uv sync`, `uv run`, `uv lock --check`, and `uv build`; no repository pin fixes this exact tool version.
- `tests/package/test_py_typed.py`, `tests/package/test_installed_typing.py`, and `tests/package/test_release_hygiene.py` verify wheel/sdist contents, the `py.typed` marker, installed typing, metadata, and quality gates.

## Dependency Audit

### Declared direct dependencies

| Dependency | Scope | Version contract | Necessity and evidence |
|---|---|---:|---|
| None | Runtime | Not applicable | Intentional. `pyproject.toml` declares an empty runtime dependency list, and `tests/package/test_py_typed.py` asserts it. Keep the base package standard-library-only. |
| hatchling | Build isolation | `>=1.28` | Required to produce the wheel and sdist configured under `[tool.hatch.*]`; `tests/package/test_py_typed.py` invokes `uv build` and checks exact archive content. |
| pytest | Test extra + dev group | `>=8.4`; locked 9.1.1 | Required throughout `tests/`; strict runner behavior is configured in `pyproject.toml`. |
| coverage[toml] | Test extra + dev group | `>=7.6`; locked 7.15.3 | Required for the documented branch-coverage gate and enforced 79% threshold. |
| mypy | Test extra + dev group | `>=1.18`; locked 2.3.0 | Required for the documented strict type gate and installed-package typing checks. |
| ruff | Test extra + dev group | `>=0.12`; locked 0.16.1 | Required for the documented lint and format checks and the configured release hygiene contract. |

The four quality tools intentionally appear in both `[project.optional-dependencies].test` and `[dependency-groups].dev` in `pyproject.toml`. This is maintenance duplication, but it serves two distinct consumers: `pip install openrund[test]` and default `uv sync`. `tests/package/test_py_typed.py` asserts both surfaces. Do not remove one copy unless one installation workflow is deliberately retired.

### Locked transitive dependencies

| Locked package | Brought in by | Necessity assessment |
|---|---|---|
| `ast-serialize` 0.6.0 | mypy 2.3.0 | Tool implementation dependency; do not declare directly. |
| `librt` 0.13.0 | mypy 2.3.0 | Tool implementation dependency; do not declare directly. |
| `mypy-extensions` 1.1.0 | mypy | Tool implementation dependency; do not declare directly. |
| `pathspec` 1.1.1 | mypy | Tool implementation dependency; do not declare directly. |
| `typing-extensions` 4.16.0 | mypy on applicable interpreters | Tool compatibility dependency; not used by production source. |
| `iniconfig` 2.3.0 | pytest | Test-runner dependency; do not declare directly. |
| `packaging` 26.3 | pytest | Test-runner dependency; do not declare directly. |
| `pluggy` 1.6.0 | pytest | Pytest plugin mechanism; do not declare directly. |
| `pygments` 2.20.0 | pytest | Test failure rendering; do not declare directly. |
| `colorama` 0.4.6 | platform-conditional test tooling | Present in `uv.lock` for cross-platform resolution; not active in the local macOS dependency tree and not a product dependency. |

`uv tree --locked --all-groups` resolves the four direct development tools and their transitive graph. The lock contains no hidden product SDK, database driver, web framework, telemetry agent, or auth library.

### Build-backend reproducibility

- Hatchling is a PEP 517 build requirement, not a dev-group dependency in `uv.lock`; `uv build` resolves it in build isolation from the lower bound in `pyproject.toml`.
- This is necessary for standard packaging but is the only tooling surface not concretely represented in the project lock graph. If reproducible build-tool bytes become a release requirement, constrain or separately lock the build environment. The current exact-content package tests mitigate output drift but do not pin Hatchling itself.

## Configuration

**Environment:**
- Production configuration is explicit Python input, not ambient environment: `LocalAssemblyConfig` in `src/openrund/assembly/_model.py`, provider constructors in `src/openrund/providers/`, and CLI `--home`/`--map` options in `src/openrund/cli.py`.
- Default local custody is `~/.openrund`, implemented by `default_openrund_home()` in `src/openrund/storage/_layout.py`; `--home PATH` overrides it.
- Product source reads only the internal Documents worker variables `OPENRUND_DOCUMENT_ROOTS`, `OPENRUND_DOCUMENT_MAX_BYTES`, and `OPENRUND_DOCUMENT_MAX_DIFF_BYTES` in `src/openrund/capabilities/documents_worker.py`. The parent transport constructs these values in `src/openrund/capabilities/documents.py`.
- Provider credentials are explicit constructor values. Production provider modules are tested not to read `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `tests/providers/test_hygiene.py` and `tests/package/test_release_hygiene.py`.
- No `.env`, `.env.example`, global application config file, credential file, or settings framework is tracked.

**Build and tools:**
- `pyproject.toml` is the sole tracked build/tool configuration: package metadata, Hatchling, pytest, coverage, mypy, and Ruff.
- `uv.lock` is the sole dependency lock.
- `.gitignore` excludes builds, virtual environments, Python bytecode, test/type/lint caches, coverage output, package metadata, GSD caches, and `.local/` runtime data.
- `src/openrund/_version.py` is the single package version source; Hatchling reads it and Bundle compatibility imports it.
- `src/openrund/py.typed` is required in the wheel to declare PEP 561 typing support.
- No `setup.py`, `setup.cfg`, requirements file, tox/nox configuration, Makefile, Taskfile, pre-commit configuration, Docker file, `.python-version`, `.tool-versions`, or GitHub Actions workflow is present.

**Distribution shape:**
- Wheel - Only `src/openrund/` plus distribution metadata and the installed `openrund` command.
- Source distribution - `CHANGELOG.md`, `README.md`, `SECURITY.md`, `docs/`, `examples/`, `pyproject.toml`, and `src/openrund/`; exact content is checked in `tests/package/test_py_typed.py`.
- `uv.lock`, tests, planning files, local caches, and built archives are development/repository inputs and are not wheel runtime content.

## Build, Config, and Tool File Necessity

| Path | Role | Keep/simplify assessment |
|---|---|---|
| `pyproject.toml` | Package, build, test, coverage, typing, and lint contract | Essential and already consolidated. Splitting tool configs would add redundancy. |
| `uv.lock` | Reproducible contributor dependency graph | Essential for `uv sync` and `uv lock --check`; never treat it as a runtime dependency. |
| `.gitignore` | Keeps local builds, caches, runtime data, and virtualenvs out of history | Essential; current ignored paths match observed local output. |
| `src/openrund/_version.py` | Dynamic distribution/runtime/Bundle version | Essential single source; avoid duplicating version text in build config. |
| `src/openrund/py.typed` | Installed static-typing marker | Essential; package tests require it. |
| `tests/fixtures/compatibility/v1/manifest.json` | Integrity manifest for frozen compatibility evidence | Essential tracked test data, not a general project configuration file and not safe to regenerate casually. |
| `AGENTS.md` | Local agent/project instructions | Development-only; no effect on package build or runtime. Keep separate from product configuration. |

## Generated and Local-Only Items

The following observed items are ignored by `.gitignore`, untracked, and safely reproducible or disposable:

| Path | Classification | Safe action |
|---|---|---|
| `.venv/` | uv-created local CPython environment | Recreate with `uv sync`; safe to remove when rebuilding the environment. |
| `dist/` | Local Hatchling wheel and sdist output, currently including `openrund-2.0.0-py3-none-any.whl` and `.tar.gz` | Recreate with `uv build`; safe to remove after release verification. |
| `.pytest_cache/` | Pytest runtime cache | Safe to remove; tests regenerate it. |
| `.mypy_cache/` | mypy incremental cache | Safe to remove; strict mypy regenerates it. |
| `.ruff_cache/` | Ruff cache | Safe to remove; Ruff regenerates it. |
| `.coverage` | Local coverage database | Safe to remove; coverage commands regenerate it. |
| `tests/__pycache__/` and other `__pycache__/` directories | CPython bytecode | Safe to remove; Python regenerates it. |
| `.local/` when present | Documented repository-local runtime/demo custody | Safe only when its local run evidence is no longer needed; never package it. |

Several ignored cache/build directories contain duplicate collision-style names such as `.gitignore 2`, `CACHEDIR 2.TAG`, `README 2.md`, and duplicated version directories. They are local cache artifacts, not tracked variants. Removing the enclosing ignored cache or `dist/` directory is the safest simplification; do not promote these suffixed files into source control.

No generated build output or cache is tracked. By contrast, `tests/fixtures/compatibility/v1/` is intentionally tracked, hash-manifested evidence and must not be cleaned as generated output.

## Safe Simplification Guidance

- Keep the dependency-free runtime. Adding vendor SDKs would duplicate the direct bounded transports in `src/openrund/providers/_http.py` and violate tested package constraints.
- Keep tool configuration centralized in `pyproject.toml`; there is no redundant pytest, coverage, mypy, or Ruff config file to remove.
- Keep both the `test` extra and `dev` group while both pip and uv contributor workflows remain supported; use the package metadata test to prevent their four-package sets from drifting.
- Clean ignored caches and `dist/` rather than adding more ignore exceptions or committing local metadata files.
- Do not replace the committed compatibility corpus with generated-on-test fixtures; its independent manifest is part of cross-runtime evidence.
- A repository `.python-version` set to 3.12 would reduce accidental use of an incompatible system Python, but it would be a new tool preference rather than a deletion/simplification. The authoritative constraint remains `pyproject.toml`.
- Avoid adding Makefile/tox/nox wrappers unless they provide a genuinely new matrix or release function; current uv commands are short, documented, and directly tested.

## Platform Requirements

**Development:**
- Any OS with CPython 3.12+, uv, and filesystem/SQLite support.
- Git is required for Git Capability and governed-coding demonstration tests; tests skip the demonstration when Git is unavailable.
- Network access is unnecessary for the normal deterministic suite after dependencies are available. Real-provider checks are separately marked and opt-in.
- Supported quality commands are the uv invocations in `README.md` and `docs/contributing.md`; use them instead of the host's unqualified `python3`.

**Production:**
- Distributed as an OS-independent pure-Python wheel with the `openrund` console script.
- No server, container, browser, GUI, cloud hosting platform, or daemon is required.
- Local assembly needs writable private custody for SQLite and Artifact files. Optional Capability integrations need explicitly configured filesystem mounts, absolute process/Git executables, and identities.
- Provider adapters need outbound HTTP(S) only when a caller explicitly configures and invokes them.

---

*Stack analysis: 2026-08-06*
*Update after Python support, dependency, build-backend, or packaging changes*
