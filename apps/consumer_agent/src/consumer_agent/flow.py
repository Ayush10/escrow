from __future__ import annotations

import os
import time
import uuid
from collections.abc import Callable
from typing import Any

from .client_x402 import X402Client
from .escrow_client import build_client
from .receipt_client import ReceiptClient


ProgressCallback = Callable[[dict[str, Any]], None]


def _runtime_contract_address() -> str:
    if os.environ.get("ESCROW_CONTRACT_MODE", "").lower() == "split":
        return os.environ.get("ESCROW_COURT_ADDRESS", "0x0000000000000000000000000000000000000000")
    return os.environ.get("ESCROW_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000")


def _emit(callback: ProgressCallback | None, event: dict[str, Any]) -> None:
    if callback is None:
        return
    callback(event)


def _step_start(
    emit: ProgressCallback | None, step_id: str, label: str, message: str = ""
) -> None:
    _emit(
        emit,
        {
            "type": "step.started",
            "stepId": step_id,
            "label": label,
            "status": "running",
            "message": message,
        },
    )


def _step_done(
    emit: ProgressCallback | None,
    step_id: str,
    label: str,
    message: str = "",
    artifacts: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "step.updated",
        "stepId": step_id,
        "label": label,
        "status": "done",
        "message": message,
    }
    if artifacts:
        payload["artifacts"] = artifacts
    _emit(emit, payload)


def _maybe_open_split_contract(
    *,
    emit: ProgressCallback | None,
    rc: ReceiptClient,
    agreement_id: str,
    clause_hash: str,
    provider_actor,
    consumer_actor,
    provider_escrow,
    consumer_escrow,
    consideration: int,
) -> dict[str, Any] | None:
    if provider_escrow.deployment_mode != "split":
        return None

    judge_key = os.environ.get("JUDGE_PRIVATE_KEY", "")
    if not judge_key:
        raise RuntimeError("JUDGE_PRIVATE_KEY is required in split contract mode")
    judge_actor = rc.actor_from_key(judge_key)

    _step_start(emit, "open_contract", "Open Court contract", "Proposing split court agreement")
    propose_tx = provider_escrow.create_agreement(
        agreement_id,
        principal=provider_actor.address,
        client=consumer_actor.address,
        judge=judge_actor.address,
        consideration=consideration,
        terms_hash=clause_hash,
    )
    contract_id = int((propose_tx.extra or {}).get("contractId", 0))
    _step_done(
        emit,
        "open_contract",
        "Open Court contract",
        "Court contract proposed",
        {"contractId": contract_id, "txHash": propose_tx.tx_hash, "judge": judge_actor.address},
    )

    _step_start(emit, "accept_contract", "Accept Court contract", "Counterparty accepts split court agreement")
    accept_tx = consumer_escrow.accept_agreement(contract_id)
    _step_done(
        emit,
        "accept_contract",
        "Accept Court contract",
        "Court contract active",
        {"contractId": contract_id, "txHash": accept_tx.tx_hash},
    )

    return {
        "contractId": contract_id,
        "judge": judge_actor.address,
        "proposeTx": propose_tx.tx_hash,
        "acceptTx": accept_tx.tx_hash,
    }


