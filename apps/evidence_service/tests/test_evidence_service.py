import os
import tempfile
import uuid

from eth_account import Account
from fastapi.testclient import TestClient
from verdict_protocol import compute_receipt_hash, hash_canonical, sign_hash_eip191


def test_receipt_ingest_and_anchor() -> None:
    with tempfile.TemporaryDirectory() as td:
        os.environ["SQLITE_PATH"] = f"{td}/ev.db"
        os.environ["ESCROW_DRY_RUN"] = "1"
        os.environ["ESCROW_CONTRACT_ADDRESS"] = "0x" + "1" * 40

        from evidence_service.server import create_app

        app = create_app()
        client = TestClient(app)

        account_a = Account.create()
        account_b = Account.create()

        agreement_id = str(uuid.uuid4())
        clause = {
            "schemaVersion": "1.0.0",
            "clauseId": str(uuid.uuid4()),
            "chainId": 48816,
            "contractAddress": "0x" + "1" * 40,
            "agreementId": agreement_id,
            "serviceScope": "GET /api/data",
            "slaRules": [],
            "abuseRules": [],
            "disputeWindowSec": 30,
            "evidenceWindowSec": 30,
            "remedyRules": [],
            "judgeFeePercent": 5,
            "clauseHash": "0x" + "a" * 64,
        }

        from verdict_protocol import compute_clause_hash

        clause["clauseHash"] = compute_clause_hash(clause)

        assert client.post("/clauses", json=clause).status_code == 200

        receipt = {
            "schemaVersion": "1.0.0",
            "receiptId": str(uuid.uuid4()),
            "chainId": 48816,
            "contractAddress": "0x" + "1" * 40,
            "agreementId": agreement_id,
            "clauseHash": clause["clauseHash"],
            "sequence": 0,
            "eventType": "request",
            "timestamp": 123456,
            "actorId": f"did:8004:{account_a.address}",
            "counterpartyId": f"did:8004:{account_b.address}",
            "requestId": "r1",
            "payloadHash": hash_canonical({"x": 1}),
            "prevHash": "0x0",
            "metadata": {},
            "receiptHash": "",
            "signature": "",
        }
        receipt["receiptHash"] = compute_receipt_hash(receipt)
        receipt["signature"] = sign_hash_eip191(account_a.key.hex(), receipt["receiptHash"])

        assert client.post("/receipts", json=receipt).status_code == 200

        anchor_resp = client.post("/anchor", json={"agreementId": agreement_id})
        assert anchor_resp.status_code == 200
        payload = anchor_resp.json()
        assert payload["agreementId"] == agreement_id
        assert payload["rootHash"].startswith("0x")
        assert payload["txHash"].startswith("0x")
