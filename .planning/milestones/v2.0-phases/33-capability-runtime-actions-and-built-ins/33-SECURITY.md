---
phase: 33
slug: capability-runtime-actions-and-built-ins
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-05
---

# Phase 33 — Security

## Trust Boundaries

| Boundary | Description | Data Crossing |
|---|---|---|
| Engine → Action runner | Dispatch begins only after accepted Action creation and durable start facts. | identity, capability/action name, frozen input |
| Action runner → Capability | Registered definitions and schemas constrain in-process or stdio invocation. | invocation, cancellation, timeout |
| Capability → Action runner | Results are untrusted data until exact validation and Artifact custody complete. | output, effects, evidence, Artifact material |
| Named mount → filesystem | Lexical and real-path containment, no-follow opens, hashes, and atomic replacement protect host paths. | relative paths and bytes |
| Runtime → subprocess | Executables, arguments, environment, output, deadlines, and cancellation are bounded. | process invocation and streams |
| Runtime → local repository | Fixed Git verbs run without ambient configuration, credentials, helpers, hooks, signing, remotes, or filters. | repository paths, patches, staged bytes |
| Runtime → documents worker | Strict line-delimited JSON-RPC frames cross one root-bound stdio process. | Markdown operations and results |

## Threat Register

| Threat ID | Category | Component | Severity | Mitigation | Status |
|---|---|---|---|---|---|
| T-33-01 | Elevation of Privilege | Action dispatch | critical | Engine acceptance and durable `action.started` precede dispatch; changed input is rejected. | closed |
| T-33-02 | Tampering | Capability result | critical | Closed result codec; capabilities cannot return or append Events; Artifact bytes are hashed before facts commit. | closed |
| T-33-03 | Repudiation | Action lifecycle | high | Exact terminal state, replay receipts, cancellation reliability, and explicit unknown/reconciliation episodes are tested. | closed |
| T-33-04 | Path Traversal | Filesystem/documents | critical | Named roots, portable relative paths, symlink rejection, no-follow access, and real containment fail closed. | closed |
| T-33-05 | Time-of-check/time-of-use | Filesystem mutation | high | Expected hashes are rechecked immediately before same-directory atomic replacement; overwrite policy is explicit. | closed |
| T-33-06 | Command Injection | Process | critical | No shell interpolation; pinned executable bindings, bounded arguments, scrubbed environment, timeout, and process-group cancellation. | closed |
| T-33-07 | Information Disclosure | Process output | high | Stream byte limits, full-stream hashes, bounded previews, and Artifact-backed bodies prevent Event bloat and uncontrolled disclosure. | closed |
| T-33-08 | Elevation of Privilege | Git | critical | Fixed local verbs, clean environment, rejected remotes/credentials/config includes/helpers/hooks/signing/filters/alternates. | closed |
| T-33-09 | Protocol Injection | stdio worker | high | One-request/one-response strict JSON framing, schema validation, stderr isolation, timeout, and malformed-frame rejection. | closed |
| T-33-10 | Architectural bypass | Imports/package | critical | AST import fences and installed-wheel tests keep effects outside Engine/Event custody and prevent source-only behavior. | closed |

## Accepted Risks Log

No accepted security risks. Hosts must choose trustworthy root directories; concurrent privileged mutation of the host filesystem outside OpenRund's custody is outside the local runtime threat model.

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|---|---:|---:|---:|---|
| 2026-08-05 | 10 | 10 | 0 | Codex inline security verification |

## Sign-Off

- [x] All threats have a disposition.
- [x] Accepted risks are documented.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set in frontmatter.

**Approval:** verified 2026-08-05
