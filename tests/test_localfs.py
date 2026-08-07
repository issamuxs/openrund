from __future__ import annotations

from pathlib import Path

import pytest

from openrund._localfs import (
    LocalFilesystemError,
    fsync_directory,
    read_regular_file,
    secure_directory_tree,
    write_new_file,
)


def test_directory_tree_rejects_symlink_ancestors(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    redirected = tmp_path / "redirected"
    redirected.symlink_to(target, target_is_directory=True)

    with pytest.raises(LocalFilesystemError) as raised:
        secure_directory_tree(redirected / "child", create=True)

    assert raised.value.reason == "symlink"
    assert not (target / "child").exists()


def test_exclusive_write_and_bounded_regular_read(tmp_path: Path) -> None:
    target = tmp_path / "evidence"
    write_new_file(target, b"durable")
    fsync_directory(tmp_path)

    assert read_regular_file(target, limit=7) == b"durable"
    with pytest.raises(FileExistsError):
        write_new_file(target, b"replacement")
    with pytest.raises(LocalFilesystemError) as raised:
        read_regular_file(target, limit=6)
    assert raised.value.reason == "too_large"


def test_bounded_read_rejects_symlinks_and_non_regular_files(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_bytes(b"content")
    link = tmp_path / "link"
    link.symlink_to(target)

    with pytest.raises(LocalFilesystemError):
        read_regular_file(link, limit=100)
    with pytest.raises(LocalFilesystemError):
        read_regular_file(tmp_path, limit=100)
