"""Installed `openrund` console entry point."""

from __future__ import annotations

import asyncio
import sys

from openrund.cli import run_cli_process


def main() -> int:
    result = asyncio.run(run_cli_process(tuple(sys.argv[1:])))
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
