---
phase: 33-capability-runtime-actions-and-built-ins
plan: "01"
status: complete
completed: 2026-08-05
requirements: [CAP-01]
commits: [916651f]
---

# Plan 33-01 Summary

Implemented frozen Capability batching, cancellation, produced-Artifact, transport, and inline-Artifact contracts; an explicit exact-binding registry; input/output and Artifact declaration validation; an in-process transport; and a bounded one-request stdio JSON-RPC transport.

The subprocess boundary uses an absolute executable, explicit environment, exact request ID/version/method, strict JSON/result keys, base64 Artifact bytes, bounded stdout/stderr, timeout/cancellation cleanup, and safe protocol/transport errors. Workers can return `CapabilityResult` data only; Event-like fields are rejected.

Verification passed with 17 focused tests, 44 existing contract/port tests, strict mypy, Ruff, and diff checks.
