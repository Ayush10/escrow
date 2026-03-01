"""Agent Court API server.

FastAPI backend that bridges off-chain judge logic with on-chain smart contract.
Judge reviews evidence via LLM, submits ruling on-chain via web3.

Endpoints:
  POST /dispute/argue    — plaintiff submits off-chain argument
  POST /dispute/respond  — defendant submits off-chain argument
  POST /dispute/data     — submit transaction data (request, response, terms)
  POST /rule             — trigger judge to review and rule
  POST /rule/auto        — poll and judge all unresolved disputes
  GET  /disputes         — list all disputes
  GET  /disputes/{id}    — get dispute details + ruling
  GET  /balance/{addr}   — check agent balance (USDC)
  GET  /status           — contract info
"""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from web3 import Web3
from dotenv import load_dotenv

from judge import AIJudge, TieredCourt, Evidence, JudgeRuling

# --- Config ---
load_dotenv(Path.home() / ".agent-court" / ".env")

RPC_URL = os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network")
CHAIN_ID = int(os.environ.get("CHAIN_ID", "48816"))
JUDGE_PRIVATE_KEY = os.environ.get("JUDGE_PRIVATE_KEY", "")

# Load contract address and ABI from files
_addr_file = Path.home() / ".agent-court" / "contract_address.txt"
CONTRACT_ADDR = os.environ.get("CONTRACT_ADDRESS", "")
if not CONTRACT_ADDR and _addr_file.exists():
    CONTRACT_ADDR = _addr_file.read_text().strip()

_abi_file = Path.home() / ".agent-court" / "abi.json"
ABI = json.loads(_abi_file.read_text()) if _abi_file.exists() else []

# --- State ---
# Off-chain arguments storage (on-chain only stores hashes)
arguments: dict[int, dict[str, str]] = {}  # dispute_id -> {plaintiff: "...", defendant: "..."}
rulings: dict[int, dict] = {}  # dispute_id -> ruling dict
prior_rulings_store: dict[int, list[dict]] = {}  # dispute_id -> list of prior rulings

w3: Web3 = None
contract = None
judge_account = None
court: TieredCourt = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global w3, contract, judge_account, court
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if CONTRACT_ADDR:
        contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDR), abi=ABI)
    if JUDGE_PRIVATE_KEY:
        judge_account = w3.eth.account.from_key(JUDGE_PRIVATE_KEY)
    court = TieredCourt()
    print(f"Agent Court API running")
    print(f"  RPC: {RPC_URL}")
    print(f"  Contract: {CONTRACT_ADDR or 'NOT SET'}")
    print(f"  Judge: {judge_account.address if judge_account else 'NOT SET'}")
    print(f"  Chain ID: {CHAIN_ID}")
    yield


