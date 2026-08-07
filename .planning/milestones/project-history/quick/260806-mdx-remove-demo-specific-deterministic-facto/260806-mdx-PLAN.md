---
quick_id: 260806-mdx
status: ready
description: Remove demo-specific deterministic factories and run the governed-coding demo through production local assembly behavior
---

# Quick Task 260806-mdx Plan

## Goal

Make the governed-coding demonstration exercise the same production identity,
clock, timing, storage, Engine, Capability, operator, and Bundle paths as an
ordinary local OpenRund assembly. Keep only explicit user configuration needed
to grant the demo's roots, executable, and Git identity.

## Task 1 — Remove demo-only runtime substitutions

**Files:** `src/openrund/demo.py`

**Action:** Delete the demo clock, sequence-ID factory, token factory, and
monotonic-clock substitute. Construct `LocalAssemblyConfig` with its production
clock and ID defaults, obtain every Run, Action, and Wait identity from that
assembly's factories, and use the real process timer. Remove wording that
claims the runtime path is deterministic.

**Verify:** The demo completes twice against separate homes, each result uses a
valid production-prefixed UUID identity, and the two Run IDs differ while all
governance assertions remain true.

**Done:** No demo-specific entropy or timing implementation remains and every
state mutation still crosses the normal Engine and ActionRunner paths.

## Task 2 — Align tests, examples, and documentation

**Files:** `tests/demo/test_governed_coding.py`, `README.md`,
`examples/README.md`, `examples/governed_coding.py`, `docs/quickstart.md`,
`docs/contributing.md`

**Action:** Replace exact-result determinism assertions with behavioral and
production-ID assertions. Describe the demo as an offline production-assembly
workflow rather than a deterministic fixture, without weakening deterministic
rendering, replay, or Bundle semantics elsewhere.

**Verify:** Demo, CLI, documentation, package, typing, lint, and full pytest
gates pass.

**Done:** Public guidance accurately states that the demonstration runs the
real local assembly and generates fresh production identities and timestamps.
