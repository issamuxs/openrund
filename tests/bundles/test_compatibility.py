from __future__ import annotations

from collections.abc import Mapping

from openrund.bundles import (
    BundleArtifactAvailability,
    FrozenBundleProfile,
    read_frozen_bundle_profile,
)
from openrund.contracts.portable import BundleProfile
from tests.conftest import CorpusEntry, read_corpus_entry


def _bundle_entries(phase28_manifest: Mapping[str, object]) -> tuple[CorpusEntry, ...]:
    raw = phase28_manifest["bundles"]
    assert isinstance(raw, tuple)
    result: list[CorpusEntry] = []
    for value in raw:
        assert isinstance(value, Mapping)
        key = value["key"]
        assert isinstance(key, str)
        if key not in {"bundle:complete", "bundle:audit", "bundle:redacted"}:
            continue
        relative_path = value["relativePath"]
        byte_length = value["byteLength"]
        sha256 = value["sha256"]
        assert isinstance(relative_path, str)
        assert isinstance(byte_length, int)
        assert isinstance(sha256, str)
        result.append(
            CorpusEntry(
                category="bundle",
                key=key,
                relative_path=relative_path,
                byte_length=byte_length,
                sha256=sha256,
                decoded_meaning=value.get("decodedMeaning"),
                required_pointers=(),
                absent_pointers=(),
                null_pointers=(),
                manifest_entry=value,
            )
        )
    return tuple(result)


def test_all_authenticated_frozen_profiles_cross_read(
    phase28_manifest: Mapping[str, object],
) -> None:
    entries = _bundle_entries(phase28_manifest)
    assert {item.key for item in entries} == {
        "bundle:complete",
        "bundle:audit",
        "bundle:redacted",
    }
    profiles: dict[BundleProfile, FrozenBundleProfile] = {}
    for entry in entries:
        decoded = read_frozen_bundle_profile(read_corpus_entry(entry))
        profiles[decoded.profile] = decoded
        assert decoded.manifest.run_id.value == "run_oracle_bundle_profiles"
        assert decoded.manifest.integrity.events.count == 3
        assert (
            decoded.event_head == "279bf6bbecc0c290cc5a9646df8fc2c4d6c32674b16b48778ae3ed28304db75f"
        )

    complete = profiles[BundleProfile.COMPLETE]
    assert complete.manifest.artifacts[0].availability is BundleArtifactAvailability.INCLUDED
    assert complete.manifest.completeness.status.value == "complete"
    for profile_kind in (BundleProfile.AUDIT, BundleProfile.REDACTED):
        frozen = profiles[profile_kind]
        assert frozen.manifest.artifacts[0].availability is BundleArtifactAvailability.OMITTED
        assert frozen.manifest.completeness.status.value == "partial"


def test_frozen_commitments_are_recomputed_not_trusted(
    phase28_manifest: Mapping[str, object],
) -> None:
    entry = next(
        item for item in _bundle_entries(phase28_manifest) if item.key == "bundle:complete"
    )
    content = read_corpus_entry(entry)
    tampered = content.replace(b'"bundleCommitment":"26a79d', b'"bundleCommitment":"06a79d', 1)
    import pytest

    from openrund.errors import BundleError

    with pytest.raises(BundleError, match="bundle_profile_evidence_mismatch"):
        read_frozen_bundle_profile(tampered)
