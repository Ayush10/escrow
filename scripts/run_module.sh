#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ "$#" -lt 1 ]; then
  echo "Usage: ./scripts/run_module.sh <python.module> [args...]" >&2
  exit 1
fi

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

module="$1"
shift

uv run python -m "$module" "$@"
