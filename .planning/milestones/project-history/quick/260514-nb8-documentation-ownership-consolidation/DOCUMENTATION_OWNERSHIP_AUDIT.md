# Documentation Ownership Audit

## Canonical Ownership

| Document | Canonical ownership | Current status |
|---|---|---|
| `README.md` | Public positioning, wedge, core invariants, demo entry point. | Healthy. Intentionally repeats the core lifecycle and invariants. |
| `docs/README.md` | Documentation index and reading order. | Stale. It repeats old top-level positioning and mixed decision categories. |
| `docs/concepts.md` | Ontology, root concepts, attached governance semantics, secondary surfaces, naming rules. | Mostly healthy, but the Governance Surfaces section repeats `control.md` philosophy. |
| `docs/control.md` | Runtime legality semantics, governance model, Authority/Wait/Check/reconciliation/completion, falsifiability. | Canonical owner for legality and first-class governance. Keep the detailed model here. |
| `docs/architecture.md` | Runtime flow, Engine authority, package map, implementation responsibility. | Healthy. Some overlap with `control.md` is acceptable because it is implementation-facing. |
| `docs/api.md` | Public TypeScript and CLI surfaces. | Healthy. Should stay reference-shaped, not philosophical. |
| `docs/events.md` | Canonical immutable runtime facts, envelope, grammar, catalog, event rules. | Healthy after materialization semantics update. |
| `docs/capabilities.md` | Governed execution interfaces, worker boundary, CapabilityResult, effects/evidence. | Healthy. It should keep execution-boundary semantics but avoid broad control philosophy. |
| `docs/delegation.md` | Governed sub-work, Delegation contracts, Authority attenuation, join semantics. | Healthy after legality pass. |
| `docs/bundles.md` | Portable replayable governed runtime history, verification, import/replay/resume. | Healthy. It is canonical owner for Bundle philosophy. |
| `docs/quickstart.md` | First-contact smallest governed mutation runtime loop. | Healthy after recent update. |
| `docs/providers.md` | Provider adapters as non-authority transport/parsing boundary. | Healthy after provider-boundary pass. |
| `docs/storage.md` | Durable Event/Artifact/Lease storage, runtime home, workspace roots. | Mostly healthy, but its Bundle section repeats resume semantics owned by `docs/bundles.md`. |

## Healthy Overlap

The following repetition is intentional and should remain:

- Model output is not authority.
- Engine-owned authority over authoritative Event append.
- `Operation -> Command -> CommandDecision -> Events`.
- Approval is not legality.
- Views are derived and non-authoritative.
- Completion is terminal legality.
- Unknown outcomes and reconciliation are runtime semantics.
- Delegated Authority attenuation.

These are structural reinforcement, not accidental duplication.

## Unnecessary Duplication

| Theme | Current spread | Ownership decision | Refactor |
|---|---|---|---|
| First-class governance manifesto text | `README.md`, `docs/concepts.md`, `docs/control.md` | `docs/control.md` owns full explanation. `README.md` keeps short positioning. `concepts.md` should name surfaces only. | Shorten `docs/concepts.md` Governance Surfaces opening and point to `control.md`. |
| Bundle replay/import/resume philosophy | `docs/bundles.md`, `docs/storage.md`, `docs/quickstart.md` | `docs/bundles.md` owns details. `quickstart.md` keeps onboarding summary. `storage.md` should only mention storage/default path. | Shorten `docs/storage.md` Bundle section. |
| Provider non-authority philosophy | `docs/providers.md`, `docs/architecture.md`, `docs/concepts.md` | `docs/providers.md` owns provider boundary. Architecture/concepts keep concise rules. | No change needed after recent provider pass. |
| Legality basis lists | `docs/control.md`, `docs/architecture.md` | `docs/control.md` owns conceptual legality. `architecture.md` owns implementation basis. | Keep both; overlap is useful and not essay-like. |
| Replay semantics | `docs/events.md`, `docs/bundles.md`, `docs/storage.md`, `docs/quickstart.md` | Each has a different perspective. Only `storage.md` overreaches into Bundle resume details. | Shorten `storage.md`. |

## Findings

- No current doc introduces a competing lifecycle model.
- No current doc introduces a new root ontology concept.
- `docs/README.md` is stale relative to the current governed-mutation framing.
- `docs/concepts.md` should be more clearly ontology-owned and less control-owned.
- `docs/storage.md` should stop carrying Bundle resume semantics beyond storage path/custody references.
