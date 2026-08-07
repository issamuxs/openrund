---
quick_id: 260512-ufd
slug: finalize-ontology-migration-guide-for-re
status: completed
created: 2026-05-12
---

# Quick Plan: Finalize Ontology Migration Guide

## Objective

Apply the final review corrections so `docs/ontology-migration.md` is the
authoritative refactor-control document for the code migration.

## Tasks

1. Split model-originated and non-model mutation paths in the guide opening.
2. Clarify ModelCall lifecycle handling, Command decision semantics, payload
   normalization failures, and `.orun` Command metadata behavior.
3. Replace the single-fact normalized event shape with raw event plus
   `facts[]`.
4. Add operation kind classes, expanded ID mappings, static-check nuance,
   documentation synchronization gate, and missing tests/checks.
5. Align concepts/events docs where they would otherwise contradict the guide.
6. Run docs/public API tests, typecheck, hygiene, and focused stale-term scans.

## Non-Goals

- Do not rename runtime code or persisted event literals in this task.
- Do not start the code migration itself.
- Do not stage unrelated dirty worktree changes.
