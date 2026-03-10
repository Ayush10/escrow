from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from verdict_protocol import EscrowClient

from .storage import EvidenceStorage


@dataclass(slots=True)
class ServerState:
    storage: EvidenceStorage
    escrow: EscrowClient


def get_state(request: Request) -> ServerState:
    state = getattr(request.app.state, "server_state", None)
    if state is None:
        raise RuntimeError("server state not initialized")
    return state
