<!-- GSD:project-start source:PROJECT.md -->
## Project

OpenRund is a Python runtime framework for durable agent runs where the runtime enforces legality, persistence, waits, authority, and terminal state. The current milestone releases the complete governed runtime as one typed Python package.

Core value: provide a minimal but authoritative runtime where long-running agent runs remain durable, lawful, replayable, portable, and inspectable even when models, workers, or infrastructure fail.
Current direction: release one dependency-free Python base package with explicit local assembly, governed built-in Capabilities, provider adapters, `.orun` Bundles, an installed command, and a deterministic offline demonstration.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Python 3.12+, uv, hatchling, SQLite, pytest, strict mypy, and Ruff. Runtime dependencies remain standard-library only unless an explicit adapter requires an optional dependency.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Follow the normative runtime docs in `docs/`, keep event payloads compact, treat artifacts as immutable references, and preserve the engine as the only authority boundary.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

The implementation contract lives in [docs/architecture.md](docs/architecture.md), scoped by [docs/concepts.md](docs/concepts.md), with supporting references in `docs/events.md`, `docs/providers.md`, `docs/capabilities.md`, `docs/storage.md`, `docs/delegation.md`, and `docs/bundles.md`.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add project-local skills later only if they meaningfully codify OpenRund-specific workflows.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `$gsd-quick` for small fixes and doc updates
- `$gsd-debug` for investigation and bug fixing
- `$gsd-execute-phase` for planned phase work
- `$gsd-next` to detect and run the next milestone action
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `$gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` - do not edit manually.
<!-- GSD:profile-end -->
