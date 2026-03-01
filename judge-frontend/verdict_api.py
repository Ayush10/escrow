"""Verdict API — serves judicial opinions from SQLite."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = os.environ.get("VERDICT_DB", "/opt/court-api/verdicts.db")
API_KEY = os.environ.get("VERDICT_API_KEY", "agent-court-judge-key-2026")

app = FastAPI(title="Verdict API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS verdicts (
          dispute_id TEXT PRIMARY KEY,
          winner TEXT,
          loser TEXT,
          opinion TEXT,
          tier INTEGER DEFAULT 0,
          confidence REAL DEFAULT 0.95,
          reason_codes TEXT DEFAULT '[]',
          payload_json TEXT DEFAULT '{}',
          created_at INTEGER NOT NULL DEFAULT (unixepoch())
        );
    """)
    conn.commit()
    return conn


@app.get("/api/verdicts")
def list_verdicts():
    db = get_db()
    rows = db.execute("SELECT * FROM verdicts ORDER BY created_at DESC").fetchall()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


@app.get("/api/verdicts/{dispute_id}")
def get_verdict(dispute_id: str):
    db = get_db()
    row = db.execute("SELECT * FROM verdicts WHERE dispute_id = ?", (dispute_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"No verdict for dispute {dispute_id}")
    return dict(row)


@app.post("/api/verdicts")
async def post_verdict(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {API_KEY}":
        raise HTTPException(403, "Invalid API key")
    data = await request.json()
    dispute_id = str(data.get("disputeId", data.get("dispute_id", "")))
    if not dispute_id:
        raise HTTPException(400, "disputeId required")

    db = get_db()
    db.execute(
        """INSERT OR REPLACE INTO verdicts
           (dispute_id, winner, loser, opinion, tier, confidence, reason_codes, payload_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            dispute_id,
            data.get("winner", ""),
            data.get("loser", ""),
            data.get("fullOpinion", data.get("opinion", "")),
            data.get("tier", 0),
            data.get("confidence", 0.95),
            json.dumps(data.get("reasonCodes", [])),
            json.dumps(data),
        ),
    )
    db.commit()
    return {"ok": True, "disputeId": dispute_id}


@app.get("/api/health")
def health():
    return {"status": "ok"}
