from __future__ import annotations

import asyncio
import contextlib
import importlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _ensure_pythonpath() -> None:
    root = Path(__file__).resolve().parents[4]
    for rel in [
        "apps/consumer_agent/src",
        "apps/evidence_service/src",
        "apps/provider_api/src",
        "apps/judge_service/src",
        "apps/reputation_service/src",
        "apps/demo_runner/src",
        "packages/protocol/src",
    ]:
        candidate = root / rel
        if str(candidate) not in sys.path and candidate.exists():
            sys.path.append(str(candidate))


_ensure_pythonpath()

_RUNNER_PORT = int(os.environ.get("DEMO_RUNNER_PORT", "4004"))


def _apply_runtime_defaults() -> None:
    # Keep local demo runnable with zero setup; real env vars always override these defaults.
    if os.environ.get("DEMO_RUNTIME_DEFAULTS", "1") not in {"1", "true", "yes", "on"}:
        return

    provider_pk = "0x" + ("1" * 64)
    consumer_pk = "0x" + ("2" * 64)
    judge_pk = "0x" + ("3" * 64)
    defaults = {
        "ESCROW_DRY_RUN": "1",
        "X402_ALLOW_MOCK": "1",
        "GOAT_CHAIN_ID": "48816",
        "GOAT_RPC_URL": "https://rpc.testnet3.goat.network",
        "GOAT_EXPLORER_URL": "https://explorer.testnet3.goat.network",
        "ESCROW_CONTRACT_ADDRESS": "0xFBf9b5293A1737AC53880d3160a64B49bA54801D",
        "PROVIDER_PRIVATE_KEY": provider_pk,
        "CONSUMER_PRIVATE_KEY": consumer_pk,
        "JUDGE_PRIVATE_KEY": judge_pk,
        "X402_SELLER_WALLET": "0x0000000000000000000000000000000000000000",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


_apply_runtime_defaults()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _module_pythonpath() -> str:
    root = _repo_root()
    return os.pathsep.join(
        [
            str(root / "packages" / "protocol" / "src"),
            str(root / "apps" / "evidence_service" / "src"),
            str(root / "apps" / "provider_api" / "src"),
            str(root / "apps" / "judge_service" / "src"),
            str(root / "apps" / "reputation_service" / "src"),
            str(root / "apps" / "consumer_agent" / "src"),
            str(root / "apps" / "demo_runner" / "src"),
        ]
    )


def _base_env() -> dict[str, str]:
    env = os.environ.copy()
    if env.get("PYTHONPATH"):
        env["PYTHONPATH"] = os.pathsep.join([_module_pythonpath(), env["PYTHONPATH"]])
    else:
        env["PYTHONPATH"] = _module_pythonpath()
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _sqlite_path_for_service(env: dict[str, str], service_name: str) -> str | None:
    explicit_key = f"{service_name.upper()}_SQLITE_PATH"
    if env.get(explicit_key):
        return env[explicit_key]

    base = env.get("SQLITE_PATH", "./data/verdict.db")

    base_path = Path(base)
    if base_path.suffix:
        return str(base_path.with_name(f"{base_path.stem}_{service_name}{base_path.suffix}"))
    return str(base_path.with_name(f"{base_path.name}_{service_name}.db"))


def _explorer_link(tx_hash: str) -> str:
    explorer = os.environ.get("GOAT_EXPLORER_URL", "https://explorer.testnet3.goat.network")
    return f"{explorer}/tx/{tx_hash}"


@dataclass(slots=True)
class DemoRun:
    run_id: str
    mode: str
    status: str = "pending"
    start_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    update_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    current_step: str | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    agreement_ids: list[str] = field(default_factory=list)
    dispute_ids: list[str] = field(default_factory=list)
    start_services: bool = True
    keep_services: bool = False
    cancel_requested: bool = False
    error: str | None = None

    def emit(self, event: dict[str, Any]) -> None:
        if "runId" not in event:
            event["runId"] = self.run_id
        event.setdefault("atMs", int(time.time() * 1000))

        self.events.append(event)
        self.update_ms = int(time.time() * 1000)

        step_id = event.get("stepId")
        if not step_id:
            return
        run_events = {
            "step.started",
            "step.updated",
            "run.started",
            "run.info",
            "run.complete",
            "run.error",
        }
        if event.get("type") in run_events:
            if event.get("type") in {"step.started", "step.updated"}:
                self.current_step = step_id

            for idx, existing in enumerate(self.steps):
                if existing.get("stepId") == step_id:
                    self.steps[idx] = {**existing, **event}
                    break
            else:
                self.steps.append(event)


@dataclass(slots=True)
class _ServiceProcess:
    name: str
    cmd: list[str]
    health_url: str
    env: dict[str, str]
    proc: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            return
        self.proc = subprocess.Popen(
            self.cmd,
            stdout=sys.stdout,
            stderr=sys.stderr,
            env=self.env,
        )

    def stop(self) -> None:
        if not self.proc or self.proc.poll() is not None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=3)


