# Quick Task 260511-raq: Correct governed write semantics - Context

**Gathered:** 2026-05-11
**Status:** Complete

<domain>
## Task Boundary

The runtime correctly requested approval because policy blocked
`documents.write`, but the research-brief demo proposed a draft path as the
action input and then used approval to relocate to the approved output path.

That made governance look theatrical: the runtime blocked the action, but the
demo authored a draft-to-approved choreography that was not required by the
runtime contract.

User decision:

- The proposed `documents.write` action should target the proposed final output
  path directly.
- Approval should authorize, deny, or relocate that final output path.
- A draft path should not appear unless the draft itself is a governed side
  effect.

</domain>
