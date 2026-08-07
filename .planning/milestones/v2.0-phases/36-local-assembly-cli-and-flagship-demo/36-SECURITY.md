---
phase: 36
slug: local-assembly-cli-and-flagship-demo
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-06
---

# Phase 36 — Security

## Trust Boundaries

| Boundary | Description | Data Crossing |
|---|---|---|
| Host → assembly | Explicit roots, executables, provider, clocks, IDs, reporter, and operator input enter the resource graph. | configuration |
| CLI → operator | Untrusted strings become validated IDs, paths, mappings, statuses, and typed operations. | operator input |
| Operator → Engine | Every attempted mutation becomes one typed Command. | legality proposal |
| Action runner → workers | Validated Action input crosses in-process or controlled stdio/process boundaries. | bounded effect request |
| Demo → local machine | Only the explicit workspace, Python executable, Git executable, and runtime home are reachable. | local effects |

## Threat Register

| Threat ID | Category | Component | Severity | Mitigation | Status |
|---|---|---|---|---|---|
| T-36-01 | Confused Deputy | Assembly | critical | Registration grants reachability only; empty defaults have no roots, Capabilities, or Authority. | closed |
| T-36-02 | Authority Bypass | CLI/operator | critical | Mutations submit Engine Commands; append-authority architecture fence permits only Engine and custody decorators. | closed |
| T-36-03 | Path Escape | Runtime homes/workspaces | critical | Explicit normalized roots, lstat ancestor checks, mount confinement, and Bundle path validation fail closed. | closed |
| T-36-04 | Credential Leakage | Providers/demo | high | Provider credentials are constructor inputs; demo is offline and tests reject ambient credential reads. | closed |
| T-36-05 | Command Injection | Process/Git | critical | Executables, arguments, roots, environments, and Git operations are allowlisted; no shell or network operation is exposed. | closed |
| T-36-06 | Ambiguous Effect | Action execution | high | Transport uncertainty becomes `action.unknown`; evidence-backed operator reconciliation is required. | closed |
| T-36-07 | Error Disclosure | CLI | high | Stable semantic codes and safe messages replace raw paths, content, provider bodies, and storage errors. | closed |
| T-36-08 | Interrupt Corruption | CLI/workers | high | CLI catches ordinary exceptions only; cancellation propagates while owned resources drain explicitly. | closed |
| T-36-09 | API Drift | Installed package | medium | Exact root allowlist, CLI/library parity, installed-wheel typing, and isolated console tests fail on drift. | closed |
| T-36-10 | Presentation Authority | CLI | high | Text and JSON are deterministic renderings of one immutable operator result and cannot append Events. | closed |

## Accepted Risks Log

No accepted security risks. The local process and Git Capabilities intentionally
execute explicit allowlisted local binaries inside explicit roots; hosts remain
responsible for choosing trustworthy executables and writable mounts.

## Sign-Off

- [x] All threats have a disposition.
- [x] Accepted risks are documented.
- [x] `threats_open: 0` confirmed.
- [x] `status: verified` set in frontmatter.

**Approval:** verified 2026-08-06
