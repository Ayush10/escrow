from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eth_utils import keccak, to_checksum_address
from web3 import Web3

DEFAULT_ABI_PATH = Path(__file__).resolve().parents[4] / "contracts" / "abi" / "Escrow.json"


@dataclass(slots=True)
class EscrowTxResult:
    tx_hash: str
    block_number: int | None = None
    status: int | None = None
    extra: dict[str, Any] | None = None


class EscrowClient:
    """Dual-compat escrow adapter over current and target contract ABIs."""

    def __init__(
        self,
        rpc_url: str,
        chain_id: int,
        contract_address: str,
        private_key: str | None = None,
        abi_path: str | Path | None = None,
        dry_run: bool = False,
    ) -> None:
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.chain_id = chain_id
        self.contract_address = to_checksum_address(contract_address)
        self.private_key = private_key
        self.account = self.w3.eth.account.from_key(private_key) if private_key else None
        self.dry_run = dry_run

        path = Path(abi_path) if abi_path else DEFAULT_ABI_PATH
        abi = json.loads(path.read_text(encoding="utf-8"))
        self.abi = abi
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=abi)

        self.fn_index = {f["name"]: f for f in abi if f.get("type") == "function"}
        self.event_index = {e["name"]: e for e in abi if e.get("type") == "event"}

    def capabilities(self) -> dict[str, bool]:
        return {
            "depositPool": "depositPool" in self.fn_index,
            "postBond": "postBond" in self.fn_index,
            "commitEvidenceHash": "commitEvidenceHash" in self.fn_index,
            "commitEvidence": "commitEvidence" in self.fn_index,
            "fileDispute": "fileDispute" in self.fn_index,
            "submitRuling": "submitRuling" in self.fn_index,
            "PayoutExecuted": "PayoutExecuted" in self.event_index,
        }

    def _send_tx(self, fn_call, *, value: int = 0) -> EscrowTxResult:
        if self.dry_run:
            return EscrowTxResult(tx_hash="0x" + "0" * 64, status=1)
        if not self.account:
            raise RuntimeError("private key required for state-changing transactions")

        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = fn_call.build_transaction(
            {
                "from": self.account.address,
                "nonce": nonce,
                "chainId": self.chain_id,
                "value": value,
                "gas": 700_000,
                "gasPrice": self.w3.eth.gas_price,
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        return EscrowTxResult(tx_hash=tx_hash.hex(), block_number=receipt.blockNumber, status=receipt.status)

    def deposit_pool(self, amount_wei: int) -> EscrowTxResult:
        if "depositPool" in self.fn_index:
            fn = self.contract.functions.depositPool(amount_wei)
            return self._send_tx(fn)
        if "deposit" in self.fn_index:
            fn = self.contract.functions.deposit()
            return self._send_tx(fn, value=amount_wei)
        raise RuntimeError("No compatible deposit function in ABI")

    def post_bond(self, agreement_id: str, amount_wei: int) -> EscrowTxResult:
        if "postBond" in self.fn_index:
            fn = self.contract.functions.postBond(agreement_id, amount_wei)
            return self._send_tx(fn)
        if "deposit" in self.fn_index:
            fn = self.contract.functions.deposit()
            return self._send_tx(fn, value=amount_wei)
        raise RuntimeError("No compatible post bond function in ABI")

    def commit_evidence_hash(self, agreement_id: str, root_hash: str) -> EscrowTxResult:
        if "commitEvidenceHash" in self.fn_index:
            fn = self.contract.functions.commitEvidenceHash(agreement_id, root_hash)
            return self._send_tx(fn)
        if "commitEvidence" in self.fn_index:
            tx_key = Web3.to_hex(keccak(text=agreement_id))
            fn = self.contract.functions.commitEvidence(tx_key, root_hash)
            return self._send_tx(fn)
        raise RuntimeError("No compatible evidence commit function in ABI")

    def file_dispute(
        self,
        agreement_id: str,
        *,
        defendant: str | None = None,
        stake: int | None = None,
        plaintiff_evidence: str | None = None,
    ) -> EscrowTxResult:
        _ = agreement_id
        if "fileDispute" not in self.fn_index:
            raise RuntimeError("No fileDispute function in ABI")

        inputs = self.fn_index["fileDispute"].get("inputs", [])
        if len(inputs) == 1:
            fn = self.contract.functions.fileDispute(agreement_id)
            return self._send_tx(fn)

        if len(inputs) >= 3 and inputs[0]["type"] == "address":
            if defendant is None or stake is None:
                raise ValueError("defendant and stake are required for this ABI")
            evidence = plaintiff_evidence or "0x" + "0" * 64
            fn = self.contract.functions.fileDispute(to_checksum_address(defendant), int(stake), evidence)
            return self._send_tx(fn)

        raise RuntimeError("Unsupported fileDispute ABI signature")

    def submit_ruling(self, dispute_id: int, verdict_data: dict[str, Any]) -> EscrowTxResult:
        if "submitRuling" not in self.fn_index:
            raise RuntimeError("No submitRuling function in ABI")

        inputs = self.fn_index["submitRuling"].get("inputs", [])
        if len(inputs) != 2:
            raise RuntimeError("Unsupported submitRuling ABI signature")

        second = inputs[1]["type"]
        if second == "address":
            winner = _winner_from_verdict(verdict_data)
            fn = self.contract.functions.submitRuling(int(dispute_id), to_checksum_address(winner))
            return self._send_tx(fn)

        if second in {"bytes", "string"}:
            encoded = json.dumps(verdict_data, separators=(",", ":"))
            fn = self.contract.functions.submitRuling(int(dispute_id), encoded)
            return self._send_tx(fn)

        raise RuntimeError("Unsupported submitRuling second parameter type")

    def get_dispute(self, dispute_id: int) -> Any:
        if "getDispute" not in self.fn_index:
            return None
        return self.contract.functions.getDispute(dispute_id).call()

    def judge_address(self) -> str | None:
        if "judge" not in self.fn_index:
            return None
        return to_checksum_address(self.contract.functions.judge().call())

    def poll_events(self, event_name: str, from_block: int, to_block: int | str = "latest") -> list[dict[str, Any]]:
        if event_name not in self.event_index:
            return []
        event_obj = getattr(self.contract.events, event_name)
        flt = event_obj.create_filter(from_block=from_block, to_block=to_block)
        return [dict(log) for log in flt.get_all_entries()]


def _winner_from_verdict(verdict_data: dict[str, Any]) -> str:
    if "winner" in verdict_data:
        return verdict_data["winner"]

    transfers = verdict_data.get("transfers", [])
    if not transfers:
        raise ValueError("verdict_data must include winner or transfers")

    sorted_transfers = sorted(transfers, key=lambda t: int(t.get("amount", "0")), reverse=True)
    return sorted_transfers[0]["to"]
