---
phase: 36-local-assembly-cli-and-flagship-demo
plan: "06"
status: complete
completed: 2026-08-06
requirements: [CLI-01, DEMO-01, DX-09, DX-10]
commits: [e0cbc97]
---

# Plan 36-06 Summary

Sealed the installed assembly, API, operator service, CLI, and demonstration
with no-second-authority, no-ambient-root/credential, parity, determinism,
interrupt, import, package, and no-graphical-interface fences. Rewrote live
usage and contributor documentation for the Python package and command line.

The full gate passed with 963 tests and three expected opt-in live-provider
skips, strict mypy across 219 source/test files, Ruff lint/format, lock
verification, wheel/sdist builds, isolated installed-console execution, and
clean diff checks.
