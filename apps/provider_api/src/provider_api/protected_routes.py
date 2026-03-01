from __future__ import annotations

import json
import time

from fastapi import APIRouter, Query, Response
from verdict_protocol import keccak_hex

router = APIRouter()


@router.get("/api/data")
def get_data(response: Response, bad: bool = Query(default=False)) -> dict:
    if bad:
        time.sleep(3)
        payload = {
            "result": {"unexpected": "bad_format"},
            "timestamp": int(time.time() * 1000),
            "quality": "degraded",
        }
    else:
        payload = {"result": "some_data", "timestamp": int(time.time() * 1000)}

    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    response.headers["X-Evidence-Hash"] = keccak_hex(body)
    return payload
