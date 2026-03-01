import os
import tempfile
import uuid

import pytest
from eth_account import Account
from verdict_protocol import (
    compute_receipt_hash,
    hash_canonical,
    merkle_root_hash,
    sign_hash_eip191,
)


class _Tx:
    def __init__(self):
        self.tx_hash = "0x" + "3" * 64
        self.status = 1
        self.block_number = 1


class FakeEscrow:
    def __init__(self, dispute):
        self._dispute = dispute
        self.account = type("A", (), {"address": dispute[0]})()

    def get_dispute(self, dispute_id: int):
        assert dispute_id == 1
        return self._dispute

    def judge_address(self):
        return self.account.address

    def submit_ruling(self, dispute_id, verdict):
        _ = (dispute_id, verdict)
        return _Tx()


class FakeLLM:
    def judge(self, clause, facts, evidence_summary):
        _ = (clause, facts, evidence_summary)
        return ["llm_unused"], None, 0.5


@pytest.mark.asyncio
async def test_judge_pipeline_deterministic_submission(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        os.environ["SQLITE_PATH"] = f"{td}/judge.db"
        os.environ["GOAT_CHAIN_ID"] = "48816"
        os.environ["ESCROW_CONTRACT_ADDRESS"] = "0x" + "1" * 40
        os.environ["ESCROW_DRY_RUN"] = "1"

        judge_key = Account.create().key.hex()
        os.environ["JUDGE_PRIVATE_KEY"] = judge_key

        from judge_service.server import _handle_dispute
        from judge_service.server_state import JudgeState
        from judge_service.storage import JudgeStorage
        from judge_service.watcher import DisputeEvent

        plaintiff = Account.create()
        defendant = Account.create()

        clause = {
            "schemaVersion": "1.0.0",
            "clauseId": str(uuid.uuid4()),
            "chainId": 48816,
            "contractAddress": "0x" + "1" * 40,
            "agreementId": "agreement-test",
            "serviceScope": "GET /api/data",
            "slaRules": [
                {
                    "ruleId": "latency",
                    "metric": "latency_ms",
                    "operator": "<=",
                    "value": 3000,
                    "unit": "ms",
                }
            ],
            "abuseRules": [],
            "disputeWindowSec": 30,
            "evidenceWindowSec": 30,
            "remedyRules": [{"condition": "sla_breach", "action": "refund", "percent": 100}],
            "judgeFeePercent": 5,
            "clauseHash": "0x" + "2" * 64,
        }

        r0 = {
            "schemaVersion": "1.0.0",
            "receiptId": str(uuid.uuid4()),
            "chainId": 48816,
            "contractAddress": "0x" + "1" * 40,
            "agreementId": "agreement-test",
            "clauseHash": clause["clauseHash"],
            "sequence": 0,
            "eventType": "request",
            "timestamp": 1000,
            "actorId": f"did:8004:{plaintiff.address}",
            "counterpartyId": f"did:8004:{defendant.address}",
            "requestId": "req-1",
            "payloadHash": hash_canonical({"req": 1}),
            "prevHash": "0x0",
            "metadata": {},
            "receiptHash": "",
            "signature": "",
        }
        r0["receiptHash"] = compute_receipt_hash(r0)
        r0["signature"] = sign_hash_eip191(plaintiff.key.hex(), r0["receiptHash"])

        r1 = {
            "schemaVersion": "1.0.0",
            "receiptId": str(uuid.uuid4()),
            "chainId": 48816,
            "contractAddress": "0x" + "1" * 40,
            "agreementId": "agreement-test",
            "clauseHash": clause["clauseHash"],
            "sequence": 1,
            "eventType": "response",
            "timestamp": 5000,
            "actorId": f"did:8004:{defendant.address}",
            "counterpartyId": f"did:8004:{plaintiff.address}",
            "requestId": "req-1",
            "payloadHash": hash_canonical({"res": 1}),
            "prevHash": r0["receiptHash"],
            "metadata": {},
            "receiptHash": "",
            "signature": "",
        }
        r1["receiptHash"] = compute_receipt_hash(r1)
        r1["signature"] = sign_hash_eip191(defendant.key.hex(), r1["receiptHash"])

        root = merkle_root_hash([r0["receiptHash"], r1["receiptHash"]])

        dispute = (
            plaintiff.address,
            defendant.address,
            100,
            100,
            bytes.fromhex(root[2:]),
            bytes.fromhex("00" * 32),
            False,
            "0x" + "0" * 40,
        )

        fake_state = JudgeState(
            storage=JudgeStorage(os.environ["SQLITE_PATH"]),
            escrow=FakeEscrow(dispute),
            watcher=None,
            llm=FakeLLM(),
            evidence_url="http://unused",
        )

        async def fake_bundle(url, root_hash):
            _ = (url, root_hash)
            return {
                "agreementId": "agreement-test",
                "anchor": {"rootHash": root},
                "clause": clause,
                "receipts": [r0, r1],
            }

        monkeypatch.setattr("judge_service.server._get_evidence_bundle", fake_bundle)
        monkeypatch.setattr("judge_service.server.send_telegram_notification", lambda _: None)

        await _handle_dispute(
            fake_state,
            DisputeEvent(dispute_id=1, plaintiff=plaintiff.address, defendant=defendant.address, block_number=1),
        )

        verdicts = fake_state.storage.list_verdicts()
        assert verdicts
        assert verdicts[0]["status"] == "submitted"
        assert verdicts[0]["winner"].lower() == plaintiff.address.lower()
