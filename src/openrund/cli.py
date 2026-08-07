"""Deterministic command-line adapter over the typed operator service."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import final

from openrund.assembly import (
    LocalAssemblyConfig,
    OperatorInput,
    OperatorInputRequest,
    OperatorInputResponse,
    create_local_runtime,
)
from openrund.contracts.ids import ActionId, ArtifactId, CommandId, RunId, WaitId
from openrund.contracts.json import JsonObject, freeze_json
from openrund.contracts.portable import BundleProfile
from openrund.contracts.runs import CheckStatus
from openrund.errors import (
    BundleError,
    OpenRundError,
    StorageError,
    StorageIntegrityError,
    ValidationError,
)
from openrund.operator import (
    AnyOperatorResult,
    HelpData,
    OperatorExitCode,
    OperatorResult,
    OperatorService,
    render_operator_json,
    render_operator_text,
)
from openrund.storage import default_openrund_home


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CliProcessResult:
    result: AnyOperatorResult
    stdout: str
    stderr: str
    exit_code: int


_USAGE = (
    "Expected runs create|advance|inspect|replay|timeline|readiness; "
    "waits list|resolve|resume; commands explain; actions receipt|reconcile; "
    "checks list|record; artifacts show; bundles export|verify|replay|import|assess; "
    "or demo governed-coding [WORKSPACE]"
)


@final
@dataclass(frozen=True, slots=True)
class _ParsedCommand:
    route: str
    args: tuple[str, ...]


@final
@dataclass(frozen=True, slots=True)
class _ParsedInvocation:
    home: Path
    json_output: bool
    command: _ParsedCommand


@final
class _ConsoleOperatorInput:
    """Terminal input owned by the CLI host, outside runtime legality."""

    __slots__ = ()

    async def request(self, value: OperatorInputRequest, /) -> OperatorInputResponse:
        if not isinstance(value, OperatorInputRequest):
            raise ValidationError(code="operator_input_request_invalid")
        answer = await asyncio.to_thread(input, value.prompt)
        return OperatorInputResponse(value=answer)


def _stdio_is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _usage(message: str) -> OperatorResult[JsonObject]:
    return OperatorResult.failed(
        command="help",
        code="cli_usage",
        message=message,
        exit_code=OperatorExitCode.USAGE,
    )


def _help() -> OperatorResult[HelpData]:
    return OperatorResult.success(
        command="help",
        title="OpenRund command line",
        data=HelpData(usage=_USAGE),
    )


def _option(values: tuple[str, ...], name: str, default: str | None = None) -> str | None:
    try:
        index = values.index(name)
    except ValueError:
        return default
    if index + 1 >= len(values):
        raise ValidationError(code="cli_option_value_missing", safe_detail=name)
    return values[index + 1]


def _root_mappings(values: tuple[str, ...]) -> dict[str, str]:
    mappings: dict[str, str] = {}
    for index, value in enumerate(values):
        if value != "--map":
            continue
        if index + 1 >= len(values) or "=" not in values[index + 1]:
            raise ValidationError(code="cli_root_mapping_invalid")
        key, path = values[index + 1].split("=", 1)
        if key == "" or path == "" or key in mappings:
            raise ValidationError(code="cli_root_mapping_invalid")
        mappings[key] = path
    return mappings


def _input_json(values: tuple[str, ...]) -> JsonObject | None:
    raw = _option(values, "--input-json")
    if raw is None:
        return None
    try:
        value = freeze_json(json.loads(raw))
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError):
        raise ValidationError(code="cli_input_json_invalid") from None
    if not isinstance(value, JsonObject):
        raise ValidationError(code="cli_input_json_object_required")
    return value


def _options(
    values: tuple[str, ...],
    *,
    allowed: frozenset[str],
    repeatable: frozenset[str] = frozenset(),
) -> dict[str, tuple[str, ...]]:
    parsed: dict[str, list[str]] = {}
    index = 0
    while index < len(values):
        name = values[index]
        if name not in allowed or index + 1 >= len(values):
            raise ValidationError(code="cli_usage")
        value = values[index + 1]
        if value == "" or value.startswith("--"):
            raise ValidationError(code="cli_option_value_missing", safe_detail=name)
        existing = parsed.setdefault(name, [])
        if existing and name not in repeatable:
            raise ValidationError(code="cli_option_duplicate", safe_detail=name)
        existing.append(value)
        index += 2
    return {name: tuple(items) for name, items in parsed.items()}


def _parse_command(values: tuple[str, ...], *, allow_demo: bool) -> _ParsedCommand:
    if values in ((), ("--help",), ("help",)):
        return _ParsedCommand(route="help", args=values)
    if len(values) < 2:
        raise ValidationError(code="cli_usage")
    route = " ".join(values[:2])

    if route == "runs create" and len(values) >= 3:
        RunId(value=values[2])
        _options(values[3:], allowed=frozenset(("--title", "--objective")))
    elif route == "runs advance" and len(values) >= 4:
        RunId(value=values[2])
        if " ".join(values[3:]) == "":
            raise ValidationError(code="cli_usage")
    elif (
        route
        in {
            "runs inspect",
            "runs replay",
            "runs timeline",
            "runs readiness",
            "waits list",
            "checks list",
        }
        and len(values) == 3
    ):
        RunId(value=values[2])
    elif route == "waits resolve" and len(values) >= 4:
        RunId(value=values[2])
        WaitId(value=values[3])
        options = _options(
            values[4:],
            allowed=frozenset(("--decision", "--input-json", "--note", "--by")),
        )
        decision = options.get("--decision")
        if decision is None:
            raise ValidationError(code="cli_approval_decision_required")
        if decision[0] not in ("approved", "denied", "cancelled"):
            raise ValidationError(code="resolve_approval_decision_invalid")
        _input_json(values[4:])
    elif route == "waits resume" and len(values) == 4:
        RunId(value=values[2])
        WaitId(value=values[3])
    elif route == "commands explain" and len(values) == 4:
        RunId(value=values[2])
        CommandId(value=values[3])
    elif route == "actions receipt" and len(values) == 4:
        RunId(value=values[2])
        ActionId(value=values[3])
    elif route == "actions reconcile" and len(values) >= 4:
        RunId(value=values[2])
        ActionId(value=values[3])
        options = _options(
            values[4:],
            allowed=frozenset(("--outcome", "--evidence", "--note", "--by")),
        )
        outcome = options.get("--outcome")
        if outcome is None or "--evidence" not in options:
            raise ValidationError(code="cli_reconciliation_evidence_required")
        if outcome[0] not in ("completed", "failed", "cancelled"):
            raise ValidationError(code="reconcile_action_outcome_invalid")
    elif route == "checks record" and len(values) >= 4:
        RunId(value=values[2])
        options = _options(
            values[4:],
            allowed=frozenset(("--status", "--summary", "--subject", "--rule", "--validator")),
        )
        raw_status = options.get("--status")
        if raw_status is None or "--summary" not in options:
            raise ValidationError(code="cli_check_fields_required")
        try:
            CheckStatus(raw_status[0])
        except ValueError:
            raise ValidationError(code="cli_check_status_invalid") from None
    elif route == "artifacts show" and len(values) == 4:
        RunId(value=values[2])
        ArtifactId(value=values[3])
    elif route == "bundles export" and len(values) >= 4:
        RunId(value=values[2])
        options = _options(values[4:], allowed=frozenset(("--profile",)))
        try:
            BundleProfile(options.get("--profile", (BundleProfile.COMPLETE.value,))[0])
        except ValueError:
            raise ValidationError(code="cli_bundle_profile_invalid") from None
    elif route in {"bundles verify", "bundles replay"} and len(values) == 3:
        pass
    elif route in {"bundles import", "bundles assess"} and len(values) >= 3:
        _options(
            values[3:],
            allowed=frozenset(("--map",)),
            repeatable=frozenset(("--map",)),
        )
        _root_mappings(values[3:])
    elif route == "demo governed-coding" and allow_demo and len(values) in (2, 3):
        if len(values) == 3 and values[2].startswith("--"):
            raise ValidationError(code="cli_usage")
        return _ParsedCommand(route=route, args=values)
    else:
        raise ValidationError(code="cli_usage")
    return _ParsedCommand(route=route, args=values)


async def _execute_cli(command: _ParsedCommand, service: OperatorService) -> AnyOperatorResult:
    values = command.args
    if command.route == "help":
        return _help()
    if command.route == "runs create":
        return await service.create_run(
            RunId(value=values[2]),
            title=_option(values[3:], "--title"),
            objective=_option(values[3:], "--objective"),
        )
    if command.route == "runs advance":
        return await service.advance_run(RunId(value=values[2]), " ".join(values[3:]))
    if command.route == "runs inspect":
        return await service.inspect_run(RunId(value=values[2]))
    if command.route == "runs replay":
        return await service.replay_run(RunId(value=values[2]))
    if command.route == "runs timeline":
        return await service.timeline(RunId(value=values[2]))
    if command.route == "runs readiness":
        return await service.readiness(RunId(value=values[2]))
    if command.route == "waits list":
        return await service.waits(RunId(value=values[2]))
    if command.route == "waits resolve":
        decision = _option(values[4:], "--decision")
        if decision is None:
            raise ValidationError(code="cli_approval_decision_required")
        return await service.resolve_approval(
            RunId(value=values[2]),
            WaitId(value=values[3]),
            decision=decision,
            approved_input=_input_json(values[4:]),
            note=_option(values[4:], "--note"),
            resolved_by=_option(values[4:], "--by", "operator") or "operator",
        )
    if command.route == "waits resume":
        return await service.resume_approval(RunId(value=values[2]), WaitId(value=values[3]))
    if command.route == "commands explain":
        return await service.explain_command(RunId(value=values[2]), CommandId(value=values[3]))
    if command.route == "actions receipt":
        return await service.action_receipt(RunId(value=values[2]), ActionId(value=values[3]))
    if command.route == "actions reconcile":
        outcome = _option(values[4:], "--outcome")
        evidence = _option(values[4:], "--evidence")
        if outcome is None or evidence is None:
            raise ValidationError(code="cli_reconciliation_evidence_required")
        return await service.reconcile_action(
            RunId(value=values[2]),
            ActionId(value=values[3]),
            outcome=outcome,
            evidence=evidence,
            note=_option(values[4:], "--note"),
            reconciled_by=_option(values[4:], "--by", "operator") or "operator",
        )
    if command.route == "checks list":
        return await service.checks(RunId(value=values[2]))
    if command.route == "checks record":
        raw_status = _option(values[4:], "--status")
        summary = _option(values[4:], "--summary")
        if raw_status is None or summary is None:
            raise ValidationError(code="cli_check_fields_required")
        try:
            status = CheckStatus(raw_status)
        except ValueError:
            raise ValidationError(code="cli_check_status_invalid") from None
        return await service.record_check(
            RunId(value=values[2]),
            values[3],
            status=status,
            summary=summary,
            subject=_option(values[4:], "--subject", "run") or "run",
            rule=_option(values[4:], "--rule", "operator_check") or "operator_check",
            validator=_option(values[4:], "--validator", "operator") or "operator",
        )
    if command.route == "artifacts show":
        return await service.artifact(RunId(value=values[2]), ArtifactId(value=values[3]))
    if command.route == "bundles export":
        raw_profile = _option(values[4:], "--profile", BundleProfile.COMPLETE.value)
        assert raw_profile is not None
        try:
            profile = BundleProfile(raw_profile)
        except ValueError:
            raise ValidationError(code="cli_bundle_profile_invalid") from None
        return await service.export_run_bundle(RunId(value=values[2]), values[3], profile=profile)
    if command.route == "bundles verify":
        return service.verify_run_bundle(values[2])
    if command.route == "bundles replay":
        return service.replay_run_bundle(values[2])
    if command.route == "bundles import":
        return service.import_run_bundle(values[2], _root_mappings(values[3:]))
    if command.route == "bundles assess":
        return service.assess_run_bundle(values[2], _root_mappings(values[3:]))
    return _usage(_USAGE)


def _failure_from_exception(command: str, error: Exception) -> OperatorResult[JsonObject]:
    if isinstance(error, (ValidationError, TypeError, ValueError)):
        code = error.code if isinstance(error, OpenRundError) else "cli_input_invalid"
        return OperatorResult.failed(
            command=command,
            code=code,
            message="Command input is invalid",
            exit_code=OperatorExitCode.USAGE,
        )
    if isinstance(error, (StorageIntegrityError, BundleError)):
        return OperatorResult.failed(
            command=command,
            code=error.code,
            message="Stored evidence failed integrity validation",
            exit_code=OperatorExitCode.INTEGRITY,
        )
    if isinstance(error, StorageError):
        return OperatorResult.failed(
            command=command,
            code=error.code,
            message="Required local custody is unavailable",
            exit_code=OperatorExitCode.UNAVAILABLE,
        )
    code = error.code if isinstance(error, OpenRundError) else "internal_error"
    return OperatorResult.failed(
        command=command,
        code=code,
        message="OpenRund could not complete the command",
        exit_code=OperatorExitCode.INTERNAL,
    )


async def execute_cli(args: tuple[str, ...], service: OperatorService, /) -> AnyOperatorResult:
    if not isinstance(service, OperatorService):
        raise TypeError("cli_operator_service_invalid")
    try:
        return await _execute_cli(_parse_command(tuple(args), allow_demo=False), service)
    except Exception as error:
        return _failure_from_exception(" ".join(args[:2]) or "help", error)


async def run_cli(
    args: tuple[str, ...],
    service: OperatorService,
    /,
    *,
    json_output: bool = False,
) -> CliProcessResult:
    result = await execute_cli(args, service)
    rendered = render_operator_json(result) if json_output else render_operator_text(result)
    return CliProcessResult(
        result=result,
        stdout=rendered if result.ok else "",
        stderr="" if result.ok else rendered,
        exit_code=int(result.exit_code),
    )


def _parse_invocation(args: tuple[str, ...]) -> _ParsedInvocation:
    values = tuple(args)
    json_output = False
    home: Path | None = None
    index = 0
    while index < len(values):
        value = values[index]
        if value == "--json":
            if json_output:
                raise ValidationError(code="cli_option_duplicate", safe_detail=value)
            json_output = True
            index += 1
            continue
        if value == "--home":
            if index + 1 >= len(values):
                raise ValidationError(code="cli_home_value_missing")
            if home is not None:
                raise ValidationError(code="cli_option_duplicate", safe_detail=value)
            if values[index + 1] == "" or values[index + 1].startswith("--"):
                raise ValidationError(code="cli_home_value_missing")
            home = Path(values[index + 1])
            index += 2
            continue
        break
    command = _parse_command(values[index:], allow_demo=True)
    return _ParsedInvocation(
        home=home or default_openrund_home(),
        json_output=json_output,
        command=command,
    )


async def run_cli_process(
    args: tuple[str, ...],
    *,
    operator_input: OperatorInput | None = None,
) -> CliProcessResult:
    json_output = False
    result: AnyOperatorResult
    try:
        invocation = _parse_invocation(args)
        json_output = invocation.json_output
    except Exception as error:
        result = _failure_from_exception("help", error)
        rendered = render_operator_text(result)
        return CliProcessResult(
            result=result,
            stdout="",
            stderr=rendered,
            exit_code=int(result.exit_code),
        )
    if invocation.command.route == "help":
        result = _help()
        rendered = (
            render_operator_json(result) if invocation.json_output else render_operator_text(result)
        )
        return CliProcessResult(result=result, stdout=rendered, stderr="", exit_code=0)
    if invocation.command.route == "demo governed-coding":
        from openrund.demo import run_governed_coding_demo

        try:
            workspace_input = operator_input
            if workspace_input is None and not json_output and _stdio_is_interactive():
                workspace_input = _ConsoleOperatorInput()
            command_args = invocation.command.args
            result = await run_governed_coding_demo(
                runtime_home=invocation.home,
                workspace=command_args[2] if len(command_args) == 3 else None,
                operator_input=workspace_input,
            )
        except Exception as error:
            result = _failure_from_exception("demo governed-coding", error)
        rendered = render_operator_json(result) if json_output else render_operator_text(result)
        return CliProcessResult(
            result=result,
            stdout=rendered if result.ok else "",
            stderr="" if result.ok else rendered,
            exit_code=int(result.exit_code),
        )
    runtime = create_local_runtime(LocalAssemblyConfig(runtime_home=invocation.home))
    async with runtime:
        result = await _execute_cli(invocation.command, runtime.operator)
        rendered = (
            render_operator_json(result) if invocation.json_output else render_operator_text(result)
        )
        return CliProcessResult(
            result=result,
            stdout=rendered if result.ok else "",
            stderr="" if result.ok else rendered,
            exit_code=int(result.exit_code),
        )
