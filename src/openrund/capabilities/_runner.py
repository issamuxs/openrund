"""Durable Action start, Capability dispatch, Artifact custody, and terminal recording."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import final

from openrund.capabilities._registry import CapabilityRegistry
from openrund.codec import canonical_content_hash
from openrund.contracts.capabilities import (
    ActionFailure,
    ActionReliability,
    CapabilityInlineArtifact,
    CapabilityReliability,
    CapabilityResult,
)
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    CancelActionOperation,
    Command,
    CommandOrigin,
    CommandResult,
    CompleteActionOperation,
    FailActionOperation,
    MarkActionUnknownOperation,
    ProducedArtifact,
    StartActionOperation,
)
from openrund.contracts.content import ArtifactReference, Content, EvidenceEntry
from openrund.contracts.ids import ArtifactId, CommandId, RunId
from openrund.contracts.json import MISSING, JsonObject, MissingType, freeze_json
from openrund.engine import RuntimeEngine
from openrund.errors import (
    CapabilityExecutionError,
    CapabilityProtocolError,
    CapabilityTransportError,
    OpenRundError,
    ValidationError,
)
from openrund.ports.artifacts import ArtifactBlob, ArtifactEntry, ArtifactStore
from openrund.ports.capabilities import CapabilityInvocation
from openrund.ports.runtime import Clock, IdFactory

type ActionLifecycleOperation = (
    StartActionOperation
    | CompleteActionOperation
    | FailActionOperation
    | CancelActionOperation
    | MarkActionUnknownOperation
)


def _accepted(result: CommandResult, code: str) -> CommandResult:
    if not isinstance(result.decision, AcceptedCommandDecision):
        raise CapabilityProtocolError(code=code)
    return result


def _evidence_wire(evidence: tuple[EvidenceEntry, ...]) -> list[dict[str, object]]:
    return [
        {
            **(
                {"artifactId": item.artifact_id.value}
                if isinstance(item.artifact_id, ArtifactId)
                else {}
            ),
            **({"description": item.description} if isinstance(item.description, str) else {}),
            **({"metadata": item.metadata} if isinstance(item.metadata, JsonObject) else {}),
        }
        for item in evidence
    ]


def _result_content(
    result: CapabilityResult,
    produced: tuple[tuple[ArtifactId, CapabilityInlineArtifact], ...],
) -> Content:
    metadata: dict[str, object] = {}
    data = result.output if isinstance(result.output, JsonObject) else MISSING
    if result.output is not MISSING and not isinstance(result.output, JsonObject):
        metadata["output"] = result.output
    if result.evidence:
        metadata["evidence"] = _evidence_wire(result.evidence)
    if isinstance(result.metadata, JsonObject):
        metadata["worker"] = result.metadata
    frozen_metadata: JsonObject | MissingType
    if metadata:
        candidate = freeze_json(metadata)
        assert isinstance(candidate, JsonObject)
        frozen_metadata = candidate
    else:
        frozen_metadata = MISSING
    artifact_ids = (*result.artifact_ids, *(item[0] for item in produced))
    return Content(
        preview=result.preview,
        data=data,
        artifact_refs=tuple(
            ArtifactReference(
                artifact_id=artifact_id,
                kind=artifact.kind,
                preview=artifact.preview,
                metadata=artifact.metadata,
            )
            for artifact_id, artifact in produced
        ),
        artifact_ids=artifact_ids,
        metadata=frozen_metadata,
    )


def _unknown_reliability(error: OpenRundError) -> ActionReliability:
    if error.code == "capability_worker_timeout":
        return ActionReliability.TIMEOUT_AFTER_DISPATCH
    if isinstance(error, CapabilityTransportError):
        if error.code == "capability_worker_failed":
            return ActionReliability.WORKER_CRASH
        return ActionReliability.TRANSPORT_LOST
    return ActionReliability.PARTIAL_EVIDENCE


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionRunnerDependencies:
    engine: RuntimeEngine
    registry: CapabilityRegistry
    artifact_store: ArtifactStore
    clock: Clock
    command_ids: IdFactory[CommandId]
    artifact_ids: IdFactory[ArtifactId]

    def __post_init__(self) -> None:
        if not isinstance(self.engine, RuntimeEngine):
            raise ValidationError(code="action_runner_engine_invalid")
        if not isinstance(self.registry, CapabilityRegistry):
            raise ValidationError(code="action_runner_registry_invalid")
        for name in ("artifact_store", "clock", "command_ids", "artifact_ids"):
            if getattr(self, name) is None:
                raise ValidationError(code=f"action_runner_{name}_invalid")


@final
class ActionRunner:
    __slots__ = ("_dependencies",)

    def __init__(self, dependencies: ActionRunnerDependencies) -> None:
        if not isinstance(dependencies, ActionRunnerDependencies):
            raise ValidationError(code="action_runner_dependencies_invalid")
        self._dependencies = dependencies

    def _command(self, run_id: RunId, operation: ActionLifecycleOperation, suffix: str) -> Command:
        if not isinstance(run_id, RunId):
            raise ValidationError(code="action_runner_run_id_invalid")
        return Command(
            command_id=self._dependencies.command_ids.new_id(),
            run_id=run_id,
            origin=CommandOrigin.CAPABILITY,
            operation=operation,
            idempotency_key=f"action:{operation.action_id.value}:{suffix}",
            created_at=self._dependencies.clock.now(),
        )

    async def _unknown(
        self,
        run_id: RunId,
        invocation: CapabilityInvocation,
        error: OpenRundError,
    ) -> CommandResult:
        operation = MarkActionUnknownOperation(
            action_id=invocation.action_id,
            reliability=_unknown_reliability(error),
            reason=error.code,
            message="Capability outcome could not be confirmed",
        )
        return _accepted(
            await self._dependencies.engine.submit(self._command(run_id, operation, "unknown")),
            "action_unknown_rejected",
        )

    async def _store_artifacts(
        self, result: CapabilityResult
    ) -> tuple[
        tuple[tuple[ArtifactId, CapabilityInlineArtifact], ...],
        tuple[ProducedArtifact, ...],
    ]:
        stored: list[tuple[ArtifactId, CapabilityInlineArtifact]] = []
        produced: list[ProducedArtifact] = []
        for artifact in result.inline_artifacts:
            artifact_id = self._dependencies.artifact_ids.new_id()
            digest = hashlib.sha256(artifact.content).hexdigest()
            entry = ArtifactEntry(
                artifact_id=artifact_id,
                kind=artifact.kind,
                created_at=self._dependencies.clock.now(),
                content_type=artifact.content_type,
                byte_length=len(artifact.content),
                sha256=digest,
                metadata=artifact.metadata,
            )
            await self._dependencies.artifact_store.put(
                entry,
                blob=ArtifactBlob(
                    content=artifact.content,
                    content_type=artifact.content_type,
                ),
            )
            stored.append((artifact_id, artifact))
            produced.append(
                ProducedArtifact(
                    artifact_id=artifact_id,
                    kind=artifact.kind,
                    content_type=artifact.content_type,
                    byte_length=len(artifact.content),
                    sha256=digest,
                    preview=artifact.preview,
                    metadata=artifact.metadata,
                )
            )
        return tuple(stored), tuple(produced)

    async def execute(self, run_id: RunId, invocation: CapabilityInvocation, /) -> CommandResult:
        if not isinstance(run_id, RunId) or not isinstance(invocation, CapabilityInvocation):
            raise ValidationError(code="action_runner_invocation_invalid")
        registry = self._dependencies.registry
        route = registry.resolve(invocation.capability_id, invocation.action_name)
        route.validate_input(
            invocation.input.data if isinstance(invocation.input.data, JsonObject) else None
        )
        start = StartActionOperation(
            action_id=invocation.action_id,
            capability_id=invocation.capability_id,
            action_name=invocation.action_name,
            input_hash=canonical_content_hash(invocation.input),
        )
        _accepted(
            await self._dependencies.engine.submit(self._command(run_id, start, "start")),
            "action_start_rejected",
        )
        try:
            result = route.validate_result(await route.transport.invoke(invocation))
            stored, produced = await self._store_artifacts(result)
        except asyncio.CancelledError:
            if (
                route.action.reliability is CapabilityReliability.INTERRUPTIBLE
                and route.action.cancellation.supported
            ):
                cancellation = CancelActionOperation(
                    action_id=invocation.action_id,
                    reason="executor cancelled after worker cancellation",
                )
                _accepted(
                    await self._dependencies.engine.submit(
                        self._command(run_id, cancellation, "cancelled")
                    ),
                    "action_cancellation_rejected",
                )
            else:
                error = CapabilityTransportError(code="capability_cancel_outcome_unknown")
                await self._unknown(run_id, invocation, error)
            raise
        except CapabilityExecutionError as error:
            failure = FailActionOperation(
                action_id=invocation.action_id,
                error=ActionFailure(
                    message="Capability execution was rejected",
                    code=error.code,
                    retryable=False,
                ),
            )
            return _accepted(
                await self._dependencies.engine.submit(self._command(run_id, failure, "failed")),
                "action_failure_rejected",
            )
        except (CapabilityProtocolError, CapabilityTransportError) as error:
            return await self._unknown(run_id, invocation, error)
        except OpenRundError as error:
            return await self._unknown(run_id, invocation, error)

        content = _result_content(result, stored)
        complete = CompleteActionOperation(
            action_id=invocation.action_id,
            result=content,
            effects=result.effects,
            artifact_ids=content.artifact_ids,
            produced_artifacts=produced,
        )
        return _accepted(
            await self._dependencies.engine.submit(self._command(run_id, complete, "complete")),
            "action_completion_rejected",
        )
