from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import pytest

from openrund.assembly import LocalAssemblyConfig, create_local_runtime
from openrund.cli import execute_cli, run_cli, run_cli_process
from openrund.contracts.ids import RunId
from openrund.operator import (
    BundleAssessmentData,
    BundleImportData,
    BundleReplayData,
    BundleVerificationData,
    CommandResultData,
    DemoResultData,
    OperatorExitCode,
)


def test_help_is_successful_and_never_opens_runtime_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "must-not-exist"

    def forbidden_runtime(_config: LocalAssemblyConfig) -> None:
        raise AssertionError("help opened runtime custody")

    monkeypatch.setattr("openrund.cli.create_local_runtime", forbidden_runtime)
    completed = asyncio.run(run_cli_process(("--home", str(home), "--help")))

    assert completed.exit_code == OperatorExitCode.OK
    assert completed.stderr == ""
    assert "OpenRund command line" in completed.stdout
    assert "demo governed-coding" in completed.stdout
    assert not home.exists()


@pytest.mark.parametrize(
    "command",
    (
        ("unknown", "command"),
        ("runs", "inspect"),
        ("runs", "inspect", "run_bad", "extra"),
        ("runs", "create", "run_bad", "--title"),
        ("runs", "create", "run_bad", "--title", "one", "--title", "two"),
        ("waits", "resolve", "run_bad", "wait_bad", "--decision", "maybe"),
        ("checks", "record", "run_bad", "check", "--status", "unknown", "--summary", "x"),
        ("demo", "governed-coding", "workspace", "extra"),
    ),
)
def test_invalid_commands_are_fully_parsed_before_runtime_custody(
    command: tuple[str, ...], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "must-not-exist"

    def forbidden_runtime(_config: LocalAssemblyConfig) -> None:
        raise AssertionError("invalid command opened runtime custody")

    monkeypatch.setattr("openrund.cli.create_local_runtime", forbidden_runtime)
    completed = asyncio.run(run_cli_process(("--home", str(home), *command)))

    assert completed.exit_code == OperatorExitCode.USAGE
    assert completed.stdout == ""
    assert "OpenRund command failed" in completed.stderr
    assert not home.exists()


def test_duplicate_global_options_are_rejected_before_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    def forbidden_runtime(_config: LocalAssemblyConfig) -> None:
        raise AssertionError("invalid globals opened runtime custody")

    monkeypatch.setattr("openrund.cli.create_local_runtime", forbidden_runtime)
    completed = asyncio.run(
        run_cli_process(("--home", str(first), "--home", str(second), "runs", "inspect", "run_bad"))
    )

    assert completed.exit_code == OperatorExitCode.USAGE
    assert not first.exists() and not second.exists()


def test_interactive_demo_proposes_default_and_accepts_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if shutil.which("git") is None:
        pytest.skip("git is required for the governed coding demonstration")
    home = tmp_path / "runtime"
    selected = tmp_path / "operator-workspace"
    prompts: list[str] = []

    def answer(prompt: str) -> str:
        prompts.append(prompt)
        return str(selected)

    monkeypatch.setattr("openrund.cli._stdio_is_interactive", lambda: True)
    monkeypatch.setattr("builtins.input", answer)
    completed = asyncio.run(run_cli_process(("--home", str(home), "demo", "governed-coding")))

    assert completed.exit_code == 0
    assert isinstance(completed.result.data, DemoResultData)
    assert completed.result.data.workspace_root == str(selected)
    assert completed.result.data.workspace_selected_by == "operator"
    assert selected.joinpath("report.md").is_file()
    assert len(prompts) == 1
    assert "Workspace root for run work products" in prompts[0]
    assert "Workspace root [Enter for default]" in prompts[0]


def test_engine_backed_run_control_check_and_legality_exit(tmp_path: Path) -> None:
    runtime = create_local_runtime(LocalAssemblyConfig(runtime_home=tmp_path / "runtime"))

    async def scenario() -> None:
        created = await execute_cli(
            (
                "runs",
                "create",
                "run_cli",
                "--title",
                "CLI run",
                "--objective",
                "Prove authority routing",
            ),
            runtime.operator,
        )
        advanced = await execute_cli(
            ("runs", "advance", "run_cli", "operator message"), runtime.operator
        )
        checked = await execute_cli(
            (
                "checks",
                "record",
                "run_cli",
                "unit_tests",
                "--status",
                "passed",
                "--summary",
                "All tests passed",
            ),
            runtime.operator,
        )
        illegal_approval = await execute_cli(
            ("waits", "resolve", "run_cli", "wait_missing", "--decision", "approved"),
            runtime.operator,
        )
        reconciliation = await execute_cli(
            (
                "actions",
                "reconcile",
                "run_cli",
                "action_missing",
                "--outcome",
                "completed",
                "--evidence",
                "operator inspected the effect",
            ),
            runtime.operator,
        )
        history = await runtime.event_store.read(RunId(value="run_cli"))
        await runtime.aclose()

        assert created.ok and advanced.ok and checked.ok
        assert isinstance(created.data, CommandResultData)
        assert isinstance(advanced.data, CommandResultData)
        assert isinstance(checked.data, CommandResultData)
        assert created.data.decision == "accepted"
        assert advanced.data.decision == "accepted"
        assert checked.data.decision == "accepted"
        assert illegal_approval.exit_code is OperatorExitCode.REJECTED
        assert illegal_approval.failure is not None
        assert illegal_approval.failure.code == "wait_not_found"
        assert reconciliation.exit_code is OperatorExitCode.NOT_FOUND
        assert len(history.events) == 8

    asyncio.run(scenario())


def test_every_bundle_command_uses_verified_portable_lifecycle(tmp_path: Path) -> None:
    runtime = create_local_runtime(LocalAssemblyConfig(runtime_home=tmp_path / "runtime"))
    bundle = tmp_path / "run.orun"

    async def scenario() -> None:
        await execute_cli(("runs", "create", "run_bundle_cli"), runtime.operator)
        exported = await execute_cli(
            ("bundles", "export", "run_bundle_cli", str(bundle)), runtime.operator
        )
        verified = await execute_cli(("bundles", "verify", str(bundle)), runtime.operator)
        replayed = await execute_cli(("bundles", "replay", str(bundle)), runtime.operator)
        assessed = await execute_cli(("bundles", "assess", str(bundle)), runtime.operator)
        imported = await execute_cli(("bundles", "import", str(bundle)), runtime.operator)
        await runtime.aclose()

        assert exported.ok and bundle.is_dir()
        assert isinstance(verified.data, BundleVerificationData)
        assert isinstance(replayed.data, BundleReplayData)
        assert isinstance(assessed.data, BundleAssessmentData)
        assert isinstance(imported.data, BundleImportData)
        assert verified.ok and len(verified.data.checks) > 0
        assert replayed.data.event_count == 3
        assert assessed.data.resumable is True
        assert imported.ok and isinstance(imported.data.import_id, str)

    asyncio.run(scenario())


def test_process_runner_persists_between_invocations_and_emits_json(tmp_path: Path) -> None:
    home = tmp_path / "runtime"

    async def scenario() -> None:
        created = await run_cli_process(("--home", str(home), "runs", "create", "run_process"))
        inspected = await run_cli_process(
            ("--home", str(home), "--json", "runs", "inspect", "run_process")
        )
        invalid = await run_cli_process(("--home", str(home), "checks", "record"))

        assert created.exit_code == 0
        assert json.loads(inspected.stdout)["data"]["status"] == "running"
        assert inspected.stderr == ""
        assert invalid.exit_code == OperatorExitCode.USAGE
        assert invalid.stdout == "" and "cli_usage" in invalid.stderr

    asyncio.run(scenario())


def test_tampered_bundle_maps_to_integrity_exit_without_raw_detail(tmp_path: Path) -> None:
    runtime = create_local_runtime(LocalAssemblyConfig(runtime_home=tmp_path / "runtime"))
    bundle = tmp_path / "tampered.orun"

    async def scenario() -> None:
        await execute_cli(("runs", "create", "run_tamper"), runtime.operator)
        await execute_cli(("bundles", "export", "run_tamper", str(bundle)), runtime.operator)
        (bundle / "events.jsonl").write_bytes(b"{}\n")
        result = await execute_cli(("bundles", "verify", str(bundle)), runtime.operator)
        await runtime.aclose()

        assert result.exit_code is OperatorExitCode.INTEGRITY
        assert result.failure is not None
        assert result.failure.code.startswith("bundle_")
        assert str(bundle) not in result.failure.message

    asyncio.run(scenario())


def test_cli_and_library_share_one_typed_result_and_deterministic_rendering(
    tmp_path: Path,
) -> None:
    runtime = create_local_runtime(LocalAssemblyConfig(runtime_home=tmp_path / "runtime"))

    async def scenario() -> None:
        run_id = RunId(value="run_parity")
        await runtime.operator.create_run(run_id)
        direct = await runtime.operator.inspect_run(run_id)
        cli = await execute_cli(("runs", "inspect", run_id.value), runtime.operator)
        first = await run_cli(("runs", "inspect", run_id.value), runtime.operator)
        second = await run_cli(("runs", "inspect", run_id.value), runtime.operator)
        await runtime.aclose()

        assert cli == direct
        assert first.result == direct
        assert first.stdout == second.stdout
        assert first.stderr == second.stderr == ""
        assert first.exit_code == second.exit_code == 0

    asyncio.run(scenario())
