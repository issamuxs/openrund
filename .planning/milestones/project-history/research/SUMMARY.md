# Project Research Summary

**Project:** OpenRund — v2.0 Python OpenRund
**Domain:** Event-sourced governed mutation runtime for durable agent runs
**Researched:** 2026-08-04
**Confidence:** HIGH for runtime semantics and sequencing; MEDIUM for time-sensitive Python ecosystem choices

## Executive Summary

OpenRund v2.0 is a complete Python reimplementation of an already-defined governed runtime, not a new agent framework and not a mechanical language port. Its non-negotiable product is the semantic boundary: the Engine alone evaluates Commands and appends authoritative Events; canonical Run history is ordered and replayable; waits, delegation, checks, artifacts, uncertainty, terminality, and `.orun` portability remain explicit runtime facts. Experts should preserve those behaviors and serialized formats as executable compatibility contracts while redesigning the public package as an idiomatic Python project.

The recommended implementation is one pure-Python `openrund` distribution for Python 3.12+, organized into deep semantic modules under `src/openrund/`. Use immutable dataclasses and explicit wire codecs, an async-first `RuntimeEngine`, deterministic pure Views, stdlib `sqlite3` behind narrow ports, HTTPX provider adapters, strict JSON Schema validation, stdio JSON-RPC workers, and a thin `argparse` CLI. Preserve camelCase only on the wire; use Python naming, `Protocol` injection seams, `PathLike` inputs, explicit resource lifetimes, and a curated import surface in code. Build the dependency chain from frozen fixtures through contracts, Views, storage, Engine semantics, capabilities/providers, Bundles, operator surfaces, and finally one clean Python-only cutover.

The largest risk is silently changing serialized meaning before the existing implementation has been captured as an oracle. The first phase must freeze predecessor-produced Events, decisions, SQLite rows, Views, provider normalization, Artifacts, and Bundles, then explicitly adjudicate known documentation/code discrepancies. Other critical risks are performing effects before durable acceptance, creating a second authority path, weakening SQLite/Artifact atomicity, mishandling cancellation or ambiguous effects, and accepting hash-valid but semantically invalid Bundles. Prevent them with one private append gate, durable pre-dispatch Action state, strict untrusted-boundary validation, atomic multi-Run storage, fault-injection tests, and a final one-way cutover only after installed-wheel end-to-end parity passes.

## Key Findings

### Recommended Stack

Use one standards-based Python distribution rather than recreating the former package graph. Keep the authority-bearing runtime deliberately small: the standard library supplies domain values, async orchestration, SQLite, subprocesses, canonical JSON, hashing, paths, and CLI parsing. The only required runtime dependencies should be `jsonschema` for untrusted envelopes and `httpx` for provider HTTP/SSE; Markdown tooling belongs in the `documents` extra. Direct HTTP adapters are preferred over provider SDKs so provider types, retries, and release cadence do not leak into runtime contracts.

**Core technologies:**

- **CPython `>=3.12`:** supported runtime floor — provides modern `sqlite3` transaction control plus `TaskGroup` and `asyncio.timeout`; test 3.12, 3.13, and 3.14, using current patch releases.
- **Frozen stdlib dataclasses, `StrEnum`, and `Protocol`:** domain model and injectable ports — immutable Python objects remain separate from explicit canonical wire encoders.
- **stdlib `asyncio`:** canonical concurrency model — one async Engine owns provider, worker, timer, cancellation, and shutdown lifecycles.
- **stdlib `sqlite3` with SQLite `>=3.24.0`:** local Event, Artifact metadata, and Lease persistence — explicit `BEGIN IMMEDIATE`, WAL, foreign keys, bounded busy handling, and `synchronous=FULL` preserve ordering and durability.
- **`jsonschema >=4.26,<5`:** Draft 2020-12 validation — schemas are checked and retained at registration; validation proves shape, never authority.
- **`httpx >=0.28.1,<1`:** direct async OpenAI, Anthropic, and local OpenAI-compatible HTTP/SSE adapters — one provider-neutral proposal boundary without SDK retry behavior.
- **stdlib JSON plus `asyncio.subprocess`:** strict stdio JSON-RPC transport — bounded frames, minimal environments, handshake versioning, cancellation cleanup, and no shell execution.
- **Hatchling 1.31.0, PEP 621/735 metadata, and uv 0.11.29:** build and contributor workflow — produce standard wheel/sdist artifacts that install without uv or Node.
- **pytest, pytest-asyncio strict mode, Hypothesis, coverage, Ruff, mypy strict, and pip-audit:** verification toolchain — compatibility, state-machine, failure, real-adapter, and clean-wheel tests matter more than coverage percentage.
- **MkDocs, Material, and mkdocstrings:** Python-only documentation build — handwritten semantic contracts remain normative; generated pages cover only the supported Python API.

