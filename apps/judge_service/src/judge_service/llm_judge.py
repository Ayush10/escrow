from __future__ import annotations

import json
import os
from typing import Any


class LLMJudge:
    def __init__(self) -> None:
        self.api_key = os.environ.get("LLM_API_KEY", "")
        self.model = os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")

    def judge(
        self, clause: dict[str, Any], facts: dict[str, Any], evidence_summary: dict[str, Any]
    ) -> tuple[list[str], str | None, float]:
        if not self.api_key:
            return ["insufficient_signal"], None, 0.5

        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=self.api_key)
            prompt = {
                "instruction": "Resolve dispute using clause/facts. Return strict JSON.",
                "clause": clause,
                "facts": facts,
                "evidence": evidence_summary,
                "output": {
                    "reasonCodes": ["string"],
                    "winner": "plaintiff|defendant|null",
                    "confidence": "float_0_to_1",
                },
            }
            resp = client.messages.create(
                model=self.model,
                max_tokens=600,
                messages=[{"role": "user", "content": json.dumps(prompt, separators=(",", ":"))}],
            )
            text = "".join(
                block.text for block in resp.content if getattr(block, "type", None) == "text"
            )
            payload = json.loads(text)
            return (
                payload.get("reasonCodes", []),
                payload.get("winner"),
                float(payload.get("confidence", 0.5)),
            )
        except Exception:
            return ["llm_parse_error"], None, 0.45
