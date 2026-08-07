# Codebase Concerns

**Analysis Date:** 2026-08-06

## Leanness Classification

The repository is product-complete and deliberately contract-heavy: `.planning/STATE.md` records 974 passing tests, 3 opt-in provider checks skipped, and no active milestone. Most apparent duplication is independent compatibility or authority evidence and should not be deleted merely to reduce file count.

| Classification | Concrete paths | Assessment | Recommended action |
|---|---|---|---|
| Essential product code | `src/openrund/` | The 102 tracked Python files implement the typed contracts, codecs, engine authority, deterministic views, SQLite custody, capabilities, providers, bundles, assembly, operator, CLI, and demo. Package-content tests define this surface exactly. | Keep. Simplify internals only behind unchanged public, wire, and authority contracts. |
| Essential normative documentation | `README.md`, `SECURITY.md`, `CHANGELOG.md`, `docs/` | `docs/architecture.md`, `docs/concepts.md`, and the subsystem pages are the implementation contract; package and docs tests validate links, language, sentinels, security text, and release contents. | Keep every topic page. Consolidate repeated command prose, not the normative content. |
| Essential configuration | `pyproject.toml`, `uv.lock`, `.gitignore`, `AGENTS.md` | These define the install/build surface, exact development lock, strict pytest/mypy/Ruff/coverage gates, ignored local output, and repository workflow constraints. | Keep. Do not split configuration across extra tool files without a demonstrated need. |
| Essential consumer examples | `examples/governed_coding.py`, `examples/README.md` | The example is type-checked, linted, included in the source distribution, and demonstrates the production assembly rather than a substitute runtime. | Keep. Avoid adding parallel examples that exercise the same path with different terminology. |
| Essential verification | `tests/` | The 409 tracked test files include frozen evidence; unit count alone overstates duplication because tests independently prove return values, authoritative Events, packaging, docs, redaction, architecture, and recovery. | Keep behavioral assertions. Refactor only mechanical setup and scanners. |
| Essential compatibility oracle | `tests/fixtures/compatibility/v1/manifest.json`, `tests/fixtures/compatibility/v1/` | The 287-file fixture tree is authenticated before semantic use and consumed across contracts, codecs, storage, views, and package integrity. It must remain independent of current production encoders. | Keep byte-for-byte. Never regenerate expectations from `src/openrund/`. |
| Essential private test support | `src/openrund/_testing/` | These typed stores, clocks, factories, and reporters are used throughout the suite and by installed-package typing tests; `docs/api.md` deliberately documents them as private, non-root exports. | Keep unless moved to a separately supported test package with all installed-consumer checks retained. |
| Generated/local-only | `.coverage`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`, `dist/`, `**/__pycache__/` | All are ignored working-tree output. Duplicate local names such as `.mypy_cache/.gitignore 2`, `.pytest_cache/CACHEDIR 2.TAG`, and `dist/.gitignore 2` have no source or release role. | Safe deletion from the local working tree. Regenerate through tests, environment sync, or `uv build` when needed. Do not commit. |
| Active workflow metadata | `.planning/PROJECT.md`, `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/MILESTONES.md`, `.planning/config.json`, `.planning/codebase/` | These are not shipped in wheel/sdist but guide GSD and future changes. The live documents are already compact. | Keep while GSD is used. Refresh codebase maps after structural changes. |
| Historical-only workflow evidence | `.planning/milestones/`, `.planning/RETROSPECTIVE.md` | `.planning/milestones/` contains 455 tracked files across shipped milestones and project history. They do not affect runtime, tests, wheels, or source distributions. | Candidate for external archive or GSD cleanup, not an unreviewed delete. Retain summaries/audits/requirements or a tagged immutable copy before pruning detailed phase records. |
| Redundant mechanics | Five contract-test path insertions, repeated test scanners/build helpers, repeated quality command blocks | These repeat setup rather than contract expectations. Exact paths and safe approaches are ranked below. | Refactor or remove the repeated mechanics; preserve independent assertions. |

## Ranked Simplification Opportunities

| Rank | Candidate | Change kind | Value | Risk | Safe boundary |
|---:|---|---|---|---|---|
| 1 | Remove ignored local output under `.coverage`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`, `dist/`, and `**/__pycache__/` | Deletion, local-only | High immediate workspace and disk cleanup | Low | Confirm every target is ignored/untracked; use explicit paths and allow tools to regenerate them. |
| 2 | Remove per-file `sys.path.insert` setup in `tests/contracts/test_ids.py`, `tests/contracts/test_errors.py`, `tests/contracts/test_values.py`, `tests/contracts/test_paths.py`, and `tests/contracts/test_leaf_concepts.py` | Deletion of redundant test setup | Small but certain reduction in import ambiguity | Low | `pyproject.toml` already configures pytest `pythonpath = ["src"]` and mypy `mypy_path = ["src"]`; rerun the five files plus strict mypy and the full suite. |
| 3 | Share AST/source traversal utilities used by `tests/bundles/test_hygiene.py`, `tests/capabilities/test_hygiene.py`, `tests/engine/test_coordination_hygiene.py`, `tests/providers/test_hygiene.py`, `tests/storage/test_hygiene.py`, `tests/views/test_view_hygiene.py`, and `tests/package/test_import_hygiene.py` | Test refactor | Medium maintainability gain | Low–Medium | Centralize only parsing/enumeration in a typed test helper. Keep every subsystem's independent forbidden edges, allowlists, and failure messages. |
| 4 | Share distribution build/subprocess setup between `tests/package/test_py_typed.py` and `tests/package/test_installed_typing.py` | Test refactor | Medium test-runtime and maintenance gain | Medium | Build wheel/sdist once per appropriate scope, but retain fresh installed environments, both artifact kinds, source-tree isolation, typing, and exact-content assertions. |
| 5 | Make one quality-command block canonical | Documentation refactor | Medium drift reduction | Low | Keep the full block in `docs/contributing.md`; replace repeated blocks in `README.md` and `docs/README.md` with links, or test that all three remain identical. Do not delete the overview documents. |
| 6 | Archive detailed shipped planning records | Conditional repository deletion after archival | High file-count reduction; no runtime/package effect | Medium–High | Preserve `.planning/MILESTONES.md`, milestone roadmaps/requirements/audits, and a git tag or external immutable archive before pruning `.planning/milestones/*-phases/` and `.planning/milestones/project-history/`. Use the GSD cleanup workflow rather than ad hoc deletion. |
| 7 | Split the largest contract and boundary modules | Source refactor, not deletion | Medium navigation and review improvement | High | Preserve exports, event/command discriminants, codecs, error codes, and exact package contents. Start with internal partitions behind existing `__init__.py` barrels and compatibility corpus tests. |

