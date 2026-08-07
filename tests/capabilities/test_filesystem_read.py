from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from openrund.capabilities import CapabilityRegistry, FilesystemCapability, FilesystemMount
from openrund.contracts.capabilities import CapabilityAccessMode, CapabilityResult
from openrund.contracts.content import Content
from openrund.contracts.ids import ActionId, CapabilityId
from openrund.contracts.json import JsonArray, JsonObject
from openrund.errors import CapabilityExecutionError, ValidationError
from openrund.ports.capabilities import CapabilityInvocation


def _filesystem(root: Path, **limits: int) -> tuple[FilesystemCapability, CapabilityRegistry]:
    capability = FilesystemCapability(
        mounts=(
            FilesystemMount(
                name="workspace",
                root=root,
                access=CapabilityAccessMode.READ,
            ),
        ),
        **limits,
    )
    return capability, CapabilityRegistry((capability.registered(),))


def _invoke(
    registry: CapabilityRegistry,
    action: str,
    *,
    path: str | None = None,
) -> CapabilityResult:
    data: dict[str, object] = {"mount": "workspace"}
    if path is not None:
        data["path"] = path
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


def test_read_returns_bounded_bytes_text_hash_and_evidence(tmp_path: Path) -> None:
    content = b"# Report\n\nSafe text.\n"
    (tmp_path / "report.md").write_bytes(content)
    _capability, registry = _filesystem(tmp_path)

    result = _invoke(registry, "read", path="report.md")

    output = _output(result)
    assert output["byteLength"] == len(content)
    assert output["sha256"] == hashlib.sha256(content).hexdigest()
    assert output["text"] == content.decode()
    assert result.inline_artifacts[0].content == content
    assert result.inline_artifacts[0].content_type == "text/plain; charset=utf-8"
    assert result.effects[0].kind == "filesystem.read"


def test_binary_read_uses_octet_stream_without_decoding(tmp_path: Path) -> None:
    content = b"\xff\x00binary"
    (tmp_path / "data.bin").write_bytes(content)
    _capability, registry = _filesystem(tmp_path)

    result = _invoke(registry, "read", path="data.bin")

    assert _output(result)["text"] is None
    assert result.inline_artifacts[0].content == content
    assert result.inline_artifacts[0].content_type == "application/octet-stream"


def test_list_is_sorted_bounded_and_does_not_follow_symlinks(tmp_path: Path) -> None:
    (tmp_path / "z.txt").write_text("z", encoding="utf-8")
    (tmp_path / "a-dir").mkdir()
    outside = tmp_path.parent / "outside-list-target"
    outside.write_text("outside", encoding="utf-8")
    (tmp_path / "link").symlink_to(outside)
    _capability, registry = _filesystem(tmp_path)

    result = _invoke(registry, "list")

    entries = _output(result)["entries"]
    assert isinstance(entries, JsonArray)
    assert all(isinstance(entry, JsonObject) for entry in entries)
    assert [entry["name"] for entry in entries if isinstance(entry, JsonObject)] == [
        "a-dir",
        "link",
        "z.txt",
    ]
    assert [entry["kind"] for entry in entries if isinstance(entry, JsonObject)] == [
        "directory",
        "symlink",
        "file",
    ]

    _small, small_registry = _filesystem(tmp_path, max_list_entries=2)
    with pytest.raises(CapabilityExecutionError, match="filesystem_list_too_large"):
        _invoke(small_registry, "list")


def test_stat_reports_file_hash_and_directory_without_following_links(tmp_path: Path) -> None:
    content = b"stable"
    (tmp_path / "file.txt").write_bytes(content)
    (tmp_path / "folder").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "file.txt")
    _capability, registry = _filesystem(tmp_path)

    file_result = _invoke(registry, "stat", path="file.txt")
    directory_result = _invoke(registry, "stat", path="folder")

    assert _output(file_result)["kind"] == "file"
    assert _output(file_result)["sha256"] == hashlib.sha256(content).hexdigest()
    assert _output(directory_result)["kind"] == "directory"
    assert _output(directory_result)["sha256"] is None
    with pytest.raises(CapabilityExecutionError, match="filesystem_symlink_forbidden"):
        _invoke(registry, "stat", path="link")


@pytest.mark.parametrize(
    "path",
    ["../outside", "/absolute", "C:/windows", "folder\\file", "./dot", "a//b", "nul\x00x"],
)
def test_sandbox_rejects_nonportable_paths_before_io(tmp_path: Path, path: str) -> None:
    _capability, registry = _filesystem(tmp_path)
    with pytest.raises(CapabilityExecutionError, match="filesystem_path_invalid"):
        _invoke(registry, "read", path=path)


def test_sandbox_rejects_symlink_components_and_mount_substitution(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret").write_text("secret", encoding="utf-8")
    (root / "linked").symlink_to(outside, target_is_directory=True)
    capability, registry = _filesystem(root)

    with pytest.raises(CapabilityExecutionError, match="filesystem_symlink_forbidden"):
        _invoke(registry, "read", path="linked/secret")

    moved = tmp_path / "moved"
    root.rename(moved)
    root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(CapabilityExecutionError, match="filesystem_mount_changed"):
        capability.sandbox.resolve("workspace", "secret")


def test_mount_configuration_rejects_relative_missing_file_and_symlink_roots(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="filesystem_mount_root_invalid"):
        FilesystemMount(
            name="workspace",
            root="relative",
            access=CapabilityAccessMode.READ,
        )
    missing = tmp_path / "missing"
    with pytest.raises(ValidationError, match="filesystem_mount_root_unavailable"):
        FilesystemMount(name="workspace", root=missing, access=CapabilityAccessMode.READ)
    file_root = tmp_path / "file"
    file_root.write_text("x", encoding="utf-8")
    with pytest.raises(ValidationError, match="filesystem_mount_root_invalid"):
        FilesystemMount(name="workspace", root=file_root, access=CapabilityAccessMode.READ)
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValidationError, match="filesystem_mount_root_invalid"):
        FilesystemMount(name="workspace", root=linked, access=CapabilityAccessMode.READ)


def test_read_limits_apply_before_unbounded_allocation(tmp_path: Path) -> None:
    (tmp_path / "large.bin").write_bytes(b"x" * 33)
    _capability, registry = _filesystem(tmp_path, max_read_bytes=32)

    with pytest.raises(CapabilityExecutionError, match="filesystem_read_too_large"):
        _invoke(registry, "read", path="large.bin")
    with pytest.raises(CapabilityExecutionError, match="filesystem_read_too_large"):
        _invoke(registry, "stat", path="large.bin")
