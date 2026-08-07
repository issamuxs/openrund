---
phase: 34-providers-and-durable-run-loop
verified: 2026-08-06T12:00:00Z
status: passed
score: 3/3 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred: []
---

# Phase 34 Verification — Providers and Durable Run Loop

## Verdict

**Passed.** Runtime hosts can drive long-running model interaction through provider-neutral, resource-safe async execution without granting provider output authority. PROV-01 and DX-04 are satisfied.

## Goal Achievement

| # | Required truth | Status | Evidence |
|---|---|---|---|
| 1 | OpenAI, Anthropic, and local-compatible adapters share normalization and direct async HTTP/SSE, returning proposals only. | VERIFIED | JSON/SSE request-response matrices, neutral normalization tests, and architecture fences pass. |
| 2 | Malformed output and transport failures fail safely; offline mocks prove normalization; real calls are opt-in. | VERIFIED | Malicious response/framing/argument tests and three default-skipped `live_provider` checks pass. |
| 3 | Engine, storage, provider, loop, and worker lifetimes are explicit and cancellation preserves facts without orphans. | VERIFIED | Context closure, use-after-close, exact lifecycle ordering, cancellation, worker PID reaping, and concurrency tests pass. |

## Automated Evidence

| Check | Result |
|---|---|
| Full Python suite | PASS — 893 passed, 3 opt-in live checks skipped |
| Strict mypy | PASS — 169 source/test files |
| Ruff lint and format | PASS — 169 files |
| Lockfile and distributions | PASS |
| Installed-wheel typing | PASS |
| Plan completeness | PASS — 6 plans, 6 summaries |
| Standard-depth code review | PASS — one first-pass defect fixed; final report clean |
| Security audit | PASS — 10 threats closed, 0 open |

## Requirement Coverage

| Requirement | Status | Evidence |
|---|---|---|
| PROV-01 | SATISFIED | Three concrete adapters, neutral normalization, direct async HTTP/SSE, safe errors, deterministic tests, and opt-in drift checks are complete. |
| DX-04 | SATISFIED | Async-first loop plus explicit Engine/storage/provider/worker lifetimes preserve ModelCall/Action facts and reap owned resources. |

## Gaps

None.
