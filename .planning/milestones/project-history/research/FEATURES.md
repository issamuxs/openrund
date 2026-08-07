# Feature Research

**Domain:** Complete Python governed mutation runtime
**Researched:** 2026-08-04
**Confidence:** HIGH for required runtime behavior; MEDIUM for Python-native ergonomics

## Research Position

This milestone is complete only when the full governed run loop is available through Python-native product surfaces. The compatibility boundary is semantic behavior and serialized data: canonical ontology, Event grammar, CommandDecision outcomes, persistence rules, and `.orun` content must remain stable. Python package organization and callable API shape should be designed for Python users rather than treated as serialized compatibility surfaces.

The release should therefore separate three classes of work:

1. **Must-have parity:** observable runtime behavior without which the release is incomplete.
2. **Python-native differentiators:** developer-experience improvements that expose the same behavior more naturally without adding product scope.
3. **Deferred work and anti-features:** attractive additions that would dilute or bypass the governed runtime.

Suggested identifiers below are feature-cluster IDs suitable for conversion into milestone REQ-IDs. Each item includes an observable acceptance boundary so roadmap requirements can be tested rather than inferred from code structure.

## Feature Landscape

### Table Stakes: Must-Have Semantic and Behavioral Parity

| Suggested ID | Feature | Why Required | Complexity | Observable acceptance boundary |
|--------------|---------|--------------|------------|--------------------------------|
| SEM-01 | Canonical ontology and typed identifiers | Run history, policy, capabilities, Views, and Bundles need one shared language. | HIGH | Python exposes the canonical concepts `Run`, `Command`, `Event`, `Message`, `ModelCall`, `Action`, `Wait`, `Delegation`, `Check`, `Checkpoint`, `Annotation`, `Artifact`, `Capability`, `Authority`, `Lease`, `Bundle`, and `View`; generated IDs validate by kind; public secondary types use non-authoritative suffixes. |
| SEM-02 | Stable serialized formats and Event grammar | Existing run data and portable bundles are part of the product contract. | HIGH | Golden fixtures round-trip without semantic drift; Event envelopes retain `id`, `runID`, `position`, `type`, `version`, `timestamp`, `payload`, optional causation/correlation links, canonical `<subject>.<verb>` names, and compact payload discipline. Unsupported schema or Event versions fail closed. |
| EVT-01 | Append-only, per-Run ordered canonical history | Replay, audit, recovery, and concurrency all depend on authoritative ordering. | HIGH | Appends require an expected position; stale writers receive a distinct conflict; positions are gap-free and deterministic; Events cannot be mutated or deleted through product APIs; subscribers cannot invalidate already-committed history. |
| ENG-01 | Engine-owned mutation for every origin | The runtime's defining promise is that no secondary surface can create authoritative history. | HIGH | Model, API, timer, capability result, operator, delegation handoff, and recovery paths all create an Engine-evaluated Command before state-changing Events; providers, workers, CLI, Views, storage, and bundle code cannot append lifecycle Events directly. |
| ENG-02 | Persisted CommandDecision and explanation trace | Accepted, rejected, deferred, and superseded outcomes must be auditable facts. | HIGH | Every attempted mutation records `command.recorded` with origin, operation, decision, decision trace, result Event IDs, Wait linkage, and replacement linkage; rejected/superseded Commands produce no target lifecycle Events; deferred Commands identify the blocking condition. |
| RUN-01 | Full Run lifecycle and terminal legality | Durable Runs need lawful creation, advancement, failure, cancellation, and completion. | HIGH | Bootstrap records created/started history; completion, failure, and cancellation are Commands; terminal Runs reject later mutation; completion is rejected while required Waits, Checks, artifacts, joins, or unknown outcomes remain unsatisfied. |
| MSG-01 | Messages, ModelCalls, and parsed Operations as proposals | Host and model interaction must be durable without turning provider output into authority. | HIGH | Message addition/deltas and ModelCall start/complete/fail/cancel lifecycles replay correctly; supported parsed operations cover messages, actions, safe operation batches, delegation, waits, checkpoints, and terminal proposals; provider/transport/parse failures remain ModelCall failures while illegal operations become rejected Commands. |
| CAP-01 | Generic Capability registry, schemas, reliability, and transports | Domain work must remain outside semantic core while obeying one execution contract. | HIGH | Definitions validate IDs, versions, action schemas, read/write access mode, reliability, batch eligibility, cancellation, artifacts, and transport metadata; in-process and transported worker paths return `CapabilityResult`; malformed definitions and results fail closed. |
| ACT-01 | Engine-controlled Action lifecycle | Consequential effects need durable identity, evidence, and failure semantics. | HIGH | Accepted action Commands materialize create/start and exactly one current outcome among completed, failed, cancelled, or unknown; worker results become compact output/effect/evidence metadata plus Artifact references; cancellation and retries obey declared capability reliability. |
| ACT-02 | Explicit unknown-outcome reconciliation | Ambiguous external effects cannot be guessed, retried blindly, or hidden as generic failure. | HIGH | An uncertain result records `action.unknown` and a reconciliation Wait when required; completion remains illegal; evidence-backed reconciliation appends `action.reconciled` without rewriting the unknown Event; replay retains the previous outcome and evidence trail. |
| WAIT-01 | All five canonical Wait kinds | Approval is only one reason a durable Run may lawfully pause. | HIGH | Approval, interaction, timer, join, and reconciliation Waits can be created and replayed; each resolves, cancels, or expires at most once; unresolved Waits derive waiting state and block relevant advancement; external signals and retry metadata remain payload/policy, not new root blocker concepts. |
| WAIT-02 | Approval deferral, revision, and governed resume | Approval must authorize a still-legal operation rather than legalize an invalid one. | HIGH | Illegal operations are rejected before approval; valid gated actions defer with an approval Wait and do not execute; resolution records operator/decision; revised input is limited to declared roots and schema, revalidated with current Authority/policy, and resumed through a new accepted Command. |
| DEL-01 | Bounded Delegation and join semantics | Delegated work must remain governed, replayable, and unable to expand authority. | HIGH | Delegation contracts capture objective, bounded Authority, budgets, result schema, nesting, cancellation, and late handoff policy; delegated Runs have parent linkage; joins support all/any/quorum; child terminal state never directly terminates or advances the parent; partial failures remain recoverable. |
| GOV-01 | Authority, contracts, policy, and legality diagnostics | Capability registration is not authorization, and approval is not legality. | HIGH | Authority grants/revocations are durable; resource/workspace scope, budgets, required checks, capability metadata, delegation lineage, and outcome constraints participate in decisions; diagnostic trace entries explain which rule accepted, rejected, or deferred work. |
| CHK-01 | Checks, Checkpoints, Annotations, and completion gates | Semantic validation and recovery boundaries must be runtime facts rather than host logs. | MEDIUM | Checks record subject, result, message, requirement identity, and Artifact evidence; semantic checks gate completion while diagnostic checks remain explanatory; Checkpoints and Annotations append and replay without becoming authority; required-check helpers produce serializable contracts. |
| ART-01 | Immutable Artifact custody | Large content, evidence, diffs, and outputs cannot safely live inside Event payloads. | HIGH | Artifact IDs bind immutable metadata/content; duplicate conflicting writes fail; inline worker artifacts are materialized before referenced Events become authoritative; unavailable content is explicitly recorded; large outputs are Artifact-backed and integrity-checkable. |
| VIEW-01 | Deterministic Views, Receipts, Reports, and readiness | Operators need useful state without introducing another source of truth. | HIGH | Rebuilding from complete Events and Artifacts yields deterministic Run status/readiness, timeline, wait queues, Action status/receipts/reconciliation, Artifact index, Checkpoints, and Delegation state; derived surfaces are marked derived and never append Events or decide legality independently. |
| STO-01 | Local SQLite Event and Artifact stores | A complete local release must survive process restart with exact ordering and content. | HIGH | Real SQLite integration tests cover migrations, ordered reads, expected-position conflicts, duplicate Event IDs, restart/reopen behavior, Artifact metadata/blob integrity, and explicit partial-failure handling. |
| STO-02 | Execution Leases and canonical Run-home layout | Multiple executors need coordination, and local data needs predictable custody. | MEDIUM | Lease acquire/release/expiry obey owner and time constraints but never grant runtime Authority; each Run receives deterministic `runtime/`, `workspace/`, and `exports/` paths under the configured runtime home; all path APIs accept explicit overrides. |
| BND-01 | Complete `.orun` export, verify, replay, import, and resume assessment | Portability is part of runtime semantics, not an optional reporting feature. | HIGH | Export includes manifest, canonical Events, Event hash chain, available Artifacts, derived summaries, policy/capability metadata, reports, and resume requirements; verification fails closed on path, schema, hash-chain, or manifest corruption; replay adds no Events; import stages verified history; resume assessment reports every unmet condition and never authorizes resume. |
| BUILTIN-01 | Workspace-bounded filesystem capability | Governed file work is the default local substrate and must prove read/write scope enforcement. | HIGH | Read/list/stat/write/update/delete/move/diff operate only through declared mounts; read-only mounts, traversal, symlinks, stale hashes, overwrite policy, and workspace escape are tested; mutations are atomic where possible and return effects/evidence/artifacts. |
| BUILTIN-02 | Markdown documents capability | Document manipulation is required domain behavior but must remain a Capability. | HIGH | Read, whole-document write, and structured patch support hashes, diffs, headings/sections, ranges, appends, and frontmatter; writes are root-bounded and approval-revisable; worker/transport errors map to structured capability outcomes rather than Events authored by the worker. |
| BUILTIN-03 | Bounded process and git capabilities | The flagship coding flow needs real execution and repository evidence without becoming a coding product. | HIGH | Process execution constrains working roots, arguments, environment, shell choice, timeout, cancellation, and artifact-backed stdout/stderr; git supports local status/diff/head/apply/stage/commit with root constraints and excludes network/credential operations. |
| PROV-01 | OpenAI, Anthropic, and local OpenAI-compatible adapters | Provider choice is expected, but all adapters must preserve the same proposal-only boundary. | MEDIUM | Deterministic transport mocks verify request mapping, operation parsing, redacted errors, timeout/malformed response handling, and absence of Event authority; optional credential-gated smoke tests detect API drift without making default tests network-dependent. |
| CLI-01 | Thin but complete operator CLI | Durable control points must be inspectable and operable without custom host code. | HIGH | The installed `openrund` command covers create/run/inspect, timeline/replay, waits and approvals, Command explanations, reconciliation and Action receipts, readiness, Checks, Artifacts, and all Bundle operations; it delegates legality to the Engine, supports deterministic human and JSON output, and returns meaningful exit codes. |
| DEMO-01 | One deterministic governed coding proof | Completeness must be visible in one end-to-end run, not inferred from isolated unit tests. | HIGH | A Python demo proves illegal mutation rejection before approval, approval deferral/resume, filesystem/process/git/documents execution, unknown outcome plus reconciliation, delegated join, Check-gated completion, CLI explanations, and verified/replayed/imported `.orun` output. |
| REL-01 | Python-only install, test, docs, and release surface | A Python release is incomplete if users or contributors need a second runtime/toolchain. | HIGH | Wheel and sdist install in clean environments; `python -m pytest`, type checking, lint/hygiene, package-content, docs-link, demo, and optional live-provider commands are documented and pass; all live source, tests, examples, packaging, CLI, and docs are Python-native. |

