from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from verdict_protocol import (
    ArbitrationClause,
    EventReceipt,
    compute_clause_hash,
    compute_receipt_hash,
    validate_schema,
    verify_receipt_chain,
)

from .chain_anchor import compute_anchor_root
from .server_state import ServerState, get_state

router = APIRouter()


class AnchorRequest(BaseModel):
    agreementId: str


def _logical_receipt_fields(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": receipt.get("schemaVersion"),
        "chainId": receipt.get("chainId"),
        "contractAddress": receipt.get("contractAddress"),
        "agreementId": receipt.get("agreementId"),
        "clauseHash": receipt.get("clauseHash"),
        "sequence": receipt.get("sequence"),
        "eventType": receipt.get("eventType"),
        "actorId": receipt.get("actorId"),
        "counterpartyId": receipt.get("counterpartyId"),
        "requestId": receipt.get("requestId"),
        "payloadHash": receipt.get("payloadHash"),
        "prevHash": receipt.get("prevHash"),
        "metadata": receipt.get("metadata", {}),
    }


def _same_logical_receipt(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return _logical_receipt_fields(left) == _logical_receipt_fields(right)


@router.post("/clauses")
def post_clause(payload: ArbitrationClause, state: ServerState = Depends(get_state)) -> dict[str, Any]:
    clause = payload.model_dump()
    errors = validate_schema("arbitration_clause.schema.json", clause)
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    computed = compute_clause_hash(clause)
    if clause["clauseHash"] != computed:
        raise HTTPException(status_code=400, detail=f"clauseHash mismatch expected={computed}")

    state.storage.store_clause(clause)
    return {"ok": True, "clauseId": clause["clauseId"], "clauseHash": clause["clauseHash"]}


@router.get("/clauses/{agreement_id}")
def get_clause(agreement_id: str, state: ServerState = Depends(get_state)) -> dict[str, Any]:
    clause = state.storage.get_clause_by_agreement(agreement_id)
    if not clause:
        raise HTTPException(status_code=404, detail="clause not found")
    return clause


@router.get("/clauses")
def list_clauses(
    limit: int = Query(default=200, ge=1, le=2000),
    state: ServerState = Depends(get_state),
) -> dict[str, Any]:
    items = state.storage.list_clauses(limit=limit)
    return {"count": len(items), "items": items}


@router.get("/agreements/{agreement_id}")
def get_agreement(agreement_id: str, state: ServerState = Depends(get_state)) -> dict[str, Any]:
    clause = state.storage.get_clause_by_agreement(agreement_id)
    if not clause:
        raise HTTPException(status_code=404, detail="clause not found")

    receipts = state.storage.list_receipts(agreement_id=agreement_id)
    anchor = state.storage.get_anchor(agreement_id)

    chain_ok = True
    chain_errors: list[str] = []
    if receipts:
        chain = verify_receipt_chain(receipts)
        chain_ok = chain.ok
        chain_errors = chain.errors

    expected_root = None
    root_match = None
    if anchor:
        expected_root = compute_anchor_root([r["receiptHash"] for r in receipts]) if receipts else "0x0"
        root_match = expected_root == anchor["rootHash"]

    return {
        "agreementId": agreement_id,
        "clause": clause,
        "receipts": receipts,
        "receiptCount": len(receipts),
        "anchor": anchor,
        "receiptChain": {
            "valid": chain_ok,
            "errors": chain_errors,
        },
        "root": {
            "expected": expected_root,
            "anchored": anchor["rootHash"] if anchor else None,
            "matched": root_match,
        },
    }


@router.get("/agreements/{agreement_id}/export")
def export_agreement(agreement_id: str, state: ServerState = Depends(get_state)) -> dict[str, Any]:
    """Return a complete evidence bundle suitable for audit or download."""
    clause = state.storage.get_clause_by_agreement(agreement_id)
    if not clause:
        raise HTTPException(status_code=404, detail="clause not found")

    receipts = state.storage.list_receipts(agreement_id=agreement_id)
    anchor = state.storage.get_anchor(agreement_id)

    chain_ok = True
    chain_errors: list[str] = []
    if receipts:
        chain = verify_receipt_chain(receipts)
        chain_ok = chain.ok
        chain_errors = chain.errors

    expected_root = None
    root_match = None
    if anchor:
        expected_root = compute_anchor_root([r["receiptHash"] for r in receipts]) if receipts else "0x0"
        root_match = expected_root == anchor["rootHash"]

    return {
        "schemaVersion": "1.0.0",
        "exportType": "evidence_bundle",
        "agreementId": agreement_id,
        "clause": clause,
        "receipts": receipts,
        "receiptCount": len(receipts),
        "anchor": anchor,
        "receiptChain": {
            "valid": chain_ok,
            "errors": chain_errors,
            "receiptHashes": [r["receiptHash"] for r in receipts],
        },
        "root": {
            "expected": expected_root,
            "anchored": anchor["rootHash"] if anchor else None,
            "matched": root_match,
        },
        "integrity": {
            "clauseHash": clause.get("clauseHash"),
            "clauseHashValid": clause.get("clauseHash") == compute_clause_hash(clause) if clause.get("clauseHash") else None,
            "chainValid": chain_ok,
            "rootAnchored": anchor is not None,
            "rootCommittedOnChain": bool(anchor and anchor.get("txHash")),
            "rootMatched": root_match,
        },
    }


@router.get("/agreements")
def list_agreements(
    limit: int = Query(default=200, ge=1, le=2000),
    state: ServerState = Depends(get_state),
) -> dict[str, Any]:
    clauses = state.storage.list_clauses(limit=limit)
    items: list[dict[str, Any]] = []
    for clause in clauses:
        agreement_id = clause["agreementId"]
        receipts = state.storage.list_receipts(agreement_id=agreement_id)
        anchor = state.storage.get_anchor(agreement_id)
        request_count = sum(1 for r in receipts if r.get("eventType") == "request")
        response_count = sum(1 for r in receipts if r.get("eventType") == "response")
        dispute_count = sum(1 for r in receipts if r.get("eventType") == "dispute_filed")
        actors = sorted({str(r.get("actorId", "")) for r in receipts if r.get("actorId")})
        items.append(
            {
                "agreementId": agreement_id,
                "clauseId": clause.get("clauseId"),
                "serviceScope": clause.get("serviceScope"),
                "clauseHash": clause.get("clauseHash"),
                "createdAt": clause.get("createdAt"),
                "receiptCount": len(receipts),
                "requestCount": request_count,
                "responseCount": response_count,
                "disputeReceiptCount": dispute_count,
                "actors": actors,
                "anchor": anchor,
            }
        )
    return {"count": len(items), "items": items}


@router.post("/receipts")
def post_receipt(payload: EventReceipt, state: ServerState = Depends(get_state)) -> dict[str, Any]:
    receipt = payload.model_dump()
    errors = validate_schema("event_receipt.schema.json", receipt)
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    computed = compute_receipt_hash(receipt)
    if receipt["receiptHash"] != computed:
        raise HTTPException(status_code=400, detail=f"receiptHash mismatch expected={computed}")

    existing_by_id = state.storage.get_receipt(receipt["receiptId"])
    if existing_by_id:
        if existing_by_id.get("receiptHash") == receipt["receiptHash"]:
            return {
                "ok": True,
                "receiptId": existing_by_id["receiptId"],
                "receiptHash": existing_by_id["receiptHash"],
                "idempotent": True,
            }
        raise HTTPException(status_code=409, detail="receipt_id_conflict")

    existing_at_sequence = state.storage.get_receipt_by_sequence(
        receipt["agreementId"],
        int(receipt["sequence"]),
    )
    if existing_at_sequence:
        if _same_logical_receipt(existing_at_sequence, receipt):
            return {
                "ok": True,
                "receiptId": existing_at_sequence["receiptId"],
                "receiptHash": existing_at_sequence["receiptHash"],
                "idempotent": True,
            }
        raise HTTPException(
            status_code=409,
            detail="receipt_sequence_conflict",
        )

    existing = state.storage.list_receipts(agreement_id=receipt["agreementId"])
    chain = verify_receipt_chain(existing + [receipt])
    if not chain.ok:
        raise HTTPException(status_code=400, detail=chain.errors)

    try:
        state.storage.store_receipt(receipt)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"ok": True, "receiptId": receipt["receiptId"], "receiptHash": receipt["receiptHash"]}


