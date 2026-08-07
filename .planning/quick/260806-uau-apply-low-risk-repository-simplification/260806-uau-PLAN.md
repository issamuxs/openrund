---
quick_id: 260806-uau
phase: quick-260806-uau
plan: "01"
type: execute
wave: 1
depends_on: []
status: ready
description: Apply low-risk repository simplifications from the codebase map
autonomous: true
files_modified:
  - tests/contracts/test_ids.py
  - tests/contracts/test_errors.py
  - tests/contracts/test_values.py
  - tests/contracts/test_paths.py
  - tests/contracts/test_leaf_concepts.py
  - tests/_quality.py
  - tests/bundles/test_hygiene.py
  - tests/capabilities/test_hygiene.py
  - tests/engine/test_coordination_hygiene.py
  - tests/providers/test_hygiene.py
  - tests/storage/test_hygiene.py
  - tests/views/test_view_hygiene.py
  - tests/package/test_import_hygiene.py
  - tests/package/_distributions.py
  - tests/package/conftest.py
  - tests/package/test_py_typed.py
  - tests/package/test_installed_typing.py
  - README.md
  - docs/README.md
  - docs/contributing.md
  - tests/docs/test_documentation.py
must_haves:
  truths:
    - "Disposable local output and the empty duplicate environment directory are gone, while the working .venv symlink and its target are unchanged."
    - "Contract tests import through the centrally configured src layout without per-file path mutation."
    - "Hygiene tests share typed parsing and traversal mechanics while retaining their local architectural rules, allowlists, failure messages, and assertions."
    - "Packaging tests share build and subprocess mechanics while every installed-artifact test still uses a fresh environment isolated from the source tree."
    - "docs/contributing.md is the sole complete quality-command reference, and both overview documents link readers to it."
  artifacts:
    - path: "tests/_quality.py"
      provides: "Typed test-only Python source enumeration, parsing, and import extraction mechanics"
    - path: "tests/package/_distributions.py"
      provides: "Typed distribution build, checked subprocess, and fresh artifact installation mechanics"
    - path: "tests/package/conftest.py"
      provides: "Session-scoped wheel and source-distribution fixture"
    - path: "docs/contributing.md"
      provides: "Canonical complete local quality and release command block"
    - path: "tests/docs/test_documentation.py"
      provides: "Executable ownership guard for canonical quality commands and overview links"
  key_links:
    - from: "seven subsystem/package hygiene tests"
      to: "tests/_quality.py"
      via: "typed helper imports for source enumeration, UTF-8 parsing, and import-name extraction"
    - from: "tests/package/test_py_typed.py and tests/package/test_installed_typing.py"
      to: "tests/package/_distributions.py and tests/package/conftest.py"
      via: "shared built artifacts plus a fresh installed environment per installed-behavior test"
    - from: "README.md and docs/README.md"
      to: "docs/contributing.md#development-setup"
      via: "relative Markdown links checked by documentation tests"
---

# Quick Task 260806-uau Plan

## Goal

Reduce local repository clutter and repeated test/documentation mechanics without changing
OpenRund runtime code, public APIs, compatibility evidence, authority assertions, or release
coverage.

## Scope Guardrails

- Remove only observed disposable local output: `.coverage`, `.mypy_cache/`,
  `.pytest_cache/`, `.ruff_cache/`, `dist/`, Python `__pycache__/` directories beneath
  `src/` and `tests/`, and the verified-empty `.venv 2/` directory.
- Preserve the working `.venv` symlink and its current target
  `/Users/issam/.local/share/openrund-venv`.
- Do not modify or delete `.planning/milestones`, runtime modules under `src/openrund`, public
  APIs, compatibility fixtures or assertions, or the supported installed-artifact proofs.
- Do not split runtime modules, add CI, add dependencies, or add a production helper for
  test-only mechanics.

<tasks>

