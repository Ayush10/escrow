from __future__ import annotations

import asyncio
import contextlib
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from verdict_protocol import EscrowClient

from .storage import ReputationStorage
from .watcher import ReputationWatcher


def create_app() -> FastAPI:
    app = FastAPI(title="Reputation Service", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    storage = ReputationStorage(os.environ.get("SQLITE_PATH", "./data/verdict.db"))
    escrow = EscrowClient(
        rpc_url=os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network"),
        chain_id=int(os.environ.get("GOAT_CHAIN_ID", "48816")),
        contract_address=os.environ.get("ESCROW_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"),
        private_key=None,
        dry_run=os.environ.get("ESCROW_DRY_RUN", "0") == "1",
    )
    watcher = ReputationWatcher(storage=storage, escrow=escrow)
    app.state.reputation_watcher = watcher

    @app.on_event("startup")
    async def startup() -> None:
        poll = float(os.environ.get("REPUTATION_POLL_SEC", "5"))
        app.state.watcher_task = asyncio.create_task(watcher.run_forever(poll))

    @app.on_event("shutdown")
    async def shutdown() -> None:
        task = getattr(app.state, "watcher_task", None)
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    @app.get("/health")
    def health() -> dict[str, object]:
        sanity = watcher.escrow.contract_sanity()
        status = "ok"
        if (not sanity["contractHasCode"]) and (not sanity["dryRun"]):
            status = "degraded"
        return {"status": status, "escrow": sanity}

    @app.get("/reputation/{actor_id}")
    def get_reputation(actor_id: str) -> dict:
        return storage.get_reputation(actor_id)

    @app.get("/reputation")
    def list_reputation() -> dict:
        items = storage.list_reputations()
        return {"count": len(items), "items": items}

    return app

app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("reputation_service.api:app", host="0.0.0.0", port=4003, reload=False)


if __name__ == "__main__":
    main()
