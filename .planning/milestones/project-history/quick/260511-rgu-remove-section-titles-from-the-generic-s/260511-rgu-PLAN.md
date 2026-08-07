---
status: complete
mode: quick
must_haves:
  truths:
    - "Generic session completion summary no longer renders section titles."
    - "Summary element order remains identity, locations, outputs, proof."
  artifacts:
    - "packages/runtime/src/session-summary.ts"
    - "tests/runtime/session-summary.test.ts"
    - "examples/research-brief/README.md"
---

# Quick Task 260511-rgu Plan

1. Remove section title strings from `renderSessionRunSummary`.
2. Update the summary renderer test to assert the full title-free output.
3. Adjust README wording from grouped sections to ordered elements.
