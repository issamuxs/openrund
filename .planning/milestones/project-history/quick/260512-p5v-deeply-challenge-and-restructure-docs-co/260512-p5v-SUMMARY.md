---
quick_id: 260512-p5v
slug: deeply-challenge-and-restructure-docs-co
status: complete
completed: 2026-05-12
implementation_commit: 5195e41
---

# Quick Task Summary: Deep Ontology Restructure For `docs/concepts.md`

## Outcome

Completed. `docs/concepts.md` was rewritten from a broad glossary into a
stricter ontology reference organized around canonical entities,
relationships, identities, lifecycle events, operations, derived views, and
boundaries.

## Key Changes

- Removed `Compatibility Helper` as an ontology category; helper aliases are
  now treated as API compatibility, not ontology.
- Made `Transition Request` the meta entity with symmetrical `Model Request`,
  `Input Request`, and `Control Request` variants.
- Separated entity nouns from event-state verbs such as `created`, `added`,
  `requested`, `recorded`, `completed`, and `resolved`.
- Added explicit naming conventions for human concept names, TypeScript
  symbols, event literals, operation literals, fields, and helper APIs.
- Added a root hierarchy, canonical relationship table, lifecycle verb
  convention table, boundary rules, dependency graphs, non-concepts, and an
  admission checklist.

## Verification

- `pnpm test -- tests/docs/docs-links.test.ts tests/public-api/exports.test.ts`
  passed.
- `pnpm hygiene` passed.
- `pnpm typecheck` passed.
- Stale ontology guard search returned no matches for removed request and
  delegation terms in `docs/concepts.md`.
