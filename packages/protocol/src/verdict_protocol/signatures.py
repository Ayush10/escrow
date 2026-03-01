from __future__ import annotations

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_checksum_address


def sign_hash_eip191(private_key: str, digest_hex: str) -> str:
    message = encode_defunct(hexstr=digest_hex)
    signed = Account.sign_message(message, private_key=private_key)
    raw = signed.signature.hex()
    return raw if raw.startswith("0x") else f"0x{raw}"


def recover_signer_eip191(digest_hex: str, signature: str) -> str:
    message = encode_defunct(hexstr=digest_hex)
    signer = Account.recover_message(message, signature=signature)
    return to_checksum_address(signer)


def verify_signature_eip191(digest_hex: str, signature: str, expected_address: str) -> bool:
    recovered = recover_signer_eip191(digest_hex, signature)
    return recovered == to_checksum_address(expected_address)


def did_to_address(actor_id: str) -> str:
    if not actor_id.startswith("did:8004:0x"):
        raise ValueError("invalid did: expected did:8004:0x...")
    return to_checksum_address("0x" + actor_id.split(":")[-1][2:])
