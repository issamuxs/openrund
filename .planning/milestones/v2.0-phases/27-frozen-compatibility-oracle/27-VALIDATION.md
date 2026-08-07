---
phase: 27
slug: frozen-compatibility-oracle
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-04
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.5 for oracle contracts; pytest for the supplemental transported-documents scenario |
| **Config file** | `vitest.config.ts`; `python/openrund_documents_worker/pyproject.toml` |
| **Quick run command** | `pnpm exec vitest run tests/compatibility/oracle-manifest.test.ts tests/compatibility/oracle-wire.test.ts` |
| **Full suite command** | `pnpm test && pnpm test:python-documents` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run the focused compatibility test named in the task, plus `pnpm typecheck` when source or types change.
- **After every plan wave:** Run `pnpm test`; also run `pnpm test:python-documents` when transported-document evidence changes.
- **Before `$gsd-verify-work`:** The full suite, two-run regeneration check, manifest completeness check, and committed-corpus drift check must be green.
- **Max feedback latency:** 30 seconds for focused tests.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 1 | SEM-02 | T-27-01-05 | Independent Event/View-branch/encoding/number/field-policy inventories reject missing, duplicate, unknown, and overwritten keys | contract | `pnpm exec vitest run tests/compatibility/oracle-manifest.test.ts -t "inventory"` | ✅ | ✅ green |
| 27-01-02 | 01 | 1 | SEM-02 | T-27-01-06 | All three research questions and every byte/meaning ambiguity are resolved before generation | contract/docs | `pnpm exec vitest run tests/compatibility/oracle-manifest.test.ts -t "decision ledger"` | ✅ | ✅ green |
| 27-01-03 | 01 | 1 | SEM-02 | T-27-01-05 | Event declarations, strict/allowlisted field policy, docs, and normalization inventory agree | contract | `pnpm exec vitest run tests/core/event-normalization.test.ts tests/compatibility/oracle-manifest.test.ts` | ✅ | ✅ green |
| 27-02-01 | 02 | 2 | SEM-02 | T-27-02-01 | SQLite command linkage preserves non-null current and SQL NULL legacy states | integration | `pnpm exec vitest run tests/storage/sqlite-store.test.ts` | ✅ | ✅ green |
| 27-07-01 | 07 | 2 | SEM-02 | T-27-07-01 | Malformed/non-object provider arguments fail closed with safe errors | contract/security | `pnpm exec vitest run tests/providers/provider-normalization.test.ts tests/providers/openai.test.ts tests/providers/anthropic.test.ts tests/providers/local-openai-compatible.test.ts` | ✅ | ✅ green |
| 27-07-02 | 07 | 2 | SEM-02 | T-27-07-03 | Fixed exportedAt preserves Bundle profile commitments | integration/determinism | `pnpm exec vitest run tests/runtime/orun-bundle.test.ts` | ✅ | ✅ green |
| 27-03-01 | 03 | 3 | SEM-02 | T-27-03-03 | Fixed entropy, Git-derived revision, forged-revision rejection, and dirty promotion/read-only boundaries fail closed | determinism/security | `pnpm exec vitest run tests/compatibility/oracle-regeneration.test.ts -t "fixed entropy|fresh output|source revision|dirty"` | ✅ | ✅ green |
| 27-03-02 | 03 | 3 | SEM-02 | T-27-03-06 | Engine, Action, and reconciliation bytes/links use injected identities | determinism/invariant | `pnpm exec vitest run tests/runtime/action-lifecycle.test.ts tests/runtime/action-reconciliation.test.ts tests/compatibility/oracle-regeneration.test.ts -t "Engine|Action|reconciliation"` | ✅ | ✅ green |
| 27-08-01 | 08 | 4 | SEM-02 | T-27-08-02 | Artifact identity, exact UTF-8 byte length, and composed/decomposed no-normalization are deterministic and synthetic | integration/security | `pnpm exec vitest run tests/runtime/artifact-materialization.test.ts tests/storage/sqlite-artifact.test.ts tests/compatibility/oracle-regeneration.test.ts -t "Artifact|byte length|Unicode"` | ✅ | ✅ green |
| 27-04-01 | 04 | 5 | SEM-02 | T-27-04-06 | Check, Checkpoint, and Delegation topology/links regenerate exactly | determinism/invariant | `pnpm exec vitest run tests/runtime/check-gate.test.ts tests/runtime/checkpoint.test.ts tests/runtime/delegation-spawn.test.ts tests/runtime/delegation-joins.test.ts tests/runtime/delegation-cancellation.test.ts tests/compatibility/oracle-regeneration.test.ts -t "Check|Checkpoint|Delegation"` | ✅ | ✅ green |
| 27-04-02 | 04 | 5 | SEM-02 | T-27-04-06 | All five Wait kinds cover lifecycle, null/absence, and timer threshold edges | state/edge | `pnpm exec vitest run tests/runtime/interaction-waits.test.ts tests/runtime/timer-waits.test.ts tests/runtime/wait-approval.test.ts tests/runtime/wait-approval-revision.test.ts tests/compatibility/oracle-regeneration.test.ts -t "Wait|timer|approval"` | ✅ | ✅ green |
| 27-04-03 | 04 | 5 | SEM-02 | T-27-04-03 | Bundle profiles are fixed and contain no live/private input | determinism/security | `pnpm exec vitest run tests/compatibility/oracle-regeneration.test.ts -t "Bundle profiles"` | ✅ | ✅ green |
| 27-05-01 | 05 | 6 | SEM-02 | T-27-05-05 | Event/Command/material-View/provider plus escaping/number/field-policy evidence covers independent inventories | golden/replay/security | `pnpm exec vitest run tests/compatibility/oracle-wire.test.ts tests/compatibility/oracle-views.test.ts tests/compatibility/oracle-providers.test.ts` | ✅ | ✅ green |
| 27-05-02 | 05 | 6 | SEM-02 | T-27-05-01 | SQLite/Artifact/Bundle raw, decoded, and commitment evidence is complete | integration/golden | `pnpm exec vitest run tests/compatibility/oracle-sqlite.test.ts tests/compatibility/oracle-artifacts.test.ts tests/compatibility/oracle-bundles.test.ts` | ✅ | ✅ green |
| 27-06-01 | 06 | 7 | SEM-02 | T-27-06-05 | Unsafe/tampered/incomplete/forged corpora and strict-envelope/payload-policy violations fail read-only | integrity/negative | `pnpm exec vitest run tests/compatibility/oracle-rejections.test.ts tests/compatibility/oracle-manifest.test.ts` | ✅ | ✅ green |
| 27-06-02 | 06 | 7 | SEM-02 | T-27-06-06 | Routine dirty-worktree drift verification never writes and reports added/removed/changed files | determinism/drift | `pnpm exec vitest run tests/compatibility/oracle-regeneration.test.ts` | ✅ | ✅ green |
| 27-06-03 | 06 | 7 | SEM-02 | T-27-06-07 | Oracle stays internal and RET-01 through RET-10 block indefinite retention | architecture/release | `pnpm exec vitest run tests/compatibility/oracle-retirement.test.ts` | ✅ | ✅ green |
| 27-09-01 | 09 | 8 | SEM-02 | T-27-09-01 | Finalized source/provenance tests prove pre-promotion capture, later corpus/unrelated commit acceptance, protected-tree drift rejection, forgery rejection, and no corpus writes | provenance/security | `pnpm exec vitest run tests/compatibility/oracle-regeneration.test.ts tests/compatibility/oracle-manifest.test.ts -t "source revision|promotion provenance|forged|later commit|stale"` | ✅ | ✅ green |
| 27-09-02 | 09 | 8 | SEM-02 | T-27-09-02 | Corpus-only promotion from the clean source commit seals two-run-identical evidence with complete inventory/file/View/fallback bijection | promotion/determinism | `pnpm exec vitest run tests/compatibility/oracle-regeneration.test.ts tests/compatibility/oracle-manifest.test.ts tests/compatibility/oracle-wire.test.ts tests/compatibility/oracle-views.test.ts tests/compatibility/oracle-rejections.test.ts` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `scripts/compatibility/oracle-inventory.ts` — independent expected inventories and duplicate detection.
- [x] `scripts/compatibility/generate-v1-oracle.ts` — deterministic generator with an explicit fresh output root.
- [x] `scripts/compatibility/verify-v1-oracle.ts` — read-only recursive verifier and human-readable diff.
- [x] `tests/compatibility/oracle-manifest.test.ts` — completeness, uniqueness, references, and tree integrity.
- [x] `tests/compatibility/oracle-wire.test.ts` — exact bytes, presence/null pointers, IDs, timestamps, positions, and links.
- [x] `tests/compatibility/oracle-views.test.ts` — every material reducer/result branch beneath all nine View surfaces through focused streams.
- [x] `tests/compatibility/oracle-providers.test.ts` — provider outcome matrix using fixed mocks only.
- [x] `tests/compatibility/oracle-sqlite.test.ts` — schema, indexes, raw rows, SQL NULL, and decoded evidence.
- [x] `tests/compatibility/oracle-artifacts.test.ts` — Artifact state matrix.
- [x] `tests/compatibility/oracle-bundles.test.ts` — all three Bundle profiles and commitments.
- [x] `tests/compatibility/oracle-rejections.test.ts` — malformed, unsupported, tampered, and unsafe-path inputs.
- [x] `tests/compatibility/oracle-regeneration.test.ts` — two-run determinism and committed-corpus drift.
- [x] `tests/compatibility/oracle-retirement.test.ts` — package/public-surface guard and Phase 37 retirement gates.
- [x] `tests/fixtures/compatibility/v1/manifest.json` plus its fully referenced corpus tree — committed by Task 27-09-02 after the protected source snapshot was clean, followed by two-run equality, ledger closure, and read-only verification.
- [x] `docs/archive/compatibility-v1-decisions.md` — closed writer/backward-read/rejected-defect ledger.

---

## Manual-Only Verifications

All phase behaviors have automated verification. Promotion of a new corpus version remains an explicit maintainer action, but its prerequisites and resulting bytes are machine-checked.

---

## Validation Sign-Off

- [x] All tasks have automated verification or Wave 0 dependencies.
- [x] Sampling continuity: every task has focused automated feedback; no three-task gap exists.
- [x] Wave 0 covers all missing test references.
- [x] No watch-mode or snapshot-update flags are used.
- [x] Focused commands are scoped; measured latency is recorded during execution.
- [x] Two fresh generations are byte-identical.
- [x] The ambiguity ledger has zero unresolved byte-or-meaning decisions before promotion.
- [x] Promotion records the clean pre-promotion source commit, writes only the corpus tree, rejects dirty protected inputs, and post-promotion verification allows corpus-only/unrelated commits while rejecting committed protected-source drift.
- [x] `nyquist_compliant: true` and `wave_0_complete: true` record the complete implemented plan/test mapping and committed corpus.

**Approval:** passed — 2026-08-05
