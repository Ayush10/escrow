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
              review_reason TEXT,
              payload_json TEXT NOT NULL,
              created_at INTEGER NOT NULL DEFAULT (unixepoch()),
              updated_at INTEGER NOT NULL DEFAULT (unixepoch())
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_verdicts_dispute
              ON verdicts(dispute_id);

            CREATE TABLE IF NOT EXISTS cursors (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )
        self._ensure_columns()
        self.conn.commit()

    def _ensure_columns(self) -> None:
        columns = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(verdicts)").fetchall()
        }
        if "review_reason" not in columns:
            self.conn.execute("ALTER TABLE verdicts ADD COLUMN review_reason TEXT")
        if "updated_at" not in columns:
            self.conn.execute(
                "ALTER TABLE verdicts ADD COLUMN updated_at INTEGER NOT NULL DEFAULT (unixepoch())"
            )

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

    def store_verdict(self, verdict: dict[str, Any], status: str, review_reason: str | None = None) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO verdicts
              (verdict_id, dispute_id, agreement_id, status, review_reason, payload_json, updated_at)
            VALUES
              (?, ?, ?, ?, ?, ?, unixepoch())
            """,
            (
                verdict.get("verdictId"),
                str(verdict.get("disputeId")),
                verdict.get("agreementId"),
                status,
                review_reason,
                json.dumps(verdict, separators=(",", ":")),
            ),
        )
        self.conn.commit()

    def list_verdicts(self, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            rows = self.conn.execute(
                "SELECT payload_json, status, review_reason FROM verdicts WHERE status = ? ORDER BY updated_at DESC, created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT payload_json, status, review_reason FROM verdicts ORDER BY updated_at DESC, created_at DESC"
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            payload["status"] = row["status"]
            payload["reviewReason"] = row["review_reason"]
            result.append(payload)
        return result

    def list_manual_review(self) -> list[dict[str, Any]]:
        return self.list_verdicts(status="manual_review")

    def manual_review_count(self) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS count FROM verdicts WHERE status = ?",
            ("manual_review",),
        ).fetchone()
        return int(row["count"]) if row else 0

    def get_verdict_by_dispute(self, dispute_id: int | str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json, status, review_reason FROM verdicts WHERE dispute_id = ? ORDER BY updated_at DESC, created_at DESC LIMIT 1",
            (str(dispute_id),),
        ).fetchone()
        if not row:
            return None
        payload = json.loads(row["payload_json"])
        payload["status"] = row["status"]
        payload["reviewReason"] = row["review_reason"]
        return payload
