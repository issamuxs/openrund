"""Narrow runtime dependency protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar, final

from openrund.contracts.ids import RuntimeId
from openrund.contracts.json import MISSING, JsonObject, MissingType, freeze_json
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError

TId_co = TypeVar("TId_co", bound=RuntimeId, covariant=True)


class Clock(Protocol):
    def now(self) -> Timestamp: ...


class IdFactory(Protocol[TId_co]):
    def new_id(self) -> TId_co: ...


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ReportEntry:
    timestamp: Timestamp
    category: str
    message: str
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, Timestamp):
            raise ValidationError(code="report_timestamp_invalid")
        if not isinstance(self.category, str) or self.category == "":
            raise ValidationError(code="report_category_invalid")
        if not isinstance(self.message, str) or self.message == "":
            raise ValidationError(code="report_message_invalid")
        if self.metadata in (MISSING, None):
            return
        metadata = freeze_json(self.metadata)
        if not isinstance(metadata, JsonObject):
            raise ValidationError(code="report_metadata_invalid")
        object.__setattr__(self, "metadata", metadata)


class Reporter(Protocol):
    async def report(self, entry: ReportEntry, /) -> None: ...
