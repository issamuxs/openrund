# Coding Conventions

**Analysis Date:** 2026-08-06

## Naming Patterns

**Files:**

- Use lowercase `snake_case.py` for modules, as in `src/openrund/engine/legality.py` and `src/openrund/providers/openai_responses.py`.
- Prefix implementation-only modules with `_`, as in `src/openrund/assembly/_operator.py` and `src/openrund/storage/_sqlite.py`. Keep public imports in the package `__init__.py` rather than asking consumers to import private modules.
- Name tests `test_<subject>.py` and place them under the matching subsystem, such as `tests/engine/test_legality.py` and `tests/storage/test_sqlite_event_store.py`.
- Use `conftest.py` only for fixtures and deterministic test support shared within that directory tree; examples include `tests/conftest.py`, `tests/engine/conftest.py`, and `tests/storage/conftest.py`.

**Functions:**

- Use `snake_case` for functions and methods. Test functions describe observable behavior with `test_<condition>_<outcome>` rather than mirroring implementation names.
- Prefix module-private helpers with `_`, for example the `_imports` source scanners in `tests/package/test_import_hygiene.py` and subsystem hygiene tests.
- Give public callables verb-oriented names that expose domain intent (`dispatch`, `append`, `resume`, `render_operator_json`) instead of transport or storage mechanics.
- Use positional-only parameters (`/`) for narrow Protocol seams where argument names are not part of the contract, and keyword-only parameters (`*`) for configuration-heavy construction.

**Variables:**

- Use `snake_case` for locals, parameters, fields, and fixture names.
- Use `UPPER_SNAKE_CASE` for module constants and singleton defaults, such as `DEFAULT_REPORTER` in `src/openrund/assembly/_operator.py`.
- Name values by domain role (`run_id`, `expected_position`, `runtime_event`) rather than generic containers (`data`, `obj`) when they cross a contract boundary.
- Keep wire keys and serialized aliases explicit in codec modules; do not derive external names from Python attribute names.

**Types:**

- Use `PascalCase` for classes, protocols, enums, dataclasses, and type aliases. Semantic identifiers use the `Id` suffix (`RunId`, `WorkerId`), not `ID`.
- Model stable concepts as immutable value objects, commonly `@final` plus `@dataclass(frozen=True, slots=True, kw_only=True)`.
- Use `StrEnum` or precise unions for closed vocabularies. Avoid replacing domain types with open-ended strings or dictionaries.
- Use Python 3.12 generic and `type` alias syntax where it improves clarity. Keep public annotations complete and compatible with strict mypy.

## Code Style

**Formatting:**

- Ruff is the formatter. `pyproject.toml` sets Python 3.12 syntax and a 100-character line length for `src`, `tests`, and `examples`.
- Run `uv run ruff format --check src tests examples` to verify formatting; apply `uv run ruff format src tests examples` when changing code.
- Prefer small immutable expressions and explicit branches over clever compression. Preserve compact event payloads and immutable artifact references as required by `AGENTS.md`.
- Add `from __future__ import annotations` to normal source and test modules unless the file is a deliberate package metadata or export-only exception.

**Linting:**

- Ruff is configured in `pyproject.toml` with `ANN`, `B`, `E`, `F`, `I`, `RUF`, `SIM`, and `UP`; verify with `uv run ruff check src tests examples`.
- Strict mypy covers `src/openrund`, `tests`, and `examples`; verify with `uv run mypy --strict src/openrund tests examples`.
- Keep suppressions narrow and coded. Test-only `# type: ignore[...]` comments are acceptable when a test intentionally constructs an invalid runtime value or attempts a forbidden mutation; do not broaden them to hide unrelated typing failures.
- AST-based hygiene tests in `tests/package/test_import_hygiene.py` and subsystem `test_hygiene.py` files are architectural lint, not optional style checks. Keep them passing when dependencies or exports change.

## Import Organization

**Order:**

1. `from __future__ import annotations`.
2. Standard-library imports.
3. Third-party imports such as `pytest`.
4. Absolute project imports rooted at `openrund`.

Ruff's `I` rules enforce grouping and sorting. Do not use ad hoc `sys.path` mutation in new tests.

**Path Aliases:**

- No application-specific import aliases are configured. Source imports are absolute (`from openrund...`) and resolve through the `src` layout.
- `pyproject.toml` supplies `pythonpath = ["src"]` to pytest and `mypy_path = ["src"]` to mypy.
- Five contract tests currently insert `src` into `sys.path`: `tests/contracts/test_ids.py`, `tests/contracts/test_errors.py`, `tests/contracts/test_values.py`, `tests/contracts/test_paths.py`, and `tests/contracts/test_leaf_concepts.py`. These insertions are mechanically redundant with the central configuration and are safe consolidation candidates after focused and full-suite verification.

## Error Handling

**Patterns:**

- Raise the semantic `OpenRundError` hierarchy defined in `src/openrund/errors.py`, with stable safe codes suitable for callers and tests.
- Validate immutable value objects in `__post_init__` and fail at construction time. Deep-freeze nested values before retaining them.
- Translate platform exceptions at trust boundaries. Storage adapters convert SQLite and filesystem failures to domain errors; provider and capability boundaries likewise avoid leaking implementation exceptions.
- Preserve an existing `OpenRundError`; translate unrelated exceptions with `raise ... from None` when the original exception could expose credentials, paths, payloads, or driver details.
- Keep `pointer` and `safe_detail` bounded and redacted. Do not include absolute paths, secrets, raw model output, database contents, or authorization material in user-visible errors.
- Represent legal engine outcomes as typed values and events where the runtime contract calls for a decision. Exceptions are for malformed input, failed boundaries, and broken invariants—not an alternate authority path.
- Distinguish optimistic-position conflicts, unavailable storage, corrupt data, transport failures, and invalid values instead of collapsing them into a generic runtime error.

