import os
import tempfile

from reputation_service.storage import ReputationStorage


def test_reputation_storage_exposes_v2_profile_fields() -> None:
    with tempfile.TemporaryDirectory() as td:
        os.environ["SQLITE_PATH"] = f"{td}/reputation.db"
        storage = ReputationStorage(os.environ["SQLITE_PATH"])

        actor = "did:8004:0x" + "1" * 40
        storage.apply_event(
            actor_id=actor,
            delta=1,
            reason="completed_without_dispute",
            event_key="event-1",
            payload={"txHash": "0x" + "2" * 64},
        )
        storage.apply_event(
            actor_id=actor,
            delta=2,
            reason="won_dispute",
            event_key="event-2",
            payload={"disputeId": 9},
        )

        record = storage.get_reputation(actor)
        assert record["modelVersion"] == "2.0.0-draft"
        assert record["components"]["service"] == 1
        assert record["components"]["court"] == 2
        assert record["stats"]["eventCount"] == 2
        assert record["stats"]["confidence"] >= 0.1

        leaderboard = storage.list_reputations()
        assert leaderboard
        assert leaderboard[0]["actorId"] == actor
        assert leaderboard[0]["modelVersion"] == "2.0.0-draft"
