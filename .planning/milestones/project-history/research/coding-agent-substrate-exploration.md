# Coding-Agent Substrate Exploration

**Date:** 2026-05-12
**Topic:** Whether OpenRund is at the right abstraction level to enable coding-agent products without becoming one.

## Conclusion

OpenRund's direction is right: durable governed runtime semantics, not coding-product UX. However, coding-agent products still need a stronger substrate before CLI and demo polish. The missing substrate is not LSP or editor UX; it is governed mutation metadata, process execution, git capability, and deterministic evidence receipts.

The refined positioning is semantic ownership: OpenRund interoperates at system boundaries, but full guarantees require governed run control flow to be represented through OpenRund primitives. External orchestration can be translated into OpenRund semantics or invoked as a black-box capability, but black-box internal execution is not fully traceable by OpenRund.

## Decision

Add Phase 8.5 before Phase 9:

**Coding-Agent Substrate Capability Hardening**

This phase should preserve minimalism by adding only semantics that affect replay, governance, legality, auditability, or recovery.

## Rationale

- Coding agents require filesystem, process, and git-like workflows. Filesystem exists; process and git do not.
- Existing governed mutation metadata is under-wired: action requests do not yet persist the intended mutation descriptor.
- External frameworks prove demand for these substrate capabilities, but most conflate runtime semantics with product behavior.
- OpenRund's novelty is strongest if products can build rich coding agents on top while the runtime remains the authority boundary.

## Comparative Notes

| System | Relevant Signal | Implication For OpenRund |
| --- | --- | --- |
| Temporal | Durable execution, retries, waits, event history, AI cookbook patterns. | Confirms durability direction, but not agent authority semantics. |
| LangGraph | Checkpointed graph execution, interrupts, tasks for side effects, resume. | Confirms need to wrap side effects and preserve deterministic replay boundaries; full OpenRund guarantees require translating topology into OpenRund events rather than delegating the loop as a black box. |
| Deep Agents | Filesystem, shell, subagents, planning, context management, sandboxing. | Confirms minimum coding-agent substrate bundle. |
| Pi | Coding tools, bash execution, edit/diff/write, runs, branch-like history. | Confirms product layers need process and mutation surfaces. |
| OpenCode | Shell, git, permissions, LSP, TUI, runs, prompts, product UX. | Confirms process/git substrate while keeping LSP/UX out of OpenRund. |
| AGT | Policy, receipts, trust/sandbox boundaries, audit. | Confirms deterministic evidence/receipt views without turning OpenRund into governance middleware. |

## Recommended Boundaries

- Add TypeScript process capability.
- Add TypeScript git capability as an extension capability.
- Harden action-level governed mutation metadata.
- Generate deterministic policy/evidence receipts from canonical events/artifacts.
- Defer coding demo to Phase 10 after substrate hardening.
- Keep LSP/editor/code-review workflows out of Phase 8.5.
- Distinguish native, translated, and boundary integration modes in future docs and demos.
