---
type: quick
slug: authority-loop-decision-boundary
status: planned
created: 2026-05-13
---

# Quick Task: Authority Loop Decision Boundary

## Goal

Make the architecture authority loop explicit enough for implementation:
separate model and non-model paths, name Legality evaluation, expose
CommandDecision outcomes, and keep explanation surfaces derived.

## Tasks

1. Replace the compressed `input/model/operator/capability/timer -> Command`
   loop in `docs/architecture.md`.
2. Add decision outcome semantics for accepted, rejected, deferred, and
   superseded.
3. Clarify that Capability workers return data to the Engine and do not author
   Commands or Events directly.
4. Run docs and hygiene checks.

## Verification

```bash
pnpm test -- tests/docs/docs-links.test.ts
pnpm hygiene
```
