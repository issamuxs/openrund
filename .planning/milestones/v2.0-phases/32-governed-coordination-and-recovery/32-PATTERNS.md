# Phase 32: Governed Coordination and Recovery — Patterns

## Closest Existing Analogs

| New responsibility | Existing Python analog | Pattern to preserve |
|---|---|---|
| Wait legality | `src/openrund/views/_waits.py` | Pending/terminal state is replayed by `(WaitKind, WaitId)` and never inferred from caller intent |
| Action reconciliation | `src/openrund/views/_actions.py` | Unknown and reconciled facts are additive, immutable, and causally linked |
| Durable Authority | `src/openrund/views/_run_status.py` | Current grants/rules derive from ordered grant/revoke Events; history remains inspectable |
| Completion governance | `src/openrund/views/_run_status.py` | Views enumerate blockers; Engine alone decides legality |
| Delegation topology | `src/openrund/views/_delegation.py` | Parent contracts, establishment facts, terminal handoffs, and join satisfaction remain separate |
| Multi-Run commit | `src/openrund/ports/events.py`, `src/openrund/storage/_events.py` | Preflight all expected positions and commit every Run batch atomically |
| Command authority | `src/openrund/engine/_engine.py` | Complete replay, durable duplicate recovery, pure evaluation, ordered evidence, bounded conflict retry |
| Explicit Event mapping | `src/openrund/engine/_events.py` | One typed operation branch maps to exact payload classes without reflection |

## Dependency Direction

```text
contracts + ports + codec + views
              ↑
            engine
              ↑
    later capability runtime / assembly / CLI
```

Coordination and governance remain Engine internals. Views do not resolve Waits, apply approval, reconcile Actions, or advance joins. Storage does not evaluate Authority. Capability code cannot append Events.

## Proposed File Map

| Path | Responsibility |
|---|---|
| `src/openrund/contracts/commands.py` | Typed Wait, approval, recovery, Check, Annotation, Delegation, and Authority operations |
| `src/openrund/engine/_model.py` | Coordination ID factories, atomic store seam, and trusted governance context |
| `src/openrund/engine/_governance.py` | Pure Capability metadata, schema, Authority, policy, scope, budget, tenant, and security evaluation |
| `src/openrund/engine/_coordination.py` | Wait lookup/end rules, approval snapshots/revalidation, Checks, and reconciliation intents |
| `src/openrund/engine/_delegation.py` | Delegation contract validation, atomic parent/child batches, terminal handoffs, joins, and cancellation policy |
| `src/openrund/engine/_legality.py` | Exhaustive operation dispatch and hard-invariant decisions |
| `src/openrund/engine/_engine.py` | Single-Run/deferred/multi-Run materialization and conflict-safe persistence |
| `tests/engine/` | Coordination, governance, recovery, Delegation, compatibility, and hygiene gates |

## Required Patterns

- Every Wait terminal Command proves a matching currently pending Wait of the exact kind.
- Timer firing/expiry compares canonical injected timestamps; no wall clock is read outside `Clock`.
- Deferred Action evidence links one decision Wait record to one approval `wait.created` Event in the same append.
- Approval resolution stores any revised input, but resumption separately re-evaluates current Capability metadata, schema, writable scope, Authority, policy, budgets, lineage, tenant, and security facts.
- Rejected hard invariants never create approval Waits.
- Action uncertainty and reconciliation preserve original unknown Event identity and require evidence for a claimed outcome.
- Delegation creation preallocates all parent/child IDs, validates both expected positions, and uses `append_many` once.
- Delegated child terminal state becomes a parent fact only through an explicit parent Command; join satisfaction remains explanatory until a resolution Command commits.
- Checkpoints, Annotations, Reports, and Views remain explanatory and never confer Authority.

## Prohibited Patterns

- Separate approval, timer, recovery, or Delegation append methods outside `RuntimeEngine.submit`.
- Treating approval, Capability registration, a Lease, a View, or a Check as permission by itself.
- Generic arbitrary policy execution, dynamic code evaluation, or permissive schema fallback.
- Resolving a Wait from an ID without checking its kind, request, and terminal history.
- Retrying unknown consequential Actions instead of recording and reconciling uncertainty.
- Parent state advancement as an automatic side effect of child completion.
- Best-effort parent/child Delegation creation when an atomic store is available.
- Graphical UI artifacts or UI workflow gates.

## Test Map

- `test_coordination_contracts.py`: all operation values, governance context, and dependency factories.
- `test_wait_lifecycle.py`: open/resolve/cancel/expire exactly once across five Wait kinds.
- `test_governance.py`: Capability metadata, schema, Authority, policy, scope, budget, lineage, tenant, and security traces.
- `test_approval.py`: legal defer, illegal rejection, resolution, revised input, stale Authority, and resumption.
- `test_recovery.py`: unknown outcome, reconciliation evidence, matching Wait, and terminal safeguards.
- `test_checks.py`: semantic/diagnostic Checks, Checkpoints, Annotations, and non-authority fences.
- `test_delegation.py`: atomic establishment, child bootstrap, bounded Authority, budgets, schema, and nesting.
- `test_delegation_lifecycle.py`: terminal handoff, cancellation policy, late handoff, and all/any/quorum joins.
- `test_coordination_compatibility.py`: explicit authenticated Phase 32 Event allowlist.
- `test_coordination_hygiene.py`: sole authority, no effect execution, no UI, and installed typing.
