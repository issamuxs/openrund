# Testing Patterns

**Analysis Date:** 2026-08-06

## Test Framework

**Runner:**

- Pytest 8.4 or newer is the sole test runner. Configuration lives in `pyproject.toml` under `[tool.pytest.ini_options]`.
- Tests are discovered under `tests`, `src` is placed on the import path, unknown configuration and markers are rejected, and xfail is strict.
- `live_provider` is the only declared marker. It isolates explicitly opted-in network/provider checks from the normal offline suite.

**Config:**

- `pyproject.toml` is the canonical configuration for pytest, coverage, mypy, Ruff, build metadata, and test/dev dependencies.
- There is no `tox.ini`, `noxfile.py`, pre-commit configuration, Makefile, or repository CI workflow. Quality gates are currently documented local commands plus executable pytest assertions.
- Normal verification is offline and deterministic. `tests/providers/test_live.py` skips unless its explicit live-provider prerequisites are supplied.

**Assertion Library:**

- Use plain pytest `assert`, `pytest.raises`, `pytest.mark.parametrize`, fixtures, and `monkeypatch`.
- Do not add a second assertion library. Compare precise typed values, event sequences, canonical bytes/JSON, error codes, exit codes, and captured streams directly.

**Run Commands:**

- Full suite with branch coverage: `uv run coverage run -m pytest -q`
- Enforce/report coverage: `uv run coverage report`
- Focused test: `uv run pytest tests/<subsystem>/test_<subject>.py -q`
- Opt-in live providers: `uv run pytest -m live_provider`
- Strict types: `uv run mypy --strict src/openrund tests examples`
- Lint: `uv run ruff check src tests examples`
- Format check: `uv run ruff format --check src tests examples`
- Lockfile integrity: `uv lock --check`
- Distribution build: `uv build`
- No watch-mode command is configured.

## Test File Organization

**Location:**

- Tests mirror package responsibilities: `tests/contracts`, `tests/codec`, `tests/engine`, `tests/storage`, `tests/providers`, `tests/capabilities`, `tests/bundles`, `tests/views`, `tests/operator`, `tests/runtime`, `tests/assembly`, and `tests/ports`.
- Cross-cutting release and architecture checks live in `tests/package`; documentation checks live in `tests/docs`; CLI and end-to-end example coverage live in `tests/cli` and `tests/demo`.
- Frozen compatibility evidence lives under `tests/fixtures`, authenticated by `tests/fixtures/manifest.json` and loaded through `tests/conftest.py`.
- Shared subsystem fixtures belong in the nearest `conftest.py`, such as `tests/engine/conftest.py`, `tests/storage/conftest.py`, and `tests/bundles/conftest.py`.

**Naming:**

- Files use `test_<subject>.py`; functions use `test_<condition>_<expected_outcome>`.
- Fixture names state the domain value they supply (`event_store`, `engine_dependencies`, `runtime_event`, `database_path`) rather than their implementation mechanics.
- Helper types used only by tests are explicit and typed (`FixedClock`, `SequenceIdFactory`, `RecordingReporter`) instead of anonymous mocks.

**Structure:**

- Keep the arrangement local: construct immutable input, invoke one public boundary, then assert the result and authoritative evidence.
- Test happy paths, invalid runtime types, boundary values, Unicode, omitted versus null fields, error redaction, and deep immutability.
- For engine behavior, assert both the returned decision and the complete event-store history. For rejected commands, assert that only the permitted audit event was appended.
- For adapters, assert semantic exceptions and recovery/rollback behavior, not private implementation calls.

## Test Structure

**Suite Organization:**

```python
def test_rejected_command_records_only_the_rejection(
    event_store: MemoryEventStore,
    engine_dependencies: EngineDependencies,
) -> None:
    command = make_invalid_command()

    result = dispatch(command, dependencies=engine_dependencies)

    assert result.outcome is DispatchOutcome.REJECTED
    assert event_store.read(result.run_id) == (expected_rejection_event(),)
```

Use the actual public boundary and assert the authoritative state change. Helper builders may reduce setup, but expected outcomes should remain visible in the test.

**Patterns:**

- Tests are function-based; no unittest-style class hierarchy is used.
- Parameterize data matrices when the behavior is identical across inputs. Keep separate tests when the failure reason or authority implication differs.
- Use exact equality for dataclasses, tuples, event payloads, canonical serialized bytes, and public export sets.
- Use `# type: ignore[<code>]` only to present deliberately invalid values to runtime validators or to test immutability. This is test input construction, not permission to loosen strict typing.
- Hygiene tests parse Python with `ast` and scan source trees to enforce dependency direction, static Protocols, append authority, wire alias confinement, and the absence of forbidden legacy or unsafe constructs.

## Mocking

**Framework:**

- No mocking framework is used. The suite does not rely on `unittest.mock`, `Mock`, `AsyncMock`, or patching production internals.
- Use pytest's `monkeypatch` sparingly for process-environment edges such as TTY detection and interactive input in `tests/cli`.

