#!/usr/bin/env python3
"""Test AI judge — full 3-tier escalation with fresh arguments at each level."""
import asyncio
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

os.environ["ANTHROPIC_API_KEY"] = open(os.path.expanduser("~/.fix/api_key")).read().strip()

from judge import Evidence, AIJudge, COURT_TIERS

# Base transaction data (same across all tiers)
TX_DATA = {
    "service": "weather",
    "sla": "accurate data",
    "price": "0.005 USDC",
    "request": {"city": "sf", "timestamp": 1709150000},
    "response": {"city": "San Francisco", "temp_f": 999, "condition": "Raining fire", "humidity": -50},
}

# Each tier gets fresh arguments from both sides
TIER_ARGUMENTS = [
    {  # District Court — initial filing
        "plaintiff": (
            "I requested weather data for San Francisco. The provider returned: "
            "temperature 999°F, condition 'Raining fire', humidity -50%. "
            "This is clearly fabricated data. San Francisco has never recorded "
            "anything close to 999°F. The provider violated the SLA which requires "
            "'accurate data'. I am requesting a full refund of my payment."
        ),
        "defendant": (
            "Our sensors showed 999°F at the time of the request. We delivered "
            "the data our system produced. The SLA says 'accurate data' which "
            "means data from our sensors, not data the consumer agrees with. "
            "We fulfilled our obligation by returning sensor readings."
        ),
    },
    {  # Appeals Court — defendant lost, escalates with new argument
        "plaintiff": (
            "The district court correctly found that 999°F is physically impossible. "
            "The defendant has offered no explanation for how their sensors could "
            "produce readings that violate the laws of thermodynamics. Negative humidity "
            "is mathematically impossible. 'Raining fire' is not a meteorological term. "
            "The defendant's 'sensor defense' is a post-hoc rationalization for delivering "
            "garbage data. I urge this court to affirm the lower ruling."
        ),
        "defendant": (
            "The district court applied an unreasonably strict interpretation of 'accurate.' "
            "The SLA does not define accuracy against physical constants — it simply requires "
            "that we return the data our system produces. Our API had a temporary calibration "
            "error. The SLA contains no warranty of physical plausibility, only that data is "
            "'accurate' to what our instruments report. The consumer could have validated the "
            "data before relying on it. We request the appeals court overturn and find for defendant."
        ),
    },
    {  # Supreme Court — defendant lost twice, final appeal
        "plaintiff": (
            "Two courts have now ruled against the defendant. The district court found the data "
            "physically impossible. The appeals court rejected the 'calibration error' defense. "
            "The defendant has never produced logs, maintenance records, or any evidence of a "
            "sensor malfunction. They simply assert it happened. An SLA for 'accurate data' "
            "cannot be satisfied by data that is objectively, provably false. This is the "
            "defendant's third attempt to avoid accountability. I ask the Supreme Court to "
            "issue a final, unappealable ruling in my favor."
        ),
        "defendant": (
            "With respect to this honorable court, both lower rulings have been based on a "
            "fundamental misreading of the SLA. 'Accurate data' in the context of automated "
            "API services means the API returned a well-formed response in the correct schema. "
            "The response WAS well-formed JSON with the correct fields. The consumer's contract "
            "was for API access, not for a guarantee about the physical world. If the consumer "
            "wanted validated, physically plausible data, they should have contracted for a "
            "premium tier with data validation. We delivered exactly what was contracted: "
            "a functioning API endpoint that returns weather data. The SLA was met."
        ),
    },
]


async def main():
    judge = AIJudge()
    prior_rulings = []

    for i, tier in enumerate(COURT_TIERS):
        args = TIER_ARGUMENTS[i]

        evidence = Evidence(
            dispute_id=0,
            plaintiff="0xC633f39CbE3E8bdF549789325a98004d86536472",
            defendant="0x9D6Cc5556aB60779193517da30E1Bb18aeEd3f80",
            plaintiff_stake=5000,   # 0.005 USDC (6 decimals)
            defendant_stake=5000,
            plaintiff_evidence="0xabc123...committed_hash",
            defendant_evidence="0xdef456...committed_hash",
            plaintiff_argument=args["plaintiff"],
            defendant_argument=args["defendant"],
            transaction_data=TX_DATA,
            hash_match=True,
        )

        print("=" * 80)
        print(f"  {tier['name'].upper()} COURT  —  {tier['model']}  —  Fee: ${tier['fee_usd']}")
        print("=" * 80)

        ruling = await judge.rule(
            evidence,
            level=i,
            prior_rulings=prior_rulings if prior_rulings else None,
        )

        # Print the full judicial opinion
        if ruling.full_opinion:
            print()
            print(ruling.full_opinion)
        else:
            print(f"\nWinner: {ruling.winner}")
            print(f"\nReasoning:\n{ruling.reasoning}")

        print()
        print(f"  VERDICT: {ruling.winner.upper()} wins  |  Court: {ruling.court}  |  Final: {ruling.final}")
        print()

        prior_rulings.append(ruling.to_dict())


asyncio.run(main())
