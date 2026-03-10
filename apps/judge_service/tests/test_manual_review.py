import os
import tempfile
import uuid

import pytest
from eth_account import Account


class FakeEscrow:
    def __init__(self, dispute):
        self._dispute = dispute
        self.account = type("A", (), {"address": dispute[1]})()

    def get_dispute(self, dispute_id: int):
        assert dispute_id == 7
        return self._dispute

    def judge_address(self):
        return self.account.address

    def submit_ruling(self, dispute_id, verdict):
        raise AssertionError(f"submit_ruling should not be called for manual review: {dispute_id} {verdict}")


class FakeLowConfidenceLLM:
    def judge(self, clause, facts, evidence_summary, tier=0):
        _ = (clause, facts, evidence_summary, tier)
        return ["manual_review_needed"], "plaintiff", 0.2, "Draft opinion"


@pytest.mark.asyncio
async def test_low_confidence_dispute_goes_to_manual_review(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        os.environ["SQLITE_PATH"] = f"{td}/judge.db"
        os.environ["GOAT_CHAIN_ID"] = "48816"
        os.environ["ESCROW_CONTRACT_ADDRESS"] = "0x" + "1" * 40
        os.environ["JUDGE_PRIVATE_KEY"] = Account.create().key.hex()

        from judge_service.server import _handle_dispute
        from judge_service.server_state import JudgeState
        from judge_service.signer import build_judge_signer
        from judge_service.storage import JudgeStorage
        from judge_service.watcher import DisputeEvent

        plaintiff = Account.create()
        defendant = Account.create()

        dispute = (
            55,
            plaintiff.address,
            defendant.address,
            100,
            5,
            0,
            "0x0",
            "0x0",
            False,
            "0x" + "0" * 40,
        )

        clause = {
            "schemaVersion": "1.0.0",
            "clauseId": str(uuid.uuid4()),
            "chainId": 48816,
            "contractAddress": "0x" + "1" * 40,
            "agreementId": "agreement-review",
            "serviceScope": "GET /api/data",
            "slaRules": [],
            "abuseRules": [],
            "disputeWindowSec": 30,
            "evidenceWindowSec": 30,
            "remedyRules": [],
            "judgeFeePercent": 5,
            "clauseHash": "0x" + "2" * 64,
        }

        state = JudgeState(
            storage=JudgeStorage(os.environ["SQLITE_PATH"]),
            escrow=FakeEscrow(dispute),
            watcher=None,
            llm=FakeLowConfidenceLLM(),
            signer=build_judge_signer(),
            evidence_url="http://unused",
        )

        async def fake_bundle(url, root_hash):
            _ = (url, root_hash)
            return {
                "agreementId": "agreement-review",
                "anchor": {"rootHash": "0x0"},
                "clause": clause,
                "receipts": [],
            }

        monkeypatch.setattr("judge_service.server._get_evidence_bundle", fake_bundle)
        monkeypatch.setattr("judge_service.server.send_telegram_notification", lambda _: None)

        await _handle_dispute(
            state,
            DisputeEvent(dispute_id=7, plaintiff=plaintiff.address, defendant=defendant.address, block_number=1),
        )

        items = state.storage.list_manual_review()
        assert len(items) == 1
        assert items[0]["status"] == "manual_review"
        assert items[0]["reviewReason"] == "low_confidence"
        assert "needs_manual_review" in items[0]["flags"]
