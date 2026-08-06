"""MCP client implementations.

StdioClient  — connect to an MCP server by spawning a subprocess.
HTTPClient   — connect to an MCP server that accepts JSON-RPC over HTTP.

Both implement MCPClient and can be used as async context managers.

Example — stdio::

    async with mcp.StdioClient("npx", ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]) as client:
        tools = await mcp.tools_from_client(client)

Example — HTTP::

    async with mcp.HTTPClient("http://localhost:3000") as client:
        tools = await mcp.tools_from_client(client)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from agenkit.protocols.mcp.types import (
    MCPClient,
    MCPContent,
    MCPServerInfo,
    MCPTool,
    MCPToolResult,
    _JSONRPCRequest,
    _JSONRPCResponse,
)

_PROTOCOL_VERSION = "2024-11-05"
_CLIENT_INFO = {"name": "agenkit", "version": "0.89.0"}
_INIT_PARAMS = {
    "protocolVersion": _PROTOCOL_VERSION,
    "capabilities": {},
    "clientInfo": _CLIENT_INFO,
}


class StdioClient(MCPClient):
    """MCP client that talks JSON-RPC 2.0 to a subprocess over stdin/stdout.

    Args:
        command: Executable to spawn (e.g. ``"npx"``).
        args: Arguments passed to *command*.
        env: Additional environment variables (mapping). The subprocess
             inherits the parent environment; entries here are merged.
    """

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self._command = command
        self._args = args or []
        self._env = env
        self._proc: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()
        self._next_id = 0
        self._server_info = MCPServerInfo()

    async def initialize(self) -> None:
        """Spawn the subprocess and perform the MCP initialize handshake."""
        import os

        effective_env: dict[str, str] | None = None
        if self._env:
            effective_env = {**os.environ, **self._env}

        self._proc = await asyncio.create_subprocess_exec(
            self._command,
            *self._args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=effective_env,
        )

        resp = await self._send("initialize", _INIT_PARAMS)
        if resp.error:
            raise RuntimeError(f"mcp initialize error {resp.error.code}: {resp.error.message}")
        result = resp.result or {}
        info = result.get("serverInfo", {})
        self._server_info = MCPServerInfo(
            name=info.get("name", ""),
            version=info.get("version", ""),
        )

    async def list_tools(self) -> list[MCPTool]:
        resp = await self._send("tools/list", None)
        if resp.error:
            raise RuntimeError(f"mcp tools/list error {resp.error.code}: {resp.error.message}")
        result = resp.result or {}
        return [
            MCPTool(
                name=t.get("name", ""),
                description=t.get("description", ""),
                input_schema=t.get("inputSchema"),
            )
            for t in result.get("tools", [])
        ]

    async def call_tool(self, name: str, args: dict[str, Any]) -> MCPToolResult:
        resp = await self._send("tools/call", {"name": name, "arguments": args})
        if resp.error:
            raise RuntimeError(f"mcp tools/call error {resp.error.code}: {resp.error.message}")
        result = resp.result or {}
        return _parse_tool_result(result)

    @property
    def server_info(self) -> MCPServerInfo:
        return self._server_info

    async def close(self) -> None:
        if self._proc is not None:
            if self._proc.stdin:
                self._proc.stdin.close()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5.0)
            except TimeoutError:
                self._proc.kill()

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _send(self, method: str, params: dict[str, Any] | None) -> _JSONRPCResponse:
        async with self._lock:
            self._next_id += 1
            req = _JSONRPCRequest(
                jsonrpc="2.0",
                id=self._next_id,
                method=method,
                params=params,
            )

            if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
                raise RuntimeError("mcp: client not initialized — call initialize() first")

            line = json.dumps(req.to_dict()) + "\n"
            self._proc.stdin.write(line.encode())
            await self._proc.stdin.drain()

            raw = await self._proc.stdout.readline()
            if not raw:
                raise RuntimeError("mcp: server closed stdout unexpectedly")
            return _JSONRPCResponse.from_dict(json.loads(raw))


class HTTPClient(MCPClient):
    """MCP client that POSTs JSON-RPC 2.0 to a running MCP HTTP server.

    Args:
        base_url: Base URL of the MCP HTTP server (e.g. ``"http://localhost:3000"``).
        timeout: Request timeout in seconds (default 30).
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._http: httpx.AsyncClient | None = None
        self._next_id = 0
        self._server_info = MCPServerInfo()

    async def initialize(self) -> None:
        """Open the HTTP client and perform the MCP initialize handshake."""
        self._http = httpx.AsyncClient(timeout=self._timeout)
        resp = await self._send("initialize", _INIT_PARAMS)
        if resp.error:
            raise RuntimeError(f"mcp initialize error {resp.error.code}: {resp.error.message}")
        result = resp.result or {}
        info = result.get("serverInfo", {})
        self._server_info = MCPServerInfo(
            name=info.get("name", ""),
            version=info.get("version", ""),
        )

    async def list_tools(self) -> list[MCPTool]:
        resp = await self._send("tools/list", None)
        if resp.error:
            raise RuntimeError(f"mcp tools/list error {resp.error.code}: {resp.error.message}")
        result = resp.result or {}
        return [
            MCPTool(
                name=t.get("name", ""),
                description=t.get("description", ""),
                input_schema=t.get("inputSchema"),
            )
            for t in result.get("tools", [])
        ]

    async def call_tool(self, name: str, args: dict[str, Any]) -> MCPToolResult:
        resp = await self._send("tools/call", {"name": name, "arguments": args})
        if resp.error:
            raise RuntimeError(f"mcp tools/call error {resp.error.code}: {resp.error.message}")
        result = resp.result or {}
        return _parse_tool_result(result)

    @property
    def server_info(self) -> MCPServerInfo:
        return self._server_info

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _send(self, method: str, params: dict[str, Any] | None) -> _JSONRPCResponse:
        self._next_id += 1
        req = _JSONRPCRequest(
            jsonrpc="2.0",
            id=self._next_id,
            method=method,
            params=params,
        )

        if self._http is None:
            raise RuntimeError("mcp: client not initialized — call initialize() first")

        http_resp = await self._http.post(
            self._base_url,
            content=json.dumps(req.to_dict()).encode(),
            headers={"Content-Type": "application/json"},
        )
        http_resp.raise_for_status()
        return _JSONRPCResponse.from_dict(http_resp.json())


# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse_tool_result(result: dict[str, Any]) -> MCPToolResult:
    contents = [
        MCPContent(type=c.get("type", "text"), text=c.get("text", ""))
        for c in result.get("content", [])
    ]
    return MCPToolResult(content=contents, is_error=result.get("isError", False))
