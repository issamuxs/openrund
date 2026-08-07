"""Canonical timestamps used by OpenRund semantic contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final, final

from openrund.errors import ValidationError

_TIMESTAMP_PATTERN: Final = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$"
)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Timestamp:
    """Exact UTC RFC 3339 timestamp with millisecond precision."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise ValidationError(code="timestamp_type_invalid")
        if _TIMESTAMP_PATTERN.fullmatch(self.value) is None:
            raise ValidationError(code="timestamp_format_invalid")
        try:
            datetime.strptime(self.value, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError as error:
            raise ValidationError(code="timestamp_value_invalid") from error

    def __str__(self) -> str:
        return self.value
