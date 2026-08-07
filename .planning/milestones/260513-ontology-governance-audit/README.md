# 260513-ontology-governance-audit

**Milestone:** v1.2  
**Started:** 2026-05-13  
**Status:** launched, discovery baseline written

## Mission

Audit and harden OpenRund so the codebase proves the thesis:

> Model output is untrusted input. The Engine controls what becomes Run history.

The milestone is intentionally skeptical. Passing tests is not enough. The code, Events, Views, CLI output, examples, bundles, and docs must show that governance is real runtime semantics rather than demo theater.

## Source Of Truth

Semantic contract documents:

- `docs/concepts.md`
- `docs/architecture.md`
- `docs/control.md`
- `docs/capabilities.md`
- `docs/events.md`
- `docs/delegation.md`
- `docs/bundles.md`
- `docs/api.md`
- `docs/storage.md`
- `docs/providers.md`

Core ontology:

```text
Run
Command
Event
Message
ModelCall
Action
Wait
Delegation
Check
Checkpoint
Annotation
Artifact
Capability
Authority
Lease
Bundle
View
```

Approved secondary suffixes:

```text
View
Report
Receipt
Summary
Assessment
Manifest
Snapshot
IndexView
Milestone
Entry
Issue
```

Banned exported semantic nouns:

```text
State
Facts
Boundary
Blocker
Projection
Record
```

## Discovery Notes

Competitor scope:

- Temporal: durable execution and deterministic workflow replay.
- Kitaru: long-running Python agent runtime with checkpoints, replay, waits, isolated execution, and versioned deployments.
- Microsoft Agent Framework/AGT: enterprise agent framework and governance toolkit surface with agents, graph workflows, conversation state, middleware, telemetry, connectors, MCP/A2A integrations, and human-in-the-loop support.
- OpenAI Agents SDK: agent construction with tools, handoffs, tracing, conversation state, and guardrails.
- LangChain Deep Agents: deep-agent harness built on LangChain/LangGraph patterns with planning, filesystem, subagents, and middleware.

OpenRund's differentiator must remain narrower: the Engine makes governance part of runtime semantics by deciding which proposed operations become Commands, Events, Actions, Waits, Checks, Artifacts, Views, Receipts, Reports, and Bundles.

Initial code discovery:

- `packages/runtime/src/runtime-engine.ts` records `command.recorded` for model output paths, approval resolution, approval continuation, and action reconciliation.
- `packages/runtime/src/runtime-engine.ts` also has non-model methods such as `resolveInteraction`, `fireTimer`, `cancelTimer`, `recordDelegatedRunCompleted`, `requestCheckpoint`, and `recordActionOutcomeUnknown` that append Events without an adjacent visible `command.recorded`; these are audit-critical until justified or patched.
- `packages/cli/src/index.ts` renders `commands explain`, `actions receipt`, and `runs readiness` from runtime Events/Views, which matches the intended secondary-surface model.
- `packages/runtime/src/orun.ts` contains manifest, layout, file-integrity, Event hash-chain, bundle commitment, and Artifact manifest checks. Tests must prove the failure modes, not just the happy path.

## Required Artifacts

- `CODEBASE_MAP.md`
- `ONTOLOGY_AUDIT.md`
- `SECONDARY_SURFACE_AUDIT.md`
- `COMMAND_PATH_AUDIT.md`
- `GOVERNANCE_REALITY_AUDIT.md`
- `CLI_SURFACE_AUDIT.md`
- `DOC_CODE_GAP_REPORT.md`
- `PATCH_PLAN.md`
- `TEST_PLAN.md`
- `SUMMARY.md`

## Execution Rule

Do not patch before `PATCH_PLAN.md` is updated from the audits. Semantic violations must be corrected together with related naming and documentation when those surfaces are part of the public runtime contract.