def run_happy_flow(*, emit: ProgressCallback | None = None, agreement_window_sec: int = 30) -> dict[str, Any]:
    evidence_url = os.environ.get("EVIDENCE_SERVICE_URL", "http://127.0.0.1:4001")
    provider_url = os.environ.get("PROVIDER_API_URL", "http://127.0.0.1:4000")

    provider_key = os.environ.get("PROVIDER_PRIVATE_KEY", "")
    consumer_key = os.environ.get("CONSUMER_PRIVATE_KEY", "")
    if not provider_key or not consumer_key:
        raise RuntimeError("PROVIDER_PRIVATE_KEY and CONSUMER_PRIVATE_KEY are required")

    rc = ReceiptClient(evidence_url)
    provider_actor = rc.actor_from_key(provider_key)
    consumer_actor = rc.actor_from_key(consumer_key)

    _step_done(
        emit,
        "agent_init",
        "Initialize agents and wallets",
        "Loaded provider and consumer identities from env",
    )

    agreement_id = str(uuid.uuid4())
    chain_id = int(os.environ.get("GOAT_CHAIN_ID", "48816"))
    contract_addr = _runtime_contract_address()

    _step_start(emit, "clause_created", "Create arbitration clause", "Preparing clause fields")
    clause = rc.create_clause(
        agreement_id=agreement_id,
        chain_id=chain_id,
        contract_address=contract_addr,
        dispute_window_sec=agreement_window_sec,
        evidence_window_sec=agreement_window_sec,
    )
    rc.post_clause(clause)
    _step_done(
        emit,
        "clause_created",
        "Create arbitration clause",
        "Clause stored in evidence service",
        {"agreementId": agreement_id, "clauseId": clause["clauseId"]},
    )

    provider_escrow = build_client(provider_key)
    consumer_escrow = build_client(consumer_key)
    escrow_amount = 10**15

    _step_start(emit, "deposit_pool", "Provider deposits escrow pool", "Submitting deposit transaction")
    deposit_tx = provider_escrow.deposit_pool(escrow_amount)
    _step_done(
        emit,
        "deposit_pool",
        "Provider deposits escrow pool",
        "Pool deposit complete",
        {"txHash": deposit_tx.tx_hash, "contractAddress": contract_addr},
    )

    _step_start(emit, "post_bond", "Consumer posts bond", "Submitting bond on GOAT")
    bond_tx = consumer_escrow.post_bond(agreement_id, escrow_amount)
    _step_done(
        emit,
        "post_bond",
        "Consumer posts bond",
        "Bond transaction complete",
        {"txHash": bond_tx.tx_hash, "agreementId": agreement_id},
    )

    split_contract = _maybe_open_split_contract(
        emit=emit,
        rc=rc,
        agreement_id=agreement_id,
        clause_hash=clause["clauseHash"],
        provider_actor=provider_actor,
        consumer_actor=consumer_actor,
        provider_escrow=provider_escrow,
        consumer_escrow=consumer_escrow,
        consideration=escrow_amount,
    )

    _step_start(emit, "provider_call", "Provider API call", "Requesting /api/data with x402 payment")
    x402 = X402Client(consumer_key)
    request_id = str(uuid.uuid4())

    req_payload = {"path": "/api/data", "requestId": request_id}
    req_receipt = rc.create_receipt(
        chain_id=chain_id,
        contract_address=contract_addr,
        agreement_id=agreement_id,
        clause_hash=clause["clauseHash"],
        sequence=0,
        actor=consumer_actor,
        counterparty=provider_actor,
        event_type="request",
        request_id=request_id,
        payload=req_payload,
        prev_hash="0x0",
    )
    rc.post_receipt(req_receipt)
    _step_done(
        emit,
        "provider_call",
        "Consumer request receipt",
        "Request receipt recorded",
        {"receiptId": req_receipt["receiptId"], "actorId": req_receipt["actorId"]},
    )

    response = x402.get(f"{provider_url}/api/data")

    res_receipt = rc.create_receipt(
        chain_id=chain_id,
        contract_address=contract_addr,
        agreement_id=agreement_id,
        clause_hash=clause["clauseHash"],
        sequence=1,
        actor=provider_actor,
        counterparty=consumer_actor,
        event_type="response",
        request_id=request_id,
        payload=response.payload,
        prev_hash=req_receipt["receiptHash"],
        metadata={
            "status_code": response.status_code,
            "evidence_hash": response.headers.get("x-evidence-hash", ""),
        },
    )
    rc.post_receipt(res_receipt)
    _step_done(
        emit,
        "provider_call",
        "Provider response receipt",
        "Response receipt recorded",
        {"receiptId": res_receipt["receiptId"], "statusCode": response.status_code},
    )

    _step_start(emit, "payment_receipt", "Record payment event", "Signing x402 payment evidence")
    payment_receipt = rc.create_receipt(
        chain_id=chain_id,
        contract_address=contract_addr,
        agreement_id=agreement_id,
        clause_hash=clause["clauseHash"],
        sequence=2,
        actor=consumer_actor,
        counterparty=provider_actor,
        event_type="payment",
        request_id=request_id,
        payload={"network": os.environ.get("X402_NETWORK", "eip155:84532")},
        prev_hash=res_receipt["receiptHash"],
        metadata={"x402_payment_reference": response.payment_reference},
    )
    rc.post_receipt(payment_receipt)
    _step_done(
        emit,
        "payment_receipt",
        "Record payment event",
        "Payment receipt recorded",
        {"receiptId": payment_receipt["receiptId"], "paymentReference": response.payment_reference},
    )

    _step_start(emit, "anchor", "Anchor evidence root", "Committing evidence hash on GOAT")
    anchor = rc.anchor(agreement_id)
    _step_done(
        emit,
        "anchor",
        "Anchor evidence root",
        "Merkle root committed on chain",
        {
            "agreementId": agreement_id,
            "rootHash": anchor["rootHash"],
            "txHash": anchor.get("txHash"),
        },
    )

    completion_tx = None
    if split_contract is not None:
        _step_start(emit, "complete_contract", "Complete Court contract", "Consumer releases split court settlement")
        completion_tx = consumer_escrow.complete_agreement(split_contract["contractId"])
        _step_done(
            emit,
            "complete_contract",
            "Complete Court contract",
            "Split court contract settled",
            {"contractId": split_contract["contractId"], "txHash": completion_tx.tx_hash},
        )
    else:
        _step_start(emit, "dispute_window_wait", "Wait dispute window", f"Waiting {agreement_window_sec}s")
        time.sleep(agreement_window_sec)
        _step_done(emit, "dispute_window_wait", "Wait dispute window", "Dispute window elapsed")

    return {
        "mode": "happy",
        "agreementId": agreement_id,
        "depositTx": deposit_tx.tx_hash,
        "bondTx": bond_tx.tx_hash,
        "contractId": split_contract["contractId"] if split_contract else None,
        "proposeTx": split_contract["proposeTx"] if split_contract else None,
        "acceptTx": split_contract["acceptTx"] if split_contract else None,
        "completionTx": completion_tx.tx_hash if completion_tx else None,
        "receiptIds": [
            req_receipt["receiptId"],
            res_receipt["receiptId"],
            payment_receipt["receiptId"],
        ],
        "anchor": anchor,
        "x402PaymentReference": response.payment_reference,
    }


