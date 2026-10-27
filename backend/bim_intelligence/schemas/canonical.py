"""Canonical JSON and content hashing.

Determinism (NFR-01) is tested as byte equality of ``findings.json``, so there must be exactly
one serialisation of any value: sorted keys, two-space indent, UTF-8, trailing newline. The
same canonical form, compacted, feeds the content hashes used for ``CheckSpec.id`` and
``Finding.id`` so that identity never depends on dictionary insertion order.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

CONTENT_HASH_LENGTH = 16


def canonical_json(value: Any) -> str:
    """Pretty, key-sorted JSON with a trailing newline; the on-disk form."""
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def compact_canonical_json(value: Any) -> str:
    """Key-sorted JSON without whitespace; the hashing form."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(*parts: str) -> str:
    """First 16 hex characters of SHA-1 over ``"|".join(parts)``.

    SHA-1 is used as a fast, stable content address (C-03), not as a security primitive.
    """
    material = "|".join(parts).encode("utf-8")
    return hashlib.sha1(material, usedforsecurity=False).hexdigest()[:CONTENT_HASH_LENGTH]
