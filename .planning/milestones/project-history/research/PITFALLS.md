# Pitfalls Research

**Domain:** Complete Python implementation of an event-sourced governed mutation runtime
**Researched:** 2026-08-04
**Confidence:** HIGH for repository-specific hazards; MEDIUM for implementation sequencing until requirements are approved

## Critical Pitfalls

### Pitfall 1: Losing Serialized Compatibility Before Freezing The Oracle

**What goes wrong:**
The Python implementation emits different IDs, timestamps, optional fields, JSON ordering, JSONL bytes, hashes, Event envelopes, SQLite values, or Bundle commitments even though the behavior appears equivalent.

**Why it happens:**
Language defaults differ, and the current declarations do not always describe the persisted payloads precisely. For example, some emitted Action failure and policy-rule payload shapes are more specific than their shared declarations.

**How to avoid:**
Before removing the current executable reference, export a versioned golden corpus covering every Event type, CommandDecision, View, Artifact record, SQLite row contract, provider normalization result, and `.orun` profile. Specify UTF-8, canonical JSON key ordering, numeric rules, optional-field omission, UTC timestamp precision, hash inputs, and Event-position semantics. Treat the frozen corpus plus resolved normative docs as the compatibility oracle.

**Warning signs:**
Python tests assert only decoded object equality; fixtures are hand-authored; timestamps mix `Z` and `+00:00`; Bundle verification passes only on Python-produced Bundles.

**Phase to address:**
First compatibility-contract phase, before runtime implementation or removal work.

---

### Pitfall 2: Translating Files And Types Instead Of Runtime Semantics

**What goes wrong:**
The new tree copies modules, public names, and type declarations mechanically while preserving accidental complexity or missing behavior that exists only in control flow and tests.

**Why it happens:**
A file-for-file port feels measurable, but OpenRund's contract spans documentation, emitted Events, expected-position append behavior, legality ordering, replay, capability dispatch, and failure tests.

**How to avoid:**
Organize one Python distribution around deep semantic modules. Map every frozen behavior to a Python contract and test, and resolve declaration-versus-emission contradictions explicitly. Do not expose predecessor-shaped packages solely for migration convenience.

**Warning signs:**
Python module names mirror package directories one-for-one; compatibility is measured by symbol counts; public aliases exist only because old imports existed.

**Phase to address:**
Compatibility and core ontology phases.

---

### Pitfall 3: Letting External Effects Happen Before Durable Acceptance

**What goes wrong:**
A Capability mutates external state before the accepted Command and Action lifecycle are durable. Append conflicts or crashes then create effects with no authoritative history, or retries duplicate mutations.

**Why it happens:**
Combining legality evaluation, dispatch, result handling, and Event append into one convenient async call obscures the durability boundary.

**How to avoid:**
Persist the accepted Command and pre-dispatch Action lifecycle before invoking mutating work. Use idempotency keys or fencing where available. On ambiguous recovery, record `action.unknown` and require evidence-backed reconciliation; never blindly retry a consequential mutation.

**Warning signs:**
Worker invocation appears before the first durable Action Event; append conflicts occur after successful side effects; cancellation converts uncertainty into a normal failure.

**Phase to address:**
Engine and Action lifecycle phase.

---

### Pitfall 4: Creating A Second Authority Boundary

**What goes wrong:**
Providers, workers, storage adapters, Views, CLI handlers, sync wrappers, or a public raw-append method can create authoritative Events or decide legality outside `RuntimeEngine`.

**Why it happens:**
Python's flexible protocols and direct object access make convenience bypasses easy to expose accidentally.

**How to avoid:**
Keep authoritative append internal to the Engine. Expose narrow proposal/result protocols. If low-level append is required for fixtures or bootstrap, put it behind an unmistakably internal testing interface. Add import-boundary and API-surface tests proving live consumers cannot append or decide legality.

**Warning signs:**
CLI or provider modules import a concrete Event store; workers return Event drafts; the synchronous client contains evaluation logic; Views are consulted without a known complete watermark.

**Phase to address:**
Core API and Engine phases, then continuously enforced.

---

### Pitfall 5: Mis-handling Async Cancellation And Process Cleanup

**What goes wrong:**
Provider or worker calls hang, cancellation is recorded as success/failure instead of cancellation or uncertainty, SQLite transactions remain open across awaits, or child processes survive their Run.

