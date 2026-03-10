from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx
from verdict_protocol import EscrowClient


def _tool_result(payload: Any, *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, sort_keys=True, separators=(",", ":")),
            }
        ],
        "isError": is_error,
    }


class VerdictMCPServer:
    def __init__(self) -> None:
        self.name = "verdict-protocol-mcp"
        self.version = "0.1.0"
        self.protocol_version = "2025-03-26"
        self.evidence_url = os.environ.get("EVIDENCE_SERVICE_URL", "http://127.0.0.1:4001").rstrip("/")
        self.judge_url = os.environ.get("JUDGE_SERVICE_URL", "http://127.0.0.1:4002").rstrip("/")

    def tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "health",
                "description": "Return escrow connectivity and service endpoints.",
                "inputSchema": {"type": "object", "properties": {"actor": {"type": "string"}}, "additionalProperties": False},
            },
            {
                "name": "create_agreement",
                "description": "Propose a split Court agreement.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "actor": {"type": "string"},
                        "agreementId": {"type": "string"},
                        "principal": {"type": "string"},
                        "client": {"type": "string"},
                        "judge": {"type": "string"},
                        "consideration": {"type": "integer"},
                        "termsHash": {"type": "string"},
                    },
                    "required": ["actor", "agreementId", "principal", "client", "judge", "consideration", "termsHash"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "accept_agreement",
                "description": "Accept a split Court agreement.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"actor": {"type": "string"}, "contractId": {"type": "integer"}},
                    "required": ["actor", "contractId"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "anchor_agreement",
                "description": "Build, pin, and anchor the agreement evidence bundle.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"agreementId": {"type": "string"}},
                    "required": ["agreementId"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "export_bundle",
                "description": "Fetch the full evidence bundle for an agreement.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"agreementId": {"type": "string"}},
                    "required": ["agreementId"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "file_dispute",
                "description": "File a dispute for an agreement or Court contract.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "actor": {"type": "string"},
                        "agreementId": {"type": "string"},
                        "contractId": {"type": "integer"},
                        "defendant": {"type": "string"},
                        "stake": {"type": "integer"},
                        "plaintiffEvidence": {"type": "string"},
                    },
                    "required": ["actor", "agreementId"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "get_dispute",
                "description": "Fetch the normalized dispute struct.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"actor": {"type": "string"}, "disputeId": {"type": "integer"}},
                    "required": ["actor", "disputeId"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "process_dispute",
                "description": "Ask the judge service to process a dispute now.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"disputeId": {"type": "integer"}},
                    "required": ["disputeId"],
                    "additionalProperties": False,
                },
            },
        ]

    def _private_key_for_actor(self, actor: str | None) -> str | None:
        actor_key = (actor or "provider").strip().lower()
        mapping = {
            "provider": os.environ.get("PROVIDER_PRIVATE_KEY"),
            "consumer": os.environ.get("CONSUMER_PRIVATE_KEY"),
            "judge": os.environ.get("JUDGE_PRIVATE_KEY"),
        }
        if actor_key not in mapping:
            raise ValueError("actor must be provider, consumer, or judge")
        return mapping[actor_key]

    def _escrow_for_actor(self, actor: str | None) -> EscrowClient:
        return EscrowClient(
            rpc_url=os.environ.get("GOAT_RPC_URL", "https://rpc.testnet3.goat.network"),
            chain_id=int(os.environ.get("GOAT_CHAIN_ID", "48816")),
            contract_address=os.environ.get(
                "ESCROW_CONTRACT_ADDRESS",
                os.environ.get("ESCROW_COURT_ADDRESS", "0x0000000000000000000000000000000000000000"),
            ),
            private_key=self._private_key_for_actor(actor),
            dry_run=os.environ.get("ESCROW_DRY_RUN", "0") == "1",
        )

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "health":
            client = self._escrow_for_actor(arguments.get("actor"))
            return _tool_result(
                {
                    "capabilities": client.capabilities(),
                    "escrow": client.contract_sanity(),
                    "evidenceUrl": self.evidence_url,
                    "judgeUrl": self.judge_url,
                }
            )

        if name == "create_agreement":
            client = self._escrow_for_actor(arguments["actor"])
            tx = client.create_agreement(
                arguments["agreementId"],
                principal=arguments["principal"],
                client=arguments["client"],
                judge=arguments["judge"],
                consideration=int(arguments["consideration"]),
                terms_hash=arguments["termsHash"],
            )
            return _tool_result(
                {
                    "txHash": tx.tx_hash,
                    "blockNumber": tx.block_number,
                    "contractId": (tx.extra or {}).get("contractId"),
                }
            )

        if name == "accept_agreement":
            client = self._escrow_for_actor(arguments["actor"])
            tx = client.accept_agreement(int(arguments["contractId"]))
            return _tool_result(
                {
                    "txHash": tx.tx_hash,
                    "blockNumber": tx.block_number,
                    "contractId": (tx.extra or {}).get("contractId"),
                }
            )

        if name == "anchor_agreement":
            with httpx.Client(timeout=60) as client:
                resp = client.post(f"{self.evidence_url}/anchor", json={"agreementId": arguments["agreementId"]})
                resp.raise_for_status()
                return _tool_result(resp.json())

        if name == "export_bundle":
            with httpx.Client(timeout=60) as client:
                resp = client.get(f"{self.evidence_url}/agreements/{arguments['agreementId']}/export")
                resp.raise_for_status()
                return _tool_result(resp.json())

        if name == "file_dispute":
            client = self._escrow_for_actor(arguments["actor"])
            tx = client.file_dispute(
                arguments["agreementId"],
                tx_id=arguments.get("contractId"),
                defendant=arguments.get("defendant"),
                stake=arguments.get("stake"),
                plaintiff_evidence=arguments.get("plaintiffEvidence"),
            )
            return _tool_result(
                {
                    "txHash": tx.tx_hash,
                    "blockNumber": tx.block_number,
                    "disputeId": (tx.extra or {}).get("disputeId"),
                }
            )

        if name == "get_dispute":
            client = self._escrow_for_actor(arguments["actor"])
            return _tool_result({"dispute": client.get_dispute(int(arguments["disputeId"]))})

        if name == "process_dispute":
            with httpx.Client(timeout=60) as client:
                resp = client.post(f"{self.judge_url}/disputes/{int(arguments['disputeId'])}/process")
                resp.raise_for_status()
                return _tool_result(resp.json())

        raise ValueError(f"unknown tool: {name}")

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})

        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": self.name, "version": self.version},
                },
            }
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": self.tools()}}
        if method == "tools/call":
            try:
                result = self._call_tool(str(params.get("name")), dict(params.get("arguments") or {}))
                return {"jsonrpc": "2.0", "id": request_id, "result": result}
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": _tool_result({"error": str(exc)}, is_error=True),
                }
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


def _read_message() -> dict[str, Any] | None:
    content_length = None
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        header = line.decode("utf-8").strip()
        if header.lower().startswith("content-length:"):
            content_length = int(header.split(":", 1)[1].strip())

    if content_length is None:
        return None
    body = sys.stdin.buffer.read(content_length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _write_message(payload: dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def main() -> None:
    server = VerdictMCPServer()
    while True:
        message = _read_message()
        if message is None:
            break
        response = server.handle_request(message)
        if response is not None:
            _write_message(response)


if __name__ == "__main__":
    main()
