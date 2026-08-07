from __future__ import annotations

from pathlib import Path
from typing import Final

import pytest
from pytest import TempPathFactory
from tests.package._distributions import BuiltDistributions, build_distributions

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def built_distributions(tmp_path_factory: TempPathFactory) -> BuiltDistributions:
    output_directory = tmp_path_factory.mktemp("built-distributions")
    return build_distributions(PROJECT_ROOT, output_directory)
