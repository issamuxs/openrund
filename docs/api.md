# API and CLI

OpenRund exposes a typed Python API and one installed `openrund` command.
Library operations return `OperatorResult[TData]` with a frozen typed payload.
The CLI rendering adapter converts that typed payload to the stable JSON/text
wire shape; rendering never decides legality.

## Import compatibility

The exact `openrund` package-root facade is frozen for the 2.x release line.
Common assembly and runtime entry points remain available there, while advanced
contracts and typed result payloads should be imported from named subpackages
such as `openrund.operator`, `openrund.engine`, and `openrund.bundles`.

Contracting the root facade is a major-release change. It requires migration
notes and updated compatibility evidence; names are not removed as routine
cleanup within 2.x.

## Local assembly

```python
from openrund import LocalAssemblyConfig, create_local_runtime

runtime = create_local_runtime(LocalAssemblyConfig(runtime_home=".openrund"))
```

`LocalAssemblyConfig` accepts explicit mounts, registered Capabilities, bounded
process bindings, optional Git configuration, an optional model provider,
clock and ID factories, operator input, reporter, and SQLite busy timeout.

`LocalRuntime` exposes:

- `engine: RuntimeEngine`
- `operator: OperatorService`
- `action_runner: ActionRunner`
- `registry: CapabilityRegistry`
- Event, Artifact, and Lease stores
- optional `run_loop`
- `materialize_run_home(run_id)`
- async context management and `aclose()`

An empty mount set registers no built-in Capability. Configuration makes a
Capability reachable; only durable Engine Commands can grant Authority.

## Engine

The public mutation API is:

```python
result = await runtime.engine.submit(command)
```

`Command` contains a stable `CommandId`, target `RunId`, origin, typed
operation, and optional idempotency evidence. `CommandResult.decision` is one of
accepted, rejected, deferred, or superseded. Callers must not append canonical
Events directly. [Control](./control.md) owns the normative distinction between
the Engine's procedural mutation boundary and the authoritative decision for an
individual attempt.

## Operator service

`OperatorService` groups stable host operations:

- Runs: `create_run`, `advance_run`, `inspect_run`, `replay_run`, `timeline`,
  and `readiness`.
- Waits: `waits`, `resolve_approval`, and `resume_approval`.
- Evidence: `explain_command`, `action_receipt`, `reconcile_action`, `checks`,
  `record_check`, and `artifact`.
- Bundles: `export_run_bundle`, `verify_run_bundle`, `replay_run_bundle`,
  `import_run_bundle`, and `assess_run_bundle`.

Every mutation method constructs a typed Command and calls the Engine.
Read-only methods rebuild deterministic Views from complete Event history.

## CLI

Global options precede the command:

```text
openrund [--home PATH] [--json] COMMAND
```

Supported commands are:

```text
runs create RUN_ID [--title TEXT] [--objective TEXT]
runs advance RUN_ID MESSAGE
runs inspect RUN_ID
runs replay RUN_ID
runs timeline RUN_ID
runs readiness RUN_ID

waits list RUN_ID
waits resolve RUN_ID WAIT_ID --decision approved|denied|cancelled
  [--input-json JSON] [--note TEXT] [--by ACTOR]
waits resume RUN_ID WAIT_ID

commands explain RUN_ID COMMAND_ID
actions receipt RUN_ID ACTION_ID
actions reconcile RUN_ID ACTION_ID --outcome completed|failed|cancelled
  --evidence TEXT [--note TEXT] [--by ACTOR]

checks list RUN_ID
checks record RUN_ID NAME --status passed|failed|blocked --summary TEXT
  [--subject TEXT] [--rule TEXT] [--validator TEXT]
artifacts show RUN_ID ARTIFACT_ID

bundles export RUN_ID PATH [--profile complete|audit|redacted]
bundles verify PATH
bundles replay PATH
bundles import PATH [--map NAME=/absolute/path]
bundles assess PATH [--map NAME=/absolute/path]

demo governed-coding [WORKSPACE]
```

With no `WORKSPACE`, interactive text execution proposes the per-Run default
and accepts Enter or an operator-selected replacement. JSON and non-interactive
execution select the default without prompting. An explicit `WORKSPACE`
bypasses selection. Runtime custody remains controlled independently by
`--home` and defaults to `~/.openrund`.

Use `execute_cli(args, service)` for a structured `OperatorResult`, `run_cli`
for rendered library output, and `run_cli_process` for process-level assembly.

Exit classes are stable: `0` success, `2` usage, `3` not found, `4` Engine
rejection, `5` integrity failure, `6` unavailable local custody, and `70`
internal failure. Cancellation and process interrupts are not converted into
ordinary command failures.

## Bundles and Views

The root package exports `export_bundle`, `verify_bundle`, `replay_bundle`,
`import_bundle`, `assess_resume`, and their immutable results. It also exports
`rebuild_views`, whose complete result contains Run status/readiness, Waits,
Action receipts and reconciliation, Artifact index, Checks, Checkpoints,
Delegation, timeline, and Reports at a known watermark.

Bundle verification is fail-closed. Import and resume assessment are custody
operations, not authority decisions.

## Extension protocols

`openrund.ports` defines static structural protocols for Events, Artifacts,
Leases, providers, Capabilities, clocks, IDs, and reporters. Protocols do not
contain methods that decide legality or grant Authority. Test-only in-memory
adapters remain under `openrund._testing` and are not exported from the package
root.
