"""Legacy-compatible verdict API shim.

Remote branch introduced a dedicated verdict API under `judge-frontend/`.
This shim keeps that integration point, but sources data from the
authoritative `apps/judge_service` backend.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

JUDGE_SERVICE_URL = os.environ.get("JUDGE_SERVICE_URL", "http://127.0.0.1:4002").rstrip("/")

app = FastAPI(title="Verdict API Shim", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _judge_get(path: str) -> dict[str, Any]:
    with httpx.Client(timeout=20) as client:
        response = client.get(f"{JUDGE_SERVICE_URL}{path}")
    if response.status_code >= 400:
        detail = response.text
        try:
            detail = response.json()
        except Exception:
            pass
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


@app.get("/api/health")
def health() -> dict[str, Any]:
    upstream = _judge_get("/health")
    return {"status": "ok", "upstream": JUDGE_SERVICE_URL, "judge": upstream}


@app.get("/api/verdicts")
def list_verdicts() -> dict[str, Any]:
    # Prefer the new native route and preserve response shape.
    return _judge_get("/verdicts")


@app.get("/api/verdicts/{dispute_id}")
def get_verdict(dispute_id: int) -> dict[str, Any]:
    return _judge_get(f"/verdicts/{dispute_id}")

