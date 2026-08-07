# Fix Demo Run-Space Layout

Date: 2026-05-13

## Outcome

The governed coding demo now separates the governed workspace from runtime storage and uses the runtime-owned run-space layout for exported runtime artifacts.

Default demo layout:

- `<demoRoot>/workspace`
- `<demoRoot>/runtime`
- `runtimeHome/runs/<runID>/exports/<runID>.orun`

## Changes

- Updated `examples/governed-coding-run/run.ts` to use a generated `runID` by default.
- Updated the demo so the governed project workspace is distinct from `runtimeHome`.
- Kept `.orun` export under the canonical runtime run export path via `defaultBundlePath`.
- Added `runtimeHome` to the readable demo output so the run-space relationship is visible.
- Added regression assertions in `tests/examples/governed-coding-run.test.ts` for unique run IDs, workspace/runtime separation, and canonical bundle layout.

## Verification

- `pnpm demo:governed-coding-run`
- `pnpm test -- tests/examples/governed-coding-run.test.ts`
- `pnpm hygiene`
- `pnpm package:check`

## Notes

The regression was real: the demo had conflated governed workspace content with runtime run storage and used a fixed fixture `runID`. The demo now treats workspace as host-selected work product space and runtime home as OpenRund state/export space.
