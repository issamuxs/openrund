# Quick Summary: Final Documentation Ontology Consistency Pass

## Result

Applied the final documentation ontology consistency pass across the public docs.
The docs now consistently use `docs/concepts.md` as the locked ontology source
and frame current implementation names as compatibility surfaces.

## Changes

- Tightened the canonical mutation path across docs: ModelCall -> Operation ->
  Command -> Events -> Views.
- Normalized Wait kinds to `approval`, `interaction`, `timer`, `join`,
  `external_signal`, `operational_backoff`, `operational_exhaustion`, and
  `reconciliation`.
- Removed remaining ambiguous delegation, authority, capability lifecycle, and
  approval-expiry wording.
- Added Command compatibility notes, target API names, and current-vs-canonical
  migration guidance.
- Separated Message from Annotation in the event reference and kept
  `session.waiting` / `session.resumed` as compatibility facts only.

## Verification

- `rg` stale-term scan for the final correction guide: passed with only
  compatibility-safe legacy mapping mentions.
- `pnpm test -- tests/docs/docs-links.test.ts tests/public-api/exports.test.ts`
  passed.
- `pnpm typecheck` passed.
- `pnpm hygiene` passed.

## Commits

- Docs commit: `55b70d1`.
- Tracking commit: `ba6ae2f`.
