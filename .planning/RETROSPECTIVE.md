# Retrospective: OpenRund v1.0

## Summary

v1.0 successfully turned OpenRund from a normative runtime specification into a working MVP that demonstrates the full governed long-running run loop. The strongest outcome is that the framework now has executable semantics for authority, waits, delegation, uncertainty, check, and portability instead of relying on prompt convention or demo-only glue.

## What Worked

- Keeping the engine as the only authority boundary preserved the project's minimalism while still allowing rich filesystem and document workflows.
- Treating filesystem as a built-in governed capability, not semantic core, created a clean extension model for future capabilities.
- Adding explicit uncertainty before the demo made the runtime feel meaningfully novel rather than just another agent loop.
- The `.orun` export work sharpened OpenRund's portability story and made replay/verification concrete.
- The canonical demo stayed aligned with real primitives and helper APIs, which protects the framework from being shaped around a one-off showcase.

## Lessons

- Planning artifacts need regular checkpoint; detailed phase roadmaps are useful during execution but noisy once a milestone is complete.
- Generated milestone summaries need human review before becoming canonical project history.
- Runtime semantics that seem like "demo polish" often belong deeper in the framework when they affect authority, replay, or auditability.

## Recommended Next-Milestone Questions

- What developer journey should v1.1 optimize: provider breadth, capability authoring, production hardening, or richer replay/resume portability?
- Which runtime invariants should become public compatibility promises, and which should remain experimental?
- How much of the local MVP assembly should be treated as default developer ergonomics versus optional packages?

---

# Retrospective: OpenRund v1.1

## Summary

v1.1 moved OpenRund from a working MVP toward a stricter governed-runtime
surface. The milestone hardened SDK entry points, `.orun` portability,
coding-agent substrate capabilities, canonical ontology naming, first-class
Command decision semantics, CLI explanation surfaces, and the public flagship
demo.

The strongest outcome is that OpenRund's central claim became testable: model
output is a proposal, the Engine records a Command decision, accepted Commands
produce Events, and derived CLI/Receipt/Readiness surfaces explain rather than
decide.

## What Worked

- The ontology cutover forced real design clarity. Removing old names exposed
  hidden authority and secondary-surface drift that would otherwise have stayed
  vague.
- Treating approval as a Wait, not legality, produced a stronger demo and a
  cleaner runtime story.
- The single governed coding demo became a better launch artifact than multiple
  narrower examples.
- Static hygiene checks gave the ontology work teeth instead of leaving naming
  consistency as a review convention.
- `.orun` verification, Action Receipts, and Run readiness made governance
  inspectable from runtime artifacts.

## What Was Inefficient

- Several quick tasks were created after the main phase flow and remained
  uncommitted or partially superseded, making closure harder.
- v1.2 planning started before v1.1 was formally archived, so the v1.1 archive
  had to be reconstructed from phase artifacts.
- The original v1.1 audit became stale after later phases and inserted phases
  completed the gaps it reported.

## Patterns Established

- Canonical bare nouns are reserved for ontology roots; derived surfaces use
  approved suffixes.
- CLI output should render runtime/view fields directly and must not invent
  runtime facts.
- Command explanations should expose decision kind, decision trace, result
  Events, and typed Wait relationships.
- Unknown side-effect outcomes need explicit evidence-backed reconciliation.

## Key Lessons

- Milestone closure should happen before starting the next milestone's roadmap
  and requirements, otherwise archive automation loses its source of truth.
- GSD quick tasks need explicit final summaries and commits when they affect
  milestone-defining behavior.
- If the product claim is "governance is runtime semantics," rejected and
  deferred paths must be as visible as successful paths.

## Recommended Next-Milestone Questions

- Does every non-model mutation path now have a visible Command boundary, or
  does v1.2 still need to classify intentional internal lifecycle exceptions?
- Are Bundle/Receipt/Readiness surfaces complete enough for external audit, or
  only sufficient for the demo?
- Which launch claims should wait until v1.2 finishes the skeptical governance
  audit?

---

# Retrospective: OpenRund v2.0

## Summary

v2.0 shipped OpenRund as one typed Python 3.12+ distribution while preserving
the governed-runtime semantics, canonical data, and portability guarantees
proved by the milestone's authenticated evidence.

## What Worked

- Freezing compatibility evidence before implementation kept semantic and wire
  decisions explicit.
- Building contracts, replay, storage, Engine authority, effects, providers,
  Bundles, and assembly in dependency order kept authority seams local.
- Installed wheel and source-archive tests caught packaging behavior that
  source-tree tests alone could not prove.
- The Python-only retirement gates prevented a partially migrated product from
  being presented as complete.

## What Was Inefficient

- Detailed phase and quick-task records accumulated in active planning paths
  after their usefulness had become historical.
- Generated milestone accomplishments required manual compression before they
  were suitable as canonical project history.
- Demo workspace behavior needed two post-phase corrections to match the
  production assembly and intended operator experience.

## Patterns Established

- `src/openrund` is the single import package; repository metadata, tests,
  documentation, and runtime custody remain outside it.
- Runtime-owned state and operator workspaces are distinct, with a per-Run
  workspace proposed by the CLI.
- Living planning files stay compact; detailed execution evidence belongs in
  milestone archives.

## Key Lessons

- Close and compact a milestone before beginning another one.
- Treat package installation and CLI interaction as product behavior, not
  release afterthoughts.
- Preserve detailed evidence without forcing every historical record into the
  active project surface.
