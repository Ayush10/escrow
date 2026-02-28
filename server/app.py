"""Agent Court API server.

FastAPI backend that bridges off-chain judge logic with on-chain smart contract.
Judge reviews evidence via LLM, submits ruling on-chain via web3.

Endpoints:
  POST /deposit          — deposit into contract (proxied)
  POST /dispute          — file dispute + submit arguments
  POST /respond          — defendant responds with arguments
  POST /rule             — trigger judge to review and rule (auto or manual)
  GET  /disputes         — list all disputes
  GET  /disputes/{id}    — get dispute details + ruling
  GET  /balance/{addr}   — check agent balance
  GET  /status           — contract info
"""

import json
import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from web3 import Web3

from judge import AIJudge, TieredCourt, Evidence, JudgeRuling

# --- Config ---
RPC_URL = os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network")
CONTRACT_ADDR = os.environ.get("CONTRACT_ADDRESS", "")
JUDGE_PRIVATE_KEY = os.environ.get("JUDGE_PRIVATE_KEY", "")
CHAIN_ID = int(os.environ.get("CHAIN_ID", "48816"))

# ERC-8004 registries on GOAT Testnet3
IDENTITY_REGISTRY = "0x556089008Fc0a60cD09390Eca93477ca254A5522"
REPUTATION_REGISTRY = "0x52B2e79558ea853D58C2Ac5Ddf9a4387d942b4B4"
VALIDATION_REGISTRY = "0x6193b3EC92f075AB759783A4c8D2dCDa21A71d40"
X402_API = "https://api.x402.goat.network"

ABI = json.loads("""[
    {"inputs":[{"internalType":"address","name":"_judge","type":"address"},{"internalType":"uint256","name":"_minDeposit","type":"uint256"},{"internalType":"uint256","name":"_judgeFee","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},
    {"inputs":[],"name":"deposit","outputs":[],"stateMutability":"payable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"withdraw","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"bytes32","name":"txKey","type":"bytes32"},{"internalType":"bytes32","name":"evidenceHash","type":"bytes32"}],"name":"commitEvidence","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"defendant","type":"address"},{"internalType":"uint256","name":"stake","type":"uint256"},{"internalType":"bytes32","name":"plaintiffEvidence","type":"bytes32"}],"name":"fileDispute","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"disputeId","type":"uint256"},{"internalType":"bytes32","name":"evidence","type":"bytes32"}],"name":"respondDispute","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"disputeId","type":"uint256"},{"internalType":"address","name":"winner","type":"address"}],"name":"submitRuling","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"disputeId","type":"uint256"}],"name":"getDispute","outputs":[{"components":[{"internalType":"address","name":"plaintiff","type":"address"},{"internalType":"address","name":"defendant","type":"address"},{"internalType":"uint256","name":"plaintiffStake","type":"uint256"},{"internalType":"uint256","name":"defendantStake","type":"uint256"},{"internalType":"bytes32","name":"plaintiffEvidence","type":"bytes32"},{"internalType":"bytes32","name":"defendantEvidence","type":"bytes32"},{"internalType":"bool","name":"resolved","type":"bool"},{"internalType":"address","name":"winner","type":"address"}],"internalType":"struct AgentCourt.Dispute","name":"","type":"tuple"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"agent","type":"address"}],"name":"getBalance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"agent","type":"address"}],"name":"isEligible","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"disputeCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"judge","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"minDeposit","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"judgeFee","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"balances","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]""")

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
    argument: str  # plaintiff's off-chain argument

class RespondArgs(BaseModel):
    dispute_id: int
    argument: str  # defendant's off-chain argument

class RuleRequest(BaseModel):
    dispute_id: int
    level: int = 0  # court tier

class TransactionData(BaseModel):
    dispute_id: int
    data: dict  # request, response, terms — whatever the parties want to submit


# --- Endpoints ---

@app.get("/status")
async def status():
    info = {"rpc": RPC_URL, "chain_id": CHAIN_ID, "contract": CONTRACT_ADDR}
    if contract:
        try:
            info["dispute_count"] = contract.functions.disputeCount().call()
            info["min_deposit"] = contract.functions.minDeposit().call()
            info["judge_fee"] = contract.functions.judgeFee().call()
            info["judge"] = contract.functions.judge().call()
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
    eligible = contract.functions.isEligible(addr).call()
    return {"address": addr, "balance": bal, "balance_btc": str(bal / 1e18), "eligible": eligible}


