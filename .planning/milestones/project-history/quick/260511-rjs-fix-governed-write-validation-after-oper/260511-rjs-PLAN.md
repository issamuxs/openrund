---
status: complete
mode: quick
must_haves:
  truths:
    - "governed_write_approval validation no longer hard-codes research-brief.md."
    - "The framework path prompt treats y/yes as keeping the proposed final path."
    - "The full suite passes after the live-demo failure fix."
  artifacts:
    - "examples/research-brief/run.ts"
    - "packages/runtime/src/operator-prompts.ts"
    - "tests/runtime/operator-prompts.test.ts"
---

# Quick Task 260511-rjs Plan

1. Relax research-brief governed write validation to accept the actual approved
   final path when it is under the approved mount.
2. Normalize `y` and `yes` path prompt answers to the proposed final path.
3. Add a unit test for the path-answer guard.
4. Run focused tests and the full suite.
