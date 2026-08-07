---
phase: 27-frozen-compatibility-oracle
verified: 2026-08-05T07:41:14Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "Artifact publication recovers every filesystem/SQLite crash window"
    addressed_in: "Phase 30: Durable Storage, Artifacts, and Leases"
    evidence: "Phase 30 success criteria explicitly require injected-crash, partial-failure, and staged blob/metadata recovery coverage."
---

# Phase 27 Verification — Frozen Compatibility Oracle

## Verdict

**Passed.** Maintainers have complete, executable, source-revision-pinned evidence of the canonical serialized behavior the Python implementation must preserve. All four roadmap success criteria and requirement SEM-02 are verified by committed artifacts and automated tests. No human verification or behavioral override is required.

## Goal Achievement

| # | Required truth | Status | Evidence |
|---|---|---|---|
| 1 | A versioned predecessor-produced corpus can be regenerated across every required canonical surface. | VERIFIED | `tests/fixtures/compatibility/v1/` contains one manifest plus 286 referenced evidence files. Two fresh promotion-mode generations independently verified and produced byte-identical trees. Coverage tests establish inventory/file/View/fallback bijection across Events, Command decisions, Views, providers, SQLite, Artifacts, and all `.orun` profiles. |
| 2 | Exact wire keys, enums, null/absence, identities, timestamps, links, hashes, and Bundle commitments are machine fixed. | VERIFIED | `manifest.json` records byte length, SHA-256, semantic SHA-256, required/absent/null pointers, source links, decision IDs, and provenance for each evidence item. Exact-byte, decoded-meaning, Artifact, SQLite, provider, and Bundle tests pass. |
| 3 | Contract ambiguities are resolved and drift fails visibly. | VERIFIED | `docs/archive/compatibility-v1-decisions.md` is sealed against the exact 22 required resolved decisions. Tests reject missing, duplicate, extra, malformed, or unresolved decisions and reject added, removed, changed, malformed, unsafe, forged, or stale corpus/source data. |
| 4 | The executable predecessor remains a temporary internal oracle with explicit retirement gates. | VERIFIED | The package/public-surface retirement test keeps the oracle internal and requires all ten Phase 37 retirement gates. The corpus records clean protected-source commit `b8cb9c6f7809a86f80e59f7b262d73115944b097`; the commit exists, is a commit object, and its protected tree equals the post-promotion protected tree. |

**Score:** 4/4 must-haves verified.

## Required Artifacts

| Artifact | Status | Verification |
|---|---|---|
| `tests/fixtures/compatibility/v1/manifest.json` | VERIFIED | Schema version 1, corpus version `v1`, exact source revision, 22 decisions, 10 retirement gates, and 286 evidence entries. |
| `tests/fixtures/compatibility/v1/evidence/` | VERIFIED | 286 regular immutable fixture files; no symlinks or executable file types; every file is referenced exactly once. |
| `docs/archive/compatibility-v1-decisions.md` | VERIFIED | Closed decision ledger with exact-ID and resolved-status enforcement. |
| `scripts/compatibility/generate-v1-oracle.ts` | VERIFIED | Deterministic fixed-entropy generator with Git-derived provenance and absent-only atomic final publication. |
| `scripts/compatibility/verify-v1-oracle.ts` | VERIFIED | Read-only recursive verification of provenance, inventories, schema, exact bytes, semantic hashes, paths, decisions, links, and retirement gates. |
| `scripts/compatibility/oracle-inventory.ts` | VERIFIED | Independent canonical surface inventory and duplicate detection. |
| `scripts/compatibility/oracle-source-paths.ts` | VERIFIED | One shared protected-source inventory covers normative documents plus generation, build, and test inputs. |
| `scripts/compatibility/oracle-decisions.ts` | VERIFIED | One shared exact inventory of all 22 V1 decisions. |
| `tests/compatibility/*.test.ts` | VERIFIED | Manifest, wire, Views, providers, SQLite, Artifacts, Bundles, rejection, regeneration, and retirement suites all pass. |

## Key-Link Verification

| Link | Status | Evidence |
|---|---|---|
| Protected Git source → generator provenance | WIRED | Promotion derives and validates the recorded commit, rejects dirty protected inputs and forged/stale revisions, and permits only later corpus-only or unrelated commits. |
| Generator inventories and fixed entropy → evidence | WIRED | Every independently inventoried key maps bijectively to one evidence file with deterministic bytes and decoded meaning. |
| View history → View result | WIRED | The plan's schematic `streams/` → `views/` path is implemented as a stronger co-located evidence record: each View item carries its input stream, watermark, and result together, with manifest pointers and tests proving the relationship. No semantic link is missing. |
| Manifest → committed corpus tree | WIRED | Recursive verification proves all 286 evidence paths, hashes, semantic hashes, pointers, decision references, source links, and provenance; unreferenced, missing, duplicate, or altered files fail. |
| Package scripts → generator/verifier | WIRED | `compatibility:generate:v1` and `compatibility:verify:v1` invoke the reviewed scripts; the verifier completed with 286 checked files and zero issues. |
| Retirement gates → Phase 37 cutover | WIRED | RET-01 through RET-10 are required by the manifest and tests before executable-oracle removal. |

## Data-Flow Trace

1. Normative contracts, the closed decision ledger, and the shared source inventory define the protected inputs.
2. The generator reads the clean Git revision and production behavior, injects fixed identities/times, and writes staged evidence beneath an owned private sibling directory.
3. Each evidence file is bound into the manifest by exact bytes, decoded meaning, hashes, pointers, links, and provenance.
4. Final publication is an absent-only atomic rename; existing destinations, ancestor symlinks, and destination swaps fail closed.
5. The independent read-only verifier and compatibility suites traverse the committed corpus and reject byte, meaning, inventory, provenance, schema, path, or decision drift.
6. Later Python phases consume these files as inert golden evidence; they do not execute the predecessor to define new behavior.

## Automated Evidence

| Check | Result |
|---|---|
| Full TypeScript test suite | PASS — 68 files; 380 passed; 2 credential-gated skipped |
| Supplemental Python documents-worker suite | PASS — 4 passed |
| Typecheck/build validation | PASS |
| Frozen-corpus verifier | PASS — 286 evidence files; zero issues |
| Independent two-root regeneration | PASS — both roots independently valid and byte-identical |
| Post-promotion protected-tree comparison | PASS |
| Second standard-depth code review | PASS — zero critical, warning, or informational findings |

## Requirement Coverage

| Requirement | Status | Evidence |
|---|---|---|
| SEM-02 | SATISFIED | Canonical versioned data can be round-tripped, hashed, and rejected deterministically with exact names, keys, enums, absence/null semantics, identities, timestamps, links, and Bundle commitments fixed by the corpus and exercised by automated compatibility tests. |

## Anti-Patterns and Human Verification

- No TODO, FIXME, placeholder, or not-implemented markers were found in the reviewed Phase 27 production, generator, verifier, test, or normative-document scope.
- No human-only verification is required. Corpus promotion is an explicit maintainer operation, but all its prerequisites, side effects, and resulting bytes are machine checked.
- No verification probes were declared; probes are therefore skipped.
- No overrides were applied.

## Deferred Work

The current Artifact implementation now preserves immutability across reviewed conflicts and ordinary failures, but exhaustive recovery across every filesystem/SQLite crash boundary belongs to Phase 30. That phase explicitly requires injected-crash, partial-failure, reopen, and staged blob/metadata recovery behavior. This does not weaken Phase 27's frozen compatibility evidence or its successful goal.

## Gaps

None.
