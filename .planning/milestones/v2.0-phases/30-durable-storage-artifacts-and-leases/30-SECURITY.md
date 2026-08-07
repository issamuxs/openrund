---
phase: 30
slug: durable-storage-artifacts-and-leases
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-05
---

# Phase 30 — Security

> Per-phase security contract for durable local custody, coordination, and compatibility evidence.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|---|---|---|
| Host → storage ports | Callers provide typed Events, Artifacts, Lease inputs, IDs, timestamps, and local roots. | Runtime facts, immutable content, coordination identity, local paths |
| Storage adapters → SQLite | Private short-lived connections persist ordered history, Artifact metadata, and active Leases. | SQL parameters and domain-valued rows |
| Artifact adapter → local filesystem | The adapter stages, publishes, verifies, quarantines, and recovers immutable blob bytes. | Artifact bytes, relative blob references, filesystem metadata |
| Frozen evidence → compatibility tests | Authenticated read-only files define the retained SQLite compatibility surface. | Schema records, representative rows, hashes |
| Durable Event store → subscribers | Committed Event tuples are delivered only after successful persistence. | Immutable committed Events and sanitized failure facts |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|---|---|---|---|---|---|---|
| T-30-01 | Tampering | SQLite migration/transaction | high | mitigate | Versioned immediate migrations, explicit rollback, schema validation, and injected-failure tests. | closed |
| T-30-02 | Denial of Service | SQLite writer coordination | high | mitigate | Validated finite busy timeout and typed bounded busy outcomes. | closed |
| T-30-03 | Information Disclosure | Storage errors | high | mitigate | Stable typed error translation plus path/content/SQLite leakage assertions. | closed |
| T-30-04 | Tampering | Lease renewal/release | high | mitigate | Exact opaque token, Lease ID, Run, and owner fences on conditional operations. | closed |
| T-30-05 | Tampering | Event append | high | mitigate | `BEGIN IMMEDIATE`, complete watermark comparison, and unique stream positions. | closed |
| T-30-06 | Tampering | Atomic multi-Run append | high | mitigate | Preflight all batches and insert them in one explicit transaction. | closed |
| T-30-07 | Tampering | Event read | high | mitigate | Whole-stream count/min/max validation plus ordered contiguous decode for every read cursor. | closed |
| T-30-08 | Spoofing | Global Event identity | high | mitigate | Input preflight, primary-key enforcement, rollback, and typed duplicate failure. | closed |
| T-30-09 | Repudiation | Post-commit callback | high | mitigate | Commit-first ordering always returns the original durable result despite ordinary observer failure. | closed |
| T-30-10 | Information Disclosure | Event subscriber | high | mitigate | Subscribers receive immutable Events only after the durable store reports success. | closed |
| T-30-11 | Elevation of Privilege | Event observer wrapper | high | mitigate | The wrapper exposes only EventStore operations and imports no Engine or Authority behavior. | closed |
| T-30-12 | Elevation of Privilege | Artifact paths | high | mitigate | Single-component IDs, relative exact blob paths, containment checks, no-follow open, and `fstat`. | closed |
| T-30-13 | Tampering | Artifact publication | high | mitigate | Exclusive staging, absent-only hard-link publication, and exact immutable comparisons. | closed |
| T-30-14 | Tampering | Artifact bytes | high | mitigate | Length and SHA-256 validation on write, descriptor-based read, and recovery. | closed |
| T-30-15 | Repudiation | Artifact split custody | high | mitigate | Named crash checkpoints and explicit idempotent stage/orphan/metadata recovery. | closed |
| T-30-16 | Spoofing | Active Lease holder | high | mitigate | Immediate transaction and unique one-per-Run constraint produce at most one active holder. | closed |
| T-30-17 | Tampering | Replacement Lease | high | mitigate | Replacement changes identity/token and stale renew/release requires the exact current fence. | closed |
| T-30-18 | Repudiation | Lease expiry | high | mitigate | Expiry is derived only from an explicit validated caller-supplied timestamp. | closed |
| T-30-19 | Elevation of Privilege | Lease API | high | mitigate | Coordination types and adapters expose no legality, grant, revoke, or permission operation. | closed |
| T-30-20 | Elevation of Privilege | Run-home construction | high | mitigate | IDs are revalidated as one safe component across POSIX and Windows separators/drives. | closed |
| T-30-21 | Elevation of Privilege | Run-home materialization | high | mitigate | Component-by-component lstat checks reject symlinks/non-directories and verify final containment. | closed |
| T-30-22 | Elevation of Privilege | Run-home values | high | mitigate | Pure layout values and explicit materialization confer no capability or Authority. | closed |
| T-30-23 | Repudiation | Compatibility inventory | high | mitigate | Exact 32-row manifest bijection with containment, size, and SHA-256 authentication. | closed |
| T-30-24 | Elevation of Privilege | Public storage API | high | mitigate | Exact exports, dependency/method fences, and no Engine/Authority/provider/capability/presentation imports. | closed |
| T-30-25 | Information Disclosure | Packaging boundary | high | mitigate | Installed-wheel strict typing, private infrastructure types, and sanitized public failures. | closed |
| T-30-26 | Tampering | Frozen evidence | high | mitigate | Before/after evidence-tree snapshots and temporary-copy-only tests; no update/generator path. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*  
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` count toward `threats_open`.*  
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party).*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|---|---:|---:|---:|---|
| 2026-08-05 | 26 | 26 | 0 | Codex inline security verification |

The Phase 30 threat register was authored during planning. With ASVS level 1, exact mitigation placement was verified from implementation/tests and the clean post-review release gate; the workflow's no-open-threat short-circuit therefore applies without a separate auditor.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer).
- [x] Accepted risks documented in Accepted Risks Log.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set in frontmatter.

**Approval:** verified 2026-08-05
