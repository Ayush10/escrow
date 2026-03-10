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

SPLIT_COURT_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "nextContractId",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "uint256"}],
    },
    {
        "type": "function",
        "name": "propose",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "principal", "type": "address"},
            {"name": "client", "type": "address"},
            {"name": "judge", "type": "address"},
            {"name": "consideration", "type": "uint256"},
            {"name": "termsHash", "type": "bytes32"},
        ],
        "outputs": [{"type": "uint256"}],
    },
    {
        "type": "function",
        "name": "accept",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "id", "type": "uint256"}],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "complete",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "id", "type": "uint256"}],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "dispute",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "id", "type": "uint256"}],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "submitEvidence",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "id", "type": "uint256"}, {"name": "evidenceHash", "type": "bytes32"}],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "rule",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "id", "type": "uint256"},
            {"name": "winner", "type": "address"},
            {"name": "rulingHash", "type": "bytes32"},
        ],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "contracts",
        "stateMutability": "view",
        "inputs": [{"name": "", "type": "uint256"}],
        "outputs": [
            {"type": "address"},
            {"type": "address"},
            {"type": "address"},
            {"type": "uint256"},
            {"type": "uint256"},
            {"type": "bytes32"},
            {"type": "address"},
            {"type": "uint256"},
            {"type": "address"},
            {"type": "uint8"},
            {"type": "uint256"},
            {"type": "uint256"},
            {"type": "uint256"},
            {"type": "uint256"},
            {"type": "uint256"},
        ],
    },
    {
        "type": "function",
        "name": "disputes",
        "stateMutability": "view",
        "inputs": [{"name": "", "type": "uint256"}],
        "outputs": [
            {"type": "address"},
            {"type": "address"},
            {"type": "address"},
            {"type": "address"},
            {"type": "uint256"},
            {"type": "uint256"},
            {"type": "bytes32"},
        ],
    },
    {
        "type": "function",
        "name": "evidenceCount",
        "stateMutability": "view",
        "inputs": [{"name": "id", "type": "uint256"}],
        "outputs": [{"type": "uint256"}],
    },
    {
        "type": "function",
        "name": "evidenceHashes",
        "stateMutability": "view",
        "inputs": [{"name": "", "type": "uint256"}, {"name": "", "type": "uint256"}],
        "outputs": [{"type": "bytes32"}],
    },
    {
        "type": "function",
        "name": "evidenceSubmitters",
        "stateMutability": "view",
        "inputs": [{"name": "", "type": "uint256"}, {"name": "", "type": "uint256"}],
        "outputs": [{"type": "address"}],
    },
    {
        "type": "event",
        "name": "DisputeFiled",
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "id", "type": "uint256"},
            {"indexed": True, "name": "plaintiff", "type": "address"},
        ],
    },
    {
        "type": "event",
        "name": "Ruled",
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "id", "type": "uint256"},
            {"indexed": True, "name": "winner", "type": "address"},
            {"indexed": True, "name": "judge", "type": "address"},
            {"indexed": False, "name": "rulingHash", "type": "bytes32"},
        ],
    },
]

SPLIT_VAULT_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "usdc",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "address"}],
    },
    {
        "type": "function",
        "name": "deposit",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "amount", "type": "uint256"}],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "moveToBond",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "amount", "type": "uint256"}],
        "outputs": [],
    },
]

SPLIT_REGISTRY_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "judges",
        "stateMutability": "view",
        "inputs": [{"name": "", "type": "address"}],
        "outputs": [
            {"type": "address"},
            {"type": "uint256"},
            {"type": "uint256"},
            {"type": "uint8"},
            {"type": "bool"},
            {"type": "bool"},
            {"type": "string"},
            {"type": "uint256"},
        ],
    },
    {
        "type": "function",
        "name": "canRule",
        "stateMutability": "view",
        "inputs": [{"name": "judge", "type": "address"}],
        "outputs": [{"type": "bool"}],
    },
    {
        "type": "function",
        "name": "chainFeeSum",
        "stateMutability": "view",
        "inputs": [{"name": "judge", "type": "address"}],
        "outputs": [{"type": "uint256"}],
    },
    {
        "type": "function",
        "name": "registerJudge",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "superior", "type": "address"},
            {"name": "fee", "type": "uint256"},
            {"name": "endpoint", "type": "string"},
            {"name": "maxResponseTime", "type": "uint256"},
        ],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "topUpBond",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "amount", "type": "uint256"}],
        "outputs": [],
    },
]

SPLIT_EVIDENCE_ANCHOR_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "commitEvidence",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "agreementId", "type": "string"},
            {"name": "rootHash", "type": "bytes32"},
            {"name": "bundleHash", "type": "bytes32"},
            {"name": "bundleCid", "type": "string"},
        ],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "getAnchor",
        "stateMutability": "view",
        "inputs": [{"name": "agreementId", "type": "string"}],
        "outputs": [
            {"type": "bytes32"},
            {"type": "bytes32"},
            {"type": "string"},
            {"type": "address"},
            {"type": "uint256"},
        ],
    },
    {
        "type": "event",
        "name": "EvidenceCommitted",
        "anonymous": False,
        "inputs": [
            {"indexed": False, "name": "agreementId", "type": "string"},
            {"indexed": True, "name": "rootHash", "type": "bytes32"},
            {"indexed": True, "name": "bundleHash", "type": "bytes32"},
            {"indexed": False, "name": "bundleCid", "type": "string"},
            {"indexed": True, "name": "submitter", "type": "address"},
        ],
    },
]

