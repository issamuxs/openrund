# Quick Task 260514-nb8: Documentation Ownership Consolidation

## Goal

Consolidate OpenRund documentation ownership after the ontology/governance
clarification pass. Preserve the governed mutation runtime direction while
reducing unnecessary repeated philosophy and stale framing.

## Scope

- Review live docs as one semantic system.
- Produce ownership audit, refactor plan, and consistency report.
- Apply focused refactors directly in docs.
- Do not rewrite project philosophy.
- Do not introduce new ontology concepts or product/platform language.

## Primary Docs

- `README.md`
- `docs/README.md`
- `docs/concepts.md`
- `docs/control.md`
- `docs/architecture.md`
- `docs/api.md`
- `docs/events.md`
- `docs/capabilities.md`
- `docs/delegation.md`
- `docs/bundles.md`
- `docs/quickstart.md`
- `docs/providers.md`
- `docs/storage.md`

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm test -- tests/docs/docs-links.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
