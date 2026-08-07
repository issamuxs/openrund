---
phase: 35
slug: portable-orun-bundles
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-06
---

# Phase 35 — Security

## Trust Boundaries

| Boundary | Description | Data Crossing |
|---|---|---|
| Runtime custody → export | Canonical Events, optional Artifact bytes, and derived Views enter a staged portable tree. | governed Run evidence |
| Bundle tree → verifier | All paths, nodes, manifests, bytes, hashes, Events, and declarations are untrusted. | portable files |
| Verified Bundle → replay | Only authenticated, complete, contiguous history reaches View reduction. | canonical Events |
| Verified Bundle → import | Content is copied into isolated local custody and reverified before atomic publication. | immutable evidence |
| Import → resume assessment | Local mappings and available services are compared with declared requirements. | explanatory readiness facts |

## Threat Register

| Threat ID | Category | Component | Severity | Mitigation | Status |
|---|---|---|---|---|---|
| T-35-01 | Path Traversal | Bundle paths | critical | Portable relative paths reject traversal, ambiguity, platform separators, and invalid components. | closed |
| T-35-02 | Symlink Attack | Export/verify/import | critical | Roots and every existing ancestor are lstat-checked; links and non-directory ancestors fail closed. | closed |
| T-35-03 | Tampering | File/Event commitments | critical | Exact byte length, SHA-256, raw Event chain, Bundle commitment, and semantic replay are recomputed. | closed |
| T-35-04 | Smuggling | Bundle topology | high | Exact declared files and directories are enforced; unknown or undeclared nodes are rejected. | closed |
| T-35-05 | Confused Deputy | Import/resume | critical | Import appends no Events, grants no Authority, and never resumes automatically; assessment is typed and non-authoritative. | closed |
| T-35-06 | TOCTOU | Import publication | high | Source is verified, copied without following links, reverified in staging, recorded, and renamed under an exclusive lock. | closed |
| T-35-07 | Resource Exhaustion | Untrusted files | high | Manifest, Events, and transported files have explicit byte/count bounds. | closed |
| T-35-08 | Identity Confusion | Run/Artifact/policy | high | Manifest Run IDs, Event stream IDs, Artifact declarations, policy identifiers, and resume requirements must agree. | closed |
| T-35-09 | Compatibility Downgrade | Versions | high | Bundle, Event, View, policy, and capability schema versions are exact and unsupported values fail closed. | closed |
| T-35-10 | Information Disclosure | Profiles | high | Audit/redacted profiles declare omissions; absent content cannot be presented as complete or resumable. | closed |

## Accepted Risks Log

No accepted security risks. Bundle authenticity is not claimed by schema 1; integrity commitments detect mutation but do not identify a signer. Hosts must establish provenance separately.

## Sign-Off

- [x] All threats have a disposition.
- [x] Accepted risks are documented.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set in frontmatter.

**Approval:** verified 2026-08-06
