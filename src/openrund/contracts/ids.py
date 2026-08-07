"""Runtime-distinct identifiers used by OpenRund semantic contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import final


def _validate_id_value(value: object) -> None:
    if not isinstance(value, str):
        raise TypeError("id_value_type_invalid")
    if value == "":
        raise ValueError("id_value_empty")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class EventId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CommandId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ModelCallId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class WaitId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CheckId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class MessageId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AnnotationId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AuthorityId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class LeaseId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyRuleId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CorrelationId:
    value: str

    def __post_init__(self) -> None:
        _validate_id_value(self.value)


type RuntimeId = (
    RunId
    | EventId
    | CommandId
    | ModelCallId
    | WaitId
    | DelegationId
    | CheckId
    | CheckpointId
    | MessageId
    | AnnotationId
    | AuthorityId
    | ActionId
    | ArtifactId
    | LeaseId
    | CapabilityId
    | PolicyRuleId
    | CorrelationId
)
