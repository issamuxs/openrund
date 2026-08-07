---
type: quick
slug: ontology-surface-audit-after-control
status: planned
created: 2026-05-13
---

# Quick Task: Ontology Surface Audit After Control Additions

## Goal

Check whether Phase 8.8 control additions polluted or overexpanded the core
ontology, secondary surface naming, event verbs, or suffix doctrine.

## Tasks

1. Scan new control-related nouns and exported types.
2. Check core ontology docs remain limited to the approved root concepts.
3. Check secondary concepts use approved suffixes and do not introduce
   disallowed suffixes.
4. Check Event verbs/subjects remain within existing grammar.
5. Patch only real drift.
6. Record audit result.

## Verification

```bash
pnpm hygiene
pnpm test -- tests/docs/docs-links.test.ts tests/core/commands.test.ts tests/public-api/exports.test.ts
```
