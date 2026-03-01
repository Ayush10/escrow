#!/usr/bin/env python3
"""Agent Court Guardian — reputation-gated reverse proxy with x402 payment.

Drop this in front of any API to get:
  - On-chain reputation check (AgentCourt USDC balance)
  - ERC-8004 identity verification
  - x402 PAYMENT-REQUIRED headers (standard format)
  - Auto evidence hash commitment
  - Dispute-ready transactions

Usage:
  python3 guardian.py --api http://localhost:3000 --port 8402
  python3 guardian.py --api http://localhost:3000 --min-balance 0.10
"""

import base64
import hashlib
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import httpx
from web3 import Web3
from dotenv import load_dotenv

# --- Config ---
load_dotenv(Path.home() / ".agent-court" / ".env")

RPC_URL = os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network")
CHAIN_ID = int(os.environ.get("CHAIN_ID", "48816"))
GUARDIAN_KEY = os.environ.get("GUARDIAN_PRIVATE_KEY", os.environ.get("JUDGE_PRIVATE_KEY", ""))
UPSTREAM_API = os.environ.get("UPSTREAM_API", "http://localhost:3000")
MIN_BALANCE = int(os.environ.get("MIN_BALANCE_USDC", "100000"))  # 0.10 USDC (6 decimals)

# USDC on GOAT testnet3
USDC_ADDRESS = "0x29d1ee93e9ecf6e50f309f498e40a6b42d352fa1"

# Load contract
_addr_file = Path.home() / ".agent-court" / "contract_address.txt"
CONTRACT_ADDR = os.environ.get("CONTRACT_ADDRESS", "")
if not CONTRACT_ADDR and _addr_file.exists():
    CONTRACT_ADDR = _addr_file.read_text().strip()

_abi_file = Path.home() / ".agent-court" / "abi.json"
ABI = json.loads(_abi_file.read_text()) if _abi_file.exists() else []

IDENTITY_REGISTRY = os.environ.get("IDENTITY_REGISTRY", "0x556089008Fc0a60cD09390Eca93477ca254A5522")
IDENTITY_ABI = json.loads('[{"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]')

# --- Init ---
w3 = Web3(Web3.HTTPProvider(RPC_URL))
court = None
identity = None
guardian_acct = None

app = FastAPI(title="Agent Court Guardian")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    global court, identity, guardian_acct
    if CONTRACT_ADDR and ABI:
        court = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDR), abi=ABI)
    if IDENTITY_REGISTRY:
        identity = w3.eth.contract(address=Web3.to_checksum_address(IDENTITY_REGISTRY), abi=IDENTITY_ABI)
    if GUARDIAN_KEY:
        from eth_account import Account
        guardian_acct = Account.from_key(GUARDIAN_KEY)
    print(f"Guardian started")
    print(f"  Upstream: {UPSTREAM_API}")
    print(f"  Contract: {CONTRACT_ADDR or 'NOT SET'}")
    print(f"  Min balance: {MIN_BALANCE / 1e6} USDC")
    print(f"  Identity check: {bool(identity)}")
    print(f"  USDC: {USDC_ADDRESS}")


def make_x402_payment_required(agent_addr: str = "") -> Response:
    """Return a proper x402 402 response with PAYMENT-REQUIRED header."""
    payment_required = {
        "x402_version": 1,
        "accepts": [{
            "scheme": "exact",
            "network": f"eip155:{CHAIN_ID}",
            "asset": USDC_ADDRESS,
            "amount": str(MIN_BALANCE),
            "pay_to": CONTRACT_ADDR,
            "max_timeout_seconds": 300,
            "extra": {
                "method": "register_and_deposit",
                "min_deposit": str(MIN_BALANCE),
                "identity_required": True,
                "identity_registry": IDENTITY_REGISTRY,
            },
        }],
        "resource": {
            "url": UPSTREAM_API,
            "description": "Agent Court protected API",
        },
    }
    encoded = base64.b64encode(json.dumps(payment_required).encode()).decode()

    return Response(
        status_code=402,
        content=json.dumps({
            "error": "Payment Required",
            "message": f"Deposit at least {MIN_BALANCE / 1e6} USDC into AgentCourt contract",
            "contract": CONTRACT_ADDR,
            "usdc": USDC_ADDRESS,
            "identity_registry": IDENTITY_REGISTRY,
            "network": f"eip155:{CHAIN_ID}",
        }),
        media_type="application/json",
        headers={"PAYMENT-REQUIRED": encoded},
    )