Do not treat line count as permission to delete `src/openrund/contracts/events.py`, `src/openrund/contracts/commands.py`, the frozen fixture corpus, subsystem hygiene tests, or the explicit export oracle in `tests/package/test_public_api.py`. Their repetition is the mechanism that makes contract drift observable.

## Tech Debt

**Large contract catalogs:**

- Issue: `src/openrund/contracts/events.py` is 2,227 lines, `src/openrund/contracts/commands.py` is 1,693 lines, and `src/openrund/contracts/runs.py` is 927 lines. Closed catalogs, validation, and related semantic records are concentrated in single modules.
- Files: `src/openrund/contracts/events.py`, `src/openrund/contracts/commands.py`, `src/openrund/contracts/runs.py`, `src/openrund/codec/_events.py`, `src/openrund/codec/_commands.py`
- Impact: Reviews are broad, import cycles are easier to introduce, and a new event or command requires synchronized changes across large files and exact codecs.
- Fix approach: Partition private definitions by lifecycle domain while keeping current package exports and discriminants stable. Treat `tests/contracts`, `tests/codec`, `tests/package/test_public_api.py`, and the compatibility corpus as mandatory migration gates. This is a refactor, never a catalog deletion.

**Broad orchestration modules:**

- Issue: `src/openrund/operator/_service.py` (914 lines), `src/openrund/engine/_governance.py` (884), `src/openrund/engine/_legality.py` (770), and `src/openrund/engine/_delegation.py` (755) each coordinate many related cases.
- Files: `src/openrund/operator/_service.py`, `src/openrund/engine/_governance.py`, `src/openrund/engine/_legality.py`, `src/openrund/engine/_delegation.py`
- Impact: Small semantic changes can touch dense dispatch logic and risk inconsistent event materialization or error mapping.
- Fix approach: Extract cohesive private decision tables/helpers by command family while preserving one Engine-owned mutation path. Do not introduce a service layer that can append Events independently.

