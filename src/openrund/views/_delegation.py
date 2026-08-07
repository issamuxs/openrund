"""Deterministic Delegation lifecycle, handoff, and join projections."""

from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Literal, final

from openrund.contracts.events import (
    DelegationCancelledPayload,
    DelegationCompletedPayload,
    DelegationContractCreatedPayload,
    DelegationFailedPayload,
    DelegationHandoffCreatedPayload,
    EventPayload,
    JoinWaitCancelledPayload,
    JoinWaitCreatedPayload,
    JoinWaitExpiredPayload,
    JoinWaitResolvedPayload,
)
from openrund.contracts.ids import EventId, RunId, WaitId
from openrund.contracts.runs import DelegationJoinMode
from openrund.contracts.time import Timestamp
from openrund.views._history import KnownHistory

type DelegatedRunStatus = Literal["establishing", "running", "completed", "failed", "cancelled"]
type DelegationTerminalPayload = (
    DelegationCompletedPayload | DelegationFailedPayload | DelegationCancelledPayload
)
type DelegationTerminalStatus = Literal["completed", "failed", "cancelled"]
type DelegationJoinStatus = Literal["pending", "completed", "cancelled", "expired"]
type JoinTerminalPayload = (
    JoinWaitResolvedPayload | JoinWaitCancelledPayload | JoinWaitExpiredPayload
)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationEstablishmentFact:
    event_id: EventId
    established_at: Timestamp
    payload: DelegationHandoffCreatedPayload


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationTerminalFact:
    delegated_run_id: RunId
    status: DelegationTerminalStatus
    event_id: EventId
    recorded_at: Timestamp
    payload: DelegationTerminalPayload


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegatedRunEntry:
    parent_run_id: RunId
    delegated_run_id: RunId
    status: DelegatedRunStatus
    creation_event_id: EventId
    created_at: Timestamp
    creation: DelegationContractCreatedPayload
    establishment: DelegationEstablishmentFact | None = None
    terminal: DelegationTerminalFact | None = None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class JoinTerminalFact:
    event_id: EventId
    recorded_at: Timestamp
    payload: JoinTerminalPayload


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationJoinEntry:
    wait_id: WaitId
    status: DelegationJoinStatus
    requested_event_id: EventId
    requested_at: Timestamp
    request: JoinWaitCreatedPayload
    terminal: JoinTerminalFact | None
    completed_run_ids: tuple[RunId, ...]
    failed_run_ids: tuple[RunId, ...]
    cancelled_run_ids: tuple[RunId, ...]
    pending_run_ids: tuple[RunId, ...]
    satisfied: bool


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OrphanDelegationEstablishment:
    event_id: EventId
    recorded_at: Timestamp
    payload: DelegationHandoffCreatedPayload


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OrphanJoinTerminal:
    event_id: EventId
    recorded_at: Timestamp
    payload: JoinTerminalPayload


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationView:
    delegated_runs: MappingProxyType[RunId, DelegatedRunEntry]
    handoffs: MappingProxyType[RunId, tuple[DelegationTerminalFact, ...]]
    joins: MappingProxyType[WaitId, DelegationJoinEntry]
    orphan_establishments: tuple[OrphanDelegationEstablishment, ...]
    orphan_join_terminals: tuple[OrphanJoinTerminal, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class _JoinSeed:
    request_event_id: EventId
    requested_at: Timestamp
    request: JoinWaitCreatedPayload
    status: DelegationJoinStatus = "pending"
    terminal: JoinTerminalFact | None = None


def _delegation_terminal(
    payload: EventPayload,
) -> tuple[RunId, DelegationTerminalStatus, DelegationTerminalPayload] | None:
    if isinstance(payload, DelegationCompletedPayload):
        return payload.delegated_run_id, "completed", payload
    if isinstance(payload, DelegationFailedPayload):
        return payload.delegated_run_id, "failed", payload
    if isinstance(payload, DelegationCancelledPayload):
        return payload.delegated_run_id, "cancelled", payload
    return None


def _join_terminal(
    payload: EventPayload,
) -> tuple[WaitId, DelegationJoinStatus, JoinTerminalPayload] | None:
    if isinstance(payload, JoinWaitResolvedPayload):
        return payload.wait_id, "completed", payload
    if isinstance(payload, JoinWaitCancelledPayload):
        return payload.wait_id, "cancelled", payload
    if isinstance(payload, JoinWaitExpiredPayload):
        return payload.wait_id, "expired", payload
    return None


def _ordered_targets(
    targets: tuple[RunId, ...],
    selected: set[RunId],
) -> tuple[RunId, ...]:
    return tuple(run_id for run_id in targets if run_id in selected)


def _join_entry(
    seed: _JoinSeed,
    child_outcomes: dict[RunId, DelegationTerminalStatus],
) -> DelegationJoinEntry:
    request = seed.request
    completed = {run_id for run_id, outcome in child_outcomes.items() if outcome == "completed"}
    failed = {run_id for run_id, outcome in child_outcomes.items() if outcome == "failed"}
    cancelled = {run_id for run_id, outcome in child_outcomes.items() if outcome == "cancelled"}
    if seed.terminal is not None and isinstance(seed.terminal.payload, JoinWaitResolvedPayload):
        completed.update(seed.terminal.payload.completed_run_ids)
        reported_terminal = set(seed.terminal.payload.terminal_run_ids)
    else:
        reported_terminal = set()

    targets = request.target_run_ids
    completed_ids = _ordered_targets(targets, completed)
    failed_ids = _ordered_targets(targets, failed)
    cancelled_ids = _ordered_targets(targets, cancelled)
    known_terminal = completed | failed | cancelled | reported_terminal
    pending_ids = tuple(run_id for run_id in targets if run_id not in known_terminal)

    if request.outcome_filter == "completed_only":
        eligible = completed
    elif request.outcome_filter == "completed_or_failed":
        eligible = completed | failed
    else:
        eligible = known_terminal
    eligible_count = sum(run_id in eligible for run_id in targets)
    if request.mode is DelegationJoinMode.ALL:
        satisfied = eligible_count == len(targets)
    elif request.mode is DelegationJoinMode.ANY:
        satisfied = eligible_count >= 1
    else:
        assert isinstance(request.quorum, int)
        satisfied = eligible_count >= request.quorum

    return DelegationJoinEntry(
        wait_id=request.wait_id,
        status=seed.status,
        requested_event_id=seed.request_event_id,
        requested_at=seed.requested_at,
        request=request,
        terminal=seed.terminal,
        completed_run_ids=completed_ids,
        failed_run_ids=failed_ids,
        cancelled_run_ids=cancelled_ids,
        pending_run_ids=pending_ids,
        satisfied=satisfied,
    )


def reduce_delegation(history: KnownHistory) -> DelegationView:
    """Replay Delegation and join facts without advancing or scheduling a parent Run."""

    delegated_runs: dict[RunId, DelegatedRunEntry] = {}
    handoff_lists: dict[RunId, list[DelegationTerminalFact]] = {}
    child_outcomes: dict[RunId, DelegationTerminalStatus] = {}
    joins: dict[WaitId, _JoinSeed] = {}
    orphan_establishments: list[OrphanDelegationEstablishment] = []
    orphan_join_terminals: list[OrphanJoinTerminal] = []

    for event in history.events:
        payload = event.payload
        if isinstance(payload, DelegationContractCreatedPayload):
            if payload.delegated_run_id not in delegated_runs:
                delegated_runs[payload.delegated_run_id] = DelegatedRunEntry(
                    parent_run_id=event.run_id,
                    delegated_run_id=payload.delegated_run_id,
                    status="establishing",
                    creation_event_id=event.event_id,
                    created_at=event.timestamp,
                    creation=payload,
                )
            continue
        if isinstance(payload, DelegationHandoffCreatedPayload):
            establishment = DelegationEstablishmentFact(
                event_id=event.event_id,
                established_at=event.timestamp,
                payload=payload,
            )
            current = delegated_runs.get(payload.delegated_run_id)
            if current is None:
                orphan_establishments.append(
                    OrphanDelegationEstablishment(
                        event_id=event.event_id,
                        recorded_at=event.timestamp,
                        payload=payload,
                    )
                )
            elif current.establishment is None:
                delegated_runs[payload.delegated_run_id] = replace(
                    current,
                    status=("running" if current.terminal is None else current.status),
                    establishment=establishment,
                )
            continue

        terminal = _delegation_terminal(payload)
        if terminal is not None:
            delegated_run_id, status, terminal_payload = terminal
            fact = DelegationTerminalFact(
                delegated_run_id=delegated_run_id,
                status=status,
                event_id=event.event_id,
                recorded_at=event.timestamp,
                payload=terminal_payload,
            )
            handoff_lists.setdefault(delegated_run_id, []).append(fact)
            child_outcomes.setdefault(delegated_run_id, status)
            current = delegated_runs.get(delegated_run_id)
            if current is not None and current.terminal is None:
                delegated_runs[delegated_run_id] = replace(
                    current,
                    status=status,
                    terminal=fact,
                )
            continue

        if isinstance(payload, JoinWaitCreatedPayload):
            if payload.wait_id not in joins:
                joins[payload.wait_id] = _JoinSeed(
                    request_event_id=event.event_id,
                    requested_at=event.timestamp,
                    request=payload,
                )
            continue
        terminal_join = _join_terminal(payload)
        if terminal_join is None:
            continue
        join_wait_id, join_status, join_terminal_payload = terminal_join
        join_fact = JoinTerminalFact(
            event_id=event.event_id,
            recorded_at=event.timestamp,
            payload=join_terminal_payload,
        )
        current_join = joins.get(join_wait_id)
        if current_join is None or current_join.terminal is not None:
            orphan_join_terminals.append(
                OrphanJoinTerminal(
                    event_id=event.event_id,
                    recorded_at=event.timestamp,
                    payload=join_terminal_payload,
                )
            )
        else:
            joins[join_wait_id] = replace(
                current_join,
                status=join_status,
                terminal=join_fact,
            )

    immutable_handoffs = {run_id: tuple(facts) for run_id, facts in handoff_lists.items()}
    immutable_joins = {
        wait_id: _join_entry(seed, child_outcomes) for wait_id, seed in joins.items()
    }
    return DelegationView(
        delegated_runs=MappingProxyType(delegated_runs),
        handoffs=MappingProxyType(immutable_handoffs),
        joins=MappingProxyType(immutable_joins),
        orphan_establishments=tuple(orphan_establishments),
        orphan_join_terminals=tuple(orphan_join_terminals),
    )
