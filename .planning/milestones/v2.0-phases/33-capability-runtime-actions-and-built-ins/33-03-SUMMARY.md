---
phase: 33-capability-runtime-actions-and-built-ins
plan: "03"
status: complete
completed: 2026-08-05
requirements: [BUILTIN-01]
commits: [0335418]
---

# Plan 33-03 Summary

Implemented immutable named filesystem mounts, root verification, portable relative path resolution, lexical escape rejection, component-by-component lstat checks, symlink refusal, containment proof, and no-follow regular-file descriptors.

Added validated filesystem read, list, and stat Capability actions. Reads are size-bounded, hashed, and returned as inline Artifact material; binary content is never decoded. Listings are sorted, entry-bounded, and classify symlinks without following them. Stat hashes bounded regular files and handles directories explicitly.

Verification passed with 14 focused malicious-path/limit tests, 138 capability and Engine tests, strict mypy, Ruff, and diff checks.