**Repeated quality mechanics:**

- Issue: AST import scanning, source enumeration, distribution building, subprocess sanitization, and source-path setup are repeated across tests.
- Files: `tests/package/test_import_hygiene.py`, `tests/package/test_release_hygiene.py`, `tests/package/test_py_typed.py`, `tests/package/test_installed_typing.py`, subsystem `test_hygiene.py` files, five `tests/contracts/test_*.py` files named in the ranking
- Impact: Mechanical changes need several edits and can drift while appearing to preserve the same guard.
- Fix approach: Share mechanisms through test-only helpers; keep expected dependency rules, public surfaces, artifact contents, and negative cases literal and local to each test.

**Quality gates are local rather than continuously automated:**

- Issue: `pyproject.toml` defines strong gates and `docs/contributing.md` documents them, but no repository CI workflow is present.
- Files: `pyproject.toml`, `docs/contributing.md`, `tests/package/test_release_hygiene.py`
- Impact: A contributor can merge or publish without automatically repeating the 3.12–3.14, installed-artifact, coverage, type, lint, docs, and security matrix.
- Fix approach: If remote collaboration or automated releases begin, add one minimal CI workflow that invokes the canonical commands. Avoid duplicating tool configuration inside the workflow.

**Historical planning volume:**

- Issue: Completed workflow evidence dominates repository file count despite no active milestone.
- Files: `.planning/milestones/v2.0-phases/`, `.planning/milestones/v1.3-phases/`, `.planning/milestones/project-history/`, `.planning/milestones/260513-ontology-governance-audit/`
- Impact: Search results and repository browsing include obsolete implementation plans, and new agents may mistake archived statements for current contracts.
- Fix approach: Keep active state and shipped milestone summaries in place; archive detailed records through a deliberate GSD cleanup with links and immutable provenance. Runtime leanness does not require this because `.planning/` is already absent from built artifacts.

## Known Bugs

**No reproducible product bug detected in the current tree:**

- Symptoms: None established by repository evidence. `.planning/STATE.md` reports the v2.0 audit passed with 974 tests and no product gaps.
- Files: `.planning/STATE.md`, `.planning/milestones/v2.0-MILESTONE-AUDIT.md`
- Trigger: Not applicable.
- Workaround: Not applicable. Treat future failures as bugs only after reproducing them against the current Python package; archived predecessor issues under `.planning/milestones/project-history/` are not current defects.

**Local duplicate cache/build filenames:**

