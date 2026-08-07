from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from openrund.capabilities import (
    CapabilityRegistry,
    FilesystemMount,
    GitCapability,
    GitIdentity,
)
from openrund.contracts.capabilities import CapabilityAccessMode, CapabilityResult
from openrund.contracts.content import Content
from openrund.contracts.ids import ActionId, CapabilityId
from openrund.contracts.json import JsonObject
from openrund.errors import CapabilityExecutionError, CapabilityProtocolError, ValidationError
from openrund.ports.capabilities import CapabilityInvocation


def _git_executable() -> Path:
    candidate = shutil.which("git")
    assert candidate is not None
    return Path(candidate).resolve()


def _raw_git(root: Path, *arguments: str, input_text: str | None = None) -> str:
    result = subprocess.run(
        (_git_executable(), *arguments),
        cwd=root,
        env={
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        },
        input=input_text,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def _raw_git_bytes(root: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        (_git_executable(), *arguments),
        cwd=root,
        env={
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        },
        capture_output=True,
        check=True,
    )
    return result.stdout


def _repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _raw_git(root, "init", "--quiet")
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    _raw_git(root, "add", "--", "README.md")
    _raw_git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.rejected",
        "commit",
        "--quiet",
        "-m",
        "initial",
    )
    return root


def _capability(root: Path, **limits: int) -> GitCapability:
    return GitCapability(
        mounts=(
            FilesystemMount(
                name="workspace",
                root=root,
                access=CapabilityAccessMode.READ_WRITE,
            ),
        ),
        git_executable=_git_executable(),
        identities=(
            GitIdentity(
                name="robot",
                author_name="OpenRund Robot",
                author_email="robot@example.rejected",
            ),
        ),
        **limits,
    )


def _invocation(action: str, data: dict[str, object]) -> CapabilityInvocation:
    return CapabilityInvocation(
        action_id=ActionId(value=f"action-git-{action}"),
        capability_id=CapabilityId(value="git"),
        action_name=action,
        input=Content(data=data),  # type: ignore[arg-type]
    )


def _invoke(
    capability: GitCapability,
    action: str,
    data: dict[str, object] | None = None,
) -> CapabilityResult:
    registry = CapabilityRegistry((capability.registered(),))
    payload: dict[str, object] = {"repoMount": "workspace"}
    if data is not None:
        payload.update(data)
    return asyncio.run(registry.invoke(_invocation(action, payload)))


def _output(result: CapabilityResult) -> JsonObject:
    assert isinstance(result.output, JsonObject)
    return result.output


