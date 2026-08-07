---
quick_id: 260512-qw7
slug: tighten-concepts-md-ontology-mappings
status: complete
completed: 2026-05-12T19:23:52+02:00
commit: 8b8ad1d
---

# Summary: Tighten `docs/concepts.md` Ontology Mappings

## Completed

- Tightened Rule 2 so runtime entities require identity, lifecycle, and
  references, while value types, Views, Bundles, helpers, relationships, and
  aliases can remain non-entity ontology terms.
- Removed the ambiguous ModelCall-to-Event path: ModelCall responses yield
  parsed Operations; the Engine records Commands; accepted Commands produce
  state-changing Events.
- Made child Run, Delegation, and join Wait lifecycle mappings deterministic.
- Chose registry-only Capability semantics for the minimal ontology.
- Replaced ambiguous policy-to-Authority mappings with compatibility-event
  language pending a later Authority migration.
- Replaced prose child join mappings with exact current event literals.

## Verification

- `pnpm test -- tests/docs/docs-links.test.ts tests/public-api/exports.test.ts`
- `pnpm typecheck`
- `pnpm hygiene`
