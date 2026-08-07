---
quick_id: 260514-ibv
slug: tighten-api-surface-semantics
status: planned
created: 2026-05-14
---

# Quick Task: Tighten API Surface Semantics

## Objective

Apply the API review where it reflects current runtime semantics.

## Scope

- Remove stale `runRun(runID)` from API docs; no such public method exists.
- Strengthen `RuntimeEngine` method description around Command evaluation.
- Strengthen `append(...)` warning as a legality-bypassing escape hatch.
- Rename CLI `.orun` resume command from `resume-report` to `resume-assessment`.
- Update API, Bundle, Quickstart, example, CLI, and tests for the new command.
- Clarify current View bundle field semantics without broad unrelated renames.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm hygiene`
- `pnpm test -- tests/runtime/cli-phase5.test.ts tests/public-api/exports.test.ts`
- `pnpm package:check`
