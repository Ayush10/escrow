# Verdict Protocol — Validation Results

## Environment and scope
- Date: 2026-03-01 (UTC)
- Network: GOAT Testnet3 (`goat-testnet3`), RPC `https://rpc.testnet3.goat.network`
- Agent wallet used for dashboard flow: `0x00289Dbbb86b64881CEA492D14178CF886b066Be`
- Dashboard label used: `Ayush + Karan and Verdict Protocol`
- Repository: `/Users/ayushojha/Desktop/03_Projects/escrow`

## What was executed

### Step 0 — Environment snapshot
- Command:
```bash
cd /Users/ayushojha/Desktop/03_Projects/escrow && cat artifacts/validation/logs/step0_env_summary.json
```
- Result:
  - Snapshot saved at `artifacts/validation/logs/step0_env_summary.json`
  - Includes GOAT chain id, local wallet mapping used for test harness, and selected mock flags

Screenshot:
![Step 0 env snapshot](/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots/01_env_summary.png)

### Step 1 — Unit/integration test suite
- Command:
```bash
cd /Users/ayushojha/Desktop/03_Projects/escrow && uv run pytest
```
- Result: pass
- Log: `artifacts/validation/logs/step1_tests.log`

Screenshot:
![Step 1 tests](/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots/02_tests_pass.png)

### Step 2 — Service health checks
- Command: `pnpm demo` (starts all services; runs validation probes)
- Result: evidence, provider, judge, reputation endpoints reached (`status: ok`)
- Log: `artifacts/validation/logs/step2_health.json`

Screenshot:
![Step 2 services](/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots/03_service_health.png)

### Step 3 — Happy path agent flow
- Command:
```bash
cd /Users/ayushojha/Desktop/03_Projects/escrow && uv run python -m consumer_agent.run_happy_path
```
- Output:
  - Agreement: `d8801f0b-51d3-40ca-bc90-b599b8858dec`
  - Receipt IDs: `5fdb2e14-1dbd-4394-b9c1-0c8b24bf9da1`, `9b7bad6a-1494-48e9-b35e-ea424cad1601`, `47f682d2-9562-4e58-aac4-8c763db30d7d`
  - Merkle root: `0x18da45be0bcd5f9b26db0a597b6ccae6a1bf25314f032ad0228647ec11ba180f`
  - x402 payment reference: `fallback-b65b755316911ebb9d00b86d5bd8cde2ab0bebb39f24bcd3631538a4fb4ccba8`
- Log: `artifacts/validation/logs/step3_happy_path.json`

Screenshot:
![Step 3 happy path](/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots/04_happy_path.png)

### Step 4 — Dispute path flow
- Command:
```bash
cd /Users/ayushojha/Desktop/03_Projects/escrow && uv run python -m consumer_agent.run_dispute_path
```
- Output:
  - Agreement: `73e3f161-f603-42e3-8dbd-b6f817be20a0`
  - Receipt IDs: `5cd20100-87b3-4eb0-8fd0-8e763c1303e9`, `039fcd2a-6667-4047-880e-1610939a4795`, `7f803faf-ac71-430f-9bbc-22d0f15dc058`
  - Merkle root: `0xe40e521736adf1672269e2ad395137d75858535d784cd81f285421fd52bfe17a`
  - x402 payment reference: `fallback-3153835d58b366988981c1fdae0260441c0a0f5e7b7382e24ad5e1346add192c`
- Log: `artifacts/validation/logs/step4_dispute_path.json`

Screenshot:
![Step 4 dispute path](/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots/05_dispute_path.png)

### Step 5 — Service state and judge pipeline integration check
- Commands:
```bash
cat /Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/logs/step5_service_state.json
uv run pytest apps/judge_service/tests/test_judge_pipeline.py -q
```
- Result:
  - State artifact exists and contains dispute/receipts/verdict artifacts
  - Judge pipeline test logs stored at `artifacts/validation/logs/step6_judge_pipeline_test.log`

Screenshot:
![Step 5 judge pipeline](/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots/06_service_state.png)

### Step 6 — GOAT address funding/status check
- Command:
```bash
cd /Users/ayushojha/Desktop/03_Projects/escrow && uv run --package demo-runner python - <<'PY'
from web3 import Web3
import requests, json
rpc='https://rpc.testnet3.goat.network'
w3=Web3(Web3.HTTPProvider(rpc))
addr='0x00289Dbbb86b64881CEA492D14178CF886b066Be'
usdc='0x29d1ee93e9ecf6e50f309f498e40a6b42d352fa1'
abi=[{"constant":True,"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]
bal=int(w3.eth.get_balance(addr))
usdc_contract=w3.eth.contract(address=Web3.to_checksum_address(usdc),abi=abi)
usdc_bal=int(usdc_contract.functions.balanceOf(Web3.to_checksum_address(addr)).call())
print(json.dumps({
 'native_btc_wei':str(bal),
 'native_btc':str(bal/1e18),
 'usdc_base_units':str(usdc_bal),
},indent=2))
PY
```
(Equivalent check was also logged as a JSON artifact.)
- Latest balance snapshot taken during validation:
  - native BTC: `5.784e-06 BTC` at one point in earlier scan, then `0.000718828597474621 BTC` in a later on-demand check
  - USDC base units: `997000`
  - ERC-8004 registration: initially `false`, later recognized via agent mapping in dashboard flow
  - explorer tx sample includes both native and token activity
