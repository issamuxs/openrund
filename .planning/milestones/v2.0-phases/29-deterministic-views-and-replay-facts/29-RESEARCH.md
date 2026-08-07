---
phase: 29-deterministic-views-and-replay-facts
status: complete
created: 2026-08-05
sources: [normative-docs, frozen-corpus, phase-28-python-contracts]
---

# Phase 29 Research — Deterministic Views and Replay Facts

## Recommendation

Build focused pure reducers over one validated `KnownHistory`, then compose them through `rebuild_views`. Represent all outputs with final frozen dataclasses, tuples, and read-only ordered mappings. Return an explicit incomplete replay result whenever the declared source boundary cannot be proven; never return a partial bundle carrying the appearance of current truth.

## Normative Constraints

- Events and Artifacts are canonical facts; Views are disposable derived read models.
- A View is usable only from complete source Events at a known watermark.
- Views explain or supply replay facts; only the Engine evaluates Commands and decides legality.
- Event positions are one-based and contiguous per Run; an empty history has watermark zero.
- Waiting derives from unresolved Wait facts across approval, interaction, timer, join, and reconciliation kinds.
- Action unknown outcomes remain unresolved until an explicit reconciliation fact.
- Checkpoints are append-only summaries; corrections mark earlier checkpoints obsolete rather than rewriting them.
- Receipts and Reports explain facts and may reference Artifacts; they do not create state.

## Frozen Compatibility Inventory

The authenticated corpus contains 71 View cases:

| Surface | Cases |
|---|---:|
| Run status/readiness | 13 |
| Timeline | 3 |
| Action status | 9 |
| Action reconciliation | 4 |
| Action receipts | 9 |
| Artifact index | 3 |
| Checkpoints | 4 |
| Delegation | 14 |
| Wait queues | 12 |

Each evidence file contains the complete focused Event stream, declared watermark, and expected result. The Phase 29 harness must authenticate each file before decode, require an exact 71-row bijection, and compare typed reducer results without rewriting any fixture.

## Replay Boundary

Validate before reduction:

1. `watermark` is explicitly supplied as a non-boolean non-negative integer.
2. Every input is a Phase 28 `RuntimeEvent`.
3. Non-empty history has exactly one `run_id`.
4. Positions are exactly `1..watermark` in input order, with no gaps, duplicates, regressions, or events past the declaration.
5. Empty history is complete only at watermark zero.
6. Artifact inputs are semantic Artifact values with unique identities; conflicting duplicates produce an incomplete issue.

Return stable issues such as `watermark_unknown`, `watermark_invalid`, `history_incomplete`, `history_out_of_order`, `history_mixed_run`, and `artifact_conflict`. Issue detail may include safe numeric positions or typed IDs but never raw content.

## Semantic Model

- `KnownHistory`: private validated event/artifact tuple plus watermark and optional Run ID.
- `CompleteViewReplay`: declared watermark, optional Run ID, and one `RunViewBundle`.
- `IncompleteViewReplay`: declared watermark if valid, observed safe positions, and ordered unique `ReplayIssue` values; contains no bundle.
- `RunViewBundle`: run status/readiness, timeline, Action status/reconciliation/receipts, unified Wait queues, Artifact index, Checkpoints, Delegation, and Reports.
- Keyed surfaces use insertion-ordered immutable mappings. Histories and queue entries use tuples.

## Reducer Notes

### Timeline, Artifacts, Checkpoints, Reports

- Timeline preserves Event order and uses explicit Event-class summaries with an optional summary when the event carries no defined presentation fact.
- Artifact index combines `artifact.created`/`artifact.unavailable` facts with supplied Artifact availability without reading a store.
- Checkpoint corrections mark referenced prior entries obsolete; both complete and active ordered tuples remain visible.
- Reports derive from `check.recorded` report content and Artifact evidence, retaining Event/Check identity and watermark provenance.

### Actions

- Status moves from requested to started/terminal/unknown/reconciled only for a known Action ID.
- Reconciliation is keyed by the original unknown Event ID, never merely Action ID, so multiple uncertainty episodes remain distinguishable.
- Receipts retain request/start/terminal/reconciliation Event IDs, timestamps, inputs/results/errors/evidence, and outcome history without invoking a Capability.

### Waits

- One internal ordered lifecycle covers all five Wait kinds.
- Resolution, cancellation, and expiry remove a matching pending item exactly once in the derived state; malformed histories remain observable through replay issues rather than reducer mutation.
- Approval, interaction, and timer projections preserve the frozen v1 surface; join and reconciliation queues are additionally exposed as typed Python View facts.

### Delegation

- Delegated runs retain creation contract/handoff identity and derived establishing/running/terminal state.
- Join Views derive all/any/quorum satisfaction from declared targets and child terminal Events; they do not advance a parent or append completion facts.
- Ordering follows first appearance in Event history.

### Run Status and Readiness

- Lifecycle state follows canonical Run facts; unresolved Waits derive `waiting` only while non-terminal.
- Readiness reports ordered blockers for pending Waits, missing required Artifacts, unresolved Action outcomes, and unsatisfied semantic Checks.
- `ready` is a derived fact, never permission to complete. Phase 31 consumes the underlying facts and records its own decision.

## Verification Strategy

- Unit tests per reducer with constructor/runtime edge cases.
- Exact corpus tests for all 71 authenticated cases.
- Replay boundary tests for absent/invalid watermark, gaps, duplicates, reorder, mixed Runs, events beyond watermark, and Artifact conflicts.
- Determinism tests across fresh processes/instances and unrelated cache state.
- Prefix tests: each prefix rebuilt at its exact watermark equals reduction of the same prefix through the aggregate entry point.
- Static dependency/import fence and method-surface tests prove Views cannot append Events or decide legality.
- Full pytest, strict mypy, Ruff, lock, build, and installed typing remain green.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Partial history presented as current | Typed incomplete result with no View bundle. |
| Mutable reducer results drift after return | Final dataclasses, tuples, mapping proxies, and copied inputs. |
| Reducer order depends on hash/set iteration | Preserve Event order and insertion-ordered maps; sort only by explicit semantic keys where required. |
| Compatibility projection contaminates semantic API | Keep raw JSON comparison projection test-only or inside codec internals. |
| Readiness becomes a second legality engine | Emit blocker facts and `ready` as explanatory data; forbid submit/append/authorize methods. |
| UI workflow accidentally triggered by operator surfaces | No UI artifacts or UI phase; CLI rendering remains Phase 36. |
