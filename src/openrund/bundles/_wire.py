"""Bundle manifest wire rendering; parsing is completed by verification."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Final, cast

from openrund.contracts.ids import ArtifactId, RunId
from openrund.contracts.json import JsonArray, JsonObject, JsonValue
from openrund.contracts.portable import BundleProfile
from openrund.contracts.time import Timestamp
from openrund.errors import BundleError, ValidationError
from openrund.paths import PortablePath

from ._model import (
    BundleArtifact,
    BundleArtifactAvailability,
    BundleArtifactOmission,
    BundleCommitment,
    BundleCompatibility,
    BundleCompleteness,
    BundleCompletenessStatus,
    BundleEventCommitment,
    BundleExports,
    BundleFileCommitment,
    BundleIntegrity,
    BundleLayout,
    BundleManifest,
    BundlePolicy,
    BundleResumeRequirements,
    BundleViews,
)

MAX_MANIFEST_BYTES: Final = 8 * 1024 * 1024
_MAX_SAFE_INTEGER: Final = 9_007_199_254_740_991


def plain_json(value: JsonValue) -> object:
    if isinstance(value, JsonObject):
        return {key: plain_json(item) for key, item in value.entries}
    if isinstance(value, JsonArray):
        return [plain_json(item) for item in value.values]
    return value


def pretty_json_bytes(value: JsonValue | Mapping[str, object] | list[object]) -> bytes:
    source: object = plain_json(value) if isinstance(value, (JsonObject, JsonArray)) else value
    return (json.dumps(source, ensure_ascii=False, indent=2) + "\n").encode()


def compact_json_bytes(value: JsonValue) -> bytes:
    return (
        json.dumps(plain_json(value), ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode()


def _compatibility(value: BundleCompatibility) -> dict[str, object]:
    return {
        "bundleSchema": value.bundle_schema,
        "runtime": {
            "name": "openrund",
            "version": value.runtime_version,
            "range": value.runtime_range,
        },
        "eventGrammar": value.event_grammar,
        "viewSchema": value.view_schema,
        "policyManifest": value.policy_manifest,
        "capabilityManifest": value.capability_manifest,
    }


def _artifact(value: BundleArtifact) -> dict[str, object]:
    result: dict[str, object] = {
        "artifactID": value.artifact_id.value,
        "kind": value.kind,
        "availability": value.availability.value,
        "available": value.available,
        "requiredForResume": value.required_for_resume,
    }
    if value.content_type is not None:
        result["contentType"] = value.content_type
    if value.byte_length is not None:
        result["byteLength"] = value.byte_length
    if value.sha256 is not None:
        result["sha256"] = value.sha256
    if value.path is not None:
        result["path"] = value.path.value
    if value.availability is not BundleArtifactAvailability.INCLUDED:
        assert value.omission is not None
        assert value.omission_reason is not None
        result["omissionCategory"] = value.omission.value
        result["omissionReason"] = value.omission_reason
    return result


def manifest_mapping(value: BundleManifest) -> dict[str, object]:
    exports: dict[str, object] = {
        "runtimeAuditJsonPath": value.exports.runtime_audit_json.value,
        "runtimeAuditMarkdownPath": value.exports.runtime_audit_markdown.value,
        "actionReceiptPaths": [item.value for item in value.exports.action_receipts],
    }
    if value.exports.check_json is not None:
        exports["checkJsonPath"] = value.exports.check_json.value
    if value.exports.check_markdown is not None:
        exports["checkMarkdownPath"] = value.exports.check_markdown.value
    return {
        "version": value.version,
        "runID": value.run_id.value,
        "source": {"runID": value.source_run_id.value},
        "exportedAt": value.exported_at.value,
        "compatibility": _compatibility(value.compatibility),
        "profile": value.profile.value,
        "criticalFields": list(value.critical_fields),
        "layout": {
            "manifest": value.layout.manifest,
            "events": value.layout.events,
            "artifacts": value.layout.artifacts,
            "views": value.layout.views,
            "policy": value.layout.policy,
            "capabilities": value.layout.capabilities,
            "exports": value.layout.exports,
        },
        "completeness": {
            "status": value.completeness.status.value,
            "excludedArtifactIDs": [
                item.value for item in value.completeness.excluded_artifact_ids
            ],
        },
        "integrity": {
            "files": {
                item.path.value: {"sha256": item.sha256, "bytes": item.byte_length}
                for item in value.integrity.files
            },
            "events": {
                "algorithm": value.integrity.events.algorithm,
                "count": value.integrity.events.count,
                "head": value.integrity.events.head,
            },
            "bundle": {
                "algorithm": value.integrity.bundle.algorithm,
                "sha256": value.integrity.bundle.sha256,
            },
        },
        "views": {
            "status": value.views.status,
            "currentPosition": value.views.current_position,
            "pendingWaits": list(value.views.pending_waits),
            "eventCount": value.views.event_count,
        },
        "capabilities": {"grants": list(value.capability_grants)},
        "providers": {"required": list(value.provider_ids)},
        "policy": {"rules": list(value.policy.rules), "key": value.policy.key},
        "exports": exports,
        "artifacts": [_artifact(item) for item in value.artifacts],
        "resume": {
            "requiredRootMappings": list(value.resume.required_root_mappings),
            "requiredCapabilities": list(value.resume.required_capabilities),
            "requiredProviders": list(value.resume.required_providers),
            "pendingWaits": list(value.resume.pending_waits),
            "unavailableArtifacts": [item.value for item in value.resume.unavailable_artifacts],
        },
    }


def manifest_bytes(value: BundleManifest) -> bytes:
    return pretty_json_bytes(manifest_mapping(value))


def profile_from_wire(value: object) -> BundleProfile:
    return BundleProfile(cast(str, value))


def _object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def _integer(value: str) -> int:
    parsed = int(value)
    if abs(parsed) > _MAX_SAFE_INTEGER:
        raise ValueError("unsafe_integer")
    return parsed


def parse_json_bytes(content: bytes, *, code: str) -> object:
    if not isinstance(content, bytes) or not content or len(content) > MAX_MANIFEST_BYTES:
        raise BundleError(code=code)
    if content.startswith(b"\xef\xbb\xbf"):
        raise BundleError(code=code)
    try:
        text = content.decode("utf-8", errors="strict")
        return cast(
            object,
            json.loads(
                text,
                object_pairs_hook=_object_pairs,
                parse_int=_integer,
                parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("non_finite")),
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
        raise BundleError(code=code) from None


def _mapping(value: object, pointer: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise BundleError(code="bundle_manifest_malformed", pointer=pointer)
    return cast(dict[str, object], value)


def _array(value: object, pointer: str) -> list[object]:
    if not isinstance(value, list):
        raise BundleError(code="bundle_manifest_malformed", pointer=pointer)
    return value


def _required(value: dict[str, object], key: str, pointer: str = "") -> object:
    if key not in value:
        raise BundleError(code="bundle_manifest_field_missing", pointer=f"{pointer}/{key}")
    return value[key]


def _text(value: object, pointer: str) -> str:
    if not isinstance(value, str) or value == "":
        raise BundleError(code="bundle_manifest_malformed", pointer=pointer)
    return value


def _boolean(value: object, pointer: str) -> bool:
    if not isinstance(value, bool):
        raise BundleError(code="bundle_manifest_malformed", pointer=pointer)
    return value


def _count(value: object, pointer: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BundleError(code="bundle_manifest_malformed", pointer=pointer)
    return value


def _texts(value: object, pointer: str) -> tuple[str, ...]:
    return tuple(
        _text(item, f"{pointer}/{index}") for index, item in enumerate(_array(value, pointer))
    )


def _artifact_ids(value: object, pointer: str) -> tuple[ArtifactId, ...]:
    return tuple(ArtifactId(value=item) for item in _texts(value, pointer))


def _optional_text(value: dict[str, object], key: str, pointer: str) -> str | None:
    return None if key not in value else _text(value[key], f"{pointer}/{key}")


def _optional_count(value: dict[str, object], key: str, pointer: str) -> int | None:
    return None if key not in value else _count(value[key], f"{pointer}/{key}")


def _portable(value: object, pointer: str) -> PortablePath:
    try:
        return PortablePath(value=_text(value, pointer))
    except ValidationError:
        raise BundleError(code="bundle_path_invalid", pointer=pointer) from None


def _compatibility_from(value: object) -> BundleCompatibility:
    data = _mapping(value, "/compatibility")
    runtime = _mapping(_required(data, "runtime", "/compatibility"), "/compatibility/runtime")
    if (
        _text(_required(runtime, "name", "/compatibility/runtime"), "/compatibility/runtime/name")
        != "openrund"
    ):
        raise BundleError(
            code="bundle_compatibility_unsupported", pointer="/compatibility/runtime/name"
        )
    return BundleCompatibility(
        bundle_schema=_count(
            _required(data, "bundleSchema", "/compatibility"), "/compatibility/bundleSchema"
        ),
        runtime_version=_text(
            _required(runtime, "version", "/compatibility/runtime"),
            "/compatibility/runtime/version",
        ),
        runtime_range=_text(
            _required(runtime, "range", "/compatibility/runtime"), "/compatibility/runtime/range"
        ),
        event_grammar=_count(
            _required(data, "eventGrammar", "/compatibility"), "/compatibility/eventGrammar"
        ),
        view_schema=_count(
            _required(data, "viewSchema", "/compatibility"), "/compatibility/viewSchema"
        ),
        policy_manifest=_count(
            _required(data, "policyManifest", "/compatibility"), "/compatibility/policyManifest"
        ),
        capability_manifest=_count(
            _required(data, "capabilityManifest", "/compatibility"),
            "/compatibility/capabilityManifest",
        ),
    )


def _integrity_from(value: object) -> BundleIntegrity:
    data = _mapping(value, "/integrity")
    raw_files = _mapping(_required(data, "files", "/integrity"), "/integrity/files")
    files = tuple(
        BundleFileCommitment(
            path=_portable(path, f"/integrity/files/{path}"),
            sha256=_text(
                _required(
                    _mapping(raw, f"/integrity/files/{path}"), "sha256", f"/integrity/files/{path}"
                ),
                f"/integrity/files/{path}/sha256",
            ),
            byte_length=_count(
                _required(
                    _mapping(raw, f"/integrity/files/{path}"), "bytes", f"/integrity/files/{path}"
                ),
                f"/integrity/files/{path}/bytes",
            ),
        )
        for path, raw in raw_files.items()
    )
    raw_events = _mapping(_required(data, "events", "/integrity"), "/integrity/events")
    raw_bundle = _mapping(_required(data, "bundle", "/integrity"), "/integrity/bundle")
    return BundleIntegrity(
        files=files,
        events=BundleEventCommitment(
            algorithm=_text(
                _required(raw_events, "algorithm", "/integrity/events"),
                "/integrity/events/algorithm",
            ),
            count=_count(
                _required(raw_events, "count", "/integrity/events"), "/integrity/events/count"
            ),
            head=_text(
                _required(raw_events, "head", "/integrity/events"), "/integrity/events/head"
            ),
        ),
        bundle=BundleCommitment(
            algorithm=_text(
                _required(raw_bundle, "algorithm", "/integrity/bundle"),
                "/integrity/bundle/algorithm",
            ),
            sha256=_text(
                _required(raw_bundle, "sha256", "/integrity/bundle"), "/integrity/bundle/sha256"
            ),
        ),
    )


def _artifact_from(value: object, index: int) -> BundleArtifact:
    pointer = f"/artifacts/{index}"
    data = _mapping(value, pointer)
    try:
        availability = BundleArtifactAvailability(
            _text(_required(data, "availability", pointer), f"{pointer}/availability")
        )
        omission = (
            None
            if "omissionCategory" not in data
            else BundleArtifactOmission(
                _text(data["omissionCategory"], f"{pointer}/omissionCategory")
            )
        )
    except ValueError:
        raise BundleError(code="bundle_artifact_manifest_invalid", pointer=pointer) from None
    return BundleArtifact(
        artifact_id=ArtifactId(
            value=_text(_required(data, "artifactID", pointer), f"{pointer}/artifactID")
        ),
        kind=_text(_required(data, "kind", pointer), f"{pointer}/kind"),
        availability=availability,
        available=_boolean(_required(data, "available", pointer), f"{pointer}/available"),
        required_for_resume=_boolean(
            _required(data, "requiredForResume", pointer), f"{pointer}/requiredForResume"
        ),
        content_type=_optional_text(data, "contentType", pointer),
        byte_length=_optional_count(data, "byteLength", pointer),
        sha256=_optional_text(data, "sha256", pointer),
        path=None if "path" not in data else _portable(data["path"], f"{pointer}/path"),
        omission=omission,
        omission_reason=_optional_text(data, "omissionReason", pointer),
    )


def manifest_from_bytes(content: bytes) -> BundleManifest:
    root = _mapping(parse_json_bytes(content, code="bundle_manifest_malformed"), "")
    required = {
        "version",
        "runID",
        "source",
        "exportedAt",
        "compatibility",
        "profile",
        "criticalFields",
        "layout",
        "completeness",
        "integrity",
        "views",
        "capabilities",
        "policy",
        "exports",
        "artifacts",
        "resume",
    }
    allowed = required | {"providers"}
    if missing := required - set(root):
        key = sorted(missing)[0]
        raise BundleError(code="bundle_manifest_field_missing", pointer=f"/{key}")
    if unknown := set(root) - allowed:
        key = sorted(unknown)[0]
        raise BundleError(code="bundle_manifest_field_unknown", pointer=f"/{key}")
    source = _mapping(root["source"], "/source")
    layout = _mapping(root["layout"], "/layout")
    completeness = _mapping(root["completeness"], "/completeness")
    views = _mapping(root["views"], "/views")
    capabilities = _mapping(root["capabilities"], "/capabilities")
    policy = _mapping(root["policy"], "/policy")
    exports = _mapping(root["exports"], "/exports")
    resume = _mapping(root["resume"], "/resume")
    provider_ids = _texts(
        _required(resume, "requiredProviders", "/resume"), "/resume/requiredProviders"
    )
    if "providers" in root:
        providers = _mapping(root["providers"], "/providers")
        if (
            _texts(_required(providers, "required", "/providers"), "/providers/required")
            != provider_ids
        ):
            raise BundleError(code="bundle_provider_requirements_mismatch", pointer="/providers")
    try:
        profile = BundleProfile(_text(root["profile"], "/profile"))
        status = BundleCompletenessStatus(
            _text(_required(completeness, "status", "/completeness"), "/completeness/status")
        )
        manifest = BundleManifest(
            version=_count(root["version"], "/version"),
            run_id=RunId(value=_text(root["runID"], "/runID")),
            source_run_id=RunId(
                value=_text(_required(source, "runID", "/source"), "/source/runID")
            ),
            exported_at=Timestamp(value=_text(root["exportedAt"], "/exportedAt")),
            compatibility=_compatibility_from(root["compatibility"]),
            profile=profile,
            critical_fields=_texts(root["criticalFields"], "/criticalFields"),
            layout=BundleLayout(
                manifest=_text(_required(layout, "manifest", "/layout"), "/layout/manifest"),
                events=_text(_required(layout, "events", "/layout"), "/layout/events"),
                artifacts=_text(_required(layout, "artifacts", "/layout"), "/layout/artifacts"),
                views=_text(_required(layout, "views", "/layout"), "/layout/views"),
                policy=_text(_required(layout, "policy", "/layout"), "/layout/policy"),
                capabilities=_text(
                    _required(layout, "capabilities", "/layout"), "/layout/capabilities"
                ),
                exports=_text(_required(layout, "exports", "/layout"), "/layout/exports"),
            ),
            completeness=BundleCompleteness(
                status=status,
                excluded_artifact_ids=_artifact_ids(
                    _required(completeness, "excludedArtifactIDs", "/completeness"),
                    "/completeness/excludedArtifactIDs",
                ),
            ),
            integrity=_integrity_from(root["integrity"]),
            views=BundleViews(
                status=_text(_required(views, "status", "/views"), "/views/status"),
                current_position=_count(
                    _required(views, "currentPosition", "/views"), "/views/currentPosition"
                ),
                pending_waits=_texts(
                    _required(views, "pendingWaits", "/views"), "/views/pendingWaits"
                ),
                event_count=_count(_required(views, "eventCount", "/views"), "/views/eventCount"),
            ),
            capability_grants=_texts(
                _required(capabilities, "grants", "/capabilities"), "/capabilities/grants"
            ),
            provider_ids=provider_ids,
            policy=BundlePolicy(
                rules=_texts(_required(policy, "rules", "/policy"), "/policy/rules"),
                key=_text(_required(policy, "key", "/policy"), "/policy/key"),
            ),
            exports=BundleExports(
                runtime_audit_json=_portable(
                    _required(exports, "runtimeAuditJsonPath", "/exports"),
                    "/exports/runtimeAuditJsonPath",
                ),
                runtime_audit_markdown=_portable(
                    _required(exports, "runtimeAuditMarkdownPath", "/exports"),
                    "/exports/runtimeAuditMarkdownPath",
                ),
                action_receipts=tuple(
                    _portable(item, f"/exports/actionReceiptPaths/{index}")
                    for index, item in enumerate(
                        _array(exports.get("actionReceiptPaths", []), "/exports/actionReceiptPaths")
                    )
                ),
                check_json=None
                if "checkJsonPath" not in exports
                else _portable(exports["checkJsonPath"], "/exports/checkJsonPath"),
                check_markdown=None
                if "checkMarkdownPath" not in exports
                else _portable(exports["checkMarkdownPath"], "/exports/checkMarkdownPath"),
            ),
            artifacts=tuple(
                _artifact_from(item, index)
                for index, item in enumerate(_array(root["artifacts"], "/artifacts"))
            ),
            resume=BundleResumeRequirements(
                required_root_mappings=_texts(
                    _required(resume, "requiredRootMappings", "/resume"),
                    "/resume/requiredRootMappings",
                ),
                required_capabilities=_texts(
                    _required(resume, "requiredCapabilities", "/resume"),
                    "/resume/requiredCapabilities",
                ),
                required_providers=provider_ids,
                pending_waits=_texts(
                    _required(resume, "pendingWaits", "/resume"), "/resume/pendingWaits"
                ),
                unavailable_artifacts=_artifact_ids(
                    _required(resume, "unavailableArtifacts", "/resume"),
                    "/resume/unavailableArtifacts",
                ),
            ),
        )
    except BundleError:
        raise
    except (TypeError, ValueError, ValidationError):
        raise BundleError(code="bundle_manifest_malformed") from None
    return manifest
