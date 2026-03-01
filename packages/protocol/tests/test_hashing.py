from verdict_protocol import hash_canonical


def test_hashing_is_stable() -> None:
    payload = {"foo": "bar", "n": 1}
    assert hash_canonical(payload) == hash_canonical({"n": 1, "foo": "bar"})
    assert hash_canonical(payload).startswith("0x")
    assert len(hash_canonical(payload)) == 66
