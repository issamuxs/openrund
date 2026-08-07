---
quick_id: 260514-fjg
slug: architecture-governance-phrasing
status: planned
created: 2026-05-14
---

# Quick Task: Architecture Governance Phrasing

## Objective

Adjust `docs/architecture.md` so the architecture contract removes ambiguity around Action dispatch, terminal Run mutations, capability completion, View authority, diagnostics, provider package naming, and Delegation Authority.

## Scope

- Update architecture wording only.
- Avoid review-note phrasing or instructions to a reviewer/model.
- Preserve the locked ontology and runtime governance direction.
- Run deterministic documentation/ontology checks available in the repo.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm hygiene`
