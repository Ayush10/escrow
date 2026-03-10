import os
import tempfile
import uuid

from eth_account import Account
from fastapi.testclient import TestClient
from verdict_protocol import compute_clause_hash, compute_receipt_hash, hash_canonical, sign_hash_eip191


def _make_clause(agreement_id: str) -> dict[str, object]:
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
    clause["clauseHash"] = compute_clause_hash(clause)
    return clause


def _make_receipt(
    *,
    account_a,
    account_b,
    agreement_id: str,
    clause_hash: str,
    sequence: int,
    request_id: str = "r1",
    event_type: str = "request",
    prev_hash: str = "0x0",
    payload: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
    timestamp: int = 123456,
) -> dict[str, object]:
    receipt = {
        "schemaVersion": "1.0.0",
        "receiptId": str(uuid.uuid4()),
        "chainId": 48816,
        "contractAddress": "0x" + "1" * 40,
        "agreementId": agreement_id,
        "clauseHash": clause_hash,
        "sequence": sequence,
        "eventType": event_type,
        "timestamp": timestamp,
        "actorId": f"did:8004:{account_a.address}",
        "counterpartyId": f"did:8004:{account_b.address}",
        "requestId": request_id,
        "payloadHash": hash_canonical(payload or {"x": sequence}),
        "prevHash": prev_hash,
        "metadata": metadata or {},
        "receiptHash": "",
        "signature": "",
    }
    receipt["receiptHash"] = compute_receipt_hash(receipt)
    receipt["signature"] = sign_hash_eip191(account_a.key.hex(), receipt["receiptHash"])
    return receipt


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
        clause = _make_clause(agreement_id)
        assert client.post("/clauses", json=clause).status_code == 200

        receipt = _make_receipt(
            account_a=account_a,
            account_b=account_b,
            agreement_id=agreement_id,
            clause_hash=clause["clauseHash"],
            sequence=0,
            payload={"x": 1},
        )

        assert client.post("/receipts", json=receipt).status_code == 200

        anchor_resp = client.post("/anchor", json={"agreementId": agreement_id})
        assert anchor_resp.status_code == 200
        payload = anchor_resp.json()
        assert payload["agreementId"] == agreement_id
        assert payload["rootHash"].startswith("0x")
        assert payload["txHash"].startswith("0x")


def test_agreement_export_returns_complete_bundle() -> None:
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
        clause = _make_clause(agreement_id)
        assert client.post("/clauses", json=clause).status_code == 200

        receipt = _make_receipt(
            account_a=account_a,
            account_b=account_b,
            agreement_id=agreement_id,
            clause_hash=clause["clauseHash"],
            sequence=0,
            payload={"x": 1},
        )
        assert client.post("/receipts", json=receipt).status_code == 200
        assert client.post("/anchor", json={"agreementId": agreement_id}).status_code == 200

        export_resp = client.get(f"/agreements/{agreement_id}/export")
        assert export_resp.status_code == 200
        payload = export_resp.json()
        assert payload["schemaVersion"] == "1.0.0"
        assert payload["exportType"] == "evidence_bundle"
        assert payload["agreementId"] == agreement_id
        assert payload["receiptCount"] == 1
        assert payload["receiptChain"]["valid"] is True
        assert payload["receiptChain"]["receiptHashes"] == [receipt["receiptHash"]]
        assert payload["integrity"]["clauseHashValid"] is True
        assert payload["integrity"]["rootAnchored"] is True


def test_receipt_post_is_idempotent_for_same_logical_receipt() -> None:
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
        clause = _make_clause(agreement_id)
        assert client.post("/clauses", json=clause).status_code == 200

        first = _make_receipt(
            account_a=account_a,
            account_b=account_b,
            agreement_id=agreement_id,
            clause_hash=clause["clauseHash"],
            sequence=0,
            payload={"x": 1},
            timestamp=123456,
        )
        second = _make_receipt(
            account_a=account_a,
            account_b=account_b,
            agreement_id=agreement_id,
            clause_hash=clause["clauseHash"],
            sequence=0,
            payload={"x": 1},
            timestamp=999999,
        )

        first_resp = client.post("/receipts", json=first)
        assert first_resp.status_code == 200

        second_resp = client.post("/receipts", json=second)
        assert second_resp.status_code == 200
        assert second_resp.json()["idempotent"] is True
        assert second_resp.json()["receiptId"] == first["receiptId"]

        receipts = client.get("/receipts", params={"agreementId": agreement_id}).json()["items"]
        assert len(receipts) == 1
        assert receipts[0]["receiptId"] == first["receiptId"]


def test_anchor_post_is_idempotent_and_rejects_conflicting_reanchor() -> None:
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
        clause = _make_clause(agreement_id)
        assert client.post("/clauses", json=clause).status_code == 200

        first = _make_receipt(
            account_a=account_a,
            account_b=account_b,
            agreement_id=agreement_id,
            clause_hash=clause["clauseHash"],
            sequence=0,
            payload={"x": 1},
        )
        assert client.post("/receipts", json=first).status_code == 200

        anchor_one = client.post("/anchor", json={"agreementId": agreement_id})
        assert anchor_one.status_code == 200

        anchor_two = client.post("/anchor", json={"agreementId": agreement_id})
        assert anchor_two.status_code == 200
        assert anchor_two.json()["idempotent"] is True
        assert anchor_two.json()["txHash"] == anchor_one.json()["txHash"]

        second = _make_receipt(
            account_a=account_b,
            account_b=account_a,
            agreement_id=agreement_id,
            clause_hash=clause["clauseHash"],
            sequence=1,
            event_type="response",
            prev_hash=first["receiptHash"],
            payload={"ok": True},
        )
        assert client.post("/receipts", json=second).status_code == 200

        conflict = client.post("/anchor", json={"agreementId": agreement_id})
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["error"] == "anchor_conflict"