## Logging

**Framework:**

- The package does not use the standard `logging` module as an ambient side channel. Reporting is a typed port: `Reporter` and `ReportEntry` live in `src/openrund/ports/runtime.py`.
- `NullReporter` in `src/openrund/assembly/_operator.py` is the default, and `RecordingReporter` in `src/openrund/_testing/fakes.py` supports deterministic assertions.
- User-facing output is rendered from typed operator results. The example `examples/governed_coding.py` prints `render_operator_json(result)` only at the executable boundary.

**Patterns:**

- Inject a `Reporter` through runtime dependencies; do not call `print`, global loggers, or telemetry services from engine and contract modules.
- Report structured, bounded entries after the engine has authorized and persisted the corresponding transition. Reporting must not become an authority or persistence boundary.
- Keep tests deterministic by recording entries in memory and asserting typed content, ordering, and omission of unsafe details.

## Comments

**When to Comment:**

- Explain invariants, authority boundaries, compatibility constraints, redaction decisions, and non-obvious concurrency behavior.
- Avoid comments that narrate straightforward code. Prefer domain names and small helpers that make intent visible.
- Treat `docs/architecture.md`, `docs/concepts.md`, `docs/events.md`, `docs/providers.md`, `docs/capabilities.md`, `docs/storage.md`, `docs/delegation.md`, and `docs/bundles.md` as normative context. Update code and the relevant docs together when a public contract changes.
- Keep TODO/FIXME placeholders out of completed behavior. Track planned work in GSD artifacts rather than leaving executable stubs.

**JSDoc/TSDoc:**

- This is a Python codebase; use Python docstrings, not JSDoc/TSDoc.
- Give public modules, protocols, classes, and non-obvious public functions concise docstrings describing the contract and invariants. Do not duplicate type annotations in prose.
- Private helpers need docstrings only when their constraints or failure behavior are not evident from their names and types.

## Function Design

**Size:**

- Keep contract validation, legality decisions, persistence, provider transport, and presentation in separate functions or modules.
- Extract helpers when they isolate a security boundary, codec rule, transactional step, or repeated operation. Do not split cohesive domain logic merely to reduce line count.
- Keep engine entry points readable as ordered state transitions: load and validate history, decide legality, create events/effects, append atomically, then report or render.

**Parameters:**

- Prefer semantic value types from `src/openrund/contracts` over primitive strings, paths, or open dictionaries.
- Use dependency records and Protocols for clocks, identifier factories, event stores, artifact stores, providers, reporters, and capability runners.
- Use keyword-only construction for records with multiple same-typed fields. Avoid ambient credentials, current directories, clocks, randomness, or process globals.

**Return Values:**

- Return precise immutable domain values, tuples, or result types. Avoid `Any`, mutable dictionaries, and nullable sentinels at public boundaries.
- Use `None` only when absence is explicitly part of the contract. Use typed outcomes for accepted/rejected/terminal decisions.
- Keep artifacts immutable and refer to them by typed identity rather than returning mutable filesystem or database handles.

## Module Design

**Exports:**

- The root public API is deliberately curated in `src/openrund/__init__.py`. Add a public symbol there only when it is part of the supported package contract.
- Keep implementation helpers private and exclude `src/openrund/_testing` from the public surface.
- Preserve the engine as the only authority boundary. Adapters, providers, capabilities, views, CLI, and examples may request or render behavior but must not manufacture authoritative state transitions.
- Maintain dependency direction through the AST guards in `tests/package/test_import_hygiene.py` and subsystem hygiene tests.

**Barrel Files:**

- Package `__init__.py` files are explicit Python barrels with sorted imports and explicit `__all__`, for example `src/openrund/engine/__init__.py` and `src/openrund/storage/__init__.py`.
- Do not use star imports or dynamically generated export lists. The independent expected export set in `tests/package/test_public_api.py` is intentional contract coverage and must not be derived from `src/openrund/__init__.py`.
- Re-export only stable public contracts. Import private implementation modules directly inside the package.

## Quality Consolidation Guidance

- Safe: remove the five per-file `sys.path.insert` blocks listed above because central pytest/mypy configuration already owns source discovery. Verify the five contract modules, strict mypy, Ruff, and the full suite afterward.
- Safe: centralize repeated AST import/source traversal helpers from `tests/bundles/test_hygiene.py`, `tests/capabilities/test_hygiene.py`, `tests/engine/test_coordination_hygiene.py`, `tests/providers/test_hygiene.py`, `tests/storage/test_hygiene.py`, `tests/views/test_view_hygiene.py`, and `tests/package/test_import_hygiene.py` in a test-only helper. Keep each subsystem's independent forbidden-import rules and assertions.
- Preserve: the explicit public API oracle in `tests/package/test_public_api.py`, subsystem hygiene rules, strict type/lint settings, and runtime error redaction tests. Deriving expected contracts from production code would make regressions invisible.
- Preserve: duplicate dev requirements in `[project.optional-dependencies].test` and `[dependency-groups].dev` unless the published `openrund[test]` or local `uv` workflow is intentionally removed; they serve different installation surfaces.

---

*Convention analysis: 2026-08-06*
