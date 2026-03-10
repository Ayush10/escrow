from __future__ import annotations

from typing import Any

from verdict_protocol import compute_verdict_hash, validate_schema

from .signer import JudgeSigner

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def finalize_verdict_package(
    verdict: dict[str, Any],
    signer: JudgeSigner,
    *,
    judge_address: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    package = dict(verdict)
    package["judgeAddress"] = judge_address or signer.address or ZERO_ADDRESS
    package["judgeSignerBackend"] = signer.backend
    package["verdictHash"] = compute_verdict_hash(package)

    errors: list[str] = []
    if signer.can_sign:
        package["judgeSignature"] = signer.sign_digest(package["verdictHash"])
        errors.extend(validate_schema("verdict_package.schema.json", package))
    else:
        package["judgeSignature"] = ""
        errors.append(f"judge signer backend '{signer.backend}' cannot sign")

    return package, errors
