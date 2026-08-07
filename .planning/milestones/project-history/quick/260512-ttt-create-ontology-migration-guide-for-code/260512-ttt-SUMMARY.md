# Quick Summary: Create Ontology Migration Guide

## Result

Created `docs/ontology-migration.md` as the mechanical control surface for the
codebase ontology refactor.

## Changes

- Added current-to-target maps for concepts, event literals, and model
  operations.
- Defined package-by-package migration order across core contracts, event
  codecs, Command path, Wait collapse, Message/Annotation, Delegation, Checks,
  Checkpoints, providers, capabilities, Views, public APIs, CLI, and tests.
- Added compatibility policy for old event literals, package exports, CLI
  commands, `.orun` manifests, and old-history tests.
- Added migration test checklist and red flags that should block future
  refactor patches.
- Linked the guide from `docs/README.md`, `docs/architecture.md`, and
  `docs/concepts.md`.

## Verification

- `rg` link/discovery scan for `ontology-migration`: passed.
- `rg` red-flag scan: passed; only intentional "do not introduce" bullets
  matched.
- `pnpm test -- tests/docs/docs-links.test.ts tests/public-api/exports.test.ts`
  passed.
- `pnpm typecheck` passed.
- `pnpm hygiene` passed.

## Commits

- Docs commit: `3527de4`.
- Tracking commit: `15f6a74`.
