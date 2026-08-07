from __future__ import annotations

import json

import pytest

from openrund.errors import ValidationError
from openrund.operator import (
    OperatorExitCode,
    OperatorResult,
    render_operator_json,
    render_operator_text,
)


def test_success_result_has_stable_text_and_json_from_one_value() -> None:
    result = OperatorResult.success(
        command="runs inspect",
        title="Run inspection",
        data={"run_id": "run_one", "ready": False, "position": 3},
    )

    assert result.ok
    assert result.exit_code is OperatorExitCode.OK
    assert render_operator_text(result) == (
        "Run inspection\nrun_id: run_one\nready: false\nposition: 3\n"
    )
    assert json.loads(render_operator_json(result)) == {
        "ok": True,
        "command": "runs inspect",
        "exit_code": 0,
        "data": {"run_id": "run_one", "ready": False, "position": 3},
        "error": None,
    }


def test_failure_result_preserves_safe_classification_and_nonzero_exit() -> None:
    result = OperatorResult.failed(
        command="runs inspect",
        code="run_not_found",
        message="Run was not found",
        exit_code=OperatorExitCode.NOT_FOUND,
        data={"run_id": "missing"},
    )

    assert not result.ok
    assert render_operator_text(result) == (
        "OpenRund command failed\n"
        "error: run_not_found\n"
        "message: Run was not found\n"
        "run_id: missing\n"
    )
    assert json.loads(render_operator_json(result))["exit_code"] == 3


def test_result_rejects_inconsistent_success_and_failure_branches() -> None:
    failure = OperatorResult.failed(
        command="x",
        code="failed",
        message="failed",
        exit_code=OperatorExitCode.REJECTED,
    ).failure
    assert failure is not None
    with pytest.raises(ValidationError, match="operator_result_branch_invalid"):
        OperatorResult(
            command="x",
            title="x",
            data={},
            failure=failure,
        )
