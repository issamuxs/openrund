# Phase 34 Existing Patterns

| New responsibility | Existing pattern to preserve |
|---|---|
| Provider semantic values | Frozen, slotted, keyword-only dataclasses in `openrund.ports.providers` |
| Boundary JSON | `freeze_json`, `JsonObject`, and strict exact-shape decoding |
| Provider proposal authority | `command_from_model_proposal` followed only by `RuntimeEngine.submit` |
| Durable lifecycle | `ActionRunner` start-before-dispatch and terminal recording pattern |
| Async subprocess cleanup | `StdioJsonRpcTransport` bounded gather, terminate, wait, then kill fallback |
| Safe failures | Stable `OpenRundError.code` values and redacted `safe_detail` |
| Test doubles | Injected structural protocols and deterministic fixtures under tests or `_testing` |
| Public exports | Narrow explicit module `__all__` surfaces with installed-wheel typing tests |

## Import Direction

`contracts/ports → providers → runtime loop → Engine submit`

Provider adapters may import semantic contracts, codecs, provider ports, and safe errors. They must not import EventStore, concrete storage, capability execution, or append authoritative Events. The runtime loop coordinates provider calls and Engine Commands but does not decide legality itself.
