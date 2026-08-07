from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from openrund.bundles import (
    BundleCompatibility,
    BundleEventCommitment,
    BundleFileCommitment,
    bundle_commitment,
    event_frame_commitment,
    hash_bytes,
    hash_canonical_json,
    render_event_frames_jsonl,
)
from openrund.contracts.ids import RunId
from openrund.contracts.json import JsonObject, freeze_json
from openrund.contracts.portable import BundleProfile
from openrund.paths import PortablePath

FIXTURES = Path(__file__).parents[1] / "fixtures" / "compatibility" / "v1" / "evidence"


def _record(profile: str) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((FIXTURES / f"bundle-{profile}.jsonl").read_text(encoding="utf-8")),
    )


def _fixed_events() -> tuple[JsonObject, ...]:
    run_id = "run_oracle_bundle_profiles"
    timestamp = "2026-01-02T03:04:05.678Z"
    raw = (
        {
            "id": f"evt_{run_id}_created",
            "runID": run_id,
            "position": 1,
            "type": "run.created",
            "version": 1,
            "timestamp": timestamp,
            "actor": "system",
            "payload": {
                "rootID": run_id,
                "title": "Fixed portable Run",
                "objective": "Prove deterministic Bundle profiles",
            },
        },
        {
            "id": f"evt_{run_id}_started",
            "runID": run_id,
            "position": 2,
            "type": "run.started",
            "version": 1,
            "timestamp": timestamp,
            "actor": "system",
            "causationID": f"evt_{run_id}_created",
            "payload": {"reason": "fixed Bundle oracle"},
        },
        {
            "id": f"evt_{run_id}_artifact",
            "runID": run_id,
            "position": 3,
            "type": "artifact.created",
            "version": 1,
            "timestamp": timestamp,
            "actor": "system",
            "causationID": f"evt_{run_id}_started",
            "payload": {
                "artifactID": "art_oracle_bundle",
                "kind": "portable-test",
                "metadata": {"fixture": "synthetic"},
                "contentPreview": "fixed portable artifact",
            },
        },
    )
    result = tuple(freeze_json(item) for item in raw)
    assert all(isinstance(item, JsonObject) for item in result)
    return cast(tuple[JsonObject, ...], result)


def test_hash_canonical_json_uses_approved_utf16_key_order() -> None:
    value = freeze_json({"\ue000": 1, "\U00010000": 2, "a": -0.0})
    assert hash_canonical_json(value) == hash_bytes('{"a":0,"𐀀":2,"":1}'.encode())


def test_event_jsonl_and_chain_match_frozen_complete_profile() -> None:
    events = _fixed_events()
    record = _record("complete")
    expected_tree = record["relativeTree"]
    assert isinstance(expected_tree, dict)
    expected_file = expected_tree["events.jsonl"]
    assert isinstance(expected_file, dict)
    rendered = render_event_frames_jsonl(events)
    assert len(rendered) == expected_file["bytes"]
    assert hash_bytes(rendered) == expected_file["sha256"]
    commitment = event_frame_commitment(events)
    assert commitment.head == record["eventHead"]
    assert commitment.count == 3


def test_bundle_commitments_match_all_frozen_profiles() -> None:
    for profile in BundleProfile:
        record = _record(profile.value)
        raw_manifest = record["manifest"]
        assert isinstance(raw_manifest, dict)
        raw_integrity = raw_manifest["integrity"]
        assert isinstance(raw_integrity, dict)
        raw_files = raw_integrity["files"]
        assert isinstance(raw_files, dict)
        files = tuple(
            BundleFileCommitment(
                path=PortablePath(value=path),
                sha256=value["sha256"],
                byte_length=value["bytes"],
            )
            for path, value in raw_files.items()
            if isinstance(value, dict)
        )
        raw_events = raw_integrity["events"]
        assert isinstance(raw_events, dict)
        commitment = bundle_commitment(
            profile=profile,
            source_run_id=RunId(value="run_oracle_bundle_profiles"),
            compatibility=BundleCompatibility(
                runtime_version="0.0.0-oracle",
                runtime_range="^0.0.0",
            ),
            events=BundleEventCommitment(
                count=raw_events["count"],
                head=raw_events["head"],
            ),
            files=files,
        )
        assert commitment.sha256 == record["bundleCommitment"]
