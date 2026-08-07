# Patch Plan

**Analysis date:** 2026-05-14  
**Status:** Phase 18 implemented

## Scope Rule

Semantic violations are corrected together with related naming and documentation. Naming and docs are not cosmetic when they define the public ontology and authority model.

## Implemented Patch Set

| Priority | Problem | Files changed | Semantic effect | Tests updated | Risk |
|---:|---|---|---|---|---|
| 1 | Non-model mutation paths appended Events without visible Commands. | `packages/runtime/src/runtime-engine.ts` | Runtime interaction, timer, checkpoint, unknown-outcome, and delegation handoff/cancellation paths now prepend `command.recorded` and link result Event IDs/types. | `tests/runtime/action-reconciliation.test.ts`, `tests/runtime/timer-waits.test.ts`, `tests/runtime/interaction-waits.test.ts`, `tests/runtime/checkpoint.test.ts` | Event counts/order changed by one Command Event on patched paths. |
| 1 | Check recording could bypass Command evaluation through `runtime.append(...recordCheckResult(...))`. | `packages/runtime/src/runtime-engine.ts`, `examples/governed-coding-run/run.ts` | Checks that affect completion can enter history through `RuntimeEngine.recordCheckResult(...)`, producing a visible `record_check_result` Command. The flagship demo uses the Command-owned path. | `tests/examples/governed-coding-run.test.ts` covered by targeted run. | Some fixture-only tests still use raw append for setup and remain Phase 19 cleanup targets. |
| 1 | Public `RuntimeEngine.append` was promoted as a normal API. | `docs/api.md` | Raw append is documented as a low-level bootstrap/fixture/storage-adjacent escape hatch, not a provider/worker/CLI/example mutation path. | Build/docs compile via `pnpm build`; guard hardening remains Phase 19. | Raw append still exists for fixtures and low-level use. |
| 1 | Terminal fallback could produce terminal Run lifecycle Events outside guarded paths. | `packages/runtime/src/runtime-engine.ts` | Fallback `complete_run` and `fail_run` no longer emit direct terminal Events; completion must pass through guarded completion evaluation. | `tests/examples/governed-coding-run.test.ts`, targeted runtime tests. | Fallback still has older unsupported-operation rejection shape; Phase 19 can tighten command decisions. |
| 1 | Public ontology names used banned nouns. | `packages/core/src/model.ts`, `packages/core/src/events.ts`, `packages/core/src/storage.ts`, `packages/capabilities/src/definition.ts`, `packages/runtime/src/*`, `packages/views/src/*`, `packages/storage-sqlite/src/*`, tests | Public semantic names now use `CommandDecisionEntry`, `EffectEntry`, `LeaseEntry`, `ArtifactEntry`, and `retainedContext`. | Checkpoint/action/storage compile coverage plus targeted tests. | Export rename is breaking for consumers using the old names. |
| 2 | Public docs used `Boundary` headings and overpromoted raw append. | `docs/architecture.md`, `docs/capabilities.md`, `docs/api.md` | Public docs avoid banned `Boundary` headings and describe raw append as an exception rather than normal authority path. | `pnpm build` and targeted tests. | Historical `.planning/` archive guard failures remain outside code/docs patch scope. |

## Remaining Work For Phase 19

- Add tests proving provider and worker modules cannot append Events or create Commands.
- Add targeted approval revised-input tests for schema, Authority, policy, and resource-scope revalidation.
- Replace fixture-only raw Check append usage where it is not purely setup.
- Add tests for delegated handoff/cancellation Command records.
- Add Bundle corruption tests for Event hash chain and Artifact manifest claims.
- Decide whether the canonical ontology guard should ignore historical `.planning/` archive files or migrate them.

## Verification

Commands run:

```text
pnpm build
pnpm exec vitest run tests/runtime/action-reconciliation.test.ts tests/runtime/timer-waits.test.ts tests/runtime/interaction-waits.test.ts tests/runtime/checkpoint.test.ts tests/views/checkpoints.test.ts tests/examples/governed-coding-run.test.ts
pnpm demo:governed-coding-run
pnpm package:check
```

Result:

- Build passed.
- Targeted tests passed: 6 files, 30 tests.
- Demo passed and rendered runtime/CLI surfaces with Command-owned approval, resume, reconciliation, Check-gated completion, and Bundle verification.
- Package content check passed.

Known verification caveat:

- `pnpm test -- ...` invokes the repository-wide Vitest run because the script ignores extra positional arguments. That full run currently fails the canonical ontology guard on historical `.planning/` archive/quick files that predate this phase. The failures are not from production code, current docs, examples, or tests changed in Phase 18.

## Requirement Status

- `PATCH-01`: Complete for Phase 18. Semantic patches, related naming, and related documentation were implemented with targeted verification. Phase 19 remains responsible for broader test hardening.
