# OpenRund

OpenRund is a Python runtime for durable agent runs that perform consequential
work. Callers propose mutations; the runtime validates authority, policy,
contracts, and current Run state before committing them to immutable history.

Use it when an agent may edit files, run processes, create artifacts, delegate
work, or perform another effect that must remain auditable across retries,
crashes, and uncertain external outcomes.

## What the runtime guarantees

- Model output is a proposal, not authority.
- Only the Engine decides whether a Run mutation is accepted.
- Approval cannot make an illegal operation legal.
- External outcomes remain unknown when the runtime cannot prove success or
  failure.
- Views are rebuilt from immutable Events.
- Run completion is checked by the runtime.

[Control](./docs/control.md) defines these semantics. [Concepts](./docs/concepts.md)
defines the vocabulary.

OpenRund has no graphical interface. The Python API and installed `openrund`
command use the same Engine and storage boundaries.

## Install

OpenRund requires Python 3.12 or newer.

```sh
python -m pip install openrund
```

From a repository checkout:

```sh
uv sync
uv run pytest -q
```

## Run the demonstration

```sh
openrund demo governed-coding
```

The demo uses the production local assembly and runs offline. It covers
authority rejection, approval, built-in Capabilities, and
unknown-outcome reconciliation, Delegation, completion Checks, and the complete
Bundle lifecycle.

Runtime custody defaults to `~/.openrund`. In an interactive terminal, the
command proposes a workspace for the new Run; press Enter to accept it or enter
another path. For scripts, pass an explicit workspace or use `--json` to accept
the default without prompting:

```sh
openrund --json demo governed-coding ./demo-workspace
```

Use `--home PATH` only to change private runtime custody.

## Basic CLI flow

```sh
openrund --home .openrund runs create run_example --title "Example run"
openrund --home .openrund runs inspect run_example
openrund --home .openrund runs timeline run_example
openrund --home .openrund bundles export run_example ./run_example.orun
openrund bundles verify ./run_example.orun
```

Add `--json` for machine-readable output. See [API and CLI](./docs/api.md) for
the command reference and exit codes.

## Documentation

- [Documentation index](./docs/README.md)
- [Quickstart](./docs/quickstart.md)
- [Control](./docs/control.md)
- [Architecture](./docs/architecture.md)
- [API and CLI](./docs/api.md)
- [Contributing](./docs/contributing.md)
- [Security policy](./SECURITY.md)

For the complete development checks, see
[Development setup](./docs/contributing.md#development-setup).
