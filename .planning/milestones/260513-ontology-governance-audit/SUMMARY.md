# Summary

**Milestone:** v1.2 `260513-ontology-governance-audit`  
**Status:** complete  
**Updated:** 2026-05-15

## Milestone Objective

Audit and harden OpenRund so the repository proves the MVP thesis:

> Model output is untrusted input. The Engine controls what becomes Run history.

The audit standard was not "tests pass." The standard was whether OpenRund's ontology, runtime-governance model, CLI/operator surfaces, documentation, examples, and tests make the governed mutation model real:

```text
Operation -> Command -> CommandDecision -> Event materialization -> Views / Receipts / Reports
```

## What Was Audited

- Codebase ownership and authority paths: `CODEBASE_MAP.md`.
- Public ontology and semantic names: `ONTOLOGY_AUDIT.md`.
- Derived and explanatory surfaces: `SECONDARY_SURFACE_AUDIT.md`.
- Model and non-model mutation paths: `COMMAND_PATH_AUDIT.md`.
- Runtime governance reality: `GOVERNANCE_REALITY_AUDIT.md`.
- CLI and demo output surfaces: `CLI_SURFACE_AUDIT.md`.
- Documentation claims versus code: `DOC_CODE_GAP_REPORT.md`.
- Semantic patch plan and implementation: `PATCH_PLAN.md`.
- Test coverage and verification results: `TEST_PLAN.md`.
- Phase 18 implementation evidence: `.planning/phases/18-patch-plan-and-semantic-fixes/18-SUMMARY.md`.
- Phase 19 verification evidence: `.planning/phases/19-governance-test-hardening/19-VERIFICATION.md`.
- Recent live-documentation coherence: `.planning/quick/260514-nb8-documentation-ownership-consolidation/CODE_DOC_COHERENCE_REPORT.md` and `DOCUMENTATION_CONSISTENCY_REPORT.md`.

## Critical Findings

- Early audit findings were legitimate: non-model runtime paths, Check recording, terminal fallback Events, and public raw append framing could weaken the Engine-owned Command claim.
- The model-originated path was already strong: illegal filesystem writes were rejected through `command.recorded`, approval-required writes deferred through `Wait(kind = approval)`, unknown outcomes blocked completion, reconciliation was evidence-linked, and completion was gated by runtime checks.
- The largest semantic gap was consistency across non-model mutation origins. Timers, interactions, checkpoints, unknown outcome marking, delegated handoff/cancellation, and Check recording needed visible runtime Commands before state-changing Events.
- CLI and demo surfaces were not the primary source of invented authority. They were mostly derived, but they depended on runtime Command-path correctness.
- Bundle verification was materially implemented, but needed a stronger corruption test proving Event hash-chain verification instead of only file-integrity mismatch.
- Documentation was directionally correct but initially overclaimed implementation uniformity. The later documentation consolidation made live docs coherent around governed mutation runtime positioning and CommandDecision-centered lifecycle semantics.

## Patches Made

- Phase 18 added visible `command.recorded` Events to critical non-model runtime mutations in `packages/runtime/src/runtime-engine.ts`.
- Phase 18 added `RuntimeEngine.recordCheckResult(...)` and moved the governed coding demo to the Command-owned Check path.
- Phase 18 removed direct terminal fallback Events for guarded terminal Run mutations.
- Phase 18 corrected public ontology-facing names including `CommandDecisionEntry`, `EffectEntry`, `LeaseEntry`, `ArtifactEntry`, and `retainedContext`.
- Phase 18 reframed `RuntimeEngine.append(...)` in docs as a low-level bootstrap/fixture/storage-adjacent escape hatch, not a normal provider/worker/CLI/example mutation path.
- Follow-up documentation quick tasks aligned README, concepts, control, architecture, API, events, capabilities, delegation, bundles, providers, quickstart, and storage around the governed mutation runtime model.
- Documentation consolidation in `260514-nb8` reduced duplicated philosophy, clarified semantic ownership, and verified code/doc coherence against live docs and implementation symbols.

## Tests Run

The final milestone test evidence is in `TEST_PLAN.md` and Phase 19 verification.

- Targeted runtime governance tests passed: approval deferral/resume, revised input validation, unknown outcomes, reconciliation, Check gating, timers, interactions, checkpoints, and delegation.
- Provider and worker non-authority tests passed.
- CLI field-discipline tests passed, including negative checks for `receiptID`, `receiptIdentity`, `gateExplanation`, and `outcomeExplanation`.
- Bundle corruption testing passed for tampered `events.jsonl` with recomputed file integrity, proving Event hash-chain verification fails closed.
- Required verification passed:
  - `pnpm test -- tests/examples/governed-coding-run.test.ts tests/runtime/cli-phase5.test.ts tests/runtime/orun-bundle.test.ts tests/views/action-reconciliation.test.ts tests/runtime/action-reconciliation.test.ts`
  - `node scripts/check-ontology-canonical.mjs`
  - `pnpm test`
  - `pnpm demo:governed-coding-run`
  - `pnpm hygiene`
  - `pnpm package:check`
- Phase 20 reran:
  - `node scripts/check-ontology-canonical.mjs`
  - `pnpm hygiene`
  - `pnpm package:check`

## Remaining Risks

- `RuntimeEngine.append(...)` still exists. It is now documented as an exceptional low-level path, but it remains a real escape hatch if future code or consumers misuse it outside bootstrap, fixture, or storage-adjacent contexts.
- Live provider smoke tests remain skipped without credentials or local endpoints. Provider non-authority is structurally tested, but live transport behavior is not fully exercised in this milestone.
- The verdict applies to audited MVP runtime paths and public surfaces. Future mutation APIs must be held to the same `Command -> CommandDecision -> Event materialization` pattern or the governance claim can regress.
- Historical archived docs and planning artifacts still contain older terminology by design. The live docs and current public surfaces are the supported scope.
- Git continues to report repository GC warnings about unreachable loose objects during commits. This is repository maintenance noise, not a runtime-governance failure.

## Follow-Up Tasks

- Keep `RuntimeEngine.append(...)` under review. If OpenRund grows beyond MVP, consider moving it behind a lower-level storage/testing interface or adding stronger guardrails around production-facing use.
- Add live provider smoke coverage when credentials/local endpoints are available.
- Add a regression checklist for every future mutation API: origin, Command, CommandDecision, Event materialization, View/Receipt derivation, tests.
- Preserve the live-documentation ownership model so docs do not drift back into repeated manifesto language or overclaiming beyond code.
- Continue treating UI, if added, as a runtime-backed operator surface over ontology primitives, not a workflow builder, chatbot, DAG editor, or authority boundary.

## Verdict

**Verdict: governance is real.**

This verdict is scoped: governance is real for the audited MVP runtime paths and public surfaces. The claim is now backed by code, Events, CLI/demo output, documentation coherence, and tests.

It is not a claim that OpenRund is production-hard, competitor-proof, or safe against future API drift. The remaining risks are real, especially the raw append escape hatch and skipped live provider smoke tests. But the MVP is no longer governance theater: illegal mutations are rejected without target lifecycle Events, approval is deferred and revalidated through Commands, non-model mutations now have visible Command paths, unknown outcomes block completion until evidence-backed reconciliation, completion is terminal legality, CLI surfaces render derived runtime primitives, and Bundles fail closed on Event hash-chain corruption.

