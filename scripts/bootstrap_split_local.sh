#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DATA_DIR="$ROOT/data"
FOUNDRY_DEPLOY_DIR="$ROOT/foundry/deployments"
DEPLOY_OUTPUT_REL="./deployments/split-local-deployment.json"
DEPLOY_OUTPUT_PATH="$FOUNDRY_DEPLOY_DIR/split-local-deployment.json"
ENV_OUTPUT_PATH="$ROOT/.env.split.local"
ANVIL_LOG_PATH="$DATA_DIR/anvil.log"
ANVIL_PID_PATH="$DATA_DIR/anvil.pid"

RPC_URL="${LOCAL_RPC_URL:-http://127.0.0.1:8545}"
CHAIN_ID="${LOCAL_CHAIN_ID:-31337}"
ANVIL_MNEMONIC="${ANVIL_MNEMONIC:-test test test test test test test test test test test junk}"
DEPLOYER_PRIVATE_KEY="${LOCAL_DEPLOYER_PRIVATE_KEY:-$(cast wallet private-key --mnemonic "$ANVIL_MNEMONIC" --mnemonic-index 0)}"
PROVIDER_PRIVATE_KEY="${PROVIDER_PRIVATE_KEY:-$(cast wallet private-key --mnemonic "$ANVIL_MNEMONIC" --mnemonic-index 1)}"
CONSUMER_PRIVATE_KEY="${CONSUMER_PRIVATE_KEY:-$(cast wallet private-key --mnemonic "$ANVIL_MNEMONIC" --mnemonic-index 2)}"
JUDGE_PRIVATE_KEY="${JUDGE_PRIVATE_KEY:-$(cast wallet private-key --mnemonic "$ANVIL_MNEMONIC" --mnemonic-index 3)}"
JUDGE_ENDPOINT="${JUDGE_ENDPOINT:-http://127.0.0.1:4002}"
IPFS_LOCAL_STORE_PATH="${IPFS_LOCAL_STORE_PATH:-./data/ipfs}"

mkdir -p "$DATA_DIR" "$FOUNDRY_DEPLOY_DIR"

provider_address="$(cast wallet address --private-key "$PROVIDER_PRIVATE_KEY")"
consumer_address="$(cast wallet address --private-key "$CONSUMER_PRIVATE_KEY")"
judge_address="$(cast wallet address --private-key "$JUDGE_PRIVATE_KEY")"
charity_address="$(cast wallet address --private-key "$DEPLOYER_PRIVATE_KEY")"

wait_for_rpc() {
  local waited=0
  local max_wait=20
  while [ "$waited" -lt "$max_wait" ]; do
    if cast chain-id --rpc-url "$RPC_URL" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  return 1
}

if ! cast chain-id --rpc-url "$RPC_URL" >/dev/null 2>&1; then
  echo "Starting anvil on ${RPC_URL}..."
  nohup anvil --host 127.0.0.1 --port "${RPC_URL##*:}" --mnemonic "$ANVIL_MNEMONIC" >"$ANVIL_LOG_PATH" 2>&1 &
  echo "$!" >"$ANVIL_PID_PATH"
  wait_for_rpc
else
  echo "Using existing local RPC at ${RPC_URL}."
fi

rm -f "$DEPLOY_OUTPUT_PATH"

(
  cd "$ROOT/foundry"
  PROVIDER_ADDRESS="$provider_address" \
  CONSUMER_ADDRESS="$consumer_address" \
  JUDGE_ADDRESS="$judge_address" \
  CHARITY_ADDRESS="$charity_address" \
  DEPLOY_OUTPUT_PATH="$DEPLOY_OUTPUT_REL" \
  forge script script/DeployLocal.s.sol:DeployLocal \
    --rpc-url "$RPC_URL" \
    --broadcast \
    --private-key "$DEPLOYER_PRIVATE_KEY"
)

if [ ! -f "$DEPLOY_OUTPUT_PATH" ]; then
  echo "Expected deployment output at $DEPLOY_OUTPUT_PATH" >&2
  exit 1
fi