### Differentiators: Python-Native Developer Experience Without Scope Expansion

These features improve how developers express and test the same runtime semantics. They should not create new ontology, new execution authority, or new product domains.

| Suggested ID | Feature | Value Proposition | Complexity | Scope guardrail / acceptance boundary |
|--------------|---------|-------------------|------------|---------------------------------------|
| DX-01 | Pythonic objects with exact wire aliases | Developers use `snake_case`, keyword-only constructors, enums, and pattern matching while persisted JSON remains canonical. | MEDIUM | One explicit codec boundary maps Python names to canonical serialized keys and back; golden fixture round-trips prove zero wire drift. Do not leak serialization dictionaries throughout engine code. |
| DX-02 | Typed immutable value objects | Frozen dataclasses and precise unions make illegal lifecycle states harder to construct and improve IDE completion. | MEDIUM | Canonical facts and decisions are read-only after construction; `py.typed` is shipped; public functions have complete type annotations; runtime validation still occurs at untrusted/provider/worker/bundle boundaries. |
| DX-03 | Structural dependency injection with `Protocol` | Hosts can supply stores, clocks, ID factories, providers, transports, and reporters without inheriting framework base classes. | MEDIUM | Public seams are small Protocols; in-memory/test implementations satisfy the same contract; runtime `isinstance` checks are not used as a substitute for validation. |
| DX-04 | Async-first runtime with explicit resource lifetime | Providers, subprocesses, timers, transports, and concurrent workers map naturally to `async`/`await`. | HIGH | Engine and I/O seams are awaitable; runtime/storage/worker resources support explicit close or async context management; cancellation maps to Action/ModelCall semantics. A sync wrapper, if offered, exists only at a top-level boundary and never nests event loops. |
| DX-05 | `pathlib.Path` and `os.PathLike` inputs | Python callers should not stringify every runtime home, workspace root, database, or bundle path. | LOW | Public path parameters accept path-like objects, normalize once at the boundary, preserve sandbox rules, and serialize portable strings only where the wire format requires them. |
| DX-06 | One installable distribution with targeted extras | Installation should be obvious while heavyweight provider integrations stay optional. | MEDIUM | Standards-based `pyproject.toml`, `src/` layout, wheel/sdist, `[project.scripts]` CLI entry point, minimal core dependencies, provider extras, and separate development dependency groups; clean-install tests cover base and extras. |
| DX-07 | Reusable pytest contract kit | Extension authors need to prove stores, providers, and capabilities obey authority and serialization rules. | MEDIUM | A small `openrund.testing` surface provides deterministic clock/ID factories, in-memory stores, fixture builders, and contract test helpers; temporary real directories/databases remain the default for filesystem and storage behavior. |
| DX-08 | Semantic exception hierarchy plus result values | Python callers need predictable handling without confusing legal rejection with program failure. | MEDIUM | Rejected/deferred/superseded are persisted decision results, not exceptions; exceptions distinguish caller validation, optimistic concurrency, storage integrity, transport, and capability protocol failures and retain safe structured context. |
| DX-09 | Local runtime assembly with override points | The first lawful Run should take little code without hiding storage, workspace, capability, or policy choices. | MEDIUM | A documented local factory wires SQLite, default paths, built-ins, providers, operator, and reporter; every dependency remains injectable; defaults never silently grant Authority or writable roots. |
| DX-10 | Stable import surface and executable CLI parity | Users should not need internal-module knowledge to embed or operate the runtime. | MEDIUM | A deliberate top-level namespace exports the Engine, local assembly, IDs, contracts, Views, capability/provider factories, storage, and test helpers; import tests and CLI/library parity tests prevent accidental surface drift. |

