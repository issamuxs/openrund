---
phase: 35-portable-orun-bundles
verified: 2026-08-06T18:00:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred: []
---

# Phase 35 Verification — Portable `.orun` Bundles

## Verdict

**Passed.** Operators can export, verify, replay, import, and assess portable governed Run evidence without hidden state, implicit Authority, or automatic resume. BND-01 is satisfied.

## Goal Achievement

| # | Required truth | Status | Evidence |
|---|---|---|---|
| 1 | Complete, audit, and redacted profiles contain canonical history, commitments, metadata, reports, Artifacts, and explicit resume requirements. | VERIFIED | Deterministic profile export, omission, Artifact, report, and commitment tests pass. |
| 2 | Verification and replay fail closed and cross-read every authenticated frozen profile with compatible commitments. | VERIFIED | Structural, cryptographic, semantic, replay, and frozen-profile matrices pass. |
| 3 | Import stages and publishes verified evidence atomically; resume assessment is deterministic and non-authoritative. | VERIFIED | Collision, tamper, mapping, imported-record, and all resume issue tests pass without Event or Authority creation. |
| 4 | Malicious paths, links, versions, identities, gaps, counts, Artifacts, policies, and undeclared nodes are rejected. | VERIFIED | Adversarial Bundle and architecture-hygiene suites pass. |

## Automated Evidence

| Check | Result |
|---|---|
| Full Python suite | PASS — 936 passed, 3 opt-in live checks skipped |
| Strict mypy | PASS — 194 source/test files |
| Ruff lint and format | PASS — 194 files |
| Lockfile and distributions | PASS |
| Installed-wheel typing | PASS |
| Plan completeness | PASS — 6 plans, 6 summaries |
| Standard-depth code review | PASS — final report clean |
| Security audit | PASS — 10 threats closed, 0 open |

## Requirement Coverage

| Requirement | Status | Evidence |
|---|---|---|
| BND-01 | SATISFIED | Three profiles, exact commitments, strict verify/replay, authenticated cross-read, atomic import, and non-authoritative resume assessment are complete. |

## Gaps

None.