<task type="auto">
  <name>Task 1: Clean disposable output and remove contract-test path mutation</name>
  <files>.coverage, .mypy_cache/, .pytest_cache/, .ruff_cache/, dist/, src/**/__pycache__/, tests/**/__pycache__/, .venv 2/, tests/contracts/test_ids.py, tests/contracts/test_errors.py, tests/contracts/test_values.py, tests/contracts/test_paths.py, tests/contracts/test_leaf_concepts.py</files>
  <action>Before deleting anything, enumerate every exact target, confirm the cache/build paths are ignored and untracked, reject symlinks or unexpected file kinds among deletion targets, and confirm `.venv 2/` is an empty real directory. Record the current `.venv` symlink target, exclude `.venv` from every deletion set, and stop if its type or target differs from the scope guardrail. Remove only the enumerated output directories/files and cache directories below the explicit `src/` and `tests/` roots. In the five named contract tests, delete the module-local source-path mutation and its setup-only imports/comment separator; retain any `Path`, `sys`, or other import still used by actual test behavior. Let Ruff restore the normal standard-library, third-party, and `openrund` import grouping supplied by `pyproject.toml`.</action>
  <verify>
    <automated>test -L .venv &amp;&amp; test "$(readlink .venv)" = "/Users/issam/.local/share/openrund-venv" &amp;&amp; test ! -e '.venv 2' &amp;&amp; test ! -e .coverage &amp;&amp; test ! -e .mypy_cache &amp;&amp; test ! -e .pytest_cache &amp;&amp; test ! -e .ruff_cache &amp;&amp; test ! -e dist &amp;&amp; test -z "$(find src tests -type d -name __pycache__ -print -quit)" &amp;&amp; ! rg -n 'sys\.path\.insert|# isort: split' tests/contracts/test_ids.py tests/contracts/test_errors.py tests/contracts/test_values.py tests/contracts/test_paths.py tests/contracts/test_leaf_concepts.py &amp;&amp; uv run --python 3.12 pytest tests/contracts/test_ids.py tests/contracts/test_errors.py tests/contracts/test_values.py tests/contracts/test_paths.py tests/contracts/test_leaf_concepts.py -q &amp;&amp; uv run ruff check tests/contracts/test_ids.py tests/contracts/test_errors.py tests/contracts/test_values.py tests/contracts/test_paths.py tests/contracts/test_leaf_concepts.py</automated>
  </verify>
  <done>All scoped generated output is absent, the empty duplicate environment directory is removed, `.venv` still resolves to the same working environment, and all five contract modules pass without local import-path setup.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Consolidate typed hygiene and distribution-test mechanics</name>
  <files>tests/_quality.py, tests/bundles/test_hygiene.py, tests/capabilities/test_hygiene.py, tests/engine/test_coordination_hygiene.py, tests/providers/test_hygiene.py, tests/storage/test_hygiene.py, tests/views/test_view_hygiene.py, tests/package/test_import_hygiene.py, tests/package/_distributions.py, tests/package/conftest.py, tests/package/test_py_typed.py, tests/package/test_installed_typing.py</files>
  <behavior>
    - "The shared quality helper returns deterministically sorted Python paths for shallow and recursive scans, parses UTF-8 source with the filename attached, and extracts both import forms without changing ordering."
    - "Each hygiene module retains its own forbidden prefixes/tokens, allowlists, source-specific exceptions, failure context, and higher-order AST checks."
    - "One package-session build yields exactly one wheel and one source distribution; every installed-behavior test creates a new virtual environment and installs the selected local artifact with no dependencies."
    - "Installed probes run with an allowlisted environment, isolated interpreter flags where already required, and assertions proving the imported module is outside the repository source tree."
  </behavior>
  <action>Create `tests/_quality.py` as a strict-typed test-only module exposing narrow helpers for sorted `.py` enumeration (shallow or recursive), UTF-8 source reading/parsing, and import-name extraction. Refactor the seven named hygiene modules to use those mechanics, but keep storage direct-body traversal, SQLite-call detection, append-authority scans, public-callable scans, and every subsystem rule/assertion local. Create `tests/package/_distributions.py` with final typed records for built and installed artifacts plus checked subprocess, environment, build, and install functions. Preserve two explicit environment policies: repository subprocesses inherit the environment after removing Python/virtualenv path overrides, while installed-artifact subprocesses receive only the current `HOME`, `LANG`, and `PATH`. Add a session-scoped `built_distributions` fixture in `tests/package/conftest.py` using `tmp_path_factory`; assert exactly one wheel and one source archive. Refactor both package test modules to consume the shared artifacts and runner. Build once per package-test session, but create a fresh virtual environment under each test's `tmp_path` before installing either wheel or source archive. Retain exact wheel/sdist content assertions, `py.typed` assertions, representative strict-mypy consumer coverage, installed CLI/demo/worker behavior, and source-tree isolation checks.</action>
  <verify>
    <automated>uv run --python 3.12 pytest tests/bundles/test_hygiene.py tests/capabilities/test_hygiene.py tests/engine/test_coordination_hygiene.py tests/providers/test_hygiene.py tests/storage/test_hygiene.py tests/views/test_view_hygiene.py tests/package/test_import_hygiene.py -q &amp;&amp; uv run --python 3.12 pytest tests/package/test_py_typed.py tests/package/test_installed_typing.py -q &amp;&amp; uv run mypy --strict tests/_quality.py tests/package/_distributions.py tests/package/conftest.py tests/bundles/test_hygiene.py tests/capabilities/test_hygiene.py tests/engine/test_coordination_hygiene.py tests/providers/test_hygiene.py tests/storage/test_hygiene.py tests/views/test_view_hygiene.py tests/package/test_import_hygiene.py tests/package/test_py_typed.py tests/package/test_installed_typing.py &amp;&amp; uv run ruff check tests/_quality.py tests/package tests/bundles/test_hygiene.py tests/capabilities/test_hygiene.py tests/engine/test_coordination_hygiene.py tests/providers/test_hygiene.py tests/storage/test_hygiene.py tests/views/test_view_hygiene.py</automated>
  </verify>
  <done>Repeated traversal, parsing, build, and subprocess code has one typed test-only owner; subsystem policy remains independently readable; wheel and source-distribution behavior is still proven from fresh source-isolated installed environments.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Canonicalize quality commands and run repository-wide gates</name>
  <files>README.md, docs/README.md, docs/contributing.md, tests/docs/test_documentation.py</files>
  <behavior>
    - "docs/contributing.md contains the complete ordered quality-command block, including test coverage, strict typing, lint, format, lock, build, and diff checks."
    - "README.md and docs/README.md keep concise verification guidance and link directly to the canonical development-setup section instead of copying the complete block."
    - "Documentation tests fail if the canonical block disappears, an overview restores a second complete copy, or either relative link stops resolving."
  </behavior>
  <action>Keep the full existing command sequence in `docs/contributing.md` under the stable `Development setup` heading and make that section the named canonical source. Replace only the redundant complete blocks in `README.md` and `docs/README.md` with concise audience-appropriate prose and relative links to `docs/contributing.md#development-setup` and `contributing.md#development-setup`, respectively; retain the README checkout smoke command and both overview documents. Extend `tests/docs/test_documentation.py` with an explicit quality-documentation ownership test that checks the complete ordered sequence in the canonical file, the two overview links, and a single complete-block owner. Run documentation checks first, then the complete project test/type/lint/format/lock/build/diff gates. Confirm the tracked diff contains no `.planning/milestones`, `src/openrund`, compatibility fixture, public-API oracle, or CI path.</action>
  <verify>
    <automated>uv run --python 3.12 pytest tests/docs/test_documentation.py tests/package/test_py_typed.py tests/package/test_installed_typing.py -q &amp;&amp; uv run --python 3.12 coverage run -m pytest -q &amp;&amp; uv run coverage report &amp;&amp; uv run mypy --strict src/openrund tests examples &amp;&amp; uv run ruff check src tests examples &amp;&amp; uv run ruff format --check src tests examples &amp;&amp; uv lock --check &amp;&amp; uv build &amp;&amp; git diff --check &amp;&amp; test -z "$(git diff --name-only -- .planning/milestones src/openrund tests/fixtures tests/package/test_public_api.py .github)" &amp;&amp; test -L .venv &amp;&amp; test "$(readlink .venv)" = "/Users/issam/.local/share/openrund-venv"</automated>
  </verify>
  <done>The complete quality command block has one canonical documentation owner, overview readers reach it through valid links, all repository gates pass, and the diff stays inside the locked simplification scope.</done>
