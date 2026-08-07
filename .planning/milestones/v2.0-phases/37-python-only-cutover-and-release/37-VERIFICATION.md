---
phase: 37-python-only-cutover-and-release
verified: 2026-08-04T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred: []
---

# Phase 37 Verification — Python-Only Cutover and Release

## Verdict

**Passed.** OpenRund stands alone as one typed Python distribution with one
authoritative implementation, Python-only live product surfaces, authenticated
compatibility evidence, exact release contents, and no open release or security
finding. DX-06, REL-01, REL-02, and REL-03 are satisfied.

## Goal Achievement

| # | Required truth | Status | Evidence |
|---|---|---|---|
| 1 | Wheel and source distribution install cleanly with an empty base dependency set and run the installed flagship command. | VERIFIED | Isolated wheel/source installs, installed typing probe, worker interpreter probe, and governed-coding console demo pass. |
| 2 | The complete quality and behavioral gate passes on Python 3.12–3.14. | VERIFIED | 972 passed and 3 opt-in skips on each interpreter; coverage, mypy, Ruff, lock, build, docs, security, fixtures, Bundles, and demos pass. |
| 3 | Every live product, code, test, example, package, and command surface is Python-native and current. | VERIFIED | Cutover inventory, extension, removed-root, command, documentation, and exact distribution tests pass. |
| 4 | The executable oracle was retired only after all immutable retirement gates passed. | VERIFIED | `37-RETIREMENT-GATES.md` records RET-01 through RET-10 and the pre-deletion 3.12–3.14 matrix; cutover followed in a later commit. |
| 5 | Compatibility provenance remains inspectable without a second executable implementation. | VERIFIED | Authenticated frozen manifest/JSONL corpus and Git history remain; generators, verifiers, and alternate runtime code are absent. |

## Automated Evidence

| Check | Result |
|---|---|
| Python 3.12 | PASS — 972 passed, 3 opt-in live-provider checks skipped |
| Python 3.13 | PASS — 972 passed, 3 opt-in live-provider checks skipped |
| Python 3.14 | PASS — 972 passed, 3 opt-in live-provider checks skipped |
| Branch coverage | PASS — 79% at enforced threshold |
| Strict mypy | PASS — 224 source/test/example files |
| Ruff lint and format | PASS — 225 files |
| Lockfile | PASS — 15 packages resolved |
| Fresh distributions | PASS — `openrund-2.0.0` wheel and source distribution |
| Wheel SHA-256 | `2d4df963c3c9a9732c0b30f60acc23f94ec22e8b0de107f7c592515c9a359186` |
| Source-distribution SHA-256 | `88f060ddc85110a4501210afad773b82b5516775322f659c61078d1896beb41d` |
| Code review | PASS — clean, 0 open findings |
| Security audit | PASS — 10 threats closed, 0 open |

## Requirement Coverage

| Requirement | Status | Evidence |
|---|---|---|
| DX-06 | SATISFIED | Versioned standards package, empty base, test extra, clean wheel/source installs, installed command. |
| REL-01 | SATISFIED | Complete supported-interpreter, behavior, coverage, type, lint, docs, security, package, and demo matrix. |
| REL-02 | SATISFIED | Python-only source/test/example/package/docs inventory and greenfield terminology gates. |
| REL-03 | SATISFIED | Authenticated retirement ordering, retained inert corpus, removed executables, one implementation. |

## Gaps

None.

