---
quick_id: 260806-mdx
status: complete
completed: 2026-08-06
commit: 3395ad9
---

# Quick Task 260806-mdx Summary

Removed every demo-owned runtime substitute. The governed-coding demonstration
now uses `LocalAssemblyConfig` production defaults for its system clock, UUID
factories, lease tokens, and process timing. It also registers the process
built-in through the assembly's normal `process_bindings` path rather than
constructing a special Capability registration.

All Run, Action, Command, Event, Wait, Delegation, Check, Artifact, Authority,
Lease, Message, and related identities now originate from the production
assembly. The demo still configures only the explicit workspace mount, Python
executable binding, and local Git identity required by the workflow.

Tests now require fresh `run_<32 hex>` identities, different identities and
Bundle commitments across executions, complete 71-Event behavior, and the
absence of demo-defined classes or clock/ID/Capability overrides. Wheel and
source-distribution console tests also enforce the production Run ID shape.

Documentation now describes the demo as an offline production-assembly proof,
not a deterministic fixture.

## Verification

- Full pytest: 973 passed, 3 opt-in live-provider checks skipped.
- Installed wheel/source demo tests: 6 passed.
- Focused demo and documentation tests: 5 passed before the final assembly
  registration refinement; focused demo tests: 2 passed afterward.
- Strict mypy: 224 source/test/example files.
- Ruff lint and format: 225 files.
- `git diff --check`: passed.
