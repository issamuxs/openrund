# Quick Task 260512-gxt: Update GSD documentation with refined OpenRund positioning - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning

<domain>
## Task Boundary

Update GSD documentation and related positioning references so OpenRund is described positively and precisely:

- OpenRund is a governed runtime for durable long-running agent sessions.
- OpenRund's strongest guarantees require native ownership of session execution semantics.
- OpenRund interoperates at system boundaries, but black-box external orchestration is only partially visible.
- OpenRund can replace orchestration semantics inside governed sessions without becoming a broad orchestration product, prompt framework, coding product, policy middleware, or UI platform.

</domain>

<decisions>
## Implementation Decisions

### Positioning
- Use positive language centered on semantic ownership: canonical history, authority, approvals, side-effect discipline, uncertainty, validation, replay, resume, and portability.
- Avoid defensive "not X" framing except where it prevents scope drift.

### Compatibility
- Express three integration modes: native OpenRund mode for full guarantees, translated/compiled mode for full guarantees if external topology is represented as OpenRund events, and black-box capability mode for boundary-only guarantees.

### Phase Scope
- Phase 8.5 should prove coding-agent substrate through OpenRund-owned semantics.
- Phase 9 should present CLI as semantic inspection/operator control.
- Phase 10 should explain the thesis clearly in docs and demos: OpenRund owns governed session semantics when full guarantees matter, while neighboring frameworks remain useful at system boundaries or product layers.

</decisions>

<specifics>
## Specific Ideas

The key formulation is: OpenRund interoperates broadly at system boundaries, but its strongest value appears when long-running agent control flow is expressed natively through OpenRund primitives.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/phases/08.5-coding-agent-substrate-hardening/08.5-CONTEXT.md`
- `.planning/phases/09-cli-and-operator-experience/09-CONTEXT.md`
- `.planning/phases/10-demo-minimality-documentation-and-package-readiness/10-CONTEXT.md`
- `.planning/research/coding-agent-substrate-exploration.md`
- `docs/principles.md`

</canonical_refs>
