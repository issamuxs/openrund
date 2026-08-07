---
quick_id: 260512-qhe
slug: align-all-documentation-with-locked-conc
status: complete
completed: 2026-05-12T19:20:06+02:00
commit: a36276e
---

# Summary: Align Documentation With Locked Ontology

## Completed

- Reframed public docs around the locked `docs/concepts.md` ontology.
- Updated event documentation to distinguish canonical concepts from current
  persisted event literals.
- Reworked principles, architecture, capabilities, providers, delegation,
  storage, runtime semantics, quickstart, `.orun`, API, and example README
  language to use canonical concepts first.
- Updated active Phase 9 and Phase 10 context so CLI/demo work does not carry
  stale ontology forward.

## Verification

- `pnpm test -- tests/docs/docs-links.test.ts tests/public-api/exports.test.ts`
- `pnpm typecheck`
- `pnpm hygiene`
- Stale-term scans for old model-step/subsession terminology passed outside the
  locked legacy-mapping section of `docs/concepts.md`.

## Notes

- This task did not rename code types, API names, or persisted event literals.
- Current names such as `SessionRuntime`, `sessionID`, `session.*`,
  `model.request.*`, `validation.recorded`, `child_session.*`, and
  `projections` are documented as implementation mappings rather than
  independent ontology roots.
