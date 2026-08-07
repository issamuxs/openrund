---
type: quick
slug: ontology-surface-audit-after-control
status: complete
completed: 2026-05-13
commit: uncommitted
---

# Summary

Audited the Phase 8.8 control additions against the locked ontology and
secondary-surface doctrine.

## Result

The audit found one real drift: exported `ControlFinding` / `ControlCheck`
names made `Control` look entity-like, and `Finding` was not an approved
secondary suffix.

## Corrections

- Renamed `ControlCheck` to `LegalityCriterion`.
- Renamed `ControlFinding` to `CommandDecisionTraceEntry`.
- Renamed decision payload field `findings` to `decisionTrace`.
- Renamed Check report row type from `CheckFinding` to `CheckReportEntry`.
- Updated docs and Phase 8.8 / Phase 9 planning language from Control findings
  to Command decision trace entries.

## Verification

```bash
pnpm typecheck
pnpm hygiene
pnpm test -- tests/docs/docs-links.test.ts tests/core/commands.test.ts tests/public-api/exports.test.ts
```

All passed.
