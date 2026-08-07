# Capabilities

A Capability is an executable interface invoked through an Action. This page
defines registration, transports, results, and the built-in implementations.
[Control](./control.md#external-effects) defines the governing Action lifecycle.

## Capability Contract

```text
ModelCall or API proposes Action
  -> Command
  -> Engine evaluates legality and produces CommandDecision
  -> accepted Command produces action.created
  -> ActionRunner submits a start Command
  -> Engine commits action.started
  -> worker receives CapabilityInvocation
  -> worker returns CapabilityResult
  -> ActionRunner stores inline Artifact bytes
  -> Engine materializes Artifact and terminal Action Events
```

Workers return bounded data. They do not construct Event envelopes, grant
Authority, decide Run state, mutate Views, or append Events.

## Capability Definition

Capability definitions include:

- `capabilityID`
- version
- action definitions
- input/output schemas
- `CapabilityAccessMode`
- `CapabilityReliability`
- operation-batch metadata
- Artifact specs
- transport config

Python hosts construct immutable `Capability`, `CapabilityAction`, and related
contract values. A `RegisteredCapability` pairs every declared action with one
live transport binding. `CapabilityRegistry` rejects duplicate Capability IDs,
missing or duplicate bindings, unsupported schemas, transport mismatches,
undeclared Artifact kinds, missing required Artifacts, and invalid result
shapes before they can cross into runtime history.

The two transport kinds are:

- `InProcessTransport`, for a typed async handler in the host process;
- `StdioJsonRpcTransport`, for one strict JSON-RPC request to one isolated
  worker process.

The stdio transport uses an absolute executable, explicit cwd and environment,
bounded stdout/stderr, a timeout, exact response keys, and result-only codecs.
Cancellation terminates and reaps the worker. A worker error is a structured
`CapabilityExecutionError`; a lost or malformed transport is ambiguous after
dispatch and therefore produces `action.unknown`, never a fabricated failure.

`CapabilityAccessMode` constrains how an Action may interact with external
resources: `read`, `write`, or `read_write`. `CapabilityReliability`
communicates expected execution semantics, including pure or read-only work,
idempotent mutation, externally transactional mutation, compensatable mutation,
irreversible mutation, and interruptible work.

## CapabilityResult

`CapabilityResult` may include:

- `output`
- `preview`
- `effects`
- `evidence`
- `inlineArtifacts`
- `artifactIDs`
- `metadata`

The Engine decides how worker output becomes Events and Artifacts.

Effects describe claimed external mutations or observations produced by the
Capability. Evidence supports those claims but does not itself authorize or
guarantee legality.

Capability execution contributes evidence, Artifacts, and outcome semantics
that the Engine uses alongside Checks and contracts to evaluate completion
legality.

Inline Artifact bytes are written before the terminal Action Command. Their
stored byte length and SHA-256 digest must match the `artifact.created` fact.
If custody or transport becomes ambiguous after `action.started`, the Action is
unknown until an operator or recovery Command supplies evidence-backed
reconciliation.

## Built-In Capabilities

### Filesystem

`FilesystemCapability` exposes read, list, stat, write, update, delete, move,
and diff. Hosts grant named `FilesystemMount` roots with read, write, or
read-write access. Relative portable paths are inspected component by
component; traversal, absolute paths, platform-confused paths, symlinks, mount
substitution, and non-file mutation targets fail closed.

Reads and directory listings are bounded. Existing-content mutation requires
an expected SHA-256 value and explicit overwrite intent where applicable.
Writes use a same-directory staged file, fsync, atomic replace, and directory
sync. Delete is file-only and non-recursive. Move never falls back to a
cross-device copy. Mutations and diffs return compact evidence and immutable
receipt or diff Artifacts.

### Markdown Documents

`DocumentsCapability` exposes Markdown read, whole write, heading discovery,
frontmatter read/set, exact section read/replace, one-based range replacement,
append, and ordered structured patch operations. It always crosses the generic
stdio transport to `openrund.capabilities.documents_worker`.

The worker receives only explicit mount roots and byte limits. It repeats root,
path, symlink, UTF-8, size, frontmatter, heading ambiguity, range, patch overlap,
and expected-hash checks independently. Reads return Markdown Artifact bytes;
mutations return before/after hashes and bounded unified-diff Artifacts. The
worker cannot import or append Events.

### Process

`ProcessCapability` accepts a named `ProcessBinding`, not an arbitrary command
path. Each binding pins one absolute non-symlink executable identity and may
provide fixed environment values plus explicitly enumerated caller-selectable
values. Children receive no ambient environment, credentials, `PATH`, or
shell. Arguments, stdin, cwd, timeout, retained output, and previews are
bounded.

Stdout and stderr are always drained and hashed over their complete streams;
only bounded prefixes are retained as Artifacts. Exit, signal, timeout, byte
count, digest, and truncation metadata remain explicit. Timeout and runtime
cancellation terminate, escalate to kill if needed, and reap the child before
control returns.

### Git

`GitCapability` exposes exactly status, diff, head, apply, stage, and commit for
a verified local repository. It uses one pinned Git executable through the
bounded process substrate. The repository and `.git` directory must remain
inside a writable named mount; symlinked Git metadata, object alternates, and
configuration capable of invoking helpers or external configuration are
rejected.

The child receives no inherited credentials or configuration, and fixed flags
disable remote protocols, prompts, pagers, signing, editors, hooks, external
diff drivers, and text conversion. Apply checks bounded patch bytes before
mutation. Stage accepts explicit portable non-option paths, reads regular files
without following links, hashes raw bytes without clean filters, and updates
the index directly. Commit messages travel on stdin and identities are selected
from named host configuration. Status and diff output are hash-bound, bounded
Artifacts. No remote, fetch, pull, push, config, submodule, or credential action
exists.

## Errors And Lifetimes

Capability configuration and untrusted value errors use stable safe OpenRund
exceptions. Worker stderr, local paths, credentials, provider bodies, and raw
subprocess failures are not copied into caller-visible messages. Handler and
transport APIs are async. Process-owning transports and handlers clean up their
child before propagating timeout or cancellation; resource ownership never
falls to the Engine or a derived View.

## Operation Batches

Operation batching is restricted to low-risk Capability operations that do not
require approval, do not mutate governed resources, and do not bypass runtime
legality evaluation. Batched operations still require schema-valid inputs,
Authority-reachable Actions, trusted Capability metadata, and policy allowance.