app = FastAPI(title="Agent Court", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# --- Request Models ---
class DisputeArgs(BaseModel):
    dispute_id: int
    argument: str

class RespondArgs(BaseModel):
    dispute_id: int
    argument: str

class RuleRequest(BaseModel):
    dispute_id: int
    level: int = 0  # court tier (overridden by on-chain tier)

class TransactionData(BaseModel):
    dispute_id: int
    data: dict


# --- Endpoints ---

@app.get("/status")
async def status():
    info = {"rpc": RPC_URL, "chain_id": CHAIN_ID, "contract": CONTRACT_ADDR}
    if contract:
        try:
            info["dispute_count"] = contract.functions.disputeCount().call()
            info["service_count"] = contract.functions.serviceCount().call()
            info["transaction_count"] = contract.functions.transactionCount().call()
            info["min_deposit"] = contract.functions.minDeposit().call()
            info["judge"] = contract.functions.judge().call()
            info["payment_token"] = contract.functions.paymentToken().call()
            info["require_identity"] = contract.functions.requireIdentity().call()
            info["connected"] = True
        except Exception as e:
            info["error"] = str(e)
            info["connected"] = False
    else:
        info["connected"] = False
    return info


@app.get("/balance/{address}")
async def get_balance(address: str):
    if not contract:
        raise HTTPException(503, "Contract not configured")
    addr = Web3.to_checksum_address(address)
    bal = contract.functions.balances(addr).call()
    return {"address": addr, "balance": bal, "balance_usdc": bal / 1e6, "eligible": contract.functions.isEligible(addr).call()}


@app.get("/disputes")
async def list_disputes():
    if not contract:
        raise HTTPException(503, "Contract not configured")
    count = contract.functions.disputeCount().call()
    result = []
    for i in range(count):
        d = contract.functions.getDispute(i).call()
        result.append({
            "id": i,
            "transaction_id": d[0],
            "plaintiff": d[1],
            "defendant": d[2],
            "stake": d[3],
            "judge_fee": d[4],
            "tier": d[5],
            "resolved": d[8],
            "winner": d[9],
            "has_arguments": i in arguments,
            "has_ruling": i in rulings,
        })
    return {"count": count, "disputes": result}


@app.get("/disputes/{dispute_id}")
async def get_dispute(dispute_id: int):
    if not contract:
        raise HTTPException(503, "Contract not configured")
    try:
        d = contract.functions.getDispute(dispute_id).call()
    except Exception:
        raise HTTPException(404, "Dispute not found")
    return {
        "id": dispute_id,
        "transaction_id": d[0],
        "plaintiff": d[1],
        "defendant": d[2],
        "stake": d[3],
        "judge_fee": d[4],
        "tier": d[5],
        "plaintiff_evidence": "0x" + d[6].hex(),
        "defendant_evidence": "0x" + d[7].hex(),
        "resolved": d[8],
        "winner": d[9],
        "arguments": arguments.get(dispute_id, {}),
        "ruling": rulings.get(dispute_id),
    }


@app.post("/dispute/argue")
async def submit_argument(args: DisputeArgs):
    """Plaintiff submits their off-chain argument."""
    if args.dispute_id not in arguments:
        arguments[args.dispute_id] = {}
    arguments[args.dispute_id]["plaintiff"] = args.argument
    return {"ok": True, "dispute_id": args.dispute_id, "side": "plaintiff"}


@app.post("/dispute/respond")
async def submit_response(args: RespondArgs):
    """Defendant submits their off-chain counter-argument."""
    if args.dispute_id not in arguments:
        arguments[args.dispute_id] = {}
    arguments[args.dispute_id]["defendant"] = args.argument
    return {"ok": True, "dispute_id": args.dispute_id, "side": "defendant"}


@app.post("/dispute/data")
async def submit_transaction_data(data: TransactionData):
    """Submit off-chain transaction data (request, response, terms)."""
    if data.dispute_id not in arguments:
        arguments[data.dispute_id] = {}
    arguments[data.dispute_id]["transaction_data"] = data.data
    return {"ok": True}


@app.post("/rule")
async def trigger_ruling(req: RuleRequest):
    """Trigger the AI judge to review evidence and submit ruling on-chain.

    Reads dispute from chain, verifies fee was paid, calls AI judge at the
    correct tier, then submits ruling on-chain.
    """
    if not contract or not judge_account:
        raise HTTPException(503, "Contract or judge key not configured")

    try:
        d = contract.functions.getDispute(req.dispute_id).call()
    except Exception:
        raise HTTPException(404, "Dispute not found")

    # Unpack dispute struct
    tx_id, plaintiff, defendant, stake = d[0], d[1], d[2], d[3]
    judge_fee_paid, tier = d[4], d[5]
    p_evidence, d_evidence = d[6], d[7]
    resolved, winner = d[8], d[9]

    if resolved:
        raise HTTPException(400, "Dispute already resolved")
    if judge_fee_paid == 0:
        raise HTTPException(402, "No judge fee paid for this dispute")

    # Fetch underlying transaction for context
    tx_data = {}
    try:
        t = contract.functions.getTransaction(tx_id).call()
        tx_data = {
            "service_id": t[0], "consumer": t[1], "provider": t[2],
            "payment": t[3], "request_hash": "0x" + t[4].hex(),
            "response_hash": "0x" + t[5].hex(),
        }
    except Exception:
        pass

    # Build evidence bundle
    args = arguments.get(req.dispute_id, {})
    evidence = Evidence(
        dispute_id=req.dispute_id,
        plaintiff=plaintiff,
        defendant=defendant,
        plaintiff_stake=stake,
        defendant_stake=stake,
        plaintiff_evidence="0x" + p_evidence.hex(),
        defendant_evidence="0x" + d_evidence.hex(),
        plaintiff_argument=args.get("plaintiff", "(no argument submitted)"),
        defendant_argument=args.get("defendant", "(no argument submitted)"),
        transaction_data={**tx_data, **args.get("transaction_data", {})},
    )

    # Call AI judge at the on-chain tier
    prior = prior_rulings_store.get(req.dispute_id, [])
    ruling = await court.rule(evidence, level=tier, prior_rulings=prior)

    # Determine winner address
    winner_addr = plaintiff if ruling.winner == "plaintiff" else defendant

    # Submit ruling on-chain
    try:
        nonce = w3.eth.get_transaction_count(judge_account.address)
        tx = contract.functions.submitRuling(req.dispute_id, winner_addr).build_transaction({
            "from": judge_account.address,
            "nonce": nonce,
            "chainId": CHAIN_ID,
            "gas": 500000,
            "gasPrice": w3.eth.gas_price,
        })
        signed = judge_account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        on_chain = {"tx_hash": tx_hash.hex(), "block": receipt.blockNumber, "status": receipt.status}
    except Exception as e:
        on_chain = {"error": str(e)}

    # Store ruling
    ruling_dict = ruling.to_dict()
    ruling_dict["winner_address"] = winner_addr
    ruling_dict["judge_fee_paid"] = judge_fee_paid
    ruling_dict["tier"] = tier
    ruling_dict["tier_name"] = ["district", "appeals", "supreme"][min(tier, 2)]
    ruling_dict["on_chain"] = on_chain

    rulings[req.dispute_id] = ruling_dict

    if req.dispute_id not in prior_rulings_store:
        prior_rulings_store[req.dispute_id] = []
    prior_rulings_store[req.dispute_id].append(ruling_dict)

    return ruling_dict


@app.post("/rule/auto")
async def auto_judge_poll():
    """Poll for unresolved disputes and auto-judge them."""
    if not contract or not judge_account:
        raise HTTPException(503, "Not configured")

    count = contract.functions.disputeCount().call()
    judged = []

    for i in range(count):
        d = contract.functions.getDispute(i).call()
        if not d[8]:  # not resolved
            try:
                result = await trigger_ruling(RuleRequest(dispute_id=i))
                judged.append({"dispute_id": i, "result": result})
            except Exception as e:
                judged.append({"dispute_id": i, "error": str(e)})

    return {"judged": len(judged), "results": judged}


# --- Serve frontend ---
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "judge-frontend")

@app.get("/")
async def serve_frontend():
    index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "Agent Court API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8402)
