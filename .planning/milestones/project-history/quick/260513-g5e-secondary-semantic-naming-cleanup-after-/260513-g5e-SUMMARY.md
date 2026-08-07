---
status: complete
created: 2026-05-13
quick_id: 260513-g5e
slug: secondary-semantic-naming-cleanup-after-
---

# Summary

Completed a secondary semantic naming cleanup after the ontology migration.

Changes:
- Renamed output contract surfaces from `GovernedOutput*` to output-artifact requirement names.
- Renamed model operation validator results from `ModelOperationCheck*` to `ModelOperationValidation*`.
- Replaced capability binding/policy record naming with Authority grant and PolicyRule vocabulary.
- Renamed capability worker result/spec/config types away from runtime Action terminology.
- Renamed `RunRuntime` to `RuntimeEngine` and moved the implementation file to `runtime-engine.ts`.
- Renamed `.orun` exported type/helper surfaces toward Bundle vocabulary while preserving the `.orun` file format.
- Aligned model context builder names and returned control keys with the canonical `commandContract` and `waits` model.
- Extended the secondary-surface hygiene checker to reject the cleaned-up stale names.

Verification:
- `pnpm typecheck`
- `pnpm test`
- `pnpm hygiene`
