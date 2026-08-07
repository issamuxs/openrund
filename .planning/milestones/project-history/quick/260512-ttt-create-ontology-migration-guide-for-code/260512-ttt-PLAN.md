---
quick_id: 260512-ttt
slug: create-ontology-migration-guide-for-code
status: completed
created: 2026-05-12
---

# Quick Plan: Create Ontology Migration Guide

## Objective

Add an explicit migration-control document that turns the locked ontology into
mechanical guidance for refactoring the codebase from current compatibility
names to canonical concepts.

## Tasks

1. Create `docs/ontology-migration.md` with layer-by-layer migration rules,
   current-to-target mappings, sequencing, compatibility policy, and tests.
2. Link the migration guide from `docs/README.md` and relevant normative docs.
3. Verify links and stale terminology scans.
4. Run docs/public API tests, typecheck, and hygiene.

## Non-Goals

- Do not rename code, APIs, event literals, or tests in this task.
- Do not change the locked ontology in `docs/concepts.md` except for links if
  needed.
- Do not stage unrelated dirty worktree changes.
