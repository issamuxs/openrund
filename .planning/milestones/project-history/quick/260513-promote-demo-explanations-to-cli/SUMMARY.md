# Promote Demo Explanations To CLI

Date: 2026-05-13

## Outcome

The semantic explanations previously embedded in the governed coding demo output
now live in CLI/framework rendering surfaces.

## Changes

- `actions receipt` now renders:
  - `receiptID: none`
  - `receiptIdentity: derived from actionID; Receipt is not a canonical entity`
  - outcome explanation for terminal, unknown, and reconciled Actions
- `waits show --kind approval` now renders `resolvedBy`.
- `runs readiness` now renders a generic completion gate explanation.
- Removed the inspection-guide helper after review. It was unnecessary MVP
  complexity; the demo now prints only actual CLI-rendered command outputs.
- Updated the governed coding demo to use the CLI inspection guide and remove
  demo-local explanations for Receipt identity, unknown outcomes, Checks, and
  approval actors.
- Removed the demo-owned compact summary. The demo entrypoint now prints only
  CLI-rendered outputs: `inspect`, `commands explain`, `waits show`,
  `actions receipt`, `runs readiness`, `orun verify`, and the CLI inspection
  guide.
- Tightened CLI rendering so Action Receipts do not dump embedded Markdown/JSON
  by default and readiness shows a requirement count instead of raw artifact
  internals.
- Updated the demo regression test to assert these explanations come through
  CLI-rendered output.

## Verification

- `pnpm demo:governed-coding-run`
- `pnpm test -- tests/examples/governed-coding-run.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
