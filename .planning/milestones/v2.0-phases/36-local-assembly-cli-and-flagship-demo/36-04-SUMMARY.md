---
phase: 36-local-assembly-cli-and-flagship-demo
plan: "04"
status: complete
completed: 2026-08-06
requirements: [CLI-01]
commits: [c12d6a1]
---

# Plan 36-04 Summary

Completed Engine-backed Run creation/advance, approval resolve/resume, Action
reconciliation, Check recording, and every Bundle command. Added the installed
`openrund` console entry point and stable usage, not-found, rejection,
integrity, availability, and internal exit classes.

Mutation methods only construct typed Commands and call the Engine; Bundle
operations retain verified lifecycle and non-authoritative import semantics.