Exact tool pins are time-sensitive inputs to the lockfile, not semantic contracts. Reconfirm them when Phase 28 creates `uv.lock`; never use post-3.12 syntax or behavior in shipped code, and do not add an upper Python bound.

### Expected Features

**Must have (table stakes):**

- Canonical ontology, typed IDs, exact Event grammar, explicit codecs, expected-position append semantics, and golden compatibility fixtures.
- One Engine-owned Command path for every mutation origin, with persisted accepted, rejected, deferred, and superseded `CommandDecision` traces.
- Complete Run, Message, ModelCall, Action, Wait, Delegation, Authority, Check, Checkpoint, Annotation, Artifact, Lease, and terminal-state semantics.
- Durable Actions with pre-dispatch recording, compact evidence, immutable Artifacts, cancellation, explicit unknown outcomes, and evidence-backed reconciliation.
- All five Wait kinds, governed approval revision/revalidation, bounded Delegation, join modes, and completion gates.
- Deterministic Views, Receipts, Reports, readiness, and replay from a complete known Event watermark.
- Real SQLite Event/Artifact/Lease persistence, atomic multi-Run append for Delegation, canonical Run homes, and restart/recovery behavior.
- Complete `.orun` export, semantic verification, replay, staged import, and non-authoritative ResumeAssessment.
- Full sandboxed filesystem, Markdown documents, bounded process, and local-only git capabilities through the generic capability boundary.
- OpenAI, Anthropic, and local OpenAI-compatible provider adapters that return proposals only and fail safely on malformed or secret-bearing responses.
- A thin complete CLI, deterministic governed coding demo, Python tests, clean wheel/sdist, Python-only live documentation, and no Node/TypeScript requirement.

**Should have (Python-native competitive quality):**

- `snake_case` APIs over exact camelCase wire aliases, frozen typed values, `py.typed`, structural dependency injection, and semantic exceptions that do not replace persisted decisions.
- Async context-managed runtime resources, `PathLike` inputs, a deliberate top-level import surface, and a local assembly factory with explicit override points.
- A reusable pytest contract kit if its supported-public status is deliberately approved during planning.
- Human and JSON CLI renderers backed by the same structured runtime query results.
- A thin context-managed sync facade only if required; it must delegate to the single async Engine and contain no independent semantics.

**Defer beyond v2.0:**

- Hosted multi-tenancy, distributed storage/leases, sharding, HA, rich UI, workflow or prompt/persona layers, and general observability infrastructure.
- Broad first-party capability catalogs, remote git/network credentials, provider routing/optimization, and document formats beyond Markdown.
- Persisted View snapshots until replay measurements justify them.
- Automatic cross-environment resume; verified import can diagnose missing bindings but cannot grant Authority.
- General plugin discovery unless concrete v2.0 requirements justify it. Static registration is the safer launch default; any later entry-point discovery belongs only in assembly and remains opt-in and allowlisted.

### Architecture Approach

Build a deep `RuntimeEngine` facade over pure command handlers, deterministic reducers, a single private append gate, and injected ports. Contracts own canonical meanings and codecs; Views reduce facts without deciding legality; storage persists without authoring lifecycle; capabilities and providers return untrusted results/proposals; Bundles move and verify history without authorizing it; assembly alone knows all concrete adapters; CLI and examples are thin consumers. The canonical API is async. If a sync client is retained, it owns an `asyncio.Runner` and delegates every operation.

#### Frozen compatibility contracts versus Python-native choices

