# Code And Documentation Coherence Report

## Scope

Checked the consolidated documentation edits against live docs, public API
sentinels, CLI command names, runtime helper names, and implementation symbols.

## Checks Performed

- Searched live docs and planning context for stale broad positioning:
  `TypeScript runtime for controlled`, mixed decision wording, `legality-kernel`,
  platform/harness/product language, workflow/DAG terminology, and old
  first-class governance duplication.
- Checked lifecycle strings across README and docs for consistency with
  `Operation -> Command -> CommandDecision -> Events`.
- Checked quickstart/API examples against implementation exports:
  `createLocalRuntime`, `sqlite`, `defaultBundlePath`, `RuntimeEngine`,
  `command.recorded`, `commands explain`, `runs readiness`, and
  `resume-assessment`.
- Checked docs index links and sentinels through the existing docs test.

## Findings

| Area | Result | Notes |
|---|---|---|
| Public positioning | Pass | Live docs now use governed mutation runtime framing. Archived docs retain old historical wording and are intentionally out of live-doc scope. |
| Lifecycle model | Pass | README, concepts, control, and architecture all preserve CommandDecision-centered lifecycle semantics. |
| Quickstart API references | Pass | `createLocalRuntime`, `sqlite`, `defaultBundlePath`, `recordModelOutput`, `readEvents`, and CLI commands exist in the codebase. |
| CLI/UI semantics | Pass | Docs describe CLI as a runtime-backed operator surface. No live doc introduces UI workflow builder, chatbot, DAG, task, or job abstractions. |
| Bundle semantics | Pass | `bundles.md` owns replay/import/resume semantics; `storage.md` now points to it instead of duplicating details. |
| Provider/worker/storage non-authority | Pass | Provider, Capability, and Storage docs each own their specific non-authority boundary. |
| Stale wording | Fixed | Replaced `Why did this model-proposed Operation become executable?` with `Why did this model-proposed Operation become accepted runtime work?` in `docs/control.md`. |

## Residual Notes

- `executable` still appears in valid contexts such as executable interfaces,
  the `openrund` executable, and executable CLI routing.
- Historical archived docs still contain pre-refresh language by design.
- Planning artifacts intentionally preserve prior audit/problem statements and
  should not be rewritten as live documentation.
