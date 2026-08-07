# Quick Task 260514-lfq: Clarify Event Materialization Semantics

## Goal

Improve `docs/events.md` so Events are framed as canonical immutable
materializations of Engine-evaluated runtime transitions, not generic
event-sourcing records.

## Scope

- Connect Events explicitly to accepted CommandDecisions.
- Explain `command.recorded`.
- Clarify rejected, deferred, and superseded Command effects.
- Clarify approval Wait resolution, unknown/reconciliation, Delegation,
  Authority, Lease, provenance, Bundle, and replay semantics.
- Keep event names and code unchanged.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm test -- tests/docs/docs-links.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
