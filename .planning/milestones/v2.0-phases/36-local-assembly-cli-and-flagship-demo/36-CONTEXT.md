---
phase: 36
slug: local-assembly-cli-and-flagship-demo
mode: autonomous
discussion: skipped
ui: disabled
---

# Phase 36 Context

## Fixed Direction

- Preserve the established runtime architecture and sole Engine authority boundary.
- Build an explicit local Python assembly; callers must choose runtime home, workspace mounts, providers, process bindings, git identities, governance, and any Authority Commands.
- Expose a deliberate typed package-root API only now that all core subsystems are stable.
- Implement CLI behavior through normal Python modules and tests. No graphical UI, `UI-SPEC.md`, frontend safety gate, or UI review applies.
- Provide deterministic text and JSON output, stable exit classes, and a library/CLI parity boundary.
- Prove the installed distribution with one deterministic governed coding demonstration.

## Scope Fence

The CLI translates operator intent into typed Commands, calls the Engine or read-only Views/Bundle services, and renders results. It never appends Events, grants implicit Authority, infers writable roots, or creates a second legality implementation.