### Explicit Deferred Work

Deferred items are not launch gaps for this milestone and should not receive P1 requirements.

| Deferred Feature | Why Defer | Trigger to Reconsider |
|------------------|-----------|-----------------------|
| Hosted multi-tenant control plane | Introduces identity, tenancy, service operations, and network authority beyond the local runtime contract. | Stable local semantics plus concrete hosted-user demand. |
| Distributed Event storage, sharding, and high-availability leases | Requires a distributed consistency model and operational envelope not needed to prove local durability. | Measured local-store limits or a server deployment milestone. |
| Rich web/operator UI | Risks moving legality explanations into presentation code before APIs and CLI are stable. | Stable structured inspection APIs and validated operator workflows. |
| Broad first-party Capability catalog | Turns a semantics framework into an integration marketplace and multiplies security review. | Repeated user demand for a specific capability that cannot be served as an external package. |
| Provider routing, model optimization, prompt management, or agent personas | These are host/harness concerns and do not improve mutation legality. | A separate integration package with no semantic-core coupling. |
| Persisted View snapshots and production observability pipelines | Views are rebuildable now; snapshot invalidation and telemetry backends add operational scope. | Replay profiling demonstrates a real bottleneck or production deployment requires it. |
| Automatic cross-environment resume | Resume depends on explicit roots, providers, capabilities, policy, Waits, and Artifacts. | Never automatic; future work may improve assisted rebinding while retaining Engine authorization. |
| Expanded document formats beyond Markdown | Format-specific parsing is capability-domain work, not needed for complete runtime parity. | A follow-up capability milestone with explicit format requirements and tests. |

