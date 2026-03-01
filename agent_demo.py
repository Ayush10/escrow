"""Agent Court — End-to-End Live Agent Demo.

This script acts as two real agents on GOAT Testnet3:
1. Provider registers a service, fulfills a transaction (badly)
2. Consumer requests the service, gets bad data, files a real dispute
3. Both submit arguments to the court API
4. Court API triggers AI judge → ruling submitted on-chain

Everything is real. Real USDC. Real contract. Real AI judge. Real on-chain ruling.
"""
import json
import os
import sys
import time
import hashlib

import httpx
from web3 import Web3

# ── Config ────────────────────────────────────────────────────────────────────

RPC = "https://rpc.testnet3.goat.network"
CHAIN_ID = 48816
CONTRACT = "0xFBf9b5293A1737AC53880d3160a64B49bA54801D"
USDC = Web3.to_checksum_address("0x29d1ee93e9ecf6e50f309f498e40a6b42d352fa1")
COURT_API = os.environ.get("COURT_API", "https://court.notruefireman.org/api")

# Wallets
CONSUMER_KEY = "0f88ebc84fad53e61ce75dffb9f48b8f9df91814bdd5ee8832b9cfdfeceff395"
PROVIDER_KEY = "a5ad76e96ca9e89071ddc58da34286236182924a9a7bfa3e088027efda296d70"

ABI = json.load(open(os.path.join(os.path.dirname(__file__), "contracts/abi/AgentCourt.json")))

USDC_ABI = [
    {"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
]

# ── Helpers ────────────────────────────────────────────────────────────────────

w3 = Web3(Web3.HTTPProvider(RPC))
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT), abi=ABI)
usdc = w3.eth.contract(address=USDC, abi=USDC_ABI)

consumer = w3.eth.account.from_key(CONSUMER_KEY)
provider = w3.eth.account.from_key(PROVIDER_KEY)


def send_tx(account, fn, gas=500000):
    """Build, sign, send a transaction."""
    tx = fn.build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "chainId": CHAIN_ID,
        "gas": gas,
        "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    return receipt


def sha256_hash(data: dict) -> bytes:
    return bytes.fromhex(hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest())


def api(method, path, data=None):
    url = f"{COURT_API}{path}"
    if method == "GET":
        r = httpx.get(url, timeout=120)
    else:
        r = httpx.post(url, json=data, timeout=120)
    r.raise_for_status()
    return r.json()