**Why it happens:**
Cancellation crosses runtime, provider, subprocess, and persistence boundaries, each with different failure behavior.

**How to avoid:**
Use one durable orchestration layer for timeouts and cancellation. Propagate `asyncio.CancelledError`, use structured concurrency, never hold database transactions across awaits, and terminate subprocess groups with TERM, bounded grace, then KILL. Persist lifecycle facts at each durable boundary.

**Warning signs:**
Broad `except Exception` blocks swallow cancellation; tasks are created without ownership; subprocess tests leave descendants; transaction scope includes network or process awaits.

**Phase to address:**
Durable Engine runner and Capability transport phases.

---

### Pitfall 6: Weakening SQLite Ordering Or Transaction Semantics

**What goes wrong:**
Event positions become off by one, two writers both appear to win, busy handling spins, async tasks share unsafe connections, or parent/child Delegation histories partially commit.

**Why it happens:**
SQLite allows one writer even in WAL mode, Python connection defaults differ from the current store, and multi-Run workflows need stronger semantics than independent appends.

**How to avoid:**
Define the watermark and expected-position contract explicitly. Use short `BEGIN IMMEDIATE` transactions, per-task connection discipline, bounded busy handling, rollback on every error, and conflict reload before reevaluation. Provide an atomic multi-Run append or a fully specified idempotent recovery protocol for Delegation creation.

**Warning signs:**
Tests cover sequential appends only; connections cross task/thread boundaries; retry repeats a stale decision; a parent records Delegation spawn without recoverable child establishment.

**Phase to address:**
Storage foundation before the full Engine and Delegation phases.

---

### Pitfall 7: Breaking Artifact Immutability Or Blob/Metadata Consistency

**What goes wrong:**
Writing the same Artifact ID overwrites content or metadata, crashes leave orphan blobs, or metadata references missing bytes.

**Why it happens:**
Filesystem bytes and SQLite metadata do not share a native transaction.

**How to avoid:**
Use content hashes, insert-only semantics, and idempotency only when bytes, hash, and metadata match. Stage blob writes atomically, make partial states detectable, and provide cleanup/recovery rules rather than silently updating immutable content.

**Warning signs:**
Upsert replaces bytes; repeated puts with different content succeed; export discovers missing content without a prior unavailable/corrupt state.

**Phase to address:**
Storage and Artifact foundation.

---

### Pitfall 8: Trusting Capability Inputs Or Results At The Wrong Boundary

**What goes wrong:**
Filesystem or documents operations escape authorized roots, environment secrets leak to workers, malformed result envelopes enter Events, or unbounded output exhausts memory.

**Why it happens:**
Schema-valid input is not resource authorization, and a worker result is still untrusted boundary data.

**How to avoid:**
Use one canonical path sandbox; pass mount-relative paths; independently canonicalize and reject symlink/reparse escapes in the worker; minimize subprocess environments; validate the entire `CapabilityResult`, declared output schema, effect/evidence shapes, Artifact ownership, and size limits before Engine materialization.

**Warning signs:**
Absolute document paths are accepted; caller-provided authority metadata is trusted; the default assembly uses a different filesystem implementation than tests; output is buffered without bounds.

**Phase to address:**
Capability protocol and built-in Capability phase.

---

### Pitfall 9: Treating Provider Output Or Errors As Safe Data

**What goes wrong:**
Malformed tool arguments become empty input, provider response bodies leak secrets, transport failures are confused with rejected Commands, or nominal "live" tests never invoke the provider.

**Why it happens:**
Adapters often normalize permissively for convenience and include remote detail for debugging.

**How to avoid:**
Treat parse and malformed-output failures as ModelCall failures. Persist typed sanitized failure codes, exclude remote bodies by default, and keep bounded diagnostic material behind explicit redaction. Use deterministic recorded fixtures by default and opt-in minimal live invocations with normalization assertions.

**Warning signs:**
Invalid JSON becomes `{}`; exceptions include raw response text; live tests only construct an adapter or check environment variables.

**Phase to address:**
Provider adapters and provider verification.

---

### Pitfall 10: Verifying Bundle Hashes Without Verifying Bundle Meaning

**What goes wrong:**
A self-consistent Bundle with the wrong Run IDs, position gaps, unsupported Event versions, invalid counts, unsafe paths, excessive files, or inconsistent provider requirements passes integrity checks.