### Anti-Features: Scope and Authority Hazards

| Anti-Feature | Why It Seems Attractive | Why It Is Problematic | Required Alternative |
|--------------|-------------------------|-----------------------|----------------------|
| Public direct-append mutation API | Convenient for hosts and fixtures. | Lets callers create canonical facts without legality, breaking the sole-authority claim. | Keep raw append private/internal to bootstrap and controlled tests; normal APIs always submit Commands. |
| Public API shape compatibility shims | Appears to reduce migration work. | Freezes non-Python idioms and confuses implementation shape with semantic compatibility. | Preserve serialized formats and behavior; publish a clean Python-native namespace. |
| Treating approval as a universal override | Operators may expect an “approve anyway” button. | Allows malformed, unauthorized, or out-of-scope work to become legal. | Reject illegality first; defer only valid operations that require authorization; revalidate revisions. |
| Additional blocker roots such as Approval, Timer, Signal, or Reconciliation objects | Makes each waiting scenario look explicit. | Fragments lifecycle logic and undermines the single replayable Wait abstraction. | Use the five `Wait(kind=...)` variants with typed payloads. |
| Views or cached state as an authority source | Faster reads and simpler code paths. | Cache staleness could change legality and make replay disagree with execution. | Use only Views rebuilt to a known Event watermark as inputs; Engine records every decision. |
| Worker- or provider-authored Events | Reduces Engine plumbing. | Crosses the trust boundary and lets untrusted integrations rewrite lifecycle semantics. | Workers return results and providers return Operation proposals; the Engine materializes Events. |
| Blind retry after ambiguous side effects | Easy resilience story. | Can duplicate irreversible work when the first attempt actually succeeded. | Record unknown outcome, open reconciliation, gather evidence, and reconcile explicitly. |
| Bundle import that automatically resumes or grants Authority | Makes portability appear seamless. | Imported data cannot prove local roots, policy, providers, capabilities, or operator intent. | Verify, stage, assess, explicitly bind requirements, then request Engine-authorized resume. |
| Workflow designer, prompt framework, planner, or agent persona layer | Makes the project feel like a complete agent platform. | Expands into orchestration/product behavior and distracts from governed mutation semantics. | Let hosts own planning and prompts; translate consequential operations into Commands and capabilities. |
| Remote git/network credentials in the built-in git capability | Useful for autonomous coding. | Expands secrets, network, and irreversible external-effect scope substantially. | Keep built-in git local-only; add remote operations later as separately governed external capabilities. |
| Capability-specific exceptions as the main audit record | Feels Pythonic for errors. | Exceptions disappear across restart and cannot explain legal decisions during replay. | Persist CommandDecision and Action outcome Events; use exceptions only for caller/transport/integrity failures. |
| Implicit synchronous wrappers around async internals | Makes examples superficially shorter. | Nested loops, cancellation loss, and hidden blocking make durable I/O behavior unpredictable. | Keep the library async-first; use `asyncio.run` only in CLI/examples or an explicitly separate sync facade. |

