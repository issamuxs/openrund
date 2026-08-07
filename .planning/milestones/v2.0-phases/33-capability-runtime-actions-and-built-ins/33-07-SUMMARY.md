---
phase: 33-capability-runtime-actions-and-built-ins
plan: "07"
status: complete
completed: 2026-08-05
requirements: [BUILTIN-03]
commits: [48eb6b2]
---

# Plan 33-07 Summary

Completed a local-only Git Capability exposing exactly status, diff, head, apply, stage, and commit. Every action resolves a writable named mount to an exact repository root, requires a confined real `.git` directory, rejects symlinks and object alternates throughout Git metadata, bounds repository inspection, and fails closed on configuration sections capable of invoking helpers or loading external configuration.

Git runs through the bounded process substrate with an absolute pinned executable and no inherited environment, PATH, credentials, pager, editor, prompt, remote protocol, signing, or system/global configuration. Diff disables external drivers and text conversion. Apply checks bounded patch bytes before mutation. Stage accepts explicit portable non-option files only, reads them no-follow, hashes raw bytes without filters, and updates the index directly. Commit accepts a named configured identity, reads its message from stdin, and disables hooks and signing.

Verification passed with 18 actual-repository tests covering all six verbs, binary and deletion staging, full-stream hashes with bounded Artifacts, closed remote/config/submodule surfaces, option/path/repository escapes, symlinks, object alternates, malicious hooks/diff/clean/credential helpers, patch bounds, identity/message injection, and safe nonzero exits. The combined capability/Engine suite passed 188 tests with strict mypy, Ruff, and diff checks.
