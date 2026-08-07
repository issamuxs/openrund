"""Injectable local operator input and reporting seams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, final

from openrund.contracts.json import MISSING, JsonObject, MissingType, freeze_json
from openrund.errors import ValidationError
from openrund.ports.runtime import ReportEntry, Reporter


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OperatorInputRequest:
    kind: str
    prompt: str
    choices: tuple[str, ...] = ()
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or self.kind == "":
            raise ValidationError(code="operator_input_kind_invalid")
        if not isinstance(self.prompt, str) or self.prompt == "":
            raise ValidationError(code="operator_input_prompt_invalid")
        choices = tuple(self.choices)
        if any(not isinstance(item, str) or item == "" for item in choices):
            raise ValidationError(code="operator_input_choices_invalid")
        metadata: JsonObject | MissingType | None = self.metadata
        if metadata not in (MISSING, None):
            candidate = freeze_json(metadata)
            if not isinstance(candidate, JsonObject):
                raise ValidationError(code="operator_input_metadata_invalid")
            metadata = candidate
        object.__setattr__(self, "choices", choices)
        object.__setattr__(self, "metadata", metadata)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OperatorInputResponse:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise ValidationError(code="operator_input_response_invalid")


class OperatorInput(Protocol):
    async def request(self, value: OperatorInputRequest, /) -> OperatorInputResponse: ...


@final
class RejectingOperatorInput:
    """Safe default: local assembly never prompts or approves implicitly."""

    __slots__ = ()

    async def request(self, value: OperatorInputRequest, /) -> OperatorInputResponse:
        if not isinstance(value, OperatorInputRequest):
            raise ValidationError(code="operator_input_request_invalid")
        raise ValidationError(code="operator_input_unavailable")


@final
class NullReporter:
    __slots__ = ()

    async def report(self, entry: ReportEntry, /) -> None:
        if not isinstance(entry, ReportEntry):
            raise ValidationError(code="report_entry_invalid")


DEFAULT_OPERATOR_INPUT: OperatorInput = RejectingOperatorInput()
DEFAULT_REPORTER: Reporter = NullReporter()
