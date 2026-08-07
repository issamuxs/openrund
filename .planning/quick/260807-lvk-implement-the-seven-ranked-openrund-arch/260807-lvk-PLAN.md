---
quick_id: 260807-lvk
phase: quick-260807-lvk
plan: "01"
type: execute
wave: 1
depends_on: []
status: ready
description: Implement the seven ranked OpenRund architecture review improvements in order
autonomous: true
requirements:
  - ARCH-01
  - ARCH-02
  - ARCH-03
  - ARCH-04
  - ARCH-05
  - ARCH-06
  - ARCH-07
  - ARCH-08
files_modified:
  - src/openrund/ports/runtime.py
  - src/openrund/cli.py
  - src/openrund/demo.py
  - src/openrund/engine/_engine.py
  - src/openrund/engine/_legality.py
  - src/openrund/engine/_delegation.py
  - src/openrund/engine/_events.py
  - src/openrund/_localfs.py
  - src/openrund/assembly/_factory.py
  - src/openrund/storage/_layout.py
  - src/openrund/storage/_artifacts.py
  - src/openrund/bundles/_paths.py
  - src/openrund/bundles/_export.py
  - src/openrund/bundles/_verify.py
  - src/openrund/bundles/_importing.py
  - src/openrund/operator/_model.py
  - src/openrund/operator/_service.py
  - src/openrund/operator/_render.py
  - src/openrund/operator/__init__.py
  - README.md
  - docs/control.md
  - docs/concepts.md
  - docs/architecture.md
  - docs/api.md
  - tests/ports/test_runtime_protocols.py
  - tests/cli/test_commands.py
  - tests/docs/test_documentation.py
  - tests/engine/test_engine.py
  - tests/engine/test_legality.py
  - tests/engine/test_concurrency.py
  - tests/engine/test_delegation.py
  - tests/engine/test_delegation_lifecycle.py
  - tests/test_localfs.py
  - tests/assembly/test_local_runtime.py
  - tests/storage/test_layout.py
  - tests/storage/test_artifacts.py
  - tests/storage/test_artifact_recovery.py
  - tests/bundles/test_export.py
  - tests/bundles/test_verify.py
  - tests/bundles/test_import.py
  - tests/bundles/test_malicious.py
  - tests/operator/test_results.py
  - tests/operator/test_service.py
  - tests/demo/test_governed_coding.py
  - tests/package/test_public_api.py
  - tests/package/test_py_typed.py
  - tests/package/test_installed_typing.py
must_haves:
  truths:
    - "Help and every malformed CLI invocation are completely parsed before local runtime or SQLite custody can be opened, while demo remains a normal parsed command route."
    - "docs/control.md is the single normative authority-loop owner and consistently distinguishes RuntimeEngine as the procedural mutation boundary from CommandDecision as the authoritative result of one attempted mutation."
    - "RuntimeEngine.submit(Command) remains the only public mutation path and performs one complete replay per loaded stream before legality, Event planning, and atomic append."
    - "Shared local filesystem mechanics remain symlink-safe, no-overwrite, and durable without absorbing domain validation, stable error codes, or independent checks at separate trust boundaries."
    - "Operator success data is statically typed until the rendering adapter converts it to the unchanged text/JSON wire shape; migrated callers require no operator-data type suppressions."
    - "The exact 2.x package-root facade remains compatible, advanced access is documented through named subpackages, and any contraction is explicitly reserved for a major release."
    - "The test extra and development dependency group have identical package names, extras, lower bounds, and ordering."
    - "Frozen compatibility evidence, Event/Command catalogs, Bundle verification/import defenses, rebuild_views, and production/in-memory adapter seams retain their independent coverage."
  artifacts:
    - path: "src/openrund/cli.py"
      provides: "Custody-free complete parsing into typed CLI command variants followed by route execution"
    - path: "docs/control.md"
      provides: "Normative authority-loop contract"
    - path: "src/openrund/engine/_engine.py"
      provides: "Deep private command-attempt orchestration behind unchanged RuntimeEngine.submit"
    - path: "src/openrund/_localfs.py"
      provides: "Private low-level local filesystem-custody primitives with no domain policy"
    - path: "src/openrund/operator/_model.py"
      provides: "Generic OperatorResult and immutable typed success payloads"
    - path: "src/openrund/operator/_render.py"
      provides: "Sole operator-domain to ordered JSON/text adaptation"
    - path: "tests/package/test_public_api.py"
      provides: "Exact release-sensitive root-facade freeze"
    - path: "tests/package/test_py_typed.py"
      provides: "Exact test-extra/development-group dependency parity guard"
  key_links:
    - from: "src/openrund/cli.py"
      to: "src/openrund/assembly/_factory.py"
      via: "a fully validated parsed command is obtained before create_local_runtime is reachable"
    - from: "src/openrund/engine/_engine.py"
      to: "src/openrund/engine/_legality.py and src/openrund/engine/_events.py"
      via: "one loaded attempt-facts value feeds decision planning and the resulting audit-first atomic batch"
    - from: "src/openrund/_localfs.py"
      to: "assembly, storage, and Bundle custody modules"
      via: "low-level lstat/no-follow/exclusive-write/fsync mechanics wrapped by boundary-specific validation and error translation"
    - from: "src/openrund/operator/_service.py"
      to: "src/openrund/operator/_render.py"
      via: "typed success payloads cross unchanged until the rendering adapter serializes them"
    - from: "docs/api.md and tests/package/test_public_api.py"
      to: "src/openrund/__init__.py"
      via: "documented 2.x compatibility policy plus the unchanged exact __all__ allowlist"
