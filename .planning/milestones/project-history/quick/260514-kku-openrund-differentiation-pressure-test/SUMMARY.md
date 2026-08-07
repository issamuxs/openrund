# Quick Exploration 260514-kku Summary

## Objective

Pressure-test whether OpenRund is meaningfully differentiated from modern agent
harnesses and adjacent runtimes.

## Finding

OpenRund is not differentiated by permissions, approvals, waits, replay,
persistence, HITL, tracing, tool control, or sandboxing. Those are mainstream
harness/runtime primitives.

OpenRund has a plausible but narrow wedge only if it remains a
mutation-legality runtime: attempted mutation becomes Command, legality becomes
CommandDecision, and only accepted Commands materialize canonical Events.

Latest review update: the wedge is real but fragile. A strong team could
recreate much of it with Temporal, LangGraph or Agents SDK, middleware, an event
store, and custom audit records. OpenRund's defensible claim is that it makes
the convergent legality kernel explicit, coherent, and testable.

## Decision

Continue only under this stricter framing:

> OpenRund is a governed mutation runtime for consequential agent work.

Treat generic harness positioning as a trap. The differentiator must be proven
through completion legality, unknown outcome reconciliation, approval-not-
legality, delegated Authority attenuation, replayable CommandDecisions, and
Bundle/CLI explanations derived from runtime artifacts.

Classify OpenRund as a serious systems/research artifact with a possible narrow
OSS wedge, not an obvious product startup or broad agent platform. The next
finish line should be an ontology-clean runtime, governed coding demo, CLI proof
surfaces, and optionally a small legality-debugger UI or systems-style paper.

## Artifact

- `EXPLORATION.md`

## Verification

- Planning-only exploration. No runtime code or public docs were changed.
