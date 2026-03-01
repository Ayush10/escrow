from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any

import httpx
from eth_utils import to_checksum_address
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from verdict_protocol import EscrowClient, compute_verdict_hash, sign_hash_eip191

from .fact_extractor import extract_facts
from .llm_judge import LLMJudge
from .server_state import JudgeState
from .storage import JudgeStorage
from .submit_ruling import submit_ruling
from .telegram_notifier import send_telegram_notification
from .verifier import verify_evidence_bundle
from .watcher import DisputeEvent, DisputeWatcher


def _tier_name(tier: int) -> str:
    names = ["district", "appeals", "supreme"]
    if 0 <= tier < len(names):
        return names[tier]
    return "district"


def _hex_or_str(value: Any) -> str:
    if hasattr(value, "hex"):
        out = value.hex()
    else:
        out = str(value)
    if out.startswith("0x"):
        return out
    return "0x" + out


def _reason_line(code: str) -> str:
    if code == "sla_breach:latency":
        return "- SLA breach established: latency exceeded the allowed threshold."
    if code == "clause_violated:rate_limit":
        return "- Abuse rule violated: requests per minute exceeded contract limits."
    if code == "hash_mismatch":
        return "- Evidence integrity failure: receipt hashes did not match the anchored root."
    return f"- Rule finding: {code}"


