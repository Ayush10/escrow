from __future__ import annotations

from dataclasses import dataclass

from verdict_protocol import EscrowClient

from .storage import EvidenceStorage


@dataclass(slots=True)
class ServerState:
    storage: EvidenceStorage
    escrow: EscrowClient


def get_state() -> ServerState:
    from .server import app

    state = getattr(app.state, "server_state", None)
    if state is None:
        raise RuntimeError("server state not initialized")
    return state
