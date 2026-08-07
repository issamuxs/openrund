# CLI Surface Audit

**Analysis date:** 2026-05-13  
**Status:** Phase 16 complete, audit-only

## Verdict

The CLI mostly respects runtime primitives. Read-only commands render Events, replayed Views, Artifact indexes, Check reports, Bundle verification results, and resume assessments. Mutating commands perform CLI argument parsing and then delegate to runtime methods; they do not decide legality locally.

No shipped CLI or demo surface was found that invents authoritative fields such as `receiptID`, `receiptIdentity`, `gateExplanation`, or `outcomeExplanation`. No shipped `openrund why` command exists.

Post-Phase-18 rerun: CLI correctness still inherits runtime correctness, but the largest inherited gap was reduced. Critical non-model runtime mutation paths now emit runtime Commands, and the governed demo’s Check recording uses the runtime-owned path. No new fake CLI fields or shipped `openrund why` command appeared after the patches.

## Command Matrix

| CLI section | Source object/View | Canonical concept(s) | Derived? | Invented fields? | Legality decision made by CLI? | Fixes needed |
|---|---|---|---:|---:|---:|---|
| `openrund inspect` | `runtime.replay(...)` plus execution metadata in `packages/cli/src/index.ts` | Run, View | Yes | No | No | None. `runtimeHome` and `workspaceRoot` are runtime/execution metadata, not new root concepts. |
| `openrund waits` | `replay.waits`, `runStatus.pendingWaits`, approval/interaction/timer Wait lists | Wait, Run, View | Yes | No | No | None. Approval, interaction, and timer remain Wait kinds, not root concepts. |
| `openrund waits show` | replayed approval Waits plus `wait.resolved` payloads | Wait, Action, Authority, Event | Yes | No | No | None. `approvedInputValidation` is runtime Wait-resolution data. |
| `openrund waits resolve` | `runtime.resolveApproval(...)` | Command, Wait, Authority | No, mutating runtime call | No | No; runtime decides | Good. CLI parses operator input and delegates to a Command-owned runtime method. |
| `openrund actions reconcile` | `runtime.reconcileActionOutcome(...)` | Command, Action, Artifact, Event | No, mutating runtime call | No | No; runtime decides | Runtime path is Command-owned. Phase 19 should harden evidence-required tests. |
| `openrund replay` | `runtime.replay(...)` | Run, Event, View | Yes | No | No | None. |
| `openrund timeline` | `runtimeMilestonesFromEvents(...)` over `runtime.readEvents(...)` | Event, Run, Action, Wait, Delegation, Check | Yes | No | No | None. Timeline labels are explanatory display labels, not lifecycle concepts. |
| `openrund checks export` | `runStatus.latestCheck`, `checkReportFromContent(...)`, `renderCheckMarkdown(...)` | Check, Artifact, Report | Yes | No | No | None in CLI. Runtime Check recording still needs Command ownership. |
| `openrund artifacts show` | `runtime.replay().artifactIndex` | Artifact, Event, View | Yes | No | No | None. |
| `openrund orun export` | `runtime.exportBundle(...)` | Bundle, Manifest, Event, Artifact | Filesystem mutation, not Run history | No | No; runtime/bundle API decides export shape | None. |
| `openrund orun verify` | `runtime.verifyBundle(...)` | Bundle, Event, Artifact | Yes | No | No; verifier decides result | None. CLI renders verifier checks. |
| `openrund orun import` | `runtime.importBundle(...)` then `runtime.assessImportedResume(...)` | Bundle, Assessment, Capability, Provider, Authority | Filesystem import plus derived assessment | No | No resume legality decision | None. Import does not auto-resume. |
| `openrund orun resume-report` | `runtime.importBundle(...)` and resume assessment | Bundle, Assessment, Wait, Artifact, Capability | Yes after import | No | No | None. Output is an assessment, not a resume action. |
| `openrund orun replay` | `runtime.replayBundle(...)` | Bundle, Run, Event, View | Yes | No | No | None. |
| `pnpm demo:governed-coding-run` | example orchestration plus `renderCliResult(...)` outputs | Run, Command, Action, Wait, Check, Bundle, View | Mixed, but rendered sections are runtime-derived | No | No | None in demo output. Phase 13 ran the demo and found no banned fake fields. |

## Extra Shipped CLI Surfaces

The implementation also includes create/run-style entry points not listed in the milestone prompt. They are not explanation surfaces and should stay thin runtime callers:

| CLI surface | Authority classification | Risk |
|---|---|---|
| Run creation | Delegates to runtime bootstrap/create behavior. | Bootstrap is an accepted documented exception if limited to Run creation. |
| Run advancement | Delegates to provider/model/runtime paths. | Must not grow local legality checks; provider output remains proposal input to runtime. |

## Renderer Findings

`packages/cli/src/index.ts` renders:

- Command explanation from `command.recorded` Events.
- Action receipt output from replayed ActionReceipt View data.
- Wait lists and approval Wait details from replayed Wait data.
- Run completion readiness from `runStatus.completionReadiness`.
- Check reports from Check Artifact content.
- Bundle verification, import, resume assessment, and replay output from runtime Bundle APIs.

These are acceptable secondary surfaces. They are derived displays over canonical runtime data and do not create new authoritative lifecycle concepts.

## Invented Field Check

Production/demo source contains no shipped surface using:

- `receiptID`
- `receiptIdentity`
- `gateExplanation`
- `outcomeExplanation`

The only relevant occurrences found in prior audit evidence were negative test assertions.

## `openrund why` Status

No shipped `openrund why ...` command exists. Public documentation should not present `openrund why` as an available CLI unless it is implemented as a runtime-backed explanation surface. Existing CLI explanation capabilities are represented by shipped command explanation, Action receipt, readiness, timeline, Wait, Check, and Bundle commands.

## Runtime Dependency Risks

| Severity | Risk | Why it matters | Owner phase |
|---|---|---|---|
| Reduced | CLI renders Events even if they entered through low-level fixture/bootstrap append paths. | Derived surfaces can be truthful but still display Events from low-level setup paths. | Phase 19 fixture/raw-append cleanup |
| Resolved for flagship path | `checks export` is derived, and the governed demo now records Checks through runtime-owned `recordCheckResult`. | Checks influence completion legality and should have visible Command ownership. | Phase 19 should migrate remaining fixture-only raw Check append usage where practical. |
| Medium | Bundle CLI is correct as a renderer, but verifier coverage needs corruption tests. | The CLI can only expose what bundle verification proves. | Phase 19 |

## Requirement Status

- `CLI-01`: Complete. Required CLI/demo commands are mapped to source objects and canonical concepts.
- `CLI-02`: Complete for CLI audit. CLI renders explanations and delegates mutations to runtime; it does not decide legality locally. Runtime command-path gaps remain Phase 18 work.
