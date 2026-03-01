from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class ReputationStorage:
    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS agent_scores (
              actor_id TEXT PRIMARY KEY,
              score INTEGER NOT NULL,
              updated_at INTEGER NOT NULL DEFAULT (unixepoch())
            );

            CREATE TABLE IF NOT EXISTS score_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              actor_id TEXT NOT NULL,
              delta INTEGER NOT NULL,
              reason TEXT NOT NULL,
              event_key TEXT NOT NULL UNIQUE,
              payload_json TEXT NOT NULL,
              created_at INTEGER NOT NULL DEFAULT (unixepoch())
            );

            CREATE TABLE IF NOT EXISTS cursors (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def get_cursor(self, key: str, default: int = 0) -> int:
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

    def _ensure_actor(self, actor_id: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO agent_scores (actor_id, score) VALUES (?, 100)", (actor_id,)
        )

    def apply_event(
        self,
        *,
        actor_id: str,
        delta: int,
        reason: str,
        event_key: str,
        payload: dict[str, Any],
    ) -> bool:
        self._ensure_actor(actor_id)
        try:
            self.conn.execute(
                """
                INSERT INTO score_events (actor_id, delta, reason, event_key, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (actor_id, delta, reason, event_key, json.dumps(payload, separators=(",", ":"))),
            )
        except sqlite3.IntegrityError:
            return False

        self.conn.execute(
            "UPDATE agent_scores SET score = score + ?, updated_at = unixepoch() WHERE actor_id = ?",
            (delta, actor_id),
        )
        self.conn.commit()
        return True

    def get_reputation(self, actor_id: str) -> dict[str, Any]:
        self._ensure_actor(actor_id)
        score_row = self.conn.execute(
            "SELECT score FROM agent_scores WHERE actor_id = ?", (actor_id,)
        ).fetchone()
        events = self.conn.execute(
            "SELECT delta, reason, payload_json, created_at FROM score_events WHERE actor_id = ? ORDER BY id DESC",
            (actor_id,),
        ).fetchall()
        history = [
            {
                "delta": r["delta"],
                "reason": r["reason"],
                "payload": json.loads(r["payload_json"]),
                "createdAt": r["created_at"],
            }
            for r in events
        ]
        return {"actorId": actor_id, "score": int(score_row["score"]), "history": history}

    def list_reputations(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT actor_id, score FROM agent_scores ORDER BY score DESC, actor_id ASC"
        ).fetchall()
        return [{"actorId": r["actor_id"], "score": int(r["score"])} for r in rows]
