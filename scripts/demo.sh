#!/usr/bin/env bash
# Verdict Protocol — one-command demo bootstrap.
#
# Starts the local services, demo runner, and console. In default mode it also
# creates a full happy+dispute run through the runner API and waits for it to
# finish.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHONPATH_ENTRIES=(
  "$ROOT/packages/protocol/src"
  "$ROOT/apps/evidence_service/src"
  "$ROOT/apps/judge_service/src"
  "$ROOT/apps/reputation_service/src"
  "$ROOT/apps/provider_api/src"
  "$ROOT/apps/consumer_agent/src"
  "$ROOT/apps/demo_runner/src"
)
export PYTHONPATH="$(IFS=:; echo "${PYTHONPATH_ENTRIES[*]}")${PYTHONPATH:+:$PYTHONPATH}"

EVIDENCE_PORT=4001
PROVIDER_PORT=4000
JUDGE_PORT=4002
REPUTATION_PORT=4003
RUNNER_PORT=4004
CONSOLE_PORT=4173
RUN_MODE="full"
LIVE_MODE=false
CONSOLE_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --live) LIVE_MODE=true ;;
    --console) CONSOLE_ONLY=true ;;
    --happy) RUN_MODE="happy" ;;
    --dispute) RUN_MODE="dispute" ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Usage: ./scripts/demo.sh [--live] [--console] [--happy|--dispute]" >&2
      exit 1
      ;;
  esac
done

load_env_file() {
  local file="$1"
  if [ ! -f "$file" ]; then
    return 0
  fi

  set -a
  source <(grep -E '^(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=.*$' "$file")
  set +a
}

load_env_file .env
load_env_file .env.local

: "${PROVIDER_PRIVATE_KEY:=0x1111111111111111111111111111111111111111111111111111111111111111}"
: "${CONSUMER_PRIVATE_KEY:=0x2222222222222222222222222222222222222222222222222222222222222222}"
: "${JUDGE_PRIVATE_KEY:=0x3333333333333333333333333333333333333333333333333333333333333333}"
: "${GOAT_CHAIN_ID:=48816}"
: "${GOAT_RPC_URL:=https://rpc.testnet3.goat.network}"
: "${GOAT_EXPLORER_URL:=https://explorer.testnet3.goat.network}"
: "${ESCROW_CONTRACT_ADDRESS:=0xFBf9b5293A1737AC53880d3160a64B49bA54801D}"
: "${X402_NETWORK:=eip155:84532}"
: "${X402_SELLER_WALLET:=0x0000000000000000000000000000000000000000}"

export PROVIDER_PRIVATE_KEY
export CONSUMER_PRIVATE_KEY
export JUDGE_PRIVATE_KEY
export GOAT_CHAIN_ID
export GOAT_RPC_URL
export GOAT_EXPLORER_URL
export ESCROW_CONTRACT_ADDRESS
export X402_NETWORK
export X402_SELLER_WALLET

if [ "$LIVE_MODE" = false ]; then
  export X402_ALLOW_MOCK=1
  export ESCROW_DRY_RUN=1
  echo "[MOCK MODE] Payments and contract interactions are simulated."
  if [ "${DEMO_RESET_STATE:-1}" != "0" ]; then
    rm -f \
      "$ROOT/data/verdict.db" \
      "$ROOT/data/verdict.db-shm" \
      "$ROOT/data/verdict.db-wal" \
      "$ROOT/data/escrow_mock.db" \
      "$ROOT/data/escrow_mock.db-shm" \
      "$ROOT/data/escrow_mock.db-wal"
    echo "[MOCK MODE] Reset local demo state."
  fi
else
  unset X402_ALLOW_MOCK || true
  unset ESCROW_DRY_RUN || true
  echo "[LIVE MODE] Using real chain interactions."
fi

PIDS=()
cleanup() {
  echo ""
  echo "Shutting down services..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  echo "All services stopped."
}
trap cleanup EXIT

wait_for_service() {
  local name="$1"
  local url="$2"
  local max_wait=45
  local waited=0

  while [ "$waited" -lt "$max_wait" ]; do
    if curl -fsS --max-time 2 "$url/health" >/dev/null 2>&1; then
      echo "  $name: ready"
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done

  echo "  $name: TIMEOUT (waited ${max_wait}s)" >&2
  return 1
}

