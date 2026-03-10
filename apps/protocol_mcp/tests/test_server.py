from __future__ import annotations

from protocol_mcp.server import VerdictMCPServer


def test_mcp_server_initialize_and_list_tools() -> None:
    server = VerdictMCPServer()

    init = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init is not None
    assert init["result"]["serverInfo"]["name"] == "verdict-protocol-mcp"

    tools = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    assert tools is not None
    names = {tool["name"] for tool in tools["result"]["tools"]}
    assert "create_agreement" in names
    assert "complete_agreement" in names
    assert "anchor_agreement" in names
    assert "register_judge" in names


def test_mcp_server_returns_tool_error_payload_for_bad_actor() -> None:
    server = VerdictMCPServer()
    response = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "health", "arguments": {"actor": "nobody"}},
        }
    )
    assert response is not None
    assert response["result"]["isError"] is True