---

# Quick Task 260807-lvk Plan

<objective>
Implement ARCH-01 through ARCH-08 in their ranked order while preserving OpenRund's defining
`Operation -> Command -> CommandDecision -> Events -> Views` path.

Purpose: Deepen the authority, custody, operator, documentation, and release seams identified by
the architecture review without weakening compatibility, security, or independent evidence.

Output: One coherent refactor with focused regression coverage, unchanged public Engine submission,
unchanged CLI wire output, an explicitly frozen 2.x root facade, and all release gates green.
</objective>

<execution_context>
@/Users/issam/.codex/gsd-core/workflows/execute-plan.md
@/Users/issam/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@README.md
@docs/control.md
@docs/concepts.md
@docs/architecture.md
@docs/api.md
@pyproject.toml
@src/openrund/cli.py
@src/openrund/engine/_engine.py
@src/openrund/engine/_legality.py
@src/openrund/operator/_model.py
@src/openrund/operator/_service.py
@src/openrund/operator/_render.py
@src/openrund/__init__.py
@tests/package/test_public_api.py

<interfaces>
Existing contracts that must remain recognizable throughout the refactor:

- `RuntimeEngine.submit(self, command: Command, /) -> CommandResult` is the complete public Engine
  mutation surface; `RuntimeEngine` continues to expose only `submit` and `aclose` publicly.
- A successful append remains one ordered batch beginning with `command.recorded`; accepted target
  Events retain both `command_id` and causation linkage to that record. Delegation and parent
  cancellation retain `append_many` all-or-nothing cross-Run custody.
- `run_cli_process(args, *, operator_input=None) -> CliProcessResult` owns process-level parsing and
  assembly. `execute_cli(args, service)` and `run_cli(args, service, json_output=False)` remain
  supported library entry points.
- `OperatorResult` remains the shared library/CLI result envelope and `OperatorExitCode` values stay
  0, 2, 3, 4, 5, 6, and 70. Existing rendered field names, ordering, and safe failure messages are
  wire contracts.
- `openrund.__all__` and `tests/package/test_public_api.py::EXPECTED_PUBLIC_API` are exact release
  evidence. Named subpackages already expose the advanced APIs and become the preferred documented
  access without deleting root names in this release line.
</interfaces>
</context>

## Scope Guardrails

- Execute the numbered recommendations in order: ARCH-01, ARCH-02, ARCH-03, then ARCH-04 through
  ARCH-08. Each task below is sequential within this single atomic plan.
- Keep `Operation -> Command -> CommandDecision -> Events -> Views` intact. Models, providers,
  workers, operators, CLI code, Views, and filesystem helpers gain no legality or Event-append path.
