---
phase: 33-capability-runtime-actions-and-built-ins
plan: "05"
status: complete
completed: 2026-08-05
requirements: [BUILTIN-02]
commits: [420d766]
---

# Plan 33-05 Summary

Completed the Markdown documents Capability and its isolated one-request stdio JSON-RPC worker. The action catalog covers UTF-8 read, whole-document write, heading discovery, frontmatter read/set, exact section read/replace, one-based range replacement, append, and ordered structured patches. Reads return hashes and Markdown Artifact material; every mutation requires the current hash for an existing target and returns before/after hashes plus a bounded deterministic unified-diff Artifact.

The worker receives a minimal environment containing only explicit mount roots and limits. It independently repeats root, traversal, symlink, size, UTF-8, structural, ambiguity, and stale-hash checks. Its generic transport accepts only validated Capability results and safe failure classifications, so the worker has no Event or Engine authority.

Verification passed with 11 document tests—including actual subprocess invocation—and 159 capability/Engine tests, plus strict mypy, Ruff, and diff checks.
