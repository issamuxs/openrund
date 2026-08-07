"""Deeply immutable values for JSON-shaped semantic data."""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Self, final, overload

from openrund.errors import ValidationError

type JsonScalar = bool | int | float | str | None


@final
class MissingType:
    """Identity-only marker for an omitted field.

    ``None`` is a present JSON null. ``MISSING`` is absence.
    """

    __slots__ = ()
    _instance: ClassVar[MissingType | None] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "MISSING"

    def __reduce__(self) -> tuple[type[MissingType], tuple[()]]:
        return (MissingType, ())


MISSING = MissingType()


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class JsonArray(Sequence["JsonValue"]):
    """Immutable ordered JSON array."""

    values: tuple[JsonValue, ...]

    def __post_init__(self) -> None:
        try:
            raw_values = tuple(self.values)
        except TypeError as error:
            raise ValidationError(code="json_array_type_invalid") from error
        object.__setattr__(self, "values", tuple(freeze_json(value) for value in raw_values))

    @overload
    def __getitem__(self, index: int) -> JsonValue: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[JsonValue, ...]: ...

    def __getitem__(self, index: int | slice) -> JsonValue | tuple[JsonValue, ...]:
        return self.values[index]

    def __len__(self) -> int:
        return len(self.values)

    def __iter__(self) -> Iterator[JsonValue]:
        return iter(self.values)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class JsonObject(Mapping[str, "JsonValue"]):
    """Immutable JSON object that retains construction order."""

    entries: tuple[tuple[str, JsonValue], ...]

    def __post_init__(self) -> None:
        try:
            raw_entries = tuple(self.entries)
        except TypeError as error:
            raise ValidationError(code="json_object_type_invalid") from error

        seen: set[str] = set()
        frozen_entries: list[tuple[str, JsonValue]] = []
        for entry in raw_entries:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValidationError(code="json_object_entry_invalid")
            key, value = entry
            if not isinstance(key, str):
                raise ValidationError(code="json_object_key_type_invalid")
            if key in seen:
                raise ValidationError(code="json_object_key_duplicate")
            seen.add(key)
            frozen_entries.append((key, freeze_json(value)))
        object.__setattr__(self, "entries", tuple(frozen_entries))

    def __getitem__(self, key: str) -> JsonValue:
        for candidate, value in self.entries:
            if candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _ in self.entries)

    def __len__(self) -> int:
        return len(self.entries)


type JsonValue = JsonScalar | JsonArray | JsonObject


def freeze_json(value: object) -> JsonValue:
    """Validate and recursively freeze a Python JSON-shaped value."""

    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError(code="json_number_non_finite")
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, (JsonArray, JsonObject)):
        return value
    if isinstance(value, Mapping):
        entries: list[tuple[str, JsonValue]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError(code="json_object_key_type_invalid")
            entries.append((key, freeze_json(item)))
        return JsonObject(entries=tuple(entries))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray, memoryview)):
        return JsonArray(values=tuple(freeze_json(item) for item in value))
    raise ValidationError(code="json_value_type_invalid")
