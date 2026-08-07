from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
from typing import get_args, get_type_hints

import pytest

from openrund.contracts.ids import (
    ActionId,
    AnnotationId,
    ArtifactId,
    AuthorityId,
    CapabilityId,
    CheckId,
    CheckpointId,
    CommandId,
    CorrelationId,
    DelegationId,
    EventId,
    LeaseId,
    MessageId,
    ModelCallId,
    PolicyRuleId,
    RunId,
    RuntimeId,
    WaitId,
)

ID_TYPES = (
    RunId,
    EventId,
    CommandId,
    ModelCallId,
    WaitId,
    DelegationId,
    CheckId,
    CheckpointId,
    MessageId,
    AnnotationId,
    AuthorityId,
    ActionId,
    ArtifactId,
    LeaseId,
    CapabilityId,
    PolicyRuleId,
    CorrelationId,
)
type IdClass = (
    type[RunId]
    | type[EventId]
    | type[CommandId]
    | type[ModelCallId]
    | type[WaitId]
    | type[DelegationId]
    | type[CheckId]
    | type[CheckpointId]
    | type[MessageId]
    | type[AnnotationId]
    | type[AuthorityId]
    | type[ActionId]
    | type[ArtifactId]
    | type[LeaseId]
    | type[CapabilityId]
    | type[PolicyRuleId]
    | type[CorrelationId]
)


@pytest.mark.parametrize("id_type", ID_TYPES)
def test_id_kinds_preserve_non_empty_strings_exactly(id_type: IdClass) -> None:
    value = "  id-e\N{COMBINING ACUTE ACCENT}-\N{GRINNING FACE}  "

    identifier = id_type(value=value)

    assert identifier.value == value
    assert is_dataclass(identifier)
    assert [field.name for field in fields(identifier)] == ["value"]
    assert not hasattr(identifier, "__dict__")
    with pytest.raises(FrozenInstanceError):
        identifier.value = "changed"  # type: ignore[misc]


@pytest.mark.parametrize("id_type", ID_TYPES)
@pytest.mark.parametrize("invalid", ["", None, True, False, b"id", 1, 1.0])
def test_id_kinds_reject_empty_and_wrong_runtime_kinds(id_type: IdClass, invalid: object) -> None:
    with pytest.raises(TypeError if invalid != "" else ValueError):
        id_type(value=invalid)  # type: ignore[arg-type]


def test_id_kinds_compare_and_hash_only_with_the_same_kind() -> None:
    first = RunId(value="shared")
    same = RunId(value="shared")
    other_kind = EventId(value="shared")

    assert first == same
    assert hash(first) == hash(same)
    assert first != other_kind  # type: ignore[comparison-overlap]
    assert len({first, same, other_kind}) == 2


@pytest.mark.parametrize("id_type", ID_TYPES)
def test_id_kinds_reject_cross_kind_construction(id_type: IdClass) -> None:
    other_kind = EventId(value="event") if id_type is not EventId else RunId(value="run")

    with pytest.raises(TypeError):
        id_type(value=other_kind)  # type: ignore[arg-type]


def test_runtime_id_is_the_closed_union_of_all_identifier_kinds() -> None:
    assert get_args(RuntimeId.__value__) == ID_TYPES


@pytest.mark.parametrize("id_type", ID_TYPES)
def test_id_public_value_annotation_is_complete(id_type: IdClass) -> None:
    assert get_type_hints(id_type) == {"value": str}
