# Operator Smoke Checklist

Verify the Verdict Protocol stack is working correctly after setup or deployment.

## Quick smoke test

```bash
./scripts/demo.sh
```

If the demo completes without errors, the stack is healthy. The script now:
- starts evidence, provider, judge, reputation, and demo-runner services
- serves the console on `http://127.0.0.1:4173`
- creates a full happy+dispute run through the runner API and waits for completion

## Manual checklist

### 1. Environment

- [ ] `.env` file exists and has all required values
- [ ] `GOAT_RPC_URL` is reachable: `curl -s https://rpc.testnet3.goat.network -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'`
- [ ] `ESCROW_CONTRACT_ADDRESS` has deployed code
- [ ] Private keys are set for judge, provider, and consumer

### 2. Services start cleanly

- [ ] Evidence service: `curl http://127.0.0.1:4001/clauses` returns `{"count": ..., "items": [...]}`
- [ ] Provider API: `curl http://127.0.0.1:4000/health` returns `{"status": "ok", ...}`
- [ ] Judge service: `curl http://127.0.0.1:4002/health` returns `{"status": "ok", ...}`
- [ ] Reputation service: `curl http://127.0.0.1:4003/health` returns `{"status": "ok", ...}`

### 3. Happy path flow

- [ ] Run: `uv run --package consumer-agent python -m consumer_agent.run_happy_path`
- [ ] Clause is stored in evidence service
- [ ] Request, response, and payment receipts are created
- [ ] Evidence is anchored (Merkle root committed)
- [ ] Dispute window elapses without error
- [ ] No errors in judge or reputation service logs

### 4. Dispute path flow

- [ ] Run: `uv run --package consumer-agent python -m consumer_agent.run_dispute_path`
- [ ] Bad response receipt and SLA-check receipt are created
- [ ] Evidence is anchored
- [ ] Dispute is filed on-chain (or mock)
- [ ] Judge service detects the dispute
- [ ] Verdict is generated with opinion
- [ ] Ruling is submitted (or flagged for manual review)
- [ ] Reputation scores are updated

### 5. Console

- [ ] Open `http://localhost:4173` — landing page loads
- [ ] Click "Launch Console" — dashboard loads
- [ ] Environment panel shows chain ID, contract address, MOCK/LIVE mode
- [ ] Service health cards show all services as "ok"
- [ ] Connect to runner succeeds
- [ ] Happy path autoplay completes
- [ ] Dispute path autoplay completes
- [ ] Verdicts table shows rulings
- [ ] Reputation leaderboard shows agent scores
- [ ] Agreement explorer loads agreement details

### 6. Evidence integrity

- [ ] `curl http://127.0.0.1:4001/agreements/<agreement-id>` returns valid chain
- [ ] `receiptChain.valid` is `true`
- [ ] `root.matched` is `true`
- [ ] Export endpoint returns complete bundle

### 7. Mock mode clarity

- [ ] When `X402_ALLOW_MOCK=1`: console shows yellow mock banner
- [ ] When `X402_ALLOW_MOCK=1`: environment panel shows `MOCK` chip
- [ ] When mock mode is off: no banner, panel shows `LIVE` chip

## Failure recovery

If any check fails:

1. Check service logs for errors
2. Verify `.env` values match expected config
3. Verify GOAT RPC endpoint is reachable
4. Verify wallet balances (gas for GOAT, USDC for payments)
5. Try restarting the failed service
6. See `docs/runbooks/operator-runbook.md` for detailed troubleshooting
