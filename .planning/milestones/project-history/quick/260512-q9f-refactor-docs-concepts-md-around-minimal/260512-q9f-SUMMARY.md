---
quick_id: 260512-q9f
slug: refactor-docs-concepts-md-around-minimal
status: complete
completed: 2026-05-12
implementation_commit: 955e598
---

# Quick Task Summary: Minimal Core Ontology Refactor

## Outcome

Completed. `docs/concepts.md` now defines a small semantic ontology centered
on Run, Command, Event, Message, ModelCall, Action, Wait, Delegation, Check,
Checkpoint, Annotation, Artifact, Capability, Authority, Lease, Bundle, and
View.

## Key Changes

- Replaced the implementation-surface taxonomy with supreme ontology rules and
  a minimal concept graph.
- Made Command the semantic replacement for Transition Request.
- Made ModelCall the semantic replacement for Model Request.
- Collapsed Approval, Interaction, Timer, child joins, and other blockers into
  Wait with a `kind` discriminator.
- Collapsed Input and Output Message into Message with direction/source/role.
- Recast Child Session as Run with `parentRunID`, connected by Delegation and
  joined through Wait.
- Demoted effects, evidence, mutation, outcome, contracts, policy rules, and
  content to value types.
- Added clean event grammar, clean target event set, boundary rules, derived
  View rules, refactor strategy, and an admission test for new concepts.

## Verification

- `pnpm test -- tests/docs/docs-links.test.ts tests/public-api/exports.test.ts`
  passed.
- `pnpm hygiene` passed.
- `pnpm typecheck` passed.
- Exact stale-token guard returned no matches for removed request/delegation
  terms in `docs/concepts.md`.
