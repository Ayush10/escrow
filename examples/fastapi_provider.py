"""Example: FastAPI provider protected by Verdict Protocol.

This example mirrors the reference provider stack used in the repo:
1. Installs x402 payment middleware for `/api/*`
2. Returns an X-Evidence-Hash header for receipt binding
3. Exposes the same happy/bad paths used by the consumer and demo flows

Run from the repo root:
    uv sync
    cp examples/provider.env.example .env
    uv run python examples/fastapi_provider.py
"""

from __future__ import annotations

import json
import os
import time

from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from provider_api.x402_integration import X402IntegrationError, install_x402
from verdict_protocol import keccak_hex

app = FastAPI(title="Example Provider API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

mode = "disabled"
try:
    mode = install_x402(app)
except X402IntegrationError as exc:
    @app.middleware("http")
    async def strict_gate(request, call_next):
        if request.url.path.startswith("/api/"):
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=500, content={"error": str(exc)})
        return await call_next(request)


@app.get("/api/data")
def data(response: Response, bad: bool = Query(default=False)) -> dict[str, object]:
    """Protected endpoint that matches the canonical repo flow.

    In mock mode, callers must send `x-mock-x402: 1` to simulate payment.
    In live mode, the x402 middleware enforces exact payment on Base Sepolia.
    """
    if bad:
        payload: dict[str, object] = {
            "result": {"unexpected": "bad_format"},
            "timestamp": int(time.time() * 1000),
            "quality": "degraded",
        }
    else:
        payload = {
            "result": "some_data",
            "timestamp": int(time.time() * 1000),
        }

    body_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    evidence_hash = keccak_hex(body_bytes)
    response.headers["X-Evidence-Hash"] = evidence_hash
    return payload


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "example-provider-api",
        "x402_mode": mode,
        "mockMode": os.environ.get("X402_ALLOW_MOCK", "") == "1",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=4000)
