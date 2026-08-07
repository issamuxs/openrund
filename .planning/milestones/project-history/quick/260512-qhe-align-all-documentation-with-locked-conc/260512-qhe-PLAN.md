---
quick_id: 260512-qhe
slug: align-all-documentation-with-locked-conc
status: in_progress
created: 2026-05-12
---

# Quick Plan: Align Documentation With Locked Ontology

## Objective

Make the documentation set consistent with the locked ontology in
`docs/concepts.md`, without migrating code or persisted event literals in this
task.

## Scope

- Treat `docs/concepts.md` as the semantic source of truth.
- Update public docs so they use canonical concepts first: Run, Command, Event,
  Message, ModelCall, Action, Wait, Delegation, Check, Checkpoint, Annotation,
  Artifact, Capability, Authority, Lease, Bundle, and View.
- Where current TypeScript names or event literals differ, describe them as
  current implementation literals or compatibility mappings, not ontology roots.
- Update relevant phase planning context only where it would otherwise carry
  stale public-facing guidance into Phase 9 or Phase 10.

## Tasks

1. Inventory stale or ambiguous ontology terms across public docs and active
   planning docs.
2. Rewrite documentation language that incorrectly promotes implementation
   helpers, current event literals, projections, or compatibility terms into
   concepts.
3. Add clear ontology notes to documents that must still reference current
   implementation names.
4. Run documentation/public-surface checks and record residual scope.
5. Commit the documentation alignment and GSD tracking artifacts separately.

## Non-Goals

- Do not rename code types, event literals, tests, or persisted data.
- Do not change the locked ontology in `docs/concepts.md`.
- Do not start the Phase 9 CLI implementation.
