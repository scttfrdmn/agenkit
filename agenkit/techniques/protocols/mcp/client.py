"""
MCP Client Implementation.

Client for connecting to MCP servers and accessing resources/tools.

References:
    - MCP Specification: https://modelcontextprotocol.io/
"""

from typing import Any

from .message import MCPResponse, create_request
from .schema import MCPMethod, MCPResourceInfo, MCPToolInfo


class MCPClient:
    """
    MCP Client.

    Connects to an MCP server and provides access to resources and tools.

    Example:
        >>> client = MCPClient(server_url="http://localhost:3000/mcp")
        >>> await client.initialize()
        >>>
        >>> # List resources
        >>> resources = await client.list_resources()
        >>>
        >>> # Read resource
        >>> data = await client.get_resource("user://profile")
        >>>
        >>> # List tools
        >>> tools = await client.list_tools()
        >>>
        >>> # Call tool
        >>> result = await client.call_tool("search", query="AI agents")
    """

    def __init__(self, server_url: str, auth: dict[str, str] | None = None, timeout: float = 30.0):
        """
        Initialize MCP client.

        Args:
            server_url: URL of MCP server (e.g., "http://localhost:3000/mcp")
            auth: Optional authentication credentials
            timeout: Request timeout in seconds
        """
        self.server_url = server_url
        self.auth = auth
        self.timeout = timeout
        self.request_id_counter = 0
        self.server_info = None

    def _next_request_id(self) -> str:
        """Generate next request ID."""
        self.request_id_counter += 1
        return f"req-{self.request_id_counter}"

    async def _send_request(self, method: str, params: dict[str, Any] | None = None) -> MCPResponse:
        """
        Send request to server.

        Args:
            method: Method name
            params: Request parameters

        Returns:
            Response from server

        Raises:
            ConnectionError: If request fails
        """
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx is required for MCP client. Install with: pip install httpx")

        request = create_request(method=method, params=params, request_id=self._next_request_id())

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.server_url,
                    json=request.to_dict(),
                    timeout=self.timeout,
                    headers=self.auth if self.auth else None,
                )

                response.raise_for_status()

                response_data = response.json()
                return MCPResponse.from_dict(response_data)

        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to send request: {e}")

    async def initialize(self) -> dict[str, Any]:
        """
        Initialize connection to server.

        Returns:
            Server information

        Example:
            >>> info = await client.initialize()
            >>> print(info["serverInfo"]["name"])
        """
        response = await self._send_request(
            method=MCPMethod.INITIALIZE.value, params={"protocolVersion": "1.0"}
        )

        if response.is_error:
            raise ValueError(f"Initialization failed: {response.error}")

        self.server_info = response.result
        return response.result

    async def list_resources(self) -> list[MCPResourceInfo]:
        """
        List available resources.

        Returns:
            List of resource information

        Example:
            >>> resources = await client.list_resources()
            >>> for resource in resources:
            ...     print(f"{resource.name}: {resource.uri}")
        """
        response = await self._send_request(method=MCPMethod.RESOURCES_LIST.value)

        if response.is_error:
            raise ValueError(f"Failed to list resources: {response.error}")

        resources_data = response.result.get("resources", [])
        return [
            MCPResourceInfo(
                uri=r["uri"],
                name=r["name"],
                description=r.get("description"),
                mime_type=r.get("mimeType", "text/plain"),
            )
            for r in resources_data
        ]

    async def get_resource(self, uri: str, **params) -> Any:
        """
        Read resource data.

        Args:
            uri: Resource URI
            **params: Additional parameters

        Returns:
            Resource data

        Example:
            >>> data = await client.get_resource("user://profile", user_id="123")
        """
        response = await self._send_request(
            method=MCPMethod.RESOURCES_READ.value, params={"uri": uri, **params}
        )

        if response.is_error:
            raise ValueError(f"Failed to read resource: {response.error}")

        contents = response.result.get("contents", [])
        if contents:
            return contents[0].get("text")  # Return text content

        return None

    async def list_tools(self) -> list[MCPToolInfo]:
        """
        List available tools.

        Returns:
            List of tool information

        Example:
            >>> tools = await client.list_tools()
            >>> for tool in tools:
            ...     print(f"{tool.name}: {tool.description}")
        """
        response = await self._send_request(method=MCPMethod.TOOLS_LIST.value)

        if response.is_error:
            raise ValueError(f"Failed to list tools: {response.error}")

        tools_data = response.result.get("tools", [])
        return [
            MCPToolInfo(name=t["name"], description=t["description"], input_schema=t["inputSchema"])
            for t in tools_data
        ]

    async def call_tool(self, name: str, **arguments) -> Any:
        """
        Call a tool.

        Args:
            name: Tool name
            **arguments: Tool arguments

        Returns:
            Tool result

        Example:
            >>> result = await client.call_tool(
            ...     "search",
            ...     query="AI agents",
            ...     limit=10
            ... )
        """
        response = await self._send_request(
            method=MCPMethod.TOOLS_CALL.value, params={"name": name, "arguments": arguments}
        )

        if response.is_error:
            raise ValueError(f"Tool call failed: {response.error}")

        result = response.result
        if result and "content" in result:
            content = result["content"]
            if content:
                return content[0].get("text")

        return result

    async def close(self):
        """Close client connection."""
        # Cleanup if needed
        pass

    def __repr__(self) -> str:
        """String representation."""
        return f"MCPClient(server_url='{self.server_url}')"
