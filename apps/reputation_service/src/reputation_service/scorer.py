from __future__ import annotations

MODEL_VERSION = "2.0.0-draft"

SCORES = {
    "completed_without_dispute": 1,
    "won_dispute": 2,
    "lost_dispute": -5,
    "lost_as_filer": -3,
}


def to_did(address: str) -> str:
    if address.startswith("did:8004:"):
        return address
    return f"did:8004:{address}"


def component_deltas(reason: str, delta: int) -> dict[str, int]:
    service_delta = 0
    court_delta = 0
    reliability_delta = 0
    successful_delta = 0
    dispute_delta = 0

    if reason == "completed_without_dispute":
        service_delta = delta
        reliability_delta = delta
        successful_delta = 1
    elif reason == "won_dispute":
        court_delta = delta
        dispute_delta = 1
    elif reason == "lost_dispute":
        court_delta = delta
        dispute_delta = 1
    elif reason == "lost_as_filer":
        reliability_delta = delta
        dispute_delta = 1

    return {
        "service": service_delta,
        "court": court_delta,
        "reliability": reliability_delta,
        "successful_events": successful_delta,
        "dispute_events": dispute_delta,
    }


def confidence_for_event_count(event_count: int) -> float:
    return round(min(1.0, max(0.1, event_count / 10.0)), 2)
