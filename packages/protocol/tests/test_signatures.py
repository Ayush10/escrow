from eth_account import Account
from verdict_protocol import recover_signer_eip191, sign_hash_eip191, verify_signature_eip191


def test_signature_verify_pass_and_fail() -> None:
    actor = Account.create()
    other = Account.create()
    digest = "0x" + "11" * 32

    sig = sign_hash_eip191(actor.key.hex(), digest)

    assert verify_signature_eip191(digest, sig, actor.address)
    assert not verify_signature_eip191(digest, sig, other.address)
    assert recover_signer_eip191(digest, sig).lower() == actor.address.lower()
