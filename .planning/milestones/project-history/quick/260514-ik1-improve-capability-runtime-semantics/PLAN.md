# Quick Task 260514-ik1: Improve Capability Runtime Semantics

## Goal

Tighten `docs/capabilities.md` so Capability execution matches the current
Command/CommandDecision authority model and explicitly covers unknown outcomes,
reconciliation, effects, evidence, and completion legality.

## Scope

- Align the Capability lifecycle with `Command -> CommandDecision -> Events`.
- Clarify that Actions are governed lifecycle semantics, not raw invocations.
- Strengthen worker non-authority language.
- Explain `CapabilityAccessMode`, `CapabilityReliability`, effects, evidence,
  and `CapabilityResult` without changing public APIs.
- Clarify unknown outcome, reconciliation, and completion legality semantics.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm test -- tests/docs/docs-links.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
