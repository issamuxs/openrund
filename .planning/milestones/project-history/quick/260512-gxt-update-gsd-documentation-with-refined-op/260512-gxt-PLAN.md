# Quick Task 260512-gxt Plan: Update GSD documentation with refined OpenRund positioning

## Goal

Align planning and positioning documents with the refined thesis: OpenRund owns governed long-running session execution semantics when full guarantees are needed, interoperates at system boundaries, and avoids becoming a broad product/orchestration platform.

## Tasks

### 1. Update canonical positioning documents

Files:
- `.planning/PROJECT.md`
- `docs/principles.md`

Action:
- Replace ambiguous "not orchestration" language with "not a general orchestration product/platform" while affirming OpenRund owns orchestration-relevant execution semantics inside governed sessions.
- Add explicit semantic ownership and integration-mode language.

Verify:
- The documents state that native OpenRund mode provides full guarantees and black-box external orchestration provides only boundary-level visibility.

Done:
- Positive positioning is clear and no longer tap dances around orchestration ownership.

### 2. Update phase and roadmap contracts

Files:
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/phases/08.5-coding-agent-substrate-hardening/08.5-CONTEXT.md`
- `.planning/phases/09-cli-and-operator-experience/09-CONTEXT.md`
- `.planning/phases/10-demo-minimality-documentation-and-package-readiness/10-CONTEXT.md`

Action:
- Sharpen Phase 8.5, 9, and 10 around semantic ownership rather than vague compatibility.
- Update requirements where they currently imply OpenRund does not replace any orchestration framework at all.

Verify:
- Phase 8.5 is about native substrate semantics.
- Phase 9 remains CLI inspection/operator control.
- Phase 10 docs/demo positioning explains boundaries against LangGraph, Temporal, Deep Agents/OpenCode, and AGT.

Done:
- Remaining phases preserve the refined thesis and avoid defensive framing.

### 3. Update research note and GSD state

Files:
- `.planning/research/coding-agent-substrate-exploration.md`
- `.planning/STATE.md`
- `.planning/quick/260512-gxt-update-gsd-documentation-with-refined-op/260512-gxt-SUMMARY.md`

Action:
- Capture the refined integration/competition positioning.
- Record the quick task completion in state and summary.

Verify:
- Search for stale "not orchestration framework" or "without positioning replacement" language in active planning docs.

Done:
- GSD trail captures the correction and next step remains Phase 8.5 planning.
