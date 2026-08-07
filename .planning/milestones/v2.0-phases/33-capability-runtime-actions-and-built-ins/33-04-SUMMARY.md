---
phase: 33-capability-runtime-actions-and-built-ins
plan: "04"
status: complete
completed: 2026-08-05
requirements: [BUILTIN-01]
commits: [a96677e]
---

# Plan 33-04 Summary

Completed filesystem write, update, delete, move, and diff actions with per-action closed schemas. Mutations require writable mounts, portable paths, bounded input, file-only targets, explicit parent creation, overwrite intent, and expected hashes for existing content.

Writes use same-directory staging, full writes, fsync, atomic replace, directory sync, target revalidation, and cleanup. Delete is non-recursive. Move revalidates source and destination, requires a target hash before replacement, and rejects cross-device fallback. Diff is UTF-8-only, deterministic, bounded, and Artifact-backed. Every mutation emits compact effects, evidence, and a receipt Artifact.

Verification passed with 24 filesystem tests, 148 capability and Engine tests, strict mypy, Ruff, and diff checks.
