from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eth_utils import keccak, to_checksum_address
from web3 import Web3

DEFAULT_ABI_PATH = Path(__file__).resolve().parents[4] / "contracts" / "abi" / "AgentCourt.json"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


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
        self.connected = self.w3.is_connected()

        path = Path(abi_path) if abi_path else DEFAULT_ABI_PATH
        abi = json.loads(path.read_text(encoding="utf-8"))
        self.abi = abi
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=abi)
        code = self.w3.eth.get_code(self.contract_address)
        self.contract_code_size = len(code)
        self.contract_has_code = self.contract_code_size > 0

        self.fn_index = {f["name"]: f for f in abi if f.get("type") == "function"}
        self.event_index = {e["name"]: e for e in abi if e.get("type") == "event"}

        self._mock_conn: sqlite3.Connection | None = None
        if self.dry_run:
            self._init_mock_db()

    def _init_mock_db(self) -> None:
        db_path = Path(os.environ.get("ESCROW_MOCK_DB_PATH", "./data/escrow_mock.db"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._mock_conn = sqlite3.connect(db_path, check_same_thread=False)
        self._mock_conn.row_factory = sqlite3.Row
        self._mock_conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS counters (
              key TEXT PRIMARY KEY,
              value INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              event_name TEXT NOT NULL,
              block_number INTEGER NOT NULL,
              tx_hash TEXT NOT NULL,
              args_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS disputes (
              dispute_id INTEGER PRIMARY KEY,
              dispute_json TEXT NOT NULL
            );
            """
        )
        block_start = self._mock_block_start()
        row = self._mock_conn.execute(
            "SELECT value FROM counters WHERE key = ?",
            ("block",),
        ).fetchone()
        if row is None:
            self._mock_conn.execute(
                "INSERT INTO counters (key, value) VALUES (?, ?)",
                ("block", block_start),
            )
        elif int(row["value"]) < block_start:
            self._mock_conn.execute(
                "UPDATE counters SET value = ? WHERE key = ?",
                (block_start, "block"),
            )
        self._mock_conn.commit()

    def _mock_block_start(self) -> int:
        try:
            if self.connected:
                return int(self.w3.eth.block_number)
        except Exception:
            pass
        return int(time.time())

    def _mock_next_counter(self, key: str, start: int = 1) -> int:
        if self._mock_conn is None:
            raise RuntimeError("mock db is not initialized")
        row = self._mock_conn.execute(
            "SELECT value FROM counters WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            value = int(start)
            self._mock_conn.execute(
                "INSERT INTO counters (key, value) VALUES (?, ?)",
                (key, value),
            )
        else:
            value = int(row["value"]) + 1
            self._mock_conn.execute(
                "UPDATE counters SET value = ? WHERE key = ?",
                (value, key),
            )
        self._mock_conn.commit()
        return value

    def _mock_tx_hash(self, label: str) -> str:
        seed = f"{label}:{time.time_ns()}:{os.getpid()}"
        return Web3.to_hex(Web3.keccak(text=seed))

    def _mock_emit_event(
        self,
        event_name: str,
        args: dict[str, Any],
        *,
        tx_hash: str,
        block_number: int | None = None,
    ) -> None:
        if self._mock_conn is None:
            raise RuntimeError("mock db is not initialized")
        block = (
            int(block_number)
            if block_number is not None
            else self._mock_next_counter("block", start=self._mock_block_start())
        )
        self._mock_conn.execute(
            """
            INSERT INTO events (event_name, block_number, tx_hash, args_json)
            VALUES (?, ?, ?, ?)
            """,
            (event_name, block, tx_hash, json.dumps(args, separators=(",", ":"))),
        )
        self._mock_conn.commit()

    def _mock_put_dispute(self, dispute_id: int, dispute_data: list[Any]) -> None:
        if self._mock_conn is None:
            raise RuntimeError("mock db is not initialized")
        self._mock_conn.execute(
            """
            INSERT OR REPLACE INTO disputes (dispute_id, dispute_json)
            VALUES (?, ?)
            """,
            (int(dispute_id), json.dumps(dispute_data, separators=(",", ":"))),
        )
        self._mock_conn.commit()

    def _mock_get_dispute(self, dispute_id: int) -> list[Any] | None:
        if self._mock_conn is None:
            return None
        row = self._mock_conn.execute(
            "SELECT dispute_json FROM disputes WHERE dispute_id = ?",
            (int(dispute_id),),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["dispute_json"])

    def capabilities(self) -> dict[str, bool]:
        return {
            "rpcConnected": self.connected,
            "contractHasCode": self.contract_has_code,
            "depositPool": "depositPool" in self.fn_index,
            "postBond": "postBond" in self.fn_index,
            "commitEvidenceHash": "commitEvidenceHash" in self.fn_index,
            "commitEvidence": "commitEvidence" in self.fn_index,
            "fileDispute": "fileDispute" in self.fn_index,
            "submitRuling": "submitRuling" in self.fn_index,
            "PayoutExecuted": "PayoutExecuted" in self.event_index,
        }

    def contract_sanity(self) -> dict[str, Any]:
        return {
            "rpcConnected": self.connected,
            "contractAddress": self.contract_address,
            "contractHasCode": self.contract_has_code,
            "contractCodeSize": self.contract_code_size,
            "dryRun": self.dry_run,
        }

    def _send_tx(self, fn_call, *, value: int = 0) -> EscrowTxResult:
        if self.dry_run:
            block = self._mock_next_counter("block", start=self._mock_block_start())
            return EscrowTxResult(tx_hash=self._mock_tx_hash("dry-run-tx"), status=1, block_number=block)
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
            inputs = self.fn_index["deposit"].get("inputs", [])
            if inputs and inputs[0]["type"] == "uint256":
                # USDC version: deposit(uint256 amount) — ERC-20 transferFrom
                fn = self.contract.functions.deposit(amount_wei)
                return self._send_tx(fn)
            else:
                # Native BTC version: deposit() payable
                fn = self.contract.functions.deposit()
                return self._send_tx(fn, value=amount_wei)
        raise RuntimeError("No compatible deposit function in ABI")

    def post_bond(self, agreement_id: str, amount_wei: int) -> EscrowTxResult:
        if "postBond" in self.fn_index:
            fn = self.contract.functions.postBond(agreement_id, amount_wei)
            return self._send_tx(fn)
        if "deposit" in self.fn_index:
            inputs = self.fn_index["deposit"].get("inputs", [])
            if inputs and inputs[0]["type"] == "uint256":
                fn = self.contract.functions.deposit(amount_wei)
                return self._send_tx(fn)
            else:
                fn = self.contract.functions.deposit()
                return self._send_tx(fn, value=amount_wei)
        raise RuntimeError("No compatible post bond function in ABI")

    def commit_evidence_hash(self, agreement_id: str, root_hash: str) -> EscrowTxResult:
        if self.dry_run:
            tx_hash = self._mock_tx_hash("commit-evidence")
            block = self._mock_next_counter("block", start=self._mock_block_start())
            agent = self.account.address if self.account else ZERO_ADDRESS
            self._mock_emit_event(
                "EvidenceCommitted",
                {
                    "agreementId": agreement_id,
                    "rootHash": root_hash,
                    "agent": to_checksum_address(agent),
                },
                tx_hash=tx_hash,
                block_number=block,
            )
            return EscrowTxResult(tx_hash=tx_hash, block_number=block, status=1)

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
        tx_id: int | None = None,
        defendant: str | None = None,
        stake: int | None = None,
        plaintiff_evidence: str | None = None,
    ) -> EscrowTxResult:
        if "fileDispute" not in self.fn_index:
            raise RuntimeError("No fileDispute function in ABI")

        if self.dry_run:
            fallback_evidence = "0x" + "0" * 64
            evidence = plaintiff_evidence or fallback_evidence
            normalized_stake = int(stake or 0)
            normalized_tx_id = int(
                tx_id if tx_id is not None else int(Web3.keccak(text=agreement_id).hex(), 16) % (2**63 - 1)
            )
            plaintiff = to_checksum_address(self.account.address) if self.account else ZERO_ADDRESS
            defendant_addr = to_checksum_address(defendant) if defendant else ZERO_ADDRESS
            dispute_id = self._mock_next_counter("dispute_id", start=1)
            judge_fee = max(normalized_stake // 200, 0)
            dispute_row = [
                normalized_tx_id,
                plaintiff,
                defendant_addr,
                normalized_stake,
                judge_fee,
                0,
                evidence,
                "0x" + "0" * 64,
                False,
                ZERO_ADDRESS,
            ]
            self._mock_put_dispute(dispute_id, dispute_row)

            tx_hash = self._mock_tx_hash("file-dispute")
            block = self._mock_next_counter("block", start=self._mock_block_start())
            self._mock_emit_event(
                "DisputeFiled",
                {
                    "disputeId": dispute_id,
                    "plaintiff": plaintiff,
                    "defendant": defendant_addr,
                },
                tx_hash=tx_hash,
                block_number=block,
            )
            return EscrowTxResult(
                tx_hash=tx_hash,
                block_number=block,
                status=1,
                extra={"disputeId": dispute_id},
            )

        inputs = self.fn_index["fileDispute"].get("inputs", [])
        evidence = plaintiff_evidence or "0x" + "0" * 64

        # Our contract: fileDispute(uint256 txId, uint256 stake, bytes32 evidence)
        if len(inputs) >= 3 and inputs[0]["type"] == "uint256" and inputs[0]["name"] == "txId":
            if tx_id is None:
                if self.dry_run:
                    # Deterministic fallback for dry-run / demo flows where txId is not yet
                    # available at this abstraction layer.
                    tx_id = int(Web3.keccak(text=agreement_id).hex(), 16)
                else:
                    raise ValueError("tx_id and stake are required for this ABI in live mode")
            if stake is None:
                if self.dry_run:
                    stake = 0
                else:
                    raise ValueError("tx_id and stake are required for this ABI in live mode")
            fn = self.contract.functions.fileDispute(int(tx_id), int(stake), evidence)
            return self._send_tx(fn)

        # Legacy: fileDispute(address defendant, uint256 stake, bytes32 evidence)
        if len(inputs) >= 3 and inputs[0]["type"] == "address":
            if defendant is None or stake is None:
                raise ValueError("defendant and stake are required for this ABI")
            fn = self.contract.functions.fileDispute(to_checksum_address(defendant), int(stake), evidence)
            return self._send_tx(fn)

        if len(inputs) == 1:
            fn = self.contract.functions.fileDispute(agreement_id)
            return self._send_tx(fn)

        raise RuntimeError("Unsupported fileDispute ABI signature")

    def submit_ruling(self, dispute_id: int, verdict_data: dict[str, Any]) -> EscrowTxResult:
        if "submitRuling" not in self.fn_index:
            raise RuntimeError("No submitRuling function in ABI")

        if self.dry_run:
            winner = to_checksum_address(_winner_from_verdict(verdict_data))
            dispute = self._mock_get_dispute(dispute_id) or self.get_dispute(dispute_id)
            loser = ZERO_ADDRESS
            if dispute:
                if len(dispute) >= 10:
                    plaintiff = to_checksum_address(dispute[1])
                    defendant = to_checksum_address(dispute[2])
                    loser = defendant if winner.lower() == plaintiff.lower() else plaintiff
                    dispute[8] = True
                    dispute[9] = winner
                else:
                    plaintiff = to_checksum_address(dispute[0])
                    defendant = to_checksum_address(dispute[1])
                    loser = defendant if winner.lower() == plaintiff.lower() else plaintiff
                self._mock_put_dispute(int(dispute_id), dispute)

            tx_hash = self._mock_tx_hash("submit-ruling")
            block = self._mock_next_counter("block", start=self._mock_block_start())
            self._mock_emit_event(
                "RulingSubmitted",
                {
                    "disputeId": int(dispute_id),
                    "winner": winner,
                    "loser": loser,
                },
                tx_hash=tx_hash,
                block_number=block,
            )
            return EscrowTxResult(tx_hash=tx_hash, block_number=block, status=1)

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
        if self.dry_run:
            mock_dispute = self._mock_get_dispute(dispute_id)
            if mock_dispute is not None:
                return mock_dispute
        if "getDispute" not in self.fn_index:
            return None
        return self.contract.functions.getDispute(dispute_id).call()

    def judge_address(self) -> str | None:
        if "judge" not in self.fn_index:
            return None
        return to_checksum_address(self.contract.functions.judge().call())

    def poll_events(self, event_name: str, from_block: int, to_block: int | str = "latest") -> list[dict[str, Any]]:
        if self.dry_run:
            if self._mock_conn is None:
                return []
            to_block_num = int(2**63 - 1) if to_block == "latest" else int(to_block)
            rows = self._mock_conn.execute(
                """
                SELECT block_number, tx_hash, args_json
                FROM events
                WHERE event_name = ?
                  AND block_number >= ?
                  AND block_number <= ?
                ORDER BY block_number ASC, id ASC
                """,
                (event_name, int(from_block), to_block_num),
            ).fetchall()
            return [
                {
                    "args": json.loads(row["args_json"]),
                    "blockNumber": int(row["block_number"]),
                    "transactionHash": row["tx_hash"],
                }
                for row in rows
            ]

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
