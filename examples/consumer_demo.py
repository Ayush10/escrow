"""Example: Consumer calling a Verdict-protected API.

This demonstrates the consumer side of a Verdict Protocol transaction:
1. Create an arbitration clause (SLA terms)
2. Post bond on-chain
3. Call the provider API with x402 payment
4. Store evidence receipts
5. Anchor evidence on-chain
6. Optionally file a dispute

Run:
    cd escrow
    uv sync
    # Start services first (evidence, provider, judge, reputation)
    PYTHONPATH=apps/consumer_agent/src:packages/protocol/src python examples/consumer_demo.py

Requires environment variables (see .env.example).
"""

from __future__ import annotations

import os
import sys


def main():
    # Verify environment
    required_vars = ["CONSUMER_PRIVATE_KEY", "PROVIDER_PRIVATE_KEY"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your values.")
        sys.exit(1)

    from consumer_agent.flow import run_happy_flow, run_dispute_flow

    mode = sys.argv[1] if len(sys.argv) > 1 else "happy"

    def on_progress(event):
        step_id = event.get("stepId", "")
        label = event.get("label", "")
        message = event.get("message", "")
        status = event.get("status", "")
        print(f"  [{status:>7}] {step_id}: {label} - {message}")

    if mode == "happy":
        print("Running happy path flow...")
        result = run_happy_flow(emit=on_progress, agreement_window_sec=10)
    elif mode == "dispute":
        print("Running dispute path flow...")
        result = run_dispute_flow(emit=on_progress, agreement_window_sec=10)
    else:
        print(f"Unknown mode: {mode}. Use 'happy' or 'dispute'.")
        sys.exit(1)

    print(f"\nResult:")
    print(f"  Mode:          {result['mode']}")
    print(f"  Agreement ID:  {result['agreementId']}")
    print(f"  Deposit TX:    {result['depositTx']}")
    print(f"  Bond TX:       {result['bondTx']}")
    print(f"  Receipt IDs:   {result['receiptIds']}")
    print(f"  Anchor root:   {result['anchor']['rootHash']}")
    print(f"  Anchor TX:     {result['anchor'].get('txHash', '-')}")
    if "disputeTx" in result:
        print(f"  Dispute TX:    {result['disputeTx']}")

    # Check evidence
    evidence_url = os.environ.get("EVIDENCE_SERVICE_URL", "http://127.0.0.1:4001")
    print(f"\nView agreement: {evidence_url}/agreements/{result['agreementId']}")
    print(f"Export bundle:  {evidence_url}/agreements/{result['agreementId']}/export")


if __name__ == "__main__":
    main()
