from __future__ import annotations

import json
import tarfile
import tomllib
import zipfile
from pathlib import Path
from typing import Final

from tests.package._distributions import (
    BuiltDistributions,
    install_distribution,
    run_installed,
)

from openrund._version import __version__
from openrund.bundles import BundleCompatibility

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]


def _content_files(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }


def test_project_metadata_locks_python_and_tooling_contract() -> None:
    metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["requires-python"] == ">=3.12"
    assert metadata["project"]["dependencies"] == []
    assert metadata["project"]["dynamic"] == ["version"]
    assert metadata["project"]["readme"] == "README.md"
    assert metadata["project"]["optional-dependencies"]["test"]
    assert (
        metadata["project"]["optional-dependencies"]["test"] == metadata["dependency-groups"]["dev"]
    )
    assert metadata["tool"]["hatch"]["version"]["path"] == "src/openrund/_version.py"
    development_tools = {
        requirement.split(">=", 1)[0].split("[", 1)[0]
        for requirement in metadata["dependency-groups"]["dev"]
    }
    assert development_tools == {
        "coverage",
        "mypy",
        "pytest",
        "ruff",
    }
    assert metadata["build-system"]["build-backend"] == "hatchling.build"
    assert __version__ == "2.0.0"
    assert BundleCompatibility().runtime_version == __version__


def test_built_artifacts_have_exact_greenfield_release_content(
    built_distributions: BuiltDistributions,
) -> None:
    wheel = built_distributions.wheel
    source_distribution = built_distributions.source

    with zipfile.ZipFile(wheel) as archive:
        wheel_files = {name for name in archive.namelist() if not name.endswith("/")}
    package_files = {
        f"openrund/{relative_path}"
        for relative_path in _content_files(PROJECT_ROOT / "src" / "openrund")
    }
    metadata_root = f"openrund-{__version__}.dist-info"
    assert wheel_files == package_files | {
        f"{metadata_root}/METADATA",
        f"{metadata_root}/RECORD",
        f"{metadata_root}/WHEEL",
        f"{metadata_root}/entry_points.txt",
    }
    assert "openrund/py.typed" in wheel_files

    with tarfile.open(source_distribution, mode="r:gz") as archive:
        source_files = {
            member.name.removeprefix(f"openrund-{__version__}/")
            for member in archive.getmembers()
            if member.isfile()
        }
    expected_source_files = {
        "CHANGELOG.md",
        ".gitignore",
        "PKG-INFO",
        "README.md",
        "SECURITY.md",
        "pyproject.toml",
        *{f"docs/{name}" for name in _content_files(PROJECT_ROOT / "docs")},
        *{f"examples/{name}" for name in _content_files(PROJECT_ROOT / "examples")},
        *{f"src/openrund/{name}" for name in _content_files(PROJECT_ROOT / "src" / "openrund")},
    }
    assert source_files == expected_source_files


def test_wheel_import_is_isolated_and_root_surface_is_narrow(
    tmp_path: Path,
    built_distributions: BuiltDistributions,
) -> None:
    installed = install_distribution(built_distributions, tmp_path)
    isolated_directory = tmp_path / "isolated"
    isolated_directory.mkdir()
    probe = """
import json
from importlib.metadata import version
from pathlib import Path
import openrund

print(json.dumps({
    "module_file": str(Path(openrund.__file__).resolve()),
    "distribution_version": version("openrund"),
    "public_names": sorted(name for name in vars(openrund) if not name.startswith("_")),
    "declared_names": list(openrund.__all__),
}))
"""

    completed = run_installed(
        str(installed.python),
        "-I",
        "-c",
        probe,
        cwd=isolated_directory,
    )
    result = json.loads(completed.stdout)
    module_file = Path(result["module_file"])

    assert result["distribution_version"] == "2.0.0"
    assert set(result["declared_names"]).issubset(result["public_names"])
    assert sorted(set(result["public_names"]) - set(result["declared_names"])) == [
        "assembly",
        "cli",
        "codec",
        "demo",
        "engine",
        "errors",
        "operator",
        "paths",
        "ports",
        "runtime",
    ]
    assert result["declared_names"] == sorted(result["declared_names"])
    assert module_file.name == "__init__.py"
    assert not module_file.is_relative_to(PROJECT_ROOT)
