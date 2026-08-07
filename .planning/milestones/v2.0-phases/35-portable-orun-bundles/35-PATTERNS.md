# Phase 35 Pattern Map

| New responsibility | Closest Python analog | Reused pattern |
|---|---|---|
| Bundle semantic values | `contracts/portable.py`, `ports/events.py` | frozen, slotted, keyword-only dataclasses with strict validation |
| Wire parsing | `codec/_json.py`, `codec/_events.py` | bounded UTF-8 JSONL, duplicate-key rejection, explicit decode boundary |
| Portable paths | `paths.py`, `storage/_artifacts.py` | lexical portable validation plus `lstat` and no-follow filesystem checks |
| Hash commitments | `codec.canonical_json_bytes` | recursively sorted UTF-16-compatible canonical JSON and SHA-256 |
| Export custody | `storage/_artifacts.py` | stage, fsync, absent-only publication, immutable bytes |
| Replay | `views/_rebuild.py` | exact known-watermark reconstruction with no authority |
| Safe failures | `errors.py` | stable codes, JSON pointers, sanitized detail |
| Deterministic tests | `openrund._testing` | injected stores, clocks, identifiers, isolated local filesystem |

No implementation imports the executable compatibility tooling. Frozen evidence is consumed only through the authenticated fixture reader used by tests.
