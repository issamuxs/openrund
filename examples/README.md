# OpenRund examples

The examples exercise the same Python API and installed command that operators
use in production. They require no network access or provider credentials.

## Python API

Run the production local-assembly governed-coding workflow from a repository
checkout:

```sh
uv run python examples/governed_coding.py
```

The script prints the canonical JSON result and exits with the operator result
code. It uses the generated Run's default workspace unless a path is supplied;
`--home` can independently override private runtime custody. Its implementation
is in [`governed_coding.py`](./governed_coding.py).

## Installed command

After installing OpenRund, run the equivalent console flow directly:

```sh
openrund demo governed-coding
```

Interactive text execution proposes the per-Run workspace. For automation,
add `--json` to accept that default without prompting or append an explicit
workspace path.

Both forms create a local Git repository, generate fresh production runtime
identities and timestamps, exercise the built-in capabilities, complete the
governed Run, and verify the exported `.orun` Bundle.
