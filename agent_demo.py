"""Verdict Protocol agent demo runner (safe wrapper).

This script integrates the remote `agent_demo.py` intent without embedding private keys.
It drives the existing demo-runner API and prints a concise run summary.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

import httpx


def _runner_url() -> str:
    return os.environ.get("DEMO_RUNNER_URL", "http://127.0.0.1:4004").rstrip("/")


def _mode() -> str:
    mode = os.environ.get("DEMO_MODE", "full").strip().lower()
    if mode not in {"happy", "dispute", "full"}:
        raise ValueError("DEMO_MODE must be happy, dispute, or full")
    return mode


def _window_sec() -> int:
    return int(os.environ.get("DEMO_WINDOW_SEC", "30"))


def _create_run(client: httpx.Client, base_url: str, mode: str, window_sec: int) -> str:
    payload = {
        "mode": mode,
        "startServices": True,
        "keepServices": False,
        "autoRun": True,
        "agreementWindowSec": window_sec,
    }
    response = client.post(f"{base_url}/runs", json=payload)
    response.raise_for_status()
    data = response.json()
    return data["runId"]


def _read_run(client: httpx.Client, base_url: str, run_id: str) -> dict[str, Any]:
    response = client.get(f"{base_url}/runs/{run_id}")
    response.raise_for_status()
    return response.json()


def _print_step_update(steps: list[dict[str, Any]], seen: set[str]) -> None:
    for step in steps:
        key = f"{step.get('stepId')}::{step.get('status')}::{step.get('message')}"
        if key in seen:
            continue
        seen.add(key)
        print(
            f"[step] {step.get('stepId', '-'):<24} "
            f"{step.get('status', '-'):<10} "
            f"{step.get('message', '-')}"
        )


def main() -> None:
    base_url = _runner_url()
    mode = _mode()
    window_sec = _window_sec()
    poll_sec = float(os.environ.get("DEMO_POLL_SEC", "2"))
    timeout_sec = float(os.environ.get("DEMO_TIMEOUT_SEC", "600"))

    print("=" * 68)
    print("VERDICT PROTOCOL AGENT DEMO")
    print(f"runner: {base_url}")
    print(f"mode: {mode}")
    print(f"window: {window_sec}s")
    print("=" * 68)

    started = time.time()
    seen_steps: set[str] = set()

    with httpx.Client(timeout=30) as client:
        health = client.get(f"{base_url}/health")
        health.raise_for_status()
        health_data = health.json()
        print(
            f"[health] chainId={health_data.get('chainId')} "
            f"contract={health_data.get('contractAddress')}"
        )

        run_id = _create_run(client, base_url, mode, window_sec)
        print(f"[run] created: {run_id}")

        while True:
            run = _read_run(client, base_url, run_id)
            _print_step_update(run.get("steps", []), seen_steps)

            status = run.get("status")
            if status in {"complete", "error", "cancelled"}:
                print("-" * 68)
                print(f"[run] final status: {status}")
                if run.get("errors"):
                    print(f"[run] errors: {run['errors']}")
                summary = run.get("artifacts", {}).get("summary", {})
                print(f"[run] agreements: {summary.get('agreementIds', run.get('agreementIds', []))}")
                print(f"[run] disputes: {summary.get('disputeIds', run.get('disputeIds', []))}")
                print("-" * 68)
                if status != "complete":
                    sys.exit(1)
                return

            if time.time() - started > timeout_sec:
                print(f"[run] timeout after {timeout_sec}s")
                sys.exit(2)

            time.sleep(poll_sec)


if __name__ == "__main__":
    main()
