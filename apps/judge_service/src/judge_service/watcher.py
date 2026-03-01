from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from verdict_protocol import EscrowClient


@dataclass(slots=True)
class DisputeEvent:
    dispute_id: int
    plaintiff: str
    defendant: str
    block_number: int


class DisputeWatcher:
    def __init__(self, escrow: EscrowClient) -> None:
        self.escrow = escrow

    def poll(self, from_block: int, to_block: int | str = "latest") -> tuple[list[DisputeEvent], int]:
        logs = self.escrow.poll_events("DisputeFiled", from_block=from_block, to_block=to_block)
        events: list[DisputeEvent] = []
        last_block = from_block

        for log in logs:
            args: dict[str, Any] = log.get("args", {})
            block_num = int(log.get("blockNumber", from_block))
            last_block = max(last_block, block_num)
            events.append(
                DisputeEvent(
                    dispute_id=int(args.get("disputeId", 0)),
                    plaintiff=args.get("plaintiff", ""),
                    defendant=args.get("defendant", ""),
                    block_number=block_num,
                )
            )

        return events, (last_block + 1)
