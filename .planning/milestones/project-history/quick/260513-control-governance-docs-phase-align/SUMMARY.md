---
type: quick
slug: control-governance-docs-phase-align
status: complete
completed: 2026-05-13
commit: uncommitted
---

# Summary

Integrated the final first-class governance refinement into live docs and Phase
8.8 / Phase 9 planning artifacts.

## Completed

- Added `docs/control.md` defining runtime governance, legality basis,
  control primitives, explanation-layer expectations, and falsifiability test.
- Updated docs index, architecture, concepts, and docs-link coverage.
- Aligned Phase 8.8 context, research, plans, patterns, validation, and roadmap
  criteria with first-class governance and explanation surfaces.
- Aligned Phase 9 context, plans, validation, and provisional note so CLI work
  must expose runtime-provided Command decisions, Control findings, receipts,
  and readiness without becoming an authority boundary.

## Verification

```bash
pnpm test -- tests/docs/docs-links.test.ts
pnpm hygiene
```

Both passed.
