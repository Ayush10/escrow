from __future__ import annotations

from collections import defaultdict
from typing import Any


def extract_facts(clause: dict[str, Any], receipts: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str], str | None]:
    request_times: dict[str, int] = {}
    response_times: dict[str, int] = {}
    response_format_ok = True

    for receipt in receipts:
        if receipt["eventType"] == "request":
            request_times[receipt["requestId"]] = receipt["timestamp"]
        if receipt["eventType"] == "response":
            response_times[receipt["requestId"]] = receipt["timestamp"]
            result_value = (receipt.get("metadata") or {}).get("result_type")
            if result_value == "bad_format":
                response_format_ok = False

    latencies: list[int] = []
    for req_id, req_ts in request_times.items():
        if req_id in response_times:
            latencies.append(max(0, response_times[req_id] - req_ts))

    max_latency = max(latencies) if latencies else 0

    by_minute: defaultdict[int, int] = defaultdict(int)
    for receipt in receipts:
        if receipt["eventType"] == "request":
            minute_bucket = receipt["timestamp"] // 60000
            by_minute[minute_bucket] += 1

    peak_rpm = max(by_minute.values()) if by_minute else 0

    facts = {
        "latency_ms": max_latency,
        "response_format_ok": response_format_ok,
        "peak_requests_per_minute": peak_rpm,
        "request_count": len(request_times),
        "response_count": len(response_times),
    }

    reason_codes: list[str] = []

    for rule in clause.get("slaRules", []):
        metric = rule.get("metric")
        op = rule.get("operator")
        value = float(rule.get("value"))

        if metric == "latency_ms" and op == "<=" and max_latency > value:
            reason_codes.append("sla_breach:latency")

    for rule in clause.get("abuseRules", []):
        metric = rule.get("metric")
        op = rule.get("operator")
        value = float(rule.get("value"))

        if metric == "requests_per_minute" and op == "<=" and peak_rpm > value:
            reason_codes.append("clause_violated:rate_limit")

    winner: str | None = None
    if reason_codes:
        winner = "plaintiff"
    elif facts["request_count"] > 0:
        winner = "defendant"

    return facts, reason_codes, winner