def run_dispute_flow(
    *, emit: ProgressCallback | None = None, agreement_window_sec: int = 30
) -> dict[str, Any]:
    evidence_url = os.environ.get("EVIDENCE_SERVICE_URL", "http://127.0.0.1:4001")
    provider_url = os.environ.get("PROVIDER_API_URL", "http://127.0.0.1:4000")

    provider_key = os.environ.get("PROVIDER_PRIVATE_KEY", "")
    consumer_key = os.environ.get("CONSUMER_PRIVATE_KEY", "")
    if not provider_key or not consumer_key:
        raise RuntimeError("PROVIDER_PRIVATE_KEY and CONSUMER_PRIVATE_KEY are required")

    rc = ReceiptClient(evidence_url)
    provider_actor = rc.actor_from_key(provider_key)
    consumer_actor = rc.actor_from_key(consumer_key)

    _step_done(
        emit,
        "agent_init",
        "Initialize agents and wallets",
        "Loaded provider and consumer identities from env",
    )

    agreement_id = str(uuid.uuid4())
    chain_id = int(os.environ.get("GOAT_CHAIN_ID", "48816"))
    contract_addr = _runtime_contract_address()

    _step_start(emit, "clause_created", "Create arbitration clause", "Preparing clause fields")
    clause = rc.create_clause(
        agreement_id=agreement_id,
        chain_id=chain_id,
        contract_address=contract_addr,
        dispute_window_sec=agreement_window_sec,
        evidence_window_sec=agreement_window_sec,
    )
    rc.post_clause(clause)
    _step_done(
        emit,
        "clause_created",
        "Create arbitration clause",
        "Clause stored for dispute path",
        {"agreementId": agreement_id, "clauseId": clause["clauseId"]},
    )

    provider_escrow = build_client(provider_key)
    consumer_escrow = build_client(consumer_key)
    escrow_amount = 10**15

    _step_start(emit, "deposit_pool", "Provider deposits escrow pool", "Submitting deposit transaction")
    deposit_tx = provider_escrow.deposit_pool(escrow_amount)
    _step_done(
        emit,
        "deposit_pool",
        "Provider deposits escrow pool",
        "Pool deposit complete",
        {"txHash": deposit_tx.tx_hash},
    )

    _step_start(emit, "post_bond", "Consumer posts bond", "Submitting bond on GOAT")
    bond_tx = consumer_escrow.post_bond(agreement_id, escrow_amount)
    _step_done(
        emit,
        "post_bond",
        "Consumer posts bond",
        "Bond transaction complete",
        {"txHash": bond_tx.tx_hash},
    )

    split_contract = _maybe_open_split_contract(
        emit=emit,
        rc=rc,
        agreement_id=agreement_id,
        clause_hash=clause["clauseHash"],
        provider_actor=provider_actor,
        consumer_actor=consumer_actor,
        provider_escrow=provider_escrow,
        consumer_escrow=consumer_escrow,
        consideration=escrow_amount,
    )

    x402 = X402Client(consumer_key)
    request_id = str(uuid.uuid4())

    _step_start(
        emit,
        "provider_call",
        "Provider API call (bad path)",
        "Requesting /api/data?bad=true",
    )
    req_receipt = rc.create_receipt(
        chain_id=chain_id,
        contract_address=contract_addr,
        agreement_id=agreement_id,
        clause_hash=clause["clauseHash"],
        sequence=0,
        actor=consumer_actor,
        counterparty=provider_actor,
        event_type="request",
        request_id=request_id,
        payload={"path": "/api/data?bad=true", "requestId": request_id},
        prev_hash="0x0",
    )
    rc.post_receipt(req_receipt)
    _step_done(
        emit,
        "provider_call",
        "Consumer request receipt",
        "Request recorded for bad path",
        {"receiptId": req_receipt["receiptId"]},
    )

    response = x402.get(f"{provider_url}/api/data?bad=true")

    res_receipt = rc.create_receipt(
        chain_id=chain_id,
        contract_address=contract_addr,
        agreement_id=agreement_id,
        clause_hash=clause["clauseHash"],
        sequence=1,
        actor=provider_actor,
        counterparty=consumer_actor,
        event_type="response",
        request_id=request_id,
        payload=response.payload,
        prev_hash=req_receipt["receiptHash"],
        metadata={
            "status_code": response.status_code,
            "evidence_hash": response.headers.get("x-evidence-hash", ""),
            "bad": True,
        },
    )
    rc.post_receipt(res_receipt)

    sla_receipt = rc.create_receipt(
        chain_id=chain_id,
        contract_address=contract_addr,
        agreement_id=agreement_id,
        clause_hash=clause["clauseHash"],
        sequence=2,
        actor=consumer_actor,
        counterparty=provider_actor,
        event_type="sla_check",
        request_id=request_id,
        payload={"latency_ms": 3500, "response_ok": False},
        prev_hash=res_receipt["receiptHash"],
        metadata={"violation": "sla_breach:latency"},
    )
    rc.post_receipt(sla_receipt)
    _step_done(
        emit,
        "provider_call",
        "Provider bad response receipts",
        "Request, response, and SLA-check receipts recorded",
        {
            "requestReceiptId": req_receipt["receiptId"],
            "responseReceiptId": res_receipt["receiptId"],
            "slaReceiptId": sla_receipt["receiptId"],
        },
    )

    _step_start(emit, "anchor", "Anchor evidence root", "Committing evidence hash on GOAT")
    anchor = rc.anchor(agreement_id)
    _step_done(
        emit,
        "anchor",
        "Anchor evidence root",
        "Merkle root committed on chain",
        {"rootHash": anchor["rootHash"], "txHash": anchor.get("txHash")},
    )

    _step_start(emit, "file_dispute", "File dispute", "Submitting dispute transaction")
    dispute_tx = consumer_escrow.file_dispute(
        agreement_id,
        tx_id=split_contract["contractId"] if split_contract else None,
        defendant=provider_actor.address,
        stake=escrow_amount,
        plaintiff_evidence=anchor["rootHash"],
    )
    _step_done(
        emit,
        "file_dispute",
        "File dispute",
        "Dispute filed on-chain",
        {"txHash": dispute_tx.tx_hash},
    )

    return {
        "mode": "dispute",
        "agreementId": agreement_id,
        "depositTx": deposit_tx.tx_hash,
        "bondTx": bond_tx.tx_hash,
        "contractId": split_contract["contractId"] if split_contract else None,
        "proposeTx": split_contract["proposeTx"] if split_contract else None,
        "acceptTx": split_contract["acceptTx"] if split_contract else None,
        "disputeTx": dispute_tx.tx_hash,
        "disputeId": (
            str(dispute_tx.extra.get("disputeId"))
            if dispute_tx.extra and dispute_tx.extra.get("disputeId") is not None
            else None
        ),
        "receiptIds": [req_receipt["receiptId"], res_receipt["receiptId"], sla_receipt["receiptId"]],
        "anchor": anchor,
        "x402PaymentReference": response.payment_reference,
    }