## Feature Dependencies

```text
[SEM-01 ontology + SEM-02 wire formats]
                 |
                 +--> [EVT-01 storage contracts + deterministic codecs]
                 |             |                     |
                 |             |                     +--> [STO-01 SQLite + STO-02 Leases]
                 |             |
                 |             +--> [VIEW-01 deterministic replay]
                 |
                 +--> [ENG-01 authority + ENG-02 CommandDecision]
                                |
                                +--> [RUN-01 lifecycle + MSG-01 ModelCalls]
                                |
                                +--> [GOV-01 Authority/contracts]
                                |          |
                                |          +--> [WAIT-01/02 Waits and approval]
                                |          +--> [CHK-01 Checks/Checkpoints]
                                |
                                +--> [CAP-01 Capability boundary + ART-01 Artifacts]
                                           |
                                           +--> [ACT-01 lifecycle]
                                           |          +--> [ACT-02 uncertainty/reconciliation]
                                           |
                                           +--> [DEL-01 Delegation/join]
                                           +--> [BUILTIN-01/02/03 capabilities]
                                           +--> [PROV-01 provider adapters]

[Complete runtime + Views + SQLite + capabilities]
                 +--> [BND-01 Bundles]
                 +--> [CLI-01 operator surface]

[Bundles + CLI + all governed behaviors]
                 +--> [DEMO-01 end-to-end proof]
                 +--> [REL-01 clean install/release verification]

[DX-01 codecs + DX-02 typing + DX-03 Protocols]
                 ──enhance every layer without changing the dependency graph above
```

