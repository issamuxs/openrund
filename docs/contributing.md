# Contributing

OpenRund favors a small, strict control surface. Contributions must preserve
the ontology, Engine authority, deterministic replay, and explicit effect
boundaries.

## Development setup

This section is the canonical source for the complete ordered local quality
and release command sequence.

```sh
uv sync
```

Normal verification is offline:

```sh
uv run coverage run -m pytest -q
uv run coverage report
uv run mypy --strict src/openrund tests examples
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv lock --check
uv build
git diff --check
```

Live provider tests are opt-in and require explicitly supplied credentials:

```sh
uv run pytest -m live_provider
```

Provider constructors never read ambient credentials. Do not place secrets in
fixtures, command output, exception detail, or committed configuration.

## Authority rules

- Providers return parsed proposals; they do not append Events.
- Capability workers return `CapabilityResult`; they do not append Events.
- CLI mutations call `OperatorService`, which submits Commands to the Engine.
- Views derive facts; they do not decide legality.
- Reports and Receipts explain history; they do not create history.
- Configuration can register reachability but cannot grant runtime Authority.

Any new mutation path must have an explicit Command operation, legality rule,
canonical decision evidence, Event materialization, replay coverage, and
negative tests proving rejected work has no target lifecycle Events.

## Naming rules

Bare nouns are reserved for canonical concepts:

```text
Run Command Event Message ModelCall Action Wait Delegation Check Checkpoint
Annotation Artifact Capability Authority Lease Bundle View
```

Derived or explanatory surfaces should use explicit suffixes such as `View`,
`Report`, `Receipt`, `Summary`, `Assessment`, `Manifest`, `Snapshot`, `Index`,
`Entry`, or `Issue`.

Prefer `StatusView` to `StateView`, `Checkpoint` to `Boundary`, `Issue` to
`Blocker`, and `Entry` to `Record` when the type is not canonical runtime
history.

## Tests

Keep tests deterministic and scoped to the contract under change. Use injected
clocks, typed ID factories, in-memory adapters, and controlled transports.
Cover success plus stale position, duplicate identity, cancellation, malformed
input, storage failure, unknown outcome, and terminal-state behavior when those
cases apply.

Installed-package behavior must be tested from a built wheel without the source
tree on `PYTHONPATH`. CLI tests must assert both structured results and exit
behavior. Documentation examples and links are part of the release gate.

## Documentation

- Live documentation describes only the current Python product.
- Examples use current exported names and executable commands.
- CLI interaction is documented and tested as a normal runtime surface.
- OpenRund has no graphical interface or separate interface specification.
- Update the relevant contract page and link tests with every public change.

## Demonstration

Run the public end-to-end proof non-interactively with isolated explicit roots:

```sh
uv run openrund --home .local/openrund/runtime --json \
  demo governed-coding .local/openrund/workspace
```

The demo must use the production local assembly, remain offline and free of
ambient credentials, and execute from an installed wheel. Do not inject
demo-only clocks, identity factories, timing sources, stores, or transports.
It is the single public proof of Engine legality, all built-in Capability
boundaries, reconciliation, Delegation, Checks, and Bundle portability.
For the normal operator experience, omit `--json` and the workspace argument;
the CLI proposes the generated Run's default workspace before execution.

## Release readiness

A release candidate must pass the full test, typing, lint, format, lock,
coverage, package-content, documentation/link, security, installed-demo,
wheel/sdist, and supported-Python gates with a clean worktree. Optional live
provider checks run only in an explicitly credentialed environment.
