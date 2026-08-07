"""Exact schema-1 Bundle hashing and Event JSONL rendering."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from openrund.codec import (
    canonical_json_bytes,
    decode_json_value,
    encode_event,
    encode_json_value,
)
from openrund.contracts.events import RuntimeEvent
from openrund.contracts.ids import RunId
from openrund.contracts.json import JsonArray, JsonObject, JsonValue, freeze_json
from openrund.contracts.portable import BundleProfile
from openrund.errors import ValidationError

from ._model import (
    BundleCommitment,
    BundleCompatibility,
    BundleEventCommitment,
    BundleFileCommitment,
)


def hash_bytes(value: bytes) -> str:
    if not isinstance(value, bytes):
        raise ValidationError(code="bundle_hash_input_invalid")
    return hashlib.sha256(value).hexdigest()


def hash_canonical_json(value: JsonValue | object) -> str:
    return hash_bytes(canonical_json_bytes(freeze_json(value)))


def render_events_jsonl(events: Iterable[RuntimeEvent]) -> bytes:
    materialized = tuple(events)
    return b"".join(encode_event(event) for event in materialized)


def render_event_frames_jsonl(events: Iterable[JsonObject]) -> bytes:
    materialized = tuple(events)
    if any(not isinstance(event, JsonObject) for event in materialized):
        raise ValidationError(code="bundle_event_frame_invalid")
    return b"".join(encode_json_value(event) for event in materialized)


def event_commitment(events: Iterable[RuntimeEvent]) -> BundleEventCommitment:
    materialized = tuple(events)
    head = hash_bytes(b"")
    for event in materialized:
        encoded = decode_json_value(encode_event(event))
        if not isinstance(encoded, JsonObject):
            raise ValidationError(code="bundle_event_encoding_invalid")
        head = hash_canonical_json(JsonObject(entries=(("previous", head), ("event", encoded))))
    return BundleEventCommitment(count=len(materialized), head=head)


def event_frame_commitment(events: Iterable[JsonObject]) -> BundleEventCommitment:
    """Hash raw authenticated frames before compatibility normalization."""

    materialized = tuple(events)
    head = hash_bytes(b"")
    for event in materialized:
        if not isinstance(event, JsonObject):
            raise ValidationError(code="bundle_event_frame_invalid")
        head = hash_canonical_json(JsonObject(entries=(("previous", head), ("event", event))))
    return BundleEventCommitment(count=len(materialized), head=head)


def _compatibility_json(value: BundleCompatibility) -> JsonObject:
    return JsonObject(
        entries=(
            ("bundleSchema", value.bundle_schema),
            (
                "runtime",
                JsonObject(
                    entries=(
                        ("name", "openrund"),
                        ("version", value.runtime_version),
                        ("range", value.runtime_range),
                    )
                ),
            ),
            ("eventGrammar", value.event_grammar),
            ("viewSchema", value.view_schema),
            ("policyManifest", value.policy_manifest),
            ("capabilityManifest", value.capability_manifest),
        )
    )


def bundle_commitment(
    *,
    profile: BundleProfile,
    source_run_id: RunId,
    compatibility: BundleCompatibility,
    events: BundleEventCommitment,
    files: tuple[BundleFileCommitment, ...],
) -> BundleCommitment:
    if not isinstance(profile, BundleProfile) or not isinstance(source_run_id, RunId):
        raise ValidationError(code="bundle_commitment_input_invalid")
    file_entries: list[tuple[str, JsonValue]] = []
    for item in files:
        if not isinstance(item, BundleFileCommitment):
            raise ValidationError(code="bundle_commitment_files_invalid")
        file_entries.append(
            (
                item.path.value,
                JsonObject(entries=(("sha256", item.sha256), ("bytes", item.byte_length))),
            )
        )
    value = JsonObject(
        entries=(
            ("profile", profile.value),
            ("source", JsonObject(entries=(("runID", source_run_id.value),))),
            ("compatibility", _compatibility_json(compatibility)),
            (
                "integrity",
                JsonObject(
                    entries=(
                        (
                            "events",
                            JsonObject(
                                entries=(
                                    ("algorithm", events.algorithm),
                                    ("count", events.count),
                                    ("head", events.head),
                                )
                            ),
                        ),
                        ("files", JsonObject(entries=tuple(file_entries))),
                    )
                ),
            ),
        )
    )
    return BundleCommitment(sha256=hash_canonical_json(value))


def canonical_profile_record(
    profile: BundleProfile,
    files: tuple[BundleFileCommitment, ...],
) -> JsonArray:
    """Small public hash-vector shape used by compatibility tests."""

    return JsonArray(
        values=(
            profile.value,
            JsonArray(
                values=tuple(
                    JsonObject(
                        entries=(
                            ("path", item.path.value),
                            ("sha256", item.sha256),
                            ("bytes", item.byte_length),
                        )
                    )
                    for item in files
                )
            ),
        )
    )