def check_reputation(agent_addr: str) -> dict:
    """Check agent's on-chain reputation."""
    addr = Web3.to_checksum_address(agent_addr)
    result = {"address": addr, "eligible": False, "balance": 0, "has_identity": False}

    if court:
        try:
            result["balance"] = court.functions.balances(addr).call()
            result["eligible"] = result["balance"] >= MIN_BALANCE
        except Exception as e:
            result["court_error"] = str(e)

    if identity:
        try:
            result["has_identity"] = identity.functions.balanceOf(addr).call() > 0
        except Exception as e:
            result["identity_error"] = str(e)

    return result


def compute_evidence_hash(request_data: bytes, response_data: bytes) -> bytes:
    """Hash(request + response + timestamp) for evidence commitment."""
    ts = str(int(time.time())).encode()
    return hashlib.sha256(request_data + response_data + ts).digest()


def commit_evidence_onchain(agent_addr: str, evidence_hash: bytes):
    """Commit evidence hash on-chain."""
    if not court or not guardian_acct:
        return None
    try:
        tx_key = Web3.solidity_keccak(
            ["address", "address", "uint256"],
            [guardian_acct.address, Web3.to_checksum_address(agent_addr), int(time.time())]
        )
        tx = court.functions.commitEvidence(tx_key, evidence_hash).build_transaction({
            "from": guardian_acct.address,
            "nonce": w3.eth.get_transaction_count(guardian_acct.address),
            "chainId": CHAIN_ID,
            "gas": 100000,
            "gasPrice": w3.eth.gas_price,
        })
        signed = guardian_acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()
    except Exception as e:
        print(f"Evidence commit failed: {e}")
        return None


@app.get("/reputation/{address}")
async def get_reputation(address: str):
    """Public endpoint: check any agent's reputation."""
    rep = check_reputation(address)
    rep["balance_usdc"] = rep["balance"] / 1e6
    rep["min_required_usdc"] = MIN_BALANCE / 1e6
    return rep


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "upstream": UPSTREAM_API,
        "contract": CONTRACT_ADDR,
        "connected": w3.is_connected(),
        "payment_token": USDC_ADDRESS,
    }


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(request: Request, path: str):
    """Main proxy: check reputation, return x402 if insufficient, forward to upstream."""

    # Extract agent address from header or x402 payment
    agent_addr = request.headers.get("X-Agent-Address", "")
    if not agent_addr:
        agent_addr = request.headers.get("X-Payment-Address", "")

    if not agent_addr:
        return make_x402_payment_required()

    # Check reputation
    rep = check_reputation(agent_addr)

    if not rep["eligible"]:
        return make_x402_payment_required(agent_addr)

    # Agent is eligible — forward request to upstream
    body = await request.body()

    async with httpx.AsyncClient() as client:
        try:
            upstream_url = f"{UPSTREAM_API}/{path}"
            headers = dict(request.headers)
            headers.pop("host", None)

            resp = await client.request(
                method=request.method,
                url=upstream_url,
                headers=headers,
                content=body,
                timeout=30,
            )

            response_body = resp.content

            # Commit evidence hash (best-effort, don't block response)
            evidence_hash = compute_evidence_hash(body, response_body)
            tx_hash = commit_evidence_onchain(agent_addr, evidence_hash)

            # Build response with court metadata headers
            response_headers = {}
            response_headers["X-Court-Contract"] = CONTRACT_ADDR
            response_headers["X-Court-Balance"] = str(rep["balance"])
            response_headers["X-Court-Balance-USDC"] = str(rep["balance"] / 1e6)
            response_headers["X-Court-Eligible"] = "true"
            response_headers["X-Court-Network"] = f"eip155:{CHAIN_ID}"
            if tx_hash:
                response_headers["X-Court-Evidence-TX"] = tx_hash
            if rep["has_identity"]:
                response_headers["X-Court-Identity"] = "verified"

            # Return upstream response with court headers
            return Response(
                status_code=resp.status_code,
                content=response_body,
                media_type=resp.headers.get("content-type", "application/json"),
                headers=response_headers,
            )

        except httpx.RequestError as e:
            return JSONResponse(status_code=502, content={"error": f"Upstream error: {str(e)}"})


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Agent Court Guardian Proxy")
    parser.add_argument("--api", default=UPSTREAM_API, help="Upstream API URL")
    parser.add_argument("--port", type=int, default=8402, help="Guardian port")
    parser.add_argument("--min-balance", type=float, default=0.10, help="Min balance in USDC")
    args = parser.parse_args()

    UPSTREAM_API = args.api
    MIN_BALANCE = int(args.min_balance * 1e6)

    uvicorn.run(app, host="0.0.0.0", port=args.port)
