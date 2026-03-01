from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any

import httpx
from eth_utils import to_checksum_address
from fastapi import FastAPI
from verdict_protocol import EscrowClient, compute_verdict_hash, sign_hash_eip191

from .fact_extractor import extract_facts
from .llm_judge import LLMJudge
from .server_state import JudgeState
from .storage import JudgeStorage
from .submit_ruling import submit_ruling
from .telegram_notifier import send_telegram_notification
from .verifier import verify_evidence_bundle
from .watcher import DisputeEvent, DisputeWatcher


def create_app() -> FastAPI:
    app = FastAPI(title="Judge Service", version="0.1.0")

    escrow = EscrowClient(
        rpc_url=os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network"),
        chain_id=int(os.environ.get("GOAT_CHAIN_ID", "48816")),
        contract_address=os.environ.get("ESCROW_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"),
        private_key=os.environ.get("JUDGE_PRIVATE_KEY") or None,
        dry_run=os.environ.get("ESCROW_DRY_RUN", "0") == "1",
    )
    watcher = DisputeWatcher(escrow)
    storage = JudgeStorage(os.environ.get("SQLITE_PATH", "./data/verdict.db"))
    llm = LLMJudge()

    app.state.judge_state = JudgeState(
        storage=storage,
        escrow=escrow,
        watcher=watcher,
        llm=llm,
        evidence_url=os.environ.get("EVIDENCE_SERVICE_URL", "http://127.0.0.1:4001"),
    )

    @app.on_event("startup")
    async def startup() -> None:
        app.state.watch_task = asyncio.create_task(_watch_loop(app.state.judge_state))

    @app.on_event("shutdown")
    async def shutdown() -> None:
        task = getattr(app.state, "watch_task", None)
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "capabilities": app.state.judge_state.escrow.capabilities()}

    @app.get("/verdicts")
    def verdicts() -> dict[str, Any]:
        items = app.state.judge_state.storage.list_verdicts()
        return {"count": len(items), "items": items}

    return app


async def _watch_loop(state: JudgeState) -> None:
    poll_sec = float(os.environ.get("JUDGE_POLL_SEC", "5"))
    from_block = state.storage.get_cursor("judge.from_block", 0)

    while True:
        try:
            events, next_block = state.watcher.poll(from_block=from_block)
            for event in events:
                if state.storage.is_processed(event.dispute_id):
                    continue
                await _handle_dispute(state, event)
            from_block = next_block
            state.storage.set_cursor("judge.from_block", from_block)
        except Exception:
            pass

        await asyncio.sleep(poll_sec)


