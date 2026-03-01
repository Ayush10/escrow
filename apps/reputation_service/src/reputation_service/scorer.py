from __future__ import annotations

SCORES = {
    "completed_without_dispute": 1,
    "won_dispute": 2,
    "lost_dispute": -5,
    "lost_as_filer": -3,
}


def to_did(address: str) -> str:
    if address.startswith("did:8004:"):
        return address
    return f"did:8004:{address}"
