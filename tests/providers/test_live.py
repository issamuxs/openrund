from __future__ import annotations

import asyncio
import os

import pytest

from openrund.contracts.content import Content
from openrund.contracts.ids import ModelCallId, RunId
from openrund.ports.providers import ModelRequest
from openrund.providers import (
    AnthropicMessagesProvider,
    LocalModelProfile,
    LocalOpenAICompatibleProvider,
    OpenAIResponsesProvider,
)


def _request(name: str) -> ModelRequest:
    return ModelRequest(
        model_call_id=ModelCallId(value=f"live-{name}"),
        run_id=RunId(value="live-provider-drift"),
        context=Content(preview="Reply with one short sentence."),
        remaining_requests=1,
    )


@pytest.mark.live_provider
def test_openai_live_drift_opt_in() -> None:
    key = os.environ.get("OPENRUND_LIVE_OPENAI_API_KEY")
    model = os.environ.get("OPENRUND_LIVE_OPENAI_MODEL")
    if not key or not model:
        pytest.skip("explicit OpenAI live configuration not supplied")

    async def run() -> None:
        async with OpenAIResponsesProvider(api_key=key, model=model) as provider:
            proposal = await provider.propose(_request("openai"))
        assert proposal.provider == "openai"

    asyncio.run(run())


@pytest.mark.live_provider
def test_local_openai_compatible_live_drift_opt_in() -> None:
    base_url = os.environ.get("OPENRUND_LIVE_LOCAL_BASE_URL")
    model = os.environ.get("OPENRUND_LIVE_LOCAL_MODEL")
    if not base_url or not model:
        pytest.skip("explicit local live configuration not supplied")

    async def run() -> None:
        async with LocalOpenAICompatibleProvider(
            base_url=base_url,
            profile=LocalModelProfile.STRONG,
            model=model,
        ) as provider:
            proposal = await provider.propose(_request("local"))
        assert proposal.provider == "local-openai-compatible"

    asyncio.run(run())


@pytest.mark.live_provider
def test_anthropic_live_drift_opt_in() -> None:
    key = os.environ.get("OPENRUND_LIVE_ANTHROPIC_API_KEY")
    model = os.environ.get("OPENRUND_LIVE_ANTHROPIC_MODEL")
    if not key or not model:
        pytest.skip("explicit Anthropic live configuration not supplied")

    async def run() -> None:
        async with AnthropicMessagesProvider(api_key=key, model=model) as provider:
            proposal = await provider.propose(_request("anthropic"))
        assert proposal.provider == "anthropic"

    asyncio.run(run())