json_get() {
  local key="$1"
  python3 -c '
import json
import sys

key = sys.argv[1]
payload = json.load(sys.stdin)
value = payload.get(key, "")
if isinstance(value, (dict, list)):
    print(json.dumps(value))
elif value is None:
    print("")
else:
    print(value)
' "$key"
}

pretty_print_json() {
  python3 -c '
import json
import sys

payload = json.load(sys.stdin)
json.dump(payload, sys.stdout, indent=2)
print()
'
}

echo "Starting services..."

uv run python -m evidence_service.server &
PIDS+=("$!")
echo "  Evidence service starting on :${EVIDENCE_PORT}"

uv run python -m provider_api.server &
PIDS+=("$!")
echo "  Provider API starting on :${PROVIDER_PORT}"

uv run python -m judge_service.server &
PIDS+=("$!")
echo "  Judge service starting on :${JUDGE_PORT}"

uv run python -m reputation_service.api &
PIDS+=("$!")
echo "  Reputation service starting on :${REPUTATION_PORT}"

uv run python -m demo_runner.server &
PIDS+=("$!")
echo "  Demo runner starting on :${RUNNER_PORT}"

echo ""
echo "Waiting for services to be ready..."
wait_for_service "Evidence" "http://127.0.0.1:${EVIDENCE_PORT}"
wait_for_service "Provider" "http://127.0.0.1:${PROVIDER_PORT}"
wait_for_service "Judge" "http://127.0.0.1:${JUDGE_PORT}"
wait_for_service "Reputation" "http://127.0.0.1:${REPUTATION_PORT}"
wait_for_service "Runner" "http://127.0.0.1:${RUNNER_PORT}"

echo ""
echo "All services ready."

echo "Starting console on :${CONSOLE_PORT}..."
python3 -m http.server "$CONSOLE_PORT" --directory console >/dev/null 2>&1 &
PIDS+=("$!")

echo ""
echo "Console: http://127.0.0.1:${CONSOLE_PORT}"
echo "Runner:  http://127.0.0.1:${RUNNER_PORT}"
echo ""

if [ "$CONSOLE_ONLY" = true ]; then
  echo "Console-only mode. Services are running. Press Ctrl+C to stop."
  wait
fi

payload=$(printf '{"mode":"%s","startServices":false,"keepServices":true,"autoRun":true,"agreementWindowSec":30}' "$RUN_MODE")
create_response=$(curl -fsS "http://127.0.0.1:${RUNNER_PORT}/runs" \
  -H "content-type: application/json" \
  -d "$payload")
run_id=$(printf '%s' "$create_response" | json_get runId)

if [ -z "$run_id" ]; then
  echo "Failed to create demo run." >&2
  exit 1
fi

echo "Created demo run: ${run_id} (${RUN_MODE})"

max_wait=180
waited=0
last_status=""

while [ "$waited" -lt "$max_wait" ]; do
  run_json=$(curl -fsS "http://127.0.0.1:${RUNNER_PORT}/runs/${run_id}")
  status=$(printf '%s' "$run_json" | json_get status)
  current_step=$(printf '%s' "$run_json" | json_get currentStep)

  if [ "$status" != "$last_status" ]; then
    echo "  run status: ${status:-unknown} ${current_step:+(step: ${current_step})}"
    last_status="$status"
  fi

  case "$status" in
    complete)
      echo ""
      echo "Demo completed successfully."
      printf '%s\n' "$run_json" | pretty_print_json
      echo ""
      echo "Console is still running at http://127.0.0.1:${CONSOLE_PORT}"
      echo "Press Ctrl+C to stop all services."
      wait
      ;;
    error|cancelled)
      echo ""
      echo "Demo failed with status: ${status}" >&2
      printf '%s\n' "$run_json" | pretty_print_json >&2
      exit 1
      ;;
  esac

  sleep 1
  waited=$((waited + 1))
done

echo "Demo timed out after ${max_wait}s." >&2
exit 1