def _deterministic_opinion(
    *,
    dispute_id: int,
    tier_name: str,
    plaintiff: str,
    defendant: str,
    plaintiff_evidence: str,
    defendant_evidence: str,
    winner: str,
    reason_codes: list[str],
    facts: dict[str, Any],
    errors: list[str] | None = None,
) -> str:
    winner_side = "PLAINTIFF" if winner.lower() == plaintiff.lower() else "DEFENDANT"
    loser = defendant if winner.lower() == plaintiff.lower() else plaintiff
    finding_lines = [_reason_line(code) for code in reason_codes] or ["- No rule violations were established."]
    integrity_lines = []
    if errors:
        integrity_lines.extend([f"- {msg}" for msg in errors])
    else:
        integrity_lines.append("- Receipt chain integrity verified against anchored evidence root.")
    if defendant_evidence.lower() in {"0x0", "0x" + "0" * 64}:
        integrity_lines.append("- Defendant evidence commitment is null; no counter-evidence was pre-committed.")

    return "\n".join(
        [
            f"AGENT COURT PROTOCOL — {tier_name.upper()} DIVISION",
            "",
            "JUDICIAL OPINION",
            "",
            f"Case No. {dispute_id}",
            f"{plaintiff} (Plaintiff) v. {defendant} (Defendant)",
            "",
            "I. PRELIMINARY MATTERS: EVIDENCE INTEGRITY",
            f"- Plaintiff committed evidence hash: {plaintiff_evidence}",
            f"- Defendant committed evidence hash: {defendant_evidence}",
            *integrity_lines,
            "",
            "II. FINDINGS OF FACT",
            f"- Request count: {facts.get('request_count', 0)}",
            f"- Response count: {facts.get('response_count', 0)}",
            f"- Observed latency (ms): {facts.get('latency_ms', 0)}",
            f"- Peak requests per minute: {facts.get('peak_requests_per_minute', 0)}",
            f"- Response format valid: {facts.get('response_format_ok', True)}",
            "",
            "III. APPLICATION OF SLA TERMS",
            *finding_lines,
            "",
            "IV. RULING",
            f"- Judgment for the {winner_side}: {winner}.",
            f"- Losing party: {loser}.",
            "- Ruling is issued under deterministic SLA checks and evidence integrity constraints.",
            "",
            "IT IS SO ORDERED.",
            "The Honorable Judge, Agent Court Protocol",
        ]
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Judge Service", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
        escrow = app.state.judge_state.escrow
        sanity = escrow.contract_sanity()
        status = "ok"
        if (not sanity["contractHasCode"]) and (not sanity["dryRun"]):
            status = "degraded"
        return {
            "status": status,
            "capabilities": escrow.capabilities(),
            "escrow": sanity,
        }

    @app.get("/api/health")
    def api_health() -> dict[str, Any]:
        # Compatibility alias for older dashboard and external watchers.
        return health()

    @app.get("/verdicts")
    def verdicts() -> dict[str, Any]:
        items = app.state.judge_state.storage.list_verdicts()
        return {"count": len(items), "items": items}

    @app.get("/api/verdicts")
    def api_verdicts() -> dict[str, Any]:
        # Compatibility alias for older frontend API shape.
        return verdicts()

    @app.get("/verdicts/{dispute_id}")
    def get_verdict(dispute_id: int) -> dict[str, Any]:
        verdict = app.state.judge_state.storage.get_verdict_by_dispute(dispute_id)
        if not verdict:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="verdict not found")
        return verdict

    @app.get("/api/verdicts/{dispute_id}")
    def api_get_verdict(dispute_id: int) -> dict[str, Any]:
        # Compatibility alias for older frontend API shape.
        return get_verdict(dispute_id)

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

    transaction_id: int | None = None
    judge_fee = 0
    plaintiff_evidence = "0x0"
    defendant_evidence = "0x0"

    # Handle both old struct (plaintiff at 0) and new struct (transactionId at 0)
    if len(dispute) >= 10:
        # New AgentCourt: (transactionId, plaintiff, defendant, stake, judgeFee, tier, pEvidence, dEvidence, resolved, winner)
        transaction_id = int(dispute[0])
        plaintiff = to_checksum_address(dispute[1])
        defendant = to_checksum_address(dispute[2])
        plaintiff_stake = int(dispute[3])
        defendant_stake = int(dispute[3])  # same stake
        judge_fee = int(dispute[4])
        dispute_tier = int(dispute[5])
        plaintiff_evidence = _hex_or_str(dispute[6])
        defendant_evidence = _hex_or_str(dispute[7])
        root_hash = plaintiff_evidence
    else:
        # Legacy: (plaintiff, defendant, plaintiffStake, defendantStake, evidence...)
        plaintiff = to_checksum_address(dispute[0])
        defendant = to_checksum_address(dispute[1])
        plaintiff_stake = int(dispute[2])
        defendant_stake = int(dispute[3])
        dispute_tier = 0
        plaintiff_evidence = _hex_or_str(dispute[4])
        root_hash = plaintiff_evidence
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

    if not full_opinion:
        full_opinion = _deterministic_opinion(
            dispute_id=event.dispute_id,
            tier_name=_tier_name(dispute_tier),
            plaintiff=plaintiff,
            defendant=defendant,
            plaintiff_evidence=plaintiff_evidence,
            defendant_evidence=defendant_evidence,
            winner=winner,
            reason_codes=reason_codes,
            facts=facts,
            errors=errors if not ok else None,
        )

    loser = defendant if winner == plaintiff else plaintiff

    verdict = {
        "schemaVersion": "1.0.0",
        "verdictId": str(uuid.uuid4()),
        "disputeId": str(event.dispute_id),
        "transactionId": str(transaction_id) if transaction_id is not None else None,
        "chainId": int(os.environ.get("GOAT_CHAIN_ID", "48816")),
        "contractAddress": os.environ.get("ESCROW_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"),
        "agreementId": agreement_id,
        "clauseHash": clause["clauseHash"],
        "plaintiff": plaintiff,
        "defendant": defendant,
        "plaintiffEvidence": plaintiff_evidence,
        "defendantEvidence": defendant_evidence,
        "stake": str(plaintiff_stake),
        "defendantStake": str(defendant_stake),
        "tier": dispute_tier,
        "courtTier": _tier_name(dispute_tier),
        "transfers": [
            {"to": winner, "amount": str(plaintiff_stake + defendant_stake), "reason": "dispute_resolution"}
        ],
        "judgeFee": str(judge_fee),
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
