---
phase: 34-providers-and-durable-run-loop
plan: "01"
status: complete
completed: 2026-08-06
requirements: [PROV-01]
commits: [0970b02]
---

# Plan 34-01 Summary

Added frozen provider-neutral tool declarations and call values, strict object-only tool argument parsing, qualified Capability/action normalization, deterministic Action fallback identities, and shared text/single-call/batch proposal construction. Provider parse, response, and tool-argument exceptions expose stable safe fields without raw bodies.

Verification passed with 16 normalization tests plus strict mypy and Ruff.
