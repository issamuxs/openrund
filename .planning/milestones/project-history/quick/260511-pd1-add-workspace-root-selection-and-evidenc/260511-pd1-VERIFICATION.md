# Quick Task 260511-pd1 Verification

**Verified:** 2026-05-11
**Status:** Passed

## Checks

- `pnpm typecheck`
- `pnpm exec vitest run tests/runtime/workspace-root.test.ts tests/examples/research-brief.test.ts tests/runtime/runtime-milestones.test.ts tests/runtime/cli-phase5.test.ts`
- `env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u OPENRUND_LOCAL_MODEL_URL -u OPENRUND_DEMO_PROVIDER pnpm demo:research-brief`
- Drift search for the removed temp-workspace/evidence-prompt wording and forbidden runtime-home token.

## Results

- TypeScript project references compile cleanly.
- Workspace-root helper, research-brief fixture, runtime milestone, and CLI timeline tests pass.
- The developer demo still fails clearly when no real provider is configured.
- Exact runtime-home override token remains absent.
- The old evidence prompt wording is gone.
- Default workspace-root behavior is covered by tests and points under `~/.openrund/sessions/<sessionID>/workspace`.
- Runtime audit expectations now assert capability-collected evidence fields including existence, size, hash, validator, candidate outcome, and evidence kind.

