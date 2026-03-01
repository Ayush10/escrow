from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ruleId: str
    metric: str
    operator: str
    value: str | int | float
    unit: str


class RemedyRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition: str
    action: str
    percent: float = Field(ge=0, le=100)


class ArbitrationClause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: Literal["1.0.0"] = "1.0.0"
    clauseId: str
    chainId: int = Field(ge=1)
    contractAddress: str
    agreementId: str
    serviceScope: str
    slaRules: list[Rule]
    abuseRules: list[Rule]
    disputeWindowSec: int = Field(ge=1)
    evidenceWindowSec: int = Field(ge=1)
    remedyRules: list[RemedyRule]
    judgeFeePercent: float = Field(ge=0, le=100)
    clauseHash: str


class EventType:
    REQUEST = "request"
    RESPONSE = "response"
    PAYMENT = "payment"
    SLA_CHECK = "sla_check"
    DISPUTE_FILED = "dispute_filed"


class EventReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: Literal["1.0.0"] = "1.0.0"
    receiptId: str
    chainId: int = Field(ge=1)
    contractAddress: str
    agreementId: str
    clauseHash: str
    sequence: int = Field(ge=0)
    eventType: Literal["request", "response", "payment", "sla_check", "dispute_filed"]
    timestamp: int = Field(ge=0)
    actorId: str
    counterpartyId: str
    requestId: str
    payloadHash: str
    prevHash: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    receiptHash: str
    signature: str

    @field_validator("actorId", "counterpartyId")
    @classmethod
    def validate_did(cls, value: str) -> str:
        if not value.startswith("did:8004:0x"):
            raise ValueError("actor DID must use did:8004:0x... format")
        if len(value) != len("did:8004:0x") + 40:
            raise ValueError("actor DID must contain a 40-hex address")
        return value


class Transfer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: str
    amount: str
    reason: str


class VerdictPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: Literal["1.0.0"] = "1.0.0"
    verdictId: str
    disputeId: str
    chainId: int = Field(ge=1)
    contractAddress: str
    agreementId: str
    clauseHash: str
    transfers: list[Transfer]
    judgeFee: str
    reasonCodes: list[str]
    evidenceReceiptIds: list[str]
    facts: dict[str, Any]
    confidence: float = Field(ge=0, le=1)
    flags: list[str]
    verdictHash: str
    judgeSignature: str
