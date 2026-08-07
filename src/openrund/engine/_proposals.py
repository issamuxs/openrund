"""Untrusted model proposal adaptation with no independent authority."""

from __future__ import annotations

from openrund.contracts.commands import Command, CommandOrigin, CommandResult
from openrund.contracts.ids import CommandId, RunId
from openrund.contracts.json import MISSING, MissingType
from openrund.contracts.time import Timestamp
from openrund.engine._engine import RuntimeEngine
from openrund.ports.providers import ModelProposal


def command_from_model_proposal(
    run_id: RunId,
    command_id: CommandId,
    proposal: ModelProposal,
    *,
    idempotency_key: str | MissingType | None = MISSING,
    created_at: Timestamp | MissingType | None = MISSING,
) -> Command:
    """Adapt a parsed provider proposal to an inert model-origin Command value."""

    if not isinstance(proposal, ModelProposal):
        raise TypeError("model_proposal_invalid")
    return Command(
        command_id=command_id,
        run_id=run_id,
        origin=CommandOrigin.MODEL,
        operation=proposal.operation,
        content=proposal.response,
        actor=proposal.provider,
        model_call_id=proposal.model_call_id,
        idempotency_key=idempotency_key,
        created_at=created_at,
        metadata=proposal.metadata,
    )


async def submit_model_proposal(
    engine: RuntimeEngine,
    run_id: RunId,
    command_id: CommandId,
    proposal: ModelProposal,
    *,
    idempotency_key: str | MissingType | None = MISSING,
    created_at: Timestamp | MissingType | None = MISSING,
) -> CommandResult:
    """Submit an adapted model Command through the sole Engine authority path."""

    if not isinstance(engine, RuntimeEngine):
        raise TypeError("runtime_engine_invalid")
    return await engine.submit(
        command_from_model_proposal(
            run_id,
            command_id,
            proposal,
            idempotency_key=idempotency_key,
            created_at=created_at,
        )
    )
