---
type: quick
slug: control-governance-docs-phase-align
status: planned
created: 2026-05-13
---

# Quick Task: Control Governance Docs And Phase Alignment

## Goal

Integrate the final controlled-runtime governance refinement into live docs and
Phase 8.8 / Phase 9 planning artifacts before Phase 8.8 execution.

## Tasks

1. Add or update live docs so OpenRund is positioned as first-class runtime
   governance for model-proposed side effects, not generic durable execution.
2. Add legality basis, approval-not-legality, explanation-layer, and
   falsifiability guidance to architecture/concepts/README docs.
3. Align Phase 8.8 planning with first-class governance, external-governance
   fragmentation, and command explanation requirements.
4. Align Phase 9 planning with CLI surfaces that answer why a Command was
   accepted, rejected, deferred, or superseded.
5. Run docs/hygiene verification.

## Verification

```bash
pnpm test -- tests/docs/docs-links.test.ts
pnpm hygiene
```
