from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.capabilities import (
    Capability,
    CapabilityAccessMode,
    CapabilityAction,
    CapabilityReliability,
)
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    Command,
    CommandOrigin,
    CreateActionOperation,
    DeferredCommandDecision,
    GrantCapabilityAuthorityOperation,
    GrantPolicyAuthorityOperation,
    RejectedCommandDecision,
    RevokeCapabilityAuthorityOperation,
)
from openrund.contracts.content import Content
from openrund.contracts.events import (
    CoreEventType,
    EventPayload,
    RunCreatedPayload,
    RunStartedPayload,
)
from openrund.contracts.ids import ActionId, CapabilityId, CommandId, PolicyRuleId, RunId
from openrund.contracts.json import JsonObject, freeze_json
from openrund.engine import EngineDependencies, GovernanceContext, RuntimeEngine, schema_violations
from openrund.errors import ValidationError
from openrund.paths import LocalPath
from openrund.ports.events import AppendEventsInput
from tests.engine.conftest import runtime_event

RUN_ID = RunId(value="run_1")


def _json(value: object) -> JsonObject:
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


def _capability() -> Capability:
    return Capability(
        capability_id=CapabilityId(value="filesystem"),
        version="1",
        actions=(
            CapabilityAction(
                name="write",
                description="write a workspace file",
                posture=CapabilityAccessMode.WRITE,
                reliability=CapabilityReliability.IDEMPOTENT_MUTATION,
                input_schema=_json(
                    {
                        "type": "object",
                        "required": ["path", "content"],
                        "properties": {
                            "path": {"type": "string", "minLength": 1},
                            "content": {"type": "string"},
                            "writableRoots": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "additionalProperties": False,
                    }
                ),
            ),
        ),
    )


def test_governance_context_is_immutable_unique_and_queryable() -> None:
    capability = _capability()
    context = GovernanceContext(
        capabilities=(capability,),
        workspace_roots=(LocalPath(raw="/workspace"),),
        tenant_id="tenant-a",
        security_context=_json({"classification": "internal"}),
    )

    assert context.capability(CapabilityId(value="filesystem")) == capability
    assert context.action(CapabilityId(value="filesystem"), "write") == capability.actions[0]
    assert context.action(CapabilityId(value="filesystem"), "missing") is None

    with pytest.raises(ValidationError, match="governance_capability_duplicate"):
        GovernanceContext(capabilities=(capability, capability))
    with pytest.raises(ValidationError, match="governance_workspace_roots_invalid"):
        GovernanceContext(workspace_roots=(LocalPath(raw="relative"),))
    with pytest.raises(ValidationError, match="governance_workspace_roots_invalid"):
        GovernanceContext(workspace_roots=(LocalPath(raw="/workspace/../outside"),))


def test_supported_schema_accepts_exact_input_and_reports_stable_violations() -> None:
    schema = _capability().actions[0].input_schema

    assert schema_violations(_json({"path": "report.md", "content": "done"}), schema) == ()
    assert schema_violations(_json({"path": "", "extra": True}), schema) == (
        "$.content:required",
        "$.path:min_length",
        "$.extra:additional_property",
    )


def test_schema_validation_fails_closed_on_unknown_keyword() -> None:
    schema = _json({"type": "object", "unevaluatedProperties": False})

    assert schema_violations(_json({}), schema) == (
        "$:schema_keyword_unsupported:unevaluatedProperties",
    )


def _seed(event_store: MemoryEventStore, *payloads: tuple[CoreEventType, EventPayload]) -> None:
    events = (
        runtime_event(
            CoreEventType.RUN_CREATED,
            RunCreatedPayload(root_id=RUN_ID, initial_status="created"),
            1,
        ),
        runtime_event(CoreEventType.RUN_STARTED, RunStartedPayload(), 2),
        *(
            runtime_event(event_type, payload, index)
            for index, (event_type, payload) in enumerate(payloads, start=3)
        ),
    )
    asyncio.run(
        event_store.append(AppendEventsInput(run_id=RUN_ID, expected_position=0, events=events))
    )


def _command(command_id: str, operation: object, *, origin: CommandOrigin) -> Command:
    return Command(
        command_id=CommandId(value=command_id),
        run_id=RUN_ID,
        origin=origin,
        operation=operation,  # type: ignore[arg-type]
    )


def _configured(dependencies: EngineDependencies) -> EngineDependencies:
    return replace(
        dependencies,
        governance=GovernanceContext(
            capabilities=(_capability(),),
            workspace_roots=(LocalPath(raw="/workspace"),),
            tenant_id="tenant-a",
            security_context=_json({"classification": "internal"}),
        ),
    )


def _action(action_id: str, *, path: object = "/workspace/report.md") -> CreateActionOperation:
    return CreateActionOperation(
        action_id=ActionId(value=action_id),
        capability_id=CapabilityId(value="filesystem"),
        action_name="write",
        input=Content(
            data=_json(
                {
                    "path": path,
                    "content": "done",
                    "writableRoots": ["/workspace"],
                }
            )
        ),
    )


def test_authority_is_durable_origin_restricted_and_revocable(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store)
    engine = RuntimeEngine(_configured(engine_dependencies))
    grant = GrantCapabilityAuthorityOperation(
        capability_id=CapabilityId(value="filesystem"),
        constraints=_json(
            {
                "actions": ["write"],
                "writableRoots": ["/workspace"],
                "tenantId": "tenant-a",
                "securityContext": {"classification": "internal"},
            }
        ),
    )

    forbidden = asyncio.run(
        engine.submit(_command("model-grant", grant, origin=CommandOrigin.MODEL))
    )
    granted = asyncio.run(
        engine.submit(_command("operator-grant", grant, origin=CommandOrigin.OPERATOR))
    )
    created = asyncio.run(
        engine.submit(_command("create", _action("action_1"), origin=CommandOrigin.MODEL))
    )
    revoked = asyncio.run(
        engine.submit(
            _command(
                "revoke",
                RevokeCapabilityAuthorityOperation(capability_id=CapabilityId(value="filesystem")),
                origin=CommandOrigin.OPERATOR,
            )
        )
    )
    after_revoke = asyncio.run(
        engine.submit(_command("create-2", _action("action_2"), origin=CommandOrigin.MODEL))
    )

    assert isinstance(forbidden.decision, RejectedCommandDecision)
    assert forbidden.decision.reason == "authority_origin_forbidden"
    assert isinstance(granted.decision, AcceptedCommandDecision)
    assert isinstance(created.decision, AcceptedCommandDecision)
    assert isinstance(revoked.decision, AcceptedCommandDecision)
    assert isinstance(after_revoke.decision, RejectedCommandDecision)
    assert after_revoke.decision.reason == "capability_authority_missing"


def test_hard_governance_rejects_before_policy_can_create_approval_wait(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store)
    engine = RuntimeEngine(_configured(engine_dependencies))
    asyncio.run(
        engine.submit(
            _command(
                "grant-capability",
                GrantCapabilityAuthorityOperation(
                    capability_id=CapabilityId(value="filesystem"),
                    constraints=_json({"writableRoots": ["/workspace"]}),
                ),
                origin=CommandOrigin.OPERATOR,
            )
        )
    )
    asyncio.run(
        engine.submit(
            _command(
                "grant-policy",
                GrantPolicyAuthorityOperation(
                    rule_id=PolicyRuleId(value="approval"),
                    rule=_json(
                        {
                            "kind": "require_approval_for_capability_action",
                            "config": {
                                "capabilityID": "filesystem",
                                "actionName": "write",
                            },
                        }
                    ),
                ),
                origin=CommandOrigin.OPERATOR,
            )
        )
    )

    invalid_schema = asyncio.run(
        engine.submit(
            _command("invalid-schema", _action("bad-schema", path=7), origin=CommandOrigin.MODEL)
        )
    )
    escaped = asyncio.run(
        engine.submit(
            _command(
                "escaped",
                _action("bad-scope", path="/etc/passwd"),
                origin=CommandOrigin.MODEL,
            )
        )
    )
    legal = asyncio.run(
        engine.submit(_command("legal", _action("legal"), origin=CommandOrigin.MODEL))
    )

    assert isinstance(invalid_schema.decision, RejectedCommandDecision)
    assert invalid_schema.decision.reason == "capability_input_invalid"
    assert isinstance(escaped.decision, RejectedCommandDecision)
    assert escaped.decision.reason == "resource_scope_escape"
    assert isinstance(legal.decision, DeferredCommandDecision)
    history = asyncio.run(event_store.read(RUN_ID))
    assert sum(event.event_type is CoreEventType.WAIT_CREATED for event in history.events) == 1


@pytest.mark.parametrize("path", ("../../etc/passwd", "C:\\Windows\\system.ini"))
def test_resource_scope_rejects_portable_path_escape_forms(
    path: str,
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store)
    engine = RuntimeEngine(_configured(engine_dependencies))
    asyncio.run(
        engine.submit(
            _command(
                "grant",
                GrantCapabilityAuthorityOperation(
                    capability_id=CapabilityId(value="filesystem"),
                    constraints=_json({"writableRoots": ["/workspace"]}),
                ),
                origin=CommandOrigin.OPERATOR,
            )
        )
    )

    escaped = asyncio.run(
        engine.submit(
            _command(
                "escaped-portable",
                _action("escaped-portable", path=path),
                origin=CommandOrigin.MODEL,
            )
        )
    )

    assert isinstance(escaped.decision, RejectedCommandDecision)
    assert escaped.decision.reason == "resource_scope_escape"
