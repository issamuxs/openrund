# Doc/Code Gap Report

**Analysis date:** 2026-05-13  
**Status:** Phase 17 complete, audit-only

## Verdict

The docs describe the correct target contract, but several claims are stronger than the current implementation. The critical mismatch is Engine-owned Command uniformity: model-originated paths are governed, but multiple non-model runtime mutation APIs still append authoritative Events without visible `command.recorded` evidence.

This does not make the whole runtime theater. It does mean the public claim “model-originated and non-model mutations share the same Engine-owned Command path” is not yet true everywhere.

Post-Phase-18 rerun: the critical doc/code mismatches for non-model Command ownership, Check recording ownership, terminal fallback Events, public ontology naming, and API raw-append framing were corrected in code/docs. This report keeps the original Phase 17 gap matrix for audit traceability; rows marked incomplete there should be read with the post-Phase-18 update below.

## Post-Phase-18 Update

| Gap area | Rerun result | Remaining follow-up |
|---|---|---|
| Non-model Command ownership | Critical runtime paths now prepend `command.recorded` before state-changing Events. | Phase 19 should add exhaustive tests for every patched path. |
| Public raw append | `docs/api.md` no longer presents `append` as a normal mutation method and documents it as a low-level bootstrap/fixture/storage-adjacent escape hatch. | Phase 19 should migrate remaining non-setup raw append tests where practical. |
| Check recording | `RuntimeEngine.recordCheckResult(...)` exists and the governed demo uses it. | Phase 19 should migrate fixture-only raw Check append where practical and add explicit Command linkage tests. |
| Terminal fallback | Direct `complete_run` and `fail_run` terminal fallback Events were removed. | Phase 19 can add regression tests that unsupported terminal fallback cannot complete/fail a Run. |
| Public ontology names | `CommandDecisionEntry`, `EffectEntry`, `LeaseEntry`, `ArtifactEntry`, and `retainedContext` replaced the old public names in current packages/docs/tests/examples. | Guard now rejects old names on current public/production surfaces. |
| CLI fake fields | No `receiptID`, `receiptIdentity`, `gateExplanation`, `outcomeExplanation`, or shipped `openrund why` appeared in current CLI/demo surfaces. | Keep negative tests. |

## Gap Matrix

