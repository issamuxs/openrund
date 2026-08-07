"""Deterministic Action status, uncertainty, and Receipt Views."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Literal, final

from openrund.contracts.capabilities import ActionFailure, ActionReliability
from openrund.contracts.content import Content, EffectEntry, Mutation
from openrund.contracts.events import (
    ActionCancelledPayload,
    ActionCompletedPayload,
    ActionCreatedPayload,
    ActionFailedPayload,
    ActionReconciledCancelledPayload,
    ActionReconciledCompletedPayload,
    ActionReconciledFailedPayload,
    ActionStartedPayload,
    ActionUnknownPayload,
)
from openrund.contracts.ids import ActionId, ArtifactId, CapabilityId, CommandId, EventId, RunId
from openrund.contracts.time import Timestamp
from openrund.views._history import KnownHistory

type ActionViewStatus = Literal[
    "requested",
    "started",
    "completed",
    "failed",
    "cancelled",
    "outcome_unknown",
    "reconciled",
]
type ReconciledOutcome = Literal["completed", "failed", "cancelled"]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionStatusEntry:
    action_id: ActionId
    capability_id: CapabilityId
    action_name: str
    status: ActionViewStatus
    mutation: Mutation | None = None
    unknown_event_id: EventId | None = None
    unknown_reason: str | None = None
    reliability: ActionReliability | None = None
    evidence: Content | None = None
    reconciled_event_id: EventId | None = None
    reconciled_outcome: ReconciledOutcome | None = None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class PendingActionReconciliation:
    action_id: ActionId
    unknown_event_id: EventId
    unknown_at: Timestamp
    reason: str
    reliability: ActionReliability
    evidence: Content | None
    note: Content | None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ReconciledActionOutcome:
    action_id: ActionId
    unknown_event_id: EventId
    reconciled_event_id: EventId
    reconciled_at: Timestamp
    outcome: ReconciledOutcome
    command_id: CommandId | None
    evidence: Content | None
    note: Content | None
    reconciled_by: str | None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionReconciliationView:
    pending: tuple[PendingActionReconciliation, ...]
    reconciled: tuple[ReconciledActionOutcome, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionUnknownDetails:
    reason: str
    reliability: ActionReliability
    evidence: Content | None
    note: Content | None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionReconciliationDetails:
    outcome: ReconciledOutcome
    unknown_event_id: EventId
    command_id: CommandId | None
    evidence: Content | None
    note: Content | None
    reconciled_by: str | None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionReceipt:
    action_id: ActionId
    run_id: RunId
    capability_id: CapabilityId
    action_name: str
    status: ActionViewStatus
    requested_event_id: EventId
    requested_at: Timestamp
    started_event_id: EventId | None = None
    started_at: Timestamp | None = None
    terminal_event_id: EventId | None = None
    completed_at: Timestamp | None = None
    failed_at: Timestamp | None = None
    cancelled_at: Timestamp | None = None
    unknown_at: Timestamp | None = None
    reconciled_at: Timestamp | None = None
    mutation: Mutation | None = None
    result: Content | None = None
    effects: tuple[EffectEntry, ...] = ()
    artifact_ids: tuple[ArtifactId, ...] = ()
    error: ActionFailure | None = None
    cancelled_reason: str | None = None
    unknown: ActionUnknownDetails | None = None
    reconciliation: ActionReconciliationDetails | None = None


def _content(value: object) -> Content | None:
    return value if isinstance(value, Content) else None


def _command_id(value: object) -> CommandId | None:
    return value if isinstance(value, CommandId) else None


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _action_status(history: KnownHistory) -> Mapping[ActionId, ActionStatusEntry]:
    actions: dict[ActionId, ActionStatusEntry] = {}
    for event in history.events:
        payload = event.payload
        if isinstance(payload, ActionCreatedPayload):
            if payload.action_id not in actions:
                actions[payload.action_id] = ActionStatusEntry(
                    action_id=payload.action_id,
                    capability_id=payload.capability_id,
                    action_name=payload.action_name,
                    status="requested",
                    mutation=(payload.mutation if isinstance(payload.mutation, Mutation) else None),
                )
            continue
        if not isinstance(
            payload,
            (
                ActionStartedPayload,
                ActionCompletedPayload,
                ActionFailedPayload,
                ActionCancelledPayload,
                ActionUnknownPayload,
                ActionReconciledCompletedPayload,
                ActionReconciledFailedPayload,
                ActionReconciledCancelledPayload,
            ),
        ):
            continue
        current = actions.get(payload.action_id)
        if current is None:
            continue
        if isinstance(payload, ActionStartedPayload):
            if current.status == "requested":
                actions[payload.action_id] = replace(current, status="started")
        elif isinstance(payload, ActionCompletedPayload):
            if current.status in ("requested", "started"):
                actions[payload.action_id] = replace(current, status="completed")
        elif isinstance(payload, ActionFailedPayload):
            if current.status in ("requested", "started"):
                actions[payload.action_id] = replace(current, status="failed")
        elif isinstance(payload, ActionCancelledPayload):
            if current.status in ("requested", "started"):
                actions[payload.action_id] = replace(current, status="cancelled")
        elif isinstance(payload, ActionUnknownPayload):
            if current.status in ("requested", "started"):
                actions[payload.action_id] = replace(
                    current,
                    status="outcome_unknown",
                    unknown_event_id=event.event_id,
                    unknown_reason=payload.reason,
                    reliability=payload.reliability,
                    evidence=_content(payload.evidence),
                )
        elif (
            isinstance(
                payload,
                (
                    ActionReconciledCompletedPayload,
                    ActionReconciledFailedPayload,
                    ActionReconciledCancelledPayload,
                ),
            )
            and current.status == "outcome_unknown"
        ):
            actions[payload.action_id] = replace(
                current,
                status="reconciled",
                unknown_event_id=payload.unknown_event_id,
                reconciled_event_id=event.event_id,
                reconciled_outcome=payload.outcome,
                evidence=_content(payload.evidence) or current.evidence,
            )
    return MappingProxyType(actions)


def _action_reconciliation(history: KnownHistory) -> ActionReconciliationView:
    pending: dict[EventId, PendingActionReconciliation] = {}
    reconciled: list[ReconciledActionOutcome] = []
    for event in history.events:
        payload = event.payload
        if isinstance(payload, ActionUnknownPayload):
            pending[event.event_id] = PendingActionReconciliation(
                action_id=payload.action_id,
                unknown_event_id=event.event_id,
                unknown_at=event.timestamp,
                reason=payload.reason,
                reliability=payload.reliability,
                evidence=_content(payload.evidence),
                note=_content(payload.note),
            )
        elif isinstance(
            payload,
            (
                ActionReconciledCompletedPayload,
                ActionReconciledFailedPayload,
                ActionReconciledCancelledPayload,
            ),
        ):
            pending.pop(payload.unknown_event_id, None)
            reconciled.append(
                ReconciledActionOutcome(
                    action_id=payload.action_id,
                    unknown_event_id=payload.unknown_event_id,
                    reconciled_event_id=event.event_id,
                    reconciled_at=event.timestamp,
                    outcome=payload.outcome,
                    command_id=_command_id(payload.command_id),
                    evidence=_content(payload.evidence),
                    note=_content(payload.note),
                    reconciled_by=_text(payload.reconciled_by),
                )
            )
    return ActionReconciliationView(pending=tuple(pending.values()), reconciled=tuple(reconciled))


def _action_receipts(history: KnownHistory) -> Mapping[ActionId, ActionReceipt]:
    receipts: dict[ActionId, ActionReceipt] = {}
    for event in history.events:
        payload = event.payload
        if isinstance(payload, ActionCreatedPayload):
            if payload.action_id not in receipts:
                receipts[payload.action_id] = ActionReceipt(
                    action_id=payload.action_id,
                    run_id=event.run_id,
                    capability_id=payload.capability_id,
                    action_name=payload.action_name,
                    status="requested",
                    requested_event_id=event.event_id,
                    requested_at=event.timestamp,
                    mutation=(payload.mutation if isinstance(payload.mutation, Mutation) else None),
                )
            continue
        if not isinstance(
            payload,
            (
                ActionStartedPayload,
                ActionCompletedPayload,
                ActionFailedPayload,
                ActionCancelledPayload,
                ActionUnknownPayload,
                ActionReconciledCompletedPayload,
                ActionReconciledFailedPayload,
                ActionReconciledCancelledPayload,
            ),
        ):
            continue
        current = receipts.get(payload.action_id)
        if current is None:
            continue
        if isinstance(payload, ActionStartedPayload):
            if current.status == "requested":
                receipts[payload.action_id] = replace(
                    current,
                    status="started",
                    started_event_id=event.event_id,
                    started_at=event.timestamp,
                )
        elif isinstance(payload, ActionCompletedPayload):
            if current.status in ("requested", "started"):
                receipts[payload.action_id] = replace(
                    current,
                    status="completed",
                    terminal_event_id=event.event_id,
                    completed_at=event.timestamp,
                    result=_content(payload.result),
                    effects=payload.effects,
                    artifact_ids=payload.artifact_ids,
                )
        elif isinstance(payload, ActionFailedPayload):
            if current.status in ("requested", "started"):
                receipts[payload.action_id] = replace(
                    current,
                    status="failed",
                    terminal_event_id=event.event_id,
                    failed_at=event.timestamp,
                    effects=payload.effects,
                    error=payload.error,
                )
        elif isinstance(payload, ActionCancelledPayload):
            if current.status in ("requested", "started"):
                receipts[payload.action_id] = replace(
                    current,
                    status="cancelled",
                    terminal_event_id=event.event_id,
                    cancelled_at=event.timestamp,
                    cancelled_reason=_text(payload.reason),
                )
        elif isinstance(payload, ActionUnknownPayload):
            if current.status in ("requested", "started"):
                receipts[payload.action_id] = replace(
                    current,
                    status="outcome_unknown",
                    terminal_event_id=event.event_id,
                    unknown_at=event.timestamp,
                    unknown=ActionUnknownDetails(
                        reason=payload.reason,
                        reliability=payload.reliability,
                        evidence=_content(payload.evidence),
                        note=_content(payload.note),
                    ),
                )
        elif (
            isinstance(
                payload,
                (
                    ActionReconciledCompletedPayload,
                    ActionReconciledFailedPayload,
                    ActionReconciledCancelledPayload,
                ),
            )
            and current.status == "outcome_unknown"
        ):
            receipts[payload.action_id] = replace(
                current,
                status="reconciled",
                terminal_event_id=event.event_id,
                reconciled_at=event.timestamp,
                reconciliation=ActionReconciliationDetails(
                    outcome=payload.outcome,
                    unknown_event_id=payload.unknown_event_id,
                    command_id=_command_id(payload.command_id),
                    evidence=_content(payload.evidence),
                    note=_content(payload.note),
                    reconciled_by=_text(payload.reconciled_by),
                ),
            )
    return MappingProxyType(receipts)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionViews:
    status: Mapping[ActionId, ActionStatusEntry]
    reconciliation: ActionReconciliationView
    receipts: Mapping[ActionId, ActionReceipt]


def reduce_actions(history: KnownHistory) -> ActionViews:
    """Derive all Action explanatory surfaces from one immutable history."""

    return ActionViews(
        status=_action_status(history),
        reconciliation=_action_reconciliation(history),
        receipts=_action_receipts(history),
    )
