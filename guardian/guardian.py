#!/usr/bin/env python3
"""Agent Court Guardian — reputation-gated reverse proxy with x402 payment.

Drop this in front of any API to get:
  - On-chain reputation check (AgentCourt bond balance)
  - ERC-8004 identity verification
  - x402 payment flow
  - Auto evidence hash commitment
  - Dispute-ready transactions

Usage:
  python3 guardian.py --api http://localhost:3000 --port 8402
  python3 guardian.py --api http://localhost:3000 --min-balance 0.001

Environment:
  GOAT_RPC_URL          — GOAT Testnet3 RPC (default: https://rpc.testnet3.goat.network)
  CONTRACT_ADDRESS      — deployed AgentCourt contract
  GUARDIAN_PRIVATE_KEY  — guardian's wallet key (for committing evidence)
  X402_API              — x402 API base URL
"""

import hashlib
import json
import os
import time
from urllib.parse import urlparse

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from web3 import Web3

# --- Config ---
RPC_URL = os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network")
CONTRACT_ADDR = os.environ.get("CONTRACT_ADDRESS", "")
GUARDIAN_KEY = os.environ.get("GUARDIAN_PRIVATE_KEY", "")
UPSTREAM_API = os.environ.get("UPSTREAM_API", "http://localhost:3000")
MIN_BALANCE = int(os.environ.get("MIN_BALANCE_WEI", "1000000000000000"))  # 0.001 BTC
X402_API = os.environ.get("X402_API", "https://api.x402.goat.network")
CHAIN_ID = int(os.environ.get("CHAIN_ID", "48816"))

# ERC-8004
IDENTITY_REGISTRY = os.environ.get("IDENTITY_REGISTRY", "0x556089008Fc0a60cD09390Eca93477ca254A5522")
REPUTATION_REGISTRY = os.environ.get("REPUTATION_REGISTRY", "0x52B2e79558ea853D58C2Ac5Ddf9a4387d942b4B4")

COURT_ABI = json.loads("""[
    {"inputs":[{"internalType":"address","name":"agent","type":"address"}],"name":"getBalance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"agent","type":"address"}],"name":"isEligible","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"balances","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"bytes32","name":"txKey","type":"bytes32"},{"internalType":"bytes32","name":"evidenceHash","type":"bytes32"}],"name":"commitEvidence","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"agent","type":"address"}],"name":"hasIdentity","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"}
]""")

IDENTITY_ABI = json.loads("""[
    {"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]""")

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
    if CONTRACT_ADDR:
        court = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDR), abi=COURT_ABI)
    if IDENTITY_REGISTRY:
        identity = w3.eth.contract(address=Web3.to_checksum_address(IDENTITY_REGISTRY), abi=IDENTITY_ABI)
    if GUARDIAN_KEY:
        from eth_account import Account
        guardian_acct = Account.from_key(GUARDIAN_KEY)
    print(f"Guardian started")
    print(f"  Upstream: {UPSTREAM_API}")
    print(f"  Contract: {CONTRACT_ADDR or 'NOT SET'}")
    print(f"  Min balance: {Web3.from_wei(MIN_BALANCE, 'ether')} BTC")
    print(f"  Identity check: {bool(identity)}")


def check_reputation(agent_addr: str) -> dict:
    """Check agent's on-chain reputation. Returns status dict."""
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


def commit_evidence_onchain(agent_addr: str, evidence_hash: bytes, nonce: int = 0):
    """Commit evidence hash on-chain (guardian side)."""
    if not court or not guardian_acct:
        return None
    try:
        tx_key = Web3.solidity_keccak(
            ["address", "address", "uint256"],
            [guardian_acct.address, Web3.to_checksum_address(agent_addr), nonce]
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
    rep["balance_btc"] = str(Web3.from_wei(rep["balance"], "ether"))
    rep["min_required_btc"] = str(Web3.from_wei(MIN_BALANCE, "ether"))
    return rep


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "upstream": UPSTREAM_API,
        "contract": CONTRACT_ADDR,
        "connected": w3.is_connected(),
    }


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(request: Request, path: str):
    """Main proxy: check reputation, handle x402, forward to upstream."""

    # Extract agent address from header
    agent_addr = request.headers.get("X-Agent-Address", "")
    if not agent_addr:
        # Check x402 payment header for address
        agent_addr = request.headers.get("X-Payment-Address", "")

    if not agent_addr:
        return JSONResponse(
            status_code=402,
            content={
                "error": "Agent address required",
                "header": "X-Agent-Address",
                "message": "Include your EVM address in X-Agent-Address header",
                "contract": CONTRACT_ADDR,
                "min_deposit": str(Web3.from_wei(MIN_BALANCE, "ether")),
                "deposit_first": f"Deposit at least {Web3.from_wei(MIN_BALANCE, 'ether')} BTC into AgentCourt contract {CONTRACT_ADDR}",
            },
        )

    # Check reputation
    rep = check_reputation(agent_addr)

    if not rep["eligible"]:
        return JSONResponse(
            status_code=402,
            content={
                "error": "Insufficient reputation",
                "balance": str(Web3.from_wei(rep["balance"], "ether")),
                "min_required": str(Web3.from_wei(MIN_BALANCE, "ether")),
                "contract": CONTRACT_ADDR,
                "message": f"Deposit at least {Web3.from_wei(MIN_BALANCE, 'ether')} BTC into the AgentCourt contract to use this API",
                "has_identity": rep["has_identity"],
            },
        )

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

            # Commit evidence hash (async, best-effort)
            evidence_hash = compute_evidence_hash(body, response_body)
            tx_hash = commit_evidence_onchain(agent_addr, evidence_hash)

            # Build response with court metadata
            response_headers = dict(resp.headers)
            response_headers["X-Court-Contract"] = CONTRACT_ADDR
            response_headers["X-Court-Balance"] = str(rep["balance"])
            response_headers["X-Court-Eligible"] = "true"
            if tx_hash:
                response_headers["X-Court-Evidence-TX"] = tx_hash
            if rep["has_identity"]:
                response_headers["X-Court-Identity"] = "verified"

            return JSONResponse(
                status_code=resp.status_code,
                content=json.loads(response_body) if resp.headers.get("content-type", "").startswith("application/json") else {"data": response_body.decode("utf-8", errors="replace")},
                headers=response_headers,
            )

        except httpx.RequestError as e:
            return JSONResponse(
                status_code=502,
                content={"error": f"Upstream error: {str(e)}"},
            )


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Agent Court Guardian Proxy")
    parser.add_argument("--api", default=UPSTREAM_API, help="Upstream API URL")
    parser.add_argument("--port", type=int, default=8402, help="Guardian port")
    parser.add_argument("--min-balance", type=float, default=0.001, help="Min balance in BTC")
    args = parser.parse_args()

    UPSTREAM_API = args.api
    MIN_BALANCE = int(args.min_balance * 1e18)

    uvicorn.run(app, host="0.0.0.0", port=args.port)
