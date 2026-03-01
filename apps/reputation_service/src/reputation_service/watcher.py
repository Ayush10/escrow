from __future__ import annotations

import asyncio
from dataclasses import dataclass

from verdict_protocol import EscrowClient

from .scorer import SCORES, to_did
from .storage import ReputationStorage


@dataclass(slots=True)
class ReputationWatcher:
    storage: ReputationStorage
    escrow: EscrowClient

    async def run_forever(self, poll_sec: float) -> None:
        from_block = self.storage.get_cursor("reputation.from_block", 0)
        while True:
            try:
                from_block = self.poll_once(from_block)
                self.storage.set_cursor("reputation.from_block", from_block)
            except Exception:
                pass
            await asyncio.sleep(poll_sec)

    def poll_once(self, from_block: int) -> int:
        last_block = from_block

        rulings = self.escrow.poll_events("RulingSubmitted", from_block, "latest")
        for log in rulings:
            args = log.get("args", {})
            dispute_id = int(args.get("disputeId", 0))
            winner = args.get("winner")
            loser = args.get("loser")

            dispute = self.escrow.get_dispute(dispute_id)
            plaintiff = dispute[0] if dispute else None

            if winner:
                self.storage.apply_event(
                    actor_id=to_did(winner),
                    delta=SCORES["won_dispute"],
                    reason="won_dispute",
                    event_key=f"ruling-win-{dispute_id}-{winner}",
                    payload={"disputeId": dispute_id},
                )
            if loser:
                self.storage.apply_event(
                    actor_id=to_did(loser),
                    delta=SCORES["lost_dispute"],
                    reason="lost_dispute",
                    event_key=f"ruling-lose-{dispute_id}-{loser}",
                    payload={"disputeId": dispute_id},
                )
                if plaintiff and loser.lower() == plaintiff.lower():
                    self.storage.apply_event(
                        actor_id=to_did(loser),
                        delta=SCORES["lost_as_filer"],
                        reason="lost_as_filer",
                        event_key=f"ruling-filer-loss-{dispute_id}-{loser}",
                        payload={"disputeId": dispute_id},
                    )

            last_block = max(last_block, int(log.get("blockNumber", from_block)))

        commits = self.escrow.poll_events("EvidenceCommitted", from_block, "latest")
        for log in commits:
            args = log.get("args", {})
            agent = args.get("agent")
            if agent:
                self.storage.apply_event(
                    actor_id=to_did(agent),
                    delta=SCORES["completed_without_dispute"],
                    reason="completed_without_dispute",
                    event_key=f"evidence-commit-{log.get('transactionHash')}-{agent}",
                    payload={"txHash": str(log.get("transactionHash"))},
                )
            last_block = max(last_block, int(log.get("blockNumber", from_block)))

        return last_block + 1
