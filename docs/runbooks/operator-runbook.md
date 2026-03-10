# Operator Runbook

Operational guide for running the Verdict Protocol platform.

## Architecture

```
Evidence Service (:4001) — receipt storage + Merkle anchoring
Provider API (:4000)     — x402-protected reference endpoint
Judge Service (:4002)    — dispute watcher + LLM judge + ruling submission
Reputation Service (:4003) — event watcher + reputation scoring
Demo Runner (:4004)      — orchestration + SSE streaming
Console (:4173)          — operator dashboard
```

## Starting services

### One-command start

```bash
./scripts/demo.sh --console
```

### Individual services

```bash
pnpm dev:evidence
pnpm dev:provider
pnpm dev:judge
pnpm dev:reputation
pnpm dev:runner
```

### Health checks

```bash
curl http://127.0.0.1:4001/clauses          # Evidence: should return JSON
curl http://127.0.0.1:4000/health           # Provider: {"status": "ok"}
curl http://127.0.0.1:4002/health           # Judge: {"status": "ok"}
curl http://127.0.0.1:4003/health           # Reputation: {"status": "ok"}
```

## Common issues and fixes

### Judge service not processing disputes

```
Symptom: Disputes filed on-chain but no verdicts appearing

Checks:
1. Is the judge service running? Check /health
2. Check logs for errors (Anthropic API, RPC, signing)
3. Is JUDGE_PRIVATE_KEY set and valid?
4. Is GOAT_RPC_URL reachable?
5. Is ANTHROPIC_API_KEY valid?
6. Is the watcher polling? Check logs for "polling" messages

Fix:
- Restart the judge service
- Verify all env vars
- Check if disputes are in "manual_review" status (low confidence)
```

### Evidence anchoring failure

```
Symptom: POST /anchor returns error or tx reverts

Checks:
1. Is the RPC endpoint reachable?
2. Does the signer have sufficient gas?
3. Is ESCROW_CONTRACT_ADDRESS correct?
4. Are receipts valid? Check receipt chain integrity

Fix:
- Retry the anchor (idempotent operation)
- Top up signer wallet with GOAT testnet BTC
- Switch to backup RPC if needed
```

### Ruling submission reverts

```
Symptom: Judge generates verdict but submitRuling tx fails

Checks:
1. Is the dispute already resolved? (d.resolved == true)
2. Is the winner address valid? (must be plaintiff or defendant)
3. Is msg.sender the judge? (JUDGE_PRIVATE_KEY must match contract judge)

Fix:
- If already resolved: skip, update local state
- If wrong signer: fix JUDGE_PRIVATE_KEY to match contract's judge address
- Log incident for audit
```

### Reputation not updating

```
Symptom: Reputation scores stale after rulings

Checks:
1. Is reputation service running?
2. Is it watching for RulingSubmitted events?
3. Check logs for event processing

Fix:
- Restart reputation service
- Check watcher polling interval (REPUTATION_POLL_SEC, default 5s)
```

### Console not connecting

```
Symptom: Console shows "not connected" after clicking Connect

Checks:
1. Is the demo runner running on port 4004?
2. Is the URL correct in the runner URL input?
3. Check browser console for CORS or network errors

Fix:
- Start the demo runner: pnpm dev:runner
- Or use the static server: python3 -m http.server 4173 --directory console
- Verify CORS is enabled on all services
```

## Database management

### Location

- `data/verdict_evidence.db` — evidence service
- `data/verdict_judge.db` — judge service
- `data/verdict_reputation.db` — reputation service

### Reset (development only)

```bash
rm -f data/verdict_*.db
# Restart services — databases are recreated automatically
```

### Backup

```bash
cp data/verdict_evidence.db data/verdict_evidence.db.bak
cp data/verdict_judge.db data/verdict_judge.db.bak
cp data/verdict_reputation.db data/verdict_reputation.db.bak
```

## Environment management

### Mock mode

Set in `.env`:
```
X402_ALLOW_MOCK=1
ESCROW_DRY_RUN=1
```

Mock mode:
- x402 payment verification is bypassed
- Contract interactions use in-memory mock DB
- Evidence anchoring returns mock tx hashes
- Console shows yellow MOCK banner

### Live mode

Remove mock vars from `.env` or set to empty:
```
X402_ALLOW_MOCK=
ESCROW_DRY_RUN=
```

Requirements for live mode:
- GOAT Testnet3 wallets funded with test BTC (gas)
- Base Sepolia wallets funded with test USDC (payments)
- Contract deployed and address set in ESCROW_CONTRACT_ADDRESS
- Anthropic API key for judge service

## Monitoring

### Key things to watch

1. **Judge service logs** — errors in dispute processing
2. **Watcher lag** — how far behind the event watchers are
3. **Dispute backlog** — unprocessed disputes piling up
4. **Failed rulings** — submitRuling transactions reverting
5. **Evidence anchor failures** — Merkle root commits failing

### Log locations

All services log to stdout. Capture with:
```bash
pnpm dev:judge 2>&1 | tee logs/judge.log
```

## Escalation

If you cannot resolve an issue:

1. Check `KNOWN_ISSUES.md` for known limitations
2. Check the contract state on GOAT explorer
3. Review recent changes in `docs/changes.md`
4. File an issue with logs and reproduction steps
