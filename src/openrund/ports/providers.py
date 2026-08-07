"""Untrusted model proposal seam with no Command or Event authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, final

from openrund.contracts.commands import (
    AddMessageOperation,
    CancelRunOperation,
    CompleteRunOperation,
    CreateActionOperation,
    CreateCheckpointOperation,
    CreateDelegationOperation,
    FailRunOperation,
    ModelOperation,
    OpenApprovalWaitOperation,
    OpenInteractionWaitOperation,
    OpenJoinWaitOperation,
    OpenTimerWaitOperation,
    OperationBatch,
)
from openrund.contracts.content import Content
from openrund.contracts.ids import ModelCallId, RunId
from openrund.contracts.json import MISSING, JsonObject, MissingType, freeze_json
from openrund.errors import ValidationError

_MODEL_OPERATION_TYPES = (
    AddMessageOperation,
    CreateActionOperation,
    CreateDelegationOperation,
    OpenApprovalWaitOperation,
    OpenInteractionWaitOperation,
    OpenTimerWaitOperation,
    OpenJoinWaitOperation,
    CreateCheckpointOperation,
    CompleteRunOperation,
    FailRunOperation,
    CancelRunOperation,
    OperationBatch,
)


def _metadata(value: object, code: str) -> JsonObject | MissingType | None:
    if value is MISSING or value is None:
        return value
    frozen = freeze_json(value)
    if not isinstance(frozen, JsonObject):
        raise ValidationError(code=code)
    return frozen


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ModelRequest:
    model_call_id: ModelCallId
    run_id: RunId
    context: Content
    remaining_requests: int
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.model_call_id, ModelCallId):
            raise ValidationError(code="model_request_id_invalid")
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="model_request_run_id_invalid")
        if not isinstance(self.context, Content):
            raise ValidationError(code="model_request_context_invalid")
        if (
            isinstance(self.remaining_requests, bool)
            or not isinstance(self.remaining_requests, int)
            or self.remaining_requests < 0
        ):
            raise ValidationError(code="model_request_budget_invalid")
        object.__setattr__(
            self, "metadata", _metadata(self.metadata, "model_request_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ModelProposal:
    model_call_id: ModelCallId
    operation: ModelOperation
    response: Content
    provider: str
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.model_call_id, ModelCallId):
            raise ValidationError(code="model_proposal_id_invalid")
        if not isinstance(self.operation, _MODEL_OPERATION_TYPES):
            raise ValidationError(code="model_proposal_operation_invalid")
        if not isinstance(self.response, Content):
            raise ValidationError(code="model_proposal_response_invalid")
        if not isinstance(self.provider, str) or self.provider == "":
            raise ValidationError(code="model_proposal_provider_invalid")
        object.__setattr__(
            self, "metadata", _metadata(self.metadata, "model_proposal_metadata_invalid")
        )


class ModelProvider(Protocol):
    async def propose(self, request: ModelRequest, /) -> ModelProposal: ...
