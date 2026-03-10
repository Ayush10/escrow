from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .scorer import MODEL_VERSION, component_deltas, confidence_for_event_count


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

            CREATE TABLE IF NOT EXISTS reputation_profiles (
              actor_id TEXT PRIMARY KEY,
              model_version TEXT NOT NULL,
              service_score INTEGER NOT NULL DEFAULT 0,
              court_score INTEGER NOT NULL DEFAULT 0,
              reliability_score INTEGER NOT NULL DEFAULT 0,
              event_count INTEGER NOT NULL DEFAULT 0,
              successful_event_count INTEGER NOT NULL DEFAULT 0,
              dispute_event_count INTEGER NOT NULL DEFAULT 0,
              confidence REAL NOT NULL DEFAULT 0.1,
              updated_at INTEGER NOT NULL DEFAULT (unixepoch())
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
        self.conn.execute(
            """
            INSERT OR IGNORE INTO reputation_profiles
              (actor_id, model_version)
            VALUES
              (?, ?)
            """,
            (actor_id, MODEL_VERSION),
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
        deltas = component_deltas(reason, delta)
        profile = self.conn.execute(
            """
            SELECT event_count
            FROM reputation_profiles
            WHERE actor_id = ?
            """,
            (actor_id,),
        ).fetchone()
        next_event_count = (int(profile["event_count"]) if profile else 0) + 1
        self.conn.execute(
            """
            UPDATE reputation_profiles
            SET model_version = ?,
                service_score = service_score + ?,
                court_score = court_score + ?,
                reliability_score = reliability_score + ?,
                event_count = event_count + 1,
                successful_event_count = successful_event_count + ?,
                dispute_event_count = dispute_event_count + ?,
                confidence = ?,
                updated_at = unixepoch()
            WHERE actor_id = ?
            """,
            (
                MODEL_VERSION,
                deltas["service"],
                deltas["court"],
                deltas["reliability"],
                deltas["successful_events"],
                deltas["dispute_events"],
                confidence_for_event_count(next_event_count),
                actor_id,
            ),
        )
        self.conn.commit()
        return True

    def get_reputation(self, actor_id: str) -> dict[str, Any]:
        self._ensure_actor(actor_id)
        score_row = self.conn.execute(
            "SELECT score FROM agent_scores WHERE actor_id = ?", (actor_id,)
        ).fetchone()
        profile_row = self.conn.execute(
            """
            SELECT model_version, service_score, court_score, reliability_score,
                   event_count, successful_event_count, dispute_event_count, confidence
            FROM reputation_profiles
            WHERE actor_id = ?
            """,
            (actor_id,),
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
        return {
            "actorId": actor_id,
            "score": int(score_row["score"]),
            "modelVersion": profile_row["model_version"],
            "components": {
                "service": int(profile_row["service_score"]),
                "court": int(profile_row["court_score"]),
                "reliability": int(profile_row["reliability_score"]),
            },
            "stats": {
                "eventCount": int(profile_row["event_count"]),
                "successfulEventCount": int(profile_row["successful_event_count"]),
                "disputeEventCount": int(profile_row["dispute_event_count"]),
                "confidence": float(profile_row["confidence"]),
            },
            "history": history,
        }

    def list_reputations(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT s.actor_id, s.score, p.model_version, p.service_score, p.court_score,
                   p.reliability_score, p.confidence
            FROM agent_scores s
            JOIN reputation_profiles p ON p.actor_id = s.actor_id
            ORDER BY s.score DESC, s.actor_id ASC
            """
        ).fetchall()
        return [
            {
                "actorId": r["actor_id"],
                "score": int(r["score"]),
                "modelVersion": r["model_version"],
                "components": {
                    "service": int(r["service_score"]),
                    "court": int(r["court_score"]),
                    "reliability": int(r["reliability_score"]),
                },
                "confidence": float(r["confidence"]),
            }
            for r in rows
        ]
