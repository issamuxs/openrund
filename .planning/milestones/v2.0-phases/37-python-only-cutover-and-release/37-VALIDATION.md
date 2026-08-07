---
phase: 37
slug: python-only-cutover-and-release
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-06
---

# Phase 37 — Validation Strategy

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest plus branch coverage; strict mypy; Ruff lint/format |
| Supported Python | 3.12, 3.13, 3.14 |
| Package gate | isolated wheel and sdist installs with console demo |
| Process posture | offline normal suite; live providers opt-in only |

## Per-Plan Verification Map

| Plan | Requirements | Automated target | Status |
|---:|---|---|---|
| 37-01 | DX-06 | release metadata, version, extras, installed metadata | ✅ passed |
| 37-02 | REL-01 | coverage, docs, security, package, and release-quality gates | ✅ passed |
| 37-03 | REL-01, REL-03 | authenticated retirement matrix and Python 3.12-3.14 clean installs | ✅ passed |
| 37-04 | REL-02, REL-03 | remove executable oracle and every live non-Python surface; Python example | ✅ passed |
| 37-05 | REL-01, REL-02 | greenfield docs, exact package content, cutover and security fences | ✅ passed |
| 37-06 | DX-06, REL-01, REL-02, REL-03 | full clean release and milestone evidence | ✅ passed |

## Wave 0 Requirements

- [x] Coverage configuration and threshold.
- [x] Retirement-evidence authentication test.
- [x] Python-only source and distribution inventory test.
- [x] Clean wheel/sdist installed-console harness.
- [x] Documentation link and greenfield-language gate.

## Manual-Only Verifications

None. Live-provider network checks are automated but explicitly opt-in.