- Preserve the frozen compatibility corpus, separate package-export and wire-format assertions,
  full Event/Command catalogs, Bundle re-verification/import checks, `rebuild_views`, and both real
  and in-memory adapters. Do not rewrite independent evidence to derive expectations from production.
- Keep the base installation dependency-free. Add no external dependency, protocol/adapter for
  invariant local-filesystem behavior, CI configuration, persisted View authority, or raw Event
  append surface.
- Retain every stable Storage/Bundle/Validation error code and safe-detail policy unless an existing
  focused test proves the code is unreachable and the removal does not affect compatibility evidence.

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Remove the dead aggregate, parse before custody, and establish documentation ownership</name>
  <files>src/openrund/ports/runtime.py, src/openrund/cli.py, README.md, docs/control.md, docs/concepts.md, docs/architecture.md, docs/api.md, tests/ports/test_runtime_protocols.py, tests/cli/test_commands.py, tests/docs/test_documentation.py</files>
  <behavior>
    - "ARCH-01: Clock, IdFactory, ReportEntry, and Reporter retain their narrow contracts, while the unused aggregate dependency value and only construction assertions disappear."
    - "ARCH-02: --help and syntactically or semantically invalid commands produce deterministic results without invoking create_local_runtime, creating the requested home, opening SQLite, or surfacing a hostile storage failure."
    - "ARCH-02: valid normal commands and demo governed-coding are typed parsed-command variants; global options, arity, option multiplicity, enum values, JSON objects, root mappings, and unexpected tokens are validated before dispatch."
    - "ARCH-03: control.md owns the full normative authority loop; README positions the product, concepts.md defines ontology, and architecture.md maps modules while linking to the owner instead of restating competing rules."
    - "ARCH-03: documentation consistently calls RuntimeEngine the sole procedural mutation-authority boundary and CommandDecision the authoritative per-attempt decision recorded before target Events."
  </behavior>
  <action>Implement ARCH-01 first: delete `RuntimeDependencies` from `src/openrund/ports/runtime.py`, remove imports used only by that aggregate, and delete `_dependencies` plus its construction/frozen/store-field tests from `tests/ports/test_runtime_protocols.py`; retain all structural protocol, generic ID factory, reporter immutability, and proposal/result-only tests. Implement ARCH-02 next with test-first parsing: introduce private immutable parsed invocation/command variants inside `src/openrund/cli.py`, make one parser consume the complete argument tuple and reject duplicate/unknown/misplaced options, extra operands, missing values, invalid enums, invalid JSON objects, and invalid root mappings before any route executes. Represent help and governed-coding demo in the same parsed command union as operator routes. Make `run_cli_process` parse first, return help/usage immediately when appropriate, and only then open the exact custody required by the selected valid route; demo dispatch may call its production assembly only after its full route has parsed. Keep `execute_cli` and `run_cli` compatible by parsing then dispatching through the supplied service, and keep cancellation/process interrupts outside ordinary failure conversion. Add monkeypatch and filesystem assertions showing help and invalid commands cannot call the runtime factory, create `--home`, touch SQLite/Artifacts, or expose storage errors. Implement ARCH-03 last: make `docs/control.md` explicitly normative; reduce README authority text to positioning plus the invariant path/link; keep `docs/concepts.md` to ontology and `docs/architecture.md` to module/responsibility wiring, both linking to control. Resolve the existing boundary wording with the RuntimeEngine/CommandDecision distinction above, update `docs/api.md` consistently, and add a documentation ownership test that checks the roles, links, invariant path, and terminology without requiring duplicated prose.</action>
  <verify>
    <automated>uv run --python 3.12 pytest tests/ports/test_runtime_protocols.py tests/cli/test_commands.py tests/docs/test_documentation.py -q &amp;&amp; uv run mypy --strict src/openrund/ports/runtime.py src/openrund/cli.py tests/ports/test_runtime_protocols.py tests/cli/test_commands.py tests/docs/test_documentation.py &amp;&amp; uv run ruff check src/openrund/ports/runtime.py src/openrund/cli.py tests/ports/test_runtime_protocols.py tests/cli/test_commands.py tests/docs/test_documentation.py</automated>
  </verify>
  <done>ARCH-01, ARCH-02, and ARCH-03 are complete in order: no unused aggregate remains; complete command validation precedes custody for every route; demo is a parsed route; and one executable documentation ownership contract resolves the authority terminology.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Deepen command attempts and consolidate hardened filesystem mechanics</name>
  <files>src/openrund/engine/_engine.py, src/openrund/engine/_legality.py, src/openrund/engine/_delegation.py, src/openrund/engine/_events.py, src/openrund/_localfs.py, src/openrund/assembly/_factory.py, src/openrund/storage/_layout.py, src/openrund/storage/_artifacts.py, src/openrund/bundles/_paths.py, src/openrund/bundles/_export.py, src/openrund/bundles/_verify.py, src/openrund/bundles/_importing.py, tests/engine/test_engine.py, tests/engine/test_legality.py, tests/engine/test_concurrency.py, tests/engine/test_delegation.py, tests/engine/test_delegation_lifecycle.py, tests/test_localfs.py, tests/assembly/test_local_runtime.py, tests/storage/test_layout.py, tests/storage/test_artifacts.py, tests/storage/test_artifact_recovery.py, tests/bundles/test_export.py, tests/bundles/test_verify.py, tests/bundles/test_import.py, tests/bundles/test_malicious.py</files>
  <behavior>
    - "ARCH-04: each Run history load validates continuity and produces its complete View replay once; submit does not immediately replay the same Event slice again."
    - "ARCH-04: duplicate recovery, idempotency supersession, all decision branches, deferred approval, conflict retry, Delegation establishment/handoff, and parent cancellation still commit exact audit-first batches through submit."
    - "ARCH-04: authority tests exercise RuntimeEngine.submit and inspect durable command.recorded/target Events rather than treating the private legality evaluator as an alternate authority API."
    - "ARCH-05: shared primitives reject symlink/non-directory ancestors, use no-follow descriptors where supported, create/write exclusively, fsync files/directories, bound reads, and never overwrite an existing publication."
    - "ARCH-05: assembly, Run-home, Artifact, Bundle export, Bundle verification, and Bundle import retain their distinct containment, topology, hash, recovery, collision, re-verification, and stable error checks."
  </behavior>
  <action>Implement ARCH-04 first. Replace `_history`'s discarded replay with a private frozen loaded-history value carrying `events`, `watermark`, and `CompleteViewReplay`; use the same loader for parent and child streams so each read is continuity-checked and replayed exactly once. Deepen `RuntimeEngine.submit` behind private command-attempt orchestration that owns fact loading, durable duplicate/idempotency lookup, current-time/ID allocation, legality, Event planning, and the final expected-position `append` or cross-Run `append_many`; keep the public signature and retry semantics unchanged, and rebuild a fresh attempt after every conflict. Replace the long set of Delegation/cancellation booleans passed to `evaluate_command` with one or two immutable attempt-fact values whose fields are populated from actual loaded child histories and available dependencies. Keep the evaluator pure, Event intent materialization downstream of an accepted/deferred decision, `command.recorded` first, and infrastructure failures as exceptions rather than fabricated rejections. Move the core lifecycle cases in `tests/engine/test_legality.py` to `RuntimeEngine.submit`, assert decision traces plus durable audit/target Events, and add instrumentation proving one View rebuild per loaded stream per attempt; retain focused pure tests only where they cover an internal algorithm not observable through submit. Implement ARCH-05 second. Add private `src/openrund/_localfs.py` containing only mechanics genuinely duplicated across the named consumers: component-wise lstat directory inspection/materialization, regular-file descriptor checks with no-follow behavior, exclusive private file creation/write+fsync, bounded regular-file reads, and directory fsync. Use small functions/frozen internal failure reasons, not a protocol, service, policy object, or public export. Keep component/domain validation and error translation in each caller: Run IDs in storage, Artifact IDs/integrity/recovery in Artifact custody, portable paths/topology/commitments in Bundles, configuration in assembly, and verify-copy-reverify/publish in import. Preserve independent pre- and post-operation checks where the same bytes/path cross different trust boundaries. Add primitive tests plus retain/extend consumer tests for symlink ancestors, non-directories, collisions, mutation between checks, absent-only publication, crash recovery, tampered Bundles, malicious topology, and atomic import/export.</action>
  <verify>
    <automated>uv run --python 3.12 pytest tests/engine/test_engine.py tests/engine/test_legality.py tests/engine/test_concurrency.py tests/engine/test_delegation.py tests/engine/test_delegation_lifecycle.py tests/test_localfs.py tests/assembly/test_local_runtime.py tests/storage/test_layout.py tests/storage/test_artifacts.py tests/storage/test_artifact_recovery.py tests/bundles/test_export.py tests/bundles/test_verify.py tests/bundles/test_import.py tests/bundles/test_malicious.py -q &amp;&amp; uv run mypy --strict src/openrund/engine src/openrund/_localfs.py src/openrund/assembly/_factory.py src/openrund/storage/_layout.py src/openrund/storage/_artifacts.py src/openrund/bundles tests/engine tests/test_localfs.py &amp;&amp; uv run ruff check src/openrund/engine src/openrund/_localfs.py src/openrund/assembly/_factory.py src/openrund/storage/_layout.py src/openrund/storage/_artifacts.py src/openrund/bundles tests/engine tests/test_localfs.py</automated>
  </verify>
  <done>ARCH-04 and ARCH-05 are complete in order: submit owns one coherent replay-to-atomic-custody attempt with no duplicate replay, and common hardened filesystem mechanics have one private implementation while every domain and security boundary retains independent enforcement.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Type operator successes, freeze the release facade, and guard dependency parity</name>
  <files>src/openrund/operator/_model.py, src/openrund/operator/_service.py, src/openrund/operator/_render.py, src/openrund/operator/__init__.py, src/openrund/cli.py, src/openrund/demo.py, docs/api.md, tests/operator/test_results.py, tests/operator/test_service.py, tests/cli/test_commands.py, tests/demo/test_governed_coding.py, tests/docs/test_documentation.py, tests/package/test_public_api.py, tests/package/test_py_typed.py, tests/package/test_installed_typing.py</files>
  <behavior>
    - "ARCH-06: every successful operator method advertises a precise immutable data type and callers access attributes with inferred scalar/tuple/domain types rather than string-keyed generic JSON."
    - "ARCH-06: JSON conversion exists only in rendering/CLI adaptation and produces the same ordered fields, text, JSON bytes, safe error data, and exit codes as before."
    - "ARCH-06: demo, CLI, source tests, and installed strict-typing consumers require no operator-result indexing/length type suppression."
    - "ARCH-07: the exact package-root allowlist remains unchanged throughout the 2.x release line, named subpackages are the preferred advanced-access surface, and the policy is documented and mechanically frozen."
    - "ARCH-08: the test extra and development group are exactly equal as requirement strings, including extras and lower bounds, so either contributor installation path selects the same direct tools."
  </behavior>
  <action>Implement ARCH-06 first with expand-migrate-contract inside this task. Expand `src/openrund/operator/_model.py` with covariant generic `OperatorResult[TData]` and cohesive final immutable success payloads for command decisions, Run inspection/replay/timeline/readiness, Wait/Check/Artifact evidence, Bundle export/verification/replay/import/assessment, and the governed-coding demo; reuse existing typed domain results such as Views, receipts, Bundle results, and assessments instead of copying them into dictionaries. Keep related payload types together in the deep operator model/service modules rather than creating one module per command. Make success construction retain typed data unchanged; keep safe failure classification/data explicit. Move `_service.py`'s JSON-shaping helpers into `_render.py` as the single adapter that converts every typed payload to the existing ordered `JsonObject`, then feeds both text and canonical JSON renderers. Migrate service return annotations, CLI result erasure at the adapter boundary, demo composition, direct tests, and installed typing before contracting away generic success JSON construction. Remove operator-data type suppressions made unnecessary by attribute/tuple access, while retaining suppressions unrelated to this migration unless independently proven obsolete. Assert exact existing rendered snapshots and failure branches to protect wire compatibility. Implement ARCH-07 second: preserve `src/openrund/__init__.py` and its exact sorted allowlist, rename/extend the public API test to state the 2.x compatibility freeze, prove representative advanced APIs remain available from their named subpackages, and add a `docs/api.md` compatibility section declaring named subpackages the preferred advanced access and root contraction a major-release migration with release notes and compatibility evidence. Add a documentation sentinel for that policy; do not remove or reorder a root export in this task. Implement ARCH-08 last by strengthening `tests/package/test_py_typed.py` to compare `[project.optional-dependencies].test` and `[dependency-groups].dev` as exact ordered requirement strings, not merely normalized package-name sets; the currently equal `pyproject.toml` needs no dependency edit. Run installed-wheel typing so the generic result annotations and preserved facade are tested outside the source tree.</action>
  <verify>
    <automated>uv run --python 3.12 pytest tests/operator/test_results.py tests/operator/test_service.py tests/cli/test_commands.py tests/demo/test_governed_coding.py tests/docs/test_documentation.py tests/package/test_public_api.py tests/package/test_py_typed.py tests/package/test_installed_typing.py -q &amp;&amp; uv run mypy --strict src/openrund/operator src/openrund/cli.py src/openrund/demo.py tests/operator tests/cli tests/demo tests/package/test_public_api.py tests/package/test_py_typed.py tests/package/test_installed_typing.py &amp;&amp; uv run ruff check src/openrund/operator src/openrund/cli.py src/openrund/demo.py tests/operator tests/cli tests/demo tests/package/test_public_api.py tests/package/test_py_typed.py tests/package/test_installed_typing.py</automated>
  </verify>
  <done>ARCH-06, ARCH-07, and ARCH-08 are complete in order: typed operator success values survive to the adapter boundary, rendered contracts are unchanged, the release-sensitive root facade has an explicit tested 2.x policy, and both development dependency surfaces are locked to exact parity.</done>
