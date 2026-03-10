"""Legacy compatibility watcher.

Remote branch shipped a standalone watcher script in `judge-frontend/`.
This replacement keeps the entrypoint but delegates to the canonical judge
service API, so the existing architecture remains the source of truth.
"""
from __future__ import annotations

import os
import time

import httpx

JUDGE_URL = os.environ.get("JUDGE_SERVICE_URL", "http://127.0.0.1:4002").rstrip("/")
POLL_SEC = float(os.environ.get("COURT_WATCHER_POLL_SEC", "10"))


def main() -> None:
    print("=" * 60)
    print("COURT WATCHER (compat mode)")
    print(f"judge service: {JUDGE_URL}")
    print(f"poll sec: {POLL_SEC}")
    print("=" * 60)

    while True:
        try:
            with httpx.Client(timeout=10) as client:
                health = client.get(f"{JUDGE_URL}/health")
                verdicts = client.get(f"{JUDGE_URL}/verdicts")
            if health.status_code >= 400 or verdicts.status_code >= 400:
                print(f"[warn] health={health.status_code} verdicts={verdicts.status_code}")
            else:
                payload = verdicts.json()
                print(f"[ok] verdict_count={payload.get('count', 0)}")
        except Exception as exc:
            print(f"[error] {exc}")

        time.sleep(POLL_SEC)


if __name__ == "__main__":
    main()
