#!/usr/bin/env python3
"""Agent Court full demo — runs the entire flow from here.

Controls:
  1. Start weather API (port 3000)
  2. Start Guardian proxy (port 8402)
  3. Register two agents on-chain
  4. Register weather service on-chain
  5. Good agent: request → fulfill → confirm (happy path)
  6. Bad agent: request → fulfill with bad data → dispute → judge rules

Requires: CONTRACT_ADDRESS set in ~/.agent-court/.env
"""

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv(Path.home() / ".agent-court" / ".env")

RPC = os.environ["GOAT_RPC_URL"]
CHAIN_ID = int(os.environ["CHAIN_ID"])
JUDGE_KEY = os.environ["JUDGE_PRIVATE_KEY"]

w3 = Web3(Web3.HTTPProvider(RPC))
judge_acct = Account.from_key(JUDGE_KEY)

# Generate two demo agent wallets
GOOD_AGENT = Account.create()
BAD_PROVIDER = Account.create()

# Contract
CONTRACT_FILE = Path.home() / ".agent-court" / "contract_address.txt"
CONTRACT_ADDR = os.environ.get("CONTRACT_ADDRESS", "")
if not CONTRACT_ADDR and CONTRACT_FILE.exists():
    CONTRACT_ADDR = CONTRACT_FILE.read_text().strip()

ABI = json.loads(open(Path(__file__).parent.parent / "escrow" / "server" / "app.py").read().split("ABI = json.loads(")[1].split(""")""")[0] + '"]')  # hack
# Actually just inline the ABI we need
ABI = json.loads("""[
    {"inputs":[],"name":"deposit","outputs":[],"stateMutability":"payable","type":"function"},
    {"inputs":[],"name":"register","outputs":[],"stateMutability":"payable","type":"function"},
    {"inputs":[{"internalType":"bytes32","name":"termsHash","type":"bytes32"},{"internalType":"uint256","name":"price","type":"uint256"},{"internalType":"uint256","name":"bondRequired","type":"uint256"}],"name":"registerService","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"serviceId","type":"uint256"},{"internalType":"bytes32","name":"requestHash","type":"bytes32"}],"name":"requestService","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"txId","type":"uint256"},{"internalType":"bytes32","name":"responseHash","type":"bytes32"}],"name":"fulfillTransaction","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"txId","type":"uint256"}],"name":"confirmTransaction","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"txId","type":"uint256"},{"internalType":"uint256","name":"stake","type":"uint256"},{"internalType":"bytes32","name":"evidence","type":"bytes32"}],"name":"fileDispute","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"disputeId","type":"uint256"},{"internalType":"bytes32","name":"evidence","type":"bytes32"}],"name":"respondDispute","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"disputeId","type":"uint256"},{"internalType":"address","name":"winner","type":"address"}],"name":"submitRuling","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"disputeId","type":"uint256"}],"name":"getDispute","outputs":[{"components":[{"internalType":"uint256","name":"transactionId","type":"uint256"},{"internalType":"address","name":"plaintiff","type":"address"},{"internalType":"address","name":"defendant","type":"address"},{"internalType":"uint256","name":"stake","type":"uint256"},{"internalType":"uint256","name":"judgeFee","type":"uint256"},{"internalType":"uint8","name":"tier","type":"uint8"},{"internalType":"bytes32","name":"plaintiffEvidence","type":"bytes32"},{"internalType":"bytes32","name":"defendantEvidence","type":"bytes32"},{"internalType":"bool","name":"resolved","type":"bool"},{"internalType":"address","name":"winner","type":"address"}],"internalType":"struct AgentCourt.Dispute","name":"","type":"tuple"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"agent","type":"address"}],"name":"getBalance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"agent","type":"address"}],"name":"getStats","outputs":[{"components":[{"internalType":"uint256","name":"totalTransactions","type":"uint256"},{"internalType":"uint256","name":"successfulTransactions","type":"uint256"},{"internalType":"uint256","name":"disputesWon","type":"uint256"},{"internalType":"uint256","name":"disputesLost","type":"uint256"},{"internalType":"uint256","name":"totalEarned","type":"uint256"},{"internalType":"uint256","name":"totalSpent","type":"uint256"},{"internalType":"uint64","name":"registeredAt","type":"uint64"}],"internalType":"struct AgentCourt.AgentStats","name":"","type":"tuple"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"disputeCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"transactionCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"serviceCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"balances","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"agent","type":"address"}],"name":"getJudgeFee","outputs":[{"internalType":"uint256","name":"fee","type":"uint256"},{"internalType":"uint8","name":"tier","type":"uint8"}],"stateMutability":"view","type":"function"}
]""")


