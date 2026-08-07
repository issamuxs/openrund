---
phase: 35-portable-orun-bundles
created: 2026-08-06
source: autonomous-context
discuss_skipped: true
---

# Phase 35 Context

## Goal

Move, verify, replay, and stage governed Run evidence without hidden local state or accidental authorization.

## Locked Decisions

- Bundle schema 1, Event grammar 1, View schema 1, policy manifest 1, and capability manifest 1 remain the supported compatibility contract.
- `complete`, `audit`, and `redacted` are explicit profiles. Only `complete` includes available Artifact bytes.
- Event JSONL preserves canonical encoder construction order and one final LF. Event-chain and bundle commitments use the approved canonical JSON hash rules.
- Verification is fail-closed and precedes replay or import. It rejects extra files as well as missing, malformed, inconsistent, linked, or uncommitted files.
- Every manifest path is portable, relative, normalized POSIX syntax and resolved with `lstat` containment checks. Symlinks are forbidden anywhere in a verified or imported Bundle tree.
- Replay is explanatory and appends no Events.
- Import stages into a sibling temporary directory, fsyncs material, and publishes with an absent-only atomic rename. It never overwrites an existing import.
- `ResumeAssessment` is immutable diagnostic data. It does not grant Authority, bind roots, or resume a Run.
- Required providers, capabilities, policy key, root mappings, pending Waits, and unavailable Artifacts are declared explicitly by the Python writer.
- CLI interaction is ordinary Phase 36 plan/test work. No graphical UI artifact applies.

## Scope

- Typed Bundle manifests, results, verification checks, imports, and resume assessments.
- Compatibility hashing and deterministic JSON/JSONL emission.
- Complete/audit/redacted export with Events, Artifacts, Views, Reports, policy, capabilities, providers, and resume requirements.
- Strict verification, semantic replay, authenticated frozen-profile cross-read, atomic stage-import, and resumability diagnostics.

## Out of Scope

- Automatic resume or implicit Authority grants.
- Compression, encryption, signing, remote object storage, or archive extraction.
- CLI commands and assembly wiring.
