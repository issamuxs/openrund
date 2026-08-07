# Phase 35 Research

## Existing contracts

- Canonical Events already encode and decode at one strict codec boundary.
- `EventStore.read()` yields one ordered, gap-free Run stream and `ArtifactStore` yields immutable metadata and verified bytes.
- `rebuild_views()` rejects incomplete history and produces all operator-facing projections and Reports at a known watermark.
- The frozen corpus records the exact schema-1 manifests, profile file tables, Event-chain heads, bundle commitments, Artifact inclusion rules, and timestamp spelling.

## Implementation guidance

1. Keep schema-1 hashes mechanically compatible while strengthening verification around them. Hashing compatibility does not require reproducing unsafe filesystem behavior.
2. Build all non-manifest payloads in a staging tree, compute exact file commitments, then write `manifest.json` last and publish the directory atomically.
3. Treat the manifest as untrusted twice: parse exact shapes and values, then compare every semantic claim against verified files and decoded Events.
4. Require the file tree to equal the manifest-declared tree plus `manifest.json`; otherwise an attacker can smuggle undeclared content into imports.
5. Import from already verified bytes into a fresh staging directory and verify the staged copy again before rename.
6. Derive resume issues deterministically in manifest order with deduplication; never infer availability from ambient credentials or grant state.

## Principal failure modes

- traversal, absolute paths, Windows drive syntax, NULs, and backslash confusion;
- symlink substitution and special-file reads;
- unsupported schema or compatibility versions and unknown critical fields;
- Run identity mismatch, Event gaps, wrong counts, and malformed canonical Events;
- missing, extra, duplicated, or conflicting Artifact declarations;
- file length/hash mismatch, Event-chain mismatch, or Bundle commitment mismatch;
- partial import publication or collision with existing custody;
- resume requirements omitted from the manifest or silently satisfied by import.