async def _handle_dispute(state: JudgeState, event: DisputeEvent) -> None:
    dispute = state.escrow.get_dispute(event.dispute_id)
    if dispute is None:
        return

    # Handle both old struct (plaintiff at 0) and new struct (transactionId at 0)
    if len(dispute) >= 10:
        # New AgentCourt: (transactionId, plaintiff, defendant, stake, judgeFee, tier, pEvidence, dEvidence, resolved, winner)
        plaintiff = to_checksum_address(dispute[1])
        defendant = to_checksum_address(dispute[2])
        plaintiff_stake = int(dispute[3])
        defendant_stake = int(dispute[3])  # same stake
        dispute_tier = int(dispute[5])
        root_hash = dispute[6].hex() if hasattr(dispute[6], "hex") else str(dispute[6])
    else:
        # Legacy: (plaintiff, defendant, plaintiffStake, defendantStake, evidence...)
        plaintiff = to_checksum_address(dispute[0])
        defendant = to_checksum_address(dispute[1])
        plaintiff_stake = int(dispute[2])
        defendant_stake = int(dispute[3])
        dispute_tier = 0
        root_hash = dispute[4].hex() if hasattr(dispute[4], "hex") else str(dispute[4])
    if not root_hash.startswith("0x"):
        root_hash = "0x" + root_hash

    evidence = await _get_evidence_bundle(state.evidence_url, root_hash)
    if evidence is None:
        return

    agreement_id = evidence["agreementId"]
    clause = evidence["clause"]
    receipts = evidence["receipts"]

    ok, errors = verify_evidence_bundle(
        receipts=receipts,
        expected_root=root_hash,
        chain_id=clause["chainId"],
        contract_address=clause["contractAddress"],
        agreement_id=agreement_id,
        clause_hash=clause["clauseHash"],
    )

    flags: list[str] = []
    reason_codes: list[str] = []
    confidence = 0.95
    full_opinion = ""

    if not ok:
        reason_codes.append("hash_mismatch")
        flags.extend(errors)
        winner = defendant
        confidence = 0.99
        facts = {"integrity_ok": False, "errors": errors}
    else:
        facts, reason_codes, logical_winner = extract_facts(clause, receipts)
        if logical_winner == "plaintiff":
            winner = plaintiff
        elif logical_winner == "defendant":
            winner = defendant
        else:
            llm_codes, llm_winner, llm_confidence, full_opinion = state.llm.judge(
                clause=clause,
                facts=facts,
                evidence_summary={"receiptCount": len(receipts), "reasonCodes": reason_codes},
                tier=dispute_tier,
            )
            reason_codes.extend(llm_codes)
            confidence = llm_confidence
            if llm_winner == "plaintiff":
                winner = plaintiff
            elif llm_winner == "defendant":
                winner = defendant
            else:
                winner = defendant

    loser = defendant if winner == plaintiff else plaintiff

    verdict = {
        "schemaVersion": "1.0.0",
        "verdictId": str(uuid.uuid4()),
        "disputeId": str(event.dispute_id),
        "chainId": int(os.environ.get("GOAT_CHAIN_ID", "48816")),
        "contractAddress": os.environ.get("ESCROW_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"),
        "agreementId": agreement_id,
        "clauseHash": clause["clauseHash"],
        "transfers": [
            {"to": winner, "amount": str(plaintiff_stake + defendant_stake), "reason": "dispute_resolution"}
        ],
        "judgeFee": "0",
        "reasonCodes": reason_codes,
        "evidenceReceiptIds": [r["receiptId"] for r in receipts],
        "facts": facts,
        "confidence": confidence,
        "flags": flags,
        "verdictHash": "",
        "judgeSignature": "",
        "winner": winner,
        "loser": loser,
        "fullOpinion": full_opinion,
    }
    verdict["verdictHash"] = compute_verdict_hash(verdict)

    judge_key = os.environ.get("JUDGE_PRIVATE_KEY", "")
    if judge_key:
        verdict["judgeSignature"] = sign_hash_eip191(judge_key, verdict["verdictHash"])

    status = "manual_review"
    tx_hash = None

    if confidence >= 0.7:
        authorized = False
        expected_judge = state.escrow.judge_address()
        if expected_judge and state.escrow.account:
            authorized = to_checksum_address(state.escrow.account.address) == expected_judge

        if authorized or os.environ.get("ESCROW_DRY_RUN", "0") == "1":
            submit = submit_ruling(state.escrow, event.dispute_id, verdict)
            tx_hash = submit["txHash"]
            status = "submitted"

    if status == "manual_review":
        verdict["flags"].append("needs_manual_review")

    verdict["submitTxHash"] = tx_hash
    verdict["processedAtMs"] = int(time.time() * 1000)

    state.storage.store_verdict(verdict, status)

    # Push verdict to public verdict API
    verdict_api = os.environ.get("VERDICT_API_URL", "")
    if verdict_api:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(f"{verdict_api}/api/verdicts", json=verdict)
        except Exception:
            pass  # best-effort push

    send_telegram_notification(
        f"dispute={event.dispute_id} winner={winner} reasons={','.join(reason_codes)} confidence={confidence:.2f} tx={tx_hash}"
    )


async def _get_evidence_bundle(evidence_url: str, root_hash: str) -> dict[str, Any] | None:
    async with httpx.AsyncClient(timeout=30) as client:
        anchor_resp = await client.get(f"{evidence_url}/anchors/by-root/{root_hash}")
        if anchor_resp.status_code >= 400:
            return None
        anchor = anchor_resp.json()

        agreement_id = anchor["agreementId"]
        clause_resp = await client.get(f"{evidence_url}/clauses/{agreement_id}")
        receipts_resp = await client.get(f"{evidence_url}/receipts", params={"agreementId": agreement_id})

        if clause_resp.status_code >= 400 or receipts_resp.status_code >= 400:
            return None

        return {
            "agreementId": agreement_id,
            "anchor": anchor,
            "clause": clause_resp.json(),
            "receipts": receipts_resp.json().get("items", []),
        }


import contextlib

app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("judge_service.server:app", host="0.0.0.0", port=4002, reload=False)


if __name__ == "__main__":
    main()
