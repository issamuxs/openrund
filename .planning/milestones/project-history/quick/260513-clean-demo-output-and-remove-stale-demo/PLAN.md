---
status: in_progress
---

# Clean Demo Output And Remove Stale Demo Residue

## Goal

Fix Phase 10 public demo quality by removing stale previous-demo surfaces
and making `pnpm demo:governed-coding-run` print a readable walkthrough instead
of raw JSON with escaped multiline strings.

## Tasks

- Replace default governed-coding demo output with concise human-readable
  sections.
- Keep machine-readable JSON behind an explicit `--json` flag.
- Remove the obsolete previous demo and its tests from the public repository
  surface.
- Update public API/docs guard tests that still reference the obsolete demo.
- Run typecheck, tests, hygiene, package check, and demo command.
