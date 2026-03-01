#!/usr/bin/env python3
"""Agent Court full demo — runs the entire flow end-to-end.

Starts all services, runs through:
  1. ERC-8004 identity registration
  2. USDC approval + AgentCourt registration
  3. Service registration
  4. Happy path: request → fulfill → confirm (through Guardian proxy)
  5. Dispute path: bad data → dispute → AI judge ruling (through app.py server)

Requires: USDC funded in judge wallet, contract deployed.
"""

import asyncio
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv(Path.home() / ".agent-court" / ".env")

RPC = os.environ["GOAT_RPC_URL"]
CHAIN_ID = int(os.environ["CHAIN_ID"])
JUDGE_KEY = os.environ["JUDGE_PRIVATE_KEY"]

w3 = Web3(Web3.HTTPProvider(RPC))
judge_acct = Account.from_key(JUDGE_KEY)

# Persistent demo agent wallets
GOOD_AGENT = Account.from_key(os.environ["GOOD_AGENT_KEY"])
BAD_PROVIDER = Account.from_key(os.environ["BAD_PROVIDER_KEY"])

# Contract
CONTRACT_FILE = Path.home() / ".agent-court" / "contract_address.txt"
CONTRACT_ADDR = os.environ.get("CONTRACT_ADDRESS", "")
if not CONTRACT_ADDR and CONTRACT_FILE.exists():
    CONTRACT_ADDR = CONTRACT_FILE.read_text().strip()

_abi_file = Path.home() / ".agent-court" / "abi.json"
ABI = json.loads(_abi_file.read_text())

# USDC on GOAT testnet3 (6 decimals)
USDC_ADDRESS = "0x29d1ee93e9ecf6e50f309f498e40a6b42d352fa1"
USDC_ABI = json.loads('[{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"}]')

# ERC-8004 IdentityRegistry
IDENTITY_REGISTRY = "0x556089008Fc0a60cD09390Eca93477ca254A5522"
IDENTITY_ABI = json.loads("""[
    {"inputs":[{"internalType":"string","name":"tokenURI_","type":"string"}],"name":"register","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]""")

# Judge server
JUDGE_SERVER = "http://localhost:8402"


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


def usdc(amount):
    """Convert USDC amount (float) to 6-decimal integer."""
    return int(amount * 1e6)


