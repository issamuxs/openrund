# Quickstart

This guide creates a durable local Run, inspects its replayed state, exports a
portable Bundle, and runs the complete governed-coding demonstration.

## Install

OpenRund supports Python 3.12 and newer.

```sh
python -m pip install openrund
```

## Assemble and inspect a Run

The local assembly requires an explicit runtime home. An assembly with no
mounts has no built-in Capabilities and grants no Authority.

```python
import asyncio
from pathlib import Path

from openrund import LocalAssemblyConfig, RunId, create_local_runtime
from openrund.operator import RunInspectionData


async def main() -> None:
    runtime = create_local_runtime(
        LocalAssemblyConfig(runtime_home=Path(".openrund"))
    )
    async with runtime:
        created = await runtime.operator.create_run(
            RunId(value="run_quickstart"),
            title="Quickstart",
            objective="Prove durable local custody",
        )
        inspected = await runtime.operator.inspect_run(
            RunId(value="run_quickstart")
        )
        assert created.ok
        if not inspected.ok or not isinstance(inspected.data, RunInspectionData):
            raise RuntimeError("Run inspection failed")
        print(inspected.data.status)


asyncio.run(main())
```

`create_local_runtime` wires SQLite Event, Artifact, and Lease custody,
`RuntimeEngine`, replay Views, `ActionRunner`, and `OperatorService`. It does not
synthesize Authority. Advanced hosts may construct the Engine from the
structural protocols in `openrund.ports`.

## Use the command line

The installed command returns deterministic text by default and canonical JSON
with `--json`.

```sh
openrund --home .openrund runs create run_cli --title "CLI run"
openrund --home .openrund --json runs inspect run_cli
openrund --home .openrund runs timeline run_cli
openrund --home .openrund runs readiness run_cli
```

Bundle operations use the same operator service:

```sh
openrund --home .openrund bundles export run_cli ./run_cli.orun
openrund bundles verify ./run_cli.orun
openrund bundles replay ./run_cli.orun
openrund --home ./import-home bundles import ./run_cli.orun
```

For a Bundle that requires external roots, pass explicit mappings such as
`--map workspace=/absolute/path`. Verification always precedes replay or import.
Import stages verified evidence atomically and never resumes a Run or grants
Authority automatically.

## Run the complete demonstration

```sh
openrund demo governed-coding
```

In an interactive text terminal, OpenRund displays the generated Run's default
workspace under `~/.openrund/runs/<runID>/workspace`; press Enter to accept it
or enter another path. JSON and non-interactive execution never prompt and use
that default. Append `WORKSPACE` to select a path explicitly, and use
`--home PATH` only when private runtime custody should live elsewhere.

The demonstration is offline and uses the production local assembly, including
normal UUID-backed runtime identities, system timestamps, process timing,
SQLite custody, and built-in Capability transports. It proves:

1. a filesystem mutation is rejected before Capability Authority exists;
2. a legal write is deferred by policy, approved, and resumed through the
   Engine;
3. filesystem, transported Markdown documents, bounded process, and Git
   Capabilities execute through `ActionRunner`;
4. an ambiguous Action becomes unknown and is reconciled with evidence;
5. a bounded child Run hands off and satisfies a join Wait;
6. completion is rejected until the required semantic Check passes; and
7. the terminal Run is explained and transported through the full `.orun`
   lifecycle.

The runtime never reads provider credentials for this demonstration, and all
effect roots and executables are explicit.

## Next steps

- Read [Control](./control.md) before granting Authority.
- Use [API](./api.md) for the operator and CLI command matrix.
- Use [Capabilities](./capabilities.md) to configure roots and executables.
- Use [Bundles](./bundles.md) for portability and recovery rules.
