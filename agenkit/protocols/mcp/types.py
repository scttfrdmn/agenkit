"""MCP protocol types and client interface.

JSON-RPC 2.0 wire types, MCP domain types, and the MCPClient abstract
base class shared by StdioClient and HTTPClient.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ── JSON-RPC 2.0 wire types ──────────────────────────────────────────────────


@dataclass
class _JSONRPCRequest:
    """JSON-RPC 2.0 request wire type (internal)."""

    jsonrpc: str
    id: int
    method: str
    params: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
        }
        if self.params is not None:
            d["params"] = self.params
        return d


@dataclass
class _JSONRPCError:
    """JSON-RPC 2.0 error object (internal)."""

    code: int
    message: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> _JSONRPCError:
        return cls(code=d["code"], message=d["message"])


@dataclass
class _JSONRPCResponse:
    """JSON-RPC 2.0 response wire type (internal)."""

    jsonrpc: str
    id: int
    result: Any = None
    error: _JSONRPCError | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> _JSONRPCResponse:
        error = _JSONRPCError.from_dict(d["error"]) if d.get("error") else None
        return cls(
            jsonrpc=d.get("jsonrpc", "2.0"),
            id=d.get("id", 0),
            result=d.get("result"),
            error=error,
        )


# ── MCP domain types ─────────────────────────────────────────────────────────


@dataclass
class MCPTool:
    """Describes a tool advertised by an MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any] | None = None


@dataclass
class MCPContent:
    """A single content block returned by a tool call."""

    type: str
    text: str = ""


@dataclass
class MCPToolResult:
    """The result of a tools/call RPC."""

    content: list[MCPContent] = field(default_factory=list)
    is_error: bool = False


@dataclass
class MCPServerInfo:
    """Information about a connected MCP server."""

    name: str = ""
    version: str = ""


# ── MCPClient interface ───────────────────────────────────────────────────────


class MCPClient(ABC):
    """Abstract interface satisfied by StdioClient and HTTPClient."""

    @abstractmethod
    async def initialize(self) -> None:
        """Perform the MCP handshake with the server."""

    @abstractmethod
    async def list_tools(self) -> list[MCPTool]:
        """Return the tools advertised by the server."""

    @abstractmethod
    async def call_tool(
        self, name: str, args: dict[str, Any]
    ) -> MCPToolResult:
        """Invoke a named tool with the given arguments."""

    @property
    @abstractmethod
    def server_info(self) -> MCPServerInfo:
        """Server name and version (populated after initialize)."""

    @abstractmethod
    async def close(self) -> None:
        """Release resources held by the client."""

    # ── Context manager support ──────────────────────────────────────────────

    async def __aenter__(self) -> MCPClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()


# ── Helper ────────────────────────────────────────────────────────────────────


def _text_content(contents: list[MCPContent]) -> str:
    """Join all text-type content blocks with a single space."""
    return " ".join(c.text for c in contents if c.type == "text" and c.text)
