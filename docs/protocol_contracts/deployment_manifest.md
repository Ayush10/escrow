# Deployment Manifest

Canonical deployment metadata lives in:
- `contracts/deployments/goat-testnet3.json`

## V1 environments

### Local dry-run

Use for repeatable development and CI:
- `ESCROW_DRY_RUN=1`
- `X402_ALLOW_MOCK=1`
- deterministic provider/consumer/judge keys
- SQLite databases under local repo paths

Expected behavior:
- no real payment settlement
- mock event emission through the escrow client
- judge and evidence logic still execute

### GOAT Testnet3

Use for shared integration and pilot rehearsal:
- `GOAT_RPC_URL=https://rpc.testnet3.goat.network`
- `GOAT_CHAIN_ID=48816`
- `ESCROW_CONTRACT_ADDRESS` from `contracts/deployments/goat-testnet3.json`
- funded provider, consumer, and judge wallets

## Canonical env set

Minimum backend env:
- `GOAT_RPC_URL`
- `GOAT_CHAIN_ID`
- `ESCROW_CONTRACT_ADDRESS`
- `PROVIDER_PRIVATE_KEY`
- `CONSUMER_PRIVATE_KEY`
- `JUDGE_PRIVATE_KEY`
- `EVIDENCE_SERVICE_URL`
- `X402_FACILITATOR_URL`
- `X402_NETWORK`
- `X402_SELLER_WALLET`

## Verification checklist

After any deploy or env change:
1. `GET /health` for provider, evidence, judge, and reputation services
2. `GET /config` for demo runner if used
3. run the dry-run end-to-end command from CI
4. if testnet, confirm contract code exists at the configured address

## Update rule

If the contract address, ABI path, or payment token changes:
- update `contracts/deployments/goat-testnet3.json`
- update README and this manifest in the same commit