| Frozen compatibility contract | Python-native design choice |
|---|---|
| Canonical Event names, versions, envelope/payload JSON, enum strings, missing-vs-null behavior, causation/correlation, IDs, timestamps, hashes, and Bundle commitments | `snake_case` attributes and methods, `PascalCase` classes, keyword-only constructors, explicit codec aliases, and `PathLike` inputs |
| `accepted` / `rejected` / `deferred` / `superseded` Command decisions and their traces/linkage | Frozen dataclasses, precise unions, typed exceptions for caller/storage/transport failures, and structured decision result values |
| Initial expected position `0`, first Event position `1`, atomic check-and-append, immutable history, and typed conflicts | Narrow async `Protocol` ports and an adapter-owned SQLite execution context; internal name `current_position`, not ambiguous predecessor naming |
| Engine-only authority, provider Operation proposals, worker `CapabilityResult`s, deterministic Views, and diagnostic-only ResumeAssessment | One `openrund` distribution, deep semantic modules, a curated public API, explicit composition root, and optional thin sync facade |
| Five Wait kinds, bounded Delegation, Action uncertainty/reconciliation, terminal legality, Artifact immutability, and Lease coordination-only semantics | `asyncio` structured concurrency, context-managed resources, pytest fixtures, and Python-specific extension ergonomics |
| `.orun` layout, schema versions, JSONL Events, canonical hashing/hash chain, profiles, integrity rules, replay, and issue vocabulary | Separate Python modules for export, verification, replay, import, audit, and resume assessment |

**Major components:**

1. **`contracts` and `ports`** — canonical ontology, IDs, Commands, decisions, Events, codecs, canonical JSON, and narrow storage/provider/capability/runtime interfaces with no infrastructure dependencies.
2. **`views`** — pure reducers for Run status/readiness, Actions, Waits, Delegation, Artifacts, Checkpoints, timeline, receipts, and reports at a known watermark.
3. **`engine`** — sole mutation facade, common submit pipeline, legality/terminal gates, private append gate, transition handlers, and durable provider/Action coordination.
4. **`storage.sqlite`** — migrations plus Event, Artifact, and Lease adapters, expected-position and atomic multi-Run transactions, connection ownership, and crash consistency.
5. **`capabilities` and `workers.documents`** — validated definitions/registry, in-process and strict stdio transports, Action execution, and one implementation each of filesystem/documents/process/git.
6. **`providers`** — private provider wire models, HTTP/SSE adapters, redaction, and provider-neutral ModelCall/Operation normalization.
7. **`bundles`** — exact `.orun` codec, canonical integrity, hostile-input verification, replay, staged import, audit, and ResumeAssessment.
8. **`assembly`, `cli`, and examples** — explicit local composition and lifecycle ownership, deterministic operator surfaces, and the flagship installed-package proof.

### Critical Pitfalls

1. **Lose compatibility before freezing the oracle** — capture predecessor-produced golden data for every serialized surface before broad Python implementation or any removal; resolve discrepancies in a versioned contract decision log.
2. **Create effects or authority outside the durable Engine path** — keep append private, persist Command and Action enabling Events before dispatch, re-enter worker/provider results as Commands, and test import/API boundaries continuously.
3. **Weaken storage, Artifact, or Delegation atomicity** — use short immediate transactions, explicit connection ownership, bounded conflict handling with reload/re-evaluation, insert-only Artifact identity, staged blob writes, and atomic multi-Run append.
4. **Trust async, capability, provider, or filesystem boundaries** — propagate cancellation, reap subprocess groups, bound all output, minimize environments, validate full envelopes/results, canonicalize paths twice, redact provider failures, and record uncertainty instead of blind retry.
5. **Treat Bundle integrity or dual-runtime coexistence as correctness** — semantic verification must check paths, versions, Run identity, positions, counts, Artifacts, and requirements; cut over once after Python parity rather than maintaining two live runtimes.

## Implications for Roadmap

Based on the dependency graph and the existing milestone numbering, use the following Phase 27–37 structure.

### Phase 27: Frozen Compatibility Oracle

**Rationale:** The only safe start is to turn existing behavior into inert, executable evidence while the predecessor can still produce it.
**Delivers:** Golden Events, decisions, Views, provider normalization, Artifact/SQLite records, and every `.orun` profile; a decision log resolves `actor`/`commandID`, omitted-vs-null fields, timestamp precision, policy payload encoding, positions, and hash inputs.
**Addresses:** SEM-01, SEM-02, the compatibility portion of EVT-01 and BND-01.
**Avoids:** Losing serialized compatibility, hand-authored fixtures, and premature predecessor removal.

### Phase 28: Python Distribution and Contract Kernel

**Rationale:** Every later layer must share one Python ontology and one explicit wire boundary.
**Delivers:** `pyproject.toml`, `src/openrund/`, typed IDs, immutable values, enums, Commands/decisions, Event catalog, canonical JSON, exact codecs, curated initial exports, `py.typed`, lockfile, and compatibility tests.
**Addresses:** SEM-01/02 and DX-01/02/03/05/06/08/10 foundations.
**Avoids:** File-for-file translation, implicit serialization, compatibility aliases, and a second object/serialization system.