**Why it happens:**
Cryptographic integrity proves bytes were not changed; it does not prove semantic validity or resumability.

**How to avoid:**
Validate manifest paths before access, file limits and symlinks, Event schemas and versions, Run identity, contiguous positions, declared counts, Artifact consistency, and required providers/capabilities before replay. Import through atomic staging and keep ResumeAssessment diagnostic rather than authoritative.

**Warning signs:**
Verification is defined as hash equality; replay accepts unknown Event versions; provider requirements are constant instead of derived from history.

**Phase to address:**
Bundle phase after codecs, Views, storage, and Engine semantics are stable.

---

### Pitfall 11: Carrying A Long-Lived Dual Implementation

**What goes wrong:**
Two live runtimes drift, tests prove different subsets, documentation must explain both, and the final removal becomes too risky to complete.

**Why it happens:**
Keeping both implementations indefinitely feels safer than committing to compatibility fixtures and a cutover gate.

**How to avoid:**
Use the existing executable only as a temporary fixture oracle. Freeze the corpus early, build Python behavior against it, and define one final cutover phase that removes all Node manifests, package trees, generated outputs, live references, and predecessor-facing examples after Python E2E gates pass.

**Warning signs:**
New features land in both runtimes; CI has separate permanent product matrices; docs include migration aliases; removal has no explicit phase or success criteria.

**Phase to address:**
Constrain in the first phase; complete in final packaging/documentation cutover.

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| File-for-file translation | Easy progress tracking | Preserves shallow boundaries and misses behavior | Never as architecture |
| Handwritten compatibility fixtures | Fast tests | Encodes assumptions rather than actual serialized behavior | Only for new Python-only cases after the oracle corpus exists |
| Public raw append | Easy bootstrap and tests | Permanent Engine-authority escape hatch | Internal test/bootstrap seam only |
| One global SQLite connection | Simple wiring | Task/thread contention and unsafe transaction ownership | Single-threaded prototypes only, not shipped runtime |
| Buffer all process output | Simple API | Memory exhaustion and late truncation | Only with strict small-output bounds |
| Broad exception normalization | Compact errors | Loses cancellation and unknown-outcome semantics | Never across runtime boundaries |
| Permanent compatibility aliases | Easier migration | Pollutes the greenfield API and live docs | Explicitly out of scope |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| OpenAI/Anthropic/local providers | Provider SDK objects leak into runtime contracts | Normalize HTTP responses into provider-neutral ModelCall proposals |
| Stdio JSON-RPC workers | Inherit the entire environment and trust result shape | Minimal environment, strict protocol envelope, timeouts, size limits, cancellation cleanup |
| Filesystem/documents | Validate lexical paths only | Resolve mount-relative paths, canonicalize, reject symlinks and out-of-root targets in Engine and worker |
| SQLite | Retry stale decisions after `SQLITE_BUSY` or expected-position conflict | End transaction, reload canonical history, reevaluate, then append |
| Delegation | Treat several single-Run appends as atomic | Atomic multi-Run transaction or idempotent recoverable spawn state machine |
| `.orun` import | Trust a verified hash as permission to resume | Stage, semantically validate, then produce a non-authoritative ResumeAssessment |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full replay for every mutation | Increasing decision and inspection latency | Preserve full replay while adding known-watermark incremental Views/snapshots later | Long Event streams |
| Unbounded stdout/stderr buffering | Memory spikes or hung process Actions | Stream to bounded preview plus Artifact-backed content | Large builds, diffs, or commands |
| SQLite transactions across awaits | Writer starvation and busy errors | Keep transactions synchronous and short; do external work outside them | First concurrent long-running Actions |
| Rehashing entire Bundles repeatedly | Slow import/export and excessive I/O | Reuse verified manifest commitments where semantically safe | Large Artifact sets |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing raw append | Any host surface can bypass legality | Internalize append and test public import boundaries |
| Trusting caller paths or authority metadata | Workspace escape and privilege expansion | Engine-owned scope evaluation plus worker-side sandboxing |
| Passing parent environment to workers | Credential leakage | Explicit minimal environment allowlist |
| Including provider bodies in exceptions | Secret or private-data disclosure | Typed sanitized errors and opt-in redacted diagnostics |
| Accepting arbitrary Bundle paths/symlinks | Read/write outside staging root | Validate normalized relative paths before filesystem access |
| Treating delegated grants as descriptive | Child can invoke more than contracted | Central typed Authority evaluator for actions, constraints, budgets, revocation |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Python API mechanically mirrors another language | Unnatural imports, lifecycle, and typing | One idiomatic distribution with deep modules and async-first Engine |
| Sync wrapper contains separate logic | Sync and async users observe different legality | Thin delegating client with no independent semantics |
| CLI synthesizes explanations | Output cannot be replayed or trusted | Render Command decisions, Views, Receipts, Reports, and Artifacts supplied by runtime |
| Current docs discuss predecessor removal | Product feels like a migration artifact | Write current docs solely for the Python product; keep provenance in archives |

