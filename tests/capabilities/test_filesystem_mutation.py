from __future__ import annotations

import asyncio
import base64
import errno
import hashlib
import os
from pathlib import Path

import pytest

from openrund.capabilities import CapabilityRegistry, FilesystemCapability, FilesystemMount
from openrund.contracts.capabilities import CapabilityAccessMode, CapabilityResult
from openrund.contracts.content import Content
from openrund.contracts.ids import ActionId, CapabilityId
from openrund.contracts.json import JsonObject
from openrund.errors import CapabilityExecutionError
from openrund.ports.capabilities import CapabilityInvocation


def _registry(
    root: Path,
    *,
    access: CapabilityAccessMode = CapabilityAccessMode.READ_WRITE,
    max_write_bytes: int = 1_024,
    max_diff_bytes: int = 4_096,
) -> CapabilityRegistry:
    capability = FilesystemCapability(
        mounts=(FilesystemMount(name="workspace", root=root, access=access),),
        max_read_bytes=4_096,
        max_write_bytes=max_write_bytes,
        max_diff_bytes=max_diff_bytes,
    )
    return CapabilityRegistry((capability.registered(),))


def _invoke(
    registry: CapabilityRegistry,
    action: str,
    data: dict[str, object],
) -> CapabilityResult:
    return asyncio.run(
        registry.invoke(
            CapabilityInvocation(
                action_id=ActionId(value=f"action-{action}"),
                capability_id=CapabilityId(value="filesystem"),
                action_name=action,
                input=Content(data=data),  # type: ignore[arg-type]
            )
        )
    )


