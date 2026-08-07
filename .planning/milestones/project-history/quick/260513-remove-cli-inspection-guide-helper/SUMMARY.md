# Remove CLI Inspection Guide Helper

Date: 2026-05-13

## Outcome

Removed `renderCliInspectionGuide(...)`. The governed coding demo now prints
only actual CLI-rendered outputs:

- `inspect`
- `commands explain`
- `waits show --kind approval`
- `actions receipt`
- `runs readiness`
- `orun verify`

No demo-owned command guidance or `OPENRUND_HOME` instructions are printed.

## Verification

- `pnpm demo:governed-coding-run`
- `pnpm test -- tests/examples/governed-coding-run.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
