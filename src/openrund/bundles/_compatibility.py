"""Read inert authenticated schema-1 Bundle profile evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import final

from openrund.contracts.portable import BundleProfile
from openrund.errors import BundleError, ValidationError
from openrund.paths import PortablePath

from ._hashing import bundle_commitment, hash_bytes
from ._model import BundleFileCommitment, BundleManifest
from ._wire import manifest_from_bytes, parse_json_bytes, pretty_json_bytes


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class FrozenBundleProfile:
    profile: BundleProfile
    manifest: BundleManifest
    relative_tree: tuple[BundleFileCommitment, ...]
    event_head: str
    bundle_commitment: str


def _mapping(value: object, pointer: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise BundleError(code="bundle_profile_evidence_invalid", pointer=pointer)
    return value


def _text(value: object, pointer: str) -> str:
    if not isinstance(value, str) or value == "":
        raise BundleError(code="bundle_profile_evidence_invalid", pointer=pointer)
    return value


def _count(value: object, pointer: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BundleError(code="bundle_profile_evidence_invalid", pointer=pointer)
    return value


def read_frozen_bundle_profile(content: bytes) -> FrozenBundleProfile:
    root = _mapping(parse_json_bytes(content, code="bundle_profile_evidence_invalid"), "")
    required = {
        "profile",
        "relativeTree",
        "eventHead",
        "bundleCommitment",
        "manifest",
        "artifactCardinality",
    }
    if set(root) != required:
        raise BundleError(code="bundle_profile_evidence_invalid")
    try:
        profile = BundleProfile(_text(root["profile"], "/profile"))
        raw_manifest = _mapping(root["manifest"], "/manifest")
        rendered_manifest = pretty_json_bytes(raw_manifest)
        manifest = manifest_from_bytes(rendered_manifest)
        raw_tree = _mapping(root["relativeTree"], "/relativeTree")
        tree = tuple(
            BundleFileCommitment(
                path=PortablePath(value=path),
                sha256=_text(
                    _mapping(raw, f"/relativeTree/{path}").get("sha256"),
                    f"/relativeTree/{path}/sha256",
                ),
                byte_length=_count(
                    _mapping(raw, f"/relativeTree/{path}").get("bytes"),
                    f"/relativeTree/{path}/bytes",
                ),
            )
            for path, raw in raw_tree.items()
        )
    except BundleError:
        raise
    except (TypeError, ValueError, ValidationError):
        raise BundleError(code="bundle_profile_evidence_invalid") from None
    if profile is not manifest.profile:
        raise BundleError(code="bundle_profile_evidence_mismatch", pointer="/profile")
    event_head = _text(root["eventHead"], "/eventHead")
    recorded_bundle = _text(root["bundleCommitment"], "/bundleCommitment")
    if event_head != manifest.integrity.events.head:
        raise BundleError(code="bundle_profile_evidence_mismatch", pointer="/eventHead")
    if recorded_bundle != manifest.integrity.bundle.sha256:
        raise BundleError(code="bundle_profile_evidence_mismatch", pointer="/bundleCommitment")
    tree_map = {item.path.value: item for item in tree}
    manifest_tree = tree_map.get("manifest.json")
    if (
        manifest_tree is None
        or manifest_tree.byte_length != len(rendered_manifest)
        or manifest_tree.sha256 != hash_bytes(rendered_manifest)
    ):
        raise BundleError(
            code="bundle_profile_evidence_mismatch", pointer="/relativeTree/manifest.json"
        )
    expected_non_manifest = {item.path.value: item for item in manifest.integrity.files}
    actual_non_manifest = {path: item for path, item in tree_map.items() if path != "manifest.json"}
    if actual_non_manifest != expected_non_manifest:
        raise BundleError(code="bundle_profile_evidence_mismatch", pointer="/relativeTree")
    recomputed = bundle_commitment(
        profile=manifest.profile,
        source_run_id=manifest.source_run_id,
        compatibility=manifest.compatibility,
        events=manifest.integrity.events,
        files=manifest.integrity.files,
    )
    if recomputed != manifest.integrity.bundle:
        raise BundleError(code="bundle_profile_evidence_mismatch", pointer="/bundleCommitment")
    return FrozenBundleProfile(
        profile=profile,
        manifest=manifest,
        relative_tree=tree,
        event_head=event_head,
        bundle_commitment=recorded_bundle,
    )
