"""Exact durable evidence mapping for Engine command decisions."""

from __future__ import annotations

from enum import StrEnum

from openrund.codec import canonical_content_hash
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    AcceptedDecisionRecord,
    Command,
    CommandDecision,
    CommandDecisionRecord,
    CommandOrigin,
    CommandRejectionRecord,
    CommandWaitRecord,
    DeferredCommandDecision,
    DeferredDecisionRecord,
    RejectedCommandDecision,
    RejectedDecisionRecord,
    SupersededDecisionRecord,
    TargetEventAbsent,
    TargetEventPresent,
)
from openrund.contracts.content import Content
from openrund.contracts.events import ModelCommandRecordedPayload, RuntimeCommandRecordedPayload
from openrund.contracts.json import MISSING, JsonObject
from openrund.contracts.runs import WaitKind
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError


def build_decision_record(
    command: Command,
    decision: CommandDecision,
    *,
    deferred_wait_kind: WaitKind | None = None,
) -> CommandDecisionRecord:
    """Convert one runtime decision to its exact durable record branch."""

    if isinstance(decision, AcceptedCommandDecision):
        if not decision.result_event_ids:
            raise ValidationError(code="accepted_result_event_ids_required")
        return CommandDecisionRecord(
            command_id=command.command_id,
            branch=AcceptedDecisionRecord(
                decision_trace=decision.trace,
                result_event_ids=decision.result_event_ids,
            ),
            target_event=TargetEventPresent(event_id=decision.result_event_ids[0]),
        )
    if isinstance(decision, RejectedCommandDecision):
        return CommandDecisionRecord(
            command_id=command.command_id,
            branch=RejectedDecisionRecord(
                decision_trace=decision.trace,
                result_event_ids=(),
                rejection=CommandRejectionRecord(code=decision.reason),
            ),
            target_event=TargetEventAbsent(),
        )
    if isinstance(decision, DeferredCommandDecision):
        if deferred_wait_kind is None:
            raise ValidationError(code="deferred_wait_kind_required")
        return CommandDecisionRecord(
            command_id=command.command_id,
            branch=DeferredDecisionRecord(
                decision_trace=decision.trace,
                result_event_ids=(),
                wait=CommandWaitRecord(
                    wait_id=decision.wait_ids[0],
                    kind=deferred_wait_kind,
                ),
            ),
            target_event=TargetEventAbsent(),
        )
    return CommandDecisionRecord(
        command_id=command.command_id,
        branch=SupersededDecisionRecord(
            decision_trace=decision.trace,
            result_event_ids=(),
            declaration_only=True,
            replacement_command_id=decision.superseded_by_command_id,
        ),
        target_event=TargetEventAbsent(),
    )


def _record_metadata(command: Command) -> JsonObject:
    entries: list[tuple[str, object]] = [("commandOrigin", command.origin.value)]
    if command.idempotency_key is not MISSING:
        entries.append(("idempotencyKey", command.idempotency_key))
    if isinstance(command.created_at, Timestamp):
        entries.append(("createdAt", command.created_at.value))
    if command.metadata is not MISSING:
        entries.append(("command", command.metadata))
    return JsonObject(entries=tuple(entries))  # type: ignore[arg-type]


def build_command_recorded_payload(
    command: Command,
    decision: CommandDecision,
    *,
    deferred_wait_kind: WaitKind | None = None,
) -> ModelCommandRecordedPayload | RuntimeCommandRecordedPayload:
    """Build the exact v1 command.recorded payload for one attempt."""

    content = command.content if isinstance(command.content, Content) else Content()
    operation_kind = command.operation.kind
    operation_name = operation_kind.value if isinstance(operation_kind, StrEnum) else operation_kind
    common: dict[str, object] = {
        "command_id": command.command_id,
        "decision_record": build_decision_record(
            command,
            decision,
            deferred_wait_kind=deferred_wait_kind,
        ),
        "operation": operation_name,
        "content_hash": canonical_content_hash(content),
        "content": content,
        "model_call_id": command.model_call_id,
        "metadata": _record_metadata(command),
    }
    if command.origin is CommandOrigin.MODEL:
        common["provider"] = command.actor
        return ModelCommandRecordedPayload(**common)  # type: ignore[arg-type]
    common["origin_actor"] = command.actor
    return RuntimeCommandRecordedPayload(**common)  # type: ignore[arg-type]