SPLIT_ERC20_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "allowance",
        "stateMutability": "view",
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "outputs": [{"type": "uint256"}],
    },
    {
        "type": "function",
        "name": "approve",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"type": "bool"}],
    },
]


def _maybe_checksum_address(value: str | None) -> str | None:
    if not value:
        return None
    return to_checksum_address(value)


def _coerce_bytes32(value: str) -> bytes:
    if not value.startswith("0x"):
        value = "0x" + value
    raw = bytes.fromhex(value[2:])
    if len(raw) != 32:
        raise ValueError("expected bytes32 hex value")
    return raw


def _legacy_tier_from_split(split_tier: int) -> int:
    if split_tier <= 1:
        return 2
    if split_tier == 2:
        return 1
    return 0


def _hex_or_str(value: Any) -> str:
    if hasattr(value, "hex"):
        rendered = value.hex()
    else:
        rendered = str(value)
    return rendered if rendered.startswith("0x") else "0x" + rendered


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
        self.private_key = private_key
        self.account = self.w3.eth.account.from_key(private_key) if private_key else None
        self.dry_run = dry_run
        self.deployment_mode = "legacy"
        self.vault_address: str | None = None
        self.registry_address: str | None = None
        self.evidence_anchor_address: str | None = None
        self.asset_address: str | None = None
        self.vault_contract = None
        self.registry_contract = None
        self.evidence_anchor_contract = None
        self.asset_contract = None

        split_requested = (
            os.environ.get("ESCROW_CONTRACT_MODE", "").lower() == "split"
            or bool(os.environ.get("ESCROW_COURT_ADDRESS"))
            or bool(os.environ.get("ESCROW_VAULT_ADDRESS"))
            or bool(os.environ.get("ESCROW_JUDGE_REGISTRY_ADDRESS"))
            or bool(os.environ.get("ESCROW_REGISTRY_ADDRESS"))
        )

        if split_requested:
            self.deployment_mode = "split"
            self.contract_address = to_checksum_address(
                os.environ.get("ESCROW_COURT_ADDRESS", contract_address)
            )
            self.vault_address = _maybe_checksum_address(os.environ.get("ESCROW_VAULT_ADDRESS"))
            self.registry_address = _maybe_checksum_address(
                os.environ.get("ESCROW_JUDGE_REGISTRY_ADDRESS") or os.environ.get("ESCROW_REGISTRY_ADDRESS")
            )
            self.evidence_anchor_address = _maybe_checksum_address(
                os.environ.get("ESCROW_EVIDENCE_ANCHOR_ADDRESS")
            )
            self.abi = SPLIT_COURT_ABI
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=SPLIT_COURT_ABI)
            self.vault_contract = (
                self.w3.eth.contract(address=self.vault_address, abi=SPLIT_VAULT_ABI)
                if self.vault_address
                else None
            )
            self.registry_contract = (
                self.w3.eth.contract(address=self.registry_address, abi=SPLIT_REGISTRY_ABI)
                if self.registry_address
                else None
            )
            self.evidence_anchor_contract = (
                self.w3.eth.contract(address=self.evidence_anchor_address, abi=SPLIT_EVIDENCE_ANCHOR_ABI)
                if self.evidence_anchor_address
                else None
            )
            if self.vault_contract is not None:
                try:
                    asset_address = self.vault_contract.functions.usdc().call()
                except Exception:
                    asset_address = None
                if asset_address:
                    self.asset_address = to_checksum_address(asset_address)
                    self.asset_contract = self.w3.eth.contract(address=self.asset_address, abi=SPLIT_ERC20_ABI)
            combined_abi = (
                SPLIT_COURT_ABI
                + SPLIT_VAULT_ABI
                + SPLIT_REGISTRY_ABI
                + SPLIT_EVIDENCE_ANCHOR_ABI
                + SPLIT_ERC20_ABI
            )
            self.fn_index = {f["name"]: f for f in combined_abi if f.get("type") == "function"}
            self.event_index = {
                e["name"]: e
                for e in (SPLIT_COURT_ABI + SPLIT_EVIDENCE_ANCHOR_ABI)
                if e.get("type") == "event"
            }
        else:
            self.contract_address = to_checksum_address(contract_address)
            path = Path(abi_path) if abi_path else DEFAULT_ABI_PATH
            abi = json.loads(path.read_text(encoding="utf-8"))
            self.abi = abi
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=abi)
            self.fn_index = {f["name"]: f for f in abi if f.get("type") == "function"}
            self.event_index = {e["name"]: e for e in abi if e.get("type") == "event"}

        self.connected = False
        self.contract_code_size = 0
        self.contract_has_code = False
        self.vault_code_size = 0
        self.registry_code_size = 0
        self.vault_has_code = False
        self.registry_has_code = False
        self.evidence_anchor_code_size = 0
        self.evidence_anchor_has_code = False
        if not self.dry_run:
            self.connected = self.w3.is_connected()
            code = self.w3.eth.get_code(self.contract_address)
            self.contract_code_size = len(code)
            self.contract_has_code = self.contract_code_size > 0
            if self.deployment_mode == "split":
                if self.vault_address:
                    vault_code = self.w3.eth.get_code(self.vault_address)
                    self.vault_code_size = len(vault_code)
                    self.vault_has_code = self.vault_code_size > 0
                if self.registry_address:
                    registry_code = self.w3.eth.get_code(self.registry_address)
                    self.registry_code_size = len(registry_code)
                    self.registry_has_code = self.registry_code_size > 0
                if self.evidence_anchor_address:
                    anchor_code = self.w3.eth.get_code(self.evidence_anchor_address)
                    self.evidence_anchor_code_size = len(anchor_code)
                    self.evidence_anchor_has_code = self.evidence_anchor_code_size > 0

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

            CREATE TABLE IF NOT EXISTS evidence_commits (
              agreement_id TEXT PRIMARY KEY,
              root_hash TEXT NOT NULL,
              bundle_hash TEXT,
              bundle_cid TEXT,
              tx_hash TEXT NOT NULL,
              block_number INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS split_contracts (
              contract_id INTEGER PRIMARY KEY,
              agreement_id TEXT NOT NULL UNIQUE,
              contract_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dispute_requests (
              request_key TEXT PRIMARY KEY,
              dispute_id INTEGER NOT NULL,
              tx_hash TEXT NOT NULL,
              block_number INTEGER NOT NULL
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

    def _mock_get_evidence_commit(self, agreement_id: str) -> sqlite3.Row | None:
        if self._mock_conn is None:
            return None
        return self._mock_conn.execute(
            """
            SELECT agreement_id, root_hash, bundle_hash, bundle_cid, tx_hash, block_number
            FROM evidence_commits
            WHERE agreement_id = ?
            """,
            (agreement_id,),
        ).fetchone()

    def _mock_store_evidence_commit(
        self,
        agreement_id: str,
        *,
        root_hash: str,
        bundle_hash: str | None = None,
        bundle_cid: str | None = None,
        tx_hash: str,
        block_number: int,
    ) -> None:
        if self._mock_conn is None:
            raise RuntimeError("mock db is not initialized")
        self._mock_conn.execute(
            """
            INSERT OR REPLACE INTO evidence_commits
              (agreement_id, root_hash, bundle_hash, bundle_cid, tx_hash, block_number)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (agreement_id, root_hash, bundle_hash, bundle_cid, tx_hash, int(block_number)),
        )
        self._mock_conn.commit()

    def _mock_put_split_contract(
        self,
        contract_id: int,
        *,
        agreement_id: str,
        contract_data: dict[str, Any],
    ) -> None:
        if self._mock_conn is None:
            raise RuntimeError("mock db is not initialized")
        self._mock_conn.execute(
            """
            INSERT OR REPLACE INTO split_contracts (contract_id, agreement_id, contract_json)
            VALUES (?, ?, ?)
            """,
            (
                int(contract_id),
                agreement_id,
                json.dumps(contract_data, sort_keys=True, separators=(",", ":")),
            ),
        )
        self._mock_conn.commit()

    def _mock_get_split_contract(self, contract_id: int) -> dict[str, Any] | None:
        if self._mock_conn is None:
            return None
        row = self._mock_conn.execute(
            "SELECT contract_json FROM split_contracts WHERE contract_id = ?",
            (int(contract_id),),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["contract_json"])

    def _mock_get_split_contract_by_agreement(self, agreement_id: str) -> dict[str, Any] | None:
        if self._mock_conn is None:
            return None
        row = self._mock_conn.execute(
            "SELECT contract_json FROM split_contracts WHERE agreement_id = ?",
            (agreement_id,),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["contract_json"])

    def _mock_get_dispute_request(self, request_key: str) -> sqlite3.Row | None:
        if self._mock_conn is None:
            return None
        return self._mock_conn.execute(
            """
            SELECT request_key, dispute_id, tx_hash, block_number
            FROM dispute_requests
            WHERE request_key = ?
            """,
            (request_key,),
        ).fetchone()

    def _mock_store_dispute_request(
        self,
        request_key: str,
        *,
        dispute_id: int,
        tx_hash: str,
        block_number: int,
    ) -> None:
        if self._mock_conn is None:
            raise RuntimeError("mock db is not initialized")
        self._mock_conn.execute(
            """
            INSERT OR REPLACE INTO dispute_requests (request_key, dispute_id, tx_hash, block_number)
            VALUES (?, ?, ?, ?)
            """,
            (request_key, int(dispute_id), tx_hash, int(block_number)),
        )
        self._mock_conn.commit()

    def _mock_file_dispute(
        self,
        agreement_id: str,
        *,
        tx_id: int | None = None,
        defendant: str | None = None,
        stake: int | None = None,
        plaintiff_evidence: str | None = None,
    ) -> EscrowTxResult:
        fallback_evidence = "0x" + "0" * 64
        evidence = plaintiff_evidence or fallback_evidence
        normalized_stake = int(stake or 0)
        normalized_tx_id = int(
            tx_id if tx_id is not None else int(Web3.keccak(text=agreement_id).hex(), 16) % (2**63 - 1)
        )
        plaintiff = to_checksum_address(self.account.address) if self.account else ZERO_ADDRESS
        defendant_addr = to_checksum_address(defendant) if defendant else ZERO_ADDRESS
        dispute_id = normalized_tx_id if self.deployment_mode == "split" else None
        judge_fee = max(normalized_stake // 200, 0)

        if self.deployment_mode == "split":
            split_contract = self._mock_get_split_contract(normalized_tx_id)
            if split_contract is not None:
                principal = to_checksum_address(split_contract["principal"])
                client = to_checksum_address(split_contract["client"])
                defendant_addr = client if plaintiff.lower() == principal.lower() else principal
                judge_fee = int(split_contract.get("chainFeeSum", 0))
                principal_locked = int(split_contract.get("principalLocked", 0))
                client_locked = int(split_contract.get("clientLocked", 0))
                normalized_stake = principal_locked if plaintiff.lower() == principal.lower() else client_locked

        request_key = json.dumps(
            {
                "agreementId": agreement_id,
                "txId": normalized_tx_id,
                "plaintiff": plaintiff,
                "defendant": defendant_addr,
                "stake": normalized_stake,
                "plaintiffEvidence": evidence,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        existing = self._mock_get_dispute_request(request_key)
        if existing is not None:
            return EscrowTxResult(
                tx_hash=existing["tx_hash"],
                block_number=int(existing["block_number"]),
                status=1,
                extra={"disputeId": int(existing["dispute_id"]), "idempotent": True},
            )
        if dispute_id is None:
            dispute_id = self._mock_next_counter("dispute_id", start=1)
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
        self._mock_store_dispute_request(
            request_key,
            dispute_id=dispute_id,
            tx_hash=tx_hash,
            block_number=block,
        )
        return EscrowTxResult(
            tx_hash=tx_hash,
            block_number=block,
            status=1,
            extra={"disputeId": dispute_id},
        )

    def _mock_submit_ruling(self, dispute_id: int, verdict_data: dict[str, Any]) -> EscrowTxResult:
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

    def _split_contract_tuple(self, dispute_id: int) -> Any:
        return self.contract.functions.contracts(int(dispute_id)).call()

    def _split_dispute_tuple(self, dispute_id: int) -> Any:
        return self.contract.functions.disputes(int(dispute_id)).call()

    def _split_judge_tuple(self, judge: str) -> Any:
        if self.registry_contract is None:
            return None
        return self.registry_contract.functions.judges(to_checksum_address(judge)).call()

    def _split_latest_evidence_hash(self, dispute_id: int, submitter: str) -> str:
        count = int(self.contract.functions.evidenceCount(int(dispute_id)).call())
        latest = "0x" + "0" * 64
        target = to_checksum_address(submitter).lower()
        for idx in range(count):
            who = to_checksum_address(self.contract.functions.evidenceSubmitters(int(dispute_id), idx).call())
            if who.lower() != target:
                continue
            latest = _hex_or_str(self.contract.functions.evidenceHashes(int(dispute_id), idx).call())
        return latest

    def _split_get_dispute(self, dispute_id: int) -> list[Any] | None:
        dispute_row = self._split_dispute_tuple(dispute_id)
        plaintiff = to_checksum_address(dispute_row[0])
        defendant = to_checksum_address(dispute_row[1])
        if plaintiff == ZERO_ADDRESS and defendant == ZERO_ADDRESS:
            return None

        contract_row = self._split_contract_tuple(dispute_id)
        current_judge = to_checksum_address(dispute_row[2]) if dispute_row[2] else ZERO_ADDRESS
        judge_row = self._split_judge_tuple(current_judge) if current_judge != ZERO_ADDRESS else None
        judge_fee = int(judge_row[1]) if judge_row else 0
        split_tier = int(judge_row[3]) if judge_row else 3
        dispute_tier = _legacy_tier_from_split(split_tier)

        principal = to_checksum_address(contract_row[0])
        client = to_checksum_address(contract_row[1])
        principal_locked = int(contract_row[10])
        client_locked = int(contract_row[11])
        plaintiff_stake = principal_locked if plaintiff.lower() == principal.lower() else client_locked

        ruling = to_checksum_address(contract_row[8]) if contract_row[8] else ZERO_ADDRESS
        resolved = int(contract_row[9]) in {2, 4}

        return [
            int(dispute_id),
            plaintiff,
            defendant,
            plaintiff_stake,
            judge_fee,
            dispute_tier,
            self._split_latest_evidence_hash(dispute_id, plaintiff),
            self._split_latest_evidence_hash(dispute_id, defendant),
            resolved,
            ruling,
        ]

    def capabilities(self) -> dict[str, bool]:
        if self.deployment_mode == "split":
            return {
                "rpcConnected": self.connected,
                "contractHasCode": self.contract_has_code,
                "splitContractSet": True,
                "vaultConfigured": self.vault_contract is not None,
                "judgeRegistryConfigured": self.registry_contract is not None,
                "evidenceAnchorConfigured": self.evidence_anchor_contract is not None,
                "assetConfigured": self.asset_contract is not None,
                "registerJudge": self.registry_contract is not None,
                "createAgreement": True,
                "acceptAgreement": True,
                "completeAgreement": True,
                "depositPool": self.vault_contract is not None,
                "postBond": self.vault_contract is not None,
                "commitEvidenceHash": self.evidence_anchor_contract is not None,
                "commitEvidence": False,
                "fileDispute": True,
                "submitRuling": True,
                "PayoutExecuted": False,
                "RulingSubmitted": True,
            }
        return {
            "rpcConnected": self.connected,
            "contractHasCode": self.contract_has_code,
            "splitContractSet": False,
            "registerJudge": False,
            "createAgreement": False,
            "acceptAgreement": False,
            "completeAgreement": False,
            "depositPool": "depositPool" in self.fn_index,
            "postBond": "postBond" in self.fn_index,
            "commitEvidenceHash": "commitEvidenceHash" in self.fn_index,
            "commitEvidence": "commitEvidence" in self.fn_index,
            "fileDispute": "fileDispute" in self.fn_index,
            "submitRuling": "submitRuling" in self.fn_index,
            "PayoutExecuted": "PayoutExecuted" in self.event_index,
        }

    def contract_sanity(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "rpcConnected": self.connected,
            "contractAddress": self.contract_address,
            "contractHasCode": self.contract_has_code,
            "contractCodeSize": self.contract_code_size,
            "dryRun": self.dry_run,
            "deploymentMode": self.deployment_mode,
        }
        if self.deployment_mode == "split":
            payload.update(
                {
                    "courtAddress": self.contract_address,
                    "vaultAddress": self.vault_address,
                    "judgeRegistryAddress": self.registry_address,
                    "evidenceAnchorAddress": self.evidence_anchor_address,
                    "assetAddress": self.asset_address,
                    "vaultHasCode": self.vault_has_code,
                    "judgeRegistryHasCode": self.registry_has_code,
                    "evidenceAnchorHasCode": self.evidence_anchor_has_code,
                    "vaultCodeSize": self.vault_code_size,
                    "judgeRegistryCodeSize": self.registry_code_size,
                    "evidenceAnchorCodeSize": self.evidence_anchor_code_size,
                }
            )
        return payload

    def _send_tx(self, fn_call, *, value: int = 0) -> EscrowTxResult:
        if self.dry_run:
            block = self._mock_next_counter("block", start=self._mock_block_start())
            return EscrowTxResult(tx_hash=self._mock_tx_hash("dry-run-tx"), status=1, block_number=block)
        if not self.account:
            raise RuntimeError("private key required for state-changing transactions")

        tx_params = {
            "from": self.account.address,
            "chainId": self.chain_id,
            "value": value,
        }
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        try:
            estimated_gas = int(fn_call.estimate_gas(tx_params))
        except Exception as exc:
            raise RuntimeError(
                f"transaction preflight failed for {self.account.address}, "
                f"chain_id={self.chain_id}, mode={self.deployment_mode}: {exc}"
            ) from exc
        tx = fn_call.build_transaction(
            {
                **tx_params,
                "nonce": nonce,
                "gas": max(700_000, estimated_gas + max(estimated_gas // 5, 25_000)),
                "gasPrice": self.w3.eth.gas_price,
            }
        )
        signed = self.account.sign_transaction(tx)
        try:
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        except Exception as exc:
            balance = None
            with_balance = ""
            try:
                balance = self.w3.eth.get_balance(self.account.address)
                with_balance = f", balance={balance}"
            except Exception:
                with_balance = ""
            raise RuntimeError(
                f"transaction submission failed for {self.account.address}"
                f"{with_balance}, chain_id={self.chain_id}, mode={self.deployment_mode}: {exc}"
            ) from exc
        if int(receipt.status) != 1:
            raise RuntimeError(
                f"transaction reverted for {self.account.address}, tx_hash={tx_hash.hex()}, "
                f"chain_id={self.chain_id}, mode={self.deployment_mode}"
            )
        return EscrowTxResult(tx_hash=tx_hash.hex(), block_number=receipt.blockNumber, status=receipt.status)

    def _ensure_split_allowance(self, amount_wei: int) -> EscrowTxResult | None:
        if self.deployment_mode != "split" or self.dry_run:
            return None
        if self.asset_contract is None or self.vault_address is None or self.account is None:
            return None

        allowance = int(
            self.asset_contract.functions.allowance(
                to_checksum_address(self.account.address),
                to_checksum_address(self.vault_address),
            ).call()
        )
        if allowance >= int(amount_wei):
            return None

        max_uint = (1 << 256) - 1
        return self._send_tx(self.asset_contract.functions.approve(self.vault_address, max_uint))

    def deposit_pool(self, amount_wei: int) -> EscrowTxResult:
        if self.deployment_mode == "split":
            if self.vault_contract is None:
                raise RuntimeError("split contract mode requires ESCROW_VAULT_ADDRESS")
            approval_tx = self._ensure_split_allowance(amount_wei)
            deposit_tx = self._send_tx(self.vault_contract.functions.deposit(int(amount_wei)))
            bond_tx = self._send_tx(self.vault_contract.functions.moveToBond(int(amount_wei)))
            extra = {"depositTxHash": deposit_tx.tx_hash, "bondMoveTxHash": bond_tx.tx_hash}
            if approval_tx is not None:
                extra["approveTxHash"] = approval_tx.tx_hash
            return EscrowTxResult(
                tx_hash=bond_tx.tx_hash,
                block_number=bond_tx.block_number,
                status=bond_tx.status,
                extra=extra,
            )
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

    def create_agreement(
        self,
        agreement_id: str,
        *,
        principal: str,
        client: str,
        judge: str,
        consideration: int,
        terms_hash: str,
    ) -> EscrowTxResult:
        if self.deployment_mode != "split":
            raise RuntimeError("create_agreement is only supported in split contract mode")

        principal_addr = to_checksum_address(principal)
        client_addr = to_checksum_address(client)
        judge_addr = to_checksum_address(judge)
        terms_hash_bytes = _coerce_bytes32(terms_hash)

        if self.dry_run:
            existing = self._mock_get_split_contract_by_agreement(agreement_id)
            if existing is not None:
                return EscrowTxResult(
                    tx_hash=existing["txHash"],
                    block_number=int(existing["blockNumber"]),
                    status=1,
                    extra={"contractId": int(existing["contractId"]), "idempotent": True},
                )

            contract_id = self._mock_next_counter("contract_id", start=0)
            proposer = to_checksum_address(self.account.address) if self.account else principal_addr
            chain_fee_sum = 0
            lock_amount = int(consideration) + chain_fee_sum
            contract_data = {
                "contractId": contract_id,
                "agreementId": agreement_id,
                "principal": principal_addr,
                "client": client_addr,
                "judge": judge_addr,
                "consideration": int(consideration),
                "chainFeeSum": chain_fee_sum,
                "termsHash": _hex_or_str(terms_hash_bytes),
                "proposer": proposer,
                "status": "proposed",
                "principalLocked": lock_amount if proposer.lower() == principal_addr.lower() else 0,
                "clientLocked": lock_amount if proposer.lower() == client_addr.lower() else 0,
                "ruling": ZERO_ADDRESS,
            }
            tx_hash = self._mock_tx_hash("split-propose")
            block = self._mock_next_counter("block", start=self._mock_block_start())
            contract_data["txHash"] = tx_hash
            contract_data["blockNumber"] = block
            self._mock_put_split_contract(contract_id, agreement_id=agreement_id, contract_data=contract_data)
            self._mock_emit_event(
                "Proposed",
                {
                    "id": contract_id,
                    "principal": principal_addr,
                    "client": client_addr,
                    "judge": judge_addr,
                },
                tx_hash=tx_hash,
                block_number=block,
            )
            return EscrowTxResult(
                tx_hash=tx_hash,
                block_number=block,
                status=1,
                extra={"contractId": contract_id},
            )

        next_contract_id = int(self.contract.functions.nextContractId().call())
        fn = self.contract.functions.propose(
            principal_addr,
            client_addr,
            judge_addr,
            int(consideration),
            terms_hash_bytes,
        )
        tx = self._send_tx(fn)
        tx.extra = {"contractId": next_contract_id}
        return tx

    def post_bond(self, agreement_id: str, amount_wei: int) -> EscrowTxResult:
        if self.deployment_mode == "split":
            if self.vault_contract is None:
                raise RuntimeError("split contract mode requires ESCROW_VAULT_ADDRESS")
            approval_tx = self._ensure_split_allowance(amount_wei)
            deposit_tx = self._send_tx(self.vault_contract.functions.deposit(int(amount_wei)))
            bond_tx = self._send_tx(self.vault_contract.functions.moveToBond(int(amount_wei)))
            extra = {
                "agreementId": agreement_id,
                "depositTxHash": deposit_tx.tx_hash,
                "bondMoveTxHash": bond_tx.tx_hash,
            }
            if approval_tx is not None:
                extra["approveTxHash"] = approval_tx.tx_hash
            return EscrowTxResult(
                tx_hash=bond_tx.tx_hash,
                block_number=bond_tx.block_number,
                status=bond_tx.status,
                extra=extra,
            )
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

    def accept_agreement(self, contract_id: int) -> EscrowTxResult:
        if self.deployment_mode != "split":
            raise RuntimeError("accept_agreement is only supported in split contract mode")

        if self.dry_run:
            contract_data = self._mock_get_split_contract(contract_id)
            if contract_data is None:
                raise ValueError(f"split contract {contract_id} not found")

            if contract_data["status"] == "active":
                return EscrowTxResult(
                    tx_hash=contract_data["acceptTxHash"],
                    block_number=int(contract_data["acceptBlockNumber"]),
                    status=1,
                    extra={"contractId": int(contract_id), "idempotent": True},
                )

            actor = to_checksum_address(self.account.address) if self.account else ZERO_ADDRESS
            lock_amount = int(contract_data["consideration"]) + int(contract_data.get("chainFeeSum", 0))
            if actor.lower() == to_checksum_address(contract_data["principal"]).lower():
                contract_data["principalLocked"] = lock_amount
            elif actor.lower() == to_checksum_address(contract_data["client"]).lower():
                contract_data["clientLocked"] = lock_amount
            contract_data["status"] = "active"
            tx_hash = self._mock_tx_hash("split-accept")
            block = self._mock_next_counter("block", start=self._mock_block_start())
            contract_data["acceptTxHash"] = tx_hash
            contract_data["acceptBlockNumber"] = block
            self._mock_put_split_contract(
                int(contract_id),
                agreement_id=str(contract_data["agreementId"]),
                contract_data=contract_data,
            )
            self._mock_emit_event(
                "Accepted",
                {"id": int(contract_id)},
                tx_hash=tx_hash,
                block_number=block,
            )
            return EscrowTxResult(
                tx_hash=tx_hash,
                block_number=block,
                status=1,
                extra={"contractId": int(contract_id)},
            )

        fn = self.contract.functions.accept(int(contract_id))
        tx = self._send_tx(fn)
        tx.extra = {"contractId": int(contract_id)}
        return tx

    def complete_agreement(self, contract_id: int) -> EscrowTxResult:
        if self.deployment_mode != "split":
            raise RuntimeError("complete_agreement is only supported in split contract mode")

        if self.dry_run:
            contract_data = self._mock_get_split_contract(contract_id)
            if contract_data is None:
                raise ValueError(f"split contract {contract_id} not found")
            contract_data["status"] = "completed"
            contract_data["principalLocked"] = 0
            contract_data["clientLocked"] = 0
            tx_hash = self._mock_tx_hash("split-complete")
            block = self._mock_next_counter("block", start=self._mock_block_start())
            contract_data["completeTxHash"] = tx_hash
            contract_data["completeBlockNumber"] = block
            self._mock_put_split_contract(
                int(contract_id),
                agreement_id=str(contract_data["agreementId"]),
                contract_data=contract_data,
            )
            self._mock_emit_event(
                "Completed",
                {"id": int(contract_id)},
                tx_hash=tx_hash,
                block_number=block,
            )
            return EscrowTxResult(
                tx_hash=tx_hash,
                block_number=block,
                status=1,
                extra={"contractId": int(contract_id)},
            )

        fn = self.contract.functions.complete(int(contract_id))
        tx = self._send_tx(fn)
        tx.extra = {"contractId": int(contract_id)}
        return tx

    def register_judge(
        self,
        *,
        superior: str | None = None,
        fee: int = 0,
        endpoint: str = "",
        max_response_time: int = 300,
        bond_amount: int | None = None,
    ) -> EscrowTxResult:
        if self.deployment_mode != "split":
            raise RuntimeError("register_judge is only supported in split contract mode")
        if self.registry_contract is None:
            raise RuntimeError("split contract mode requires ESCROW_JUDGE_REGISTRY_ADDRESS")

        normalized_superior = ZERO_ADDRESS if not superior else to_checksum_address(superior)
        required_bond = max(int(fee), int(bond_amount or 0))

        if self.dry_run:
            block = self._mock_next_counter("block", start=self._mock_block_start())
            tx_hash = self._mock_tx_hash("register-judge")
            return EscrowTxResult(
                tx_hash=tx_hash,
                block_number=block,
                status=1,
                extra={
                    "judge": self.account.address if self.account else ZERO_ADDRESS,
                    "superior": normalized_superior,
                    "fee": int(fee),
                    "bondAmount": required_bond,
                },
            )

        approval_tx = None
        deposit_tx = None
        bond_tx = None
        if required_bond > 0:
            if self.vault_contract is None:
                raise RuntimeError("split contract mode requires ESCROW_VAULT_ADDRESS")
            approval_tx = self._ensure_split_allowance(required_bond)
            deposit_tx = self._send_tx(self.vault_contract.functions.deposit(required_bond))
            bond_tx = self._send_tx(self.vault_contract.functions.moveToBond(required_bond))

        register_tx = self._send_tx(
            self.registry_contract.functions.registerJudge(
                normalized_superior,
                int(fee),
                endpoint,
                int(max_response_time),
            )
        )
        register_tx.extra = {
            "judge": self.account.address if self.account else ZERO_ADDRESS,
            "superior": normalized_superior,
            "fee": int(fee),
            "bondAmount": required_bond,
            "approveTxHash": approval_tx.tx_hash if approval_tx else None,
            "depositTxHash": deposit_tx.tx_hash if deposit_tx else None,
            "bondMoveTxHash": bond_tx.tx_hash if bond_tx else None,
        }
        return register_tx

    def commit_evidence_hash(
        self,
        agreement_id: str,
        root_hash: str,
        *,
        bundle_hash: str | None = None,
        bundle_cid: str | None = None,
    ) -> EscrowTxResult:
        if self.dry_run:
            existing = self._mock_get_evidence_commit(agreement_id)
            if existing is not None:
                if existing["root_hash"] != root_hash:
                    raise ValueError("evidence already committed for agreement with different root_hash")
                if bundle_hash and existing["bundle_hash"] and existing["bundle_hash"] != bundle_hash:
                    raise ValueError("evidence already committed for agreement with different bundle_hash")
                if bundle_cid and existing["bundle_cid"] and existing["bundle_cid"] != bundle_cid:
                    raise ValueError("evidence already committed for agreement with different bundle_cid")
                return EscrowTxResult(
                    tx_hash=existing["tx_hash"],
                    block_number=int(existing["block_number"]),
                    status=1,
                    extra={"idempotent": True},
                )

            tx_hash = self._mock_tx_hash("commit-evidence")
            block = self._mock_next_counter("block", start=self._mock_block_start())
            agent = self.account.address if self.account else ZERO_ADDRESS
            self._mock_emit_event(
                "EvidenceCommitted",
                {
                    "agreementId": agreement_id,
                    "rootHash": root_hash,
                    "agent": to_checksum_address(agent),
                    "bundleHash": bundle_hash,
                    "bundleCid": bundle_cid,
                },
                tx_hash=tx_hash,
                block_number=block,
            )
            self._mock_store_evidence_commit(
                agreement_id,
                root_hash=root_hash,
                bundle_hash=bundle_hash,
                bundle_cid=bundle_cid,
                tx_hash=tx_hash,
                block_number=block,
            )
            return EscrowTxResult(tx_hash=tx_hash, block_number=block, status=1)

        if self.deployment_mode == "split":
            if self.evidence_anchor_contract is None:
                raise RuntimeError(
                    "split contract mode requires ESCROW_EVIDENCE_ANCHOR_ADDRESS for on-chain evidence anchoring"
                )
            if not bundle_hash or not bundle_cid:
                raise ValueError("split contract mode requires bundle_hash and bundle_cid")
            fn = self.evidence_anchor_contract.functions.commitEvidence(
                agreement_id,
                _coerce_bytes32(root_hash),
                _coerce_bytes32(bundle_hash),
                bundle_cid,
            )
            return self._send_tx(fn)

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
        if self.dry_run:
            return self._mock_file_dispute(
                agreement_id,
                tx_id=tx_id,
                defendant=defendant,
                stake=stake,
                plaintiff_evidence=plaintiff_evidence,
            )

        if self.deployment_mode == "split":
            if tx_id is None:
                raise ValueError("split contract mode requires tx_id (Court contract ID)")
            dispute_tx = self._send_tx(self.contract.functions.dispute(int(tx_id)))
            if plaintiff_evidence and plaintiff_evidence not in {"0x0", "0x" + "0" * 64}:
                self._send_tx(self.contract.functions.submitEvidence(int(tx_id), _coerce_bytes32(plaintiff_evidence)))
            return EscrowTxResult(
                tx_hash=dispute_tx.tx_hash,
                block_number=dispute_tx.block_number,
                status=dispute_tx.status,
                extra={"disputeId": int(tx_id)},
            )

        if "fileDispute" not in self.fn_index:
            raise RuntimeError("No fileDispute function in ABI")

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
        if self.dry_run:
            return self._mock_submit_ruling(dispute_id, verdict_data)

        if self.deployment_mode == "split":
            winner = to_checksum_address(_winner_from_verdict(verdict_data))
            ruling_hash = verdict_data.get("verdictHash")
            if not ruling_hash:
                ruling_hash = Web3.to_hex(
                    keccak(text=json.dumps(verdict_data, sort_keys=True, separators=(",", ":")))
                )
            fn = self.contract.functions.rule(int(dispute_id), winner, _coerce_bytes32(ruling_hash))
            return self._send_tx(fn)

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
        if self.dry_run:
            mock_dispute = self._mock_get_dispute(dispute_id)
            if mock_dispute is not None:
                return mock_dispute
        if self.deployment_mode == "split":
            return self._split_get_dispute(dispute_id)
        if "getDispute" not in self.fn_index:
            return None
        return self.contract.functions.getDispute(dispute_id).call()

    def judge_address(self) -> str | None:
        if self.deployment_mode == "split":
            return None
        if "judge" not in self.fn_index:
            return None
        try:
            return to_checksum_address(self.contract.functions.judge().call())
        except Exception:
            return None

    def assigned_judge(self, dispute_id: int | None = None) -> str | None:
        if self.deployment_mode != "split":
            return self.judge_address()
        if dispute_id is None:
            return None
        if self.dry_run:
            split_contract = self._mock_get_split_contract(int(dispute_id))
            if split_contract is None:
                return None
            return to_checksum_address(split_contract["judge"])
        try:
            dispute = self._split_dispute_tuple(int(dispute_id))
        except Exception:
            return None
        judge = to_checksum_address(dispute[2]) if dispute[2] else ZERO_ADDRESS
        return None if judge == ZERO_ADDRESS else judge

    def _event_entries(self, event_obj: Any, from_block: int, to_block: int | str = "latest") -> list[dict[str, Any]]:
        if hasattr(event_obj, "get_logs"):
            raw_entries = event_obj.get_logs(from_block=from_block, to_block=to_block)
        else:
            flt = event_obj.create_filter(from_block=from_block, to_block=to_block)
            raw_entries = flt.get_all_entries()

        entries: list[dict[str, Any]] = []
        for raw in raw_entries:
            entry = dict(raw)
            if entry.get("transactionHash") is not None:
                entry["transactionHash"] = _hex_or_str(entry["transactionHash"])
            if entry.get("blockNumber") is not None:
                entry["blockNumber"] = int(entry["blockNumber"])
            entries.append(entry)
        return entries

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

        if self.deployment_mode == "split":
            if event_name == "EvidenceCommitted":
                if self.evidence_anchor_contract is None:
                    return []
                event_obj = self.evidence_anchor_contract.events.EvidenceCommitted
                logs: list[dict[str, Any]] = []
                for entry in self._event_entries(event_obj, from_block=from_block, to_block=to_block):
                    args = dict(entry.get("args", {}))
                    entry["args"] = {
                        "agreementId": args.get("agreementId"),
                        "rootHash": _hex_or_str(args.get("rootHash", bytes(32))),
                        "agent": args.get("submitter", ZERO_ADDRESS),
                        "bundleHash": _hex_or_str(args.get("bundleHash", bytes(32))),
                        "bundleCid": args.get("bundleCid"),
                    }
                    logs.append(entry)
                return logs
            if event_name == "DisputeFiled":
                event_obj = self.contract.events.DisputeFiled
                logs: list[dict[str, Any]] = []
                for entry in self._event_entries(event_obj, from_block=from_block, to_block=to_block):
                    args = dict(entry.get("args", {}))
                    dispute_id = int(args.get("id", 0))
                    dispute = self.get_dispute(dispute_id)
                    entry["args"] = {
                        "disputeId": dispute_id,
                        "plaintiff": dispute[1] if dispute else args.get("plaintiff", ZERO_ADDRESS),
                        "defendant": dispute[2] if dispute else ZERO_ADDRESS,
                    }
                    logs.append(entry)
                return logs
            if event_name == "RulingSubmitted":
                event_obj = self.contract.events.Ruled
                logs: list[dict[str, Any]] = []
                for entry in self._event_entries(event_obj, from_block=from_block, to_block=to_block):
                    args = dict(entry.get("args", {}))
                    dispute_id = int(args.get("id", 0))
                    winner = to_checksum_address(args.get("winner", ZERO_ADDRESS))
                    dispute = self.get_dispute(dispute_id)
                    loser = ZERO_ADDRESS
                    if dispute:
                        plaintiff = to_checksum_address(dispute[1])
                        defendant = to_checksum_address(dispute[2])
                        loser = defendant if winner.lower() == plaintiff.lower() else plaintiff
                    entry["args"] = {
                        "disputeId": dispute_id,
                        "winner": winner,
                        "loser": loser,
                    }
                    logs.append(entry)
                return logs

        if event_name not in self.event_index:
            return []
        event_obj = getattr(self.contract.events, event_name)
        return self._event_entries(event_obj, from_block=from_block, to_block=to_block)


def _winner_from_verdict(verdict_data: dict[str, Any]) -> str:
    if "winner" in verdict_data:
        return verdict_data["winner"]

    transfers = verdict_data.get("transfers", [])
    if not transfers:
        raise ValueError("verdict_data must include winner or transfers")

    sorted_transfers = sorted(transfers, key=lambda t: int(t.get("amount", "0")), reverse=True)
    return sorted_transfers[0]["to"]
