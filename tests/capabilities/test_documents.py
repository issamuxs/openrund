from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from openrund.capabilities import CapabilityRegistry, DocumentsCapability, FilesystemMount
from openrund.capabilities.documents import _frontmatter, _heading_entries, _replace_range
from openrund.contracts.capabilities import CapabilityAccessMode, CapabilityResult
from openrund.contracts.content import Content
from openrund.contracts.ids import ActionId, CapabilityId
from openrund.contracts.json import JsonArray, JsonObject
from openrund.errors import CapabilityExecutionError
from openrund.ports.capabilities import CapabilityInvocation

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _registry(
    root: Path,
    *,
    max_document_bytes: int = 8 * 1024 * 1024,
    max_diff_bytes: int = 2 * 1024 * 1024,
) -> CapabilityRegistry:
    capability = DocumentsCapability(
        mounts=(
            FilesystemMount(
                name="workspace",
                root=root,
                access=CapabilityAccessMode.READ_WRITE,
            ),
        ),
        max_document_bytes=max_document_bytes,
        max_diff_bytes=max_diff_bytes,
    )
    return CapabilityRegistry(
        (capability.registered(module_search_path=_PROJECT_ROOT / "src", timeout_ms=5_000),)
    )


def _invoke(
    registry: CapabilityRegistry,
    action: str,
    data: dict[str, object],
) -> CapabilityResult:
    return asyncio.run(
        registry.invoke(
            CapabilityInvocation(
                action_id=ActionId(value=f"action-{action}"),
                capability_id=CapabilityId(value="documents"),
                action_name=action,
                input=Content(data=data),  # type: ignore[arg-type]
            )
        )
    )


def _output(result: CapabilityResult) -> JsonObject:
    assert isinstance(result.output, JsonObject)
    return result.output


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_markdown_functions_are_deterministic_and_fence_aware() -> None:
    document = """---
title: "Report"
draft: false
---

# One
body
```md
# Not a heading
```
## Child
more
# Two
"""

    frontmatter, body, present = _frontmatter(document)
    headings = _heading_entries(document)

    assert present is True
    assert dict(frontmatter.entries) == {"draft": False, "title": "Report"}
    assert body.startswith("\n# One")
    assert [entry["title"] for entry in headings] == ["One", "Child", "Two"]
    assert headings[0]["endLine"] == headings[2]["startLine"]
    assert _replace_range("one\ntwo\nthree\n", 2, 3, "changed\n") == ("one\nchanged\nthree\n")


def test_stdio_read_headings_frontmatter_and_section_are_hash_bound(tmp_path: Path) -> None:
    document = """---
title: "Report"
draft: false
---

# Intro
hello

## Detail
facts
"""
    (tmp_path / "report.md").write_text(document, encoding="utf-8")
    registry = _registry(tmp_path)

    read = _invoke(registry, "read", {"mount": "workspace", "path": "report.md"})
    headings = _invoke(registry, "headings", {"mount": "workspace", "path": "report.md"})
    frontmatter = _invoke(registry, "frontmatter_read", {"mount": "workspace", "path": "report.md"})
    section = _invoke(
        registry,
        "section_read",
        {"mount": "workspace", "path": "report.md", "heading": "Intro"},
    )

    assert _output(read)["text"] == document
    assert _output(read)["sha256"] == _digest(document)
    assert read.inline_artifacts[0].kind == "documents.markdown"
    assert read.inline_artifacts[0].content == document.encode()
    heading_values = _output(headings)["headings"]
    assert isinstance(heading_values, JsonArray)
    assert [value["title"] for value in heading_values if isinstance(value, JsonObject)] == [
        "Intro",
        "Detail",
    ]
    frontmatter_value = _output(frontmatter)["frontmatter"]
    assert isinstance(frontmatter_value, JsonObject)
    assert dict(frontmatter_value.entries) == {"draft": False, "title": "Report"}
    assert _output(section)["text"] == "# Intro\nhello\n\n## Detail\nfacts\n"


