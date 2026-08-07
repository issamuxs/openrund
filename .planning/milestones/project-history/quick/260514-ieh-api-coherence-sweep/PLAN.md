---
quick_id: 260514-ieh
slug: api-coherence-sweep
status: planned
created: 2026-05-14
---

# Quick Task: API Coherence Sweep

## Objective

Ensure code, generated package outputs, docs, examples, tests, and archive docs are coherent with the current `docs/api.md`.

## Scope

- Remove stale generated outputs for retired source module names.
- Sweep the repository for retired API/surface names.
- Update archive references that otherwise read as current API names.
- Keep guard-script literals that intentionally block retired names.
- Run full repository verification.

## Verification

- repo-wide stale-name sweep
- `node scripts/check-ontology-canonical.mjs`
- `pnpm hygiene`
- `pnpm test`
- `pnpm package:check`
