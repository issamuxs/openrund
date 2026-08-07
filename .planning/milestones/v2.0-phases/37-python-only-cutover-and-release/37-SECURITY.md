---
phase: 37
slug: python-only-cutover-and-release
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-04
---

# Phase 37 — Security

## Trust Boundaries

| Boundary | Security property |
|---|---|
| Build input → distribution | Exact wheel and source-distribution file allowlists reject unreviewed content. |
| Repository → installed environment | Wheel and source distribution install without repository-local imports or tooling. |
| Frozen corpus → tests | Paths, file type, length, and SHA-256 are authenticated before bytes are consumed. |
| CLI/API → runtime | Rendering and packaging add no Event append or legality path. |
| Providers → host | Credentials remain explicit constructor inputs; normal verification is offline. |

## Threat Register

| Threat ID | Category | Severity | Mitigation | Status |
|---|---|---|---|---|
| T-37-01 | Supply-chain drift | high | Locked build backend, empty runtime dependency set, exact artifact contents, and clean builds. | closed |
| T-37-02 | Distribution contamination | high | Wheel and source-distribution inventories must equal repository-derived allowlists. | closed |
| T-37-03 | Dual implementation confusion | critical | One Python source root; removed package workspace, executable oracle, non-Python tests, and tool commands are fenced. | closed |
| T-37-04 | Oracle execution | high | Compatibility evidence is inert authenticated data; generator and verifier executables are absent. | closed |
| T-37-05 | Provenance loss | medium | Frozen manifest commitments and Git history remain; RET-01 through RET-10 authenticate provenance. | closed |
| T-37-06 | Credential leakage | high | Production source cannot read ambient provider credential keys; live checks remain opt-in. | closed |
| T-37-07 | Dynamic execution | critical | Release hygiene rejects dynamic code execution and shell-enabled subprocess calls. | closed |
| T-37-08 | Path escape | critical | Existing filesystem, worker, process, Git, Run-home, Bundle, and fixture containment suites pass. | closed |
| T-37-09 | Authority bypass | critical | Existing import/AST fences permit canonical Event append only in Engine and custody decorators. | closed |
| T-37-10 | Unsupported interpreter drift | high | Identical full suites pass on Python 3.12, 3.13, and 3.14. | closed |

## Accepted Risks

No accepted release security risks. Optional live-provider verification depends
on external services and dedicated credentials, so it remains explicitly
opt-in and is not part of the offline release gate.

## Sign-Off

- [x] All threats have a disposition.
- [x] `threats_open: 0` confirmed.
- [x] Public reporting guidance exists in `SECURITY.md`.
- [x] Clean distribution and interpreter-matrix gates pass.

