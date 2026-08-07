---
quick_id: 260514-i07
slug: implement-surface-taxonomy-corrections
status: planned
created: 2026-05-14
---

# Quick Task: Implement Surface Taxonomy Corrections

## Objective

Apply the `docs/concepts.md` surface-taxonomy cleanup consistently across current documentation, code, tests, and guard scripts.

## Scope

- Update current contributing guidance to match the softer secondary-surface rule.
- Remove current public runtime/code names that still use `Milestone` as a runtime semantic surface.
- Remove `IndexView` from current exported view reducer naming.
- Update CLI/test expectations to use the corrected public names.
- Strengthen hygiene guard coverage for the retired names.
- Leave historical archives and GSD evidence untouched.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm hygiene`
- `pnpm test -- tests/runtime/runtime-progress-entries.test.ts tests/runtime/cli-phase5.test.ts tests/views/views.test.ts`
