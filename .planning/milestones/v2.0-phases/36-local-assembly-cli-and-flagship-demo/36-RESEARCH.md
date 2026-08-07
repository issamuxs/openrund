# Phase 36 Research

## Implementation Guidance

Python's standard `argparse`, `asyncio`, `json`, `uuid`, `datetime`, and context-management facilities are sufficient. The project remains dependency-free at runtime.

The console script should resolve configuration only from explicit arguments, except for an opt-in host-default runtime home. Commands that establish writable roots or Authority require explicit values. JSON output should use the existing canonical codec-compatible value conversion where semantic values cross the boundary.

The assembly should expose its Event store, Artifact store, Lease store, Engine, Capability registry, Action runner, optional provider loop, reporter, and operator-input seam as one context-managed value. It should materialize a per-Run home only when explicitly asked for a Run ID.

The demonstration must install the built wheel into an isolated environment and invoke public package/console surfaces without source-tree imports, Node, network access, ambient credentials, or repository-local executable helpers.
