from __future__ import annotations

import asyncio
import json
from pathlib import Path

from openrund.assembly import LocalAssemblyConfig, create_local_runtime
from openrund.cli import execute_cli, run_cli
from openrund.contracts.commands import BootstrapRunOperation, Command, CommandOrigin
from openrund.contracts.ids import CommandId, RunId
from openrund.operator import (
    CommandExplanationData,
    OperatorExitCode,
    RunChecksData,
    RunInspectionData,
    RunReadinessData,
    RunReplayData,
    RunTimelineData,
    RunWaitsData,
)

RUN_ID = RunId(value="run_operator")
COMMAND_ID = CommandId(value="cmd_operator_bootstrap")


def _bootstrap() -> Command:
    return Command(
        command_id=COMMAND_ID,
        run_id=RUN_ID,
        origin=CommandOrigin.SYSTEM,
        operation=BootstrapRunOperation(
            root_id=RUN_ID,
            title="Operator test",
            objective="Inspect without mutation",
        ),
    )


def test_read_only_operator_matrix_preserves_history(tmp_path: Path) -> None:
    runtime = create_local_runtime(LocalAssemblyConfig(runtime_home=tmp_path / "runtime"))

    async def scenario() -> None:
        await runtime.engine.submit(_bootstrap())
        before = await runtime.event_store.read(RUN_ID)
        results = (
            await runtime.operator.inspect_run(RUN_ID),
            await runtime.operator.replay_run(RUN_ID),
            await runtime.operator.timeline(RUN_ID),
            await runtime.operator.waits(RUN_ID),
            await runtime.operator.explain_command(RUN_ID, COMMAND_ID),
            await runtime.operator.readiness(RUN_ID),
            await runtime.operator.checks(RUN_ID),
        )
        after = await runtime.event_store.read(RUN_ID)
        await runtime.aclose()

        assert all(result.ok for result in results)
        assert before.events == after.events
        assert isinstance(results[0].data, RunInspectionData)
        assert isinstance(results[1].data, RunReplayData)
        assert isinstance(results[2].data, RunTimelineData)
        assert isinstance(results[3].data, RunWaitsData)
        assert isinstance(results[4].data, CommandExplanationData)
        assert isinstance(results[5].data, RunReadinessData)
        assert isinstance(results[6].data, RunChecksData)
        assert results[0].data.status == "running"
        assert results[1].data.event_count == 3
        assert len(results[2].data.entries) == 3
        assert len(results[3].data.pending) == 0
        assert results[4].data.decision == "accepted"
        assert results[5].data.ready is True
        assert len(results[6].data.reports) == 0

    asyncio.run(scenario())


def test_cli_library_text_json_and_not_found_paths_share_results(tmp_path: Path) -> None:
    runtime = create_local_runtime(LocalAssemblyConfig(runtime_home=tmp_path / "runtime"))

    async def scenario() -> None:
        await runtime.engine.submit(_bootstrap())
        direct = await execute_cli(("runs", "inspect", RUN_ID.value), runtime.operator)
        text = await run_cli(("runs", "inspect", RUN_ID.value), runtime.operator)
        encoded = await run_cli(
            ("runs", "inspect", RUN_ID.value), runtime.operator, json_output=True
        )
        missing = await run_cli(("runs", "inspect", "missing"), runtime.operator)
        usage = await run_cli(("unknown",), runtime.operator)
        await runtime.aclose()

        assert direct == text.result == encoded.result
        assert text.exit_code == 0 and text.stderr == ""
        assert "Run inspection" in text.stdout
        assert json.loads(encoded.stdout)["data"]["run_id"] == RUN_ID.value
        assert missing.exit_code == OperatorExitCode.NOT_FOUND
        assert missing.stdout == "" and "run_not_found" in missing.stderr
        assert usage.exit_code == OperatorExitCode.USAGE

    asyncio.run(scenario())
