# Documentation Refactor Plan

## Refactor 1: Update `docs/README.md`

Problem:

- Uses stale "TypeScript runtime for controlled execution" framing.
- Mixes evaluation dimensions and decision outcomes: "legal, authorized, deferred, rejected, superseded, or executable."
- Duplicates top-level positioning in a slightly older form.

Change:

- Replace with concise governed mutation runtime framing.
- Keep the document as a docs index, not a positioning essay.
- Update Quickstart description to mention governed mutation loop.
- Update verification wording to be repository-check oriented.

## Refactor 2: Shorten `docs/concepts.md` Governance Surfaces

Problem:

- Concepts owns ontology, but its Governance Surfaces section repeats the full first-class governance philosophy now owned by `docs/control.md`.

Change:

- Keep CommandDecision/attached/secondary surface semantics.
- Replace the broad "Governance is first-class..." opening with a concise ownership statement and pointer to `control.md`.
- Preserve ontology rules, root concepts, Wait taxonomy, attached semantics, secondary surfaces, and admission test.

Keep repeated intentionally:

- CommandDecision attached to Command.
- Workers/providers/Views/storage/CLI/Receipts/Reports/diagnostics do not decide legality.
- Do not add root `Control`.

## Refactor 3: Shorten `docs/storage.md` Bundle Section

Problem:

- Storage doc repeats Bundle import/resume assessment details owned by `docs/bundles.md`.

Change:

- Keep storage-owned facts: default export path and import custody is storage-adjacent.
- Point to `bundles.md` for verification, replay, import, and resumability semantics.
- Preserve "storage does not decide legality."

## Refactor 4: Leave Topic Docs Intact

Rationale:

- `events.md`, `providers.md`, `capabilities.md`, `delegation.md`, `bundles.md`, and `quickstart.md` were recently sharpened around their canonical ownership.
- Their repetitions are local boundary statements, not broad manifesto duplication.

## Refactor 5: No Archive Needed

Rationale:

- This is a consolidation pass over live docs, not a replacement of a prior doc generation.
- Historical pre-refresh docs are already archived under `docs/archive/phase-8.75-pre-refresh/`.