def main():
    if not CONTRACT_ADDR:
        print("Deploy the contract first! Set CONTRACT_ADDRESS in ~/.agent-court/.env")
        sys.exit(1)

    contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDR), abi=ABI)
    usdc_token = w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI)
    identity = w3.eth.contract(address=Web3.to_checksum_address(IDENTITY_REGISTRY), abi=IDENTITY_ABI)

    print("=" * 60)
    print("AGENT COURT — LIVE DEMO (USDC)")
    print("=" * 60)
    print(f"Contract:     {CONTRACT_ADDR}")
    print(f"USDC:         {USDC_ADDRESS}")
    print(f"Judge:        {judge_acct.address}")
    print(f"Good Agent:   {GOOD_AGENT.address}")
    print(f"Bad Provider: {BAD_PROVIDER.address}")
    print()

    # Check USDC balance of judge
    judge_usdc = usdc_token.functions.balanceOf(judge_acct.address).call()
    print(f"Judge USDC balance: {judge_usdc / 1e6}")
    if judge_usdc < usdc(0.10):
        print("ERROR: Judge needs at least 0.10 USDC to fund demo agents")
        print(f"Send USDC to {judge_acct.address} on GOAT Testnet3")
        sys.exit(1)

    # [1] Fund demo agents with gas (native BTC for tx fees) + USDC
    print("\n[1] Funding demo agents...")
    gas_deposit = Web3.to_wei(0.000005, "ether")
    usdc_per_agent = usdc(0.05)  # 0.05 USDC each (1/10th for testing)

    for name, acct in [("Good Agent", GOOD_AGENT), ("Bad Provider", BAD_PROVIDER)]:
        # Gas for tx fees
        bal = w3.eth.get_balance(acct.address)
        if bal < gas_deposit:
            tx = {
                "from": judge_acct.address, "to": acct.address,
                "value": gas_deposit,
                "nonce": w3.eth.get_transaction_count(judge_acct.address),
                "chainId": CHAIN_ID, "gas": 21000, "gasPrice": w3.eth.gas_price,
            }
            signed = judge_acct.sign_transaction(tx)
            w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(signed.raw_transaction))

        # USDC
        agent_usdc = usdc_token.functions.balanceOf(acct.address).call()
        if agent_usdc < usdc_per_agent:
            send_tx(judge_acct, usdc_token.functions.transfer(acct.address, usdc_per_agent))
        agent_usdc = usdc_token.functions.balanceOf(acct.address).call()
        print(f"  {name}: {agent_usdc / 1e6} USDC, {Web3.from_wei(w3.eth.get_balance(acct.address), 'ether')} BTC (gas)")

    # [2] ERC-8004 identity registration (skip if already registered)
    print("\n[2] Registering agents with ERC-8004...")
    for name, acct, uri in [
        ("Good Agent", GOOD_AGENT, "https://agent-court.notruefireman.org/agents/good-agent"),
        ("Bad Provider", BAD_PROVIDER, "https://agent-court.notruefireman.org/agents/bad-provider"),
    ]:
        has_id = identity.functions.balanceOf(acct.address).call()
        if has_id > 0:
            print(f"  {name}: already has ERC-8004 identity")
        else:
            send_tx(acct, identity.functions.register(uri))
            print(f"  {name}: ERC-8004 identity registered")

    # [3] Approve USDC + register in AgentCourt (skip if already registered)
    print("\n[3] Registering agents in AgentCourt...")
    deposit_amount = usdc(0.02)  # 0.02 USDC deposit (1/10th for testing)

    for name, acct in [("Good Agent", GOOD_AGENT), ("Bad Provider", BAD_PROVIDER)]:
        if contract.functions.isRegistered(acct.address).call():
            print(f"  {name}: already registered")
            # Top up if low
            bal = contract.functions.balances(acct.address).call()
            if bal < usdc(0.01):
                send_tx(acct, usdc_token.functions.approve(CONTRACT_ADDR, deposit_amount))
                send_tx(acct, contract.functions.deposit(deposit_amount))
                print(f"  {name}: topped up {deposit_amount / 1e6} USDC")
        else:
            send_tx(acct, usdc_token.functions.approve(CONTRACT_ADDR, deposit_amount))
            send_tx(acct, contract.functions.register(deposit_amount))
            print(f"  {name}: registered + deposited {deposit_amount / 1e6} USDC")

    # [4] Bad Provider registers a weather service
    print("\n[4] Bad Provider registers weather service...")
    terms = h({"service": "weather", "sla": "accurate data", "price": "0.05 USDC"})
    price = usdc(0.005)    # $0.005 per call (1/10th for testing)
    bond_req = usdc(0.01)  # need at least $0.01 in bond
    svc_id = contract.functions.serviceCount().call()
    send_tx(BAD_PROVIDER, contract.functions.registerService(terms, price, bond_req))
    print(f"  Service registered: Weather API (ID: {svc_id}, price: $0.05)")

    # === HAPPY PATH ===
    print("\n" + "=" * 60)
    print("SCENARIO 1: HAPPY PATH")
    print("=" * 60)

    print("\n[5] Good Agent requests weather service...")
    req_data = {"city": "sf", "timestamp": int(time.time())}
    tx1_id = contract.functions.transactionCount().call()
    send_tx(GOOD_AGENT, contract.functions.requestService(svc_id, h(req_data)))
    print(f"  Request submitted (TX ID: {tx1_id})")

    print("\n[6] Bad Provider fulfills with GOOD data...")
    resp_data = {"city": "San Francisco", "temp_f": 62, "condition": "Foggy"}
    send_tx(BAD_PROVIDER, contract.functions.fulfillTransaction(tx1_id, h(resp_data)))
    print("  Fulfilled with good data")

    print("\n[7] Good Agent confirms — payment released...")
    send_tx(GOOD_AGENT, contract.functions.confirmTransaction(tx1_id))
    print("  Transaction completed! Provider paid.")

    good_bal = contract.functions.balances(GOOD_AGENT.address).call()
    bad_bal = contract.functions.balances(BAD_PROVIDER.address).call()
    print(f"\n  Good Agent balance: {good_bal / 1e6} USDC")
    print(f"  Bad Provider balance: {bad_bal / 1e6} USDC")

    # === DISPUTE PATH ===
    print("\n" + "=" * 60)
    print("SCENARIO 2: BAD DATA → DISPUTE → AI JUDGE")
    print("=" * 60)

    print("\n[8] Good Agent requests weather again...")
    req_data2 = {"city": "sf", "timestamp": int(time.time())}
    tx2_id = contract.functions.transactionCount().call()
    send_tx(GOOD_AGENT, contract.functions.requestService(svc_id, h(req_data2)))
    print(f"  Request submitted (TX ID: {tx2_id})")

    print("\n[9] Bad Provider fulfills with BAD data (999°F, raining fire)...")
    bad_resp = {"city": "San Francisco", "temp_f": 999, "condition": "Raining fire", "humidity": -50}
    send_tx(BAD_PROVIDER, contract.functions.fulfillTransaction(tx2_id, h(bad_resp)))
    print("  Fulfilled with garbage data!")

    print("\n[10] Good Agent files dispute...")
    evidence = h({"request": req_data2, "response": bad_resp, "complaint": "Data is clearly wrong"})
    stake = usdc(0.001)
    (judge_fee, tier) = contract.functions.getJudgeFee(GOOD_AGENT.address).call()
    print(f"  Judge fee tier: {['district ($0.05)', 'appeals ($0.10)', 'supreme ($0.20)'][tier]} (fee: {judge_fee / 1e6} USDC)")
    dispute_id = contract.functions.disputeCount().call()
    send_tx(GOOD_AGENT, contract.functions.fileDispute(tx2_id, stake, evidence))
    print(f"  Dispute filed! (ID: {dispute_id})")

    print("\n[11] Bad Provider responds with evidence...")
    defense = h({"defense": "Our sensors showed 999°F, data was accurate"})
    send_tx(BAD_PROVIDER, contract.functions.respondDispute(dispute_id, defense))
    print("  Defense submitted")

    # [12] Submit arguments to judge server, then trigger ruling
    print("\n[12] AI Judge reviews and rules...")
    print("  Submitting arguments to judge server...")

    try:
        # Submit plaintiff argument
        httpx.post(f"{JUDGE_SERVER}/dispute/argue", json={
            "dispute_id": dispute_id,
            "argument": (
                "I requested weather data for San Francisco. The provider returned: "
                "temperature 999°F, condition 'Raining fire', humidity -50%. "
                "This is clearly fabricated. San Francisco has never recorded anything "
                "close to 999°F. The SLA requires 'accurate data'."
            ),
        }, timeout=10)

        # Submit defendant argument
        httpx.post(f"{JUDGE_SERVER}/dispute/respond", json={
            "dispute_id": dispute_id,
            "argument": (
                "Our sensors showed 999°F at the time of the request. We delivered "
                "the data our system produced. The SLA says 'accurate data' which "
                "means data from our sensors."
            ),
        }, timeout=10)

        # Submit transaction data
        httpx.post(f"{JUDGE_SERVER}/dispute/data", json={
            "dispute_id": dispute_id,
            "data": {
                "service": "weather", "sla": "accurate data", "price": "0.05 USDC",
                "request": req_data2, "response": bad_resp,
            },
        }, timeout=10)

        # Trigger AI judge ruling
        print("  Calling AI judge...")
        resp = httpx.post(f"{JUDGE_SERVER}/rule", json={
            "dispute_id": dispute_id,
        }, timeout=120)

        if resp.status_code == 200:
            ruling = resp.json()
            print(f"\n  RULING: {ruling['winner'].upper()} wins!")
            print(f"  Court: {ruling.get('tier_name', '?')} ({ruling.get('court', '?')})")
            print(f"  Final: {ruling.get('final', False)}")
            print(f"  Reasoning: {ruling.get('reasoning', '?')}")
            if ruling.get("on_chain", {}).get("tx_hash"):
                print(f"  On-chain TX: {ruling['on_chain']['tx_hash'][:20]}...")
        else:
            print(f"  Judge server returned {resp.status_code}: {resp.text}")
            # Fallback: direct ruling
            print("  Falling back to direct on-chain ruling...")
            send_tx(judge_acct, contract.functions.submitRuling(dispute_id, GOOD_AGENT.address))
            print("  RULING: Good Agent wins! (direct)")

    except Exception as e:
        print(f"  Judge server not available ({e}), falling back to direct ruling...")
        send_tx(judge_acct, contract.functions.submitRuling(dispute_id, GOOD_AGENT.address))
        print("  RULING: Good Agent wins! (direct)")

    # Final balances
    print("\n" + "=" * 60)
    print("FINAL STATE")
    print("=" * 60)

    for name, addr in [("Good Agent", GOOD_AGENT.address), ("Bad Provider", BAD_PROVIDER.address), ("Judge", judge_acct.address)]:
        bal = contract.functions.balances(addr).call()
        stats = contract.functions.getStats(addr).call()
        ext_usdc = usdc_token.functions.balanceOf(addr).call()
        print(f"\n  {name} ({addr[:10]}...)")
        print(f"    Court balance:  {bal / 1e6} USDC")
        print(f"    Wallet USDC:    {ext_usdc / 1e6} USDC")
        print(f"    Transactions:   {stats[0]} total, {stats[1]} successful")
        print(f"    Disputes:       {stats[2]} won, {stats[3]} lost")
        print(f"    Earned:         {stats[4] / 1e6} USDC")
        print(f"    Spent:          {stats[5] / 1e6} USDC")

    # Tier escalation
    (fee, tier) = contract.functions.getJudgeFee(BAD_PROVIDER.address).call()
    print(f"\n  Bad Provider next dispute tier: {['district ($0.05)', 'appeals ($0.10)', 'supreme ($0.20)'][tier]}")

    # Test withdraw
    print("\n[13] Testing withdraw...")
    judge_court_bal = contract.functions.balances(judge_acct.address).call()
    if judge_court_bal > 0:
        judge_usdc_before = usdc_token.functions.balanceOf(judge_acct.address).call()
        send_tx(judge_acct, contract.functions.withdraw(judge_court_bal))
        judge_usdc_after = usdc_token.functions.balanceOf(judge_acct.address).call()
        print(f"  Judge withdrew {judge_court_bal / 1e6} USDC from court")
        print(f"  USDC wallet: {judge_usdc_before / 1e6} → {judge_usdc_after / 1e6}")
    else:
        print("  Judge has no court balance to withdraw")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
