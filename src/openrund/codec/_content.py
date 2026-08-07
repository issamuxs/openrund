"""Canonical command Content commitments owned by the codec boundary."""

from __future__ import annotations

import hashlib

from openrund.codec._decisions import _encode_semantic_value
from openrund.codec._json import canonical_json_bytes
from openrund.contracts.content import Content
from openrund.errors import EncodeError


def canonical_content_bytes(content: Content) -> bytes:
    """Return the canonical v1 Content preimage without a trailing newline."""

    if not isinstance(content, Content):
        raise EncodeError(code="content_type_invalid")
    return canonical_json_bytes(_encode_semantic_value(content))


def canonical_content_hash(content: Content) -> str:
    """Return the lowercase SHA-256 commitment for canonical Content bytes."""

    return hashlib.sha256(canonical_content_bytes(content)).hexdigest()
