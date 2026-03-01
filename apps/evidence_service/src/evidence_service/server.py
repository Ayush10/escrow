from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from verdict_protocol import EscrowClient

from .routes import router
from .server_state import ServerState
from .storage import EvidenceStorage


def create_app() -> FastAPI:
    app = FastAPI(title="Evidence Service", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    db_path = os.environ.get("SQLITE_PATH", "./data/verdict.db")
    storage = EvidenceStorage(db_path)

    escrow = EscrowClient(
        rpc_url=os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network"),
        chain_id=int(os.environ.get("GOAT_CHAIN_ID", "48816")),
        contract_address=os.environ.get("ESCROW_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"),
        private_key=os.environ.get("PROVIDER_PRIVATE_KEY") or None,
        dry_run=os.environ.get("ESCROW_DRY_RUN", "0") == "1",
    )

    app.state.server_state = ServerState(storage=storage, escrow=escrow)
    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, object]:
        sanity = app.state.server_state.escrow.contract_sanity()
        status = "ok"
        if (not sanity["contractHasCode"]) and (not sanity["dryRun"]):
            status = "degraded"
        return {"status": status, "escrow": sanity}

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("evidence_service.server:app", host="0.0.0.0", port=4001, reload=False)


if __name__ == "__main__":
    main()