**Patterns:**

```python
@final
@dataclass(slots=True)
class FixedClock:
    value: datetime

    def now(self) -> datetime:
        return self.value
```

- Implement narrow Protocol-compatible fakes for clocks, identifier factories, reporters, providers, and stores.
- Prefer `MemoryEventStore`, `MemoryArtifactStore`, and the typed fakes in `src/openrund/_testing` to method-level mocks.
- Build local TCP servers for HTTP/SSE provider behavior and use real temporary SQLite databases, filesystems, subprocesses, and Git repositories for boundary integration.

**What to Mock:**

- Nondeterministic seams: time, generated identifiers, provider replies, reporting sinks, terminal input/TTY status, and explicitly bounded environment values.
- Keep fake sequences finite so unexpected extra calls fail visibly.

**What Not to Mock:**

- Do not mock engine legality, event construction, codec canonicalization, SQLite transactions, filesystem containment, CLI result rendering, or bundle validation.
- Do not mock the public API under test or assert private call counts. Observable results, durable events, artifacts, stdout/stderr, and safe errors are the contract.
- Do not call real external providers in the normal suite. Keep live tests opt-in and separate from deterministic coverage.

## Fixtures and Factories

**Test Data:**

```python
@pytest.fixture
def engine_dependencies(event_store: MemoryEventStore) -> EngineDependencies:
    return EngineDependencies(
        event_store=event_store,
        clock=FixedClock(FIXED_TIME),
        run_ids=SequenceIdFactory((RunId("run-1"),)),
    )
```

- Construct semantic identifiers and frozen contract values directly; avoid loose dictionaries except at serialization boundaries.
- Use a fixed timezone-aware timestamp and deterministic ID sequences for reproducible events.
- Use `tmp_path` for SQLite files, bundle directories, capability roots, subprocess workspaces, and installed-package environments.
- Use `asyncio.Barrier` or controlled local servers for concurrency rather than sleeps.

**Location:**

- `tests/engine/conftest.py` owns engine clocks, ID generators, memory stores, dependencies, and base runtime events.
- `tests/storage/conftest.py` owns temporary database paths.
- `tests/bundles/conftest.py` owns in-memory bundle sources and exact wire events.
- `tests/conftest.py` owns the authenticated compatibility corpus loader and cross-subsystem corpus selections; `tests/views/conftest.py` reuses it rather than copying it.
- `src/openrund/_testing/fakes.py` contains reusable typed fakes intentionally shared with consumers or multiple test areas, but it is not part of the root public API.

**Compatibility Corpus:**

- `tests/fixtures` contains 287 files including `manifest.json`; the evidence files are independent frozen compatibility oracles used by codec, engine, storage, views, and package-integrity tests.
- The loader validates containment, regular-file status, byte length, and SHA-256 before parsing meaning. This ordering is a security and compatibility contract.
- Do not regenerate expected evidence from current production code, deduplicate semantically similar cases, or derive the manifest during tests. Those changes would erase the suite's independence from the implementation.

## Coverage

**Requirements:**

- Coverage uses `coverage.py` with branch coverage, source restricted to `openrund`, missing lines displayed, and a hard `fail_under = 79` in `pyproject.toml`.
- Treat 79% as the release floor, not the target for changed security/authority code. New branches in legality, persistence, codecs, paths, and providers need direct success and failure tests.
- Packaging, docs, examples, and architecture rules are covered by executable release-hygiene tests even though line coverage targets the package source.

**View Coverage:**

- Run `uv run coverage run -m pytest -q` followed by `uv run coverage report`.
- For local HTML investigation, `uv run coverage html` is compatible with the configured data, though it is not listed as a canonical repository gate.
- `.coverage` and `htmlcov` are ignored in `.gitignore`; do not commit generated coverage artifacts.

## Test Types

**Unit:**

- Contract constructors, IDs, paths, codecs, legality functions, views, rendering, and pure transition logic are tested with direct calls and exact value assertions.
- Examples include `tests/contracts`, `tests/codec`, and pure engine/view modules.

**Integration:**

- Storage tests exercise real SQLite databases, transaction rollback, busy-timeout bounds, corruption, recovery, and concurrent expected-position writes.
- Provider tests exercise fragmented HTTP and SSE over local `asyncio.start_server` servers, including timeout and cancellation behavior.
- Capability tests exercise real temporary filesystem roots, constrained subprocesses, symlinks, and local Git repositories.
- Bundle tests combine event/artifact stores, manifest/codecs, and validation boundaries with exact immutable source material.

**E2E:**

