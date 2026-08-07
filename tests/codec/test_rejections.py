from __future__ import annotations

import pytest

from openrund.codec import decode_command_decision, decode_event
from openrund.errors import DecodeError, UnsupportedVersionError

_BASE = (
    b'{"id":"e1","runID":"r1","position":1,"type":"run.started","version":1,'
    b'"timestamp":"2026-01-02T03:04:05.678Z","actor":"system","payload":{}}\n'
)


@pytest.mark.parametrize("version", [0, 2])
def test_unsupported_event_versions_are_classified(version: int) -> None:
    wire = _BASE.replace(b'"version":1', f'"version":{version}'.encode())

    with pytest.raises(UnsupportedVersionError) as raised:
        decode_event(wire)

    assert raised.value.version == version
    assert raised.value.pointer == "/version"


@pytest.mark.parametrize(
    ("wire", "code", "pointer"),
    [
        (
            b'{"runID":"r1","position":1,"type":"run.started","version":1,'
            b'"timestamp":"2026-01-02T03:04:05.678Z","actor":"system","payload":{}}\n',
            "event_envelope_field_missing",
            "/id",
        ),
        (
            _BASE[:-2] + b',"future":true}\n',
            "event_envelope_field_unknown",
            "/future",
        ),
        (
            _BASE.replace(b'"payload":{}', b'"payload":{"future":true}'),
            "payload_field_unknown",
            "/payload/future",
        ),
        (
            _BASE.replace(b'"position":1', b'"position":true'),
            "field_integer_required",
            "/position",
        ),
        (
            _BASE.replace(b'"type":"run.started"', b'"type":"run.future"'),
            "event_type_unknown",
            "/type",
        ),
        (
            _BASE.replace(b'"payload":{}', b'"payload":{"reason":null,"kind":"approval"}'),
            "payload_field_unknown",
            "/payload/kind",
        ),
    ],
)
def test_event_shapes_fail_closed(wire: bytes, code: str, pointer: str) -> None:
    with pytest.raises(DecodeError) as raised:
        decode_event(wire)

    assert raised.value.code == code
    assert raised.value.pointer == pointer


def test_null_is_not_accepted_for_absent_only_envelope_links() -> None:
    wire = _BASE[:-2] + b',"causationID":null}\n'

    with pytest.raises(DecodeError) as raised:
        decode_event(wire)

    assert raised.value.code == "field_string_required"
    assert raised.value.pointer == "/causationID"


@pytest.mark.parametrize(
    ("replacement", "pointer"),
    [
        (b'"decision":"future"', "/decision"),
        (b'"decision":"accepted","future":true', "/future"),
    ],
)
def test_decision_discriminators_and_unknown_fields_reject(
    replacement: bytes, pointer: str
) -> None:
    base = (
        b'{"commandID":"c1","decision":"accepted","decisionTrace":[],'
        b'"resultEventIDs":["e1"],"targetEvent":{"status":"present","eventID":"e1"}}\n'
    )
    if b"future" in replacement and replacement.startswith(b'"decision":"accepted"'):
        wire = base.replace(b'"decision":"accepted"', replacement)
    else:
        wire = base.replace(b'"decision":"accepted"', replacement)

    with pytest.raises(DecodeError) as raised:
        decode_command_decision(wire)

    expected_code = "command_decision_unknown" if pointer == "/decision" else "field_unknown"
    assert raised.value.code == expected_code
    assert raised.value.pointer == pointer


def test_hostile_values_never_appear_in_domain_decode_errors() -> None:
    secret = "Bearer secret-value"
    wire = (
        '{"id":"e1","runID":"r1","position":1,"type":"run.created","version":1,'
        '"timestamp":"2026-01-02T03:04:05.678Z","actor":"system",'
        f'"payload":{{"rootID":"r1","initialStatus":"{secret}"}}}}\n'
    )

    with pytest.raises(DecodeError) as raised:
        decode_event(wire)

    assert secret not in str(raised.value)
