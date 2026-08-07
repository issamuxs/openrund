# Providers

Providers adapt model APIs to OpenRund's typed proposal boundary. They own
transport, response parsing, and Operation normalization. They do not create
Commands or access Event storage. See [Control](./control.md) for the authority
path.

## ModelCall

A ModelCall is one durable attempt to call a model provider. On success, the
provider adapter translates the response into an Operation proposal.

The adapter does not create Commands and does not append Events.

## Provider Operation Set

Provider-parsed operations include:

- `add_message`
- `create_action`
- `operation_batch`
- `create_delegation`
- `open_wait`
- `create_checkpoint`
- `complete_run`
- `fail_run`
- `cancel_run`

Provider-originated Operations are not privileged runtime transitions. Runtime
APIs, timers, capability results, delegated Run handoffs, operator decisions,
and recovery procedures all enter the same Command and legality model.

Provider-originated `complete_run`, `fail_run`, and `cancel_run` Operations are
attempted terminal mutations. Terminal Run Events are appended only through
accepted CommandDecisions and completion legality evaluation.

## Failure Split

- Provider failures, transport failures including timeouts, and parse or
  malformed-output failures are ModelCall failures. Runtime Commands classify
  these as `provider`, `transport`, or `parse`.
- Unsupported, malformed, or policy-forbidden operations become rejected
  Commands.
- Legal Operations that cannot yet advance may produce deferred
  CommandDecisions and create or reference Waits.

Tool-call arguments cross the provider boundary before a Command exists. A
missing or empty argument string is the explicit empty-input case and becomes
an empty object. A present argument string must decode as a JSON object;
malformed JSON, arrays, scalars, and JSON null fail closed with
`ProviderToolArgumentsError` and code `provider_tool_arguments_invalid`.
`inputClassification` distinguishes `malformed_json` from `non_object` without
changing either case into a legal Action input.

Provider argument errors use a fixed safe message. They do not include the raw
provider body, parsed value, parser exception, authorization material, or
secret-looking tokens. Once parsing succeeds, the resulting Operation remains
only a proposal: unsupported, malformed, or policy-forbidden proposals are
recorded as rejected Commands by the Engine rather than by an adapter.

## Provider interface

`openrund.ports.providers.ModelProvider` is the structural adapter boundary. It
accepts a typed `ModelRequest` and returns a `ModelProposal`. The proposal
contains a provider name, ModelCall identity, response Content, and one parsed
model-safe Operation. It contains no Event and no CommandDecision.

`openrund.engine.command_from_model_proposal` converts that proposal to an
inert model-origin Command. `submit_model_proposal` then delegates to
`RuntimeEngine.submit`; it does not call a provider, append independently, or
mark a ModelCall outcome. `openrund.providers` supplies concrete adapters and
`openrund.runtime.DurableRunLoop` coordinates this boundary.

Repository tests use deterministic provider substitutes and require no live
credentials. Concrete adapters keep live smoke checks opt-in and never expose
raw provider bodies, credentials, or parser exceptions through safe runtime
errors.

## Concrete adapters

`OpenAIResponsesProvider` calls the Responses endpoint. Its local-compatible
counterpart uses the same request and normalization contract with an explicit
base URL and selected local model profile. `AnthropicMessagesProvider` calls
the Messages endpoint. All three:

- use the dependency-free async HTTP/1.1 and SSE transport directly;
- accept credentials as explicit constructor values and never inspect ambient
  environment variables;
- accept provider-neutral `ProviderTool` declarations;
- bind results to the locally allocated `ModelRequest.model_call_id` rather
  than trusting a remote response identifier;
- normalize text to `AddMessageOperation`, one client tool call to
  `CreateActionOperation`, and multiple calls to an ordered `OperationBatch`;
- retain only bounded response identity, model, streaming, and token-count
  metadata.

OpenAI-compatible tool arguments are strings at the remote boundary. Missing or
empty strings mean an explicit empty object. Every present string must be valid
JSON whose root is an object. Anthropic `tool_use.input` must already be an
object. Arrays, scalars, null, duplicate response keys, malformed JSON, and
incomplete streams fail as safe parse errors.

The HTTP transport validates `http` or `https` URLs without user information,
adds its own Host, length, and close headers, bounds status/header/body parsing,
supports content-length and chunked framing, and parses fragmented SSE events.
Timeout, connection, framing, size, UTF-8, and completion errors expose stable
codes without URLs, credentials, or response bodies.

## Durable model loop

`DurableRunLoop.step` executes this order:

1. Allocate a local ModelCall identity and submit `StartModelCallOperation`.
2. Invoke the provider only after the start fact commits.
3. Submit exactly one complete, failed, or cancelled ModelCall operation.
4. For a successful response, submit the normalized proposal as a separate
   model-origin Command through `RuntimeEngine.submit`.

A provider success does not imply proposal acceptance. The returned step result
contains the ModelCall lifecycle results and the proposal Command result, which
may be accepted, rejected, deferred, or superseded by normal Engine legality.
Provider HTTP status failures, transport failures, and response parsing failures
become respectively `provider`, `transport`, and `parse` ModelCall facts.

Cancellation during provider I/O cancels the request and shield-records a
`model_call.cancelled` fact before cancellation returns to the caller. Closing a
run-loop context cancels and drains active calls. A loop may own its provider or
leave an injected provider under the assembly's lifetime.

## Resource lifetime and live drift checks

Providers, the HTTP transport, and the durable loop are async context managers
with idempotent `aclose` methods. Use after close fails deterministically. Owned
sockets and tasks are cancelled and drained on exit.

The normal test suite is entirely offline. Real provider drift checks carry the
`live_provider` marker and skip unless their explicit `OPENRUND_LIVE_*`
configuration is present. They are diagnostics and never a release prerequisite.
