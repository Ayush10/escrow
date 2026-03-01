from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from eth_utils import keccak, to_hex

from .canonical_json import canonical_json_bytes


def keccak_hex(data: bytes) -> str:
    return to_hex(keccak(data))


def hash_canonical(value: Any) -> str:
    return keccak_hex(canonical_json_bytes(value))


def _without_fields(value: dict[str, Any], skip: set[str]) -> dict[str, Any]:
    return {k: v for k, v in value.items() if k not in skip}


def compute_clause_hash(clause: dict[str, Any]) -> str:
    return hash_canonical(_without_fields(clause, {"clauseHash"}))


def compute_receipt_hash(receipt: dict[str, Any]) -> str:
    return hash_canonical(_without_fields(receipt, {"receiptHash", "signature"}))


def compute_verdict_hash(verdict: dict[str, Any]) -> str:
    return hash_canonical(_without_fields(verdict, {"verdictHash", "judgeSignature"}))


def merkle_root_hash(leaves: Iterable[str]) -> str:
    current = list(leaves)
    if not current:
        return "0x0"

    current_bytes = [bytes.fromhex(v[2:] if v.startswith("0x") else v) for v in current]

    while len(current_bytes) > 1:
        nxt: list[bytes] = []
        for i in range(0, len(current_bytes), 2):
            left = current_bytes[i]
            right = current_bytes[i + 1] if i + 1 < len(current_bytes) else left
            nxt.append(keccak(left + right))
        current_bytes = nxt

    return to_hex(current_bytes[0])