def test_stdio_whole_write_is_atomic_and_hash_guarded(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    created = _invoke(
        registry,
        "write",
        {
            "mount": "workspace",
            "path": "nested/report.md",
            "text": "# Created\n",
            "createParents": True,
        },
    )
    assert (tmp_path / "nested" / "report.md").read_text(encoding="utf-8") == "# Created\n"
    assert _output(created)["afterSha256"] == _digest("# Created\n")
    assert created.inline_artifacts[0].kind == "documents.diff"

    with pytest.raises(CapabilityExecutionError, match="documents_expected_hash_required"):
        _invoke(
            registry,
            "write",
            {"mount": "workspace", "path": "nested/report.md", "text": "unsafe\n"},
        )
    with pytest.raises(CapabilityExecutionError, match="documents_stale_hash"):
        _invoke(
            registry,
            "write",
            {
                "mount": "workspace",
                "path": "nested/report.md",
                "text": "unsafe\n",
                "expectedSha256": "0" * 64,
            },
        )
    assert (tmp_path / "nested" / "report.md").read_text(encoding="utf-8") == "# Created\n"


def test_stdio_frontmatter_section_range_and_append_mutations(tmp_path: Path) -> None:
    target = tmp_path / "report.md"
    initial = "# Intro\nold\n# End\nlast\n"
    target.write_text(initial, encoding="utf-8")
    registry = _registry(tmp_path)

    frontmatter = _invoke(
        registry,
        "frontmatter_set",
        {
            "mount": "workspace",
            "path": "report.md",
            "frontmatter": {"title": "Report", "draft": False},
            "expectedSha256": _digest(initial),
        },
    )
    after_frontmatter = target.read_text(encoding="utf-8")
    assert after_frontmatter.startswith('---\ndraft: false\ntitle: "Report"\n---\n\n# Intro')
    assert _output(frontmatter)["beforeSha256"] == _digest(initial)

    section = _invoke(
        registry,
        "section_replace",
        {
            "mount": "workspace",
            "path": "report.md",
            "heading": "Intro",
            "text": "new body",
            "expectedSha256": _digest(after_frontmatter),
        },
    )
    after_section = target.read_text(encoding="utf-8")
    assert "# Intro\nnew body\n# End" in after_section
    assert _output(section)["afterSha256"] == _digest(after_section)

    _invoke(
        registry,
        "range_replace",
        {
            "mount": "workspace",
            "path": "report.md",
            "startLine": len(after_section.splitlines()) + 1,
            "endLine": len(after_section.splitlines()) + 1,
            "text": "range tail\n",
            "expectedSha256": _digest(after_section),
        },
    )
    after_range = target.read_text(encoding="utf-8")
    assert after_range.endswith("range tail\n")

    _invoke(
        registry,
        "append",
        {
            "mount": "workspace",
            "path": "report.md",
            "text": "appended\n",
            "expectedSha256": _digest(after_range),
        },
    )
    assert target.read_text(encoding="utf-8").endswith("range tail\nappended\n")


def test_stdio_structured_patches_apply_in_order_and_reject_overlap(tmp_path: Path) -> None:
    target = tmp_path / "report.md"
    initial = "# One\nold\n# Two\nsecond\n"
    target.write_text(initial, encoding="utf-8")
    registry = _registry(tmp_path)

    result = _invoke(
        registry,
        "patch",
        {
            "mount": "workspace",
            "path": "report.md",
            "expectedSha256": _digest(initial),
            "patches": [
                {"op": "replace_section", "heading": "One", "text": "new"},
                {"op": "append", "text": "tail\n"},
            ],
        },
    )
    updated = target.read_text(encoding="utf-8")
    assert updated == "# One\nnew\n# Two\nsecond\ntail\n"
    assert _output(result)["afterSha256"] == _digest(updated)

    with pytest.raises(CapabilityExecutionError, match="documents_patch_overlap"):
        _invoke(
            registry,
            "patch",
            {
                "mount": "workspace",
                "path": "report.md",
                "expectedSha256": _digest(updated),
                "patches": [
                    {"op": "replace_range", "startLine": 1, "endLine": 3, "text": "x\n"},
                    {"op": "replace_range", "startLine": 2, "endLine": 4, "text": "y\n"},
                ],
            },
        )
    assert target.read_text(encoding="utf-8") == updated


def test_stdio_ambiguous_sections_require_an_occurrence(tmp_path: Path) -> None:
    document = "# Same\none\n# Same\ntwo\n"
    (tmp_path / "duplicate.md").write_text(document, encoding="utf-8")
    registry = _registry(tmp_path)

    with pytest.raises(CapabilityExecutionError, match="documents_section_ambiguous"):
        _invoke(
            registry,
            "section_read",
            {"mount": "workspace", "path": "duplicate.md", "heading": "Same"},
        )
    second = _invoke(
        registry,
        "section_read",
        {
            "mount": "workspace",
            "path": "duplicate.md",
            "heading": "Same",
            "occurrence": 2,
        },
    )
    assert _output(second)["text"] == "# Same\ntwo\n"


def test_stdio_invalid_utf8_frontmatter_ranges_and_diff_limits_do_not_mutate(
    tmp_path: Path,
) -> None:
    (tmp_path / "binary.md").write_bytes(b"\xff")
    malformed = "---\ntitle: one\n# no close\n"
    (tmp_path / "malformed.md").write_text(malformed, encoding="utf-8")
    stable = "one\ntwo\n"
    target = tmp_path / "stable.md"
    target.write_text(stable, encoding="utf-8")
    registry = _registry(tmp_path, max_diff_bytes=12)

    with pytest.raises(CapabilityExecutionError, match="documents_utf8_required"):
        _invoke(registry, "read", {"mount": "workspace", "path": "binary.md"})
    with pytest.raises(CapabilityExecutionError, match="documents_frontmatter_unclosed"):
        _invoke(
            registry,
            "frontmatter_read",
            {"mount": "workspace", "path": "malformed.md"},
        )
    with pytest.raises(CapabilityExecutionError, match="documents_range_invalid"):
        _invoke(
            registry,
            "range_replace",
            {
                "mount": "workspace",
                "path": "stable.md",
                "startLine": 9,
                "endLine": 10,
                "text": "bad\n",
                "expectedSha256": _digest(stable),
            },
        )
    with pytest.raises(CapabilityExecutionError, match="documents_diff_too_large"):
        _invoke(
            registry,
            "append",
            {
                "mount": "workspace",
                "path": "stable.md",
                "text": "a substantial addition\n",
                "expectedSha256": _digest(stable),
            },
        )
    assert target.read_text(encoding="utf-8") == stable


@pytest.mark.parametrize("path", ["../outside.md", "/absolute.md", "a\\b.md"])
def test_stdio_worker_rejects_paths_outside_its_root(tmp_path: Path, path: str) -> None:
    registry = _registry(tmp_path)
    with pytest.raises(CapabilityExecutionError, match="filesystem_path_invalid"):
        _invoke(registry, "read", {"mount": "workspace", "path": path})


def test_stdio_worker_rejects_symlink_components(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("secret", encoding="utf-8")
    (root / "linked").symlink_to(outside, target_is_directory=True)
    registry = _registry(root)

    with pytest.raises(CapabilityExecutionError, match="filesystem_symlink_forbidden"):
        _invoke(
            registry,
            "read",
            {"mount": "workspace", "path": "linked/secret.md"},
        )
