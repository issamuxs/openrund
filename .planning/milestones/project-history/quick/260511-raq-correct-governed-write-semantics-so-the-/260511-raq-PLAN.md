---
status: complete
mode: quick
must_haves:
  truths:
    - "The research-brief documents.write proposal targets the final approved output path directly."
    - "The approval prompt no longer exposes a draft path."
    - "Default automated approval keeps the proposed final path and does not fabricate relocation metadata."
    - "Validation proves governed write approval, not default approval relocation."
  artifacts:
    - "examples/research-brief/run.ts"
    - "packages/runtime/src/operator-prompts.ts"
    - "examples/research-brief/expected/validation.json"
    - "examples/research-brief/expected/runtime-audit.json"
    - "tests/examples/research-brief.test.ts"
---

# Quick Task 260511-raq Plan

1. Remove `draftBriefPath` from the governed write flow.
2. Make the proposed `documents.write` action input use the proposed final path.
3. Change the operator prompt API from draft/default paths to proposed final
   path.
4. Emit relocation diff metadata only when the operator actually changes the
   final path.
5. Update validation checks and expected fixture artifacts from
   `approval_relocation` to `governed_write_approval`.
