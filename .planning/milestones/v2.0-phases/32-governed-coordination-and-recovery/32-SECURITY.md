---
phase: 32
slug: governed-coordination-and-recovery
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-05
---

# Phase 32 — Security

## Trust Boundaries

| Boundary | Description | Data Crossing |
|---|---|---|
| Host/model → Engine | Typed Commands remain untrusted until origin and complete-replay legality checks pass. | Wait, approval, Action, recovery, Check, Authority, and Delegation operations |
| Governance context → Engine | Assembly-supplied Capability metadata and workspace/security facts constrain durable per-Run Authority. | schemas, roots, tenant, security context |
| Parent Run ↔ child Run | Delegation creation and cancellation cross streams only through one atomic custody boundary. | contracts, lineage, Authority, lifecycle facts |
| Child history → parent handoff | Child terminal history is evidence and cannot advance the parent without an explicit matching Command. | result, failure, cancellation, Artifacts |
| Frozen corpus → compatibility test | Evidence is inert until path, byte length, SHA-256, shape, and exact allowlist authentication succeeds. | v1 Event bytes and manifest commitments |

## Threat Register

| Threat ID | Category | Component | Severity | Mitigation | Status |
|---|---|---|---|---|---|
| T-32-01 | Elevation of Privilege | Approval | critical | Hard legality precedes policy; trusted origins only; resume repeats current legality. | closed |
| T-32-02 | Path Traversal | Resource scope | critical | Relative paths use the portable path boundary; absolute paths must be lexically contained under a clean configured root. | closed |
| T-32-03 | Elevation of Privilege | Authority | critical | Only operator, system, or recovery origins may grant or revoke registered Capability or policy Authority. | closed |
| T-32-04 | Tampering | Event custody | critical | Normal and atomic stores must be the same object; cross-stream append is expected-position atomic. | closed |
| T-32-05 | Tampering | Wait lifecycle | high | Stable identity, exact kind, trusted terminal origins, and one terminal fact are enforced. | closed |
| T-32-06 | Spoofing | Timer/join | high | Deadlines and replay-derived join satisfaction are checked before explicit terminal Commands commit. | closed |
| T-32-07 | Elevation of Privilege | Recovery | critical | Model origins cannot mark or reconcile outcomes; exact unknown episode and substantive evidence are required. | closed |
| T-32-08 | Repudiation | Check evidence | high | Model self-certification is rejected; counts, result shape, Artifact references, and named completion semantics are verified. | closed |
| T-32-09 | Elevation of Privilege | Delegation | critical | Child Authority, action/policy scope, budget, nesting, lineage, and Artifacts must narrow current parent facts. | closed |
| T-32-10 | Tampering | Delegation handoff | critical | Child identity, terminal status, result kind, required Artifacts, failure message, and cancellation reason must match exact child history. | closed |
| T-32-11 | Tampering | Parent cancellation | critical | Contract-bound child and parent terminal facts commit in one multi-stream transaction; missing custody fails closed. | closed |
| T-32-12 | Elevation of Privilege | Late handoff | high | Persisted ignore/surface/context policy may add evidence but never changes terminal parent state. | closed |
| T-32-13 | Tampering | Compatibility | critical | One closed 40-variant authenticated allowlist proves exact bytes, branches, presence, and links without regeneration. | closed |
| T-32-14 | Elevation of Privilege | Architecture | high | Import, API, effect, package, and method-surface fences preserve `RuntimeEngine.submit` as the sole authority. | closed |

## Accepted Risks Log

No accepted risks. Filesystem symlink containment and worker execution occur at the Phase 33 Capability adapter boundary and must remain independently fail closed there.

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|---|---:|---:|---:|---|
| 2026-08-05 | 14 | 14 | 0 | Codex inline security verification |

The code review exposed four high-impact boundary defects. All four were fixed with dedicated regressions and the complete post-fix release gate passed.

## Sign-Off

- [x] All threats have a disposition.
- [x] Accepted risks are documented.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set in frontmatter.

**Approval:** verified 2026-08-05
