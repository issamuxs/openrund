---
quick_id: 260514-i5s
slug: align-control-doc-authority-model
status: planned
created: 2026-05-14
---

# Quick Task: Align Control Doc Authority Model

## Objective

Remove TypeScript from the README opening sentence and align `docs/control.md`
with the current ontology: `Operation -> Command -> CommandDecision -> Events`.

## Scope

- Keep README lead runtime-first.
- Correct Control lifecycle diagrams.
- Rewrite opening Control wording to separate attempted mutation from decision outcome.
- Lead First-Class Governance with runtime execution semantics rather than capability checklist phrasing.
- Split canonical governance primitives from attached/derived surfaces.
- Remove weak operational/portability rows from the Control Primitives table.
- Add explicit explanation-layer non-authority wording.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm hygiene`
- `pnpm package:check`
