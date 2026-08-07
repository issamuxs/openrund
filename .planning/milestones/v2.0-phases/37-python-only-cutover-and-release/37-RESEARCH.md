# Phase 37 Research — Python-Only Cutover and Release

## Current release surface

The Python package already has a `src/` layout, `py.typed`, a console entry
point, zero base dependencies, strict tests, and isolated wheel coverage. Its
metadata is intentionally provisional at version `0.0.0`, Bundle exports embed
that provisional value, and release/coverage configuration is not complete.

## Remaining live non-Python inventory

The tracked cutover set contains:

- the root package-manager, workspace, compiler, and test-runner files;
- 118 files under the former package workspace;
- 9 executable hygiene and compatibility-oracle scripts;
- 39 non-Python tests;
- 7 files in a duplicate separately packaged document worker;
- 6 files in the former public example;
- 15 archived documents describing an implementation that must not appear in
  the greenfield product documentation.

Ignored dependency/build residues include `node_modules/` and `.pnpm-store/`.
They are not Git history and must be removed after exact path and symlink
inspection. Normal Python caches remain ignored development artifacts.

## Compatibility retirement

`tests/fixtures/compatibility/v1/` is immutable data. Python tests authenticate
manifest paths, lengths, SHA-256 commitments, semantic meaning, Event bytes,
provider normalization, SQLite schema behavior, Views, Artifacts, and all three
Bundle profiles without invoking an executable oracle. The manifest also seals
RET-01 through RET-10 retirement evidence. This data remains; generators,
verifiers, package commands, and non-Python tests do not.

Before deletion, the release gate must prove:

1. Python reads every frozen contract and Bundle profile.
2. Python writes canonical Events and Bundles accepted by the sealed contract.
3. SQLite, Artifact, View, provider, and rejection matrices pass.
4. Wheel and sdist install without source-tree access.
5. The installed console runs the flagship workflow.
6. Python 3.12, 3.13, and 3.14 pass the supported matrix.

## Packaging posture

Use PEP 517/518/621 metadata through hatchling, dynamic version loading from a
small private Python module, `README.md` as package description, explicit
Python classifiers, a dependency-free base, and a targeted test extra. Do not
invent a license or project URL without owner direction. Distribution content
must be allowlisted and tested from both wheel and sdist.

## Quality posture

Use `coverage.py` with branch coverage and a repository threshold after
measuring the complete suite. Keep pytest, strict mypy, Ruff lint/format,
lockfile, docs/link, package-content, security, installed-demo, and clean-build
gates independent so failures are attributable. Live-provider checks remain
opt-in because network and credentials are explicit boundaries.

## Documentation posture

All live docs present OpenRund as a Python project. Remove historical product
docs from `docs/`; Git and milestone archives retain provenance. Replace the
example with Python library and installed-command examples. OpenRund has no
graphical interface, so CLI work remains normal implementation and test work.