</task>

</tasks>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI arguments -> local custody | Untrusted syntax and paths must be completely validated before runtime-home creation or SQLite/Artifact access. |
| Command -> RuntimeEngine -> EventStore | The sole authority path converts one attempted mutation into a durable decision and audit-first atomic Event batch. |
| Domain path -> local filesystem | Assembly, storage, Bundle, and import paths cross OS filesystem races, symlinks, file kinds, permissions, and durability semantics. |
| Typed operator domain -> renderer | Trusted typed results become public text/JSON without moving legality or inventing facts in presentation. |
| Package root -> downstream users | Exact imports are a release compatibility contract even when a narrower facade would be aesthetically preferable. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-lvk-01 | Information Disclosure | CLI parse/assembly order | high | mitigate | Parse the full route before custody, test that help/invalid input cannot call the runtime factory or expose an injected storage failure, and keep safe failure messages bounded. |
| T-lvk-02 | Elevation of Privilege | Engine command-attempt refactor | critical | mitigate | Preserve the sole public `submit` surface, pure legality, command.recorded-first batches, expected-position retry, cross-Run atomic append, and submit-level rejected/deferred/superseded tests. |
| T-lvk-03 | Tampering | Shared filesystem primitives | high | mitigate | Use lstat/no-follow/exclusive descriptors/fsync while retaining containment, hashing, topology, re-verification, collision, and recovery checks independently at every consuming boundary. |
| T-lvk-04 | Repudiation | Authority documentation ownership | medium | mitigate | Make control.md normative and add a test for document roles, cross-links, invariant path, and the RuntimeEngine/CommandDecision distinction. |
| T-lvk-05 | Tampering | Operator serialization | medium | mitigate | Keep domain values typed until one rendering adapter and assert exact ordered text/JSON snapshots plus installed strict typing. |
| T-lvk-06 | Denial of Service | Bundle/Artifact reads and publication | medium | mitigate | Preserve bounded reads, finite SQLite waits, exclusive publication, cleanup/recovery, and no-overwrite behavior in focused adversarial suites. |
| T-lvk-07 | Tampering | Package and tool contracts | high | mitigate | Keep the exact 2.x root allowlist and frozen compatibility evidence, test installed exports, and assert exact test-extra/dev-group requirement parity. |

