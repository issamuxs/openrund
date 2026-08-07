from __future__ import annotations

import re

import pytest

from openrund.assembly import LocalIdFactories, SystemClock, UuidIdFactory
from openrund.contracts.ids import EventId
from openrund.errors import ValidationError


def test_system_clock_and_uuid_factories_emit_canonical_kind_safe_values() -> None:
    timestamp = SystemClock().now()
    event_id = UuidIdFactory(EventId, "evt").new_id()

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", timestamp.value)
    assert re.fullmatch(r"evt_[0-9a-f]{32}", event_id.value)
    assert isinstance(LocalIdFactories.production().event_ids.new_id(), EventId)


@pytest.mark.parametrize("prefix", ("", "bad prefix", "../event", "event!"))
def test_uuid_factory_rejects_ambiguous_prefixes(prefix: str) -> None:
    with pytest.raises(ValidationError, match="id_factory_prefix_invalid"):
        UuidIdFactory(EventId, prefix)
