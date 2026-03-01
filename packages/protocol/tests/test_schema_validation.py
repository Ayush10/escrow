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