@router.get("/receipts")
def list_receipts(
    agreementId: str | None = Query(default=None),
    actorId: str | None = Query(default=None),
    state: ServerState = Depends(get_state),
) -> dict[str, Any]:
    receipts = state.storage.list_receipts(agreementId, actorId)
    return {"count": len(receipts), "items": receipts}


@router.get("/receipts/{receipt_id}")
def get_receipt(receipt_id: str, state: ServerState = Depends(get_state)) -> dict[str, Any]:
    receipt = state.storage.get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="receipt not found")
    return receipt


@router.post("/anchor")
def anchor_receipts(payload: AnchorRequest, state: ServerState = Depends(get_state)) -> dict[str, Any]:
    receipts = state.storage.list_receipts(agreement_id=payload.agreementId)
    if not receipts:
        raise HTTPException(status_code=404, detail="no receipts for agreement")

    receipt_hashes = [r["receiptHash"] for r in receipts]
    receipt_ids = [r["receiptId"] for r in receipts]
    root_hash = compute_anchor_root(receipt_hashes)
    existing_anchor = state.storage.get_anchor(payload.agreementId)

    if existing_anchor:
        if existing_anchor["rootHash"] == root_hash and existing_anchor["receiptIds"] == receipt_ids:
            return {
                "agreementId": payload.agreementId,
                "rootHash": existing_anchor["rootHash"],
                "txHash": existing_anchor["txHash"],
                "anchorMode": existing_anchor.get("anchorMode", "onchain"),
                "receiptIds": existing_anchor["receiptIds"],
                "idempotent": True,
            }
        raise HTTPException(
            status_code=409,
            detail={
                "error": "anchor_conflict",
                "agreementId": payload.agreementId,
                "existingRootHash": existing_anchor["rootHash"],
                "currentRootHash": root_hash,
            },
        )

    capabilities = state.escrow.capabilities()
    sanity = state.escrow.contract_sanity()
    tx_hash: str | None = None
    anchor_mode = "onchain"
    if sanity.get("deploymentMode") == "split" and not capabilities.get("commitEvidenceHash", False):
        anchor_mode = "offchain_bundle"
    else:
        tx = state.escrow.commit_evidence_hash(payload.agreementId, root_hash)
        tx_hash = tx.tx_hash
    state.storage.store_anchor(payload.agreementId, root_hash, tx_hash, receipt_ids)

    return {
        "agreementId": payload.agreementId,
        "rootHash": root_hash,
        "txHash": tx_hash,
        "anchorMode": anchor_mode,
        "receiptIds": receipt_ids,
    }


@router.get("/anchors")
def get_anchor(agreementId: str, state: ServerState = Depends(get_state)) -> dict[str, Any]:
    anchor = state.storage.get_anchor(agreementId)
    if not anchor:
        raise HTTPException(status_code=404, detail="anchor not found")
    return anchor


@router.get("/anchors/by-root/{root_hash}")
def get_anchor_by_root(root_hash: str, state: ServerState = Depends(get_state)) -> dict[str, Any]:
    anchor = state.storage.get_anchor_by_root(root_hash)
    if not anchor:
        raise HTTPException(status_code=404, detail="anchor not found")
    return anchor
