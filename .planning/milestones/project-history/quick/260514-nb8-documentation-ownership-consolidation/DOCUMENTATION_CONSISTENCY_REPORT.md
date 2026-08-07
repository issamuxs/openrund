# Documentation Consistency Report

## Ontology Consistency

Status: pass with targeted cleanup.

- Root ontology remains: Run, Command, Event, Message, ModelCall, Action, Wait,
  Delegation, Check, Checkpoint, Annotation, Artifact, Capability, Authority,
  Lease, Bundle, View.
- No reviewed live doc introduces a competing root concept.
- `concepts.md` remains canonical owner of naming and secondary-surface rules.
- The planned `concepts.md` edit reduces control philosophy without changing
  ontology.

## Lifecycle Consistency

Status: pass.

All major docs align to:

```text
ModelCall -> parsed Operation -> Command -> CommandDecision -> Event materialization -> Views / Receipts / Reports
Runtime/API/Timer/Capability/Operator/Recovery -> Command -> CommandDecision -> Event materialization -> Views / Receipts / Reports
```

The docs use both "Events" and "Event materialization"; this is acceptable:
`events.md` now owns the explanation that Events materialize Engine-evaluated
runtime transitions.

## Legality Consistency

Status: pass.

- `control.md` owns runtime legality semantics.
- `architecture.md` owns implementation authority flow.
- `events.md` owns canonical materialization facts.
- `api.md` correctly treats RuntimeEngine APIs as attempted mutation entry
  points.
- `quickstart.md` now teaches the governed mutation loop early.

## UI / CLI Consistency

Status: pass with current scope.

- CLI is consistently described as rendering or submitting through runtime APIs.
- CLI does not decide legality or append authoritative Events.
- UI is not yet a shipped public surface in the docs. The current docs do not
  introduce workflow-builder, chatbot, DAG, task, or job abstractions.
- Future UI docs should mirror CLI semantics: operator surface over ontology,
  not authority boundary.

## Bundle Semantics Consistency

Status: pass after planned storage cleanup.

- `bundles.md` owns Bundle verification, replay, import, resume assessment, and
  non-authority semantics.
- `quickstart.md` keeps only first-contact Bundle framing.
- `storage.md` should keep default path/custody details and point to
  `bundles.md` for semantics.

## Provider / Worker / Storage Boundary Consistency

Status: pass.

- `providers.md` owns provider non-authority.
- `capabilities.md` owns worker non-authority and CapabilityResult semantics.
- `storage.md` owns ordering/content persistence and explicitly does not decide
  legality.

## Overall Verdict

The docs now express one coherent runtime model. The remaining consolidation is
not a conceptual rewrite; it is ownership sharpening in `docs/README.md`,
`docs/concepts.md`, and `docs/storage.md`.
