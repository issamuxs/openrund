from __future__ import annotations

import asyncio

import pytest

from openrund.capabilities import (
    ActionTransportBinding,
    CapabilityRegistry,
    InProcessTransport,
    RegisteredCapability,
)
from openrund.contracts.capabilities import (
    Capability,
    CapabilityAccessMode,
    CapabilityAction,
    CapabilityArtifact,
    CapabilityBatching,
    CapabilityCancellation,
    CapabilityInlineArtifact,
    CapabilityReliability,
    CapabilityResult,
    CapabilityTransportKind,
    CapabilityTransportMetadata,
)
from openrund.contracts.content import Content
from openrund.contracts.ids import ActionId, CapabilityId
from openrund.contracts.json import JsonObject, freeze_json
from openrund.errors import CapabilityProtocolError, ValidationError
from openrund.ports.capabilities import CapabilityInvocation


def _schema(value: object) -> JsonObject:
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


async def _handler(invocation: CapabilityInvocation) -> CapabilityResult:
    assert invocation.action_name == "inspect"
    return CapabilityResult(
        output={"ok": True},  # type: ignore[arg-type]
        inline_artifacts=(CapabilityInlineArtifact(kind="receipt", content=b"evidence"),),
    )


def _action(**overrides: object) -> CapabilityAction:
    values: dict[str, object] = {
        "name": "inspect",
        "description": "Inspect one governed value",
        "posture": CapabilityAccessMode.READ,
        "reliability": CapabilityReliability.READ_ONLY,
        "input_schema": _schema(
            {
                "type": "object",
                "required": ["value"],
                "properties": {"value": {"type": "string", "minLength": 1}},
                "additionalProperties": False,
            }
        ),
        "output_schema": _schema(
            {
                "type": "object",
                "required": ["ok"],
                "properties": {"ok": {"type": "boolean"}},
                "additionalProperties": False,
            }
        ),
        "batching": CapabilityBatching(eligible=True, max_size=4),
        "cancellation": CapabilityCancellation(),
        "artifacts": (CapabilityArtifact(kind="receipt", required=True),),
        "transport": CapabilityTransportMetadata(kind=CapabilityTransportKind.IN_PROCESS),
    }
    values.update(overrides)
    return CapabilityAction(**values)  # type: ignore[arg-type]


def _registered(action: CapabilityAction | None = None) -> RegisteredCapability:
    transport = InProcessTransport(_handler)
    definition = Capability(
        capability_id=CapabilityId(value="cap.test"),
        version="1",
        actions=(_action() if action is None else action,),
    )
    return RegisteredCapability(
        definition=definition,
        bindings=(ActionTransportBinding(action_name="inspect", transport=transport),),
    )


def _invocation(data: object) -> CapabilityInvocation:
    return CapabilityInvocation(
        action_id=ActionId(value="action-1"),
        capability_id=CapabilityId(value="cap.test"),
        action_name="inspect",
        input=Content(data=data),  # type: ignore[arg-type]
    )


def test_registry_validates_and_invokes_one_bound_action() -> None:
    registry = CapabilityRegistry((_registered(),))

    result = asyncio.run(registry.invoke(_invocation({"value": "safe"})))

    assert result.output == freeze_json({"ok": True})
    assert result.inline_artifacts[0].content == b"evidence"
    assert registry.definitions[0].capability_id == CapabilityId(value="cap.test")


@pytest.mark.parametrize(
    ("action", "code"),
    [
        (
            _action(input_schema=_schema({"type": "object", "patternProperties": {}})),
            "capability_input_schema_unsupported",
        ),
        (
            _action(
                reliability=CapabilityReliability.INTERRUPTIBLE,
                cancellation=CapabilityCancellation(supported=False),
            ),
            "capability_interruptible_cancellation_required",
        ),
        (
            _action(
                reliability=CapabilityReliability.READ_ONLY,
                cancellation=CapabilityCancellation(supported=True),
            ),
            "capability_cancellation_reliability_mismatch",
        ),
    ],
)
def test_registration_rejects_incoherent_action_metadata(
    action: CapabilityAction, code: str
) -> None:
    with pytest.raises(ValidationError, match=code):
        _registered(action)


def test_registration_requires_exactly_one_binding_per_action() -> None:
    definition = Capability(
        capability_id=CapabilityId(value="cap.test"),
        version="1",
        actions=(_action(),),
    )
    with pytest.raises(ValidationError, match="capability_binding_incomplete"):
        RegisteredCapability(definition=definition, bindings=())

    binding = ActionTransportBinding(action_name="inspect", transport=InProcessTransport(_handler))
    with pytest.raises(ValidationError, match="capability_binding_duplicate"):
        RegisteredCapability(definition=definition, bindings=(binding, binding))


def test_registry_rejects_duplicate_capabilities_and_unknown_routes() -> None:
    registered = _registered()
    with pytest.raises(ValidationError, match="capability_registry_duplicate"):
        CapabilityRegistry((registered, registered))
    registry = CapabilityRegistry((registered,))
    with pytest.raises(CapabilityProtocolError, match="capability_not_registered"):
        registry.resolve(CapabilityId(value="missing"), "inspect")
    with pytest.raises(CapabilityProtocolError, match="capability_action_not_registered"):
        registry.resolve(CapabilityId(value="cap.test"), "missing")


def test_registry_rejects_input_output_and_artifact_drift() -> None:
    registry = CapabilityRegistry((_registered(),))
    with pytest.raises(CapabilityProtocolError, match="capability_input_schema_violation"):
        asyncio.run(registry.invoke(_invocation({"value": "", "extra": True})))

    route = registry.resolve(CapabilityId(value="cap.test"), "inspect")
    with pytest.raises(CapabilityProtocolError, match="capability_output_schema_violation"):
        route.validate_result(CapabilityResult(output={"ok": "yes"}))  # type: ignore[arg-type]
    with pytest.raises(CapabilityProtocolError, match="capability_artifact_kind_undeclared"):
        route.validate_result(
            CapabilityResult(
                output={"ok": True},  # type: ignore[arg-type]
                inline_artifacts=(CapabilityInlineArtifact(kind="other", content=b"x"),),
            )
        )
    with pytest.raises(CapabilityProtocolError, match="capability_artifact_required_missing"):
        route.validate_result(CapabilityResult(output={"ok": True}))  # type: ignore[arg-type]


def test_capability_metadata_values_are_frozen_and_strict() -> None:
    with pytest.raises(ValidationError, match="capability_batching_size_forbidden"):
        CapabilityBatching(eligible=False, max_size=2)
    with pytest.raises(ValidationError, match="capability_action_artifact_kind_duplicate"):
        _action(artifacts=(CapabilityArtifact(kind="x"), CapabilityArtifact(kind="x")))
    source = {"nested": [1]}
    artifact = CapabilityInlineArtifact(kind="receipt", content=b"x", metadata=source)  # type: ignore[arg-type]
    source["nested"].append(2)
    assert artifact.metadata == freeze_json({"nested": [1]})
