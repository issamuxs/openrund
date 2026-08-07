# Promote Demo Explanations To CLI

Date: 2026-05-13

## Problem

The governed coding demo renderer was explaining framework semantics itself:
Receipt identity, approval resolver, unknown outcome meaning, completion Check
meaning, and `OPENRUND_HOME` guidance.

That violates the intended boundary. The demo should orchestrate the workflow
and fixture failures; framework/CLI inspection surfaces should explain runtime
facts.

## Target

- CLI Action Receipt output explains Receipt identity.
- CLI approval Wait output shows resolver actor.
- CLI Action Receipt output explains unknown/reconciled outcomes.
- CLI readiness output explains completion gate semantics.
- CLI provides a shared inspection guide renderer with one `OPENRUND_HOME`.
- Demo output consumes CLI/framework renderers instead of embedding semantic prose.

## Verification

- `pnpm demo:governed-coding-run`
- `pnpm test -- tests/examples/governed-coding-run.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
