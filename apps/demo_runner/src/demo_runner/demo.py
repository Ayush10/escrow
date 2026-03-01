from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass

import httpx


@dataclass(slots=True)
class ServiceProc:
    name: str
    cmd: list[str]
    health_url: str
    proc: subprocess.Popen | None = None


def _wait_for_health(url: str, timeout: float = 45.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with httpx.Client(timeout=2) as client:
                r = client.get(url)
                if r.status_code < 500:
                    return
        except Exception:
            pass
        time.sleep(1)
    raise TimeoutError(f"service did not become healthy: {url}")


def _run_json_command(cmd: list[str]) -> dict:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    stdout = result.stdout.strip()
    return json.loads(stdout)


def _explorer_link(tx_hash: str) -> str:
    base = os.environ.get("GOAT_EXPLORER_URL", "https://explorer.testnet3.goat.network")
    return f"{base}/tx/{tx_hash}"


def main() -> None:
    services = [
        ServiceProc(
            name="evidence",
            cmd=["uv", "run", "--package", "evidence-service", "evidence-service"],
            health_url="http://127.0.0.1:4001/health",
        ),
        ServiceProc(
            name="provider",
            cmd=["uv", "run", "--package", "provider-api", "provider-api"],
            health_url="http://127.0.0.1:4000/health",
        ),
        ServiceProc(
            name="judge",
            cmd=["uv", "run", "--package", "judge-service", "judge-service"],
            health_url="http://127.0.0.1:4002/health",
        ),
        ServiceProc(
            name="reputation",
            cmd=["uv", "run", "--package", "reputation-service", "reputation-service"],
            health_url="http://127.0.0.1:4003/health",
        ),
    ]

    procs: list[subprocess.Popen] = []
    try:
        for service in services:
            service.proc = subprocess.Popen(service.cmd, stdout=sys.stdout, stderr=sys.stderr)
            procs.append(service.proc)

        for service in services:
            _wait_for_health(service.health_url)

        happy = _run_json_command(["uv", "run", "--package", "consumer-agent", "consumer-happy"])
        dispute = _run_json_command(["uv", "run", "--package", "consumer-agent", "consumer-dispute"])

        with httpx.Client(timeout=10) as client:
            verdicts = client.get("http://127.0.0.1:4002/verdicts").json()
            reputations = client.get("http://127.0.0.1:4003/reputation").json()

        summary = {
            "happy": happy,
            "dispute": dispute,
            "verdicts": verdicts,
            "reputations": reputations,
            "links": {
                "happy_deposit": _explorer_link(happy["depositTx"]),
                "dispute_tx": _explorer_link(dispute["disputeTx"]),
            },
        }

        print(json.dumps(summary, indent=2))

    finally:
        for proc in procs:
            proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
