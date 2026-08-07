# Strengthen Governed Coding Demo Proof Surfaces

Date: 2026-05-13

## Goal

Make the governed coding demo transcript defensible for external review without
adding CLI-only ontology or hiding runtime behavior behind presentation prose.

## Scope

- Persist Command wait/resume facts in framework Events rather than deriving
  them in CLI.
- Add ActionReceipt fields for reconciliation evidence and command linkage.
- Add approval input validation proof to approval Wait/resume surfaces.
- Expand RunCompletionReadinessView to distinguish semantic Checks, demo
  assertions, and output Artifact requirement satisfaction.
- Expand BundleVerificationResult with structured verification checks.
- Render these framework/view fields directly in CLI.
- Update tests and run targeted verification plus hygiene/package checks.

## Constraints

- CLI must not generate runtime facts or introduce new ontology vocabulary.
- All displayed IDs must be framework-generated and rendered in full.
- Demo code may script the scenario, but explanatory surfaces must come from
  runtime/framework/CLI commands.
