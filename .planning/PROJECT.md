# OpenRund

## What This Is

OpenRund is a Python runtime framework for governed, durable agent Runs. The
runtime—not the model, provider, worker, or host application—decides which
mutations are legal, records immutable canonical facts, governs consequential
effects, and determines terminal state.

OpenRund is deliberately a runtime-semantics framework rather than a broad
agent platform, prompt framework, visual builder, observability product, or
capability marketplace.

## Core Value

Provide a minimal authoritative runtime where long-running agent work remains
lawful, durable, replayable, portable, and inspectable when models, workers,
processes, or infrastructure fail.

## Current State

**Shipped:** v2.0 Python OpenRund on 2026-08-06. No milestone is active.

**Delivered surface:**

- Immutable semantic contracts and exact canonical codecs.
- Deterministic Views rebuilt from complete Event history.
- SQLite Event, Artifact, and Lease custody with contained Run homes.
- One Engine-owned Command and legality boundary.
- Durable Wait, Authority, Action, reconciliation, Delegation, Check,
  Checkpoint, Annotation, Message, and ModelCall lifecycles.
- Filesystem, Markdown documents, bounded process, and Git Capabilities.
- OpenAI Responses, Anthropic Messages, and local OpenAI-compatible provider
  adapters with explicit configuration.
- Durable model loop and typed proposal adaptation.
- Deterministic `.orun` export, verification, replay, import, and resume
  assessment.
- Explicit local assembly, typed operator service, installed command, and
  offline governed-coding demonstration.
- Python 3.12, 3.13, and 3.14 verification and release gates.

## Requirements

### Validated

- [x] Keep `RuntimeEngine` as the sole mutation-authority boundary.
- [x] Record every attempted mutation as an accepted, rejected, deferred, or
  superseded Command decision.
- [x] Persist canonical ordered Events and rebuild explanatory Views
  deterministically at a declared complete watermark.
- [x] Preserve immutable Artifact identity and explicit content availability.
- [x] Coordinate executors through scoped expiring Leases without granting
  runtime Authority.
- [x] Govern approvals, interaction, timers, joins, and reconciliation through
  durable Waits.
- [x] Represent ambiguous external outcomes explicitly until evidence-backed
  reconciliation.
- [x] Bound Delegation lineage, Authority, resources, budgets, handoff, join,
  and cancellation behavior.
- [x] Keep providers and model output proposal-only.
- [x] Keep Capability workers result-only and route lifecycle mutations back
  through the Engine.
- [x] Export portable, integrity-checked `.orun` Bundles without turning
  import, replay, or resume assessment into Authority.
- [x] Provide a typed Python library, explicit local assembly, installed
  command, production-assembly example, and complete Python verification suite.

### Active

None. New requirements begin with the next milestone.

### Out of Scope

- Hosted multi-tenant control plane.
- Distributed storage, sharding, and high-availability coordination.
- Broad production Capability catalogs and general plugin discovery.
- Persisted View snapshots as an authoritative replacement for Event replay.
- Automatic cross-environment resume without explicit compatibility and root
  rebinding.
- A graphical interface; CLI interaction is a normal tested runtime adapter.

## Context

The normative product contract lives in `docs/`. `docs/architecture.md`,
`docs/concepts.md`, and `docs/events.md` define the authority loop and canonical
ontology. Provider, Capability, storage, Delegation, Bundle, API, and control
pages define each boundary in detail.

Canonical truth lives in ordered Events. Views, Reports, Receipts, and resume
assessments explain history but never decide legality. Large content is held
under immutable Artifact custody. External systems integrate through explicit
ports, provider adapters, or governed Capabilities.

## Constraints

- **Runtime:** Python 3.12 or newer; standard-library-only base installation.
- **Architecture:** Implementation conforms to the contracts in `docs/`.
- **Authority:** Only the Engine decides legality or materializes canonical
  lifecycle Events.
- **Durability:** Replay, recovery, audit, and handoff facts are Event-backed
  or Artifact-backed.
- **Effects:** Capability execution is explicit, bounded, evidence-producing,
  and never a second authority path.
- **Security:** Paths fail closed on escape or symbolic-link substitution;
  processes use explicit bindings and argument vectors; provider credentials
  are explicit inputs.
- **Uncertainty:** Ambiguous effects remain unknown until reconciled from
  evidence.
- **Portability:** Bundle replay and verification are portable; resume remains
  conditional on compatible policy, providers, Capabilities, roots, Waits,
  and Artifacts.
- **Quality:** Tests, branch coverage, strict typing, lint, format, lock,
  package-content, documentation, security, installed-demo, build, and
  supported-interpreter gates all pass before release.

## Key Decisions

| Decision | Rationale | Outcome |
|---|---|---|
| Reserve bare ontology names for canonical runtime concepts | Prevent explanatory surfaces from becoming accidental authority | Validated |
| Use one Engine-owned Command path for every mutation origin | Makes legality and attempted work auditable and consistent | Validated |
| Keep configuration reachability separate from durable Authority | Prevents host assembly from granting runtime permission implicitly | Validated |
| Treat approval as authorization, never as a legality override | Hard invariants remain non-overridable | Validated |
| Keep Views complete-watermark, deterministic, and explanatory | Replay remains reproducible and fail-closed | Validated |
| Store large content as immutable Artifacts outside Events | Keeps history compact without weakening evidence | Validated |
| Model unknown outcomes explicitly | Avoids fabricating success or failure after ambiguous effects | Validated |
| Keep Capabilities outside semantic core | Domain effects remain replaceable without bypassing governance | Validated |
| Ship one dependency-free Python base package | Keeps the runtime inspectable and easy to embed | Validated |
| Treat the installed command as an adapter over `OperatorService` | CLI behavior receives no separate authority or design pipeline | Validated |
| Keep OpenRund free of a graphical interface | The milestone proves runtime and operator contracts directly | Validated |

## Evolution

Update this document at phase and milestone transitions. Move completed active
requirements to validated, record new constraints and decisions, and keep the
core value aligned with the current product.

---
*Last updated: 2026-08-06 after the v2.0 milestone*
