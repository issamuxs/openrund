---
phase: 34
slug: providers-and-durable-run-loop
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-06
---

# Phase 34 — Security

## Trust Boundaries

| Boundary | Description | Data Crossing |
|---|---|---|
| Host → provider | Explicit endpoint, model, credentials, tools, context, and bounds configure one adapter. | request configuration |
| Network → HTTP/SSE | All status, headers, frames, bytes, and JSON are untrusted and bounded. | remote response |
| Provider → proposal | Remote text and tool calls normalize to typed inert operations. | ModelProposal |
| Durable loop → Engine | Lifecycle and proposal Commands enter the sole mutation authority. | system and model-origin Commands |
| Context exit → resources | Active sockets, tasks, stores, and workers must close without orphans. | cancellation and closure |

## Threat Register

| Threat ID | Category | Component | Severity | Mitigation | Status |
|---|---|---|---|---|---|
| T-34-01 | Spoofing | ModelCall identity | high | Local request identity is authoritative; remote response IDs are bounded metadata only. | closed |
| T-34-02 | Elevation of Privilege | Provider proposal | critical | Provider returns no Events or decisions; every proposal becomes a model-origin Engine Command. | closed |
| T-34-03 | Information Disclosure | Credentials/errors | critical | Explicit credentials only; no ambient reads; URLs with userinfo rejected; remote bodies discarded from safe errors. | closed |
| T-34-04 | Injection | HTTP headers/target | critical | Header names/values, reserved headers, URL scheme, authority, target, and control characters are validated. | closed |
| T-34-05 | Denial of Service | HTTP/SSE parsing | high | Overall timeout plus bounded headers, body bytes, chunks, SSE events, JSON, and connection-close lifetime. | closed |
| T-34-06 | Tampering | HTTP framing | high | Conflicting length/chunking, unsupported transfer encodings, truncation, invalid chunks, and malformed trailers fail closed. | closed |
| T-34-07 | Injection | Tool arguments | critical | Present arguments must be JSON objects; malformed/non-object/duplicate data fails as parse evidence. | closed |
| T-34-08 | Repudiation | ModelCall lifecycle | high | Start commits before I/O and exactly one complete/fail/cancel terminal fact commits. | closed |
| T-34-09 | Denial of Service | Cancellation | high | Cancellation recording is shielded; active requests/tasks/processes are cancelled, drained, and reaped. | closed |
| T-34-10 | Architectural bypass | Imports | critical | AST fences prohibit provider EventStore, ArtifactStore, storage, concrete capability, and append authority. | closed |

## Accepted Risks Log

No accepted security risks. TLS trust uses the host Python trust store. Provider availability, pricing, model behavior, and configured endpoint trust remain host deployment concerns rather than runtime Authority.

## Sign-Off

- [x] All threats have a disposition.
- [x] Accepted risks are documented.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set in frontmatter.

**Approval:** verified 2026-08-06
