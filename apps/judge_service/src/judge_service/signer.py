from __future__ import annotations

import os
from dataclasses import dataclass

from eth_account import Account
from eth_utils import to_checksum_address
from verdict_protocol import sign_hash_eip191


@dataclass(slots=True)
class JudgeSigner:
    backend: str
    address: str | None
    can_sign: bool

    def sign_digest(self, digest_hex: str) -> str:
        raise NotImplementedError


class EnvJudgeSigner(JudgeSigner):
    def __init__(self, private_key: str | None) -> None:
        self._private_key = private_key
        address = None
        can_sign = False
        if private_key:
            address = to_checksum_address(Account.from_key(private_key).address)
            can_sign = True
        super().__init__(backend="env", address=address, can_sign=can_sign)

    def sign_digest(self, digest_hex: str) -> str:
        if not self._private_key:
            raise RuntimeError("env signer is not configured")
        return sign_hash_eip191(self._private_key, digest_hex)


class DeferredJudgeSigner(JudgeSigner):
    def __init__(self, backend: str) -> None:
        super().__init__(backend=backend, address=None, can_sign=False)

    def sign_digest(self, digest_hex: str) -> str:
        _ = digest_hex
        raise RuntimeError(f"{self.backend} signer backend is not configured in this repo")


def build_judge_signer() -> JudgeSigner:
    backend = os.environ.get("JUDGE_SIGNER_BACKEND", "env").strip().lower() or "env"
    if backend == "env":
        return EnvJudgeSigner(os.environ.get("JUDGE_PRIVATE_KEY") or None)
    if backend in {"kms", "hsm"}:
        return DeferredJudgeSigner(backend)
    return DeferredJudgeSigner(backend)