</threat_model>

## Source Coverage Audit

| Source | ID | Feature/Requirement | Task | Status | Notes |
|--------|----|---------------------|------|--------|-------|
| GOAL | — | Implement all ranked improvements without weakening the authority path | 1-3 | COVERED | Ranked execution is explicit in task names/actions. |
| CONTEXT | ARCH-01 | Delete unused RuntimeDependencies and construction-only evidence | 1 | COVERED | Narrow protocols/tests remain. |
| CONTEXT | ARCH-02 | Parse and validate completely before LocalRuntime/SQLite; demo is a parsed route | 1 | COVERED | Includes no-custody and side-effect tests. |
| CONTEXT | ARCH-03 | control.md owns authority; other documents own positioning, ontology, and module map | 1 | COVERED | Includes terminology resolution and ownership test. |
| CONTEXT | ARCH-04 | Deepen submit attempt, remove duplicate replay, reduce legality parameters, test through submit | 2 | COVERED | Public signature and atomic custody remain fixed. |
| CONTEXT | ARCH-05 | Consolidate only low-level hardened filesystem primitives | 2 | COVERED | Domain validation and distinct trust-boundary checks stay local. |
| CONTEXT | ARCH-06 | Typed operator successes with JSON conversion at rendering boundary | 3 | COVERED | Expand-migrate-contract and type-suppression removal included. |
| CONTEXT | ARCH-07 | Make the 94-name root facade an explicit release-sensitive decision | 3 | COVERED | Current compatibility evidence requires a tested 2.x freeze; named subpackages are preferred. |
| CONTEXT | ARCH-08 | Keep test extra and development dependency bounds equal | 3 | COVERED | Exact ordered requirement-string equality. |
| CONTEXT | PRESERVE-01 | Frozen fixtures, wire/export evidence, catalogs, Bundle defenses, rebuild_views, adapter seams | 1-3 | COVERED | Scope guardrails plus focused and full verification. |
| CONTEXT | EXCLUDE-01 | Do not add CI | 1-3 | COVERED | CI paths are outside files_modified and forbidden by scope guardrails. |

