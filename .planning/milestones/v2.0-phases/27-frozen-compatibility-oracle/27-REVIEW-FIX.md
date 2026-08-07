---
phase: 27-frozen-compatibility-oracle
review: 27-REVIEW.md
iteration: 1
fixed: 2026-08-05T07:36:00Z
scope: critical_warning
status: complete
findings_fixed: 9
---

# Phase 27 Code Review Fix Report

## Result

All eight critical findings and the warning from the first standard-depth review were fixed with regression coverage. The stale frozen corpus was removed through a corpus-only revert, regenerated twice from one clean protected-source revision, compared byte-for-byte, verified independently, and promoted once into the absent committed root.

## Finding Commits

| Finding | Commit(s) | Resolution |
|---|---|---|
| CR-01 | `4f61a72` | Runtime Engine and Action Dispatcher propagate the injected identity source through every production control/materialization path. |
| CR-02 | `a13108c` | The verifier enforces typed envelope and exact variant-specific payload schemas for every frozen Event. |
| CR-03 | `4d850b6` | Committed-corpus verification requires a full Git commit `provenance.sourceRevision`. |
| CR-04 | `3aad0f6` | Generation and verification consume one canonical protected-source inventory including all normative docs and build/test inputs. |
| CR-05 | `16fd9d7` | Generation and verification enforce the exact 22-entry resolved decision ledger and reject malformed, missing, duplicate, extra, or unresolved rows. |
| CR-06 | `145d354`, `3c7964c` | Corpus output is assembled in an owned sibling root and published atomically only to an absent destination; unsafe ancestors and root swaps fail closed. Direct evidence helpers retain compatibility with already-created empty temporary roots. |
| CR-07 | `b9f90f7` | Artifact IDs are validated at the store boundary and may resolve only to direct children of the canonical Artifact root. |
| CR-08 | `bcc2d35` | Artifact writes are insert-only, conflicts reject before staging, blob publication is exclusive, and database/filesystem rollback preserves existing bytes. |
| WR-01 | `a04ad56` | SQLite read-back omits absent optional Artifact/blob fields instead of materializing own `undefined` properties. |

## Corpus Recovery and Promotion

- `b8cb9c6` reverted only the stale corpus promotion, restoring an absent committed target.
- Clean source revision: `b8cb9c6f7809a86f80e59f7b262d73115944b097`.
- Two fresh promotion-mode roots each verified `ok: true` with `286` checked evidence files.
- Cross-comparison reported no added, removed, or changed files; `diff -qr` was empty.
- `07a1ae3` promoted the verified corpus as a 287-file corpus-only commit, writing evidence before `manifest.json`.
- Post-commit verification accepts HEAD advancement because the protected source tree still matches the recorded revision.

## Validation Evidence

- `pnpm test` — 68 files passed; 380 tests passed; 2 credential-gated tests skipped.
- `pnpm typecheck` — passed.
- `pnpm test:python-documents` — 4 passed.
- `pnpm compatibility:verify:v1` — passed; 286 evidence files checked; zero issues.
- Focused regression suites for provenance, decisions, output-root safety, Artifact confinement/immutability, and SQLite absence semantics all passed before their atomic commits.

## Remaining Work

None from the first review. A fresh standard-depth re-review is required to confirm closure and detect regressions introduced by the fixes.
