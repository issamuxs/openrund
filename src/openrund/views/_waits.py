"""Deterministic, non-authoritative Wait lifecycle projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, final

from openrund.contracts.events import (
    AggregateWaitCreatedPayload,
    AggregateWaitResolvedPayload,
    ApprovalWaitCancelledPayload,
    ApprovalWaitCreatedPayload,
    ApprovalWaitExpiredPayload,
    ApprovalWaitResolvedPayload,
    EventPayload,
    InteractionWaitCancelledPayload,
    InteractionWaitCreatedPayload,
    InteractionWaitExpiredPayload,
    InteractionWaitResolvedPayload,
    JoinWaitCancelledPayload,
    JoinWaitCreatedPayload,
    JoinWaitExpiredPayload,
    JoinWaitResolvedPayload,
    ReconciliationWaitCancelledPayload,
    ReconciliationWaitCreatedPayload,
    ReconciliationWaitExpiredPayload,
    ReconciliationWaitResolvedPayload,
    TimerWaitCancelledPayload,
    TimerWaitCreatedPayload,
    TimerWaitExpiredPayload,
    TimerWaitResolvedPayload,
)
from openrund.contracts.ids import EventId, WaitId
from openrund.contracts.runs import WaitKind
from openrund.contracts.time import Timestamp
from openrund.views._history import KnownHistory

type WaitRequestPayload = (
    ApprovalWaitCreatedPayload
    | InteractionWaitCreatedPayload
    | TimerWaitCreatedPayload
    | JoinWaitCreatedPayload
    | ReconciliationWaitCreatedPayload
)
type WaitTerminalPayload = (
    ApprovalWaitResolvedPayload
    | InteractionWaitResolvedPayload
    | TimerWaitResolvedPayload
    | JoinWaitResolvedPayload
    | ReconciliationWaitResolvedPayload
    | ApprovalWaitCancelledPayload
    | InteractionWaitCancelledPayload
    | TimerWaitCancelledPayload
    | JoinWaitCancelledPayload
    | ReconciliationWaitCancelledPayload
    | ApprovalWaitExpiredPayload
    | InteractionWaitExpiredPayload
    | TimerWaitExpiredPayload
    | JoinWaitExpiredPayload
    | ReconciliationWaitExpiredPayload
)
type WaitTerminalOutcome = Literal[
    "approved",
    "denied",
    "resolved",
    "fired",
    "cancelled",
    "expired",
]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class PendingWait:
    wait_id: WaitId
    kind: WaitKind
    request_event_id: EventId
    requested_at: Timestamp
    request: WaitRequestPayload


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class TerminalWait:
    wait_id: WaitId
    kind: WaitKind
    outcome: WaitTerminalOutcome
    terminal_event_id: EventId
    terminal_at: Timestamp
    terminal: WaitTerminalPayload
    request: PendingWait | None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class WaitKindQueue:
    kind: WaitKind
    pending: tuple[PendingWait, ...]
    terminal: tuple[TerminalWait, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AggregateWaitCreatedFact:
    event_id: EventId
    created_at: Timestamp
    payload: AggregateWaitCreatedPayload


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AggregateWaitResolvedFact:
    event_id: EventId
    resolved_at: Timestamp
    payload: AggregateWaitResolvedPayload


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class WaitQueues:
    approvals: WaitKindQueue
    interactions: WaitKindQueue
    timers: WaitKindQueue
    joins: WaitKindQueue
    reconciliations: WaitKindQueue
    all_pending: tuple[PendingWait, ...]
    all_terminal: tuple[TerminalWait, ...]
    aggregate_created: tuple[AggregateWaitCreatedFact, ...]
    aggregate_resolved: tuple[AggregateWaitResolvedFact, ...]


def _request(payload: EventPayload) -> tuple[WaitId, WaitKind, WaitRequestPayload] | None:
    if isinstance(payload, ApprovalWaitCreatedPayload):
        return payload.wait_id, WaitKind.APPROVAL, payload
    if isinstance(payload, InteractionWaitCreatedPayload):
        return payload.wait_id, WaitKind.INTERACTION, payload
    if isinstance(payload, TimerWaitCreatedPayload):
        return payload.wait_id, WaitKind.TIMER, payload
    if isinstance(payload, JoinWaitCreatedPayload):
        return payload.wait_id, WaitKind.JOIN, payload
    if isinstance(payload, ReconciliationWaitCreatedPayload):
        return payload.wait_id, WaitKind.RECONCILIATION, payload
    return None


def _terminal(
    payload: EventPayload,
) -> tuple[WaitId, WaitKind, WaitTerminalOutcome, WaitTerminalPayload] | None:
    if isinstance(payload, ApprovalWaitResolvedPayload):
        return payload.wait_id, WaitKind.APPROVAL, payload.decision, payload
    if isinstance(payload, InteractionWaitResolvedPayload):
        return payload.wait_id, WaitKind.INTERACTION, "resolved", payload
    if isinstance(payload, TimerWaitResolvedPayload):
        return payload.wait_id, WaitKind.TIMER, "fired", payload
    if isinstance(payload, JoinWaitResolvedPayload):
        return payload.wait_id, WaitKind.JOIN, "resolved", payload
    if isinstance(payload, ReconciliationWaitResolvedPayload):
        return payload.wait_id, WaitKind.RECONCILIATION, "resolved", payload
    if isinstance(payload, ApprovalWaitCancelledPayload):
        return payload.wait_id, WaitKind.APPROVAL, "cancelled", payload
    if isinstance(payload, InteractionWaitCancelledPayload):
        return payload.wait_id, WaitKind.INTERACTION, "cancelled", payload
    if isinstance(payload, TimerWaitCancelledPayload):
        return payload.wait_id, WaitKind.TIMER, "cancelled", payload
    if isinstance(payload, JoinWaitCancelledPayload):
        return payload.wait_id, WaitKind.JOIN, "cancelled", payload
    if isinstance(payload, ReconciliationWaitCancelledPayload):
        return payload.wait_id, WaitKind.RECONCILIATION, "cancelled", payload
    if isinstance(payload, ApprovalWaitExpiredPayload):
        return payload.wait_id, WaitKind.APPROVAL, "expired", payload
    if isinstance(payload, InteractionWaitExpiredPayload):
        return payload.wait_id, WaitKind.INTERACTION, "expired", payload
    if isinstance(payload, TimerWaitExpiredPayload):
        return payload.wait_id, WaitKind.TIMER, "expired", payload
    if isinstance(payload, JoinWaitExpiredPayload):
        return payload.wait_id, WaitKind.JOIN, "expired", payload
    if isinstance(payload, ReconciliationWaitExpiredPayload):
        return payload.wait_id, WaitKind.RECONCILIATION, "expired", payload
    return None


def _queue(
    kind: WaitKind,
    pending: dict[tuple[WaitKind, WaitId], PendingWait],
    terminal: list[TerminalWait],
) -> WaitKindQueue:
    return WaitKindQueue(
        kind=kind,
        pending=tuple(item for item in pending.values() if item.kind is kind),
        terminal=tuple(item for item in terminal if item.kind is kind),
    )


def reduce_waits(history: KnownHistory) -> WaitQueues:
    """Replay all Wait facts without resolving, expiring, or appending anything."""

    pending: dict[tuple[WaitKind, WaitId], PendingWait] = {}
    terminal: list[TerminalWait] = []
    aggregate_created: list[AggregateWaitCreatedFact] = []
    aggregate_resolved: list[AggregateWaitResolvedFact] = []

    for event in history.events:
        payload = event.payload
        if isinstance(payload, AggregateWaitCreatedPayload):
            aggregate_created.append(
                AggregateWaitCreatedFact(
                    event_id=event.event_id,
                    created_at=event.timestamp,
                    payload=payload,
                )
            )
            continue
        if isinstance(payload, AggregateWaitResolvedPayload):
            aggregate_resolved.append(
                AggregateWaitResolvedFact(
                    event_id=event.event_id,
                    resolved_at=event.timestamp,
                    payload=payload,
                )
            )
            continue

        request = _request(payload)
        if request is not None:
            wait_id, kind, request_payload = request
            pending[(kind, wait_id)] = PendingWait(
                wait_id=wait_id,
                kind=kind,
                request_event_id=event.event_id,
                requested_at=event.timestamp,
                request=request_payload,
            )
            continue

        ended = _terminal(payload)
        if ended is None:
            continue
        wait_id, kind, outcome, terminal_payload = ended
        matched = pending.pop((kind, wait_id), None)
        terminal.append(
            TerminalWait(
                wait_id=wait_id,
                kind=kind,
                outcome=outcome,
                terminal_event_id=event.event_id,
                terminal_at=event.timestamp,
                terminal=terminal_payload,
                request=matched,
            )
        )

    return WaitQueues(
        approvals=_queue(WaitKind.APPROVAL, pending, terminal),
        interactions=_queue(WaitKind.INTERACTION, pending, terminal),
        timers=_queue(WaitKind.TIMER, pending, terminal),
        joins=_queue(WaitKind.JOIN, pending, terminal),
        reconciliations=_queue(WaitKind.RECONCILIATION, pending, terminal),
        all_pending=tuple(pending.values()),
        all_terminal=tuple(terminal),
        aggregate_created=tuple(aggregate_created),
        aggregate_resolved=tuple(aggregate_resolved),
    )
