# Bundles

An `.orun` Bundle is an immutable portable directory containing replayable Run
evidence. It transports history and explanatory surfaces; it never grants
Authority, appends Events, or resumes a Run.

## Layout

Schema 1 uses this fixed layout:

```text
manifest.json
events.jsonl
artifacts/
views/summary.json
policy/snapshot.json
capabilities/manifest.json
exports/runtime-audit.json
exports/runtime-audit.md
exports/action-receipts/
```

Check Reports add `exports/check.json` and `exports/check.md`. Available
Artifact bytes use `artifacts/<artifact-id>.bin` in the `complete` profile.
The `audit` and `redacted` profiles preserve Artifact metadata and explicit
omission reasons without including those bytes.

`manifest.json` records the source Run, exact compatibility versions, profile,
file SHA-256 commitments, Event-chain head and count, Bundle commitment,
derived status and watermark, capability and provider requirements, policy
key, Reports, Artifact availability, pending Waits, required root mappings,
and every condition relevant to resume assessment.

## Python API

```python
from pathlib import Path

from openrund.bundles import (
    assess_resume,
    export_bundle,
    import_bundle,
    replay_bundle,
    verify_bundle,
)
from openrund.contracts.portable import BundleProfile
from openrund.contracts.time import Timestamp

exported = await export_bundle(
    run_id=run_id,
    output_path=Path("exports/run.orun"),
    event_store=event_store,
    artifact_store=artifact_store,
    profile=BundleProfile.COMPLETE,
    exported_at=Timestamp(value="2026-08-06T12:00:00.000Z"),
    required_providers=("local",),
)

verified = verify_bundle(exported.bundle_path)
replayed = replay_bundle(exported.bundle_path)

imported = import_bundle(
    exported.bundle_path,
    runtime_home=Path("runtime-home"),
    root_mappings={"workspace": Path("/absolute/workspace")},
    imported_at=Timestamp(value="2026-08-06T12:01:00.000Z"),
)

assessment = assess_resume(
    imported,
    available_capabilities=("filesystem", "process", "git", "documents"),
    available_providers=("local",),
    supported_policy_key=imported.manifest.policy.key,
)
```

The export time is explicit. This keeps export deterministic and makes time an
auditable host input rather than ambient process state.

## Integrity

`events.jsonl` contains canonical Event frames in position order with one LF
per frame. File commitments hash exact bytes. Event integrity starts with the
SHA-256 of empty bytes, then hashes canonical JSON containing the previous head
and the raw Event frame. The Bundle commitment hashes the profile, source Run,
compatibility block, Event commitment, and complete non-manifest file table.

Verification rejects:

- unsupported schemas, compatibility versions, layouts, or critical fields;
- malformed or duplicate-key JSON;
- absolute, traversing, platform-confused, or NUL-containing paths;
- symlinks, special files, unsafe ancestors, undeclared files, or extra
  directories;
- missing files, incorrect lengths or SHA-256 values, Event-chain drift, or
  Bundle commitment drift;
- Run identity mismatch, Event gaps, duplicate Event IDs, invalid counts, or
  incomplete replay;
- View, Wait, policy, capability, provider, Report, Artifact, or resume
  declarations that disagree with verified history and files.

Verification is required before replay and import. Replay rebuilds Views from
verified canonical Events and performs no write.

## Profiles

- `complete` includes every available Artifact byte.
- `audit` omits Artifact bytes while retaining hashes and profile omission
  evidence.
- `redacted` omits Artifact bytes with explicit redaction evidence.

If available bytes cannot be included, the Bundle is partial and identifies
the excluded Artifact in both completeness and resume metadata. An Artifact
already marked unavailable remains explicit rather than disappearing.

## Import And Resumability

Import verifies the source, requires explicit absolute root mappings, copies
only committed regular files with no-follow reads, verifies the staged copy,
writes `import.json`, and atomically publishes a new absent-only import. It does
not overwrite an existing import.

`assess_resume()` reports deterministic blocking issues for partial Bundles,
missing root mappings, missing capabilities or providers, incompatible policy,
unsupported pending Waits, unavailable Artifacts, and terminal Runs. Compatible
capability and policy mappings must be supplied explicitly. The assessment is
diagnostic data only: it cannot grant Authority, bind resources, or resume
execution.