## "Looks Done But Isn't" Checklist

- [ ] **Compatibility:** Python reads frozen legacy Events, SQLite fixtures, and Bundles and emits byte-compatible commitments where required.
- [ ] **Authority:** No provider, worker, CLI, View, storage adapter, plugin, or sync client can append authoritative Events or decide legality.
- [ ] **Durability:** Accepted mutating work is recorded before dispatch; conflicts reload and reevaluate.
- [ ] **Cancellation:** Provider and worker cancellation leaves correct lifecycle facts and no orphan tasks/processes.
- [ ] **Delegation:** Parent/child creation is atomic or deterministically recoverable, and delegated Authority is enforced.
- [ ] **Artifacts:** Immutable writes reject mismatched reuse and recover detectably from blob/metadata partial failures.
- [ ] **Capabilities:** Default assembly uses the same sandboxed implementations tested for path, symlink, environment, schema, and output bounds.
- [ ] **Providers:** Malformed output fails safely, errors are redacted, and opt-in live tests perform a real minimal call.
- [ ] **Bundles:** Verification checks semantic consistency, not only hashes; import cannot escape staging or authorize resume.
- [ ] **Greenfield cutover:** A clean sdist/wheel installs and passes tests/demo without Node; live docs, examples, packaging, and source contain no predecessor references.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Serialized compatibility drift | HIGH | Restore the oracle corpus, identify the first divergent encoder/decoder, version only when compatibility cannot be retained |
| Side effect before durable record | HIGH | Record unknown outcome, gather evidence, reconcile explicitly, add idempotency/fencing before retry |
| Partial Delegation creation | MEDIUM | Scan parent/child histories, finish or cancel the idempotent spawn state machine, record repair Commands/Events |
| Artifact blob/metadata mismatch | MEDIUM | Quarantine orphan content, verify hashes, mark unavailable/corrupt references, rebuild metadata only from evidence |
| Provider data leak | HIGH | Revoke exposed credentials, sanitize persisted diagnostics, add regression fixtures and central redaction |
| Premature source removal | HIGH | Recover the executable oracle from Git history, generate missing golden fixtures, then resume Python validation |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Serialized compatibility and contradictory payload contracts | Compatibility foundation | Golden corpus and bidirectional codec/Bundle tests |
| Authority bypass and mechanical API translation | Core ontology/API | Import-boundary tests and Command/Event mutation matrix |
| SQLite ordering, Artifacts, and multi-Run atomicity | Storage foundation | Concurrent append, crash injection, immutability, and Delegation transaction tests |
| Pre-dispatch durability, cancellation, unknown outcomes | Engine/lifecycle | State-machine and fault-injection tests at every await/append boundary |
| Capability trust and sandboxing | Capabilities | Default-assembly escape, symlink, environment, size, and malformed-result tests |
| Provider parsing and error leakage | Providers | Recorded fixtures, redaction tests, and opt-in real calls |
| Bundle semantic validation | Bundles | Corrupt/malicious fixture matrix and cross-implementation replay |
| Dual-runtime drift and stale product surfaces | Final cutover | Clean wheel install, Python-only test/demo/docs scan, no Node available |

## Sources

- `docs/concepts.md`, `docs/control.md`, `docs/architecture.md`, `docs/events.md`, `docs/capabilities.md`, `docs/storage.md`, `docs/providers.md`, `docs/bundles.md`, and `docs/delegation.md`
- `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONCERNS.md`, and `.planning/codebase/TESTING.md`
- Runtime, core, capability, storage, provider, Bundle, public-API, and governed-demo source/test evidence in the repository
- Completed `contract_hazards` specialist evidence matrix from the v2.0 GSD Pitfalls research pass

---
*Pitfalls research for: OpenRund v2.0 Python implementation*
*Researched: 2026-08-04*
