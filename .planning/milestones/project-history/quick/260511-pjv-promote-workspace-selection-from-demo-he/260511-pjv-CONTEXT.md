# Quick Task 260511-pjv: Promote workspace selection from demo helper - Context

**Gathered:** 2026-05-11
**Status:** Ready for execution

<domain>
## Task Boundary

The research-brief demo currently prompts for a workspace root and computes the
default path itself. That behavior is right for the host, but the path semantics
should be framework-owned:

- Runtime execution state lives under `~/.openrund`.
- Each session has a workspace root for work products.
- The user/host selects that workspace at session start.
- If no workspace is selected, default to the session workspace under
  `~/.openrund/sessions/<sessionID>/workspace`.
- The demo should consume generic runtime helpers and record the selected
  workspace in session metadata.

</domain>

<decisions>
## Implementation Decisions

- Keep terminal prompts out of the runtime engine.
- Add reusable runtime helper(s) for selected/default workspace resolution and
  session execution metadata.
- Let the host/demo ask the user, but make it call runtime helpers for all path
  semantics.
- Store the selected workspace root in bootstrap metadata so replay/audit has
  the execution context.

</decisions>

