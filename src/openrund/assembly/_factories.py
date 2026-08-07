"""Production time and identity factories for explicit local assemblies."""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import final

from openrund.contracts.ids import (
    ActionId,
    AnnotationId,
    ArtifactId,
    AuthorityId,
    CheckId,
    CheckpointId,
    CommandId,
    DelegationId,
    EventId,
    LeaseId,
    MessageId,
    ModelCallId,
    RunId,
    RuntimeId,
    WaitId,
)
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError
from openrund.ports.runtime import Clock, IdFactory


@final
class SystemClock:
    """UTC clock that emits the canonical millisecond representation."""

    __slots__ = ()

    def now(self) -> Timestamp:
        current = datetime.now(UTC)
        milliseconds = current.microsecond // 1_000
        return Timestamp(value=current.strftime("%Y-%m-%dT%H:%M:%S.") + f"{milliseconds:03d}Z")


@final
class UuidIdFactory[TId: RuntimeId]:
    """Kind-specific UUID factory whose prefix remains visible to operators."""

    __slots__ = ("_constructor", "_prefix")

    def __init__(self, constructor: Callable[..., TId], prefix: str) -> None:
        if not callable(constructor):
            raise ValidationError(code="id_factory_constructor_invalid")
        if (
            not isinstance(prefix, str)
            or prefix == ""
            or not prefix.replace("-", "").replace("_", "").isalnum()
        ):
            raise ValidationError(code="id_factory_prefix_invalid")
        self._constructor = constructor
        self._prefix = prefix

    def new_id(self) -> TId:
        return self._constructor(value=f"{self._prefix}_{uuid.uuid4().hex}")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class LocalIdFactories:
    run_ids: IdFactory[RunId]
    event_ids: IdFactory[EventId]
    command_ids: IdFactory[CommandId]
    model_call_ids: IdFactory[ModelCallId]
    wait_ids: IdFactory[WaitId]
    delegation_ids: IdFactory[DelegationId]
    check_ids: IdFactory[CheckId]
    checkpoint_ids: IdFactory[CheckpointId]
    message_ids: IdFactory[MessageId]
    annotation_ids: IdFactory[AnnotationId]
    authority_ids: IdFactory[AuthorityId]
    action_ids: IdFactory[ActionId]
    artifact_ids: IdFactory[ArtifactId]
    lease_ids: IdFactory[LeaseId]
    lease_tokens: Callable[[], str]

    def __post_init__(self) -> None:
        for name in (
            "run_ids",
            "event_ids",
            "command_ids",
            "model_call_ids",
            "wait_ids",
            "delegation_ids",
            "check_ids",
            "checkpoint_ids",
            "message_ids",
            "annotation_ids",
            "authority_ids",
            "action_ids",
            "artifact_ids",
        ):
            if not callable(getattr(getattr(self, name), "new_id", None)):
                raise ValidationError(code="local_id_factory_invalid")
        if not callable(self.lease_tokens):
            raise ValidationError(code="local_lease_token_factory_invalid")

    @classmethod
    def production(cls) -> LocalIdFactories:
        return cls(
            run_ids=UuidIdFactory(RunId, "run"),
            event_ids=UuidIdFactory(EventId, "evt"),
            command_ids=UuidIdFactory(CommandId, "cmd"),
            model_call_ids=UuidIdFactory(ModelCallId, "call"),
            wait_ids=UuidIdFactory(WaitId, "wait"),
            delegation_ids=UuidIdFactory(DelegationId, "del"),
            check_ids=UuidIdFactory(CheckId, "check"),
            checkpoint_ids=UuidIdFactory(CheckpointId, "checkpoint"),
            message_ids=UuidIdFactory(MessageId, "msg"),
            annotation_ids=UuidIdFactory(AnnotationId, "note"),
            authority_ids=UuidIdFactory(AuthorityId, "auth"),
            action_ids=UuidIdFactory(ActionId, "action"),
            artifact_ids=UuidIdFactory(ArtifactId, "artifact"),
            lease_ids=UuidIdFactory(LeaseId, "lease"),
            lease_tokens=lambda: secrets.token_urlsafe(32),
        )


SYSTEM_CLOCK: Clock = SystemClock()
