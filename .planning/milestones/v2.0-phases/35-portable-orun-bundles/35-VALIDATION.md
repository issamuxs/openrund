---
phase: 35
slug: portable-orun-bundles
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-06
---

# Phase 35 — Validation Strategy

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest on Python 3.12; strict mypy; Ruff lint/format |
| Quick run | `uv run --python 3.12 pytest tests/bundles -q` |
| Full suite | `uv run --python 3.12 pytest -q` |
| Filesystem posture | isolated temporary roots; no network or user-home data |

## Per-Plan Verification Map

| Plan | Requirement | Automated target | Status |
|---:|---|---|---|
| 35-01 | BND-01 | immutable contracts, exact hashes, strict paths | ✅ passed |
| 35-02 | BND-01 | deterministic three-profile export | ✅ passed |
| 35-03 | BND-01 | fail-closed verify and replay | ✅ passed |
| 35-04 | BND-01 | authenticated frozen-profile cross-read | ✅ passed |
| 35-05 | BND-01 | atomic import and resume assessment | ✅ passed |
| 35-06 | BND-01 | integration, malicious input, docs, package gate | ✅ passed |

## Wave 0 Requirements

- [x] Fixture builders for complete Run history and Artifact custody.
- [x] Exact schema-1 hash vectors and frozen profile records.
- [x] Malicious path, symlink, malformed manifest, and Event-gap matrices.
- [x] Import crash/collision and no-authority assertions.
- [x] Installed-wheel typing and package-content checks.

## Manual-Only Verifications

None.

## Validation Sign-Off

- [x] Every plan has automated behavior evidence.
- [x] No graphical UI validation applies.
- [x] Replay/import tests assert that no canonical Event or Authority is created.
