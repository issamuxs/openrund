---
phase: 29-deterministic-views-and-replay-facts
created: 2026-08-05
discuss_skipped: true
---

# Phase 29 Context — Deterministic Views and Replay Facts

## Locked Direction

- Implement one greenfield Python `openrund.views` package over the Phase 28 semantic Event catalog.
- Reducers are pure, deterministic, immutable read models. They never read stores, append Events, call the Engine, evaluate Commands, grant Authority, or decide legality.
- Callers supply a complete ordered Event history, the declared watermark, and any available Artifact values. No reducer discovers or assumes a watermark.
- An absent, invalid, mixed-Run, gapped, duplicated, out-of-order, or incomplete watermark returns a typed incomplete replay result with safe issue codes and no authoritative View bundle.
- A complete history returns one immutable bundle containing Run status/readiness, timeline, Action status/receipts/reconciliation, Wait queues for all five kinds, Artifact index, Checkpoints, Delegation state, and derived Reports.
- Match all 71 authenticated Phase 27 View fixtures at their declared watermarks without executing or importing any predecessor runtime.
- Keep serialized aliases and corpus projections in the explicit codec/test boundary; semantic View values remain `snake_case` and strongly typed.
- Keep the package root minimal until Phase 36 curates the installed public surface.

## Scope Boundaries

- No persisted View snapshots or caches.
- No Event, Artifact, Lease, or SQLite adapters.
- No Engine or policy implementation.
- No Bundle export/import implementation.
- No CLI implementation or terminal rendering contract.
- No graphical UI, UI workflow, UI-SPEC, UI safety gate, or UI review.

## Implementation Discretion

- Exact internal module split and final dataclass names.
- Whether reducers share one internal fold state or compose focused reducers, provided outputs and ordering remain deterministic.
- Test-only projection helpers used to compare typed Python values with frozen JSON evidence.

## Deferred

- Storage-backed reads and persisted snapshots: Phase 30 or later after replay measurements.
- Engine use of replay facts for legality: Phase 31.
- Full Wait/Delegation mutation semantics: Phase 32.
- Bundle summaries and replay transport: Phase 35.
- CLI presentation and root API curation: Phase 36.
