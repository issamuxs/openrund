from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, final

DistributionKind = Literal["wheel", "sdist"]


@final
@dataclass(frozen=True, slots=True)
class BuiltDistributions:
    wheel: Path
    source: Path

    def select(self, kind: DistributionKind) -> Path:
        return self.wheel if kind == "wheel" else self.source


@final
@dataclass(frozen=True, slots=True)
class InstalledDistribution:
    artifact: Path
    python: Path


def repository_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
        environment.pop(name, None)
    return environment


def installed_environment() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", ""),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "PATH": os.environ["PATH"],
    }


def run_checked(
    *args: str,
    cwd: Path,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def run_repository(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return run_checked(*args, cwd=cwd, environment=repository_environment())


def run_installed(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return run_checked(*args, cwd=cwd, environment=installed_environment())


def build_distributions(project_root: Path, output_directory: Path) -> BuiltDistributions:
    run_repository("uv", "build", "--out-dir", str(output_directory), cwd=project_root)
    wheels = tuple(output_directory.glob("*.whl"))
    sources = tuple(output_directory.glob("*.tar.gz"))
    assert len(wheels) == 1
    assert len(sources) == 1
    return BuiltDistributions(wheel=wheels[0], source=sources[0])


def install_distribution(
    built: BuiltDistributions,
    tmp_path: Path,
    *,
    kind: DistributionKind = "wheel",
) -> InstalledDistribution:
    environment = tmp_path / "environment"
    artifact = built.select(kind)
    run_installed(sys.executable, "-m", "venv", str(environment), cwd=tmp_path)
    python = environment / "bin" / "python"
    run_installed(
        "uv",
        "pip",
        "install",
        "--python",
        str(python),
        "--no-deps",
        str(artifact),
        cwd=tmp_path,
    )
    assert python.is_file()
    return InstalledDistribution(artifact=artifact, python=python)
