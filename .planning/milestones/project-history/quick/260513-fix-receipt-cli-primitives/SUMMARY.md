# Fix Receipt CLI Primitives

Date: 2026-05-13

## Outcome

Removed fake receipt identity fields from CLI output and moved the correct
derived-surface metadata into the Action Receipt view primitive.

## Changes

- `ActionReceipt` now carries:
  - `receiptType: "ActionReceipt"`
  - `subject: { subjectType: "Action", actionID }`
  - `derived: true`
- CLI no longer returns or renders `receiptID: none` or `receiptIdentity`.
- CLI renders Action Receipts by `actionID`, not by abstract subject labels.
- CLI exposes unknown-outcome reconciliation through stable facts:
  `previousStatus`, `unknownReason`, and `reconciledAs`.
- `RunCompletionReadinessView` now exposes `passedChecks`, `ready`, and
  `issues` as framework view fields instead of computing readiness language in
  the CLI.
- CLI no longer returns or renders fake explanatory fields such as
  `gateExplanation` or `outcomeExplanation`.
- CLI renders framework field names directly instead of introducing display-only
  vocabulary such as `derivedReceipt`, `capability`, `effect`, `passedCheckIDs`,
  or `eventWatermark`.
- The framework ID generator now emits full SHA-256 digest IDs instead of
  10-character digest IDs.
- The governed coding demo now obtains Run, ModelCall, Action, Wait, delegated
  Run, Check, and inline Artifact IDs from framework ID generation rather than
  hand-written demo identifiers.
- `RunCompletionReadinessView.outputArtifactRequirements` now deduplicates
  Artifact IDs and carries Action capability/action names from Action creation
  facts.

## Verification

- `pnpm demo:governed-coding-run`
- `pnpm test -- tests/core/id-provider.test.ts tests/core/commands.test.ts tests/runtime/action-dispatcher.test.ts tests/runtime/cli-smoke.test.ts tests/examples/governed-coding-run.test.ts tests/runtime/cli-phase5.test.ts tests/views/action-reconciliation.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
