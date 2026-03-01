#!/usr/bin/env python3
"""Agent Court — Hackathon Presentation Deck"""

import sys
sys.path.insert(0, "/mnt/shared")
from pres_template import Pres, BLUE, GREEN, ORANGE, PURPLE, RED, GRAY, WHITE

p = Pres("Agent Court")

# --- SLIDE 1: Title ---
p.title_slide(
    "Agent Court",
    "On-Chain Dispute Resolution for AI Agents",
    "Karan Sharma & Ayush Agarwal  |  Vibe Code Hackathon  |  GOAT Network"
)

# --- SLIDE 2: The Problem ---
p.content_slide(
    "The Problem",
    [
        "AI agents are starting to transact autonomously — calling APIs, paying for services",
        "What happens when an agent pays for data and gets garbage back?",
        "No recourse. No reputation. No accountability.",
        "Agents can't sue each other. But smart contracts can enforce rulings.",
    ],
    subtitle="The agentic economy has no justice system",
    highlight_indices={3},
    highlight_color=GREEN,
)

# --- SLIDE 3: The Solution ---
p.content_slide(
    "Agent Court: The Solution",
    [
        "A Solidity smart contract that acts as escrow + courthouse",
        "AI judges (Haiku/Sonnet/Opus) review evidence and issue real rulings",
        "Loser pays. Winner gets compensated. Judge earns a fee.",
        "All payments in USDC — visible on the GOAT dashboard",
        "ERC-8004 identity required — every agent has on-chain reputation",
    ],
    subtitle="Smart contract has the money. AI judge has the opinions. They never mix.",
    highlight_indices={2},
    highlight_color=GREEN,
)

# --- SLIDE 4: Architecture Pipeline ---
p.pipeline_slide(
    "How It Works",
    [
        ("Register", "ERC-8004 ID", BLUE),
        ("Deposit", "USDC Bond", GREEN),
        ("Transact", "Service Call", PURPLE),
        ("Dispute?", "File Claim", ORANGE),
        ("AI Judge", "Ruling", RED),
    ],
    subtitle="End-to-end on GOAT Testnet3 (Bitcoin L2, EVM-compatible)",
)

# --- SLIDE 5: Tiered Court System ---
p.two_col_slide(
    "Tiered Court System",
    [
        "District Court — Claude Haiku ($0.05)",
        "Appeals Court — Claude Sonnet ($0.10)",
        "Supreme Court — Claude Opus ($0.20)",
        "",
        "Escalation is automatic: lose a dispute,",
        "your next one goes to a higher court.",
    ],
    [
        "Judge reads both sides' evidence",
        "Evaluates against the service SLA",
        "Issues a written ruling with reasoning",
        "Smart contract enforces the verdict",
        "Loser's stake transferred to winner",
        "Judge fee paid from dispute stake",
    ],
    "Escalating Stakes", "Ruling Process",
)

# --- SLIDE 6: Tech Stack ---
p.two_col_slide(
    "Tech Stack",
    [
        "Solidity — AgentCourt.sol (escrow + disputes)",
        "GOAT Testnet3 — Bitcoin L2, EVM, Chain 48816",
        "USDC — ERC-20 token payments",
        "ERC-8004 — On-chain agent identity + reputation",
    ],
    [
        "Python — Judge server + Guardian proxy",
        "Anthropic API — Haiku / Sonnet / Opus",
        "x402 — HTTP 402 payment-required headers",
        "giveFeedback() — ERC-8004 reputation updates",
    ],
    "On-Chain", "Off-Chain",
)

# --- SLIDE 7: Live Demo Results ---
p.content_slide(
    "Live Demo Results",
    [
        "Happy path: Agent requests weather → provider delivers → payment released",
        "Dispute path: Provider returns 999°F, -50% humidity, 'raining fire'",
        "AI judge rules: 'physically impossible values violate the SLA'",
        "Plaintiff awarded stake. Provider escalated to appeals court.",
        "Judge withdrew earned fees as real USDC from the contract.",
    ],
    subtitle="Full end-to-end on GOAT Testnet3 with real USDC transfers",
    highlight_indices={2},
    highlight_color=GREEN,
)

# --- SLIDE 8: Code Example ---
p.code_slide(
    "AI Judge Ruling (District Court)",
    'The provider\'s response contains physically\n'
    'impossible values that violate the SLA\n'
    'requirement for "accurate data".\n'
    '\n'
    'Temperature of 999°F exceeds the highest\n'
    'ever recorded on Earth (134°F).\n'
    'Humidity of -50% is impossible.\n'
    '"Raining fire" is not meteorological.\n'
    '\n'
    'The consumer paid for accurate weather\n'
    'information and received fabricated,\n'
    'nonsensical values.\n'
    '\n'
    'RULING: PLAINTIFF WINS',
    'Contract: 0xFBf9b529...\n'
    'USDC:     0x29d1ee93...\n'
    'Chain:    GOAT Testnet3 (48816)\n'
    '\n'
    'Dispute ID:  0\n'
    'Tier:        District (Haiku)\n'
    'Stake:       0.001 USDC\n'
    'Judge Fee:   0.005 USDC\n'
    '\n'
    'Plaintiff:   0xC633f39C...\n'
    'Defendant:   0x9D6Cc555...\n'
    'Winner:      Plaintiff\n'
    '\n'
    'TX: 473b088e835b5fde...',
    "Judge's Written Opinion", "On-Chain Record",
    subtitle="Real ruling from Claude Haiku — submitted on-chain via submitRuling()",
)

# --- SLIDE 9: What Makes This Different ---
p.callout_slide(
    "What Makes This Different",
    [
        ("Bond-as-reputation: your deposited USDC IS your skin in the game", GREEN),
        ("ERC-8004 enforced: no anonymous agents — identity is required on-chain", BLUE),
        ("Escalating courts: bad actors face increasingly expensive judges", ORANGE),
        ("Real money moves: USDC transfers visible on GOAT dashboard", PURPLE),
    ],
    subtitle="Not a demo. Not a mock. Everything runs on-chain with real tokens.",
)

# --- SLIDE 10: Outro ---
p.outro_slide(
    "Agent Court",
    [
        ("On-Chain", GREEN, [
            "USDC escrow payments",
            "ERC-8004 identity enforced",
            "Reputation via giveFeedback()",
            "Bond-as-reputation model",
        ]),
        ("AI Justice", BLUE, [
            "3-tier court system",
            "Written judicial opinions",
            "Automatic escalation",
            "Evidence-based rulings",
        ]),
        ("Standards", ORANGE, [
            "x402 payment protocol",
            "ERC-8004 (identity + rep)",
            "GOAT Network (BTC L2)",
            "Open source (GitHub)",
        ]),
    ],
    tagline="The agentic economy needs a justice system. We built it.",
    contact="github.com/Ayush10/escrow  |  GOAT Testnet3  |  Chain 48816",
)

out = sys.argv[1] if len(sys.argv) > 1 else "/mnt/shared/agent-court-presentation.pptx"
p.save(out)
