"""Provider-neutral normalization and concrete async model adapters."""

from openrund.providers._http import (
    AsyncHttpTransport,
    HttpRequest,
    HttpResponse,
    ServerSentEvent,
    StdlibHttpTransport,
    parse_server_sent_events,
)
from openrund.providers._normalization import (
    ProviderTool,
    ProviderToolCall,
    normalize_provider_output,
    parse_provider_tool_arguments,
    split_provider_qualified_name,
)
from openrund.providers.anthropic import (
    AnthropicMessagesProvider,
    normalize_anthropic_response,
)
from openrund.providers.openai import (
    LocalModelDescription,
    LocalModelProfile,
    LocalOpenAICompatibleProvider,
    OpenAIResponsesProvider,
    normalize_openai_response,
)

__all__ = [
    "AnthropicMessagesProvider",
    "AsyncHttpTransport",
    "HttpRequest",
    "HttpResponse",
    "LocalModelDescription",
    "LocalModelProfile",
    "LocalOpenAICompatibleProvider",
    "OpenAIResponsesProvider",
    "ProviderTool",
    "ProviderToolCall",
    "ServerSentEvent",
    "StdlibHttpTransport",
    "normalize_anthropic_response",
    "normalize_openai_response",
    "normalize_provider_output",
    "parse_provider_tool_arguments",
    "parse_server_sent_events",
    "split_provider_qualified_name",
]