set -- $(
  python3 - <<'PY' "$DEPLOY_OUTPUT_PATH"
import json
import sys

payload = json.load(open(sys.argv[1], "r", encoding="utf-8"))
for key in ["mockUsdc", "vault", "judgeRegistry", "court", "evidenceAnchor"]:
    print(payload[key])
PY
)

mock_usdc_address="$1"
vault_address="$2"
registry_address="$3"
court_address="$4"
evidence_anchor_address="$5"

cat >"$ENV_OUTPUT_PATH" <<EOF
GOAT_RPC_URL=$RPC_URL
GOAT_CHAIN_ID=$CHAIN_ID
GOAT_EXPLORER_URL=$RPC_URL
ESCROW_CONTRACT_MODE=split
ESCROW_CONTRACT_ADDRESS=$court_address
ESCROW_COURT_ADDRESS=$court_address
ESCROW_VAULT_ADDRESS=$vault_address
ESCROW_JUDGE_REGISTRY_ADDRESS=$registry_address
ESCROW_EVIDENCE_ANCHOR_ADDRESS=$evidence_anchor_address
USDC_ADDRESS=$mock_usdc_address
PROVIDER_PRIVATE_KEY=$PROVIDER_PRIVATE_KEY
CONSUMER_PRIVATE_KEY=$CONSUMER_PRIVATE_KEY
JUDGE_PRIVATE_KEY=$JUDGE_PRIVATE_KEY
EVIDENCE_SIGNER_PRIVATE_KEY=$DEPLOYER_PRIVATE_KEY
X402_ALLOW_MOCK=1
X402_NETWORK=eip155:$CHAIN_ID
X402_PAYMENT_ASSET=USDC
X402_SELLER_WALLET=0x0000000000000000000000000000000000000000
IPFS_MODE=local
IPFS_LOCAL_STORE_PATH=$IPFS_LOCAL_STORE_PATH
EVIDENCE_SERVICE_URL=http://127.0.0.1:4001
PROVIDER_API_URL=http://127.0.0.1:4000
JUDGE_SERVICE_URL=http://127.0.0.1:4002
REPUTATION_SERVICE_URL=http://127.0.0.1:4003
EOF

PYTHONPATH="$ROOT/packages/protocol/src${PYTHONPATH:+:$PYTHONPATH}" \
ESCROW_CONTRACT_MODE=split \
ESCROW_CONTRACT_ADDRESS="$court_address" \
ESCROW_COURT_ADDRESS="$court_address" \
ESCROW_VAULT_ADDRESS="$vault_address" \
ESCROW_JUDGE_REGISTRY_ADDRESS="$registry_address" \
ESCROW_EVIDENCE_ANCHOR_ADDRESS="$evidence_anchor_address" \
GOAT_RPC_URL="$RPC_URL" \
GOAT_CHAIN_ID="$CHAIN_ID" \
JUDGE_PRIVATE_KEY="$JUDGE_PRIVATE_KEY" \
JUDGE_ENDPOINT="$JUDGE_ENDPOINT" \
uv run python - <<'PY'
import os

from verdict_protocol import EscrowClient

client = EscrowClient(
    rpc_url=os.environ["GOAT_RPC_URL"],
    chain_id=int(os.environ["GOAT_CHAIN_ID"]),
    contract_address=os.environ["ESCROW_CONTRACT_ADDRESS"],
    private_key=os.environ["JUDGE_PRIVATE_KEY"],
    dry_run=False,
)

judge = client.account.address
judge_row = client.registry_contract.functions.judges(judge).call()
registered = bool(judge_row[5])
if not registered:
    tx = client.register_judge(
        fee=0,
        endpoint=os.environ.get("JUDGE_ENDPOINT", "http://127.0.0.1:4002"),
        max_response_time=300,
    )
    print(f"Registered judge {judge} in tx {tx.tx_hash}")
else:
    print(f"Judge {judge} already registered")
PY

echo ""
echo "Split local environment written to $ENV_OUTPUT_PATH"
echo "Court:          $court_address"
echo "Vault:          $vault_address"
echo "Judge Registry: $registry_address"
echo "EvidenceAnchor: $evidence_anchor_address"
echo "Mock USDC:      $mock_usdc_address"
echo ""
echo "Next step:"
echo "  bash ./scripts/demo.sh --split-local --dispute"