class DemoRunManager:
    def __init__(self) -> None:
        self._runs: dict[str, DemoRun] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._watchers: dict[str, list[asyncio.Queue[str]]] = {}
        self._services: list[_ServiceProcess] = []
        self.env = _base_env()
        self._service_defs = [
            ("evidence", [sys.executable, "-m", "evidence_service.server"], "http://127.0.0.1:4001/health"),
            ("provider", [sys.executable, "-m", "provider_api.server"], "http://127.0.0.1:4000/health"),
            ("judge", [sys.executable, "-m", "judge_service.server"], "http://127.0.0.1:4002/health"),
            ("reputation", [sys.executable, "-m", "reputation_service.api"], "http://127.0.0.1:4003/health"),
        ]
        self._flow_module = None

    def create_run(
        self,
        mode: str,
        *,
        start_services: bool = True,
        keep_services: bool = False,
        agreement_window_sec: int = 30,
        auto_run: bool = True,
    ) -> DemoRun:
        if mode not in {"happy", "dispute", "full"}:
            raise ValueError("mode must be happy, dispute, or full")

        run_id = f"run-{int(time.time() * 1000)}-{os.urandom(4).hex()}"
        run = DemoRun(
            run_id=run_id,
            mode=mode,
            start_services=start_services,
            keep_services=keep_services,
        )
        run.artifacts["agreementWindowSec"] = agreement_window_sec
        self._runs[run_id] = run
        self._watchers[run_id] = []

        if auto_run:
            run.status = "queued"
            run.start_services = start_services
            run.keep_services = keep_services
            self._tasks[run_id] = asyncio.create_task(
                self._execute(run_id, agreement_window_sec=agreement_window_sec),
                name=f"demo-run-{run_id}",
            )

        return run

    def _get_flow_functions(
        self,
    ) -> tuple[
        Callable[..., dict[str, Any]],
        Callable[..., dict[str, Any]],
    ]:
        if self._flow_module is None:
            _ensure_pythonpath()
            self._flow_module = importlib.import_module("consumer_agent.flow")
        return (
            self._flow_module.run_happy_flow,
            self._flow_module.run_dispute_flow,
        )

    def get(self, run_id: str) -> DemoRun | None:
        return self._runs.get(run_id)

    def list_runs(self, limit: int = 20) -> list[DemoRun]:
        return sorted(self._runs.values(), key=lambda run: run.start_ms, reverse=True)[:limit]

    async def start(self, run_id: str, agreement_window_sec: int = 30) -> None:
        if run_id in self._tasks:
            return
        if run_id not in self._runs:
            raise ValueError("run not found")

        run = self._runs[run_id]
        if run.status in {"running", "complete", "error", "cancelled"}:
            return
        run.status = "queued"
        self._tasks[run_id] = asyncio.create_task(
            self._execute(run_id, agreement_window_sec=agreement_window_sec),
            name=f"demo-run-{run_id}",
        )

    async def wait(self, run_id: str) -> DemoRun | None:
        task = self._tasks.get(run_id)
        if not task:
            return self._runs.get(run_id)
        with contextlib.suppress(asyncio.CancelledError):
            await task
        return self._runs.get(run_id)

    async def cancel(self, run_id: str) -> bool:
        task = self._tasks.get(run_id)
        run = self._runs.get(run_id)
        if not task or not run:
            return False
        if run.status in {"complete", "error", "cancelled"}:
            return False

        run.cancel_requested = True
        run.status = "cancelled"
        run.error = "Cancelled by user"
        await self._publish(
            run,
            {
                "type": "run.error",
                "stepId": "run",
                "label": "Run cancelled",
                "status": "error",
                "message": "Cancelled by user",
            },
        )
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        return True

    def subscribe(self, run_id: str) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._watchers.setdefault(run_id, []).append(queue)
        run = self._runs.get(run_id)
        if not run:
            queue.put_nowait(
                json.dumps(
                    {"type": "run.unknown", "message": "Run not found"},
                    separators=(",", ":"),
                )
            )
            queue.put_nowait("")
            return queue
        for event in run.events:
            queue.put_nowait(json.dumps(event, separators=(",", ":")))
        return queue

    async def _broadcast(self, run_id: str, event: dict[str, Any]) -> None:
        for queue in list(self._watchers.get(run_id, [])):
            try:
                queue.put_nowait(json.dumps(event, separators=(",", ":")))
            except Exception:
                pass

    async def _publish(self, run: DemoRun, event: dict[str, Any]) -> None:
        run.emit(event)
        await self._broadcast(run.run_id, run.events[-1])

    async def _service_health_wait(self, url: str, timeout: float = 45.0) -> None:
        import httpx

        start = time.time()
        while time.time() - start < timeout:
            try:
                async with httpx.AsyncClient(timeout=2) as client:
                    response = await client.get(url)
                if response.status_code < 500:
                    return
            except Exception:
                pass
            await asyncio.sleep(1)
        raise TimeoutError(f"service did not become healthy: {url}")

    async def _start_services(self, run: DemoRun) -> None:
        if not run.start_services:
            for name, _, health_url in self._service_defs:
                await self._service_health_wait(health_url, timeout=5.0)
                await self._publish(
                    run,
                    {
                        "type": "run.info",
                        "stepId": f"service:{name}",
                        "label": f"{name} (existing)",
                        "status": "done",
                        "message": "Using existing service",
                    },
                )
            return

        self._services = [
            _ServiceProcess(
                name,
                cmd,
                url,
                {
                    **self.env,
                    **(
                        {"SQLITE_PATH": sqlite_path}
                        if (sqlite_path := _sqlite_path_for_service(self.env, name))
                        else {}
                    ),
                },
            )
            for name, cmd, url in self._service_defs
        ]

        for service in self._services:
            await self._publish(
                run,
                {
                    "type": "run.info",
                    "stepId": f"service:{service.name}",
                    "label": f"Starting {service.name}",
                    "status": "running",
                    "message": "Booting",
                },
            )
            service.start()

        for service in self._services:
            await self._service_health_wait(service.health_url)
            await self._publish(
                run,
                {
                    "type": "run.info",
                    "stepId": f"service:{service.name}",
                    "label": f"{service.name}",
                    "status": "done",
                    "message": "Ready",
                },
            )

    async def _stop_services(self, run: DemoRun) -> None:
        if not run.start_services or run.keep_services:
            return
        for service in self._services:
            service.stop()
        self._services = []

    async def _run_agent_flow(
        self,
        run: DemoRun,
        flow_fn: Callable[[Any], Any],
        flow_name: str,
        agreement_window_sec: int,
    ) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        if run.cancel_requested:
            raise RuntimeError("run cancelled")

        step_id = f"run:{flow_name}"
        await self._publish(
            run,
            {
                "type": "step.started",
                "stepId": step_id,
                "label": f"{flow_name.capitalize()} flow",
                "status": "running",
                "message": f"Starting {flow_name} flow",
            },
        )

        def emit(event: dict[str, Any]) -> None:
            if run.cancel_requested:
                return
            event["runId"] = run.run_id
            run.emit(event)
            loop.call_soon_threadsafe(
                asyncio.create_task,
                self._broadcast(run.run_id, event),
            )

        result = await asyncio.to_thread(
            flow_fn,
            emit=emit,
            agreement_window_sec=agreement_window_sec,
        )

        await self._publish(
            run,
            {
                "type": "step.updated",
                "stepId": step_id,
                "label": f"{flow_name.capitalize()} flow",
                "status": "done",
                "message": "Done",
                "artifacts": result,
            },
        )
        return result

    async def _execute(self, run_id: str, agreement_window_sec: int = 30) -> None:
        run = self._runs[run_id]
        happy_flow, dispute_flow = self._get_flow_functions()
        try:
            run.status = "running"
            await self._publish(
                run,
                {
                    "type": "run.started",
                    "stepId": "run",
                    "label": "Demo run started",
                    "status": "running",
                    "message": f"Mode={run.mode}",
                },
            )

            await self._start_services(run)

            if run.mode in {"happy", "full"}:
                result = await self._run_agent_flow(
                    run,
                    happy_flow,
                    "happy",
                    agreement_window_sec=agreement_window_sec,
                )
                run.artifacts["happy"] = result
                agreement_id = result.get("agreementId")
                if agreement_id:
                    run.agreement_ids.append(agreement_id)

            if run.mode in {"dispute", "full"}:
                result = await self._run_agent_flow(
                    run,
                    dispute_flow,
                    "dispute",
                    agreement_window_sec=agreement_window_sec,
                )
                run.artifacts["dispute"] = result
                agreement_id = result.get("agreementId")
                if agreement_id:
                    run.agreement_ids.append(agreement_id)
                dispute_tx = result.get("disputeTx") or result.get("txHash")
                if dispute_tx:
                    run.dispute_ids.append(str(dispute_tx))

            run.status = "complete"
            run.artifacts["summary"] = {
                "agreementIds": run.agreement_ids,
                "disputeIds": run.dispute_ids,
            }

            # Iterate over a snapshot because we append derived keys back into run.artifacts.
            for prefix, result in list(run.artifacts.items()):
                if not isinstance(result, dict):
                    continue
                for tx_key in ("depositTx", "bondTx", "disputeTx", "txHash"):
                    tx_value = result.get(tx_key)
                    if not tx_value:
                        continue
                    run.artifacts[f"{prefix}:{tx_key}"] = tx_value
                    if str(tx_value).startswith("0x"):
                        run.artifacts[f"{prefix}:{tx_key}:explorer"] = _explorer_link(
                            tx_value
                        )

            await self._publish(
                run,
                {
                    "type": "run.complete",
                    "stepId": "run",
                    "label": "Demo run complete",
                    "status": "done",
                    "message": "All flows complete",
                    "artifacts": run.artifacts,
                },
            )
        except asyncio.CancelledError:
            run.status = "cancelled"
            if not run.error:
                run.error = "Cancelled"
            await self._publish(
                run,
                {
                    "type": "run.error",
                    "stepId": "run",
                    "label": "Run cancelled",
                    "status": "error",
                    "message": "Cancelled",
                },
            )
            raise
        except Exception as exc:
            run.status = "error"
            run.error = str(exc)
            await self._publish(
                run,
                {
                    "type": "run.error",
                    "stepId": "run",
                    "label": "Run failed",
                    "status": "error",
                    "message": str(exc),
                },
            )
        finally:
            await self._stop_services(run)

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "contractAddress": os.environ.get(
                "ESCROW_CONTRACT_ADDRESS",
                "0xFBf9b5293A1737AC53880d3160a64B49bA54801D",
            ),
            "chainId": int(os.environ.get("GOAT_CHAIN_ID", "48816")),
            "chainRpc": os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network"),
            "ports": {
                "evidence": 4001,
                "provider": 4000,
                "judge": 4002,
                "reputation": 4003,
                "runner": _RUNNER_PORT,
            },
        }


_MANAGER: DemoRunManager | None = None


def get_manager() -> DemoRunManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = DemoRunManager()
    return _MANAGER


def serialize_run(run: DemoRun) -> dict[str, Any]:
    return {
        "runId": run.run_id,
        "mode": run.mode,
        "status": run.status,
        "startMs": run.start_ms,
        "updateMs": run.update_ms,
        "currentStep": run.current_step,
        "steps": run.steps,
        "artifacts": run.artifacts,
        "errors": [run.error] if run.error else [],
        "agreementIds": run.agreement_ids,
        "disputeIds": run.dispute_ids,
        "startServices": run.start_services,
        "keepServices": run.keep_services,
    }
