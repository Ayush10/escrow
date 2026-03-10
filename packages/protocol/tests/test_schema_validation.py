from verdict_protocol import validate_schema


def test_schema_validation_pass_and_fail() -> None:
    good = {
        "schemaVersion": "1.0.0",
        "clauseId": "c1",
        "chainId": 48816,
        "contractAddress": "0x" + "1" * 40,
        "agreementId": "a1",
        "serviceScope": "GET /api/data",
        "slaRules": [],
        "abuseRules": [],
        "disputeWindowSec": 30,
        "evidenceWindowSec": 30,
        "remedyRules": [],
        "judgeFeePercent": 5,
        "clauseHash": "0x" + "2" * 64,
    }

    assert validate_schema("arbitration_clause.schema.json", good) == []

    bad = dict(good)
    bad.pop("agreementId")
    assert validate_schema("arbitration_clause.schema.json", bad)


def test_verdict_package_schema_validation_passes_for_signed_package() -> None:
    verdict = {
        "schemaVersion": "1.0.0",
        "verdictId": "v1",
        "disputeId": "7",
        "transactionId": "55",
        "disputeTxHash": "0x" + "a" * 64,
        "chainId": 48816,
        "contractAddress": "0x" + "1" * 40,
        "agreementId": "agreement-1",
        "clauseHash": "0x" + "2" * 64,
        "plaintiff": "0x" + "3" * 40,
        "defendant": "0x" + "4" * 40,
        "plaintiffEvidence": "0x" + "5" * 64,
        "defendantEvidence": "0x0",
        "stake": "100",
        "defendantStake": "100",
        "tier": 0,
        "courtTier": "district",
        "transfers": [{"to": "0x" + "3" * 40, "amount": "200", "reason": "dispute_resolution"}],
        "judgeFee": "5",
        "reasonCodes": ["sla_breach:latency"],
        "evidenceReceiptIds": ["r1", "r2"],
        "facts": {"latency_ms": 4000},
        "confidence": 0.95,
        "flags": [],
        "verdictHash": "0x" + "6" * 64,
        "judgeSignature": "0x" + "7" * 130,
        "judgeAddress": "0x" + "8" * 40,
        "judgeSignerBackend": "env",
        "winner": "0x" + "3" * 40,
        "loser": "0x" + "4" * 40,
        "fullOpinion": "Opinion",
        "processedAtMs": 123456789,
        "submitTxHash": "0x" + "9" * 64,
    }

    assert validate_schema("verdict_package.schema.json", verdict) == []
