# Phase 33: Capability Runtime, Actions, and Built-ins — Research

**Researched:** 2026-08-05  
**Scope:** Normative repository documentation and the implemented Python contracts, Engine, storage, and Views. External research is unnecessary because this phase implements a local repository-defined protocol using standard Python facilities.

## Recommendation

Add an explicit executable Capability layer above the Engine. A registry binds validated inert definitions to transports. An `ActionRunner` submits a trusted start Command, invokes exactly one selected action, validates its result, stores inline Artifact bytes, and submits exactly one completed, failed, cancelled, or unknown terminal Command. Concrete built-ins remain transport handlers and have no EventStore access.

## Registration And Schema Boundary

Definitions must describe access posture, reliability, batching eligibility, cancellation support, produced Artifact kinds, and an explicit transport kind. Keep semantic definitions serializable; keep live Python callables in registry bindings, not metadata. Reuse the Engine's closed schema subset so governance and execution cannot disagree. Validate both invocation data and result output.

## Action Custody

Phase 32 makes `action.created` durable only after legality and Authority pass. Phase 33 adds a start operation legal only for a pending created Action and trusted Capability/System origin. Completion materializes compact output, effects, evidence, and Artifact references. Failure carries a structured safe error. Cancellation is terminal only when declared interruptible and confirmed by the transport. Timeout, broken pipe, malformed reply after dispatch, or worker crash has an uncertain external-effect boundary and must produce `action.unknown` when work might have started.

Artifact bytes are not Event payloads. The runner assigns IDs, computes hashes/length, writes immutable blobs, then submits terminal Artifact facts and the Action outcome together. If the Event append loses a race, immutable orphan recovery remains possible and the Action history does not claim bytes that were never stored.

## Stdio Protocol

Use one JSON-RPC 2.0 request and response per worker process over UTF-8 newline-delimited JSON. Reject duplicate/unknown top-level keys, wrong protocol/version/id, notifications, batches, non-object params/results, oversized frames, trailing protocol output, non-UTF-8 data, malformed errors, and Event-like result fields. Pass a minimal explicit environment, close stdin after the request, drain bounded stdout/stderr, enforce a timeout, and terminate then kill on cancellation if necessary. Encode inline Artifact bytes as strict base64 in the transport codec.

## Filesystem Sandbox

Mounts have stable names, concrete absolute roots, and read or read-write posture. User paths are non-empty portable POSIX relative paths with no `..`, NUL, backslash, drive, or leading slash. Resolve the root once. For reads, validate every existing component and require the final real path to remain contained. For mutations, reject symlinks in every existing component, create parents only when explicitly requested, and never recursively delete directories.

Read/list/stat return bounded data and hashes. Large bytes become Artifacts. Write/update use temporary files in the target directory, flush/fsync, then replace; update requires an expected hash. Move stays within governed mounts and uses atomic replace only; cross-device fallback is rejected. Diff is deterministic unified text evidence.

## Markdown Worker

Keep Markdown handling inside the generic stdio boundary. The worker receives a configured root and relative path, revalidates confinement itself, decodes UTF-8, and implements read, whole write, frontmatter read/set, heading/section read/replace, line/range replacement, append, and ordered structured patches. Every mutation supports expected hash and returns before/after hashes plus a unified diff Artifact. A small deterministic frontmatter subset is sufficient without third-party dependencies.

## Process And Git

Process execution binds logical executable names to explicit executable paths. Inputs may supply arguments, relative cwd, bounded stdin, timeout, and an environment subset allowed by host configuration. The default shell is disabled and inherited environment is not exposed. Stdout/stderr are bounded, hashed, and emitted as Artifacts when non-empty or truncated. Cancellation cleans up the child process.

Git runs one configured executable under a verified repository root with a closed operation-to-argument mapping. Permit status, diff, head, apply, stage, and commit only. Reject option-like stage paths and paths outside the repository. Disable terminal prompting, hooks, pager/editor, system/global config, remote verbs, and credential helpers. Diff/status output belongs in Artifacts rather than large Action payloads.

## Verification Strategy

Use focused malicious-input and lifecycle tests per built-in, then an integration test that proves an accepted Action is started before a handler observes it and receives one replayable terminal result. Finish with all capability/engine/storage/view tests, full pytest, strict mypy, Ruff, lock/build, installed-wheel typing and subprocess-worker tests, documentation/link checks, code review, security audit, and Nyquist validation.
