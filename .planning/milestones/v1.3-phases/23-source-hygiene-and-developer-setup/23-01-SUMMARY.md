---
phase: "23"
plan: "23-01"
status: complete
completed_at: 2026-05-15
requirements:
  - HYG-01
  - HYG-02
  - HYG-03
---

# Phase 23 Plan 23-01 Summary

## One-Liner

Removed source-side generated artifact drift, made hygiene reject future generated files under package source directories, and added a root verification path for the Python documents worker.

## Completed Work

- Removed stale ignored generated files from `packages/storage-sqlite/src` so tests resolve current TypeScript sources rather than outdated JavaScript.
- Extended `scripts/check-hygiene.mjs` with a direct filesystem scan for generated `.js`, `.js.map`, `.d.ts`, and `.d.ts.map` files under `packages/*/src`.
- Added `tests/public-api/hygiene.test.ts` to prove the hygiene script rejects a generated source artifact.
- Added `pnpm test:python-documents` in `package.json`.
- Updated `README.md`, `docs/README.md`, and `docs/contributing.md` with Python documents worker setup and verification commands.

## Tests Added

- `tests/public-api/hygiene.test.ts` creates a temporary `packages/core/src/__hygiene_probe__.js`, verifies `scripts/check-hygiene.mjs` fails with the generated-source rule, and removes the probe.

## Verification

- `pnpm test` passed: 56 test files, 231 tests passed, 2 skipped.
- `pnpm hygiene` passed: canonical ontology, secondary surface naming, and hygiene checks passed.
- `pnpm test:python-documents` passed: 4 pytest tests passed.
- `find packages -path '*/src/*' \( -name '*.js' -o -name '*.js.map' -o -name '*.d.ts' -o -name '*.d.ts.map' \) -type f` returned no files.

## Notes

- The hygiene scan intentionally walks the filesystem directly so ignored generated files cannot shadow TypeScript sources without being detected.
- Python worker dependency installation remains explicit rather than hidden in `pnpm install`.
