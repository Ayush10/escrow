from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class JudgeStorage:
    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS verdicts (
              verdict_id TEXT PRIMARY KEY,
              dispute_id TEXT NOT NULL,
              agreement_id TEXT,
              status TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at INTEGER NOT NULL DEFAULT (unixepoch())
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_verdicts_dispute
              ON verdicts(dispute_id);

            CREATE TABLE IF NOT EXISTS cursors (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def get_cursor(self, key: str, default: int) -> int:
        row = self.conn.execute("SELECT value FROM cursors WHERE key = ?", (key,)).fetchone()
        if not row:
            return default
        return int(row["value"])

    def set_cursor(self, key: str, value: int) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO cursors (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        self.conn.commit()

    def is_processed(self, dispute_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM verdicts WHERE dispute_id = ? LIMIT 1", (str(dispute_id),)
        ).fetchone()
        return row is not None

    def store_verdict(self, verdict: dict[str, Any], status: str) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO verdicts
              (verdict_id, dispute_id, agreement_id, status, payload_json)
            VALUES
              (?, ?, ?, ?, ?)
            """,
            (
                verdict.get("verdictId"),
                str(verdict.get("disputeId")),
                verdict.get("agreementId"),
                status,
                json.dumps(verdict, separators=(",", ":")),
            ),
        )
        self.conn.commit()

    def list_verdicts(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT payload_json, status FROM verdicts ORDER BY created_at DESC"
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            payload["status"] = row["status"]
            result.append(payload)
        return result

    def get_verdict_by_dispute(self, dispute_id: int | str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json, status FROM verdicts WHERE dispute_id = ? ORDER BY created_at DESC LIMIT 1",
            (str(dispute_id),),
        ).fetchone()
        if not row:
            return None
        payload = json.loads(row["payload_json"])
        payload["status"] = row["status"]
        return payload
