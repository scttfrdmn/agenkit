"""Tests for the MCP (Model Context Protocol) protocol implementation."""

from __future__ import annotations

from typing import Any

import pytest

from agenkit import Tool, ToolResult
from agenkit.protocols.mcp import (
    HTTPClient,
    MCPClient,
    MCPContent,
    MCPServer,
    MCPServerInfo,
    MCPTool,
    MCPToolAdapter,
    MCPToolResult,
    StdioClient,
    tools_from_client,
)
from agenkit.protocols.mcp.client import _parse_server_info
from agenkit.protocols.mcp.types import (
    PROTOCOL_VERSION,
    _JSONRPCRequest,
    _JSONRPCResponse,
    _text_content,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


class EchoTool(Tool):
    """Echoes the 'message' parameter."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes the input message"

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        msg = params.get("message", "")
        return ToolResult(success=True, data=msg)


class MockMCPClient(MCPClient):
    """In-memory MCPClient for testing without a real server."""

    def __init__(
        self,
        tools: list[MCPTool] | None = None,
        call_result: MCPToolResult | None = None,
        call_error: Exception | None = None,
        info: MCPServerInfo | None = None,
    ) -> None:
        self._tools = tools or []
        self._call_result = call_result or MCPToolResult()
        self._call_error = call_error
        self._info = info or MCPServerInfo(name="mock-server", version="1.0.0")

    async def initialize(self) -> None:
        pass

    async def list_tools(self) -> list[MCPTool]:
        return self._tools

    async def call_tool(self, name: str, args: dict[str, Any]) -> MCPToolResult:
        if self._call_error is not None:
            raise self._call_error
        return self._call_result

    @property
    def server_info(self) -> MCPServerInfo:
        return self._info

    async def close(self) -> None:
        pass


# ── MCPClient interface check ──────────────────────────────────────────────────


def test_mcp_client_interface_stdio() -> None:
    """StdioClient is a concrete MCPClient subclass."""
    assert issubclass(StdioClient, MCPClient)


def test_mcp_client_interface_http() -> None:
    """HTTPClient is a concrete MCPClient subclass."""
    assert issubclass(HTTPClient, MCPClient)


# ── JSON-RPC wire types ────────────────────────────────────────────────────────


def test_jsonrpc_request_to_dict() -> None:
    """_JSONRPCRequest.to_dict() produces correct fields."""
    req = _JSONRPCRequest(jsonrpc="2.0", id=42, method="tools/list")
    d = req.to_dict()
    assert d["jsonrpc"] == "2.0"
    assert d["id"] == 42
    assert d["method"] == "tools/list"
    assert "params" not in d


def test_jsonrpc_request_to_dict_with_params() -> None:
    """_JSONRPCRequest.to_dict() includes params when set."""
    req = _JSONRPCRequest(jsonrpc="2.0", id=1, method="tools/call", params={"name": "echo"})
    d = req.to_dict()
    assert d["params"] == {"name": "echo"}


def test_jsonrpc_response_from_dict() -> None:
    """_JSONRPCResponse.from_dict() parses a success response."""
    raw = {"jsonrpc": "2.0", "id": 7, "result": {"ok": True}}
    resp = _JSONRPCResponse.from_dict(raw)
    assert resp.jsonrpc == "2.0"
    assert resp.id == 7
    assert resp.result == {"ok": True}
    assert resp.error is None


def test_jsonrpc_response_from_dict_error() -> None:
    """_JSONRPCResponse.from_dict() parses an error response."""
    raw = {"jsonrpc": "2.0", "id": 3, "error": {"code": -32601, "message": "not found"}}
    resp = _JSONRPCResponse.from_dict(raw)
    assert resp.error is not None
    assert resp.error.code == -32601
    assert resp.error.message == "not found"


# ── MCPTool ───────────────────────────────────────────────────────────────────


def test_mcp_tool_fields() -> None:
    """MCPTool stores name and description correctly."""
    tool = MCPTool(name="read_file", description="Read a file from disk")
    assert tool.name == "read_file"
    assert tool.description == "Read a file from disk"
    assert tool.input_schema is None


# ── _text_content ──────────────────────────────────────────────────────────────


def test_text_content_single() -> None:
    """Single text block returns its text."""
    assert _text_content([MCPContent(type="text", text="hello")]) == "hello"


def test_text_content_multi() -> None:
    """Multiple text blocks are joined with a space."""
    contents = [
        MCPContent(type="text", text="hello"),
        MCPContent(type="text", text="world"),
    ]
    assert _text_content(contents) == "hello world"


# ── MCPToolAdapter ─────────────────────────────────────────────────────────────


def test_mcp_tool_adapter_name() -> None:
    """Adapter.name returns the MCP tool name."""
    adapter = MCPToolAdapter(MockMCPClient(), MCPTool(name="echo", description="Echo"))
    assert adapter.name == "echo"


def test_mcp_tool_adapter_description() -> None:
    """Adapter.description returns the MCP tool description."""
    adapter = MCPToolAdapter(MockMCPClient(), MCPTool(name="echo", description="Echo"))
    assert adapter.description == "Echo"


@pytest.mark.asyncio
async def test_mcp_tool_adapter_execute_success() -> None:
    """Successful call_tool maps to ToolResult(success=True)."""
    mock = MockMCPClient(
        call_result=MCPToolResult(
            content=[MCPContent(type="text", text="result data")],
            is_error=False,
        )
    )
    adapter = MCPToolAdapter(mock, MCPTool(name="mytool", description=""))
    result = await adapter.execute({"x": 1})
    assert result.success is True
    assert result.data == "result data"


@pytest.mark.asyncio
async def test_mcp_tool_adapter_execute_is_error() -> None:
    """is_error=True maps to ToolResult(success=False)."""
    mock = MockMCPClient(
        call_result=MCPToolResult(
            content=[MCPContent(type="text", text="something went wrong")],
            is_error=True,
        )
    )
    adapter = MCPToolAdapter(mock, MCPTool(name="mytool", description=""))
    result = await adapter.execute({})
    assert result.success is False
    assert result.error == "something went wrong"


# ── tools_from_client ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tools_from_client() -> None:
    """tools_from_client wraps each MCPTool as an agenkit Tool."""
    mock = MockMCPClient(
        tools=[
            MCPTool(name="tool_a", description="Tool A"),
            MCPTool(name="tool_b", description="Tool B"),
        ]
    )
    tools = await tools_from_client(mock)
    assert len(tools) == 2
    assert tools[0].name == "tool_a"
    assert tools[1].name == "tool_b"


# ── MCPServer ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mcp_server_initialize() -> None:
    """Server returns its name/version on initialize."""
    server = MCPServer(name="test-server", version="1.0.0", tools=[EchoTool()])
    req = _JSONRPCRequest(jsonrpc="2.0", id=1, method="initialize")
    resp = await server.handle_request(req)
    assert resp.error is None
    assert resp.result is not None
    info = resp.result["serverInfo"]
    assert info["name"] == "test-server"
    assert info["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_mcp_server_tools_list() -> None:
    """Server returns the list of registered tools."""
    server = MCPServer(name="test-server", version="1.0.0", tools=[EchoTool()])
    req = _JSONRPCRequest(jsonrpc="2.0", id=2, method="tools/list")
    resp = await server.handle_request(req)
    assert resp.error is None
    assert resp.result is not None
    tool_names = [t["name"] for t in resp.result["tools"]]
    assert "echo" in tool_names


@pytest.mark.asyncio
async def test_mcp_server_tools_call() -> None:
    """Server executes a tool and returns its output."""
    server = MCPServer(name="test-server", version="1.0.0", tools=[EchoTool()])
    req = _JSONRPCRequest(
        jsonrpc="2.0",
        id=3,
        method="tools/call",
        params={"name": "echo", "arguments": {"message": "hello MCP"}},
    )
    resp = await server.handle_request(req)
    assert resp.error is None
    assert resp.result is not None
    assert resp.result["isError"] is False
    assert resp.result["content"][0]["text"] == "hello MCP"


@pytest.mark.asyncio
async def test_mcp_server_unknown_method() -> None:
    """Server returns method-not-found for unknown methods."""
    server = MCPServer(name="test", version="0", tools=[])
    req = _JSONRPCRequest(jsonrpc="2.0", id=9, method="foo/bar")
    resp = await server.handle_request(req)
    assert resp.error is not None
    assert resp.error.code == -32601


# ── Protocol version negotiation (agenkit#781) ─────────────────────────────────


@pytest.mark.asyncio
async def test_mcp_server_initialize_advertises_shared_constant() -> None:
    """Server's advertised protocolVersion is the shared PROTOCOL_VERSION constant."""
    server = MCPServer(name="test-server", version="1.0.0", tools=[])
    req = _JSONRPCRequest(jsonrpc="2.0", id=1, method="initialize")
    resp = await server.handle_request(req)
    assert resp.result is not None
    assert resp.result["protocolVersion"] == PROTOCOL_VERSION


@pytest.mark.asyncio
async def test_mcp_server_warns_on_client_version_mismatch(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A mismatched client-requested protocolVersion is logged, not silently dropped.

    Negative-verification target: reverting the `_handle_initialize` mismatch
    check (removing the `logger.warning` call added for agenkit#781) makes
    this test fail, because nothing else in the server reads
    `req.params["protocolVersion"]` — this test is the only thing that would
    catch a `req.params` read that silently disappeared again.
    """
    server = MCPServer(name="test-server", version="1.0.0", tools=[])
    req = _JSONRPCRequest(
        jsonrpc="2.0",
        id=1,
        method="initialize",
        params={"protocolVersion": "1999-01-01", "capabilities": {}},
    )
    with caplog.at_level("WARNING", logger="agenkit.protocols.mcp.server"):
        resp = await server.handle_request(req)

    # The server still answers with the version it actually speaks (spec's
    # negotiation model: the server states its own supported revision).
    assert resp.result is not None
    assert resp.result["protocolVersion"] == PROTOCOL_VERSION

    assert any(
        "1999-01-01" in record.message and PROTOCOL_VERSION in record.message
        for record in caplog.records
    ), f"expected a version-mismatch warning, got: {[r.message for r in caplog.records]}"


@pytest.mark.asyncio
async def test_mcp_server_no_warning_on_matching_client_version(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A client requesting the server's own version produces no mismatch warning."""
    server = MCPServer(name="test-server", version="1.0.0", tools=[])
    req = _JSONRPCRequest(
        jsonrpc="2.0",
        id=1,
        method="initialize",
        params={"protocolVersion": PROTOCOL_VERSION, "capabilities": {}},
    )
    with caplog.at_level("WARNING", logger="agenkit.protocols.mcp.server"):
        await server.handle_request(req)

    assert not any("protocol version" in record.message for record in caplog.records)


def test_client_parse_server_info_captures_protocol_version() -> None:
    """The client's server_info now exposes the server's reported protocolVersion.

    Before agenkit#781, MCPServerInfo had no field for this and the client
    discarded `result["protocolVersion"]` entirely.
    """
    result = {
        "protocolVersion": PROTOCOL_VERSION,
        "serverInfo": {"name": "srv", "version": "9.9.9"},
    }
    info = _parse_server_info(result)
    assert info.protocol_version == PROTOCOL_VERSION
    assert info.name == "srv"
    assert info.version == "9.9.9"


def test_client_warns_on_server_version_mismatch(caplog: pytest.LogCaptureFixture) -> None:
    """A mismatched server-reported protocolVersion is logged, not silently dropped.

    Negative-verification target: reverting the mismatch-warning branch in
    `_parse_server_info` (added for agenkit#781) makes this test fail — the
    `protocol_version` field would still populate (that part is independently
    covered by `test_client_parse_server_info_captures_protocol_version`), but
    no warning would be emitted.
    """
    result = {
        "protocolVersion": "1999-01-01",
        "serverInfo": {"name": "old-server", "version": "0.1.0"},
    }
    with caplog.at_level("WARNING", logger="agenkit.protocols.mcp.client"):
        info = _parse_server_info(result)

    assert info.protocol_version == "1999-01-01"
    assert any(
        "1999-01-01" in record.message and PROTOCOL_VERSION in record.message
        for record in caplog.records
    ), f"expected a version-mismatch warning, got: {[r.message for r in caplog.records]}"
