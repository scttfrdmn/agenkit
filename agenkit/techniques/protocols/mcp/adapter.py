"""
Agenkit-MCP Adapters.

Adapters for integrating Agenkit agents with MCP protocol.

- Expose Agenkit agents as MCP servers
- Use MCP tools in Agenkit agents
"""

from typing import Dict, Any, Optional
from agenkit import Agent, Message
from .server import MCPServer
from .client import MCPClient


class MCPAdapter:
    """
    Adapter for integrating Agenkit with MCP.

    Provides bidirectional integration:
    - Expose Agenkit agents as MCP servers
    - Use MCP tools in Agenkit agents
    """

    @staticmethod
    def from_agent(
        agent: Agent,
        server_name: Optional[str] = None,
        capabilities: Optional[Dict[str, Any]] = None
    ) -> MCPServer:
        """
        Convert Agenkit agent to MCP server.

        Exposes the agent as an MCP tool that can be called via MCP protocol.

        Args:
            agent: Agenkit agent to expose
            server_name: Server name (defaults to agent name)
            capabilities: Server capabilities

        Returns:
            MCP server exposing the agent

        Example:
            >>> from agenkit.patterns import ReActAgent
            >>>
            >>> react_agent = ReActAgent(llm=my_llm, tools=[...])
            >>>
            >>> mcp_server = MCPAdapter.from_agent(
            ...     agent=react_agent,
            ...     server_name="my-react-agent"
            ... )
            >>>
            >>> await mcp_server.start(transport="stdio")
        """
        name = server_name or getattr(agent, 'name', 'agenkit-agent')

        server = MCPServer(name=name, capabilities=capabilities)

        # Register agent as a tool
        @server.tool(
            name="process",
            description=f"Process a message with {name}",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Message content to process"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata"
                    }
                },
                "required": ["content"]
            }
        )
        async def process_with_agent(params: Dict[str, Any]) -> Dict[str, Any]:
            """Process message with Agenkit agent."""
            content = params["content"]
            metadata = params.get("metadata", {})

            # Create message
            message = Message(
                role="user",
                content=content,
                metadata=metadata
            )

            # Process with agent
            response = await agent.process(message)

            # Return response
            return {
                "content": response.content,
                "metadata": response.metadata
            }

        # If agent has capabilities, expose them as resources
        if hasattr(agent, 'capabilities'):
            @server.resource(
                uri="agent://capabilities",
                name="Agent Capabilities",
                description="List agent capabilities",
                mime_type="application/json"
            )
            async def get_capabilities(params: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "capabilities": agent.capabilities
                }

        return server

    @staticmethod
    def to_tool(
        client: MCPClient,
        tool_name: str,
        description: Optional[str] = None
    ):
        """
        Convert MCP tool to Agenkit Tool.

        Creates an Agenkit tool that calls an MCP tool via the client.

        Args:
            client: MCP client connected to server
            tool_name: Name of MCP tool to wrap
            description: Tool description

        Returns:
            Agenkit Tool that calls MCP tool

        Example:
            >>> from agenkit.tools import Tool
            >>>
            >>> client = MCPClient("http://localhost:3000/mcp")
            >>> await client.initialize()
            >>>
            >>> search_tool = MCPAdapter.to_tool(
            ...     client=client,
            ...     tool_name="search",
            ...     description="Search the web"
            ... )
            >>>
            >>> # Use in ReAct agent
            >>> agent = ReActAgent(llm=my_llm, tools=[search_tool])
        """
        from agenkit.tools import Tool

        async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
            """Execute MCP tool."""
            result = await client.call_tool(tool_name, **params)
            return {"result": result}

        # Get tool info from client
        # Note: Would need to cache tool schemas for efficiency
        tool = Tool(
            name=tool_name,
            description=description or f"MCP tool: {tool_name}",
            func=execute
        )

        return tool


class AgentMCPServer:
    """
    Convenience wrapper for running an Agenkit agent as MCP server.

    Simplifies the common pattern of exposing an agent via MCP.

    Example:
        >>> from agenkit.patterns import ReActAgent
        >>>
        >>> react_agent = ReActAgent(llm=my_llm, tools=[...])
        >>>
        >>> # Run as MCP server for Claude Desktop
        >>> mcp_wrapper = AgentMCPServer(react_agent)
        >>> await mcp_wrapper.run()  # Uses stdio by default
    """

    def __init__(
        self,
        agent: Agent,
        server_name: Optional[str] = None
    ):
        """
        Initialize agent MCP server.

        Args:
            agent: Agenkit agent to expose
            server_name: Optional server name
        """
        self.agent = agent
        self.server = MCPAdapter.from_agent(agent, server_name)

    async def run(
        self,
        transport: str = "stdio",
        **kwargs
    ):
        """
        Run the MCP server.

        Args:
            transport: Transport type ("stdio", "http", "sse")
            **kwargs: Transport-specific options

        Example:
            >>> # For Claude Desktop (stdio)
            >>> await mcp_wrapper.run()
            >>>
            >>> # For HTTP
            >>> await mcp_wrapper.run(transport="http", port=3000)
        """
        await self.server.start(transport=transport, **kwargs)

    def info(self) -> Dict[str, Any]:
        """Get server info."""
        return self.server.info()
