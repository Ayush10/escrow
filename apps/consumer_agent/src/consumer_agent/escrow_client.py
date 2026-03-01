from __future__ import annotations

import os

from verdict_protocol import EscrowClient


def build_client(private_key: str | None = None, *, dry_run: bool | None = None) -> EscrowClient:
    if dry_run is None:
        dry_run = os.environ.get("ESCROW_DRY_RUN", "0") == "1"

    return EscrowClient(
        rpc_url=os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network"),
        chain_id=int(os.environ.get("GOAT_CHAIN_ID", "48816")),
        contract_address=os.environ.get(
            "ESCROW_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"
        ),
        private_key=private_key,
        dry_run=dry_run,
    )
