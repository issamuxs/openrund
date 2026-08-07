# Phase 37 Patterns

| Concern | Existing Python pattern | Cutover use |
|---|---|---|
| Package metadata | `pyproject.toml` with hatchling and `src/` layout | Complete PEP metadata and dynamic release version |
| Public API | Exact `openrund.__all__` allowlist | Prevent release metadata from expanding semantics accidentally |
| Installed validation | Build wheel, create isolated venv, remove source path | Validate typing, imports, console, and demo |
| Compatibility | Authenticated `CorpusEntry` loader | Preserve inert fixtures without an executable generator |
| Bundle portability | Frozen-profile read plus current export/verify/import | Qualify retirement and release |
| Architecture fences | AST/import/path hygiene tests | Prohibit a returning dual implementation or second authority |
| Documentation | Python link and sentinel tests | Enforce greenfield live docs and current commands |
| Determinism | Injected clocks/IDs/transports | Keep release/demo evidence reproducible |

## Deletion rule

Delete only enumerated tracked paths. Inspect ignored dependency directories,
their target type, and every symlink before recursive cleanup; remove no Python
source, frozen fixture, planning archive, or Git history.
