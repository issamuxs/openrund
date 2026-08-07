"""Run OpenRund's production local-assembly workflow through the Python API."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from openrund.demo import run_governed_coding_demo
from openrund.operator import render_operator_json
from openrund.storage import default_openrund_home


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path, nargs="?")
    parser.add_argument("--home", type=Path, default=default_openrund_home())
    return parser.parse_args()


def main() -> int:
    arguments = _arguments()
    result = asyncio.run(
        run_governed_coding_demo(
            runtime_home=arguments.home,
            workspace=arguments.workspace,
        )
    )
    print(render_operator_json(result))
    return int(result.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
