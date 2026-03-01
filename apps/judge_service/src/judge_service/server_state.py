from __future__ import annotations

from dataclasses import dataclass

from verdict_protocol import EscrowClient

from .llm_judge import LLMJudge
from .storage import JudgeStorage
from .watcher import DisputeWatcher


@dataclass(slots=True)
class JudgeState:
    storage: JudgeStorage
    escrow: EscrowClient
    watcher: DisputeWatcher
    llm: LLMJudge
    evidence_url: str