@app.get("/disputes")
async def list_disputes():
    if not contract:
        raise HTTPException(503, "Contract not configured")
    count = contract.functions.disputeCount().call()
    disputes = []
    for i in range(count):
        d = contract.functions.getDispute(i).call()
        disputes.append({
            "id": i,
            "plaintiff": d[0],
            "defendant": d[1],
            "plaintiff_stake": d[2],
            "defendant_stake": d[3],
            "plaintiff_evidence": d[4].hex(),
            "defendant_evidence": d[5].hex(),
            "resolved": d[6],
            "winner": d[7],
            "has_arguments": i in arguments,
            "has_ruling": i in rulings,
        })
    return {"count": count, "disputes": disputes}


@app.get("/disputes/{dispute_id}")
async def get_dispute(dispute_id: int):
    if not contract:
        raise HTTPException(503, "Contract not configured")
    try:
        d = contract.functions.getDispute(dispute_id).call()
    except Exception:
        raise HTTPException(404, "Dispute not found")
    result = {
        "id": dispute_id,
        "plaintiff": d[0],
        "defendant": d[1],
        "plaintiff_stake": d[2],
        "defendant_stake": d[3],
        "plaintiff_evidence": "0x" + d[4].hex(),
        "defendant_evidence": "0x" + d[5].hex(),
        "resolved": d[6],
        "winner": d[7],
        "arguments": arguments.get(dispute_id, {}),
        "ruling": rulings.get(dispute_id),
    }
    return result


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

    Verifies on-chain that:
    1. Dispute exists and is unresolved
    2. Judge fee has been paid (frozen in contract)
    3. Selects judge tier based on on-chain dispute tier
    Then spawns appropriate judge instance and submits ruling.
    """
    if not contract or not judge_account:
        raise HTTPException(503, "Contract or judge key not configured")

    # Fetch dispute from chain — this IS the payment verification
    # If fileDispute() succeeded, the fee is already frozen in the contract
    try:
        d = contract.functions.getDispute(req.dispute_id).call()
    except Exception:
        raise HTTPException(404, "Dispute not found")

    # Dispute struct: transactionId, plaintiff, defendant, stake, judgeFee, tier,
    #                 plaintiffEvidence, defendantEvidence, resolved, winner
    tx_id = d[0]
    plaintiff = d[1]
    defendant = d[2]
    stake = d[3]
    judge_fee_paid = d[4]
    tier = d[5]
    p_evidence = d[6]
    d_evidence = d[7]
    resolved = d[8]
    winner = d[9]

    if resolved:
        raise HTTPException(400, "Dispute already resolved")

    # Verify payment: judge fee must be > 0 (was frozen when dispute filed)
    if judge_fee_paid == 0:
        raise HTTPException(402, "No judge fee paid for this dispute")

    # Fetch the underlying transaction for context
    tx_data = {}
    try:
        t = contract.functions.getTransaction(tx_id).call()
        tx_data = {
            "service_id": t[0],
            "consumer": t[1],
            "provider": t[2],
            "payment": t[3],
            "request_hash": "0x" + t[4].hex(),
            "response_hash": "0x" + t[5].hex(),
        }
    except Exception:
        pass

    # Build evidence
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

    # Spawn judge at the correct tier (on-chain tier determines LLM model)
    # tier 0 = district (GLM-4, cheap), tier 1 = appeals (Sonnet), tier 2 = supreme (Opus)
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
            "gas": 300000,
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

    # Store for potential appeals
    if req.dispute_id not in prior_rulings_store:
        prior_rulings_store[req.dispute_id] = []
    prior_rulings_store[req.dispute_id].append(ruling_dict)

    return ruling_dict


@app.post("/rule/auto")
async def auto_judge_poll():
    """Poll for unresolved disputes and auto-judge them.
    Call this on a cron or let agents trigger /rule manually."""
    if not contract or not judge_account:
        raise HTTPException(503, "Not configured")

    count = contract.functions.disputeCount().call()
    judged = []

    for i in range(count):
        d = contract.functions.getDispute(i).call()
        resolved = d[8]
        if not resolved:
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
