import os
import tempfile

import pytest

from verdict_protocol import EscrowClient


def test_escrow_client_dry_run_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as td:
        os.environ["ESCROW_MOCK_DB_PATH"] = f"{td}/escrow_mock.db"

        client = EscrowClient(
            rpc_url="https://rpc.testnet3.goat.network",
            chain_id=48816,
            contract_address="0x" + "1" * 40,
            private_key="0x" + "1" * 64,
            dry_run=True,
        )

        root_hash = "0x" + "a" * 64
        commit = client.commit_evidence_hash("agreement-1", root_hash)
        assert commit.status == 1

        dispute = client.file_dispute(
            "agreement-1",
            tx_id=42,
            defendant="0x" + "2" * 40,
            stake=100,
            plaintiff_evidence=root_hash,
        )
        assert dispute.status == 1
        dispute_id = int(dispute.extra["disputeId"])

        loaded = client.get_dispute(dispute_id)
        assert loaded is not None
        assert loaded[0] == 42
        assert loaded[8] is False

        ruling = client.submit_ruling(
            dispute_id,
            {
                "winner": "0x" + "1" * 40,
                "transfers": [
                    {
                        "to": "0x" + "1" * 40,
                        "amount": "200",
                        "reason": "dispute_resolution",
                    }
                ],
            },
        )
        assert ruling.status == 1

        updated = client.get_dispute(dispute_id)
        assert updated is not None
        assert updated[8] is True
        assert updated[9].lower() == ("0x" + "1" * 40)

        dispute_events = client.poll_events("DisputeFiled", from_block=0)
        ruling_events = client.poll_events("RulingSubmitted", from_block=0)
        evidence_events = client.poll_events("EvidenceCommitted", from_block=0)

        assert dispute_events
        assert ruling_events
        assert evidence_events


def test_escrow_client_dry_run_is_idempotent_for_anchor_and_dispute() -> None:
    with tempfile.TemporaryDirectory() as td:
        os.environ["ESCROW_MOCK_DB_PATH"] = f"{td}/escrow_mock.db"

        client = EscrowClient(
            rpc_url="https://rpc.testnet3.goat.network",
            chain_id=48816,
            contract_address="0x" + "1" * 40,
            private_key="0x" + "1" * 64,
            dry_run=True,
        )

        root_hash = "0x" + "a" * 64
        first_commit = client.commit_evidence_hash("agreement-1", root_hash)
        second_commit = client.commit_evidence_hash("agreement-1", root_hash)
        assert second_commit.extra == {"idempotent": True}
        assert second_commit.tx_hash == first_commit.tx_hash
        assert second_commit.block_number == first_commit.block_number

        with pytest.raises(ValueError, match="different root_hash"):
            client.commit_evidence_hash("agreement-1", "0x" + "b" * 64)

        first_dispute = client.file_dispute(
            "agreement-1",
            tx_id=42,
            defendant="0x" + "2" * 40,
            stake=100,
            plaintiff_evidence=root_hash,
        )
        second_dispute = client.file_dispute(
            "agreement-1",
            tx_id=42,
            defendant="0x" + "2" * 40,
            stake=100,
            plaintiff_evidence=root_hash,
        )
        assert second_dispute.extra == {
            "disputeId": int(first_dispute.extra["disputeId"]),
            "idempotent": True,
        }
        assert second_dispute.tx_hash == first_dispute.tx_hash
        assert second_dispute.block_number == first_dispute.block_number

        dispute_events = client.poll_events("DisputeFiled", from_block=0)
        evidence_events = client.poll_events("EvidenceCommitted", from_block=0)
        assert len(dispute_events) == 1
        assert len(evidence_events) == 1