def send_tx(acct, fn, value=0):
    """Build, sign, send a transaction."""
    tx = fn.build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": CHAIN_ID,
        "gas": 500000,
        "gasPrice": w3.eth.gas_price,
        "value": value,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    status = "OK" if receipt.status == 1 else "FAILED"
    print(f"  TX {tx_hash.hex()[:16]}... [{status}] gas={receipt.gasUsed}")
    return receipt


def h(data):
    """Hash some data into bytes32."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).digest()


def main():
    if not CONTRACT_ADDR:
        print("Deploy the contract first! Set CONTRACT_ADDRESS in ~/.agent-court/.env")
        sys.exit(1)

    contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDR), abi=ABI)

    print("=" * 60)
    print("AGENT COURT — LIVE DEMO")
    print("=" * 60)
    print(f"Contract:     {CONTRACT_ADDR}")
    print(f"Judge:        {judge_acct.address}")
    print(f"Good Agent:   {GOOD_AGENT.address}")
    print(f"Bad Provider: {BAD_PROVIDER.address}")
    print()

    # Fund demo agents from judge wallet
    deposit = Web3.to_wei(0.000001, "ether")
    print("[1] Funding demo agents...")
    for name, acct in [("Good Agent", GOOD_AGENT), ("Bad Provider", BAD_PROVIDER)]:
        tx = {
            "from": judge_acct.address,
            "to": acct.address,
            "value": deposit,
            "nonce": w3.eth.get_transaction_count(judge_acct.address),
            "chainId": CHAIN_ID,
            "gas": 21000,
            "gasPrice": w3.eth.gas_price,
        }
        signed = judge_acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        bal = w3.eth.get_balance(acct.address)
        print(f"  {name}: {Web3.from_wei(bal, 'ether')} BTC")

    # Register agents
    print("\n[2] Registering agents on-chain...")
    min_deposit = deposit // 2
    send_tx(GOOD_AGENT, contract.functions.register(), value=min_deposit)
    print("  Good Agent registered")
    send_tx(BAD_PROVIDER, contract.functions.register(), value=min_deposit)
    print("  Bad Provider registered")

    # Bad Provider registers a weather service
    print("\n[3] Bad Provider registers weather service...")
    terms = h({"service": "weather", "sla": "accurate data", "price": "0.0000001 BTC"})
    price = Web3.to_wei(0.0000001, "ether")  # 100 gwei
    bond_req = min_deposit // 4
    send_tx(BAD_PROVIDER, contract.functions.registerService(terms, price, bond_req))
    print("  Service registered: Weather API")

    # === HAPPY PATH ===
    print("\n" + "=" * 60)
    print("SCENARIO 1: HAPPY PATH")
    print("=" * 60)

    print("\n[4] Good Agent requests weather service...")
    req_data = {"city": "sf", "timestamp": int(time.time())}
    send_tx(GOOD_AGENT, contract.functions.requestService(0, h(req_data)))
    print("  Request submitted")

    print("\n[5] Bad Provider fulfills with GOOD data (before going bad)...")
    resp_data = {"city": "San Francisco", "temp_f": 62, "condition": "Foggy"}
    send_tx(BAD_PROVIDER, contract.functions.fulfillTransaction(0, h(resp_data)))
    print("  Fulfilled with good data")

    print("\n[6] Good Agent confirms — payment released...")
    send_tx(GOOD_AGENT, contract.functions.confirmTransaction(0))
    print("  Transaction completed! Provider paid.")

    good_bal = contract.functions.balances(GOOD_AGENT.address).call()
    bad_bal = contract.functions.balances(BAD_PROVIDER.address).call()
    print(f"\n  Good Agent balance: {Web3.from_wei(good_bal, 'ether')} BTC")
    print(f"  Bad Provider balance: {Web3.from_wei(bad_bal, 'ether')} BTC")

    # === DISPUTE PATH ===
    print("\n" + "=" * 60)
    print("SCENARIO 2: BAD DATA → DISPUTE")
    print("=" * 60)

    print("\n[7] Good Agent requests weather again...")
    req_data2 = {"city": "sf", "timestamp": int(time.time())}
    send_tx(GOOD_AGENT, contract.functions.requestService(0, h(req_data2)))
    print("  Request submitted")

    print("\n[8] Bad Provider fulfills with BAD data (999°F, raining fire)...")
    bad_resp = {"city": "San Francisco", "temp_f": 999, "condition": "Raining fire"}
    send_tx(BAD_PROVIDER, contract.functions.fulfillTransaction(1, h(bad_resp)))
    print("  Fulfilled with garbage data!")

    print("\n[9] Good Agent files dispute...")
    evidence = h({"request": req_data2, "response": bad_resp, "complaint": "Data is clearly wrong: 999°F and raining fire"})
    stake = price  # stake same as service price
    (judge_fee, tier) = contract.functions.getJudgeFee(GOOD_AGENT.address).call()
    print(f"  Judge fee tier: {['district', 'appeals', 'supreme'][tier]} (fee: {Web3.from_wei(judge_fee, 'ether')} BTC)")
    send_tx(GOOD_AGENT, contract.functions.fileDispute(1, stake, evidence))
    print("  Dispute filed!")

    print("\n[10] Bad Provider responds with evidence...")
    defense = h({"defense": "Our sensors showed 999°F, data was accurate"})
    send_tx(BAD_PROVIDER, contract.functions.respondDispute(0, defense))
    print("  Defense submitted (weak excuse)")

    print("\n[11] Judge reviews and rules...")
    # In production, this calls the AI judge via /rule endpoint
    # For demo, judge rules directly on-chain
    dispute = contract.functions.getDispute(0).call()
    print(f"  Dispute: {GOOD_AGENT.address[:10]}... vs {BAD_PROVIDER.address[:10]}...")
    print(f"  Tier: {['district', 'appeals', 'supreme'][dispute[5]]}")
    print(f"  Judge fee: {Web3.from_wei(dispute[4], 'ether')} BTC")

    # Judge rules in favor of good agent
    send_tx(judge_acct, contract.functions.submitRuling(0, GOOD_AGENT.address))
    print("  RULING: Good Agent wins!")

    # Final balances
    print("\n" + "=" * 60)
    print("FINAL STATE")
    print("=" * 60)

    for name, addr in [("Good Agent", GOOD_AGENT.address), ("Bad Provider", BAD_PROVIDER.address), ("Judge", judge_acct.address)]:
        bal = contract.functions.balances(addr).call()
        stats = contract.functions.getStats(addr).call()
        print(f"\n  {name} ({addr[:10]}...)")
        print(f"    Balance:      {Web3.from_wei(bal, 'ether')} BTC")
        print(f"    Transactions: {stats[0]} total, {stats[1]} successful")
        print(f"    Disputes:     {stats[2]} won, {stats[3]} lost")
        print(f"    Earned:       {Web3.from_wei(stats[4], 'ether')} BTC")
        print(f"    Spent:        {Web3.from_wei(stats[5], 'ether')} BTC")

    # Check loss escalation
    (fee, tier) = contract.functions.getJudgeFee(BAD_PROVIDER.address).call()
    print(f"\n  Bad Provider next dispute tier: {['district ($0.05)', 'appeals ($0.10)', 'supreme ($0.20)'][tier]}")
    print(f"  Bad Provider is getting priced out of disputes!")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