# ── Main Flow ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("AGENT COURT — LIVE END-TO-END TEST")
    print(f"Contract: {CONTRACT}")
    print(f"Court API: {COURT_API}")
    print(f"Consumer: {consumer.address}")
    print(f"Provider: {provider.address}")
    print("=" * 60)

    # Check balances
    c_bal = contract.functions.balances(consumer.address).call()
    p_bal = contract.functions.balances(provider.address).call()
    print(f"\nConsumer court balance: {c_bal} ({c_bal/1e6:.6f} USDC)")
    print(f"Provider court balance: {p_bal} ({p_bal/1e6:.6f} USDC)")

    c_usdc = usdc.functions.balanceOf(consumer.address).call()
    p_usdc = usdc.functions.balanceOf(provider.address).call()
    print(f"Consumer wallet USDC:  {c_usdc/1e6:.6f}")
    print(f"Provider wallet USDC:  {p_usdc/1e6:.6f}")

    # ── Step 1: Ensure deposits ──────────────────────────────────────────────
    min_deposit = contract.functions.minDeposit().call()
    print(f"\nMin deposit: {min_deposit} ({min_deposit/1e6:.6f} USDC)")

    for name, account, bal in [("Consumer", consumer, c_bal), ("Provider", provider, p_bal)]:
        if bal < min_deposit:
            deposit_amount = min_deposit * 2
            print(f"\n[*] {name} needs deposit. Approving {deposit_amount} USDC...")
            # Approve
            allowance = usdc.functions.allowance(account.address, Web3.to_checksum_address(CONTRACT)).call()
            if allowance < deposit_amount:
                r = send_tx(account, usdc.functions.approve(Web3.to_checksum_address(CONTRACT), deposit_amount * 10))
                print(f"  Approved: tx {r.transactionHash.hex()}")
            # Deposit
            r = send_tx(account, contract.functions.deposit(deposit_amount))
            print(f"  Deposited: tx {r.transactionHash.hex()}")
        else:
            print(f"[+] {name} has sufficient balance: {bal}")

    # ── Step 2: Register service ─────────────────────────────────────────────
    sla_terms = {"service": "weather_data", "location": "sf", "requirement": "accurate data", "price": "0.005 USDC"}
    terms_hash = sha256_hash(sla_terms)
    price = 5000  # 0.005 USDC
    bond = 1000   # 0.001 USDC

    print(f"\n[*] Provider registering service...")
    print(f"  SLA: {json.dumps(sla_terms)}")
    print(f"  Terms hash: 0x{terms_hash.hex()}")
    try:
        r = send_tx(provider, contract.functions.registerService(terms_hash, price, bond))
        print(f"  Registered: tx {r.transactionHash.hex()}")
    except Exception as e:
        if "already registered" in str(e).lower() or "revert" in str(e).lower():
            print(f"  (Service may already exist, continuing)")
        else:
            raise

    service_count = contract.functions.serviceCount().call()
    service_id = service_count - 1
    print(f"  Service ID: {service_id}")

    # ── Step 3: Consumer requests service ────────────────────────────────────
    request_data = {"location": "sf", "type": "current_weather", "timestamp": int(time.time())}
    request_hash = sha256_hash(request_data)

    print(f"\n[*] Consumer requesting service #{service_id}...")
    r = send_tx(consumer, contract.functions.requestService(service_id, request_hash))
    print(f"  Requested: tx {r.transactionHash.hex()}")

    tx_count = contract.functions.transactionCount().call()
    tx_id = tx_count - 1
    print(f"  Transaction ID: {tx_id}")

    # ── Step 4: Provider fulfills with BAD data ──────────────────────────────
    bad_response = {"temperature": 999, "unit": "F", "condition": "Raining fire", "humidity": -50}
    response_hash = sha256_hash(bad_response)

    print(f"\n[*] Provider fulfilling with bad data...")
    print(f"  Response: {json.dumps(bad_response)}")
    r = send_tx(provider, contract.functions.fulfillTransaction(tx_id, response_hash))
    print(f"  Fulfilled: tx {r.transactionHash.hex()}")

    # ── Step 5: Consumer files dispute ───────────────────────────────────────
    stake = bond  # match the bond
    evidence_data = {"claim": "data is physically impossible", "sla_breach": True, "response": bad_response}
    evidence_hash = sha256_hash(evidence_data)

    print(f"\n[*] Consumer filing dispute...")
    print(f"  Stake: {stake}")
    print(f"  Evidence hash: 0x{evidence_hash.hex()}")
    r = send_tx(consumer, contract.functions.fileDispute(tx_id, stake, evidence_hash))
    print(f"  Filed: tx {r.transactionHash.hex()}")

    dispute_count = contract.functions.disputeCount().call()
    dispute_id = dispute_count - 1
    print(f"  Dispute ID: {dispute_id}")

    # Read dispute from chain
    d = contract.functions.getDispute(dispute_id).call()
    print(f"  Plaintiff: {d[1]}")
    print(f"  Defendant: {d[2]}")
    print(f"  Tier: {d[5]} ({'district' if d[5]==0 else 'appeals' if d[5]==1 else 'supreme'})")
    print(f"  Judge fee: {d[4]}")

    # ── Step 6: Submit arguments to Court API ────────────────────────────────
    print(f"\n[*] Submitting arguments to court API...")

    # Plaintiff argues
    plaintiff_arg = (
        f"I contracted for accurate weather data for San Francisco under SLA terms requiring 'accurate data'. "
        f"The provider returned: temperature={bad_response['temperature']}°F, "
        f"humidity={bad_response['humidity']}%, condition='{bad_response['condition']}'. "
        f"These values are physically impossible. 999°F exceeds the melting point of aluminum. "
        f"Humidity cannot be negative. 'Raining fire' is not a weather condition. "
        f"This is a clear, material breach of the SLA. I paid {price/1e6:.4f} USDC for garbage data."
    )
    result = api("POST", f"/disputes/{dispute_id}/argue", {"dispute_id": dispute_id, "argument": plaintiff_arg})
    print(f"  Plaintiff argument submitted: {result}")

    # Defendant responds
    defendant_arg = (
        f"Our weather sensor array returned these readings at the time of the request. "
        f"The SLA says 'accurate data' — we delivered data accurately from our sensors. "
        f"We are not responsible for sensor calibration issues. "
        f"The contract was to deliver data, which we did. The plaintiff is conflating "
        f"'data accuracy' with 'data correctness.' We fulfilled our delivery obligation."
    )
    result = api("POST", f"/disputes/{dispute_id}/respond", {"dispute_id": dispute_id, "argument": defendant_arg})
    print(f"  Defendant argument submitted: {result}")

    # Submit transaction context
    tx_context = {
        "sla_terms": sla_terms,
        "request": request_data,
        "response": bad_response,
        "price_usdc": price / 1e6,
    }
    result = api("POST", f"/disputes/{dispute_id}/data", {"dispute_id": dispute_id, "data": tx_context})
    print(f"  Transaction data submitted: {result}")

    # ── Step 7: Trigger the AI Judge ─────────────────────────────────────────
    print(f"\n[*] Triggering AI judge for dispute #{dispute_id}...")
    print(f"  (This calls the Anthropic API and submits ruling on-chain)")

    ruling = api("POST", f"/disputes/{dispute_id}/rule")
    print(f"\n{'=' * 60}")
    print(f"RULING: {ruling.get('winner', '?').upper()} WINS")
    print(f"Court: {ruling.get('court', '?')}")
    print(f"On-chain TX: {ruling.get('tx_hash', 'N/A')}")
    print(f"Opinion: {ruling.get('opinion_length', '?')} chars")
    print(f"{'=' * 60}")

    # ── Step 8: Verify on-chain ──────────────────────────────────────────────
    print(f"\n[*] Verifying on-chain state...")
    d = contract.functions.getDispute(dispute_id).call()
    print(f"  Resolved: {d[8]}")
    print(f"  Winner: {d[9]}")

    # ── Step 9: Read the full opinion from the API ───────────────────────────
    print(f"\n[*] Fetching judicial opinion from API...")
    verdict = api("GET", f"/verdicts/{dispute_id}")
    print(f"\n{'─' * 60}")
    print(verdict.get("opinion", "No opinion available"))
    print(f"{'─' * 60}")

    # Final balances
    print(f"\nFinal balances:")
    print(f"  Consumer: {contract.functions.balances(consumer.address).call()}")
    print(f"  Provider: {contract.functions.balances(provider.address).call()}")

    print(f"\nFrontend: https://court.notruefireman.org")
    print(f"Dispute: https://court.notruefireman.org (click Disputes tab, #{dispute_id})")


if __name__ == "__main__":
    main()
