"""Narrow immutable dependencies for the core Engine authority boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import final

from openrund.contracts.ids import (
    AnnotationId,
    AuthorityId,
    CheckId,
    CheckpointId,
    DelegationId,
    EventId,
    MessageId,
    RunId,
    WaitId,
)
from openrund.engine._governance import GovernanceContext
from openrund.errors import ValidationError
from openrund.ports.events import AtomicEventStore, EventStore
from openrund.ports.runtime import Clock, IdFactory


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class EngineDependencies:
    event_store: EventStore
    clock: Clock
    event_ids: IdFactory[EventId]
    message_ids: IdFactory[MessageId]
    run_ids: IdFactory[RunId] | None = None
    wait_ids: IdFactory[WaitId] | None = None
    delegation_ids: IdFactory[DelegationId] | None = None
    check_ids: IdFactory[CheckId] | None = None
    checkpoint_ids: IdFactory[CheckpointId] | None = None
    annotation_ids: IdFactory[AnnotationId] | None = None
    authority_ids: IdFactory[AuthorityId] | None = None
    atomic_event_store: AtomicEventStore | None = None
    governance: GovernanceContext = field(default_factory=GovernanceContext)
    conflict_retries: int = 3

    def __post_init__(self) -> None:
        if (
            isinstance(self.conflict_retries, bool)
            or not isinstance(self.conflict_retries, int)
            or not 0 <= self.conflict_retries <= 100
        ):
            raise ValidationError(code="engine_conflict_retries_invalid")
        if not isinstance(self.governance, GovernanceContext):
            raise ValidationError(code="engine_governance_invalid")
        if self.atomic_event_store is not None and self.atomic_event_store is not self.event_store:
            raise ValidationError(code="engine_event_store_custody_mismatch")