- Log: `artifacts/validation/logs/step8_goat_address_check.json`

Screenshot:
![Step 6 wallet status](/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots/test.png)

### Step 7 — Dashboard payment push (wallet + header)
- Command executed with the exact provided sender key and dashboard header:
```bash
cd /Users/ayushojha/Desktop/03_Projects/escrow && \
DASHBOARD_PAYMENT_DRY_RUN=0 \
DASHBOARD_PAYMENT_PRIVATE_KEY=0x135133a09ae6dc4a9cc467d65ccf985812eea146e88e9372f4ebd8b560783a70 \
DASHBOARD_PAYMENT_TOKEN=USDC \
DASHBOARD_PAYMENT_AMOUNT=0.0005 \
DASHBOARD_AGENT_RECIPIENT=0x9D6Cc5556aB60779193517da30E1Bb18aeEd3f80 \
DASHBOARD_AGENT_NAME='Ayush + Karan and Verdict Protocol' \
PYTHONPATH=apps/demo_runner/src uv run python -m demo_runner.push_dashboard_payment
```
- Live output (`artifacts/validation/logs/step9_dashboard_payment_live.json`):
```json
{
  "mode": "live",
  "headerLabel": "Ayush + Karan and Verdict Protocol",
  "sender": "0x00289Dbbb86b64881CEA492D14178CF886b066Be",
  "recipient": "0x9D6Cc5556aB60779193517da30E1Bb18aeEd3f80",
  "token": "USDC",
  "amount": "0.0005",
  "senderIsAgent": true,
  "recipientIsAgent": true,
  "dashboardEligible": true,
  "txHash": "a3c52bb6c4700eadc058704c500b07326486dad5e4a68f15c07fd01cf5dc3c97",
  "txExplorerUrl": "https://explorer.testnet3.goat.network/tx/a3c52bb6c4700eadc058704c500b07326486dad5e4a68f15c07fd01cf5dc3c97"
}
```
- Registration tx used for metadata/header visibility in one run:
  - `1bae5cfc7ab4ab4b9cd419195929dbd4c00a7a64ccdf8c345e1f56b7661c1e48`
- Additional successful transfer observed:
  - `9f94884d01172475d70f5064e1446a737070c94d8be6e30890bb44eb666cfc12`

Screenshot captures:
- ![registration tx](/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots/dashboard/tx_registration_1bae5cfc.png)
- ![payment tx](/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots/dashboard/tx_payment_9f94884.png)
- ![wallet explorer](/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots/dashboard/address_wallet.png)

### Step 8 — On-chain proof of transfer
- RPC proof (receipt status = 1, method selector `a9059cbb` transfer):
  - `a3c52bb6...c97`
  - `9f94884d...fc12`
  - `c42365f4...ce2`
- Each transfer targets USDC contract `0x29D1Ee93e9ecf6E50F309f498e40a6b42D352Fa1` and is a successful ERC-20 transfer
- Screenshot:
![Step 8 on-chain proof](/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots/dashboard/tx_payment_9f94884.png)

## Onboarding example payload
For GOAT dashboard/agent registration, the onboarding style object is:

- Project name: `RoastBattle`
- Wallet: `0xB127Ee92182C073828407F89581338dF741f5903`
- Description: two AI agents roast profiles and judge winner via Verdict Protocol evidence/judging pipeline

For this project implementation, the live dashboard-facing project identity used is:
- Project name: `Ayush + Karan and Verdict Protocol`
- Wallet: `0x00289Dbbb86b64881CEA492D14178CF886b066Be`
- Header/signature field used in registration metadata: `Ayush + Karan and Verdict Protocol`

## Notes / interpretation
- `visibleInDashboardFeed` in script output may return `false` if the dashboard indexing path is delayed; however, transactions are confirmed on-chain and can be viewed directly via GOAT explorer links above.
- To ensure immediate visibility in Agent ↔ Agent list, keep sender and recipient registered with ERC-8004 and submit non-`dry-run` payments from a funded wallet.

## Artifacts directory summary
- Logs: `/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/logs`
- Screenshots: `/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots`
- Dashboard-specific screenshots: `/Users/ayushojha/Desktop/03_Projects/escrow/artifacts/validation/screenshots/dashboard`
