"""MCPServer — expose agenkit tools as an MCP stdio server.

Reads JSON-RPC 2.0 requests from stdin, writes responses to stdout.
Handles: initialize, tools/list, tools/call.

Example::

    server = MCPServer(
        name="my-agent",
        version="1.0.0",
        tools=[EchoTool(), SearchTool()],
    )
    await server.serve_stdio()
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from agenkit.interfaces import Tool
from agenkit.protocols.mcp.types import (
    MCPContent,
    MCPServerInfo,
    MCPTool,
    MCPToolResult,
    _JSONRPCRequest,
    _JSONRPCResponse,
    _JSONRPCError,
)

_PROTOCOL_VERSION = "2024-11-05"


class MCPServer:
    """Exposes agenkit tools as an MCP stdio server.

    Args:
        name: Server name advertised during the initialize handshake.
        version: Server version advertised during the initialize handshake.
        tools: agenkit Tool instances to expose.
    """

    def __init__(self, name: str, version: str, tools: list[Tool]) -> None:
        self._info = MCPServerInfo(name=name, version=version)
        self._tools: dict[str, Tool] = {t.name: t for t in tools}

    async def serve_stdio(self) -> None:
        """Read JSON-RPC requests from stdin and write responses to stdout.

        Runs until EOF on stdin or an unrecoverable read error.
        """
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        proto = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: proto, sys.stdin.buffer)

        writer_transport, writer_protocol = await loop.connect_write_pipe(
            lambda: asyncio.BaseProtocol(), sys.stdout.buffer
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, loop)

        try:
            while True:
                raw = await reader.readline()
                if not raw:
                    break  # EOF
                await self._handle_line(raw, writer)
        finally:
            writer.close()

    async def handle_request(
        self, req: _JSONRPCRequest
    ) -> _JSONRPCResponse:
        """Dispatch one JSON-RPC request and return the response.

        This method is public for direct use in tests without needing
        a real stdin/stdout pipe.
        """
        match req.method:
            case "initialize":
                return self._handle_initialize(req)
            case "tools/list":
                return self._handle_tools_list(req)
            case "tools/call":
                return await self._handle_tools_call(req)
            case _:
                return _JSONRPCResponse(
                    jsonrpc="2.0",
                    id=req.id,
                    error=_JSONRPCError(
                        code=-32601,
                        message=f"method not found: {req.method}",
                    ),
                )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _handle_line(
        self, raw: bytes, writer: asyncio.StreamWriter
    ) -> None:
        try:
            data = json.loads(raw)
            req = _JSONRPCRequest(
                jsonrpc=data.get("jsonrpc", "2.0"),
                id=data.get("id", 0),
                method=data.get("method", ""),
                params=data.get("params"),
            )
        except (json.JSONDecodeError, KeyError):
            resp = _JSONRPCResponse(
                jsonrpc="2.0",
                id=0,
                error=_JSONRPCError(code=-32700, message="parse error"),
            )
            self._write_response(resp, writer)
            return

        resp = await self.handle_request(req)
        self._write_response(resp, writer)

    def _write_response(
        self, resp: _JSONRPCResponse, writer: asyncio.StreamWriter
    ) -> None:
        d: dict[str, Any] = {"jsonrpc": resp.jsonrpc, "id": resp.id}
        if resp.error is not None:
            d["error"] = {"code": resp.error.code, "message": resp.error.message}
        else:
            d["result"] = resp.result
        writer.write((json.dumps(d) + "\n").encode())

    def _handle_initialize(self, req: _JSONRPCRequest) -> _JSONRPCResponse:
        result = {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": self._info.name, "version": self._info.version},
        }
        return _JSONRPCResponse(jsonrpc="2.0", id=req.id, result=result)

    def _handle_tools_list(self, req: _JSONRPCRequest) -> _JSONRPCResponse:
        tools = [
            MCPTool(name=t.name, description=t.description)
            for t in self._tools.values()
        ]
        result = {
            "tools": [
                {"name": t.name, "description": t.description}
                for t in tools
            ]
        }
        return _JSONRPCResponse(jsonrpc="2.0", id=req.id, result=result)

    async def _handle_tools_call(
        self, req: _JSONRPCRequest
    ) -> _JSONRPCResponse:
        params = req.params or {}
        name = params.get("name", "")
        args: dict[str, Any] = params.get("arguments", {})

        tool = self._tools.get(name)
        if tool is None:
            return _JSONRPCResponse(
                jsonrpc="2.0",
                id=req.id,
                error=_JSONRPCError(
                    code=-32602, message=f"unknown tool: {name}"
                ),
            )

        try:
            tool_result = await tool.execute(args)
        except Exception as exc:  # noqa: BLE001
            mcp_result = MCPToolResult(
                content=[MCPContent(type="text", text=str(exc))],
                is_error=True,
            )
            return _make_tool_call_response(req.id, mcp_result)

        is_error = not tool_result.success
        text = str(tool_result.error) if is_error else str(tool_result.data)
        mcp_result = MCPToolResult(
            content=[MCPContent(type="text", text=text)],
            is_error=is_error,
        )
        return _make_tool_call_response(req.id, mcp_result)


def _make_tool_call_response(
    req_id: int, result: MCPToolResult
) -> _JSONRPCResponse:
    return _JSONRPCResponse(
        jsonrpc="2.0",
        id=req_id,
        result={
            "content": [{"type": c.type, "text": c.text} for c in result.content],
            "isError": result.is_error,
        },
    )