</task>

</tasks>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Cleanup target selection → local filesystem | Explicit ignored paths and cache directories are deleted while the working virtual-environment symlink crosses out of the repository and must remain untouched. |
| Source checkout → installed artifact probe | Package tests must prove the wheel/source archive in a fresh environment without repository imports or ambient Python path overrides. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-uau-01 | Tampering | Cleanup task | high | mitigate | Enumerate exact targets; reject symlink/unexpected kinds; require `.venv 2/` to be empty; preserve and re-check the `.venv` symlink target before and after cleanup. |
| T-uau-02 | Tampering | Distribution helper and installed tests | high | mitigate | Keep fresh per-test virtual environments, local no-dependency installs, exact artifact counts/content, isolated interpreter probes, and source-tree exclusion assertions. |
| T-uau-03 | Information Disclosure | Installed subprocess environment | medium | mitigate | Preserve the installed-test environment allowlist containing only `HOME`, `LANG`, and `PATH`; do not merge it with the broader repository subprocess environment. |
| T-uau-04 | Repudiation | Hygiene/documentation consolidation | low | accept | All subsystem assertions remain local and the docs ownership rule becomes executable; focused and full-suite gates provide reviewable evidence of unchanged contracts. |

</threat_model>

## Source Coverage Audit

| Source | Item | Task | Status |
|--------|------|------|--------|
| GOAL | Apply the map's low-risk repository simplifications without product changes | 1-3 | COVERED |
| LOCKED SCOPE 1 | Remove disposable output and empty `.venv 2/`; preserve `.venv` | 1 | COVERED |
| LOCKED SCOPE 2 | Remove five redundant contract-test path insertions | 1 | COVERED |
| LOCKED SCOPE 3 | Share typed hygiene traversal mechanics while preserving local rules | 2 | COVERED |
| LOCKED SCOPE 4 | Share package build/subprocess mechanics without weakening installed checks | 2 | COVERED |
| LOCKED SCOPE 5 | Canonicalize the complete quality block in `docs/contributing.md` | 3 | COVERED |
| EXCLUSIONS | Planning history, runtime/API/module changes, compatibility evidence, `.venv`, and CI remain untouched | 1-3 | COVERED |

## Success Criteria

- All five locked simplifications are implemented with no deferred item.
- Only test infrastructure, four live documentation/test files, and ignored local output change.
- The existing `.venv` symlink remains usable and unchanged.
- Hygiene and packaging assertions retain their independent contract evidence.
- Focused checks and the canonical full quality sequence pass on Python 3.12.