### Dependency Notes

- **Freeze semantic fixtures before broad implementation:** IDs, decision values, Event names/payloads, and Bundle fixtures are the executable compatibility baseline. Building higher layers first invites wire-format drift.
- **Build the Engine authority path before rich controls:** Run lifecycle, waits, checks, Actions, delegation, and terminal transitions must all reuse one Command/CommandDecision append path rather than acquire local shortcuts.
- **Build deterministic replay alongside Events:** Every new lifecycle Event should land with its View reducer and replay test. Deferring Views until the end hides incomplete payloads and accidental state.
- **Build Artifacts before real capabilities:** filesystem diffs, documents, process streams, git patches, checks, receipts, and Bundles all need immutable content custody.
- **Build Waits before approval and Delegation:** approval, reconciliation, and join are typed Wait applications. Separate implementations before the base Wait contract would duplicate blocker semantics.
- **Build Action unknown outcomes before process/demo completion:** process and other side effects cannot be considered complete until uncertainty and reconciliation are first-class.
- **Build SQLite before restart and CLI claims:** in-memory stores are useful for contract tests, but durability, optimistic concurrency, and lease behavior require real SQLite tests.
- **Build Bundles after replay and all canonical lifecycles stabilize:** verification and resume assessment must understand every Event, Artifact, Wait, capability, provider, policy, and terminal state.
- **Build CLI after structured runtime queries:** CLI rendering should consume Engine/Views results, not reconstruct decisions. Human and JSON renderers should share the same result models.
- **Finish with one demo and clean-install matrix:** the demo is a release proof, not a place to invent missing semantics. Run it from an installed wheel in a clean environment.

## Complete Release Definition

### Launch With: P1 Mandatory Parity

