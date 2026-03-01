from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _normalize(value[k]) for k in sorted(value)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize(v) for v in value]
    if isinstance(value, float) and value.is_integer():
        # Normalize integral floats so 5 and 5.0 hash identically.
        return int(value)
    if isinstance(value, Decimal):
        return str(value)
    return value


def canonical_json_obj(value: Any) -> Any:
    """Return a recursively normalized JSON-compatible object with stable key ordering."""
    return _normalize(value)


def canonical_json_dumps(value: Any) -> str:
    """Serialize JSON with sorted keys and no insignificant whitespace."""
    normalized = canonical_json_obj(value)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_json_bytes(value: Any) -> bytes:
    return canonical_json_dumps(value).encode("utf-8")