<verification>
After all three sequential tasks, run the focused suites above, then the complete compatibility and
release gates:

`uv run --python 3.12 coverage run -m pytest -q &amp;&amp; uv run coverage report --fail-under=79 &amp;&amp; uv run --python 3.13 pytest -q &amp;&amp; uv run --python 3.14 pytest -q &amp;&amp; uv run mypy --strict src/openrund tests examples &amp;&amp; uv run ruff check src tests examples &amp;&amp; uv run ruff format --check src tests examples &amp;&amp; uv lock --check &amp;&amp; uv build &amp;&amp; git diff --check`

Review `git diff --name-only` and confirm there are no changes under `tests/fixtures/compatibility/v1`,
`.github`, or `uv.lock`, and no unplanned public name, Event/Command catalog, error-code, or wire-format
change.
</verification>

<success_criteria>

- ARCH-01 through ARCH-08 are implemented in their ranked order with no omitted recommendation.
- `RuntimeEngine.submit(Command)` remains the sole public mutation authority and every attempted
  mutation still follows `Command -> CommandDecision -> Events -> Views`.
- Invalid/help CLI paths are proven custody-free; valid demo and operator routes remain functional.
- Authority documentation has one normative owner and no RuntimeEngine/CommandDecision contradiction.
- Engine replay/evaluation/planning/commit tests pass through submit with no duplicate same-stream replay.
- Filesystem consolidation reduces mechanical duplication without merging security trust boundaries.
- Operator callers and installed consumers see typed success data; CLI text/JSON remains exact.
- The package root is intentionally frozen for 2.x, named subpackages are documented, and contraction
  requires a major-release process.
- The 79% coverage floor, supported Python versions, strict typing, lint, format, lock, package, and
  compatibility gates all pass; no CI is added.

</success_criteria>

<output>
Create `.planning/quick/260807-lvk-implement-the-seven-ranked-openrund-arch/260807-lvk-SUMMARY.md`
when done.
</output>
