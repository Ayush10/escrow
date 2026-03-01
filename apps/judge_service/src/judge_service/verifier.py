from __future__ import annotations

from typing import Any

from verdict_protocol import merkle_root_hash, verify_receipt_chain


def verify_evidence_bundle(
    *,
    receipts: list[dict[str, Any]],
    expected_root: str,
    chain_id: int,
    contract_address: str,
    agreement_id: str,
    clause_hash: str,
) -> tuple[bool, list[str]]:
    chain = verify_receipt_chain(
        receipts,
        expected_chain_id=chain_id,
        expected_contract_address=contract_address,
        expected_agreement_id=agreement_id,
        expected_clause_hash=clause_hash,
    )
    errors = list(chain.errors)

    computed_root = merkle_root_hash([r["receiptHash"] for r in sorted(receipts, key=lambda x: x["sequence"])])
    if computed_root != expected_root:
        errors.append(f"anchor root mismatch expected={expected_root} computed={computed_root}")

    return (not errors, errors)