- [ ] **SEM/EVT:** canonical ontology, codecs, Event catalog, append-only ordering, golden serialization fixtures, and replay determinism.
- [ ] **ENG/RUN/MSG:** one Engine-owned Command path for all origins, persisted decisions/traces, ModelCall proposal boundary, and lawful Run terminal states.
- [ ] **CAP/ACT/ART:** generic registry/transports, complete Action lifecycle, immutable Artifact materialization, and explicit unknown-outcome reconciliation.
- [ ] **WAIT/DEL/GOV/CHK:** all Wait kinds, approval revision/revalidation, bounded Delegation with joins, Authority/contracts, Checks, Checkpoints, and completion gates.
- [ ] **VIEW/STO:** deterministic Views/Receipts/Reports plus real SQLite Event/Artifact/Lease durability and canonical Run homes.
- [ ] **BND:** fail-closed `.orun` export, verify, replay, import, and non-authoritative resume assessment.
- [ ] **BUILTIN:** full workspace-bounded filesystem, Markdown documents, process, and local git capabilities.
- [ ] **PROV:** OpenAI, Anthropic, and local OpenAI-compatible adapters with deterministic contract tests and optional live smoke tests.
- [ ] **CLI/DEMO:** complete operator CLI and one installed-package end-to-end governed coding demo.
- [ ] **REL:** Python-only packaging, tests, hygiene, docs, examples, and release checks; no second runtime/toolchain on any live surface.

### Include When Their Foundation Lands: P2 Python-Native DX

- [ ] Canonical codecs supporting Pythonic names and exact wire aliases.
- [ ] Frozen typed domain objects, `py.typed`, small Protocol seams, and a stable import surface.
- [ ] Async-first Engine/resources, `PathLike` inputs, explicit lifecycle cleanup, and semantic exceptions.
- [ ] Standards-based `pyproject.toml`, console script, source layout, optional provider extras, and development dependency groups.
- [ ] Deterministic pytest fixtures and contract helpers for capability/provider/storage extension authors.
- [ ] Human-readable and JSON CLI output backed by the same structured result models.

### Defer Beyond This Milestone: P3

- [ ] Hosted control plane, multi-tenancy, distributed storage/leases, sharding, and HA.
- [ ] Rich UI, workflow builder, prompt/persona framework, provider router, and broad observability platform.
- [ ] Broad first-party Capability catalog, remote git/network operations, and document formats beyond Markdown.
- [ ] Persisted View snapshots unless replay measurements establish a need.
- [ ] Any automatic resume behavior that bypasses explicit local rebinding and Engine legality.

## Feature Prioritization Matrix

| Feature Cluster | User Value | Implementation Cost | Priority |
|-----------------|------------|---------------------|----------|
| Semantic contracts, codecs, Events, and ordering | HIGH | HIGH | P1 |
| Engine authority, Commands, decisions, and terminal legality | HIGH | HIGH | P1 |
| Actions, capabilities, Waits, reconciliation, Authority, and Checks | HIGH | HIGH | P1 |
| Delegation and join/cancellation semantics | HIGH | HIGH | P1 |
| Artifacts, deterministic Views, Receipts, and readiness | HIGH | HIGH | P1 |
| SQLite Event/Artifact/Lease durability | HIGH | HIGH | P1 |
| `.orun` portability and resume assessment | HIGH | HIGH | P1 |
| Filesystem/documents/process/git capability set | HIGH | HIGH | P1 |
| Provider adapter set | HIGH | MEDIUM | P1 |
| CLI explanation/control surface | HIGH | HIGH | P1 |
| End-to-end demo and Python-only release verification | HIGH | HIGH | P1 |
| Pythonic codecs, typing, Protocols, async lifecycle, and PathLike support | HIGH | MEDIUM | P2 |
| Test kit, packaging extras, JSON CLI, and stable import ergonomics | MEDIUM | MEDIUM | P2 |
| Hosted/distributed/UI/catalog expansion | LOW for this milestone | HIGH | P3 |

## Completeness Test Matrix

