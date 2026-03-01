from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class EvidenceStorage:
    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS clauses (
              clause_id TEXT PRIMARY KEY,
              agreement_id TEXT NOT NULL,
              chain_id INTEGER NOT NULL,
              contract_address TEXT NOT NULL,
              clause_hash TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at INTEGER NOT NULL DEFAULT (unixepoch())
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_clauses_agreement
              ON clauses(agreement_id);

            CREATE TABLE IF NOT EXISTS receipts (
              receipt_id TEXT PRIMARY KEY,
              agreement_id TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              sequence INTEGER NOT NULL,
              receipt_hash TEXT NOT NULL,
              prev_hash TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at INTEGER NOT NULL DEFAULT (unixepoch())
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_receipts_agreement_sequence
              ON receipts(agreement_id, sequence);

            CREATE INDEX IF NOT EXISTS idx_receipts_agreement_actor
              ON receipts(agreement_id, actor_id);

            CREATE TABLE IF NOT EXISTS anchors (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              agreement_id TEXT NOT NULL,
              root_hash TEXT NOT NULL,
              tx_hash TEXT NOT NULL,
              receipt_ids_json TEXT NOT NULL,
              created_at INTEGER NOT NULL DEFAULT (unixepoch())
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_anchors_agreement
              ON anchors(agreement_id);

            CREATE INDEX IF NOT EXISTS idx_anchors_root
              ON anchors(root_hash);
            """
        )
        self.conn.commit()

    def store_clause(self, clause: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO clauses
              (clause_id, agreement_id, chain_id, contract_address, clause_hash, payload_json)
            VALUES
              (?, ?, ?, ?, ?, ?)
            """,
            (
                clause["clauseId"],
                clause["agreementId"],
                clause["chainId"],
                clause["contractAddress"],
                clause["clauseHash"],
                json.dumps(clause, separators=(",", ":")),
            ),
        )
        self.conn.commit()

    def get_clause_by_agreement(self, agreement_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json FROM clauses WHERE agreement_id = ?", (agreement_id,)
        ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])

    def store_receipt(self, receipt: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO receipts
              (receipt_id, agreement_id, actor_id, sequence, receipt_hash, prev_hash, payload_json)
            VALUES
              (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt["receiptId"],
                receipt["agreementId"],
                receipt["actorId"],
                receipt["sequence"],
                receipt["receiptHash"],
                receipt["prevHash"],
                json.dumps(receipt, separators=(",", ":")),
            ),
        )
        self.conn.commit()

    def get_receipt(self, receipt_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json FROM receipts WHERE receipt_id = ?", (receipt_id,)
        ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])

    def list_receipts(
        self, agreement_id: str | None = None, actor_id: str | None = None
    ) -> list[dict[str, Any]]:
        query = "SELECT payload_json FROM receipts"
        args: list[Any] = []
        where: list[str] = []

        if agreement_id:
            where.append("agreement_id = ?")
            args.append(agreement_id)
        if actor_id:
            where.append("actor_id = ?")
            args.append(actor_id)

        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY sequence ASC"

        rows = self.conn.execute(query, tuple(args)).fetchall()
        return [json.loads(r["payload_json"]) for r in rows]

    def get_last_receipt(self, agreement_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json FROM receipts WHERE agreement_id = ? ORDER BY sequence DESC LIMIT 1",
            (agreement_id,),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])

    def store_anchor(self, agreement_id: str, root_hash: str, tx_hash: str, receipt_ids: list[str]) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO anchors
              (id, agreement_id, root_hash, tx_hash, receipt_ids_json)
            VALUES
              ((SELECT id FROM anchors WHERE agreement_id = ?), ?, ?, ?, ?)
            """,
            (
                agreement_id,
                agreement_id,
                root_hash,
                tx_hash,
                json.dumps(receipt_ids, separators=(",", ":")),
            ),
        )
        self.conn.commit()

    def get_anchor(self, agreement_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT root_hash, tx_hash, receipt_ids_json FROM anchors WHERE agreement_id = ?",
            (agreement_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "agreementId": agreement_id,
            "rootHash": row["root_hash"],
            "txHash": row["tx_hash"],
            "receiptIds": json.loads(row["receipt_ids_json"]),
        }

    def get_anchor_by_root(self, root_hash: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT agreement_id, tx_hash, receipt_ids_json FROM anchors WHERE root_hash = ?",
            (root_hash,),
        ).fetchone()
        if not row:
            return None
        return {
            "agreementId": row["agreement_id"],
            "rootHash": root_hash,
            "txHash": row["tx_hash"],
            "receiptIds": json.loads(row["receipt_ids_json"]),
        }
