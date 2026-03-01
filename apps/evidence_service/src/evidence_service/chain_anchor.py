from __future__ import annotations

from verdict_protocol import merkle_root_hash


def compute_anchor_root(receipt_hashes: list[str]) -> str:
    return merkle_root_hash(receipt_hashes)
