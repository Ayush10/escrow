from __future__ import annotations

import json
import os
import time
import uuid

from .client_x402 import X402Client
from .escrow_client import build_client
from .receipt_client import ReceiptClient


def run() -> dict:
    evidence_url = os.environ.get("EVIDENCE_SERVICE_URL", "http://127.0.0.1:4001")
    provider_url = os.environ.get("PROVIDER_API_URL", "http://127.0.0.1:4000")

    provider_key = os.environ.get("PROVIDER_PRIVATE_KEY", "")
    consumer_key = os.environ.get("CONSUMER_PRIVATE_KEY", "")
    if not provider_key or not consumer_key:
        raise RuntimeError("PROVIDER_PRIVATE_KEY and CONSUMER_PRIVATE_KEY are required")

    rc = ReceiptClient(evidence_url)
    provider_actor = rc.actor_from_key(provider_key)
    consumer_actor = rc.actor_from_key(consumer_key)

    agreement_id = str(uuid.uuid4())
    chain_id = int(os.environ.get("GOAT_CHAIN_ID", "48816"))
    contract_addr = os.environ.get(
        "ESCROW_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"
    )

    clause = rc.create_clause(
        agreement_id=agreement_id,
        chain_id=chain_id,
        contract_address=contract_addr,
    )
    rc.post_clause(clause)

    provider_escrow = build_client(provider_key)
    consumer_escrow = build_client(consumer_key)

    deposit_tx = provider_escrow.deposit_pool(10**15)
    bond_tx = consumer_escrow.post_bond(agreement_id, 10**15)

    x402 = X402Client(consumer_key)
    request_id = str(uuid.uuid4())

    req_payload = {"path": "/api/data", "requestId": request_id}
    req_receipt = rc.create_receipt(
        chain_id=chain_id,
        contract_address=contract_addr,
        agreement_id=agreement_id,
        clause_hash=clause["clauseHash"],
        sequence=0,
        actor=consumer_actor,
        counterparty=provider_actor,
        event_type="request",
        request_id=request_id,
        payload=req_payload,
        prev_hash="0x0",
    )
    rc.post_receipt(req_receipt)

    response = x402.get(f"{provider_url}/api/data")
    res_payload = response.payload

    res_receipt = rc.create_receipt(
        chain_id=chain_id,
        contract_address=contract_addr,
        agreement_id=agreement_id,
        clause_hash=clause["clauseHash"],
        sequence=1,
        actor=provider_actor,
        counterparty=consumer_actor,
        event_type="response",
        request_id=request_id,
        payload=res_payload,
        prev_hash=req_receipt["receiptHash"],
        metadata={
            "status_code": response.status_code,
            "evidence_hash": response.headers.get("x-evidence-hash", ""),
        },
    )
    rc.post_receipt(res_receipt)

    payment_receipt = rc.create_receipt(
        chain_id=chain_id,
        contract_address=contract_addr,
        agreement_id=agreement_id,
        clause_hash=clause["clauseHash"],
        sequence=2,
        actor=consumer_actor,
        counterparty=provider_actor,
        event_type="payment",
        request_id=request_id,
        payload={"network": os.environ.get("X402_NETWORK", "eip155:84532")},
        prev_hash=res_receipt["receiptHash"],
        metadata={"x402_payment_reference": response.payment_reference},
    )
    rc.post_receipt(payment_receipt)

    anchor = rc.anchor(agreement_id)
    time.sleep(1)

    result = {
        "mode": "happy",
        "agreementId": agreement_id,
        "depositTx": deposit_tx.tx_hash,
        "bondTx": bond_tx.tx_hash,
        "receiptIds": [
            req_receipt["receiptId"],
            res_receipt["receiptId"],
            payment_receipt["receiptId"],
        ],
        "anchor": anchor,
        "x402PaymentReference": response.payment_reference,
    }
    return result


def main() -> None:
    result = run()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
