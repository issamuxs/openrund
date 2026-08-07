---
quick_id: 260514-i5s
slug: align-control-doc-authority-model
status: complete
completed: 2026-05-14
---

# Summary

Aligned `README.md` and `docs/control.md` with the current authority model.

## Changes

- Removed TypeScript from the README opening sentence.
- Rewrote the Control opening to separate Operation proposal, Command evaluation, and CommandDecision outcome.
- Replaced collapsed `Command decision` lifecycle diagrams with `Command -> CommandDecision -> Events`.
- Reframed first-class governance as direct participation in runtime execution semantics.
- Split canonical runtime-governance primitives from attached or derived governance surfaces.
- Removed weaker operational and portability rows from the Control Primitives table.
- Added explanation-layer wording that CLI/operator surfaces derive explanations and do not decide legality.

## Verification

- `node scripts/check-ontology-canonical.mjs` — pass.
- `pnpm hygiene` — pass.
- `pnpm package:check` — pass.
