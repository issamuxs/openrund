---
phase: 34
slug: providers-and-durable-run-loop
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-05
---

# Phase 34 — Validation Strategy

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest on Python 3.12; strict mypy; Ruff lint/format |
| Quick run | `uv run --python 3.12 pytest tests/providers tests/runtime -q` |
| Full suite | `uv run --python 3.12 pytest -q` |
| Network posture | offline deterministic by default; explicit live marker only |

## Per-Plan Verification Map

| Plan | Requirement | Automated target | Status |
|---:|---|---|---|
| 34-01 | PROV-01 | neutral tools, operation normalization, frozen evidence | ✅ passed |
| 34-02 | PROV-01, DX-04 | async HTTP/chunked/SSE bounds, cancellation, cleanup | ✅ passed |
| 34-03 | PROV-01 | OpenAI and local request/response normalization | ✅ passed |
| 34-04 | PROV-01 | Anthropic request/response normalization | ✅ passed |
| 34-05 | PROV-01, DX-04 | durable ModelCall start/terminal/proposal loop | ✅ passed |
| 34-06 | DX-04 | resource lifetimes, package typing, docs, release gate | ✅ passed |

## Wave 0 Requirements

- [x] Provider normalization fixtures and malicious argument cases.
- [x] Local async HTTP server and SSE fragmentation fixtures.
- [x] Deterministic OpenAI/local/Anthropic adapter responses.
- [x] Durable loop success/failure/cancellation/concurrency tests.
- [x] Async context cleanup and installed-wheel typing tests.
- [x] Opt-in live-provider marker that skips without explicit credentials.

## Manual-Only Verifications

None. Live drift checks are optional diagnostics, not completion evidence.

## Validation Sign-Off

- [x] Every plan has automated behavior evidence.
- [x] No graphical UI validation applies.
- [x] Normal verification performs no external provider calls.