| Requirement Area | Minimum Evidence |
|------------------|------------------|
| Serialization | Golden JSON/Event/Bundle fixtures decode, encode, round-trip, hash, and reject unsupported versions deterministically. |
| Authority | Source/import guards plus behavior tests prove only Engine-owned paths append state-changing Events. |
| Decisions | Accepted, rejected, deferred, and superseded cases assert exact target Event presence/absence and explanation linkage. |
| Lifecycle | Table-driven transition tests cover every Run, ModelCall, Action, Wait, Delegation, Authority, Lease, Checkpoint, and terminal edge. |
| Recovery | Restart tests resume from SQLite; stale positions conflict; unknown outcomes and unresolved Waits survive replay. |
| Capability trust | Real in-process and transported worker tests prove schema validation, sandboxing, result materialization, redaction, and worker non-authority. |
| Portability | Corruption matrix covers manifest paths, schema, Event hash chain, Artifact consistency, incomplete content, import staging, and resume issues. |
| Operator surfaces | CLI/library parity tests verify arguments, structured results, deterministic text/JSON, non-zero process failures, and no CLI-local legality. |
| End to end | The governed coding demo asserts both controlled non-execution and controlled execution, then verifies/replays/imports its bundle. |
| Distribution | Clean virtual environments install wheel and sdist, run import smoke tests, invoke `openrund`, execute the demo, and run without undeclared tools. |

## Sources

### Normative and Behavioral Sources — HIGH Confidence

- `.planning/PROJECT.md` and `.planning/MILESTONES.md` — active milestone contract and validated behavioral scope.
- `docs/concepts.md`, `docs/control.md`, `docs/architecture.md`, and `docs/events.md` — ontology, authority, legality, Event grammar, and terminal rules.
- `docs/capabilities.md`, `docs/providers.md`, `docs/storage.md`, `docs/bundles.md`, and `docs/delegation.md` — subsystem contracts and failure boundaries.
- `docs/api.md`, `docs/quickstart.md`, `README.md`, and `examples/governed-coding-run/README.md` — expected public workflows and operator surface.
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`, and `.planning/codebase/TESTING.md` — component inventory, integration paths, and effective verification patterns.
- `tests/public-api/exports.test.ts`, `tests/public-api/ontology-guards.test.ts`, and `tests/examples/governed-coding-run.test.ts` — direct behavior evidence for public entry points, ontology discipline, and the end-to-end proof. These inform parity assertions, not Python API shape.

### Python Ecosystem Sources — MEDIUM Confidence

- [Python Packaging User Guide: Writing `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — project metadata, scripts, dependencies, extras, and build configuration.
- [Python Packaging User Guide: `src` layout versus flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) — clean-install and import-discipline rationale.
- [Python Packaging specification: Dependency Groups](https://packaging.python.org/en/latest/specifications/dependency-groups/) — development/test dependency grouping.
- [Python documentation: `typing.Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol) — structural typing for injectable seams.
- [Python documentation: Data Classes](https://docs.python.org/3/library/dataclasses.html) — typed value objects and frozen instances.
- [Python documentation: `pathlib`](https://docs.python.org/3/library/pathlib.html) — object-oriented and path-like filesystem APIs.
- [Python documentation: `asyncio`](https://docs.python.org/3/library/asyncio.html) — async I/O, subprocess, timeout, and cancellation primitives.
- [pytest documentation: Fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html), [temporary paths](https://docs.pytest.org/en/stable/how-to/tmp_path.html), and [parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html) — reusable deterministic test surfaces.

## Confidence and Open Questions

- **Must-have behavior: HIGH.** It is specified consistently across normative docs, milestone history, codebase maps, and direct end-to-end/public-surface tests.
- **Python-native DX: MEDIUM.** Recommendations follow current official Python, PyPA, and pytest guidance, but exact Python version floor, build backend, validator/codec library, CLI library, and async test plugin belong in stack research.
- **Capability action granularity: HIGH for the current Markdown/filesystem/process/git scope.** Any new action beyond the listed behaviors should be treated as a separate requirement, not inferred parity.
- **Open question for planning:** decide whether the testing helpers are a supported `openrund.testing` public surface in this milestone or initially an internal package with the same contracts.
- **Open question for planning:** choose whether optional provider integrations ship as extras of one distribution or as separately versioned distributions; either choice must keep the base install small and the top-level imports coherent.

---
*Feature research for: Python OpenRund complete implementation*
*Researched: 2026-08-04*