def _output(result: CapabilityResult) -> JsonObject:
    assert isinstance(result.output, JsonObject)
    return result.output


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def test_write_creates_binary_content_and_parents_atomically(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    content = b"\x00binary\xff"
    result = _invoke(
        registry,
        "write",
        {
            "mount": "workspace",
            "path": "nested/data.bin",
            "contentBase64": base64.b64encode(content).decode("ascii"),
            "createParents": True,
        },
    )

    assert (tmp_path / "nested" / "data.bin").read_bytes() == content
    assert _output(result)["afterSha256"] == _digest(content)
    assert _output(result)["atomic"] is True
    assert result.inline_artifacts[0].kind == "filesystem.receipt"
    assert not tuple(tmp_path.rglob(".openrund-stage-*"))


def test_write_requires_explicit_overwrite_and_expected_hash(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("before", encoding="utf-8")
    registry = _registry(tmp_path)
    before = _digest(b"before")

    with pytest.raises(CapabilityExecutionError, match="filesystem_target_exists"):
        _invoke(
            registry,
            "write",
            {"mount": "workspace", "path": "file.txt", "text": "after"},
        )
    with pytest.raises(CapabilityExecutionError, match="filesystem_expected_hash_required"):
        _invoke(
            registry,
            "write",
            {
                "mount": "workspace",
                "path": "file.txt",
                "text": "after",
                "overwrite": True,
            },
        )
    with pytest.raises(CapabilityExecutionError, match="filesystem_stale_hash"):
        _invoke(
            registry,
            "write",
            {
                "mount": "workspace",
                "path": "file.txt",
                "text": "after",
                "overwrite": True,
                "expectedSha256": "0" * 64,
            },
        )

    _invoke(
        registry,
        "write",
        {
            "mount": "workspace",
            "path": "file.txt",
            "text": "after",
            "overwrite": True,
            "expectedSha256": before,
        },
    )
    assert target.read_text(encoding="utf-8") == "after"


def test_update_requires_existing_target_and_current_hash(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    with pytest.raises(CapabilityExecutionError, match="filesystem_update_target_missing"):
        _invoke(
            registry,
            "update",
            {
                "mount": "workspace",
                "path": "missing.txt",
                "text": "new",
                "expectedSha256": _digest(b"old"),
            },
        )
    target = tmp_path / "file.txt"
    target.write_text("old", encoding="utf-8")
    with pytest.raises(CapabilityExecutionError, match="filesystem_stale_hash"):
        _invoke(
            registry,
            "update",
            {
                "mount": "workspace",
                "path": "file.txt",
                "text": "new",
                "expectedSha256": "0" * 64,
            },
        )
    result = _invoke(
        registry,
        "update",
        {
            "mount": "workspace",
            "path": "file.txt",
            "text": "new",
            "expectedSha256": _digest(b"old"),
        },
    )
    assert target.read_text(encoding="utf-8") == "new"
    assert _output(result)["beforeSha256"] == _digest(b"old")


def test_failed_atomic_replace_preserves_target_and_cleans_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "file.txt"
    target.write_text("before", encoding="utf-8")
    registry = _registry(tmp_path)

    def fail_replace(_source: object, _target: object) -> None:
        raise OSError("simulated")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(CapabilityExecutionError, match="filesystem_atomic_replace_failed"):
        _invoke(
            registry,
            "update",
            {
                "mount": "workspace",
                "path": "file.txt",
                "text": "after",
                "expectedSha256": _digest(b"before"),
            },
        )
    assert target.read_text(encoding="utf-8") == "before"
    assert not tuple(tmp_path.glob(".openrund-stage-*"))


def test_delete_is_file_only_and_hash_guarded(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("delete me", encoding="utf-8")
    (tmp_path / "folder").mkdir()
    registry = _registry(tmp_path)
    with pytest.raises(CapabilityExecutionError, match="filesystem_stale_hash"):
        _invoke(
            registry,
            "delete",
            {
                "mount": "workspace",
                "path": "file.txt",
                "expectedSha256": "0" * 64,
            },
        )
    with pytest.raises(CapabilityExecutionError):
        _invoke(
            registry,
            "delete",
            {
                "mount": "workspace",
                "path": "folder",
                "expectedSha256": _digest(b""),
            },
        )
    result = _invoke(
        registry,
        "delete",
        {
            "mount": "workspace",
            "path": "file.txt",
            "expectedSha256": _digest(b"delete me"),
        },
    )
    assert not target.exists()
    assert _output(result)["beforeSha256"] == _digest(b"delete me")


def test_move_is_atomic_hash_guarded_and_never_copies_across_devices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.txt"
    source.write_text("move", encoding="utf-8")
    registry = _registry(tmp_path)
    result = _invoke(
        registry,
        "move",
        {
            "mount": "workspace",
            "path": "source.txt",
            "toMount": "workspace",
            "toPath": "nested/target.txt",
            "expectedSha256": _digest(b"move"),
            "createParents": True,
        },
    )
    assert not source.exists()
    assert (tmp_path / "nested" / "target.txt").read_text(encoding="utf-8") == "move"
    assert _output(result)["atomic"] is True

    second = tmp_path / "second.txt"
    second.write_text("second", encoding="utf-8")

    def cross_device(_source: object, _target: object) -> None:
        raise OSError(errno.EXDEV, "cross-device")

    monkeypatch.setattr(os, "replace", cross_device)
    with pytest.raises(CapabilityExecutionError, match="filesystem_cross_device_move_forbidden"):
        _invoke(
            registry,
            "move",
            {
                "mount": "workspace",
                "path": "second.txt",
                "toMount": "workspace",
                "toPath": "other.txt",
                "expectedSha256": _digest(b"second"),
            },
        )
    assert second.exists()
    assert not (tmp_path / "other.txt").exists()


def test_move_overwrite_requires_exact_target_hash(tmp_path: Path) -> None:
    (tmp_path / "source.txt").write_text("source", encoding="utf-8")
    (tmp_path / "target.txt").write_text("target", encoding="utf-8")
    registry = _registry(tmp_path)
    base = {
        "mount": "workspace",
        "path": "source.txt",
        "toMount": "workspace",
        "toPath": "target.txt",
        "expectedSha256": _digest(b"source"),
        "overwrite": True,
    }
    with pytest.raises(CapabilityExecutionError, match="filesystem_target_hash_required"):
        _invoke(registry, "move", base)
    with pytest.raises(CapabilityExecutionError, match="filesystem_target_stale_hash"):
        _invoke(registry, "move", {**base, "expectedTargetSha256": "0" * 64})
    _invoke(
        registry,
        "move",
        {**base, "expectedTargetSha256": _digest(b"target")},
    )
    assert (tmp_path / "target.txt").read_text(encoding="utf-8") == "source"


def test_diff_returns_deterministic_bounded_artifact_without_mutation(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("one\ntwo\n", encoding="utf-8")
    registry = _registry(tmp_path)
    result = _invoke(
        registry,
        "diff",
        {
            "mount": "workspace",
            "path": "file.txt",
            "against": "one\nchanged\n",
            "context": 1,
        },
    )
    diff = result.inline_artifacts[0].content.decode("utf-8")
    assert "--- file.txt" in diff
    assert "+changed" in diff
    assert target.read_text(encoding="utf-8") == "one\ntwo\n"
    assert _output(result)["changed"] is True

    binary = tmp_path / "binary"
    binary.write_bytes(b"\xff")
    with pytest.raises(CapabilityExecutionError, match="filesystem_diff_text_required"):
        _invoke(
            registry,
            "diff",
            {"mount": "workspace", "path": "binary", "against": "text"},
        )


def test_mutations_require_writable_mount_and_enforce_content_limit(tmp_path: Path) -> None:
    read_only = _registry(tmp_path, access=CapabilityAccessMode.READ)
    with pytest.raises(CapabilityExecutionError, match="filesystem_mount_read_only"):
        _invoke(
            read_only,
            "write",
            {"mount": "workspace", "path": "file", "text": "x"},
        )
    writable = _registry(tmp_path, max_write_bytes=1)
    with pytest.raises(CapabilityExecutionError, match="filesystem_write_too_large"):
        _invoke(
            writable,
            "write",
            {"mount": "workspace", "path": "file", "text": "xx"},
        )


def test_parent_creation_rejects_symlinked_component(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)
    registry = _registry(root)
    with pytest.raises(CapabilityExecutionError, match="filesystem_symlink_forbidden"):
        _invoke(
            registry,
            "write",
            {
                "mount": "workspace",
                "path": "linked/escaped.txt",
                "text": "no",
                "createParents": True,
            },
        )
    assert not (outside / "escaped.txt").exists()
