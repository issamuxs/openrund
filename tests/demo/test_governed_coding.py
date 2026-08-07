from __future__ import annotations

import ast
import asyncio
import re
import shutil
from pathlib import Path

import pytest

from openrund.demo import run_governed_coding_demo
from openrund.operator import DemoResultData, OperatorResult


def test_demo_has_no_runtime_substitutes() -> None:
    source = (Path(__file__).resolve().parents[2] / "src" / "openrund" / "demo.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

    assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "LocalIdFactories"
        and node.func.attr == "production"
        for node in ast.walk(tree)
    )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        keywords = {keyword.arg for keyword in node.keywords}
        if node.func.id == "LocalAssemblyConfig":
            assert keywords.isdisjoint({"clock", "capabilities"})
            assert "ids" in keywords
            assert "process_bindings" in keywords


def test_governed_coding_demo_uses_production_assembly_and_completes(tmp_path: Path) -> None:
    if shutil.which("git") is None:
        pytest.skip("git is required for the governed coding demonstration")

    async def execute(name: str, *, explicit_workspace: bool) -> OperatorResult[DemoResultData]:
        root = tmp_path / name
        return await run_governed_coding_demo(
            runtime_home=root / "runtime",
            workspace=root / "workspace" if explicit_workspace else None,
        )

    first = asyncio.run(execute("first", explicit_workspace=True))
    second = asyncio.run(execute("second", explicit_workspace=False))

    assert first.ok and second.ok
    first_run_id = first.data.run_id
    second_run_id = second.data.run_id
    assert isinstance(first_run_id, str)
    assert isinstance(second_run_id, str)
    assert re.fullmatch(r"run_[0-9a-f]{32}", first_run_id)
    assert re.fullmatch(r"run_[0-9a-f]{32}", second_run_id)
    assert first_run_id != second_run_id
    assert first.data.bundle_commitment != second.data.bundle_commitment
    assert first.data.status == second.data.status == "completed"
    assert first.data.workspace_selected_by == "host"
    assert second.data.workspace_selected_by == "default"
    assert first.data.event_count == second.data.event_count == 71
    assert first.data.illegal_mutation == second.data.illegal_mutation == "rejected"
    assert first.data.approval == second.data.approval == "deferred"
    builtins = first.data.builtins
    assert builtins == ("filesystem", "documents", "process", "git")
    assert first.data.unknown_outcome_reconciled is True
    assert first.data.delegated_join_resolved is True
    assert first.data.check_gate_rejection == "completion_blocked"
    assert first.data.completion_ready is True
    assert first.data.bundle_verified is True
    assert first.data.bundle_resumable is False
    assert second.data.bundle_verified is True
    assert second.data.bundle_resumable is False
    assert first.data.runtime_home == str(tmp_path / "first" / "runtime")
    assert first.data.workspace_root == str(tmp_path / "first" / "workspace")
    assert not (tmp_path / "first" / "runtime" / "runs" / first_run_id / "workspace").exists()
    assert (tmp_path / "first" / "workspace" / "report.md").read_text(
        encoding="utf-8"
    ) == "# Governed report\n\nCreated lawfully.\n"
    assert (tmp_path / "first" / "workspace" / "notes.md").read_text(
        encoding="utf-8"
    ) == "# Notes\n\nMarkdown worker completed.\n"
    default_workspace = tmp_path / "second" / "runtime" / "runs" / second_run_id / "workspace"
    assert second.data.workspace_root == str(default_workspace)
    assert default_workspace.joinpath("report.md").is_file()
