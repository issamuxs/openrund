---
phase: 31
slug: engine-authority-and-core-run-semantics
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-05
---

# Phase 31 — Security

> Per-phase security contract for Engine authority, durable Command evidence, lifecycle legality, and proposal isolation.

## Trust Boundaries

| Boundary | Description | Data Crossing |
|---|---|---|
| Host → Engine | A trusted host submits typed Commands from user, client, operator, timer, capability, delegation, model, system, or recovery origins. | Command identity, origin, operation, Content, metadata |
| Provider adapter → Engine | Parsed model output crosses as an untrusted proposal and inert Command, never as an Event. | ModelProposal, provider identity, ModelCall identity |
| Engine → EventStore | The sole supported authority writes one expected-position batch after complete replay and legality evaluation. | Command evidence and accepted lifecycle Events |
| EventStore → Engine | Durable history is untrusted until exact contiguous replay has been proven. | Ordered Events and watermark |
| Engine → inspection | Callers receive immutable Command results; durable inspection remains Event/View based. | Decision, trace, result Event IDs, replacement link |

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|---|---|---|---|---|---|---|
| T-31-01 | Elevation of Privilege | Public Engine API | high | mitigate | Exact export and method-surface tests leave `submit` as the only public mutation method. | closed |
| T-31-02 | Elevation of Privilege | Provider proposal | high | mitigate | Proposal adapters construct inert model-origin Commands and delegate to Engine. | closed |
| T-31-03 | Tampering | History replay | high | mitigate | Full position-one read and exact-watermark View reconstruction fail closed on gaps, ordering defects, or mixed history. | closed |
| T-31-04 | Tampering | Concurrent mutation | high | mitigate | Expected-position append, bounded conflict retries, and complete re-evaluation prevent stale legality commits. | closed |
| T-31-05 | Repudiation | Mutation attempt | high | mitigate | Every successful attempt append starts with one immutable `command.recorded` Event. | closed |
| T-31-06 | Tampering | Accepted target | high | mitigate | Command evidence and all accepted target Events are committed in one ordered atomic batch. | closed |
| T-31-07 | Elevation of Privilege | Rejected/superseded attempt | high | mitigate | Denied branches carry absent target evidence and materialize no lifecycle Event. | closed |
| T-31-08 | Repudiation | Duplicate Command retry | high | mitigate | Durable Command-ID lookup reconstructs the committed result without a second append. | closed |
| T-31-09 | Denial of Service | Idempotency retry | high | mitigate | Only non-superseded records own a key; every later collision links to the original owner. | closed |
| T-31-10 | Tampering | Idempotency corruption | high | mitigate | Multiple distinct non-superseded owners fail closed as storage-integrity corruption. | closed |
| T-31-11 | Elevation of Privilege | Terminal Run | high | mitigate | Every operation after completed, failed, or cancelled state is durably rejected. | closed |
| T-31-12 | Repudiation | Completion | high | mitigate | Pending Waits, missing Artifacts, unresolved Action outcomes, and unsatisfied Checks produce explicit trace entries. | closed |
| T-31-13 | Tampering | Message/ModelCall entity state | high | mitigate | Unknown Message IDs, duplicate ModelCalls, and invalid terminal transitions are rejected from replay facts. | closed |
| T-31-14 | Information Disclosure | Failure evidence | high | mitigate | Stable failure classifications and governed Content carry evidence; storage failures are not fabricated as domain decisions. | closed |
| T-31-15 | Tampering | Content commitment | high | mitigate | SHA-256 is computed over the single canonical Content encoding boundary. | closed |
| T-31-16 | Spoofing | Origin evidence | high | mitigate | Full CommandOrigin is preserved in compact metadata and model/runtime payload fields retain actor/provider identity. | closed |
| T-31-17 | Elevation of Privilege | Lower-layer imports | high | mitigate | Provider, capability, storage, and View layers cannot import Engine authority. | closed |
| T-31-18 | Tampering | Frozen compatibility | high | mitigate | A closed authenticated allowlist proves exact Event/decision bytes with no fixture-update path. | closed |

## Accepted Risks Log

No accepted risks. Hosts are inside the trusted composition boundary; applications must not hand raw storage adapters to untrusted extensions.

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|---|---:|---:|---:|---|
| 2026-08-05 | 18 | 18 | 0 | Codex inline security verification |

The Phase 31 implementation was checked against its planned authority and recovery failure modes. The code-review idempotency finding was fixed and the complete post-fix release gate passed, so no high-or-greater threat remains open.

## Sign-Off

- [x] All threats have a disposition.
- [x] Accepted risks are documented.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set in frontmatter.

**Approval:** verified 2026-08-05
