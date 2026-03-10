# Provider Quickstart

Protect any API endpoint with Verdict Protocol in under one hour.

## Prerequisites

- Python 3.11+
- `uv` installed
- GOAT Testnet3 wallet with test BTC (for gas)
- Base Sepolia wallet with test USDC (for x402 payments)
- Anthropic API key (optional, for judge service)

## 1. Clone and install

```bash
git clone <repo-url>
cd escrow
uv sync
cp examples/provider.env.example .env
```

## 2. Set up environment

Edit `.env` with your values:

```bash
# Required
GOAT_RPC_URL=https://rpc.testnet3.goat.network
GOAT_CHAIN_ID=48816
ESCROW_CONTRACT_ADDRESS=0xFBf9b5293A1737AC53880d3160a64B49bA54801D

# Your provider wallet
PROVIDER_PRIVATE_KEY=0x<your-provider-private-key>

# x402 payment config (Base Sepolia)
X402_FACILITATOR_URL=https://www.x402.org/facilitator
X402_NETWORK=eip155:84532
X402_SELLER_WALLET=<your-provider-wallet-address>

# For local development without real payments
X402_ALLOW_MOCK=1
ESCROW_DRY_RUN=1
```

## 3. Start the evidence service

The evidence service stores receipts and anchors evidence on-chain:

```bash
pnpm dev:evidence
# Runs on http://127.0.0.1:4001
```

## 4. Create your protected API

Here is a minimal FastAPI app protected by x402:

```python
# my_api.py
from fastapi import FastAPI
from verdict_protocol.hashing import keccak_hex
import json, time

app = FastAPI()

@app.get("/api/data")
def data():
    """Your actual API logic."""
    data = {
        "result": "some_data",
        "timestamp": int(time.time() * 1000),
    }
    return data

@app.get("/health")
def health():
    return {"status": "ok"}
```

To add Verdict Protocol protection, install the same x402 middleware used by the
reference provider service.

See:
- `apps/provider_api/src/provider_api/x402_integration.py` for the middleware installer
- `examples/fastapi_provider.py` for a complete working example with `/api/data`
- `examples/provider.env.example` for a sample config

## 5. Register on-chain

Before consumers can call your service, register as an agent and register your service:

```python
from verdict_protocol.escrow_client import EscrowClient
import os

client = EscrowClient(
    rpc_url=os.environ["GOAT_RPC_URL"],
    chain_id=int(os.environ["GOAT_CHAIN_ID"]),
    contract_address=os.environ["ESCROW_CONTRACT_ADDRESS"],
    private_key=os.environ["PROVIDER_PRIVATE_KEY"],
)

# Register as agent (deposit bond)
client.deposit_pool(10**15)  # 0.001 USDC

# Register your service
# termsHash = hash of your SLA terms
# price = price per call in token units
# bondRequired = minimum consumer bond
```

## 6. Run the full stack locally

In separate terminals:

```bash
# Terminal 1: Evidence service
pnpm dev:evidence

# Terminal 2: Your provider API
pnpm dev:provider

# Terminal 3: Judge service (handles disputes)
pnpm dev:judge

# Terminal 4: Reputation service
pnpm dev:reputation

# Terminal 5: Demo runner
pnpm dev:runner
```

Or use the demo script to start everything:

```bash
./scripts/demo.sh --console
```

## 7. Verify with the console

```bash
pnpm demo:ui
# Open http://localhost:4173
```

The console shows:
- Service health status
- Transaction history
- Evidence anchoring status
- Dispute rulings (if any)
- Reputation scores

## 8. Move to live payments

When ready for real x402 payments:

1. Remove `X402_ALLOW_MOCK=1` from `.env`
2. Remove `ESCROW_DRY_RUN=1` from `.env`
3. Fund your provider wallet with GOAT testnet BTC (gas)
4. Fund your consumer wallet with Base Sepolia USDC
5. Restart services

The console will show `LIVE` instead of `MOCK` in the environment panel.

## What happens during a call

```
Consumer                    Your API                   Evidence Service
   |                          |                              |
   |-- x402 payment + GET --> |                              |
   |                          |-- process request -->        |
   |                          |<-- response -------          |
   |<-- response + hash ---   |                              |
   |-- store receipt -------->|                              |
   |-- anchor evidence ------>|------> commit on-chain       |
```

Every call produces:
1. A request receipt (signed by consumer)
2. A response receipt (with `X-Evidence-Hash` header from your API)
3. A payment receipt (x402 reference)
4. A Merkle root anchored on GOAT (tamper-evident)

If a consumer disputes, the judge service automatically:
1. Fetches the evidence bundle
2. Verifies receipt chain integrity
3. Checks SLA rules deterministically
4. Generates a judicial opinion via LLM
5. Submits the ruling on-chain

## Next steps

- See `examples/fastapi_provider.py` for a complete working provider
- See `docs/consumer-quickstart.md` for the consumer side
- See `docs/runbooks/provider-runbook.md` for operational guidance
