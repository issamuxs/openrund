---
status: complete
quick_id: 260514-cq2
completed: 2026-05-14
---

# Quick Task Summary: Rerun Phase 12-17 Coherence Checks

## Completed

- Re-ran ontology, secondary surface, command path, governance, CLI, and doc/code gap checks against the Phase 18 patched code.
- Updated Phase 12-17 milestone artifacts with post-Phase-18 rerun findings.
- Hardened `scripts/check-ontology-canonical.mjs` so it audits current public/production surfaces instead of failing on historical `.planning/` archives.
- Added explicit guard coverage for resolved old public names: `CommandDecisionRecord`, `EffectRecord`, `LeaseRecord`, `ArtifactRecord`, and `retainedFacts`.
- Updated the public ontology guard test description to match the corrected scope.

## Findings

- Current packages/docs/tests/examples no longer expose the resolved Phase 18 old public names.
- No shipped CLI/demo surface introduced `receiptID`, `receiptIdentity`, `gateExplanation`, `outcomeExplanation`, or `openrund why`.
- Remaining raw append usage is fixture/test setup oriented; the flagship demo uses runtime-owned Check recording.
- Phase 12-17 artifacts were stale after Phase 18 and now include post-patch rerun notes.

## Verification

- `node scripts/check-ontology-canonical.mjs`: passed.
- `pnpm build`: passed.
- `pnpm exec vitest run tests/public-api/ontology-guards.test.ts tests/examples/governed-coding-run.test.ts tests/runtime/action-reconciliation.test.ts tests/runtime/timer-waits.test.ts tests/runtime/interaction-waits.test.ts tests/runtime/checkpoint.test.ts tests/views/checkpoints.test.ts`: passed, 7 files / 33 tests.
- `pnpm demo:governed-coding-run`: passed.
- `pnpm test`: passed, 55 files / 214 tests / 2 skipped.
- `pnpm package:check`: passed.

## Result

The post-Phase-18 coherence pass is complete. The runtime/governance artifacts now reflect the patched state, and the full test suite passes.
