---
phase: 33-capability-runtime-actions-and-built-ins
plan: "06"
status: complete
completed: 2026-08-05
requirements: [BUILTIN-03]
commits: [ad948a4]
---

# Plan 33-06 Summary

Completed an interruptible process Capability built around immutable named executable bindings. Bindings pin an absolute, non-symlink executable identity and define only fixed environment values plus enumerated caller-selectable values. Invocations use argument-vector execution without a shell, receive no inherited environment, require a writable named-root cwd, and enforce argument, stdin, timeout, and retained-output bounds.

Stdout and stderr are drained completely to prevent pipe deadlock, hashed over their full streams, and retained only up to configured limits as required Artifacts with truncation metadata. Known exits, signals, and reaped timeouts return explicit effect evidence. Runtime cancellation terminates or kills and reaps the child before propagating cancellation.

Verification passed with 11 focused process tests covering credential/PATH isolation, environment values, inert shell syntax, unbound network tools, cwd traversal/symlinks, argument/stdin/output bounds, spawn failure, signals, timeout escalation, and cancellation cleanup. The combined capability/Engine suite passed 170 tests with strict mypy, Ruff, and diff checks.
