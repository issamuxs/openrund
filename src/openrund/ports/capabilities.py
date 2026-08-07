"""Capability invocation transport seam without runtime authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, final

from openrund.contracts.capabilities import CapabilityResult
from openrund.contracts.content import Content, Mutation
from openrund.contracts.ids import ActionId, CapabilityId
from openrund.contracts.json import MISSING, JsonObject, MissingType, freeze_json
from openrund.errors import ValidationError


def _optional_text(value: object, code: str) -> str | MissingType | None:
    if value is MISSING or value is None:
        return value
    if not isinstance(value, str):
        raise ValidationError(code=code)
    return value


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityInvocation:
    action_id: ActionId
    capability_id: CapabilityId
    action_name: str
    input: Content
    mutation: Mutation | MissingType | None = MISSING
    idempotency_key: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="capability_invocation_action_id_invalid")
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="capability_invocation_capability_id_invalid")
        if not isinstance(self.action_name, str) or self.action_name == "":
            raise ValidationError(code="capability_invocation_action_name_invalid")
        if not isinstance(self.input, Content):
            raise ValidationError(code="capability_invocation_input_invalid")
        if self.mutation not in (MISSING, None) and not isinstance(self.mutation, Mutation):
            raise ValidationError(code="capability_invocation_mutation_invalid")
        object.__setattr__(
            self,
            "idempotency_key",
            _optional_text(self.idempotency_key, "capability_invocation_idempotency_key_invalid"),
        )
        if self.metadata in (MISSING, None):
            return
        metadata = freeze_json(self.metadata)
        if not isinstance(metadata, JsonObject):
            raise ValidationError(code="capability_invocation_metadata_invalid")
        object.__setattr__(self, "metadata", metadata)


class CapabilityTransport(Protocol):
    async def invoke(self, invocation: CapabilityInvocation, /) -> CapabilityResult: ...


class CapabilityHandler(Protocol):
    async def __call__(self, invocation: CapabilityInvocation, /) -> CapabilityResult: ...
