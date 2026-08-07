"""Durable ModelCall lifecycle and inert proposal submission loop."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Self, final

from openrund.contracts.commands import (
    AcceptedCommandDecision,
    CancelModelCallOperation,
    Command,
    CommandOrigin,
    CommandResult,
    CompleteModelCallOperation,
    FailModelCallOperation,
    ModelCallFailureClassification,
    StartModelCallOperation,
)
from openrund.contracts.content import Content
from openrund.contracts.ids import CommandId, ModelCallId, RunId
from openrund.contracts.json import MISSING, JsonObject, MissingType, freeze_json
from openrund.engine import RuntimeEngine, submit_model_proposal
from openrund.errors import (
    ProviderProtocolError,
    ProviderResponseError,
    ProviderTransportError,
    ValidationError,
)
from openrund.ports.providers import ModelProposal, ModelProvider, ModelRequest
from openrund.ports.runtime import Clock, IdFactory

type _LifecycleOperation = (
    StartModelCallOperation
    | CompleteModelCallOperation
    | FailModelCallOperation
    | CancelModelCallOperation
)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ModelCallStepResult:
    model_call_id: ModelCallId
    status: Literal["proposed", "failed"]
    start_result: CommandResult
    terminal_result: CommandResult
    proposal_result: CommandResult | None = None
    failure_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.model_call_id, ModelCallId):
            raise ValidationError(code="run_loop_result_model_call_invalid")
        if self.status == "proposed":
            if self.proposal_result is None or self.failure_code is not None:
                raise ValidationError(code="run_loop_result_branch_invalid")
        elif self.status == "failed":
            if self.proposal_result is not None or not isinstance(self.failure_code, str):
                raise ValidationError(code="run_loop_result_branch_invalid")
        else:
            raise ValidationError(code="run_loop_result_status_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DurableRunLoopDependencies:
    engine: RuntimeEngine
    provider: ModelProvider
    clock: Clock
    model_call_ids: IdFactory[ModelCallId]
    command_ids: IdFactory[CommandId]
    own_provider: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.engine, RuntimeEngine):
            raise ValidationError(code="run_loop_engine_invalid")
        if not callable(getattr(self.provider, "propose", None)):
            raise ValidationError(code="run_loop_provider_invalid")
        if not callable(getattr(self.clock, "now", None)):
            raise ValidationError(code="run_loop_clock_invalid")
        for name in ("model_call_ids", "command_ids"):
            if not callable(getattr(getattr(self, name), "new_id", None)):
                raise ValidationError(code=f"run_loop_{name}_invalid")
        if not isinstance(self.own_provider, bool):
            raise ValidationError(code="run_loop_provider_ownership_invalid")


def _operation_kind(proposal: ModelProposal) -> str:
    kind = proposal.operation.kind
    return kind.value if isinstance(kind, StrEnum) else kind


def _accepted(result: CommandResult, code: str) -> CommandResult:
    if not isinstance(result.decision, AcceptedCommandDecision):
        raise ProviderProtocolError(code=code)
    return result


@final
class DurableRunLoop:
    """One resource-bounded async coordinator for durable provider attempts."""

    __slots__ = ("_active", "_closed", "_dependencies")

    def __init__(self, dependencies: DurableRunLoopDependencies) -> None:
        if not isinstance(dependencies, DurableRunLoopDependencies):
            raise ValidationError(code="run_loop_dependencies_invalid")
        self._dependencies = dependencies
        self._active: set[asyncio.Task[ModelCallStepResult]] = set()
        self._closed = False

    async def __aenter__(self) -> Self:
        if self._closed:
            raise ProviderTransportError(code="run_loop_closed")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        active = tuple(self._active)
        for task in active:
            task.cancel()
        if active:
            await asyncio.gather(*active, return_exceptions=True)
        self._active.clear()
        if self._dependencies.own_provider:
            close = getattr(self._dependencies.provider, "aclose", None)
            if callable(close):
                await close()

    def _command(
        self,
        run_id: RunId,
        operation: _LifecycleOperation,
        *,
        model_call_id: ModelCallId,
        stage: str,
    ) -> Command:
        return Command(
            command_id=self._dependencies.command_ids.new_id(),
            run_id=run_id,
            origin=CommandOrigin.SYSTEM,
            operation=operation,
            model_call_id=model_call_id,
            idempotency_key=f"model-call:{model_call_id.value}:{stage}",
            created_at=self._dependencies.clock.now(),
        )

    async def _submit_terminal(
        self,
        run_id: RunId,
        model_call_id: ModelCallId,
        operation: CompleteModelCallOperation | FailModelCallOperation | CancelModelCallOperation,
        stage: str,
        *,
        propagate_cancel: bool = True,
    ) -> CommandResult:
        task = asyncio.create_task(
            self._dependencies.engine.submit(
                self._command(
                    run_id,
                    operation,
                    model_call_id=model_call_id,
                    stage=stage,
                )
            )
        )
        cancelled = False
        try:
            result = await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
            result = await task
        accepted = _accepted(result, f"model_call_{stage}_rejected")
        if cancelled and propagate_cancel:
            raise asyncio.CancelledError
        return accepted

    async def _record_failure(
        self,
        run_id: RunId,
        model_call_id: ModelCallId,
        *,
        start_result: CommandResult,
        classification: ModelCallFailureClassification,
        retryable: bool,
        code: str,
    ) -> ModelCallStepResult:
        terminal = await self._submit_terminal(
            run_id,
            model_call_id,
            FailModelCallOperation(
                model_call_id=model_call_id,
                message={
                    ModelCallFailureClassification.PROVIDER: "Provider request failed",
                    ModelCallFailureClassification.TRANSPORT: "Provider transport failed",
                    ModelCallFailureClassification.PARSE: "Provider response could not be parsed",
                }[classification],
                classification=classification,
                retryable=retryable,
            ),
            "failed",
        )
        return ModelCallStepResult(
            model_call_id=model_call_id,
            status="failed",
            start_result=start_result,
            terminal_result=terminal,
            failure_code=code,
        )

    async def step(
        self,
        run_id: RunId,
        context: Content,
        *,
        remaining_requests: int,
        metadata: JsonObject | MissingType | None = MISSING,
    ) -> ModelCallStepResult:
        if self._closed:
            raise ProviderTransportError(code="run_loop_closed")
        if not isinstance(run_id, RunId):
            raise ValidationError(code="run_loop_run_id_invalid")
        if not isinstance(context, Content):
            raise ValidationError(code="run_loop_context_invalid")
        task = asyncio.create_task(
            self._step(
                run_id,
                context,
                remaining_requests=remaining_requests,
                metadata=metadata,
            )
        )
        self._active.add(task)
        try:
            return await task
        finally:
            self._active.discard(task)

    async def _step(
        self,
        run_id: RunId,
        context: Content,
        *,
        remaining_requests: int,
        metadata: JsonObject | MissingType | None,
    ) -> ModelCallStepResult:
        model_call_id = self._dependencies.model_call_ids.new_id()
        start_task = asyncio.create_task(
            self._dependencies.engine.submit(
                self._command(
                    run_id,
                    StartModelCallOperation(model_call_id=model_call_id),
                    model_call_id=model_call_id,
                    stage="started",
                )
            )
        )
        cancelled_during_start = False
        try:
            start = await asyncio.shield(start_task)
        except asyncio.CancelledError:
            cancelled_during_start = True
            start = await start_task
        start_result = _accepted(start, "model_call_start_rejected")
        if cancelled_during_start:
            await self._submit_terminal(
                run_id,
                model_call_id,
                CancelModelCallOperation(
                    model_call_id=model_call_id,
                    reason="provider call cancelled",
                ),
                "cancelled",
                propagate_cancel=False,
            )
            raise asyncio.CancelledError
        request = ModelRequest(
            model_call_id=model_call_id,
            run_id=run_id,
            context=context,
            remaining_requests=remaining_requests,
            metadata=metadata,
        )
        try:
            proposal = await self._dependencies.provider.propose(request)
        except asyncio.CancelledError:
            await self._submit_terminal(
                run_id,
                model_call_id,
                CancelModelCallOperation(
                    model_call_id=model_call_id,
                    reason="provider call cancelled",
                ),
                "cancelled",
                propagate_cancel=False,
            )
            raise
        except ProviderResponseError as error:
            return await self._record_failure(
                run_id,
                model_call_id,
                start_result=start_result,
                classification=ModelCallFailureClassification.PROVIDER,
                retryable=error.retryable,
                code=error.code,
            )
        except ProviderTransportError as error:
            return await self._record_failure(
                run_id,
                model_call_id,
                start_result=start_result,
                classification=ModelCallFailureClassification.TRANSPORT,
                retryable=True,
                code=error.code,
            )
        except (ProviderProtocolError, ValidationError) as error:
            return await self._record_failure(
                run_id,
                model_call_id,
                start_result=start_result,
                classification=ModelCallFailureClassification.PARSE,
                retryable=False,
                code=error.code,
            )
        except Exception:
            return await self._record_failure(
                run_id,
                model_call_id,
                start_result=start_result,
                classification=ModelCallFailureClassification.PROVIDER,
                retryable=False,
                code="provider_unexpected_failure",
            )
        if not isinstance(proposal, ModelProposal) or proposal.model_call_id != model_call_id:
            return await self._record_failure(
                run_id,
                model_call_id,
                start_result=start_result,
                classification=ModelCallFailureClassification.PARSE,
                retryable=False,
                code="provider_model_call_mismatch",
            )
        kind = _operation_kind(proposal)
        terminal_metadata = freeze_json({"provider": proposal.provider, "operationKind": kind})
        assert isinstance(terminal_metadata, JsonObject)
        terminal = await self._submit_terminal(
            run_id,
            model_call_id,
            CompleteModelCallOperation(
                model_call_id=model_call_id,
                outcome=kind,
                metadata=terminal_metadata,
            ),
            "completed",
        )
        proposal_task = asyncio.create_task(
            submit_model_proposal(
                self._dependencies.engine,
                run_id,
                self._dependencies.command_ids.new_id(),
                proposal,
                idempotency_key=f"model-call:{model_call_id.value}:proposal",
                created_at=self._dependencies.clock.now(),
            )
        )
        try:
            proposal_result = await asyncio.shield(proposal_task)
        except asyncio.CancelledError:
            await proposal_task
            raise
        return ModelCallStepResult(
            model_call_id=model_call_id,
            status="proposed",
            start_result=start_result,
            terminal_result=terminal,
            proposal_result=proposal_result,
        )
