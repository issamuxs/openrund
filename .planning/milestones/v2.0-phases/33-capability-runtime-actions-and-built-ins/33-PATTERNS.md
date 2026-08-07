# Phase 33: Capability Runtime, Actions, and Built-ins — Patterns

## Closest Existing Analogs

| New responsibility | Existing Python analog | Pattern to preserve |
|---|---|---|
| Capability definitions | `contracts/capabilities.py`, `engine/_governance.py` | Frozen values, closed validation, exact lookup |
| Action lifecycle | `engine/_engine.py`, `engine/_events.py` | Replay, evaluate, materialize, append; Engine alone owns Events |
| Worker seam | `ports/capabilities.py` | Async structural protocol returning `CapabilityResult` only |
| Artifact custody | `storage/_artifacts.py` | Immutable metadata/blob, hash and length verification, recovery |
| Root confinement | `paths.py`, storage path validation | Normalize once, reject platform confusion, inspect symlinks |
| Bounded subprocess | async provider seams and clock injection | Explicit lifetime, timeout, cancellation, bounded evidence |

## Dependency Direction

```text
contracts + ports + storage + views + engine
                       ↑
                 capabilities
                       ↑
            later run loop / assembly / CLI
```

The Engine never imports a concrete built-in. A Capability transport never appends an Event. Built-ins return `CapabilityResult`; an Action runner stores bytes and submits trusted Commands.

## Proposed File Map

| Path | Responsibility |
|---|---|
| `src/openrund/contracts/capabilities.py` | Registration, batching, cancellation, transport, and Artifact values |
| `src/openrund/contracts/commands.py` | Start/terminal Action and Artifact fact operations |
| `src/openrund/capabilities/_registry.py` | Validated explicit registry |
| `src/openrund/capabilities/_transports.py` | In-process and strict stdio JSON-RPC transport |
| `src/openrund/capabilities/_runner.py` | Durable start, dispatch, materialization, and terminal classification |
| `src/openrund/capabilities/_sandbox.py` | Root-bound portable path resolution |
| `src/openrund/capabilities/filesystem.py` | Filesystem actions |
| `src/openrund/capabilities/documents.py` | Markdown Capability definitions and client |
| `src/openrund/capabilities/documents_worker.py` | Root-bound stdio worker entry point |
| `src/openrund/capabilities/process.py` | Bounded executable actions |
| `src/openrund/capabilities/git.py` | Fixed local git actions |
| `tests/capabilities/` | Contract, security, lifecycle, and integration tests |

## Required Patterns

- Registration is explicit and duplicate-free; unsupported schema or transport metadata fails closed.
- Input and output schemas are checked at the untrusted boundary.
- Action start is a committed Event before worker invocation.
- A result contains data, compact effects/evidence, references, and optional Artifact bytes—never Events or Commands.
- Post-dispatch ambiguity yields unknown; confirmed deterministic worker rejection yields failed.
- Artifact bytes and metadata must agree on length/hash before the terminal Action fact.
- Every external path is relative to a declared root; existing symlink components and escapes are rejected.
- Mutation uses expected hashes/overwrite flags and atomic replacement where the platform permits it.
- Subprocesses have explicit executable, cwd, environment, stdin, time, output, and cancellation limits.
- Git has a closed verb set and no remote, config, hook, pager, editor, shell, or credential surface.

## Prohibited Patterns

- Capability code writing EventStore rows or constructing authoritative Events.
- Dispatch before `action.started` is durable.
- Treating timeout or lost transport after dispatch as a harmless failure.
- Absolute user paths, lexical traversal, symlink following, recursive deletion, arbitrary shell, inherited credentials, or unbounded output.
- Dynamic entry-point discovery, remote git, network capabilities, or graphical UI artifacts.

## Test Map

- `test_registry.py`: metadata, schema, duplicate, lookup, and transport validation.
- `test_transports.py`: in-process and strict framed JSON-RPC, malformed/error/timeout/cancel paths.
- `test_action_runner.py`: start-before-dispatch, one terminal result, Artifact materialization, failure/unknown/cancel.
- `test_filesystem_read.py`, `test_filesystem_mutation.py`: full operation and sandbox matrix.
- `test_documents.py`: Markdown read/write/patch/frontmatter/section/range/append over stdio.
- `test_process.py`: executable/env/shell/time/output/cancel boundaries.
- `test_git.py`: closed local verb set, repository/path checks, Artifact output.
- `test_integration.py`, `test_hygiene.py`: end-to-end Engine boundary, imports, typing, docs, package gates.