### Phase 29: Deterministic Views and Replay Facts

**Rationale:** Legality should consume proven replay facts; reducers should stabilize before authority code obscures payload gaps.
**Delivers:** Complete-watermark replay and deterministic Run, readiness, timeline, Action, Wait, Delegation, Artifact, Checkpoint, Receipt, and Report reducers matched to golden streams.
**Addresses:** VIEW-01 and replay portions of RUN-01, ACT-01/02, WAIT-01, DEL-01, CHK-01, and ART-01.
**Avoids:** Views as hidden authority, incomplete payloads, and cache-dependent behavior.

### Phase 30: Durable Storage, Artifacts, and Leases

**Rationale:** The Engine and Delegation need trustworthy expected-position, immutability, and multi-Run primitives before lifecycle implementation.
**Delivers:** Narrow ports, deterministic in-memory test stores, SQLite migrations and startup checks, atomic expected-position append, `append_many`, immutable Artifact metadata/blob custody with staged recovery, Lease fencing, Run-home paths, concurrency/restart/crash tests, and an adapter-owned SQLite execution context.
**Addresses:** EVT-01, STO-01/02, ART-01, and the storage prerequisite for DEL-01.
**Avoids:** Off-by-one positions, stale-decision retry, global connections, event-loop blocking/transactions across awaits, partial Delegation creation, and blob/metadata drift.

### Phase 31: Engine Authority and Core Run Semantics

**Rationale:** One Command pipeline and private append gate must exist before specialized lifecycle features or external integrations.
**Delivers:** `RuntimeEngine.submit`, pure handlers and plans, `command.recorded`, all decision variants/traces, bootstrap, messages, Authority/policy, model proposal ingestion, terminal gates, conflict reload/re-evaluation, and post-commit subscriber isolation.
**Addresses:** ENG-01/02, RUN-01, MSG-01, GOV-01, and core DX-03/04/08/10.
**Avoids:** Public raw append, CLI/store shortcuts, sync divergence, subscriber-induced false failure, and terminal mutation bypasses.

### Phase 32: Governed Coordination and Recovery Semantics

**Rationale:** Waits are the shared blocker primitive; Checks, reconciliation, and Delegation must reuse the established Engine and stable storage/views.
**Delivers:** All Wait kinds, approval revision/revalidation, Checks and Checkpoints, Action unknown/reconciled transition semantics, bounded Delegation, join modes, child Authority, cancellation/late handoff rules, completion gating, and atomic parent/child establishment.
**Addresses:** WAIT-01/02, CHK-01, DEL-01, ACT-02, and the remaining GOV-01 behavior.
**Avoids:** Approval-as-override, new blocker roots, blind retry, parent/child lifecycle conflation, and descriptive-but-unenforced delegated grants.

### Phase 33: Capability Runtime, Durable Actions, and Built-ins

**Rationale:** Real effects can be added only after Command legality, Artifacts, Wait/reconciliation, and storage boundaries are enforceable.
**Delivers:** Definition/schema registry, in-process and strict stdio JSON-RPC transports, durable two-turn Action execution, bounded output and Artifact materialization, cancellation/unknown-outcome fault handling, plus the single sandboxed filesystem, Markdown documents worker, process, and local git implementations.
**Addresses:** CAP-01, ACT-01/02, BUILTIN-01/02/03, ART-01, and relevant DX-04/07/09.
**Avoids:** Effects before durable acceptance, worker-authored Events, path/symlink escapes, ambient credential leakage, malformed results, unbounded process output, and orphan children.

### Phase 34: Providers and Durable Run Loop

**Rationale:** Provider integration should target stable ModelCall, Command, Action, and cancellation semantics rather than inventing them.
**Delivers:** Shared normalization, direct HTTPX OpenAI/Anthropic/local adapters, bounded SSE, sanitized typed failures, deterministic `MockTransport` coverage, opt-in real smoke calls, ModelCall lifecycle, explicit retry policy, and lease-owned durable run/resume coordination.
**Addresses:** PROV-01, remaining MSG-01, DX-04/09, and provider portions of CLI/demo readiness.
**Avoids:** Provider SDK leakage, malformed arguments becoming empty input, secret-bearing exceptions, hidden retries, nominal live tests, and provider output becoming authority.

### Phase 35: Portable `.orun` Bundles

