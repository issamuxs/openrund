---
quick_id: 260514-hyv
slug: soften-governance-surface-taxonomy
status: complete
completed: 2026-05-14
---

# Summary

Refined `docs/concepts.md` so the attached governance and secondary-surface sections keep the semantic distinction without over-prescriptive naming language.

## Changes

- Reframed "Attached Governance Surfaces" as "Attached Governance Semantics".
- Described attached semantics as participating in legality/runtime lifecycle without becoming root ontology concepts.
- Replaced "Approved secondary suffixes" with "Common secondary suffixes".
- Removed `IndexView` and `Milestone` from the suffix guidance; added `Index`.
- Replaced hard "banned" wording with guidance to avoid exported ontology-facing names that imply authority, mutable runtime truth, or standalone lifecycle semantics.

## Verification

- `node scripts/check-ontology-canonical.mjs` — pass.
- `pnpm hygiene` — pass.
