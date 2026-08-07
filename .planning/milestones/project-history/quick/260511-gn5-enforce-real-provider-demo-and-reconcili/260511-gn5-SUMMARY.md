# Quick Task 260511-gn5 Summary

**Completed:** 2026-05-11
**Status:** Complete

## Outcome

The research-brief developer demo now requires a real model provider, while the
deterministic fixture path remains available only through tests/direct runner
injection.

- `pnpm demo:research-brief` resolves OpenAI, Anthropic, or a local
OpenAI-compatible endpoint before runtime state is created.
- `pnpm demo:research-brief:auto` automates approval and reconciliation only; it
still requires a real provider.
- The exported fixture runner still supports deterministic tests without
network access unless a model adapter is explicitly supplied.
- Root package dependencies now include the provider workspace packages used by
the example.
- Reconciliation docs now distinguish human from operator and state the default
as manual operator-mediated human evidence.
- CI/test runtime isolation is documented as explicit temporary-directory
injection, not environment selection.

## Reconciliation Semantics

A human is the person making the judgment about external-world evidence. An
operator is the authorized runtime role or channel that submits that judgment.
In the CLI demo, the developer is both.

The runtime records unknown outcomes, creates the blocker, validates the
reconciliation request, records the canonical reconciled event, and gates
completion. It does not invent evidence. Automated reconciliation is explicit
and appropriate for CI, deterministic tests, or an authorized deterministic
reconciler service.