**Rationale:** Bundle semantics depend on stable Events, Views, Artifacts, policy, capabilities, providers, and terminal/recovery state.
**Delivers:** Exact export profiles, canonical commitments/hash chain, fail-closed path/schema/semantic verification, replay, atomic staged import, audit data, and deterministic non-authoritative ResumeAssessment against golden and malicious fixtures.
**Addresses:** BND-01 and portability portions of SEM-02, VIEW-01, ART-01, and REL-01.
**Avoids:** Hash-only verification, unsafe paths/symlinks, unknown Event versions, inconsistent requirements, import-as-resume, and Python-only Bundle compatibility tests.

### Phase 36: Local Assembly, CLI, and Flagship Demo

**Rationale:** Product surfaces should consume finished structured runtime services and prove them, not contain missing semantics.
**Delivers:** Explicit local composition root, default paths/capabilities/providers, lifecycle cleanup, optional thin sync facade, stable public imports, full deterministic text/JSON CLI, and installed-package governed coding demo covering rejection, approval, execution, uncertainty/reconciliation, Delegation, Checks, completion, and Bundle portability.
**Addresses:** CLI-01, DEMO-01, DX-04/05/08/09/10, and end-to-end coverage of all P1 clusters.
**Avoids:** CLI-local legality/explanations, hidden Authority defaults, duplicate filesystem implementations, sync logic drift, and demo-only behavior.

### Phase 37: Python-Only Cutover, Documentation, and Release

**Rationale:** Removal is safe only after the Python wheel proves every frozen behavior and operator flow; one cutover prevents indefinite drift.
**Delivers:** Rewritten greenfield Python docs/examples, strict MkDocs build, full Python CI matrix, sdist/wheel and extras tests, clean-environment demo, package-content and stale-reference scans, removal of live TypeScript/JavaScript/Node/pnpm/generated surfaces, and retention of Git plus clearly archived planning/history evidence.
**Addresses:** REL-01 and final acceptance for every mandatory feature cluster.
**Avoids:** Long-lived dual runtimes, predecessor-facing live documentation, broken source-only imports, undeclared tooling, and accidental deletion of historical evidence.

### Phase Ordering Rationale

- Compatibility evidence precedes all implementation because wire drift is the only migration error that may become impossible to diagnose after cutover.
- Contracts precede Views; Views and storage precede Engine legality; the Engine precedes waits/delegation; all of those precede real external effects.
- Providers follow the generic durable Action/ModelCall boundaries, and Bundles follow every lifecycle whose Events and requirements they must verify.
- CLI, assembly, and the demo remain thin because they arrive after structured runtime services; documentation/removal/release is one final gate, not a parallel product track.
- Every phase lands Python-native ergonomics with its semantic foundation instead of postponing API quality to a risky cleanup phase.

### Research Flags

Phases likely needing `$gsd-plan-phase --research-phase <N>`:

- **Phase 27:** HIGH — adjudicate known Event envelope/payload contradictions and generate a demonstrably complete predecessor-produced oracle.
- **Phase 30:** MEDIUM — finalize adapter-owned SQLite thread/connection confinement, busy behavior, Artifact blob/metadata recovery, and atomic multi-Run transactions.
- **Phase 32:** HIGH — specify Delegation multi-stream failure/recovery and every join, cancellation, late-handoff, approval-revision, and reconciliation edge.
- **Phase 33:** HIGH — enumerate crash/cancellation points around durable Action dispatch and verify path, symlink, environment, schema, output-limit, and subprocess cleanup security.
- **Phase 34:** MEDIUM — recheck current provider HTTP/SSE/tool-call contracts and live smoke-test boundaries without importing SDK semantics.
- **Phase 35:** HIGH — confirm byte-level canonicalization, cross-platform hostile path handling, semantic verification, and every ResumeAssessment issue kind.

Phases with strong local references or standard patterns (skip research-phase unless Phase 27 exposes a discrepancy):

