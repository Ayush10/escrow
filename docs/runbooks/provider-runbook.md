# Provider Runbook

Operational guide for API providers using Verdict Protocol.

## Service overview

As a provider, you run or integrate with:
- **Your API** — your actual service endpoint, protected by x402 payment gating
- **Evidence service** (port 4001) — stores receipts and anchors evidence
- **Your wallet** — GOAT Testnet3 address for on-chain operations

The judge service, reputation service, and console are operated by the platform (or self-hosted).

## Daily operations

### Check service health

```bash
curl http://127.0.0.1:4000/health
# Expected: {"status": "ok", "x402_mode": "mock" or "live"}
```

### Check your reputation

```bash
curl http://127.0.0.1:4003/reputation/did:8004:0x<your-address>
```

### View recent transactions

Open the console at `http://localhost:4173` and navigate to the Control Panel.

## Responding to disputes

When a consumer files a dispute against your service:

1. **You are notified** via webhook (if configured) or Telegram
2. **Review the evidence**: Check the agreement in the console or via API:
   ```bash
   curl http://127.0.0.1:4001/agreements/<agreement-id>
   ```
3. **Submit counter-evidence** (optional): Call `respondDispute(disputeId, evidence)` on the contract
4. **Wait for ruling**: The judge service evaluates evidence and submits a ruling
5. **Check the verdict**:
   ```bash
   curl http://127.0.0.1:4002/verdicts/<dispute-id>
   ```

### If you win

- Your stake is returned plus the consumer's stake
- Your reputation gets a positive update (+2)
- No action needed

### If you lose

- You lose your stake and the payment for the disputed transaction
- Your reputation gets a negative update (-5)
- Your dispute tier escalates (higher fees for future disputes filed against you)
- Review the verdict opinion to understand what went wrong
- Fix the underlying service issue

## Troubleshooting

### x402 payment verification failing

```
Symptom: Consumers get 402 Payment Required errors
Check: Is X402_FACILITATOR_URL reachable?
Check: Is X402_SELLER_WALLET set correctly?
Check: Is the consumer's payment on the correct network (Base Sepolia)?
Fix: Verify env vars and facilitator connectivity
```

### Evidence hash mismatch

```
Symptom: Consumer claims X-Evidence-Hash doesn't match response
Check: Is your API returning deterministic JSON?
Check: Are you using keccak256 of the response body?
Fix: Ensure response body is serialized consistently (sort_keys=True)
```

### Service not registered on-chain

```
Symptom: Consumers cannot call requestService()
Check: Did you call register() and registerService() on the contract?
Check: Is your service status Active (not Paused/Retired)?
Fix: Register via the escrow client or contract directly
```

### Insufficient balance

```
Symptom: Cannot respond to disputes
Check: curl the contract to check your balance
Fix: Call deposit() to add more USDC to your on-chain balance
```

## Best practices

1. **Return deterministic responses** — same input should produce same output hash
2. **Always include X-Evidence-Hash** — consumers need this for receipt binding
3. **Monitor your reputation** — a declining score signals service quality issues
4. **Respond to disputes quickly** — even if you think you'll win, submit counter-evidence
5. **Keep your bond funded** — insufficient balance can block dispute responses
6. **Use SLA terms you can meet** — don't promise 100ms latency if your API takes 3 seconds
