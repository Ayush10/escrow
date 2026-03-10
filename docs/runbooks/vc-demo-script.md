# VC Demo Script

## Goal

Show that Verdict Protocol is the trust layer for paid AI services:
- payment-gated access
- verifiable execution evidence
- anchored audit trail
- machine-resolvable disputes
- reputation that compounds after rulings

## Setup

Start from the demo branch:

```bash
git switch codex/demo-ready
pnpm demo:console
```

Open:

- `http://127.0.0.1:4173`

## 3-minute version

### Opening

Say:

> Every paid AI interaction has the same problem: if an agent pays another agent or API and something goes wrong, there is no native trust layer. Verdict Protocol adds payment enforcement, evidence, arbitration, and reputation to that transaction.

### Screen 1: Control Panel

Show:

- the console landing state
- service health
- environment panel
- `MOCK` banner

Say:

> This is our operator console. For demo reliability, we are in mock mode, which means payment and escrow writes are simulated, but the protocol flow is the same: the request is paid, evidence is recorded, a dispute can be filed, a verdict is generated, and reputation updates.

### Screen 2: Happy path

Action:

- run `happy`

While it runs, say:

> First I’ll show the normal case. A consumer agent buys a provider response. We generate the agreement, record the request and response receipts, record payment, and anchor the evidence root so the interaction is auditable later.

When complete, show:

- agreement ID
- request / response / payment receipts
- anchor root
- tx links

Say:

> The important part is that this is not just logging. The transaction leaves behind a structured receipt chain and an anchored evidence root. If the service worked, the relationship completes normally and the system has a tamper-evident record of what happened.

### Screen 3: Dispute path

Action:

- run `dispute`

While it runs, say:

> Now I’ll show the failure case, because that is where the product matters. Here the provider returns a bad result, the system captures that failure in the receipt chain, packages the evidence, and opens a dispute.

When complete, show:

- dispute artifact
- verdict package
- winner / loser
- verdict hash
- judge signature
- submit tx hash

Say:

> This is the core product. We take a paid AI interaction, turn it into verifiable evidence, and produce a signed machine-readable ruling. So instead of support tickets and screenshots, you get a deterministic dispute package with an auditable outcome.

### Screen 4: Reputation

Show:

- reputation leaderboard
- score delta for winner / loser

Say:

> The ruling does not disappear after one transaction. It feeds reputation. Over time, this becomes a trust graph for providers, agents, and judges, which is what lets marketplaces and agent networks route work toward reliable counterparties.

### Close

Say:

> The wedge is paid APIs and agent-to-agent commerce. The bigger platform is a trust layer that sits underneath any autonomous transaction where payment, evidence, and dispute resolution need to exist together.

## 90-second version

Say:

> Verdict Protocol is the trust layer for paid AI services. We sit between a paying agent and a provider. On the happy path, we enforce payment and record a tamper-evident evidence chain. On the failure path, we package that evidence, resolve the dispute, and write the outcome back into reputation. So the product is not just escrow, and not just arbitration. It is a full transaction trust stack for autonomous commerce.

Demo sequence:

1. Point to the `MOCK` banner and explain it is for demo safety.
2. Run `happy` and show receipts plus anchored evidence.
3. Run `dispute` and show the signed verdict plus tx hash.
4. End on the reputation panel.

## If they ask "why now?"

Say:

> AI agents can already call APIs and move money, but trust infrastructure has not caught up. Humans have Stripe, chargebacks, contracts, and dispute systems. Agents do not. We are building that missing trust layer.

## If they ask "what is the moat?"

Say:

> The moat is not one model or one escrow contract. It is the combined protocol surface: payment hooks, structured evidence, dispute packaging, arbitration policy, and reputation data compounding across transactions.

## If the UI is slow

Trigger directly:

```bash
curl -X POST http://127.0.0.1:4004/runs \
  -H 'content-type: application/json' \
  -d '{"mode":"happy","startServices":false,"keepServices":true,"autoRun":true,"agreementWindowSec":10}'

curl -X POST http://127.0.0.1:4004/runs \
  -H 'content-type: application/json' \
  -d '{"mode":"dispute","startServices":false,"keepServices":true,"autoRun":true,"agreementWindowSec":10}'
```

Then refresh the console and narrate the artifacts.

## Things not to say

- Do not claim the current demo is fully decentralized end to end.
- Do not claim the mock flow is live settlement.
- Do not lead with blockchain. Lead with trust for paid AI transactions.
- Do not spend time on internal architecture unless asked.

## Best one-line closer

> Stripe made online payments programmable; Verdict makes AI service trust programmable.
