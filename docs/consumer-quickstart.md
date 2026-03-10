# Consumer Quickstart

Call Verdict-protected APIs with automatic evidence capture and dispute capability.

## Prerequisites

- Python 3.11+
- `uv` installed
- Base Sepolia wallet with test USDC (for x402 payments)
- GOAT Testnet3 wallet with test BTC (for gas, if filing disputes)

## 1. Clone and install

```bash
git clone <repo-url>
cd escrow
uv sync
```

## 2. Set up environment

```bash
cp .env.example .env
```

Edit `.env`:

```bash
GOAT_RPC_URL=https://rpc.testnet3.goat.network
GOAT_CHAIN_ID=48816
ESCROW_CONTRACT_ADDRESS=0xFBf9b5293A1737AC53880d3160a64B49bA54801D

CONSUMER_PRIVATE_KEY=0x<your-consumer-private-key>
PROVIDER_PRIVATE_KEY=0x<provider-private-key>

X402_FACILITATOR_URL=https://www.x402.org/facilitator
X402_NETWORK=eip155:84532

EVIDENCE_SERVICE_URL=http://127.0.0.1:4001
PROVIDER_API_URL=http://127.0.0.1:4000

# For local development
X402_ALLOW_MOCK=1
ESCROW_DRY_RUN=1
```

## 3. Run the happy path

The happy path demonstrates a successful API call with evidence capture:

```bash
uv run --package consumer-agent python -m consumer_agent.run_happy_path
```

What happens:
1. Creates an arbitration clause (SLA terms)
2. Provider deposits escrow pool
3. Consumer posts bond
4. Consumer calls `/api/data` with x402 payment
5. Request, response, and payment receipts are stored
6. Evidence is anchored on-chain (Merkle root)
7. Dispute window elapses — transaction completes cleanly

## 4. Run the dispute path

The dispute path demonstrates filing a dispute when the provider returns bad data:

```bash
uv run --package consumer-agent python -m consumer_agent.run_dispute_path
```

What happens:
1. Same setup as happy path
2. Consumer calls `/api/data?bad=true` (provider returns degraded response)
3. Consumer creates an SLA-check receipt noting the violation
4. Evidence is anchored on-chain
5. Consumer files a dispute with the evidence root hash
6. Judge service detects the dispute, evaluates evidence, submits ruling

## 5. Run the full demo

Run both paths sequentially with all services:

```bash
pnpm demo
```

Or with the console UI:

```bash
pnpm demo:ui
# Open http://localhost:4173, click "Happy", "Dispute", or "Full"
```

## 6. Using the consumer flow programmatically

```python
from consumer_agent.flow import run_happy_flow, run_dispute_flow

# Happy path
result = run_happy_flow(agreement_window_sec=30)
print(f"Agreement: {result['agreementId']}")
print(f"Receipts: {result['receiptIds']}")
print(f"Anchor: {result['anchor']['rootHash']}")

# Dispute path
result = run_dispute_flow(agreement_window_sec=30)
print(f"Dispute TX: {result['disputeTx']}")
```

## 7. Check provider reputation before calling

```bash
curl http://127.0.0.1:4003/reputation
# Returns leaderboard of all agents

curl http://127.0.0.1:4003/reputation/did:8004:0xProviderAddress
# Returns specific agent's track record
```

## 8. Inspect evidence after a call

```bash
# View full agreement (clause + receipts + anchor + chain validation)
curl http://127.0.0.1:4001/agreements/<agreement-id>

# Export evidence bundle
curl http://127.0.0.1:4001/agreements/<agreement-id>/export
# Returns downloadable JSON with complete evidence package
```

## 9. View verdicts

```bash
curl http://127.0.0.1:4002/verdicts
# Lists all verdicts

curl http://127.0.0.1:4002/verdicts/0
# Returns verdict detail with full judicial opinion
```

## Evidence receipt types

| Type | Who creates | What it captures |
|------|------------|-----------------|
| `request` | Consumer | API request payload hash, timestamp |
| `response` | Consumer (captures provider output) | Response hash, `X-Evidence-Hash`, status code |
| `payment` | Consumer | x402 payment reference, network |
| `sla_check` | Consumer | SLA violation details (if any) |
| `dispute_filed` | Consumer | Dispute ID, on-chain tx hash |

## Next steps

- See `examples/consumer_demo.py` for a self-contained consumer script
- See `docs/provider-quickstart.md` for the provider side
- See the console at `http://localhost:4173` for visual exploration
