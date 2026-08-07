# Remove CLI Inspection Guide Helper

Date: 2026-05-13

## Problem

`renderCliInspectionGuide(...)` added a framework helper that only printed
follow-up command suggestions. It was not needed for MVP behavior and kept
non-runtime guidance in the demo output path.

## Target

Remove the helper. The governed coding demo should print only actual
CLI-rendered command outputs.

## Verification

- `pnpm demo:governed-coding-run`
- `pnpm test -- tests/examples/governed-coding-run.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
