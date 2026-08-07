---
phase: 36
slug: local-assembly-cli-and-flagship-demo
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-06
---

# Phase 36 — Validation Strategy

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest on Python 3.12; strict mypy; Ruff lint/format |
| Quick run | `uv run --python 3.12 pytest tests/assembly tests/operator tests/cli -q` |
| Full suite | `uv run --python 3.12 pytest -q` |
| Process posture | isolated homes, deterministic clocks/IDs, no network or ambient credentials |

## Per-Plan Verification Map

| Plan | Requirements | Automated target | Status |
|---:|---|---|---|
| 36-01 | DX-09 | explicit local assembly, lifetime, no implicit roots/Authority | ✅ passed |
| 36-02 | DX-10 | deliberate package-root API and operator results | ✅ passed |
| 36-03 | CLI-01 | read-only Run, timeline, waits, commands, receipts, readiness, Checks, Artifacts | ✅ passed |
| 36-04 | CLI-01 | Engine-backed control plus every Bundle operation and exit class | ✅ passed |
| 36-05 | DEMO-01 | deterministic governed coding workflow through installed surfaces | ✅ passed |
| 36-06 | CLI-01, DEMO-01, DX-09, DX-10 | integration, security, docs, wheel/sdist, parity | ✅ passed |

## Wave 0 Requirements

- [x] Production and seeded assembly fixtures.
- [x] CLI process harness for text, JSON, stdout/stderr, and exits.
- [x] Package-root export allowlist and installed-wheel typing.
- [x] Installed-demo isolated-environment harness.
- [x] No-UI and no-second-authority architecture fences.

## Manual-Only Verifications

None.