- `tests/demo` runs the governed coding flow against the production local assembly and verifies repeatable terminal outcomes and files.
- `tests/cli` exercises the CLI boundary, exit codes, stdout/stderr, interactive constraints, and typed operator results.
- `tests/package/test_py_typed.py` and `tests/package/test_installed_typing.py` build wheel/sdist artifacts, install them into isolated environments, run import/demo behavior, and type-check a consumer without relying on the source tree.
- There is no separate browser or external-system E2E framework; current E2E scope is the local runtime, CLI, distribution, and explicit opt-in provider smoke tests.

## Common Patterns

**Async Testing:**

```python
def test_provider_streams_fragmented_sse() -> None:
    async def scenario() -> None:
        server = await asyncio.start_server(handle_connection, "127.0.0.1", 0)
        try:
            result = await provider.respond(request)
            assert result == expected_response
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(scenario())
```

- Async behavior is wrapped with `asyncio.run`; the suite does not depend on `pytest-asyncio`.
- Close servers and resources in `finally` blocks. Coordinate concurrency with events/barriers and bounded timeouts, not arbitrary sleeps.
- Assert cancellation and timeout translation explicitly at provider and worker boundaries.

**Error Testing:**

```python
def test_invalid_value_uses_stable_safe_error() -> None:
    with pytest.raises(InvalidValueError) as caught:
        build_value(secret_input)  # type: ignore[arg-type]

    assert caught.value.code == "invalid_value"
    assert secret_input not in str(caught.value)
```

- Assert the concrete semantic error type, stable code, safe pointer/detail, and absence of secrets or absolute paths.
- Use `pytest.raises(..., match=...)` only for stable public text. Prefer structured fields over brittle full-message matches.
- For failure atomicity, also assert the durable store, artifact set, filesystem, or output stream is unchanged except for explicitly required audit evidence.

**Security and Boundary Testing:**

- Include traversal, symlink, NUL, Windows-path, Unicode, malformed JSON/SSE, oversized input, cancellation, corruption, and concurrency cases at trust boundaries.
- Verify integrity metadata before decoding or interpreting external bytes.
- Keep process/network tests local and bound. Never read ambient credentials in ordinary tests; `tests/package/test_release_hygiene.py` enforces this statically.

## Quality Surface Assessment

**Necessary Independent Checks:**

- Keep subsystem hygiene tests and the broad checks in `tests/package/test_import_hygiene.py`. Their assertions overlap mechanically but guard different dependency and authority boundaries.
- Keep `tests/package/test_public_api.py` as an independent explicit allowlist. Generating it from `src/openrund/__init__.py` would allow accidental exports to pass.
- Keep `tests/package/test_release_hygiene.py`, `tests/package/test_python_only_cutover.py`, `tests/docs/test_documentation.py`, and fixture-integrity tests. They cover distribution, security, documentation, legacy-cutover, and compatibility properties that ordinary unit coverage cannot express.
- Keep `examples/governed_coding.py`: it is a typed, linted, sdist-shipped consumer surface. Its thin delegation to production demo behavior is intentional documentation/distribution coverage, not disposable duplication.

**Safe Consolidation Opportunities:**

1. Move repeated AST import and source-tree traversal helpers from the seven hygiene files under `tests/bundles`, `tests/capabilities`, `tests/engine`, `tests/providers`, `tests/storage`, `tests/views`, and `tests/package` into a typed test-only helper such as `tests/_quality.py`. Preserve every subsystem-specific allowlist, forbidden edge, and assertion in its current test module.
2. Consolidate the sanitized subprocess runner and distribution build discovery duplicated by `tests/package/test_py_typed.py` and `tests/package/test_installed_typing.py` into `tests/package/conftest.py`. A session-scoped wheel/sdist build may reduce repeated work, but retain fresh per-test virtual environments/runtime roots and retain both wheel and sdist proofs.
3. Remove local `sys.path.insert` setup from the five `tests/contracts/test_*.py` files listed in `CONVENTIONS.md`; central pytest and mypy configuration already supplies `src`. Installed-artifact isolation remains independently covered by package tests.
4. The same quality command block appears in `README.md`, `docs/README.md`, and `docs/contributing.md`. Either make `docs/contributing.md` canonical and link to it from the two overview documents, or add a docs test that asserts the three blocks stay synchronized. Do not introduce a `scripts` directory solely for this purpose because `tests/package/test_python_only_cutover.py` deliberately forbids that legacy surface.

**Intentional Duplication to Preserve:**

- `[project.optional-dependencies].test` and `[dependency-groups].dev` repeat tool requirements for two distinct audiences: installed package contributors and repository `uv` development. Consolidate only if one supported install path is deliberately removed.
- The frozen compatibility corpus contains semantically related evidence across subsystems by design. Keep exact bytes, manifest authentication, and consumer-specific assertions.
- Public export expectations, canonical wire expectations, and safe error expectations should remain literal in tests rather than being calculated through the production implementation.
- Repeated checks of engine outcomes and event history are complementary: a returned result alone does not prove the durable authoritative transition.

---

*Testing analysis: 2026-08-06*
