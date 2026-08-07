"""Read-only operator inspection over canonical history and Artifact custody."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import final

from openrund._version import __version__
from openrund.bundles import (
    ImportedBundle,
    ResumeAssessment,
    assess_resume,
    export_bundle,
    import_bundle,
    replay_bundle,
    verify_bundle,
)
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    AcceptedDecisionRecord,
    AddMessageOperation,
    BootstrapRunOperation,
    Command,
    CommandDecisionTraceEntry,
    CommandOperation,
    CommandOrigin,
    CommandResult,
    DeferredCommandDecision,
    DeferredDecisionRecord,
    ReconcileActionOperation,
    RecordCheckOperation,
    RejectedCommandDecision,
    RejectedDecisionRecord,
    ResolveApprovalOperation,
    ResumeApprovedActionOperation,
    SupersededCommandDecision,
    SupersededDecisionRecord,
)
from openrund.contracts.content import Content, EffectEntry, Mutation
from openrund.contracts.events import (
    ModelCommandRecordedPayload,
    RuntimeCommandRecordedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import ActionId, ArtifactId, CommandId, RunId, WaitId
from openrund.contracts.json import MISSING, JsonObject, JsonValue, freeze_json
from openrund.contracts.portable import BundleProfile
from openrund.contracts.runs import CheckStatus
from openrund.engine import RuntimeEngine
from openrund.errors import StorageIntegrityError, ValidationError
from openrund.operator._model import (
    ActionReceiptData,
    ArtifactInspectionData,
    BundleAssessmentData,
    BundleExportData,
    BundleImportData,
    BundleReplayData,
    BundleVerificationData,
    CommandExplanationData,
    CommandResultData,
    OperatorExitCode,
    OperatorResult,
    RunChecksData,
    RunInspectionData,
    RunReadinessData,
    RunReplayData,
    RunTimelineData,
    RunWaitsData,
)
from openrund.paths import PathInput, normalize_local_path
from openrund.ports.artifacts import ArtifactEntry, ArtifactStore
from openrund.ports.events import EventStore
from openrund.ports.runtime import Clock, IdFactory
from openrund.storage import materialize_run_home, run_home
from openrund.views import CompleteViewReplay, rebuild_views
from openrund.views._actions import ActionReceipt
from openrund.views._artifacts import ArtifactIndexEntry
from openrund.views._model import RunViewBundle
from openrund.views._run_status import (
    ArtifactRequirementStatus,
    NamedCheckResult,
    ReadinessBlocker,
)


def _json_object(value: object) -> JsonObject:
    frozen = freeze_json(value)
    if not isinstance(frozen, JsonObject):
        raise ValidationError(code="operator_render_object_invalid")
    return frozen


def _optional(value: object) -> JsonValue:
    if value is MISSING or value is None:
        return None
    if isinstance(value, StrEnum):
        return value.value
    return freeze_json(value)


def _not_found(command: str, code: str, message: str, data: object) -> OperatorResult[JsonObject]:
    return OperatorResult.failed(
        command=command,
        code=code,
        message=message,
        exit_code=OperatorExitCode.NOT_FOUND,
        data=data,
    )


def _content(value: Content | None) -> JsonValue:
    if value is None:
        return None
    return _json_object(
        {
            "preview": _optional(value.preview),
            "data": _optional(value.data),
            "artifact_ids": [item.value for item in value.artifact_ids],
            "artifact_refs": [item.artifact_id.value for item in value.artifact_refs],
            "metadata": _optional(value.metadata),
        }
    )


def _mutation(value: Mutation | None) -> JsonValue:
    if value is None:
        return None
    return _json_object(
        {
            "operation": value.operation_kind.value,
            "resources": list(value.affected_resources),
            "reversibility": _optional(value.reversibility),
        }
    )


def _effect(value: EffectEntry) -> JsonObject:
    return _json_object(
        {
            "kind": value.kind,
            "summary": _optional(value.summary),
            "artifact_ids": [item.value for item in value.artifact_ids],
        }
    )


def _named_check(value: NamedCheckResult) -> JsonObject:
    return _json_object(
        {
            "name": value.name,
            "status": value.status,
            "check_id": value.check_id.value,
            "event_id": value.event_id.value,
        }
    )


def _artifact_requirement(value: ArtifactRequirementStatus) -> JsonObject:
    return _json_object(
        {
            "kind": value.artifact_kind,
            "satisfied": value.satisfied,
            "artifact_ids": [item.value for item in value.artifact_ids],
        }
    )


def _blocker(value: ReadinessBlocker) -> JsonObject:
    return _json_object(
        {
            "code": value.code.value,
            "wait_id": value.wait_id.value if value.wait_id is not None else None,
            "artifact_kind": value.artifact_kind,
            "action_id": value.action_id.value if value.action_id is not None else None,
            "check": value.check,
            "observed_check_status": value.observed_check_status,
        }
    )


def _trace(value: CommandDecisionTraceEntry) -> JsonObject:
    return _json_object(
        {
            "criterion": value.criterion.value,
            "result": value.result.value,
            "reason": _optional(value.reason),
            "related_entity_ids": list(value.related_entity_ids),
        }
    )


def _receipt(value: ActionReceipt) -> JsonObject:
    unknown: JsonValue = None
    if value.unknown is not None:
        unknown = _json_object(
            {
                "reason": value.unknown.reason,
                "reliability": value.unknown.reliability.value,
                "evidence": _content(value.unknown.evidence),
                "note": _content(value.unknown.note),
            }
        )
    reconciliation: JsonValue = None
    if value.reconciliation is not None:
        reconciliation = _json_object(
            {
                "outcome": value.reconciliation.outcome,
                "unknown_event_id": value.reconciliation.unknown_event_id.value,
                "command_id": (
                    value.reconciliation.command_id.value
                    if value.reconciliation.command_id is not None
                    else None
                ),
                "reconciled_by": value.reconciliation.reconciled_by,
                "evidence": _content(value.reconciliation.evidence),
                "note": _content(value.reconciliation.note),
            }
        )
    return _json_object(
        {
            "run_id": value.run_id.value,
            "action_id": value.action_id.value,
            "capability_id": value.capability_id.value,
            "action_name": value.action_name,
            "status": value.status,
            "requested_event_id": value.requested_event_id.value,
            "terminal_event_id": (
                value.terminal_event_id.value if value.terminal_event_id is not None else None
            ),
            "mutation": _mutation(value.mutation),
            "result": _content(value.result),
            "effects": [_effect(item) for item in value.effects],
            "artifact_ids": [item.value for item in value.artifact_ids],
            "unknown": unknown,
            "reconciliation": reconciliation,
        }
    )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OperatorServiceDependencies:
    event_store: EventStore
    artifact_store: ArtifactStore
    engine: RuntimeEngine
    clock: Clock
    command_ids: IdFactory[CommandId]
    runtime_home: PathInput
    required_root_mappings: tuple[str, ...] = ()
    available_capabilities: tuple[str, ...] = ()
    available_providers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not all(
            callable(getattr(self.event_store, name, None))
            for name in ("read", "append", "has_event")
        ):
            raise ValidationError(code="operator_event_store_invalid")
        if not all(
            callable(getattr(self.artifact_store, name, None))
            for name in ("get", "get_blob", "put")
        ):
            raise ValidationError(code="operator_artifact_store_invalid")
        if not isinstance(self.engine, RuntimeEngine):
            raise ValidationError(code="operator_engine_invalid")
        if not callable(getattr(self.clock, "now", None)):
            raise ValidationError(code="operator_clock_invalid")
        if not callable(getattr(self.command_ids, "new_id", None)):
            raise ValidationError(code="operator_command_ids_invalid")
        home = normalize_local_path(self.runtime_home).path
        capabilities = tuple(self.available_capabilities)
        providers = tuple(self.available_providers)
        roots = tuple(self.required_root_mappings)
        if any(
            not isinstance(item, str) or item == "" for item in (*roots, *capabilities, *providers)
        ):
            raise ValidationError(code="operator_availability_invalid")
        object.__setattr__(self, "runtime_home", home)
        object.__setattr__(self, "required_root_mappings", roots)
        object.__setattr__(self, "available_capabilities", capabilities)
        object.__setattr__(self, "available_providers", providers)


@final
class OperatorService:
    __slots__ = ("_dependencies",)

    def __init__(self, dependencies: OperatorServiceDependencies) -> None:
        if not isinstance(dependencies, OperatorServiceDependencies):
            raise ValidationError(code="operator_dependencies_invalid")
        self._dependencies = dependencies

    async def _submit(
        self,
        *,
        command_name: str,
        title: str,
        run_id: RunId,
        operation: CommandOperation,
        origin: CommandOrigin = CommandOrigin.OPERATOR,
    ) -> OperatorResult[CommandResultData | JsonObject]:
        engine = self._dependencies.engine
        command_id = self._dependencies.command_ids.new_id()
        result = await engine.submit(
            Command(
                command_id=command_id,
                run_id=run_id,
                origin=origin,
                operation=operation,
                created_at=self._dependencies.clock.now(),
            )
        )
        return self._command_result(command_name, title, run_id, result)

    @staticmethod
    def _command_result(
        command_name: str,
        title: str,
        run_id: RunId,
        result: CommandResult,
    ) -> OperatorResult[CommandResultData | JsonObject]:
        decision = result.decision
        if isinstance(decision, AcceptedCommandDecision):
            data = CommandResultData(
                run_id=run_id.value,
                command_id=result.command_id.value,
                decision=decision.kind,
                result_event_ids=tuple(item.value for item in decision.result_event_ids),
            )
            return OperatorResult.success(command=command_name, title=title, data=data)
        if isinstance(decision, DeferredCommandDecision):
            data = CommandResultData(
                run_id=run_id.value,
                command_id=result.command_id.value,
                decision=decision.kind,
                wait_ids=tuple(item.value for item in decision.wait_ids),
                reason=decision.reason,
            )
            return OperatorResult.success(command=command_name, title=title, data=data)
        if isinstance(decision, SupersededCommandDecision):
            data = CommandResultData(
                run_id=run_id.value,
                command_id=result.command_id.value,
                decision=decision.kind,
                superseded_by_command_id=decision.superseded_by_command_id.value,
                reason=decision.reason,
            )
            return OperatorResult.success(command=command_name, title=title, data=data)
        assert isinstance(decision, RejectedCommandDecision)
        return OperatorResult.failed(
            command=command_name,
            code=decision.reason,
            message="The Engine rejected this command",
            exit_code=OperatorExitCode.REJECTED,
            data={
                "run_id": run_id.value,
                "command_id": result.command_id.value,
                "decision": decision.kind,
                "reason": decision.reason,
            },
        )

    async def create_run(
        self,
        run_id: RunId,
        /,
        *,
        title: str | None = None,
        objective: str | None = None,
    ) -> OperatorResult[CommandResultData | JsonObject]:
        layout = run_home(self._dependencies.runtime_home, run_id)
        result = await self._submit(
            command_name="runs create",
            title="Run created",
            run_id=run_id,
            operation=BootstrapRunOperation(
                root_id=run_id,
                title=title,
                objective=objective,
                metadata={
                    "execution": {
                        "runtime_home": str(layout.runtime),
                        "workspace": str(layout.workspace),
                        "exports": str(layout.exports),
                    }
                },  # type: ignore[arg-type]
                start_reason="operator create",
            ),
        )
        if result.ok:
            materialize_run_home(layout)
        return result

    async def advance_run(
        self, run_id: RunId, message: str, /
    ) -> OperatorResult[CommandResultData | JsonObject]:
        if not isinstance(message, str) or message == "":
            raise ValidationError(code="operator_message_invalid")
        return await self._submit(
            command_name="runs advance",
            title="Run advanced",
            run_id=run_id,
            operation=AddMessageOperation(message=Content(preview=message)),
        )

    async def resolve_approval(
        self,
        run_id: RunId,
        wait_id: WaitId,
        /,
        *,
        decision: str,
        approved_input: JsonObject | None = None,
        note: str | None = None,
        resolved_by: str = "operator",
    ) -> OperatorResult[CommandResultData | JsonObject]:
        if decision not in ("approved", "denied", "cancelled"):
            raise ValidationError(code="resolve_approval_decision_invalid")
        typed_decision = decision
        return await self._submit(
            command_name="waits resolve",
            title="Approval wait resolved",
            run_id=run_id,
            operation=ResolveApprovalOperation(
                wait_id=wait_id,
                decision=typed_decision,  # type: ignore[arg-type]
                approved_input=approved_input,
                note=Content(preview=note) if note is not None else None,
                resolved_by=resolved_by,
            ),
        )

    async def resume_approval(
        self, run_id: RunId, wait_id: WaitId, /
    ) -> OperatorResult[CommandResultData | JsonObject]:
        return await self._submit(
            command_name="waits resume",
            title="Approved action resumed",
            run_id=run_id,
            operation=ResumeApprovedActionOperation(wait_id=wait_id),
            origin=CommandOrigin.SYSTEM,
        )

    async def reconcile_action(
        self,
        run_id: RunId,
        action_id: ActionId,
        /,
        *,
        outcome: str,
        evidence: str,
        note: str | None = None,
        reconciled_by: str = "operator",
    ) -> OperatorResult[CommandResultData | JsonObject]:
        if outcome not in ("completed", "failed", "cancelled"):
            raise ValidationError(code="reconcile_action_outcome_invalid")
        _events, replay = await self._history(run_id, "actions reconcile")
        if isinstance(replay, OperatorResult):
            return replay
        pending = next(
            (
                item
                for item in replay.views.action_reconciliation.pending
                if item.action_id == action_id
            ),
            None,
        )
        if pending is None:
            return _not_found(
                "actions reconcile",
                "action_unknown_not_found",
                "No unresolved unknown outcome was found",
                {"run_id": run_id.value, "action_id": action_id.value},
            )
        return await self._submit(
            command_name="actions reconcile",
            title="Action reconciled",
            run_id=run_id,
            operation=ReconcileActionOperation(
                action_id=action_id,
                unknown_event_id=pending.unknown_event_id,
                outcome=outcome,  # type: ignore[arg-type]
                evidence=Content(preview=evidence),
                note=Content(preview=note) if note is not None else None,
                reconciled_by=reconciled_by,
            ),
        )

    async def record_check(
        self,
        run_id: RunId,
        name: str,
        /,
        *,
        status: CheckStatus,
        summary: str,
        subject: str = "run",
        rule: str = "operator_check",
        validator: str = "operator",
    ) -> OperatorResult[CommandResultData | JsonObject]:
        return await self._submit(
            command_name="checks record",
            title="Check recorded",
            run_id=run_id,
            operation=RecordCheckOperation(
                subject=subject,
                rule=rule,
                status=status,
                validator=validator,
                summary=summary,
                check_count=1,
                result=Content(data={"checks": [{"check": name, "status": status.value}]}),  # type: ignore[arg-type]
            ),
        )

    async def export_run_bundle(
        self,
        run_id: RunId,
        output_path: PathInput,
        /,
        *,
        profile: BundleProfile = BundleProfile.COMPLETE,
    ) -> OperatorResult[BundleExportData]:
        result = await export_bundle(
            run_id=run_id,
            output_path=output_path,
            event_store=self._dependencies.event_store,
            artifact_store=self._dependencies.artifact_store,
            profile=profile,
            runtime_version=__version__,
            exported_at=self._dependencies.clock.now(),
            required_root_mappings=self._dependencies.required_root_mappings,
            required_providers=self._dependencies.available_providers,
        )
        return OperatorResult.success(
            command="bundles export",
            title="Bundle exported",
            data=BundleExportData(
                run_id=run_id.value,
                bundle_path=str(result.bundle_path),
                profile=result.manifest.profile.value,
                completeness=result.manifest.completeness.status.value,
                commitment=result.manifest.integrity.bundle.sha256,
            ),
        )

    def verify_run_bundle(
        self, bundle_path: PathInput, /
    ) -> OperatorResult[BundleVerificationData]:
        result = verify_bundle(bundle_path)
        return OperatorResult.success(
            command="bundles verify",
            title="Bundle verified",
            data=BundleVerificationData(
                bundle_path=str(result.bundle_path),
                run_id=result.manifest.run_id.value,
                profile=result.manifest.profile.value,
                checks=tuple(item.name for item in result.checks),
            ),
        )

    def replay_run_bundle(self, bundle_path: PathInput, /) -> OperatorResult[BundleReplayData]:
        result = replay_bundle(bundle_path)
        return OperatorResult.success(
            command="bundles replay",
            title="Bundle replayed",
            data=BundleReplayData(
                bundle_path=str(result.bundle_path),
                run_id=result.manifest.run_id.value,
                event_count=len(result.events),
                status=result.views.run_status.status,
            ),
        )

    def import_run_bundle(
        self,
        bundle_path: PathInput,
        root_mappings: Mapping[str, PathInput],
        /,
    ) -> OperatorResult[BundleImportData]:
        imported = import_bundle(
            bundle_path,
            runtime_home=self._dependencies.runtime_home,
            root_mappings=root_mappings,
            imported_at=self._dependencies.clock.now(),
        )
        assessment = self._assess_imported(imported)
        return OperatorResult.success(
            command="bundles import",
            title="Bundle imported",
            data=BundleImportData(
                bundle_path=imported.bundle_path,
                run_id=imported.manifest.run_id.value,
                import_id=imported.import_id,
                resumable=assessment.resumable,
                issues=tuple(item.kind.value for item in assessment.issues),
            ),
        )

    def assess_run_bundle(
        self,
        bundle_path: PathInput,
        root_mappings: Mapping[str, PathInput],
        /,
    ) -> OperatorResult[BundleAssessmentData]:
        replay = replay_bundle(bundle_path)
        imported = ImportedBundle(
            bundle_path=str(replay.bundle_path),
            manifest=replay.manifest,
            root_mappings=tuple(
                (key, str(normalize_local_path(value).path)) for key, value in root_mappings.items()
            ),
            import_id="assessment",
            imported_at=self._dependencies.clock.now(),
        )
        assessment = self._assess_imported(imported)
        return OperatorResult.success(
            command="bundles assess",
            title="Bundle resume assessment",
            data=BundleAssessmentData(
                bundle_path=str(replay.bundle_path),
                run_id=replay.manifest.run_id.value,
                resumable=assessment.resumable,
                missing_root_mappings=assessment.missing_root_mappings,
                issues=tuple(
                    _json_object(
                        {
                            "kind": item.kind.value,
                            "severity": item.severity.value,
                            "subject": item.subject,
                            "evidence_pointer": item.evidence_pointer,
                        }
                    )
                    for item in assessment.issues
                ),
            ),
        )

    def _assess_imported(self, imported: ImportedBundle) -> ResumeAssessment:
        return assess_resume(
            imported,
            available_capabilities=self._dependencies.available_capabilities,
            available_providers=self._dependencies.available_providers,
            supported_policy_key=imported.manifest.policy.key,
            resumable_wait_kinds=(),
        )

    async def _history(
        self, run_id: RunId, command: str
    ) -> tuple[
        tuple[RuntimeEvent, ...],
        CompleteViewReplay[RunViewBundle] | OperatorResult[JsonObject],
    ]:
        event_slice = await self._dependencies.event_store.read(run_id)
        if not event_slice.events:
            return (), _not_found(
                command,
                "run_not_found",
                "Run was not found",
                {"run_id": run_id.value},
            )
        watermark = event_slice.next_position - 1
        replay = rebuild_views(event_slice.events, watermark=watermark)
        if not isinstance(replay, CompleteViewReplay):
            return (), OperatorResult.failed(
                command=command,
                code="run_history_incomplete",
                message="Run history is incomplete",
                exit_code=OperatorExitCode.INTEGRITY,
                data={"run_id": run_id.value},
            )
        return event_slice.events, replay

    async def inspect_run(self, run_id: RunId, /) -> OperatorResult[RunInspectionData | JsonObject]:
        command = "runs inspect"
        _events, replay = await self._history(run_id, command)
        if isinstance(replay, OperatorResult):
            return replay
        status = replay.views.run_status
        descriptor = status.run
        return OperatorResult.success(
            command=command,
            title="Run inspection",
            data=RunInspectionData(
                run_id=run_id.value,
                status=status.status,
                watermark=replay.watermark,
                root_id=descriptor.root_id.value if descriptor is not None else None,
                title=_optional(descriptor.creation.title) if descriptor is not None else None,
                objective=(
                    _optional(descriptor.creation.objective) if descriptor is not None else None
                ),
                pending_waits=len(status.pending_waits),
                capability_authorities=len(status.capability_authority),
                policy_authorities=len(status.policy_authority),
            ),
        )

    async def replay_run(self, run_id: RunId, /) -> OperatorResult[RunReplayData | JsonObject]:
        command = "runs replay"
        events, replay = await self._history(run_id, command)
        if isinstance(replay, OperatorResult):
            return replay
        return OperatorResult.success(
            command=command,
            title="Run replay",
            data=RunReplayData(
                run_id=run_id.value,
                event_count=len(events),
                watermark=replay.watermark,
                status=replay.views.run_status.status,
            ),
        )

    async def timeline(self, run_id: RunId, /) -> OperatorResult[RunTimelineData | JsonObject]:
        command = "runs timeline"
        _events, replay = await self._history(run_id, command)
        if isinstance(replay, OperatorResult):
            return replay
        entries = tuple(
            _json_object(
                {
                    "event_id": item.event_id.value,
                    "type": item.event_type.value,
                    "timestamp": item.timestamp.value,
                    "summary": item.summary,
                }
            )
            for item in replay.views.timeline
        )
        return OperatorResult.success(
            command=command,
            title="Run timeline",
            data=RunTimelineData(run_id=run_id.value, entries=entries),
        )

    async def waits(self, run_id: RunId, /) -> OperatorResult[RunWaitsData | JsonObject]:
        command = "waits list"
        _events, replay = await self._history(run_id, command)
        if isinstance(replay, OperatorResult):
            return replay
        waits = replay.views.waits
        return OperatorResult.success(
            command=command,
            title="Run waits",
            data=RunWaitsData(
                run_id=run_id.value,
                pending=tuple(
                    _json_object(
                        {
                            "wait_id": item.wait_id.value,
                            "kind": item.kind.value,
                            "request_event_id": item.request_event_id.value,
                            "requested_at": item.requested_at.value,
                        }
                    )
                    for item in waits.all_pending
                ),
                terminal=tuple(
                    _json_object(
                        {
                            "wait_id": item.wait_id.value,
                            "kind": item.kind.value,
                            "outcome": item.outcome,
                            "terminal_event_id": item.terminal_event_id.value,
                            "terminal_at": item.terminal_at.value,
                        }
                    )
                    for item in waits.all_terminal
                ),
            ),
        )

    async def explain_command(
        self, run_id: RunId, command_id: CommandId, /
    ) -> OperatorResult[CommandExplanationData | JsonObject]:
        command = "commands explain"
        events, replay = await self._history(run_id, command)
        if isinstance(replay, OperatorResult):
            return replay
        event = next(
            (
                item
                for item in events
                if isinstance(
                    item.payload,
                    (ModelCommandRecordedPayload, RuntimeCommandRecordedPayload),
                )
                and item.payload.command_id == command_id
            ),
            None,
        )
        if event is None:
            return _not_found(
                command,
                "command_not_found",
                "Command was not found",
                {"run_id": run_id.value, "command_id": command_id.value},
            )
        payload = event.payload
        assert isinstance(payload, (ModelCommandRecordedPayload, RuntimeCommandRecordedPayload))
        branch = payload.decision_record.branch
        reason: str | None = None
        wait_id: str | None = None
        replacement: str | None = None
        if isinstance(branch, RejectedDecisionRecord):
            reason = branch.rejection.code
        elif isinstance(branch, DeferredDecisionRecord):
            wait_id = branch.wait.wait_id.value
        elif isinstance(branch, SupersededDecisionRecord):
            replacement = branch.replacement_command_id.value
        elif not isinstance(branch, AcceptedDecisionRecord):
            raise StorageIntegrityError(code="command_decision_branch_unknown")
        types_by_id = {item.event_id: item.event_type.value for item in events}
        return OperatorResult.success(
            command=command,
            title="Command explanation",
            data=CommandExplanationData(
                run_id=run_id.value,
                command_id=command_id.value,
                origin=payload.origin_type,
                actor=_optional(payload.origin_actor),
                provider=_optional(payload.provider),
                operation=payload.operation,
                decision=branch.decision,
                reason=reason,
                trace=tuple(_trace(item) for item in branch.decision_trace),
                result_event_ids=tuple(item.value for item in branch.result_event_ids),
                result_event_types=tuple(
                    types_by_id[item] for item in branch.result_event_ids if item in types_by_id
                ),
                wait_id=wait_id,
                superseded_by_command_id=replacement,
            ),
        )

    async def action_receipt(
        self, run_id: RunId, action_id: ActionId, /
    ) -> OperatorResult[ActionReceiptData | JsonObject]:
        command = "actions receipt"
        _events, replay = await self._history(run_id, command)
        if isinstance(replay, OperatorResult):
            return replay
        receipt = replay.views.action_receipts.get(action_id)
        if receipt is None:
            return _not_found(
                command,
                "action_receipt_not_found",
                "Action receipt was not found",
                {"run_id": run_id.value, "action_id": action_id.value},
            )
        return OperatorResult.success(
            command=command,
            title="Action receipt",
            data=ActionReceiptData(status=receipt.status, receipt=_receipt(receipt)),
        )

    async def readiness(self, run_id: RunId, /) -> OperatorResult[RunReadinessData | JsonObject]:
        command = "runs readiness"
        _events, replay = await self._history(run_id, command)
        if isinstance(replay, OperatorResult):
            return replay
        status = replay.views.run_status
        readiness = status.completion_readiness
        return OperatorResult.success(
            command=command,
            title="Run completion readiness",
            data=RunReadinessData(
                run_id=run_id.value,
                status=status.status,
                ready=readiness.ready,
                requirements=_json_object(
                    {
                        "artifact_kinds": list(readiness.requirements.artifact_kinds),
                        "semantic_checks": list(readiness.requirements.semantic_checks),
                        "require_known_action_outcomes": (
                            readiness.requirements.require_known_action_outcomes
                        ),
                        "source_coverage_required": (
                            readiness.requirements.source_coverage_required
                        ),
                    }
                ),
                output_artifacts=tuple(
                    _artifact_requirement(item) for item in readiness.output_artifacts
                ),
                semantic_checks=tuple(_named_check(item) for item in readiness.semantic_checks),
                diagnostic_checks=tuple(_named_check(item) for item in readiness.diagnostic_checks),
                source_coverage=_json_object(
                    {
                        "required": readiness.source_coverage.required,
                        "satisfied": readiness.source_coverage.satisfied,
                        "evidence_check_id": (
                            readiness.source_coverage.evidence_check_id.value
                            if readiness.source_coverage.evidence_check_id is not None
                            else None
                        ),
                    }
                ),
                unresolved_unknown_outcomes=readiness.unresolved_unknown_outcomes,
                pending_waits=len(status.pending_waits),
                blockers=tuple(_blocker(item) for item in readiness.blockers),
            ),
        )

    async def checks(self, run_id: RunId, /) -> OperatorResult[RunChecksData | JsonObject]:
        command = "checks list"
        _events, replay = await self._history(run_id, command)
        if isinstance(replay, OperatorResult):
            return replay
        reports = tuple(
            _json_object(
                {
                    "check_id": item.check_id.value,
                    "event_id": item.event_id.value,
                    "timestamp": item.timestamp.value,
                    "subject": item.subject,
                    "rule": item.rule,
                    "status": item.status.value,
                    "validator": item.validator,
                    "summary": item.summary,
                    "check_count": item.check_count,
                    "message": item.message,
                    "artifact_ids": [artifact_id.value for artifact_id in item.artifact_ids],
                }
            )
            for item in replay.views.reports
        )
        return OperatorResult.success(
            command=command,
            title="Run checks",
            data=RunChecksData(run_id=run_id.value, reports=reports),
        )

    async def artifact(
        self, run_id: RunId, artifact_id: ArtifactId, /
    ) -> OperatorResult[ArtifactInspectionData | JsonObject]:
        command = "artifacts show"
        _events, replay = await self._history(run_id, command)
        if isinstance(replay, OperatorResult):
            return replay
        view: ArtifactIndexEntry | None = replay.views.artifact_index.get(artifact_id)
        stored: ArtifactEntry | None = await self._dependencies.artifact_store.get(artifact_id)
        if view is None and stored is None:
            return _not_found(
                command,
                "artifact_not_found",
                "Artifact was not found",
                {"run_id": run_id.value, "artifact_id": artifact_id.value},
            )
        return OperatorResult.success(
            command=command,
            title="Artifact inspection",
            data=ArtifactInspectionData(
                run_id=run_id.value,
                artifact_id=artifact_id.value,
                kind=view.kind if view is not None else stored.kind if stored else None,
                available=(
                    view.available
                    if view is not None
                    else stored is not None and stored.unavailable_at in (MISSING, None)
                ),
                preview=view.content_preview if view is not None else None,
                content_type=_optional(stored.content_type) if stored is not None else None,
                byte_length=_optional(stored.byte_length) if stored is not None else None,
                sha256=_optional(stored.sha256) if stored is not None else None,
                metadata=(
                    view.metadata
                    if view is not None
                    else _optional(stored.metadata)
                    if stored is not None
                    else None
                ),
            ),
        )
