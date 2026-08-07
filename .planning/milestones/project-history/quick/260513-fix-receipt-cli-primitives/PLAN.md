# Fix Receipt CLI Primitives

Date: 2026-05-13

## Problem

CLI output represented derived Action Receipts as if they had a missing
identity: `receiptID: none` plus `receiptIdentity`. That is the wrong primitive.

## Target

Action Receipt views should expose that they are derived surfaces over an
Action subject. CLI should render those generic fields directly and keep default
human output concise.

## Verification

- `pnpm demo:governed-coding-run`
- `pnpm test -- tests/runtime/cli-smoke.test.ts tests/examples/governed-coding-run.test.ts tests/runtime/cli-phase5.test.ts tests/views/action-reconciliation.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
