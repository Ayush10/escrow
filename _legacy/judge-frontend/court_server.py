"""Lightweight frontend host + API proxy compatibility layer.

This keeps legacy `judge-frontend/court_server.py` semantics from remote
while preserving the new demo-runner driven flow.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

RUNNER_URL = os.environ.get("DEMO_RUNNER_URL", "http://127.0.0.1:4004").rstrip("/")
JUDGE_URL = os.environ.get("JUDGE_SERVICE_URL", "http://127.0.0.1:4002").rstrip("/")
ROOT = Path(__file__).resolve().parent

app = FastAPI(title="Court Frontend Host", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(ROOT)), name="static")


def _forward_json(method: str, base: str, path: str, payload: dict[str, Any] | None = None) -> JSONResponse:
    with httpx.Client(timeout=30) as client:
        if method == "GET":
            response = client.get(f"{base}{path}")
        else:
            response = client.post(f"{base}{path}", json=payload or {})
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    try:
        return JSONResponse(status_code=response.status_code, content=response.json())
    except Exception:
        return JSONResponse(status_code=response.status_code, content={"raw": response.text})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/api/health")
def api_health() -> dict[str, Any]:
    def probe(url: str) -> str:
        try:
            with httpx.Client(timeout=4) as client:
                response = client.get(f"{url}/health")
            return "ok" if response.status_code < 500 else "warn"
        except Exception:
            return "down"

    return {
        "status": "ok",
        "runner": RUNNER_URL,
        "judge": JUDGE_URL,
        "services": {
            "runner": probe(RUNNER_URL),
            "judge": probe(JUDGE_URL),
        },
    }


@app.get("/api/config")
def api_config() -> JSONResponse:
    try:
        return _forward_json("GET", RUNNER_URL, "/config")
    except HTTPException:
        # Minimal fallback for standalone hosting.
        return JSONResponse(
            content={
                "contractAddress": os.environ.get(
                    "ESCROW_CONTRACT_ADDRESS",
                    "0x00289Dbbb86b64881CEA492D14178CF886b066Be",
                ),
                "chainId": int(os.environ.get("GOAT_CHAIN_ID", "48816")),
                "explorerUrl": os.environ.get(
                    "GOAT_EXPLORER_URL",
                    "https://explorer.testnet3.goat.network",
                ),
                "services": {
                    "runner": RUNNER_URL,
                    "judge": JUDGE_URL,
                },
            }
        )


@app.get("/api/runs")
def api_runs() -> JSONResponse:
    return _forward_json("GET", RUNNER_URL, "/runs")


@app.post("/api/runs")
async def api_create_run(request: Request) -> JSONResponse:
    payload = await request.json()
    return _forward_json("POST", RUNNER_URL, "/runs", payload)


@app.get("/api/runs/{run_id}")
def api_run(run_id: str) -> JSONResponse:
    return _forward_json("GET", RUNNER_URL, f"/runs/{run_id}")


@app.get("/api/verdicts")
def api_verdicts() -> JSONResponse:
    return _forward_json("GET", JUDGE_URL, "/verdicts")


@app.get("/api/verdicts/{dispute_id}")
def api_verdict(dispute_id: int) -> JSONResponse:
    return _forward_json("GET", JUDGE_URL, f"/verdicts/{dispute_id}")


def main() -> None:
    import uvicorn

    host = os.environ.get("COURT_SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("COURT_SERVER_PORT", "4174"))
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
