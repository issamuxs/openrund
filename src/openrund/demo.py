"""Installed-package proof of the production governed coding lifecycle."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

from openrund.assembly import (
    LocalAssemblyConfig,
    LocalIdFactories,
    OperatorInput,
    OperatorInputRequest,
    create_local_runtime,
)
from openrund.capabilities import (
    FilesystemMount,
    GitIdentity,
    ProcessBinding,
)
from openrund.codec import canonical_content_hash
from openrund.contracts.capabilities import ActionReliability, CapabilityAccessMode
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    BootstrapRunOperation,
    Command,
    CommandOperation,
    CommandOrigin,
    CommandResult,
    CompleteDelegationOperation,
    CompleteRunOperation,
    CreateActionOperation,
    CreateDelegationOperation,
    DeferredCommandDecision,
    GrantCapabilityAuthorityOperation,
    GrantPolicyAuthorityOperation,
    MarkActionUnknownOperation,
    OpenJoinWaitOperation,
    RejectedCommandDecision,
    ResolveJoinWaitOperation,
    StartActionOperation,
)
from openrund.contracts.content import Content, RunResult
from openrund.contracts.ids import (
    ActionId,
    CapabilityId,
    CommandId,
    PolicyRuleId,
    RunId,
)
from openrund.contracts.json import JsonObject, freeze_json
from openrund.contracts.runs import (
    AuthorityGrant,
    CheckStatus,
    DelegatedRunKind,
    DelegationBudget,
    DelegationContract,
    DelegationInput,
    DelegationJoinMode,
)
from openrund.errors import ValidationError
from openrund.operator import (
    ActionReceiptData,
    BundleAssessmentData,
    BundleExportData,
    BundleImportData,
    BundleReplayData,
    DemoResultData,
    OperatorResult,
    RunChecksData,
    RunReadinessData,
    RunTimelineData,
)
from openrund.paths import PathInput, normalize_local_path
from openrund.ports.capabilities import CapabilityInvocation
from openrund.storage import RunHome, run_home


def _json(value: object) -> JsonObject:
    frozen = freeze_json(value)
    if not isinstance(frozen, JsonObject):
        raise ValidationError(code="demo_json_object_required")
    return frozen


def _git_executable() -> Path:
    found = shutil.which("git")
    if found is None:
        raise ValidationError(code="demo_git_unavailable")
    return Path(found).resolve()


def _initialize_repository(workspace: Path, git: Path) -> None:
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
    }
    try:
        subprocess.run(
            (git, "init", "--quiet"),
            cwd=workspace,
            env=environment,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        raise ValidationError(code="demo_git_initialization_failed") from None


async def _select_workspace(
    *,
    layout: RunHome,
    workspace: PathInput | None,
    operator_input: OperatorInput | None,
) -> tuple[Path, str]:
    if workspace is not None:
        selected = normalize_local_path(workspace).path
        selected_by = "host"
    elif operator_input is None:
        selected = layout.workspace
        selected_by = "default"
    else:
        response = await operator_input.request(
            OperatorInputRequest(
                kind="workspace_root",
                prompt=(
                    "Workspace root for run work products\n"
                    f"Default: {layout.workspace}\n"
                    "Workspace root [Enter for default] "
                ),
                metadata=_json({"default_workspace": str(layout.workspace)}),
            )
        )
        answer = response.value.strip()
        selected = normalize_local_path(answer).path if answer else layout.workspace
        selected_by = "operator" if answer else "default"
    if not selected.is_absolute():
        selected = Path.cwd() / selected
    return selected, selected_by


async def run_governed_coding_demo(
    *,
    runtime_home: PathInput,
    workspace: PathInput | None = None,
    operator_input: OperatorInput | None = None,
) -> OperatorResult[DemoResultData]:
    """Run the complete production-assembly governed workflow without network access."""

    home = normalize_local_path(runtime_home).path
    if not home.is_absolute():
        home = Path.cwd() / home
    ids = LocalIdFactories.production()
    run_id = ids.run_ids.new_id()
    layout = run_home(home, run_id)
    root, workspace_selected_by = await _select_workspace(
        layout=layout,
        workspace=workspace,
        operator_input=operator_input,
    )
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    git = _git_executable()
    await asyncio.to_thread(_initialize_repository, root, git)
    mount = FilesystemMount(
        name="workspace",
        root=root,
        access=CapabilityAccessMode.READ_WRITE,
    )
    runtime = create_local_runtime(
        LocalAssemblyConfig(
            runtime_home=home,
            ids=ids,
            mounts=(mount,),
            process_bindings=(
                ProcessBinding(
                    name="python",
                    executable=Path(sys.executable).resolve(),
                ),
            ),
            git_executable=git,
            git_identities=(
                GitIdentity(
                    name="demo",
                    author_name="OpenRund Demo",
                    author_email="demo@example.rejected",
                ),
            ),
        )
    )
    clock = runtime.config.clock
    ids = runtime.config.ids
    child_id = ids.run_ids.new_id()
    rejected_action_id = ids.action_ids.new_id()
    filesystem_action_id = ids.action_ids.new_id()
    documents_action_id = ids.action_ids.new_id()
    process_action_id = ids.action_ids.new_id()
    git_action_id = ids.action_ids.new_id()
    unknown_action_id = ids.action_ids.new_id()
    join_id = ids.wait_ids.new_id()

    async def submit(
        operation: CommandOperation,
        *,
        origin: CommandOrigin,
        target: RunId = run_id,
    ) -> tuple[CommandId, CommandResult]:
        command_id = ids.command_ids.new_id()
        result = await runtime.engine.submit(
            Command(
                command_id=command_id,
                run_id=target,
                origin=origin,
                operation=operation,
                created_at=clock.now(),
            )
        )
        return command_id, result

    async def accepted_action(
        *,
        action_id: ActionId,
        capability: str,
        action: str,
        data: object,
    ) -> None:
        content = Content(data=_json(data))
        _command_id, created = await submit(
            CreateActionOperation(
                action_id=action_id,
                capability_id=CapabilityId(value=capability),
                action_name=action,
                input=content,
            ),
            origin=CommandOrigin.MODEL,
        )
        if not isinstance(created.decision, AcceptedCommandDecision):
            raise ValidationError(code="demo_action_creation_failed", safe_detail=capability)
        completed = await runtime.action_runner.execute(
            run_id,
            CapabilityInvocation(
                action_id=action_id,
                capability_id=CapabilityId(value=capability),
                action_name=action,
                input=content,
            ),
        )
        if not isinstance(completed.decision, AcceptedCommandDecision):
            raise ValidationError(code="demo_action_execution_failed", safe_detail=capability)
        receipt = await runtime.operator.action_receipt(run_id, action_id)
        if (
            not receipt.ok
            or not isinstance(receipt.data, ActionReceiptData)
            or receipt.data.status != "completed"
        ):
            raise ValidationError(
                code="demo_action_outcome_unconfirmed",
                safe_detail=capability,
            )

    async with runtime:
        _bootstrap_id, bootstrap = await submit(
            BootstrapRunOperation(
                root_id=run_id,
                title="Governed coding demonstration",
                objective="Prove durable lawful coding work",
                metadata=_json(
                    {
                        "execution": {
                            "runtime_home": str(home),
                            "workspace": str(root),
                            "workspace_selected_by": workspace_selected_by,
                            "exports": str(layout.exports),
                        },
                        "run_contract": {
                            "check": {"checks": ["quality"]},
                            "completion": {"kind": "known_action_outcomes"},
                        },
                    }
                ),
                start_reason="governed coding demo",
            ),
            origin=CommandOrigin.SYSTEM,
        )
        if not isinstance(bootstrap.decision, AcceptedCommandDecision):
            raise ValidationError(code="demo_bootstrap_failed")

        rejected_id, rejected = await submit(
            CreateActionOperation(
                action_id=rejected_action_id,
                capability_id=CapabilityId(value="filesystem"),
                action_name="write",
                input=Content(
                    data=_json(
                        {
                            "mount": "workspace",
                            "path": "report.md",
                            "text": "rejected",
                        }
                    )
                ),
            ),
            origin=CommandOrigin.MODEL,
        )
        if not isinstance(rejected.decision, RejectedCommandDecision):
            raise ValidationError(code="demo_expected_rejection_missing")

        for definition in runtime.registry.definitions:
            _grant_id, grant = await submit(
                GrantCapabilityAuthorityOperation(
                    capability_id=definition.capability_id,
                    constraints=_json(
                        {
                            "actions": [item.name for item in definition.actions],
                            "writableRoots": ["workspace"],
                        }
                    ),
                ),
                origin=CommandOrigin.OPERATOR,
            )
            if not isinstance(grant.decision, AcceptedCommandDecision):
                raise ValidationError(code="demo_authority_grant_failed")
        _policy_id, policy = await submit(
            GrantPolicyAuthorityOperation(
                rule_id=PolicyRuleId(value="filesystem_writes_require_approval"),
                rule=_json(
                    {
                        "kind": "require_approval_for_capability_action",
                        "config": {"capabilityID": "filesystem", "actionName": "write"},
                    }
                ),
            ),
            origin=CommandOrigin.OPERATOR,
        )
        if not isinstance(policy.decision, AcceptedCommandDecision):
            raise ValidationError(code="demo_policy_grant_failed")

        filesystem_input = _json(
            {
                "mount": "workspace",
                "path": "report.md",
                "text": "# Governed report\n\nCreated lawfully.\n",
            }
        )
        deferred_id, deferred = await submit(
            CreateActionOperation(
                action_id=filesystem_action_id,
                capability_id=CapabilityId(value="filesystem"),
                action_name="write",
                input=Content(data=filesystem_input),
            ),
            origin=CommandOrigin.MODEL,
        )
        if not isinstance(deferred.decision, DeferredCommandDecision):
            raise ValidationError(code="demo_expected_deferral_missing")
        wait_id = deferred.decision.wait_ids[0]
        approval = await runtime.operator.resolve_approval(
            run_id,
            wait_id,
            decision="approved",
            resolved_by="demo_operator",
            note="Reviewed explicit workspace write",
        )
        resumed = await runtime.operator.resume_approval(run_id, wait_id)
        if not approval.ok or not resumed.ok:
            raise ValidationError(code="demo_approval_failed")
        filesystem_completed = await runtime.action_runner.execute(
            run_id,
            CapabilityInvocation(
                action_id=filesystem_action_id,
                capability_id=CapabilityId(value="filesystem"),
                action_name="write",
                input=Content(data=filesystem_input),
            ),
        )
        if not isinstance(filesystem_completed.decision, AcceptedCommandDecision):
            raise ValidationError(code="demo_filesystem_execution_failed")

        await accepted_action(
            action_id=documents_action_id,
            capability="documents",
            action="write",
            data={
                "mount": "workspace",
                "path": "notes.md",
                "text": "# Notes\n\nMarkdown worker completed.\n",
            },
        )
        await accepted_action(
            action_id=process_action_id,
            capability="process",
            action="run",
            data={
                "executable": "python",
                "args": ["-c", "print('process boundary completed')"],
                "cwdMount": "workspace",
            },
        )
        await accepted_action(
            action_id=git_action_id,
            capability="git",
            action="status",
            data={"repoMount": "workspace"},
        )

        unknown_id = unknown_action_id
        unknown_input = Content(data=_json({"mount": "workspace", "path": "report.md"}))
        _unknown_create_id, unknown_created = await submit(
            CreateActionOperation(
                action_id=unknown_id,
                capability_id=CapabilityId(value="filesystem"),
                action_name="stat",
                input=unknown_input,
            ),
            origin=CommandOrigin.MODEL,
        )
        if not isinstance(unknown_created.decision, AcceptedCommandDecision):
            raise ValidationError(code="demo_unknown_action_creation_failed")
        _unknown_start_id, unknown_started = await submit(
            StartActionOperation(
                action_id=unknown_id,
                capability_id=CapabilityId(value="filesystem"),
                action_name="stat",
                input_hash=canonical_content_hash(unknown_input),
            ),
            origin=CommandOrigin.CAPABILITY,
        )
        if not isinstance(unknown_started.decision, AcceptedCommandDecision):
            raise ValidationError(code="demo_unknown_action_start_failed")
        _unknown_id, unknown = await submit(
            MarkActionUnknownOperation(
                action_id=unknown_id,
                reliability=ActionReliability.TRANSPORT_LOST,
                reason="transport_ambiguity",
            ),
            origin=CommandOrigin.CAPABILITY,
        )
        if not isinstance(unknown.decision, AcceptedCommandDecision):
            raise ValidationError(code="demo_unknown_record_failed")
        reconciled = await runtime.operator.reconcile_action(
            run_id,
            unknown_id,
            outcome="completed",
            evidence="Operator verified report.md exists with the expected digest",
            reconciled_by="demo_operator",
        )
        if not reconciled.ok:
            raise ValidationError(code="demo_reconciliation_failed")

        _delegation_command_id, delegation = await submit(
            CreateDelegationOperation(
                delegated_run_id=child_id,
                contract=DelegationContract(
                    run_kind=DelegatedRunKind.WORKER,
                    objective="Inspect the generated report",
                    authority_grants=(
                        AuthorityGrant(
                            capability_id=CapabilityId(value="filesystem"),
                            actions=("read",),
                        ),
                    ),
                    authority_drift="snapshot",
                    budget=DelegationBudget(max_requests=1, wall_clock_timeout_ms=30_000),
                    result_kind="analysis",
                    required_artifact_kinds=(),
                    allow_nested_delegation=False,
                    on_parent_cancel="cancel",
                    late_handoff="surface",
                ),
                input=DelegationInput(data=_json({"path": "report.md"})),
            ),
            origin=CommandOrigin.MODEL,
        )
        if not isinstance(delegation.decision, AcceptedCommandDecision):
            raise ValidationError(code="demo_delegation_failed")
        _join_open_id, join_opened = await submit(
            OpenJoinWaitOperation(
                wait_id=join_id,
                target_run_ids=(child_id,),
                mode=DelegationJoinMode.ALL,
                outcome_filter="completed_only",
                failure_policy="wait_for_all_terminal",
                on_satisfied="keep_bound",
                late_handoff_policy="surface",
            ),
            origin=CommandOrigin.OPERATOR,
        )
        _child_complete_id, child_completed = await submit(
            CompleteRunOperation(result=RunResult(kind="analysis", summary="Report inspected")),
            origin=CommandOrigin.SYSTEM,
            target=child_id,
        )
        _handoff_id, handoff = await submit(
            CompleteDelegationOperation(delegated_run_id=child_id),
            origin=CommandOrigin.OPERATOR,
        )
        _join_resolve_id, join_resolved = await submit(
            ResolveJoinWaitOperation(wait_id=join_id),
            origin=CommandOrigin.OPERATOR,
        )
        if not all(
            isinstance(item.decision, AcceptedCommandDecision)
            for item in (join_opened, child_completed, handoff, join_resolved)
        ):
            raise ValidationError(code="demo_join_failed")

        _early_complete_id, early_complete = await submit(
            CompleteRunOperation(result=RunResult(kind="coding", summary="Done")),
            origin=CommandOrigin.SYSTEM,
        )
        if not isinstance(early_complete.decision, RejectedCommandDecision):
            raise ValidationError(code="demo_check_gate_missing")
        checked = await runtime.operator.record_check(
            run_id,
            "quality",
            status=CheckStatus.PASSED,
            summary="All checks passed",
            validator="demo",
        )
        readiness_before_completion = await runtime.operator.readiness(run_id)
        _complete_id, completed = await submit(
            CompleteRunOperation(result=RunResult(kind="coding", summary="Demo complete")),
            origin=CommandOrigin.SYSTEM,
        )
        if not checked.ok:
            raise ValidationError(
                code="demo_check_recording_failed",
                safe_detail=(checked.failure.code if checked.failure is not None else None),
            )
        if not isinstance(completed.decision, AcceptedCommandDecision):
            blockers = (
                readiness_before_completion.data.blockers
                if isinstance(readiness_before_completion.data, RunReadinessData)
                else ()
            )
            raise ValidationError(
                code="demo_completion_failed",
                safe_detail=str(blockers),
            )

        rejected_explanation = await runtime.operator.explain_command(run_id, rejected_id)
        deferred_explanation = await runtime.operator.explain_command(run_id, deferred_id)
        receipt = await runtime.operator.action_receipt(run_id, filesystem_action_id)
        readiness = await runtime.operator.readiness(run_id)
        timeline = await runtime.operator.timeline(run_id)
        checks = await runtime.operator.checks(run_id)
        if not all(
            result.ok
            for result in (
                rejected_explanation,
                deferred_explanation,
                receipt,
                readiness,
                timeline,
                checks,
            )
        ):
            raise ValidationError(code="demo_inspection_failed")

        bundle_path = layout.exports / "governed-coding.orun"
        exported = await runtime.operator.export_run_bundle(run_id, bundle_path)
        verified = runtime.operator.verify_run_bundle(bundle_path)
        replayed = runtime.operator.replay_run_bundle(bundle_path)
        assessed = runtime.operator.assess_run_bundle(bundle_path, {"workspace": root})
        imported = runtime.operator.import_run_bundle(bundle_path, {"workspace": root})
        if not all(result.ok for result in (exported, verified, replayed, assessed, imported)):
            raise ValidationError(code="demo_bundle_lifecycle_failed")
        history = await runtime.event_store.read(run_id)

    if not isinstance(readiness.data, RunReadinessData):
        raise ValidationError(code="demo_inspection_result_invalid")
    if not isinstance(timeline.data, RunTimelineData):
        raise ValidationError(code="demo_inspection_result_invalid")
    if not isinstance(checks.data, RunChecksData):
        raise ValidationError(code="demo_inspection_result_invalid")
    if not isinstance(exported.data, BundleExportData):
        raise ValidationError(code="demo_bundle_result_invalid")
    if not isinstance(replayed.data, BundleReplayData):
        raise ValidationError(code="demo_bundle_result_invalid")
    if not isinstance(imported.data, BundleImportData):
        raise ValidationError(code="demo_bundle_result_invalid")
    if not isinstance(assessed.data, BundleAssessmentData):
        raise ValidationError(code="demo_bundle_result_invalid")
    return OperatorResult.success(
        command="demo governed-coding",
        title="Governed coding demonstration complete",
        data=DemoResultData(
            run_id=run_id.value,
            status="completed",
            runtime_home=str(home),
            workspace_root=str(root),
            workspace_selected_by=workspace_selected_by,
            bundle_path=str(bundle_path),
            event_count=len(history.events),
            illegal_mutation=rejected.decision.kind,
            approval=deferred.decision.kind,
            builtins=("filesystem", "documents", "process", "git"),
            unknown_outcome_reconciled=True,
            delegated_join_resolved=True,
            check_gate_rejection=early_complete.decision.reason,
            completion_ready=readiness.data.ready,
            timeline_entries=len(timeline.data.entries),
            check_reports=len(checks.data.reports),
            bundle_commitment=exported.data.commitment,
            bundle_verified=True,
            bundle_event_count=replayed.data.event_count,
            bundle_import_id=imported.data.import_id,
            bundle_resumable=assessed.data.resumable,
        ),
    )
