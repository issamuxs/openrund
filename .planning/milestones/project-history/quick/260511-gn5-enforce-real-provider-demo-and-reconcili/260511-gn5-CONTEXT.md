# Quick Task 260511-gn5: Enforce real-provider demo and reconciliation semantics - Context

**Gathered:** 2026-05-11
**Status:** Ready for execution

<domain>
## Task Boundary

Tighten the developer-facing research-brief demo and related docs so:

- The literal runtime-home override token is absent from the repository.
- Reconciliation defaults to manual operator-mediated human evidence.
- The developer demo requires a real model provider, while deterministic placeholder behavior remains only in tests/fixture mode.

</domain>

<decisions>
## Implementation Decisions

### Reconciliation

- A human is the person making the judgment about external evidence.
- An operator is the authorized runtime role/channel that submits that judgment.
- In the CLI demo, the developer is both the human and the operator.
- Default reconciliation is manual operator-mediated human evidence.
- Automated reconciliation is explicit and reserved for tests/CI or deterministic operator services.

### Runtime Home Token

- Do not add the forbidden runtime-home environment token to code, docs, package scripts, or planning artifacts.
- CI/test isolation uses explicit `runtimeHome` injection and temporary directories.

### Real Provider Demo

- `pnpm demo:research-brief` must require a real model provider.
- Supported provider configuration should be OpenAI, Anthropic, or local OpenAI-compatible endpoint.
- Deterministic fixture outputs are allowed only through the exported fixture runner used by tests.
- `pnpm demo:research-brief:auto` may automate approvals/reconciliation but must still require a provider.

</decisions>

<canonical_refs>
## Canonical References

- [examples/research-brief/run.ts](../../../examples/research-brief/run.ts)
- [examples/research-brief/README.md](../../../examples/research-brief/README.md)
- [docs/runtime-semantics.md](../../../docs/runtime-semantics.md)
- [docs/quickstart.md](../../../docs/quickstart.md)
- [docs/storage.md](../../../docs/storage.md)
- [docs/providers.md](../../../docs/providers.md)

</canonical_refs>