- **Phase 28:** Python packaging/layout and explicit codec patterns are well documented once contract decisions are frozen.
- **Phase 29:** Existing reducers and golden expected Views provide a strong behavioral oracle.
- **Phase 31:** Normative authority/Command documentation and current transition tests strongly define the Engine kernel.
- **Phase 36:** Composition, `argparse`, deterministic rendering, and demo assembly are standard consumers of already-built services.
- **Phase 37:** Python packaging, docs, clean-install, source scan, and archival boundaries are clear release gates.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Recommendations are grounded in official Python/PyPA/SQLite/library documentation, but exact versions are time-sensitive and SQLite async execution has one design choice to finalize. |
| Features | HIGH | Required behavior is triangulated across the milestone contract, normative docs, codebase maps, and existing direct behavior/E2E tests. |
| Architecture | HIGH for semantic boundaries; MEDIUM for Python decomposition | Engine authority, dependency order, and serialized contracts are established; module granularity, sync facade, test kit, and plugin posture are Python design choices. |
| Pitfalls | HIGH for repository hazards; MEDIUM for some recovery mechanisms | Compatibility, authority, ordering, trust, and cutover risks are directly evidenced; exact Artifact and multi-Run recovery algorithms require phase design. |

**Overall confidence:** HIGH on what must be preserved and the roadmap order; MEDIUM on time-sensitive versions and a few Python-native implementation choices.

### Gaps to Address

- **Compatibility contradictions:** Resolve Event `actor`/`commandID`, SQLite `commandID` round-trip, policy-rule payload encoding, optional omission versus `null`, timestamp precision, ID/hash inputs, and any declaration-versus-emission mismatch in Phase 27.
- **Oracle completeness:** Define a coverage manifest proving every Event type/version, decision variant, View, provider normalization outcome, SQLite row, Artifact state, and Bundle profile has predecessor-produced evidence.
- **SQLite execution model:** Reconcile the simple synchronous stdlib adapter with the async Engine by choosing and testing one adapter-owned connection/execution context; never share a connection across arbitrary tasks or hold a transaction across `await`.
- **Artifact crash recovery:** Specify exact ordering, quarantine, cleanup, and visible unavailable/corrupt states for staged filesystem blobs plus SQLite metadata.
- **Delegation atomicity:** Confirm the public port and recovery behavior for backends that cannot offer SQLite-style atomic multi-stream append; v2.0 local SQLite must provide `append_many`.
- **Public DX scope:** Decide whether `openrund.testing` and the sync facade are supported v2.0 APIs. Neither may duplicate semantics.
- **Plugin scope:** Default to static registration. Add entry-point discovery only if requirements name it, and then keep it opt-in, allowlisted, assembly-only, and deprived of Engine/store access.
- **Provider drift:** Validate HTTP/SSE/tool-call mappings at Phase 34 planning and before release; deterministic fixtures remain the gate, while real calls are optional drift detectors.
- **Release logistics:** Reconfirm package-name availability, credentials, supported patch versions, and locked tool versions during Phase 37 without changing the Python `>=3.12` semantic baseline.

## Sources

### Primary (HIGH confidence)

- `.planning/PROJECT.md` and `.planning/MILESTONES.md` — active v2.0 scope, compatibility, Python-only, and archival constraints.
- `docs/concepts.md`, `docs/control.md`, `docs/architecture.md`, and `docs/events.md` — ontology, Engine authority, legality, Event grammar, and terminal rules.
- `docs/capabilities.md`, `docs/providers.md`, `docs/storage.md`, `docs/bundles.md`, and `docs/delegation.md` — subsystem contracts, trust boundaries, portability, and failure semantics.
- `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md`, `CONCERNS.md`, and `TESTING.md` — implementation topology, hazards, and proven verification patterns.
- Existing runtime/core/capability/storage/provider/Bundle/CLI source plus public API, ontology guard, and governed-demo tests — executable parity evidence to freeze, not a Python API-shape mandate.
- `.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, and `PITFALLS.md` — the four research tracks synthesized here.

### Secondary (MEDIUM confidence)

- Official Python documentation — supported versions, dataclasses, typing/Protocols, `asyncio`, `sqlite3`, `argparse`, subprocesses, `pathlib`, and `importlib.metadata`.
- Python Packaging User Guide and PyPA specifications — PEP 517/518/621, dependency groups, `src/` layout, wheel/sdist practices, and `pyproject.toml`.
- Official SQLite documentation — transactions, isolation, WAL, PRAGMAs, durability, and filesystem constraints.
- Official jsonschema, JSON Schema Draft 2020-12, HTTPX, JSON-RPC, OpenAI, Anthropic, uv, Hatchling, pytest, Hypothesis, Ruff, mypy, coverage, pip-audit, MkDocs, and Markdown-tool documentation — selected library behavior and current releases.

### Tertiary (LOW confidence)

- None used as a roadmap authority. Any ecosystem behavior not backed by project evidence or official documentation must be validated during the flagged phase.

---
*Research completed: 2026-08-04*
*Ready for roadmap: yes*
