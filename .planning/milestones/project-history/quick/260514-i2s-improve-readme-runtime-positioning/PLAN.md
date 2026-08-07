---
quick_id: 260514-i2s
slug: improve-readme-runtime-positioning
status: planned
created: 2026-05-14
---

# Quick Task: Improve README Runtime Positioning

## Objective

Improve `README.md` first-contact clarity after the ontology cleanup.

## Scope

- Sharpen the opening around OpenRund as a runtime model implemented in TypeScript.
- Add a concise "why" paragraph contrasting runtime governance with middleware governance.
- Add core runtime invariants.
- Align lifecycle diagrams with `Command -> CommandDecision -> Events`.
- Keep the tone disciplined and non-marketing.
- Rename verification section to repository verification.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm hygiene`
- `pnpm package:check`
