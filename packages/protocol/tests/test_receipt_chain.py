import uuid

from eth_account import Account
from verdict_protocol import (
    compute_receipt_hash,
    hash_canonical,
    sign_hash_eip191,
    verify_receipt_chain,
)


def _make_receipt(*, seq: int, prev_hash: str, actor_key: str, actor_did: str, counterparty_did: str):
    receipt = {
        "schemaVersion": "1.0.0",
        "receiptId": str(uuid.uuid4()),
        "chainId": 48816,
        "contractAddress": "0x" + "1" * 40,
        "agreementId": "agreement-1",
        "clauseHash": "0x" + "2" * 64,
        "sequence": seq,
        "eventType": "request" if seq == 0 else "response",
        "timestamp": 1000 + seq,
        "actorId": actor_did,
        "counterpartyId": counterparty_did,
        "requestId": "req-1",
        "payloadHash": hash_canonical({"seq": seq}),
        "prevHash": prev_hash,
        "metadata": {},
        "receiptHash": "",
        "signature": "",
    }
    receipt["receiptHash"] = compute_receipt_hash(receipt)
    receipt["signature"] = sign_hash_eip191(actor_key, receipt["receiptHash"])
    return receipt


def test_receipt_chain_valid_and_tampered() -> None:
    a = Account.create()
    b = Account.create()
    a_did = f"did:8004:{a.address}"
    b_did = f"did:8004:{b.address}"

    r0 = _make_receipt(seq=0, prev_hash="0x0", actor_key=a.key.hex(), actor_did=a_did, counterparty_did=b_did)
    r1 = _make_receipt(
        seq=1,
        prev_hash=r0["receiptHash"],
        actor_key=b.key.hex(),
        actor_did=b_did,
        counterparty_did=a_did,
    )

    result_ok = verify_receipt_chain([r0, r1])
    assert result_ok.ok

    tampered = dict(r1)
    tampered["prevHash"] = "0x" + "0" * 64

    result_bad = verify_receipt_chain([r0, tampered])
    assert not result_bad.ok
