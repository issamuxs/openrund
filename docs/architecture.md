# Architecture

This page owns the package map and dependency wiring. [Control](./control.md)
owns mutation semantics; the contract pages own Event, Capability, provider,
Delegation, storage, and Bundle details.

## System shape

```text
provider / API / timer / capability / operator / recovery
                    |
                 Command
                    v
             RuntimeEngine.submit
                    |
              read EventStore
                    |
              rebuild Views
                    |
             evaluate legality
                    |
             CommandDecision
                    |
              append Events

action.created -> ActionRunner -> Capability transport -> CapabilityResult
                       |                                  |
                       +------ terminal Command ----------+
```

Only the Engine evaluates Run mutations and materializes lifecycle Events.
`ActionRunner`, providers, operators, the CLI, storage adapters, and Views sit
outside that boundary.

## Package map

| Package | Responsibility |
|---|---|
| `openrund.contracts` | Immutable IDs, Commands, Events, Runs, content, Capability, and Bundle values |
| `openrund.codec` | Exact v1 JSON and Event encoding, decoding, and commitments |
| `openrund.ports` | Structural protocols for storage, providers, Capabilities, time, IDs, and reporting |
| `openrund.engine` | Command attempts, legality, decisions, and lifecycle Event materialization |
| `openrund.views` | Complete-watermark replay into derived Run views |
| `openrund.storage` | SQLite Event, Artifact, and Lease custody plus Run-home paths |
| `openrund.runtime` | Durable ModelCall lifecycle and proposal submission |
| `openrund.providers` | HTTP/SSE adapters that normalize provider output into Operations |
| `openrund.capabilities` | Registration, Action execution, transports, confinement, and built-ins |
| `openrund.operator` | Typed host operations for mutation, inspection, evidence, and Bundles |
| `openrund.bundles` | Export, verification, replay, import, and resume assessment |
| `openrund.assembly` | Local composition and resource ownership |
| `openrund.cli` | Argument parsing and text/JSON rendering over operator results |
| `openrund.demo` | Offline end-to-end governed-coding scenario |

## Command path

`RuntimeEngine.submit` reads one Run's full Event history, rebuilds Views once,
loads Operation-specific facts, evaluates legality, and appends
`command.recorded` plus any allowed target Events. It retries the whole attempt
after an expected-position conflict.

The Engine receives narrow dependencies rather than a general service
container. Its Event store is private, and it exposes no raw append method.

## Model path

`DurableRunLoop` records `model_call.started` before provider I/O. It then
records exactly one completed, failed, or cancelled ModelCall outcome. A
successful provider response is normalized to an Operation and submitted as a
separate model-origin Command.

Provider success does not imply Command acceptance. Provider adapters cannot
append Events or access storage custody.

## Action path

`ActionRunner.execute` receives a `CapabilityInvocation` for a created Action.
It resolves and validates the route, then asks the Engine to start the Action.
It dispatches only after `action.started` is durable. The transport returns
data; the runner stores inline Artifacts and submits one terminal Command.

The Engine owns Action lifecycle history. Workers own domain execution. Neither
side assumes the other's responsibility.

## Delegation path

Delegation establishment uses an atomic multi-Run append for:

- the parent Command and Delegation Events;
- the child Run's creation and start Events;
- the child's bounded Authority grants.

Handoff and parent cancellation read the relevant child histories and use the
same atomic custody where multiple streams change. See
[Delegation](./delegation.md) for contract and join rules.

## Read path

`rebuild_views` requires complete, contiguous Event history at a known
watermark. The Engine uses those Views during a Command attempt; the operator
service uses them for inspection, readiness, timelines, waits, receipts, and
reports.

Views are disposable. Event and Artifact custody remains canonical.

Bundle export reads Events, Artifacts, and derived surfaces without entering the
Engine mutation path. Verification and replay are read-only. Import publishes
verified portable evidence under separate custody and does not resume a Run.

## Resource ownership

`LocalRuntime` composes SQLite stores, the Engine, operator service,
`ActionRunner`, Capability registry, and optional durable model loop. It is an
async context manager with an idempotent close operation.

Closing it closes the model loop, Engine, and SQLite stores in dependency order.
Components that own tasks, sockets, or subprocesses cancel and drain them.
Cleanup responsibility does not move into the Engine.

OpenRund has no graphical interface. The CLI is an adapter over
`OperatorService`, not a separate execution path.
