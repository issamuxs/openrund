---
status: ready
mode: quick
must_haves:
  truths:
    - "Workspace root path semantics live in reusable runtime helpers, not demo-specific defaulting."
    - "The demo only prompts/hosts; it does not define the session workspace layout."
    - "Bootstrap metadata records runtime home and selected workspace root."
    - "Default workspace remains ~/.openrund/sessions/<sessionID>/workspace."
  artifacts:
    - "packages/runtime/src/workspace-root.ts"
    - "examples/research-brief/run.ts"
    - "docs/storage.md"
    - "docs/quickstart.md"
    - "docs/api.md"
    - "tests/runtime/workspace-root.test.ts"
---

# Quick Task 260511-pjv Plan

## Task 1: Framework Workspace Resolution Helper

- Add a runtime helper that resolves selected-or-default workspace roots.
- Add a helper that produces session execution metadata for bootstrap.
- Extend runtime tests to cover explicit selection and default selection.

## Task 2: Demo Consumes Framework Semantics

- Replace demo-owned workspace defaulting with runtime helper usage.
- Keep only the interactive prompt in the demo host.
- Record workspace metadata in session bootstrap metadata.

## Task 3: Documentation

- Update docs to say hosts ask/select workspace at session start and runtime
  helpers provide the default session layout.
- Clarify that the demo is an example host, not the source of workspace
  semantics.

