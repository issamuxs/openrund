---
quick_id: 260514-hyv
slug: soften-governance-surface-taxonomy
status: planned
created: 2026-05-14
---

# Quick Task: Soften Governance Surface Taxonomy

## Objective

Refine `docs/concepts.md` so attached governance semantics and secondary surfaces remain disciplined without over-prescriptive naming doctrine.

## Scope

- Keep the distinction between root ontology concepts, attached governance semantics, and secondary surfaces.
- Rename and broaden the attached governance section.
- Replace "approved suffixes" with "common suffixes".
- Replace hard "banned" wording with guidance against exported ontology-facing authority ambiguity.
- Do not change runtime code.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm hygiene`
