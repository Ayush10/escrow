from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from eth_account import Account
from verdict_protocol import (
    compute_clause_hash,
    compute_receipt_hash,
    hash_canonical,
    sign_hash_eip191,
)


@dataclass(slots=True)
class ActorIdentity:
    private_key: str
    address: str
    did: str


class ReceiptClient:
    def __init__(self, evidence_url: str) -> None:
        self.evidence_url = evidence_url.rstrip("/")

    @staticmethod
    def actor_from_key(private_key: str) -> ActorIdentity:
        account = Account.from_key(private_key)
        return ActorIdentity(
            private_key=private_key,
            address=account.address,
            did=f"did:8004:{account.address}",
        )

    def create_clause(
        self,
        *,
        agreement_id: str,
        chain_id: int,
        contract_address: str,
        dispute_window_sec: int = 30,
        evidence_window_sec: int = 30,
    ) -> dict[str, Any]:
        clause: dict[str, Any] = {
            "schemaVersion": "1.0.0",
            "clauseId": str(uuid.uuid4()),
            "chainId": chain_id,
            "contractAddress": contract_address,
            "agreementId": agreement_id,
            "serviceScope": "GET /api/data",
            "slaRules": [
                {
                    "ruleId": "sla-latency",
                    "metric": "latency_ms",
                    "operator": "<=",
                    "value": 3000,
                    "unit": "ms",
                }
            ],
            "abuseRules": [
                {
                    "ruleId": "abuse-rate",
                    "metric": "requests_per_minute",
                    "operator": "<=",
                    "value": 60,
                    "unit": "rpm",
                }
            ],
            "disputeWindowSec": dispute_window_sec,
            "evidenceWindowSec": evidence_window_sec,
            "remedyRules": [
                {"condition": "sla_breach", "action": "consumer_refund", "percent": 100}
            ],
            "judgeFeePercent": 5,
            "clauseHash": "",
        }
        clause["clauseHash"] = compute_clause_hash(clause)
        return clause

    def create_receipt(
        self,
        *,
        chain_id: int,
        contract_address: str,
        agreement_id: str,
        clause_hash: str,
        sequence: int,
        actor: ActorIdentity,
        counterparty: ActorIdentity,
        event_type: str,
        request_id: str,
        payload: dict[str, Any],
        prev_hash: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = metadata or {}
        receipt: dict[str, Any] = {
            "schemaVersion": "1.0.0",
            "receiptId": str(uuid.uuid4()),
            "chainId": chain_id,
            "contractAddress": contract_address,
            "agreementId": agreement_id,
            "clauseHash": clause_hash,
            "sequence": sequence,
            "eventType": event_type,
            "timestamp": int(time.time() * 1000),
            "actorId": actor.did,
            "counterpartyId": counterparty.did,
            "requestId": request_id,
            "payloadHash": hash_canonical(payload),
            "prevHash": prev_hash,
            "metadata": metadata,
            "receiptHash": "",
            "signature": "",
        }
        receipt["receiptHash"] = compute_receipt_hash(receipt)
        receipt["signature"] = sign_hash_eip191(actor.private_key, receipt["receiptHash"])
        return receipt

    def post_clause(self, clause: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=30) as client:
            resp = client.post(f"{self.evidence_url}/clauses", json=clause)
            resp.raise_for_status()
            return resp.json()

    def post_receipt(self, receipt: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=30) as client:
            resp = client.post(f"{self.evidence_url}/receipts", json=receipt)
            resp.raise_for_status()
            return resp.json()

    def anchor(self, agreement_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=60) as client:
            resp = client.post(f"{self.evidence_url}/anchor", json={"agreementId": agreement_id})
            resp.raise_for_status()
            return resp.json()


def env_urls() -> tuple[str, str]:
    return (
        os.environ.get("EVIDENCE_SERVICE_URL", "http://127.0.0.1:4001"),
        os.environ.get("PROVIDER_API_URL", "http://127.0.0.1:4000"),
    )