| Doc claim | Code reality | Severity | User-facing impact | Recommended fix | Implemented? | Follow-up required? |
|---|---|---|---|---|---:|---:|
| `docs/concepts.md` and `docs/architecture.md` say Runtime/API/Timer/Capability/Operator/Recovery paths enter the Engine-owned Command path and only the Engine appends state-changing Events. | `recordModelOutput`, `resolveApproval`, `continueApprovedAction`, and `reconcileActionOutcome` record Commands. `RuntimeEngine.append`, interactions, timers, Check recording through helper + append, unknown marking, runtime checkpoint requests, and delegated handoff/cancellation can append Events without visible Commands. | Critical | Skeptical reviewers can falsify the uniform governance claim from public runtime APIs. | Add Command-owned runtime operations for non-model mutations, narrow or rename raw append to bootstrap/test/internal use, and document the bootstrap exception. | Partial | Yes |
| `docs/api.md` lists `append(runID, expectedPosition, events)` as a primary `RuntimeEngine` method while docs also claim callers do not append authoritative Events. | Public raw append is an authority escape hatch unless explicitly scoped. Tests/examples use it for setup and Check recording. | Critical | Public API invites bypassing the Command path that the architecture says is mandatory. | Replace public usage with semantic runtime methods where possible; if raw append remains, rename/document it as an internal/bootstrap/test escape hatch and exclude it from normal runtime API docs. | No | Yes |
| `docs/control.md` says approval is not legality and illegal Operations must be rejected rather than approved. | Approval resume revalidates through dispatcher and authority helpers, but proof is indirect for all revised-input dimensions. | High | Operators may believe approval grants legality if revised inputs are not explicitly tested against schema, Authority, policy, and resource scope. | Add targeted tests proving approved revised input is revalidated against schema, Authority, policy, and resource scope before any Action lifecycle Events. | Partial | Yes |
| `docs/control.md` says unknown outcomes are explicit and reconciled through evidence. | `action.unknown` exists and blocks completion when required; reconciliation is Command-owned. Direct `recordActionOutcomeUnknown` lacks visible Command ownership. | High | Unknown outcome governance can differ depending on whether unknown came from dispatcher or direct runtime API. | Make unknown-outcome marking Command-owned or restrict the direct API as internal; require evidence linkage in tests. | Partial | Yes |
| `docs/architecture.md` says completion is terminal legality, not a model utterance. | Guarded `complete_run` calls `assertRunCanComplete`, but fallback `modelOutputToEvents` still contains direct terminal/lifecycle cases for complete/fail/cancel. | High | If the fallback is reachable, terminal Run state can bypass completion legality. | Remove terminal fallback cases or prove unreachable with code structure and tests. | Partial | Yes |
| `docs/capabilities.md` says workers return `CapabilityResult`; they do not create Commands, append Events, grant Authority, decide terminal Run state, or mutate Views. | Built-in workers return results and no direct Event append was found. `ActionDispatcher` materializes Events under runtime control. | Low | Claim appears true; needs regression coverage so future workers do not bypass Engine authority. | Add provider/worker authority guard tests in Phase 19. | Yes | Yes |
| `docs/providers.md` says providers are transport/parsing adapters and do not create Commands or append Events. | Provider adapters return parsed ModelCall/operation data; no direct Event append found. | Low | Claim appears true; guard coverage should prevent regression. | Add or keep tests proving provider modules cannot append Events or create Commands. | Yes | Yes |
| `docs/storage.md` says storage preserves ordering/content and does not decide legality. | Storage append interfaces are generic and do not validate legality. That is correct, but public `RuntimeEngine.append` makes the caller path authority-sensitive. | Medium | Storage itself is not the problem; runtime API exposure can make storage-like append behavior look normal. | Keep storage legality-free; move legality enforcement to runtime Command APIs and document storage as lower-level persistence only. | Partial | Yes |
| `docs/storage.md` and `docs/events.md` say Views are rebuildable from Events and Artifacts and do not decide legality. | Views are derived. Runtime completion uses derived data from complete Event inputs; CLI renders Views only. | Low | Claim is mostly true. Risk is stale/cached View misuse, not found in current audit. | Keep tests around replay/rebuild determinism and avoid cached View authority. | Yes | Phase 19 test hardening |
| `docs/bundles.md` says Bundle verification checks manifest, layout, file integrity, Event hash chain, Artifact manifest consistency, and fail-closed metadata; import does not auto-resume. | Implementation in `packages/runtime/src/orun.ts` covers these checks and CLI import assesses resume rather than resuming. | Low | Claim appears implemented; corruption coverage must match public claims. | Add targeted corrupted Event hash chain, missing Artifact, malformed metadata, and unsupported critical-field tests. | Yes | Yes |
| `docs/events.md` says `check.recorded` records semantic validation and completion rules use Checks. | Check helpers create Events, but Check recording can be appended directly by callers such as demo/test code. | High | A Check that affects completion can enter history without visible Command ownership. | Add `RuntimeEngine.recordCheckResult(...)` or equivalent Command-owned Check recording and update examples/tests to use it. | No | Yes |
| `docs/concepts.md` bans exported production semantic names using `Record`, `Facts`, `Boundary`, `Blocker`, `Projection`, and `State`. | Public/exported or public-facing names include `CommandDecisionRecord`, `EffectRecord`, `LeaseRecord`, `ArtifactRecord`, checkpoint `retainedFacts`, and doc headings using `Boundary`. | Medium | Public ontology looks inconsistent and weakens the claim that secondary surfaces cannot invent authority. | Rename public semantic names to approved suffixes such as `Entry`; rename `retainedFacts` to `retainedContext`; update related docs and tests together. | No | Yes |
| `docs/api.md` documents runtime method names including `runRun`, `requestInteraction`, `scheduleTimer`, and `recordCheckResult`. | Exact exported runtime method surface is not fully aligned with docs; some methods exist under different names or as helpers, and `recordCheckResult` is not consistently a RuntimeEngine method. | Medium | API docs may mislead integrators and reviewers about what is actually shipped. | Align docs with actual exports or add the missing runtime methods during Phase 18/19. | No | Yes |
| `docs/api.md` says CLI explanation commands do not synthesize legality or append canonical Events. | Phase 16 confirmed CLI renderers read runtime Events/Views and mutating CLI commands delegate to runtime. | Low | Claim is true for CLI, but runtime command-path gaps can still leak through CLI output. | Keep CLI no-invented-fields tests and fix runtime authority gaps. | Yes | Yes |
| `docs/delegation.md` describes parent/child handoff and cancellation as Engine-governed delegation lifecycle. | Delegation creation from model path is Command-owned, but delegated handoff complete/fail/cancel and parent cancellation append Events without visible Commands. | High | Delegation lifecycle authority can bypass the same Command path required for other lifecycle mutations. | Add system/operator Command records for delegation handoff and cancellation paths. | Partial | Yes |

## Critical Gaps To Resolve First

1. Non-model Event append paths without visible Commands.
2. Public `RuntimeEngine.append` as a normal API surface.
3. Check recording without Command ownership.
4. Terminal Run fallback cases in `modelOutputToEvents`.
5. Delegation handoff/cancellation without Command ownership.

## High/Medium Follow-Up Queue

1. Approval revised-input revalidation tests.
2. Unknown outcome marking Command ownership and evidence-linkage tests.
3. Public ontology renames: `CommandDecisionRecord`, `EffectRecord`, `LeaseRecord`, `ArtifactRecord`, `retainedFacts`, and docs `Boundary` headings.
4. API docs alignment with actual shipped runtime methods.
5. Bundle verifier corruption test hardening.

## Claims That Appear Implemented

- Providers do not create Commands or append Events.
- Workers return results and do not append Events directly.
- CLI explanation surfaces render runtime data rather than deciding legality.
- Bundle import does not auto-resume.
- Views are rebuildable from Events and Artifacts.

These still need regression tests where Phase 19 requires them.

## Requirement Status

- `DOCGAP-01`: Complete. Material doc/code mismatches are classified with severity, impact, recommended fixes, and follow-up status.
