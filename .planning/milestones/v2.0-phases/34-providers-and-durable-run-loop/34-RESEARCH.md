# Phase 34 Research

## Chosen Approach

Use one small dependency-free HTTP/1.1 client over `asyncio.open_connection`, with TLS for `https`, strict URL validation, fixed content bounds, connection-close semantics, content-length/chunked decoding, and SSE frame parsing. Both provider families receive this transport through a structural protocol, so all normal tests use deterministic in-memory responses or a local async server.

OpenAI Responses streaming emits server-sent events and completes with a full response object. The adapter accepts ordinary JSON or selects the final `response.completed`/`response.done` payload from SSE. Function-call items normalize to one `CreateActionOperation` or an `OperationBatch`; assistant output normalizes to `AddMessageOperation`.

Anthropic Messages accepts tools with `name`, `description`, and `input_schema`; responses contain text or `tool_use` content blocks. Streaming content blocks are accumulated only until a final message is reconstructable, under the same byte and event bounds.

Sources consulted:

- [OpenAI Responses streaming events](https://platform.openai.com/docs/api-reference/responses-streaming/response/code_interpreter_call/completed)
- [OpenAI developer quickstart](https://platform.openai.com/docs/quickstart/make-your-first-api-request)
- [Anthropic tool use](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview)

## Failure Classification

| Failure | Runtime classification | Rule |
|---|---|---|
| DNS, connection, TLS, timeout, truncated HTTP/SSE | transport | Stable code; no socket or URL detail |
| HTTP non-success | provider | Status class and retryability only; body discarded from durable facts |
| Invalid JSON, SSE, response shape, or tool arguments | parse | Fixed safe message; no raw provider body |
| Engine rejects resulting proposal | normal Command decision | Provider does not relabel legality as a transport failure |
| Caller cancellation | cancelled | Provider I/O is cancelled and ModelCall cancellation is durably recorded under shielded cleanup |

## Lifecycle

1. Allocate a ModelCall ID and submit `StartModelCallOperation`.
2. Call the provider inside the loop's active async lifetime.
3. Submit exactly one complete/fail/cancel lifecycle Command.
4. On success, adapt the proposal to a model-origin Command and submit it through the Engine.
5. Return both lifecycle and proposal decisions; never execute effects implicitly.

## Pitfalls Closed by Plan

- SSE frames can split across arbitrary TCP chunks.
- HTTP chunk extensions and trailers must be bounded and parsed fail closed.
- A response ID is evidence, not a trusted local ModelCall identity; the request identity remains authoritative.
- Provider-assigned tool-call IDs must still satisfy OpenRund ID constructors.
- Cancellation can arrive while recording cancellation; terminal recording must be shielded and awaited.
- Closing a context with active provider or worker I/O must cancel, drain, and reap it.