def test_git_status_diff_apply_stage_commit_and_head(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    capability = _capability(root)
    (root / "README.md").write_text("hello\nupdated\n", encoding="utf-8")

    status = _invoke(capability, "status")
    diff = _invoke(capability, "diff")

    assert b" M README.md" in status.inline_artifacts[0].content
    assert status.inline_artifacts[0].kind == "git.status"
    assert b"+updated" in diff.inline_artifacts[0].content
    assert diff.inline_artifacts[0].kind == "git.diff"

    patch = """diff --git a/notes.md b/notes.md
new file mode 100644
index 0000000..1269488
--- /dev/null
+++ b/notes.md
@@ -0,0 +1 @@
+notes
"""
    applied = _invoke(capability, "apply", {"patch": patch})
    assert (root / "notes.md").read_text(encoding="utf-8") == "notes\n"
    assert _output(applied)["patchSha256"] == hashlib.sha256(patch.encode()).hexdigest()

    staged = _invoke(capability, "stage", {"paths": ["README.md", "notes.md"]})
    assert tuple(_output(staged)["paths"]) == ("README.md", "notes.md")  # type: ignore[arg-type]
    commit = _invoke(
        capability,
        "commit",
        {"message": "--message-is-data\n\nbody", "identity": "robot"},
    )
    head = _invoke(capability, "head")

    commit_id = _output(commit)["commit"]
    assert isinstance(commit_id, str) and len(commit_id) == 40
    assert _output(head)["commit"] == commit_id
    assert _output(commit)["identity"] == "robot"
    assert _raw_git(root, "log", "-1", "--pretty=%an <%ae>").strip() == (
        "OpenRund Robot <robot@example.rejected>"
    )
    assert _raw_git(root, "log", "-1", "--pretty=%B").startswith("--message-is-data")
    assert commit.effects[0].kind == "git.commit.created"


def test_git_stage_supports_binary_files_and_deletions_without_filters(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    capability = _capability(root)
    binary = b"\x00binary\xff"
    (root / "binary.dat").write_bytes(binary)
    (root / "README.md").unlink()

    _invoke(capability, "stage", {"paths": ["binary.dat", "README.md"]})

    assert _raw_git_bytes(root, "show", ":binary.dat") == binary
    staged_names = _raw_git(root, "diff", "--staged", "--name-status")
    assert "A\tbinary.dat" in staged_names
    assert "D\tREADME.md" in staged_names


def test_git_diff_output_is_bounded_and_hashed_over_full_stream(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    capability = _capability(root, max_output_bytes=80)
    (root / "README.md").write_text("updated\n" * 500, encoding="utf-8")

    result = _invoke(capability, "diff")
    output = _output(result)

    assert output["truncated"] is True
    assert isinstance(output["byteLength"], int) and output["byteLength"] > 80
    assert len(result.inline_artifacts[0].content) == 80
    assert len(str(output["sha256"])) == 64


def test_git_status_output_is_artifact_backed_and_bounded(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    for index in range(40):
        (root / f"untracked-{index:02}.txt").write_text("x", encoding="utf-8")
    result = _invoke(_capability(root, max_output_bytes=64), "status")

    assert _output(result)["truncated"] is True
    assert len(result.inline_artifacts[0].content) == 64
    assert result.inline_artifacts[0].kind == "git.status"


def test_git_security_exposes_no_remote_config_or_submodule_verbs(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    capability = _capability(root)
    names = {action.name for action in capability.registered().definition.actions}
    assert names == {"status", "diff", "head", "apply", "stage", "commit"}

    registry = CapabilityRegistry((capability.registered(),))
    for action in ("push", "pull", "fetch", "remote", "config", "submodule", "credential"):
        with pytest.raises(CapabilityProtocolError, match="capability_action_not_registered"):
            asyncio.run(
                registry.invoke(
                    CapabilityInvocation(
                        action_id=ActionId(value=f"action-{action}"),
                        capability_id=CapabilityId(value="git"),
                        action_name=action,
                        input=Content(data={"repoMount": "workspace"}),  # type: ignore[arg-type]
                    )
                )
            )


@pytest.mark.parametrize(
    "path",
    ["../escape", "/absolute", "-c", "folder/-option", ".git/config", "a\\b"],
)
def test_git_security_rejects_path_and_option_injection(tmp_path: Path, path: str) -> None:
    root = _repo(tmp_path / "repo")
    capability = _capability(root)
    with pytest.raises(CapabilityExecutionError, match="git_path"):
        _invoke(capability, "stage", {"paths": [path]})


def test_git_security_rejects_repository_escape_and_symlinks(tmp_path: Path) -> None:
    repository = _repo(tmp_path / "repo")
    subdir = repository / "subdir"
    subdir.mkdir()
    escaped = _capability(subdir)
    with pytest.raises(CapabilityExecutionError, match="git_repository_invalid"):
        _invoke(escaped, "status")

    outer = tmp_path / "outer"
    outer.mkdir()
    (outer / "linked").symlink_to(repository, target_is_directory=True)
    linked = _capability(outer)
    with pytest.raises(CapabilityExecutionError, match="filesystem_symlink_forbidden"):
        _invoke(linked, "status", {"repoPath": "linked"})

    fake = tmp_path / "fake"
    fake.mkdir()
    (fake / ".git").symlink_to(repository / ".git", target_is_directory=True)
    with pytest.raises(CapabilityExecutionError, match="git_directory_invalid"):
        _invoke(_capability(fake), "status")


def test_git_security_rejects_symlink_path_components_and_object_alternates(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path / "repo")
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)
    capability = _capability(root)
    with pytest.raises(CapabilityExecutionError, match="git_path_symlink_forbidden"):
        _invoke(capability, "stage", {"paths": ["linked/file.txt"]})

    alternates = root / ".git" / "objects" / "info" / "alternates"
    alternates.write_text(str(outside), encoding="utf-8")
    with pytest.raises(CapabilityExecutionError, match="git_object_alternates_forbidden"):
        _invoke(capability, "head")


def test_git_security_disables_hooks_external_diff_and_clean_filters(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    capability = _capability(root)
    marker = root / "authority-escaped"
    helper = root / "malicious.sh"
    helper.write_text(f"#!/bin/sh\ntouch '{marker}'\ncat\n", encoding="utf-8")
    helper.chmod(0o755)
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    (root / ".gitattributes").write_text("README.md diff=evil filter=evil\n", encoding="utf-8")
    _raw_git(root, "config", "diff.evil.command", str(helper))
    _raw_git(root, "config", "filter.evil.clean", str(helper))
    _raw_git(root, "config", "filter.evil.required", "true")
    (root / "README.md").write_text("changed\n", encoding="utf-8")

    with pytest.raises(CapabilityExecutionError, match="git_repository_config_forbidden"):
        _invoke(capability, "diff", {"paths": ["README.md"]})
    assert not marker.exists()

    _raw_git(root, "config", "--remove-section", "diff.evil")
    _raw_git(root, "config", "--remove-section", "filter.evil")
    _invoke(capability, "stage", {"paths": ["README.md", ".gitattributes"]})
    _invoke(capability, "commit", {"message": "safe", "identity": "robot"})

    assert not marker.exists()
    assert _raw_git(root, "show", "HEAD:README.md") == "changed\n"


def test_git_security_does_not_inherit_credentials_or_invoke_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path / "repo")
    marker = root / "credential-helper-ran"
    helper = root / "credential-helper.sh"
    helper.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
    helper.chmod(0o755)
    _raw_git(root, "config", "credential.helper", str(helper))
    _raw_git(root, "remote", "add", "origin", "https://example.invalid/repo.git")
    monkeypatch.setenv("GITHUB_TOKEN", "must-not-leak")
    monkeypatch.setenv("GIT_ASKPASS", str(helper))

    capability = _capability(root)
    with pytest.raises(CapabilityExecutionError, match="git_repository_config_forbidden"):
        _invoke(capability, "status")

    assert not marker.exists()


def test_git_security_rejects_malicious_patch_and_patch_size(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    capability = _capability(root, max_patch_bytes=256)
    escape_patch = """diff --git a/../escaped b/../escaped
new file mode 100644
--- /dev/null
+++ b/../escaped
@@ -0,0 +1 @@
+escaped
"""
    with pytest.raises(CapabilityExecutionError, match="git_command_failed"):
        _invoke(capability, "apply", {"patch": escape_patch})
    assert not (tmp_path / "escaped").exists()

    with pytest.raises(CapabilityExecutionError, match="git_patch_too_large"):
        _invoke(capability, "apply", {"patch": "x" * 257})


def test_git_security_identity_and_message_cannot_inject_options(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    capability = _capability(root)
    (root / "README.md").write_text("changed\n", encoding="utf-8")
    _invoke(capability, "stage", {"paths": ["README.md"]})

    registry = CapabilityRegistry((capability.registered(),))
    with pytest.raises(CapabilityProtocolError, match="capability_input_schema_violation"):
        asyncio.run(
            registry.invoke(
                _invocation(
                    "commit",
                    {
                        "repoMount": "workspace",
                        "message": "safe",
                        "identity": "-c user.email=attacker@example.invalid",
                    },
                )
            )
        )
    with pytest.raises(CapabilityExecutionError, match="git_commit_message_invalid"):
        _invoke(capability, "commit", {"message": "bad\x00value", "identity": "robot"})

    with pytest.raises(ValidationError, match="git_author_name_invalid"):
        GitIdentity(
            name="bad",
            author_name="Attacker\nInjected",
            author_email="safe@example.rejected",
        )


def test_git_empty_commit_and_non_repository_fail_safely(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    capability = _capability(root)
    with pytest.raises(CapabilityExecutionError, match="git_command_failed") as captured:
        _invoke(capability, "commit", {"message": "empty", "identity": "robot"})
    assert "nothing to commit" not in str(captured.value)

    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(CapabilityExecutionError, match="git_repository_invalid"):
        _invoke(_capability(plain), "status")
