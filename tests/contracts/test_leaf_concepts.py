from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

from openrund.contracts.capabilities import (
    Action,
    ActionOutcome,
    ActionReliability,
    Capability,
    CapabilityAccessMode,
    CapabilityAction,
    CapabilityReliability,
    CapabilityResult,
)
from openrund.contracts.content import (
    ArtifactReference,
    Content,
    EffectEntry,
    EvidenceEntry,
    Mutation,
    MutationOperationKind,
    MutationReversibility,
    ResultPart,
    RunResult,
    utf8_byte_length,
)
from openrund.contracts.ids import ActionId, ArtifactId, CapabilityId, EventId, RunId
from openrund.contracts.json import JsonObject
from openrund.contracts.portable import Bundle, BundleProfile, View, ViewWatermark
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError
from openrund.paths import PortablePath


def test_content_preserves_exact_strings_and_utf8_lengths() -> None:
    empty = ""
    ascii_text = "hello"
    bmp = "\N{EURO SIGN}"
    astral = "\N{GRINNING FACE}"
    composed = "caf\N{LATIN SMALL LETTER E WITH ACUTE}"
    decomposed = "cafe\N{COMBINING ACUTE ACCENT}"

    assert Content(preview=composed) != Content(preview=decomposed)
    assert utf8_byte_length(empty) == 0
    assert utf8_byte_length(ascii_text) == 5
    assert utf8_byte_length(bmp) == 3
    assert utf8_byte_length(astral) == 4
    assert utf8_byte_length(composed) == 5
    assert utf8_byte_length(decomposed) == 6


def test_content_recursively_freezes_nested_values_and_input_sequences() -> None:
    metadata: dict[str, object] = {"nested": [1, {"ok": True}]}
    artifact_ids = [ArtifactId(value="artifact-1")]
    content = Content(preview="preview", artifact_ids=artifact_ids, metadata=metadata)  # type: ignore[arg-type]

    artifact_ids.append(ArtifactId(value="artifact-2"))
    metadata["late"] = True

    assert content.artifact_ids == (ArtifactId(value="artifact-1"),)
    assert isinstance(content.metadata, JsonObject)
    assert "late" not in content.metadata
    with pytest.raises(FrozenInstanceError):
        content.preview = "changed"  # type: ignore[misc]


def test_content_and_result_values_validate_exact_id_kinds() -> None:
    reference = ArtifactReference(artifact_id=ArtifactId(value="artifact"))
    part = ResultPart(kind="artifact", artifact_id=reference.artifact_id)
    result = RunResult(kind="answer", parts=[part], artifact_ids=[reference.artifact_id])  # type: ignore[arg-type]

    assert result.parts == (part,)
    with pytest.raises(ValidationError, match="artifact_reference_id_invalid"):
        ArtifactReference(artifact_id=RunId(value="wrong"))  # type: ignore[arg-type]


def test_mutations_effects_and_evidence_are_inert_immutable_data() -> None:
    mutation = Mutation(
        affected_resources=[{"uri": "workspace/report.md"}],  # type: ignore[arg-type]
        operation_kind=MutationOperationKind.UPDATE,
        reversibility=MutationReversibility.REVERSIBLE,
        preview=Content(preview="edit"),
    )
    effect = EffectEntry(kind="document.updated", artifact_ids=[ArtifactId(value="a")])  # type: ignore[arg-type]
    evidence = EvidenceEntry(artifact_id=ArtifactId(value="e"), description="receipt")

    assert isinstance(mutation.affected_resources[0], JsonObject)
    assert effect.artifact_ids == (ArtifactId(value="a"),)
    assert evidence.description == "receipt"
    for value in (mutation, effect, evidence):
        assert not hasattr(value, "execute")
        assert not hasattr(value, "append")


def _capability_action() -> CapabilityAction:
    return CapabilityAction(
        name="read",
        description="Read a value",
        posture=CapabilityAccessMode.READ,
        reliability=CapabilityReliability.READ_ONLY,
        input_schema={"type": "object"},  # type: ignore[arg-type]
    )


def test_capability_and_action_values_validate_branches_without_authority_methods() -> None:
    definition = Capability(
        capability_id=CapabilityId(value="filesystem"),
        version="1.0.0",
        actions=[_capability_action()],  # type: ignore[arg-type]
    )
    result = CapabilityResult(output={"ok": True})  # type: ignore[arg-type]
    action = Action(
        action_id=ActionId(value="action-1"),
        capability_id=definition.capability_id,
        action_name="read",
        input=Content(data={"path": "file.md"}),  # type: ignore[arg-type]
        outcome=ActionOutcome.COMPLETED,
        result=result,
    )

    assert definition.actions == (_capability_action(),)
    assert isinstance(result.output, JsonObject)
    assert action.result == result
    for value in (definition, result, action):
        for forbidden in ("execute", "emit_event", "append", "grant_authority"):
            assert not hasattr(value, forbidden)


def test_action_cross_field_rules_reject_ambiguous_outcomes() -> None:
    common = {
        "action_id": ActionId(value="action"),
        "capability_id": CapabilityId(value="capability"),
        "action_name": "run",
        "input": Content(),
    }
    with pytest.raises(ValidationError, match="action_unknown_reliability_required"):
        Action(**common, outcome=ActionOutcome.UNKNOWN)  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="action_completed_result_required"):
        Action(**common, outcome=ActionOutcome.COMPLETED)  # type: ignore[arg-type]

    unknown = Action(
        **common,  # type: ignore[arg-type]
        outcome=ActionOutcome.UNKNOWN,
        reliability=ActionReliability.TRANSPORT_LOST,
    )
    assert unknown.reliability is ActionReliability.TRANSPORT_LOST


def test_bundle_and_view_are_typed_inert_value_envelopes() -> None:
    run_id = RunId(value="run")
    bundle = Bundle(
        run_id=run_id,
        profile=BundleProfile.AUDIT,
        exported_at=Timestamp(value="2026-01-02T03:04:05.678Z"),
        event_ids=[EventId(value="event")],  # type: ignore[arg-type]
        relative_paths=[PortablePath(value="events.jsonl")],  # type: ignore[arg-type]
    )
    view = View(
        name="run_status",
        watermark=ViewWatermark(run_id=run_id, position=1),
        value={"status": "running"},  # type: ignore[arg-type]
    )

    assert bundle.event_ids == (EventId(value="event"),)
    assert isinstance(view.value, JsonObject)
    for value in (bundle, view):
        for forbidden in ("export", "import_bundle", "replay", "reduce", "persist"):
            assert not hasattr(value, forbidden)


@pytest.mark.parametrize(
    "value_type",
    [
        Content,
        ArtifactReference,
        Mutation,
        EffectEntry,
        EvidenceEntry,
        ResultPart,
        RunResult,
        CapabilityAction,
        Capability,
        CapabilityResult,
        Action,
        Bundle,
        ViewWatermark,
        View,
    ],
)
def test_leaf_values_are_frozen_slotted_dataclasses(value_type: type[object]) -> None:
    assert is_dataclass(value_type)
    assert value_type.__dataclass_params__.frozen is True  # type: ignore[attr-defined]
    assert "__dict__" not in {field.name for field in fields(value_type)}