- Symptoms: Ignored directories contain names such as `.mypy_cache/.gitignore 2`, `.pytest_cache/README 2.md`, and `dist/.gitignore 2`.
- Files: `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `dist/`
- Trigger: Local tooling or filesystem synchronization creates duplicate generated entries.
- Workaround: Remove the explicit ignored cache/build directories and regenerate. This is workspace hygiene, not a product bug.

## Security Considerations

**Filesystem and subprocess capabilities:**

- Risk: Path substitution, traversal, symlink races, unbounded I/O, executable substitution, unsafe Git configuration, or shell interpretation could turn a capability into an authority escape.
- Files: `src/openrund/capabilities/filesystem.py`, `src/openrund/capabilities/process.py`, `src/openrund/capabilities/git.py`, `src/openrund/capabilities/documents.py`, `src/openrund/capabilities/documents_worker.py`, `src/openrund/capabilities/_sandbox.py`, `src/openrund/capabilities/_transports.py`
- Current mitigation: Explicit root/binding configuration, argument vectors instead of shells, bounded bytes/time/path counts, containment and regular-file checks, result-only worker protocols, evidence artifacts, cancellation cleanup, and adversarial tests under `tests/capabilities/`.
- Recommendations: Preserve duplicated checks at separate trust boundaries unless equivalence is proven. Any refactor must rerun traversal, symlink, mutation, timeout, output-bound, cancellation, and local Git integration tests.

**Provider transport and credentials:**

- Risk: Ambient credentials, malformed/oversized HTTP or SSE responses, retry ambiguity, or provider output treated as an authoritative command.
- Files: `src/openrund/providers/_http.py`, `src/openrund/providers/openai.py`, `src/openrund/providers/anthropic.py`, `src/openrund/runtime/_loop.py`, `tests/providers/`, `tests/package/test_release_hygiene.py`
- Current mitigation: Credentials are explicit inputs, normal source is statically checked against ambient provider credential names, payloads are bounded and strictly decoded, and model output remains proposal-only.
- Recommendations: Keep live-provider checks opt-in, but run them on a controlled release cadence. Never simplify providers by reading common environment keys in production source.

**Artifact and bundle file custody:**

- Risk: Symlink replacement, content/hash mismatch, partial import/export, oversized bundles, or exposing host paths.
- Files: `src/openrund/storage/_artifacts.py`, `src/openrund/bundles/_verify.py`, `src/openrund/bundles/_importing.py`, `src/openrund/bundles/_paths.py`, `tests/storage/`, `tests/bundles/`
- Current mitigation: `O_NOFOLLOW` where available, `fstat` regular-file checks, size/hash validation, bounded bundle files/event logs, contained portable paths, staged atomic publication, and verification before replay/import.
- Recommendations: Keep independent verify/import checks even when they appear redundant. Avoid centralizing path validation into a helper that changes time-of-check/time-of-use behavior.

**Safe error surface:**

- Risk: Low-level exceptions can disclose credentials, absolute paths, payloads, or database details.
- Files: `src/openrund/errors.py`, storage/provider/capability boundary modules, `tests/contracts/test_errors.py`
- Current mitigation: Stable semantic codes, bounded/redacted safe details, explicit translation, and tests for secret/path omission.
- Recommendations: Preserve `raise ... from None` at disclosure-sensitive boundaries and add redaction cases for every new external adapter.

## Performance Bottlenecks

**Full-history replay:**

- Problem: Common engine, operator, bundle export, and view operations load complete event slices and rebuild several views from the beginning.
- Files: `src/openrund/storage/_events.py`, `src/openrund/engine/_engine.py`, `src/openrund/operator/_service.py`, `src/openrund/views/_rebuild.py`, `src/openrund/views/_history.py`, `src/openrund/bundles/_export.py`
- Cause: Canonical truth is the ordered Event history and persisted View snapshots are explicitly out of scope in `.planning/PROJECT.md`; SQLite `read(..., limit=None)` uses `fetchall`, and projections scan the complete history.
- Improvement path: Keep this simple design for the local MVP. Before adding snapshots, benchmark long histories and define an authoritative snapshot/event-watermark contract; pagination alone cannot replace complete-watermark validation.

**Whole-blob reads and hashing:**

- Problem: Artifact retrieval reads the complete blob into memory before validating its hash, and bundle export can retain artifact content while constructing output.
- Files: `src/openrund/storage/_artifacts.py`, `src/openrund/bundles/_export.py`, `src/openrund/bundles/_verify.py`
- Cause: The local API represents content as immutable `bytes`; artifact metadata does not impose one universal product-level maximum comparable to capability-specific limits.
- Improvement path: If large artifacts become common, add a streaming verified-read API with an explicit maximum and staged hash validation. Keep the existing exact-byte API for bounded callers.

**Repeated distribution builds in tests:**

- Problem: Package tests independently invoke builds and isolated installations.
- Files: `tests/package/test_py_typed.py`, `tests/package/test_installed_typing.py`
- Cause: Each test owns its artifact setup to guarantee isolation.
- Improvement path: Share one authenticated wheel/sdist build per test session while retaining independent installations and exact-content checks.

**Large fixture manifest parsing:**

- Problem: `tests/fixtures/compatibility/v1/manifest.json` is 26,889 lines and is authenticated/parsed for compatibility selections.
- Files: `tests/fixtures/compatibility/v1/manifest.json`, `tests/conftest.py`, `tests/package/test_fixture_integrity.py`
- Cause: The manifest intentionally enumerates frozen evidence with lengths and hashes.
- Improvement path: Do not compact or generate it merely for speed. Cache the immutable parsed manifest within the pytest session, as the current session-scoped fixture pattern permits, and preserve integrity-before-meaning ordering.

## Fragile Areas

**Event/Command/Codec synchronization:**

- Files: `src/openrund/contracts/events.py`, `src/openrund/contracts/commands.py`, `src/openrund/codec/_events.py`, `src/openrund/codec/_commands.py`, `tests/contracts/`, `tests/codec/`, `tests/fixtures/compatibility/v1/`
- Why fragile: Stable type names, discriminants, exact keys, missing-versus-null semantics, versions, and canonical bytes must evolve together.
- Safe modification: Add contract and negative tests first, update explicit codecs, preserve unsupported-version behavior, then extend frozen evidence without rewriting existing cases.
- Test coverage: Strong. The remaining risk is process discipline: deriving expectations from the new implementation would silently erase the oracle.

**Engine sole-authority boundary:**

- Files: `src/openrund/engine/`, `src/openrund/runtime/_loop.py`, `src/openrund/capabilities/_runner.py`, `src/openrund/operator/_service.py`, `tests/engine/`, `tests/package/test_import_hygiene.py`
- Why fragile: Providers, workers, CLI, imports, and recovery may propose work but must never materialize lifecycle Events outside the Engine.
- Safe modification: Route every mutation origin through a typed Command, legality decision, atomic append, and authoritative replay. Keep AST hygiene checks local and broad.
- Test coverage: Strong behavioral and static coverage; new adapter categories need a new forbidden-authority-edge assertion.

**SQLite transaction and artifact publication:**

- Files: `src/openrund/storage/_database.py`, `src/openrund/storage/_events.py`, `src/openrund/storage/_artifacts.py`, `src/openrund/storage/_leases.py`, `tests/storage/`
- Why fragile: Database commits, filesystem publication, expected positions, lease fencing, rollback, recovery, and corruption translation cross process and storage boundaries.
- Safe modification: Preserve WAL/FULL synchronization, bounded busy timeouts, absent-only publication, post-failure recovery, and token fencing. Exercise real SQLite rather than mocks.
- Test coverage: Strong local concurrency and fault-injection coverage; no distributed-storage semantics exist by design.

**Package/public surface:**

- Files: `src/openrund/__init__.py`, package `__init__.py` files, `pyproject.toml`, `tests/package/test_public_api.py`, `tests/package/test_py_typed.py`, `tests/package/test_installed_typing.py`
- Why fragile: A seemingly harmless export or file move changes the supported API or exact wheel/sdist contents.
- Safe modification: Update explicit `__all__`, public docs, expected package contents, installed imports, and typing consumers together. Do not calculate the expected API from production exports.
- Test coverage: Strong; release checks must be run against built artifacts, not only the source checkout.

**Normative docs and implementation terminology:**

- Files: `docs/architecture.md`, `docs/concepts.md`, `docs/events.md`, `docs/api.md`, `tests/docs/test_documentation.py`, `AGENTS.md`
- Why fragile: Ontology wording encodes authority distinctions; generic rewriting can turn explanatory Views/Reports into implied sources of truth.
- Safe modification: Preserve canonical capitalization and authority language, update corresponding code/tests, and run link/sentinel checks.
- Test coverage: Links and key sentinels are checked; semantic contradictions still require human architectural review.

## Scaling Limits

**Single-node SQLite custody:**

- Current capacity: One local SQLite database using WAL, synchronous FULL, indexed per-Run event streams, and token-fenced leases.
- Limit: Hosted multi-tenancy, sharding, distributed storage, and high availability are explicitly out of scope in `.planning/PROJECT.md`; write coordination remains SQLite/process-local.
- Scaling path: Add a new storage adapter behind existing ports only after specifying atomic cross-stream append, expected-position, integrity, and lease-fencing semantics. Do not relax the Engine boundary to scale.

**Replay-derived views:**

- Current capacity: Views rebuild deterministically from complete event histories and a complete watermark.
- Limit: CPU and memory grow with Run history and number of projections; no persisted authoritative view snapshot exists.
- Scaling path: Measure representative long Runs, then define snapshot validation against an immutable event watermark. Keep fallback full replay for audit and recovery.

**Local capability workers:**

- Current capacity: Explicit mounted roots, bounded local subprocesses, local Git, filesystem, and Markdown document workers.
- Limit: Broad capability catalogs, plugin discovery, remote scheduling, and automatic cross-environment resume are outside current scope.
- Scaling path: Add transported workers through the existing result-only protocol and explicit capability registry; keep roots, limits, evidence, and Engine Commands explicit.

## Dependencies at Risk

**Runtime dependencies:**

- Risk: No third-party runtime dependency is present; `pyproject.toml` declares an empty base dependency list. This minimizes supply-chain and compatibility risk.
- Impact: Platform behavior depends on Python 3.12+ and the standard library; SQLite and filesystem semantics still vary by host.
- Migration plan: Keep the base dependency-free unless a new dependency removes more complexity than it adds. Verify any addition across supported interpreters and built artifacts.

**Development/build toolchain:**

- Risk: `coverage`, `mypy`, `pytest`, and `ruff` have lower bounds in both `[project.optional-dependencies].test` and `[dependency-groups].dev`; Hatchling builds the package and `uv.lock` pins the repository environment. The duplicated declarations can drift.
- Impact: An `openrund[test]` installation and a repository `uv` environment could select different minimum tool sets if only one list is updated.
- Migration plan: Keep both audiences, add a test that asserts the shared requirements match, and update `uv.lock` with either list. Do not delete one declaration unless its installation workflow is dropped.

## Missing Critical Features

**No critical feature gap for the shipped local v2.0 scope:**

- Problem: None established. `.planning/PROJECT.md` explicitly excludes hosted multi-tenancy, distributed/high-availability storage, broad plugin discovery, persisted View snapshots, automatic cross-environment resume, and a graphical interface.
- Blocks: These exclusions block broader deployment models, not the documented local durable runtime.

**Continuous gate automation:**

- Problem: The repository has no detected CI workflow even though release gates are comprehensive.
- Blocks: Automatic enforcement on remote changes and repeatable release evidence across Python 3.12–3.14.
- Priority: Medium when the project accepts remote changes or automates publication; low for a deliberately local-only workflow.

## Test Coverage Gaps

**External provider drift:**

- What's not tested: Live Anthropic/OpenAI behavior in the ordinary offline suite; 3 live checks are intentionally skipped unless configured.
- Files: `tests/providers/test_live.py`, `src/openrund/providers/openai.py`, `src/openrund/providers/anthropic.py`
- Risk: Provider protocol changes can pass local fake-server tests but fail against the service.
- Priority: Medium. Run opt-in checks on a controlled release schedule with explicit credentials and cost bounds.

**Scale and performance thresholds:**

- What's not tested: No benchmark/load suite defines acceptable latency or memory for very long histories, large artifact collections, concurrent Runs, or maximum-size bundles.
- Files: `src/openrund/views/_rebuild.py`, `src/openrund/storage/_events.py`, `src/openrund/storage/_artifacts.py`, `src/openrund/bundles/_export.py`
- Risk: Correct behavior may degrade sharply before a future deployment reaches its desired scale.
- Priority: Medium before expanding beyond the local MVP; low for the current documented scope.

**Automated platform/interpreter matrix:**

- What's not tested: No checked-in CI configuration automatically repeats the documented Python 3.12–3.14 and installed-artifact gates on each change.
- Files: `pyproject.toml`, `docs/contributing.md`, `tests/package/test_installed_typing.py`
- Risk: Host-specific SQLite, subprocess, symlink, or packaging regressions can depend on a maintainer's local verification environment.
- Priority: Medium for collaborative development and release automation.

---

*Concerns audit: 2026-08-06*
