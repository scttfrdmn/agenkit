"""Tests for the MCP (Model Context Protocol) protocol implementation."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

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
from agenkit.protocols.mcp.types import (
    _JSONRPCError,
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
