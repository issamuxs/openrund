# Documentation Refresh Outline

## Replacement Rule

The live `docs/` directory should explain the current codebase directly. It should not read as a migration log.

Historical docs are archived under:

```text
docs/archive/phase-8.75-pre-refresh/
```

Archived docs are non-normative.

## Final Live Docs

- `README.md`: reader map, normative order, verification commands.
- `concepts.md`: canonical ontology, value types, secondary surfaces, admission rules.
- `quickstart.md`: minimal setup and code sample using `RuntimeEngine`.
- `architecture.md`: normative runtime authority and package map.
- `events.md`: event envelope and current event catalog.
- `api.md`: public TypeScript and CLI API.
- `capabilities.md`: Capability/Action/Authority boundary.
- `bundles.md`: `.orun` Bundle structure and APIs.
- `providers.md`: ModelCall/provider adapter boundary.
- `storage.md`: persistence, leases, runtime home, workspace roots, artifacts.
- `delegation.md`: Delegation and join Wait semantics.
- `contributing.md`: hygiene, naming, docs, and test rules.

## Merged Or Archived Docs

- `principles.md`: merged into `concepts.md` and `architecture.md`; archived.
- `runtime-semantics.md`: merged into `architecture.md`, `api.md`, and `capabilities.md`; archived.
- `secondary-surfaces.md`: summarized in `concepts.md` and enforced through `contributing.md`; archived.
- `orun.md`: replaced by `bundles.md`; archived.

## Verification Gates

- `pnpm typecheck`
- `pnpm test`
- `pnpm hygiene`
- Docs link test updated to final live docs.
- Stale production-name scan over live docs.
