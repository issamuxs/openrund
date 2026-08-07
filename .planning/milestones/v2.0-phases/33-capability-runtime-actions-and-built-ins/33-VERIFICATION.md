---
phase: 33-capability-runtime-actions-and-built-ins
verified: 2026-08-05T23:59:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred: []
---

# Phase 33 Verification — Capability Runtime, Actions, and Built-ins

## Verdict

**Passed.** Extension authors and runtime hosts can execute real work only through durable governed Actions and validated Capability boundaries. All five roadmap criteria and CAP-01, ACT-01, BUILTIN-01, BUILTIN-02, and BUILTIN-03 are verified by executable tests.

## Goal Achievement

| # | Required truth | Status | Evidence |
|---|---|---|---|
| 1 | Validated definitions execute through in-process or strict stdio transports and return data rather than Events. | VERIFIED | Closed registry/result codecs, transport framing, schema, cancellation, timeout, and AST authority-fence tests pass. |
| 2 | Mutating work is durable before dispatch and has compact Artifact-backed, reliability-aware, exactly-current outcomes. | VERIFIED | Ordered Action integration tests cover start-before-effect, terminal commits, receipts, cancellation, unknown outcomes, and reconciliation. |
| 3 | Filesystem operations remain workspace-bounded with read-only posture and guarded atomic mutations. | VERIFIED | Read/list/stat/write/update/delete/move/diff adversarial suites cover traversal, symlinks, stale hashes, overwrite, and atomic replacement. |
| 4 | The root-bound Markdown worker supports reads, writes, structural patches, hashes, diffs, sections, ranges, append, and frontmatter. | VERIFIED | Worker protocol and real installed-wheel stdio tests exercise every operation and failure class. |
| 5 | Process and local Git operations are bounded and exclude ambient shell, network, credential, and helper authority. | VERIFIED | Actual subprocess/repository tests cover fixed verbs, env, arguments, streams, timeout, cancellation, patches, staging, commits, and hostile configuration. |

**Score:** 5/5 must-haves verified.

## Automated Evidence

| Check | Result |
|---|---|
| Capability integration/package regression | PASS — 17 passed |
| Full Python suite | PASS — 827 passed |
| Strict mypy | PASS — 152 source/test files |
| Ruff lint and format | PASS — 152 files |
| Lockfile and distributions | PASS |
| Installed-wheel worker and typing | PASS |
| Authenticated Python compatibility suite | PASS — included in full pytest |
| Plan completeness | PASS — 8 plans, 8 summaries |
| Standard-depth code review | PASS — clean |
| Security audit | PASS — 10 threats closed, 0 open |

The sealed predecessor provenance command rejects the expanded Python test tree because its historical source commitments cover whole directory roots. It was not weakened or regenerated: Python authenticates and consumes the frozen corpus, and Phase 37 owns removal of that executable tool after the remaining cross-read and installed-package gates pass.

## Requirement Coverage

| Requirement | Status | Evidence |
|---|---|---|
| CAP-01 | SATISFIED | Validated definitions, registry bindings, strict result codec, in-process transport, and stdio JSON-RPC transport are complete. |
| ACT-01 | SATISFIED | Action runner enforces durable custody, Artifact materialization, cancellation reliability, terminal uniqueness, and unknown outcomes. |
| BUILTIN-01 | SATISFIED | Root-confined filesystem reads and guarded atomic mutations are complete. |
| BUILTIN-02 | SATISFIED | Root-bound Markdown stdio worker and structured operations are complete. |
| BUILTIN-03 | SATISFIED | Bounded process execution and fixed local-only Git operations are complete. |

## Gaps

None in Phase 33 behavior.
