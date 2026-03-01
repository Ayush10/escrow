from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from web3 import Web3

from .orchestrator import get_manager, serialize_run

app = FastAPI(title="Verdict Demo Runner", version="0.1.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
manager = get_manager()

DEFAULT_ESCROW_CONTRACT = "0xFBf9b5293A1737AC53880d3160a64B49bA54801D"


def _contract_sanity() -> dict[str, Any]:
    rpc_url = os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network")
    contract_address = os.environ.get("ESCROW_CONTRACT_ADDRESS", DEFAULT_ESCROW_CONTRACT)
    dry_run = os.environ.get("ESCROW_DRY_RUN", "0") == "1"
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        connected = w3.is_connected()
        code_size = len(w3.eth.get_code(Web3.to_checksum_address(contract_address))) if connected else 0
        has_code = code_size > 0
    except Exception:
        connected = False
        code_size = 0
        has_code = False
    return {
        "rpcConnected": connected,
        "contractAddress": contract_address,
        "contractHasCode": has_code,
        "contractCodeSize": code_size,
        "dryRun": dry_run,
    }


class RunRequest(BaseModel):
    mode: str = Field(..., pattern="^(happy|dispute|full)$")
    startServices: bool = True
    keepServices: bool = False
    autoRun: bool = True
    agreementWindowSec: int = 30


class RunStartRequest(BaseModel):
    agreementWindowSec: int = 30


class DashboardPaymentRequest(BaseModel):
    token: str = "USDC"
    amount: str = "0.001"
    recipient: str | None = None
    agentName: str = "Ayush + Karan and Verdict Protocol"
    agentDescription: str = "Signature identity for Verdict Protocol agent payments"
    dryRun: bool = False
    requestFaucet: bool = False


@app.get("/health")
def health() -> dict[str, Any]:
    sanity = _contract_sanity()
    status = "ok"
    if (not sanity["contractHasCode"]) and (not sanity["dryRun"]):
        status = "degraded"
    return {
        "status": status,
        "service": "demo-runner",
        "contractAddress": sanity["contractAddress"],
        "chainId": int(os.environ.get("GOAT_CHAIN_ID", "48816")),
        "chainRpc": os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network"),
        "explorer": os.environ.get("GOAT_EXPLORER_URL", "https://explorer.testnet3.goat.network"),
        "escrow": sanity,
        "ports": {
            "evidence": 4001,
            "provider": 4000,
            "judge": 4002,
            "reputation": 4003,
            "runner": int(os.environ.get("DEMO_RUNNER_PORT", "4004")),
        },
    }


@app.get("/config")
def config() -> dict[str, Any]:
    sanity = _contract_sanity()
    runner_port = int(os.environ.get("DEMO_RUNNER_PORT", "4004"))
    return {
        "contractAddress": sanity["contractAddress"],
        "chainId": int(os.environ.get("GOAT_CHAIN_ID", "48816")),
        "chainRpc": os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network"),
        "explorerUrl": os.environ.get("GOAT_EXPLORER_URL", "https://explorer.testnet3.goat.network"),
        "escrow": sanity,
        "services": {
            "evidence": "http://127.0.0.1:4001",
            "provider": "http://127.0.0.1:4000",
            "judge": "http://127.0.0.1:4002",
            "reputation": "http://127.0.0.1:4003",
            "runner": f"http://127.0.0.1:{runner_port}",
        },
        "payment": {
            "network": os.environ.get("X402_NETWORK", "eip155:84532"),
            "asset": os.environ.get("X402_PAYMENT_ASSET", "USDC"),
        },
    }


@app.get("/runs")
def list_runs() -> dict[str, Any]:
    return {"runs": [serialize_run(run) for run in manager.list_runs()]}


@app.post("/runs")
async def create_run(payload: RunRequest) -> dict[str, Any]:
    run = manager.create_run(
        payload.mode,
        start_services=payload.startServices,
        keep_services=payload.keepServices,
        agreement_window_sec=payload.agreementWindowSec,
        auto_run=payload.autoRun,
    )
    return {
        "runId": run.run_id,
        "status": run.status,
        "mode": run.mode,
    }


@app.post("/runs/{run_id}/start")
async def start_run(run_id: str, payload: RunStartRequest) -> dict[str, Any]:
    run = manager.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_not_found")

    asyncio.create_task(manager.start(run_id, agreement_window_sec=payload.agreementWindowSec))
    return {"runId": run_id, "status": run.status}


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    run = manager.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_not_found")
    return serialize_run(run)


@app.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str) -> dict[str, Any]:
    ok = await manager.cancel(run_id)
    return {"ok": ok}


@app.get("/runs/{run_id}/stream")
async def run_stream(run_id: str) -> StreamingResponse:
    queue = manager.subscribe(run_id)

    async def stream() -> Any:
        # Replay existing events and then emit live updates.
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=10)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                if not message:
                    return
                yield f"data: {message}\n\n"
        except asyncio.CancelledError:
            return

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/dashboard-payment")
async def dashboard_payment(payload: DashboardPaymentRequest) -> dict[str, Any]:
    cmd_env = os.environ.copy()
    cmd_env["DASHBOARD_PAYMENT_TOKEN"] = payload.token
    cmd_env["DASHBOARD_PAYMENT_AMOUNT"] = payload.amount
    cmd_env["DASHBOARD_AGENT_NAME"] = payload.agentName
    cmd_env["DASHBOARD_AGENT_DESCRIPTION"] = payload.agentDescription
    cmd_env["DASHBOARD_PAYMENT_DRY_RUN"] = "1" if payload.dryRun else "0"
    cmd_env["DASHBOARD_REQUEST_FAUCET"] = "1" if payload.requestFaucet else "0"
    if payload.recipient:
        cmd_env["DASHBOARD_AGENT_RECIPIENT"] = payload.recipient

    proc = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "--package",
        "demo-runner",
        "python",
        "-m",
        "demo_runner.push_dashboard_payment",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=cmd_env,
        cwd=os.getcwd(),
    )
    stdout_bytes, stderr_bytes = await proc.communicate()
    stdout = (stdout_bytes or b"").decode("utf-8", errors="ignore").strip()
    stderr = (stderr_bytes or b"").decode("utf-8", errors="ignore").strip()
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=stderr or "dashboard payment failed")

    try:
        return json.loads(stdout)
    except Exception:
        return {"status": "ok", "output": stdout, "stderr": stderr}


@app.get("/health/services")
def service_health() -> dict[str, Any]:
    # Compatibility with UI calls from dashboards that also call a services aggregate endpoint.
    return manager.health()


def main() -> None:
    import uvicorn

    port = int(os.environ.get("DEMO_RUNNER_PORT", "4004"))
    uvicorn.run("demo_runner.server:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
