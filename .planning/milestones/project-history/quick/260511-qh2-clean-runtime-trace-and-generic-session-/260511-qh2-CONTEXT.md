# Quick Task 260511-qh2: Clean runtime trace and generic session surface - Context

**Gathered:** 2026-05-11
**Status:** Complete

<domain>
## Task Boundary

The research-brief demo had become a useful proof path, but parts of the
developer surface still looked demo-specific or insufficiently runtime-owned:

- Action and approval IDs were readable labels rather than collision-resistant
  framework IDs.
- `.orun` export defaulted outside the session tree.
- The final output printed a demo-specific semantics checklist instead of a
  generic session summary.
- The forced uncertainty path was embedded in the main example flow rather than
  isolated as demo-local fault injection.
- Evidence-backed reconciliation output did not clearly show expected versus
  observed validator facts.

User decisions captured for this task:

- Use the framework ID provider everywhere; do not add a demo ID provider.
- Use readable namespace plus hash suffix, with structured context and nonce or
  counter in the hash input to avoid same-name collisions.
- Keep the uncertainty simulator inside the demo tree, separate from the main
  agentic workflow and outside framework capability packages.
- Keep package manager and Node framework output visible; only remove useless
  OpenRund-specific verbosity.
- Default governance prompts should be no-action unless explicitly approved.
- Export `.orun` bundles under the owning session's `exports/` folder.

</domain>
