from __future__ import annotations

from typing import Any

from verdict_protocol import EscrowClient


def submit_ruling(
    escrow: EscrowClient,
    dispute_id: int,
    verdict: dict[str, Any],
) -> dict[str, Any]:
    tx = escrow.submit_ruling(dispute_id, verdict)
    return {"txHash": tx.tx_hash, "status": tx.status, "blockNumber": tx.block_number}
