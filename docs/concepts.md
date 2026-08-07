# Concepts

This page defines OpenRund's vocabulary. [Control](./control.md) defines how
mutations are evaluated; contract pages define each concept's detailed schema
and lifecycle.

## Core vocabulary

| Concept | Meaning |
|---|---|
| **Run** | Root aggregate for one durable execution. |
| **Command** | Audited attempt to mutate a Run. |
| **Event** | Immutable fact in a Run's ordered log. |
| **Message** | Information exchanged between a participant and a Run. |
| **ModelCall** | One outbound provider request and its outcome. |
| **Action** | One governed invocation of a Capability. |
| **Wait** | Condition that blocks Run advancement. |
| **Delegation** | Contract-bound relationship between a parent and delegated Run. |
| **Check** | Recorded semantic validation. |
| **Checkpoint** | Named position or summary in Event history. |
| **Annotation** | Observational note recorded in history. |
| **Artifact** | Immutable content referenced by ID. |
| **Capability** | Executable interface available to the runtime. |
| **Authority** | Constrained permission for a Run to use a Capability or policy. |
| **Lease** | Operational execution-ownership token. |
| **Bundle** | Portable Run history, Artifacts, and derived evidence. |
| **View** | Rebuildable projection of Events and Artifacts. |

Bare forms of these nouns are reserved for canonical runtime concepts.

## Related value types

Some important values belong to a core concept rather than forming independent
runtime entities:

- An **Operation** is typed proposed intent carried by a Command.
- A **CommandDecision** classifies one Command as accepted, rejected, deferred,
  or superseded.
- A **CommandDecisionTraceEntry** explains one step in legality evaluation.
- **Effects** describe mutations or observations claimed by a Capability.
- **Evidence** supports a claim; it does not authorize the claim.
- **Policies** and **contracts** constrain legality.
- **Receipts**, **Reports**, **Assessments**, and **Manifests** explain or
  transport canonical history.

These values do not acquire independent authority by being persisted or
rendered.

## Wait kinds

`Wait` is the only canonical blocker. Its `kind` identifies the missing
condition:

| Kind | Missing condition |
|---|---|
| `approval` | Required authorization |
| `interaction` | Participant input |
| `timer` | A time condition |
| `join` | Delegated Run criteria |
| `reconciliation` | Certainty about an external outcome |

External signals and retry metadata belong in a Wait payload. Exhausted budgets,
invalid operations, and terminal failures belong in legality or lifecycle
semantics, not new blocker types.

## Derived names

Derived or explanatory types should state what they are. Preferred suffixes
include `View`, `Report`, `Receipt`, `Summary`, `Assessment`, `Manifest`,
`Snapshot`, `Index`, `Entry`, and `Issue`.

Examples include `RunStatusView`, `ActionReceipt`, `BundleManifest`, and
`ResumeAssessmentIssue`.

Avoid exported names such as `State`, `Facts`, `Boundary`, `Blocker`,
`Projection`, or `Record` when they could be mistaken for canonical runtime
truth.

## Adding a concept

Before adding a root noun, ask:

1. Does it need stable identity?
2. Does it have lifecycle Events?
3. Do other concepts reference it?
4. Is it distinct from the existing vocabulary?
5. Is it canonical, or is it a value type or derived surface?

If the answers do not justify a root concept, use a payload field, value type,
helper, or explicitly derived type.
