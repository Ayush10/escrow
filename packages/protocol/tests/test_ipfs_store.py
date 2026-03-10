import tempfile

from verdict_protocol import EvidenceBundleStore


def test_local_ipfs_store_pins_and_loads_json() -> None:
    payload = {"agreementId": "a1", "receipts": [{"receiptId": "r1"}]}
    with tempfile.TemporaryDirectory() as td:
        store = EvidenceBundleStore(mode="local", local_store_path=td)
        stored = store.pin_json("agreement-a1", payload)

        assert stored.cid.startswith("bafy")
        assert stored.uri == f"ipfs://{stored.cid}"
        assert stored.bundle_hash.startswith("0x")
        assert store.load_json(stored.cid) == payload


def test_local_ipfs_store_is_deterministic_for_same_payload() -> None:
    payload = {"agreementId": "a2", "receipts": [{"receiptId": "r1"}]}
    with tempfile.TemporaryDirectory() as td:
        store = EvidenceBundleStore(mode="local", local_store_path=td)
        first = store.pin_json("agreement-a2", payload)
        second = store.pin_json("agreement-a2-repeat", payload)

        assert first.cid == second.cid
        assert first.bundle_hash == second.bundle_hash
