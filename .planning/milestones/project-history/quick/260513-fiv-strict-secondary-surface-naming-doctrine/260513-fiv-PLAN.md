---
status: in_progress
created: 2026-05-13
task: Strict secondary-surface naming doctrine and production renaming pass for Phase 8.75
---

# Quick Task 260513-fiv: Strict Secondary Surface Naming

## Goal

Make OpenRund's secondary surfaces obey the stricter ontology direction:
canonical bare nouns stay limited to the locked ontology, derived surfaces use
approved suffixes, and production code avoids stale or ambiguous naming.

## Locked Doctrine

- Canonical bare nouns: Run, Command, Event, Message, ModelCall, Action, Wait,
  Delegation, Check, Checkpoint, Annotation, Artifact, Capability, Authority,
  Lease, Bundle, View.
- Approved secondary suffixes: View, Report, Receipt, Summary, Assessment,
  Manifest, Snapshot, IndexView, Milestone, Entry, Issue.
- Banned exported production semantic suffixes: State, Facts, Boundary,
  Blocker, Projection, Record.
- Private non-exported implementation state names are allowed when not
  ontology-facing, such as ReducerState or ParserState.
- Restricted semantic vocabulary: Child. Prefer DelegatedRun,
  DelegationHandoff, or JoinWait.
- Helper rule: reduce* folds Events into a View; build* assembles from
  already-derived inputs.

## Tasks

### 1. Document and enforce the doctrine

Files:
- `docs/secondary-surfaces.md`
- `docs/README.md`
- `scripts/check-hygiene.mjs`
- new static-check script if needed

Action:
- Add a concise normative secondary-surface naming document.
- Wire a production naming scan into hygiene.

Verify:
- `pnpm hygiene` runs the naming scan.

Done:
- Naming doctrine exists and stale exported semantic names fail hygiene.

### 2. Rename production secondary surfaces

Files:
- `packages/views/src/*`
- `packages/runtime/src/*`
- `packages/cli/src/index.ts`
- dependent tests and examples

Action:
- Replace `project*` reducers with `reduce*`.
- Replace State/Facts/Boundary/Blocker/Record/Projection semantic names with
  approved View/Entry/Issue names.
- Rename CLI surfaces from old nouns to canonical nouns.
- Remove compatibility aliases from production exports.

Verify:
- `pnpm typecheck`
- targeted `rg` scan for banned names.

Done:
- Production code no longer exports stale secondary-surface names.

### 3. Update tests, examples, and docs

Files:
- `tests/**`
- `examples/**`
- `docs/**`

Action:
- Update imports, expected outputs, README snippets, and public docs to use the
  canonical secondary-surface naming scheme.

Verify:
- `pnpm test`
- `pnpm hygiene`

Done:
- Tests and examples no longer teach stale names.
