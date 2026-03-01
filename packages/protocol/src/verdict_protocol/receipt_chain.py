from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .hashing import compute_receipt_hash
from .signatures import did_to_address, verify_signature_eip191


@dataclass(slots=True)
class ReceiptChainResult:
    ok: bool
    errors: list[str]


def verify_receipt_chain(
    receipts: list[dict[str, Any]],
    *,
    expected_chain_id: int | None = None,
    expected_contract_address: str | None = None,
    expected_agreement_id: str | None = None,
    expected_clause_hash: str | None = None,
) -> ReceiptChainResult:
    errors: list[str] = []
    ordered = sorted(receipts, key=lambda r: r["sequence"])

    for idx, receipt in enumerate(ordered):
        seq = receipt["sequence"]
        if seq != idx:
            errors.append(f"sequence mismatch at index={idx}: got {seq}")

        if expected_chain_id is not None and receipt.get("chainId") != expected_chain_id:
            errors.append(f"receipt {receipt.get('receiptId')} has wrong chainId")
        if expected_contract_address and receipt.get("contractAddress") != expected_contract_address:
            errors.append(f"receipt {receipt.get('receiptId')} has wrong contractAddress")
        if expected_agreement_id and receipt.get("agreementId") != expected_agreement_id:
            errors.append(f"receipt {receipt.get('receiptId')} has wrong agreementId")
        if expected_clause_hash and receipt.get("clauseHash") != expected_clause_hash:
            errors.append(f"receipt {receipt.get('receiptId')} has wrong clauseHash")

        computed_hash = compute_receipt_hash(receipt)
        if computed_hash != receipt.get("receiptHash"):
            errors.append(f"receipt hash mismatch for {receipt.get('receiptId')}")

        if idx == 0:
            if receipt.get("prevHash") != "0x0":
                errors.append("first receipt prevHash must be 0x0")
        else:
            prev = ordered[idx - 1]
            if receipt.get("prevHash") != prev.get("receiptHash"):
                errors.append(f"prevHash mismatch for {receipt.get('receiptId')}")

        try:
            signer = did_to_address(receipt["actorId"])
            if not verify_signature_eip191(receipt["receiptHash"], receipt["signature"], signer):
                errors.append(f"signature mismatch for {receipt.get('receiptId')}")
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"signature verification failed for {receipt.get('receiptId')}: {exc}")

    return ReceiptChainResult(ok=not errors, errors=errors)
