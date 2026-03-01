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


@router.post("/receipts")
def post_receipt(payload: EventReceipt, state: ServerState = Depends(get_state)) -> dict[str, Any]:
    receipt = payload.model_dump()
    errors = validate_schema("event_receipt.schema.json", receipt)
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    computed = compute_receipt_hash(receipt)
    if receipt["receiptHash"] != computed:
        raise HTTPException(status_code=400, detail=f"receiptHash mismatch expected={computed}")

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

    tx = state.escrow.commit_evidence_hash(payload.agreementId, root_hash)
    state.storage.store_anchor(payload.agreementId, root_hash, tx.tx_hash, receipt_ids)

    return {
        "agreementId": payload.agreementId,
        "rootHash": root_hash,
        "txHash": tx.tx_hash,
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
