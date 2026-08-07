# Phase 37: Python-Only Cutover and Release - Context

**Gathered:** 2026-08-06
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via workflow.skip_discuss)

<domain>
## Phase Boundary

Cut over the verified runtime to one Python-only product and release surface.
Remove every live Node, pnpm, JavaScript, and TypeScript source, test, example,
tool, package, and generated dependency surface after preserving frozen
compatibility evidence. Finish standards-based package metadata, greenfield
Python documentation, coverage/security/docs/package gates, installed wheel and
sdist validation, Python 3.12-3.14 support, and retirement of the executable
compatibility oracle.

</domain>

<decisions>
## Implementation Decisions

### The agent's Discretion

All implementation choices are at the agent's discretion. Preserve canonical
wire/event compatibility and archived planning evidence, but present no older
implementation in live source, tests, examples, packages, commands, or
documentation. CLI interaction remains in normal plans and tests; OpenRund has
no graphical UI and requires no UI-SPEC or UI review.

</decisions>

<code_context>
## Existing Code Insights

Phase 36 verified 963 tests, strict typing, deterministic CLI output, an
isolated installed-wheel demonstration, and Engine-only authority. Remaining
live predecessor surfaces are top-level package-manager/build files,
`packages/`, `scripts/`, the separate `python/` worker tree, TypeScript tests
and examples, generated dependency directories, and historical documentation
that still names the predecessor stack. Frozen v1 fixtures under
`tests/fixtures/compatibility/v1` are data-only compatibility evidence and must
remain authenticated by Python tests.

</code_context>

<specifics>
## Specific Ideas

- Keep the base distribution dependency-free unless a runtime feature truly
  needs an optional extra.
- Replace the public example with Python-only installed CLI/library usage.
- Make cutover assertions executable so removed surfaces cannot return.
- Validate wheel and sdist from clean environments, including the console demo.

</specifics>

<deferred>
## Deferred Ideas

None. This phase is the final milestone cutover and release gate.

</deferred>
