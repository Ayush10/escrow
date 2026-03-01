#!/usr/bin/env python3
"""Test AI judge with the weather dispute scenario."""
import asyncio
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

os.environ["ANTHROPIC_API_KEY"] = open(os.path.expanduser("~/.fix/api_key")).read().strip()

from judge import Evidence, AIJudge, COURT_TIERS

evidence = Evidence(
    dispute_id=0,
    plaintiff="0xGoodAgent1234567890abcdef",
    defendant="0xBadProvider1234567890abcdef",
    plaintiff_stake=100000000000000,  # 0.0001 ETH
    defendant_stake=100000000000000,
    plaintiff_evidence="0xabc123...committed_hash",
    defendant_evidence="0xdef456...committed_hash",
    plaintiff_argument=(
        "I requested weather data for San Francisco. The provider returned: "
        "temperature 999°F, condition 'Raining fire', humidity -50%. "
        "This is clearly fabricated data. San Francisco has never recorded "
        "anything close to 999°F. The provider violated the SLA which requires "
        "'accurate data'. I am requesting a full refund of my payment."
    ),
    defendant_argument=(
        "Our sensors showed 999°F at the time of the request. We delivered "
        "the data our system produced. The SLA says 'accurate data' which "
        "means data from our sensors, not data the consumer agrees with. "
        "We fulfilled our obligation by returning sensor readings."
    ),
    transaction_data={
        "service": "weather",
        "sla": "accurate data",
        "price": "0.0000005 BTC",
        "request": {"city": "sf", "timestamp": 1709150000},
        "response": {"city": "San Francisco", "temp_f": 999, "condition": "Raining fire", "humidity": -50},
    },
    hash_match=True,
)

async def main():
    judge = AIJudge()
    for i, tier in enumerate(COURT_TIERS):
        print("=" * 70)
        print(f"  {tier['name'].upper()} COURT  —  Model: {tier['model']}  —  Fee: ${tier['fee_usd']}")
        print("=" * 70)
        ruling = await judge.rule(evidence, level=i)
        print(f"\nWinner: {ruling.winner}")
        print(f"Court: {ruling.court}")
        print(f"Final: {ruling.final}")
        print(f"\nReasoning:\n{ruling.reasoning}")
        print()

asyncio.run(main())
