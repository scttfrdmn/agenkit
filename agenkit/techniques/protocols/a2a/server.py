"""
A2A Server Implementation.

Exposes Agenkit agents via A2A protocol.
"""

import asyncio
from typing import TYPE_CHECKING

from .message import A2AMessage, AgentInfo
from .protocol import (A2AAction, create_capabilities_response,
                       create_ping_response, create_status_response)
from .transport import Transport, create_transport

if TYPE_CHECKING:
    from agenkit import Agent


class A2AServer:
    """
    A2A Server for exposing Agenkit agents.

    Handles incoming A2A messages and routes them to the wrapped agent.

    Example:
        >>> from agenkit.patterns import ReActAgent
        >>> from agenkit.techniques.protocols.a2a import A2AServer
        >>>
        >>> # Create agent
        >>> agent = ReActAgent(llm=my_llm, tools=[...])
        >>>
        >>> # Wrap as A2A server
        >>> server = A2AServer(
        ...     agent_id="react-agent-001",
        ...     agent=agent,
        ...     capabilities=["question-answering", "reasoning"]
        ... )
        >>>
        >>> # Start server
        >>> await server.start(transport="http", port=8080)
    """

    def __init__(
        self,
        agent_id: str,
        agent: "Agent",
        capabilities: list[str],
        name: str | None = None,
        transport: str = "http",
    ):
        """
        Initialize A2A server.

        Args:
            agent_id: Unique agent identifier
            agent: Agenkit agent to expose
            capabilities: List of capabilities
            name: Optional human-readable name
            transport: Transport type
        """
        self.agent_id = agent_id
        self.agent = agent
        self.capabilities = capabilities
        self.name = name or agent_id
        self.transport_type = transport

        self.transport: Transport | None = None
        self.running = False
        self._stop_event = asyncio.Event()

    def info(self) -> AgentInfo:
        """
        Get server information.

        Returns:
            AgentInfo object
        """
        return AgentInfo(
            agent_id=self.agent_id,
            name=self.name,
            capabilities=self.capabilities,
            endpoint="",  # Set when starting
            transport=self.transport_type,
            status="online" if self.running else "offline",
        )

    async def handle_message(self, message: A2AMessage) -> A2AMessage:
        """
        Handle incoming A2A message.

        Args:
            message: Incoming message

        Returns:
            Response message
        """
        try:
            action = message.action

            # Handle standard actions
            if action == A2AAction.PING.value:
                return await self._handle_ping(message)
            elif action == A2AAction.CAPABILITIES.value:
                return await self._handle_capabilities(message)
            elif action == A2AAction.STATUS.value:
                return await self._handle_status(message)
            elif action == A2AAction.PROCESS.value:
                return await self._handle_process(message)
            else:
                # Default: process with agent
                return await self._handle_process(message)

        except Exception as e:
            return message.create_error(error_code="500", error_message=f"Server error: {e!s}")

    async def _handle_ping(self, message: A2AMessage) -> A2AMessage:
        """Handle ping request."""
        response_data = create_ping_response(self.agent_id)
        return message.create_response(response_data)

    async def _handle_capabilities(self, message: A2AMessage) -> A2AMessage:
        """Handle capabilities request."""
        response_data = create_capabilities_response(self.capabilities)
        return message.create_response(response_data)

    async def _handle_status(self, message: A2AMessage) -> A2AMessage:
        """Handle status request."""
        response_data = create_status_response(
            status="online" if self.running else "offline", agent_id=self.agent_id
        )
        return message.create_response(response_data)

    async def _handle_process(self, message: A2AMessage) -> A2AMessage:
        """
        Handle process request by forwarding to agent.

        Args:
            message: A2A message

        Returns:
            Response message
        """
        # Convert A2A message to Agenkit message
        agenkit_message = message.to_agenkit_message()

        # Process with agent
        agent_response = await self.agent.process(agenkit_message)

        # Convert back to A2A
        response_content = {
            "role": agent_response.role,
            "content": agent_response.content,
            "metadata": agent_response.metadata or {},
        }

        return message.create_response(response_content)

    async def start(
        self,
        transport: str | None = None,
        host: str = "0.0.0.0",  # noqa: S104 - Server must bind to all interfaces for deployment
        port: int = 8080,
        **kwargs,
    ):
        """
        Start A2A server.

        Args:
            transport: Transport type (uses server default if not specified)
            host: Host to bind to
            port: Port to bind to
            **kwargs: Additional transport options
        """
        transport_type = transport or self.transport_type

        self.transport = create_transport(transport_type)

        # Start transport server with message handler
        await self.transport.start_server(handler=self.handle_message, host=host, port=port)

        self.running = True

        print(f"A2A Server '{self.name}' (ID: {self.agent_id}) started")
        print(f"Capabilities: {', '.join(self.capabilities)}")

    async def stop(self):
        """Stop A2A server."""
        if self.transport:
            await self.transport.stop_server()
            self.running = False
            self._stop_event.set()
            print(f"A2A Server '{self.name}' stopped")


class AgentA2AServer:
    """
    Convenience wrapper for running an Agenkit agent as A2A server.

    Simplifies the common pattern of exposing an agent via A2A.

    Example:
        >>> from agenkit.patterns import ReActAgent
        >>> from agenkit.techniques.protocols.a2a import AgentA2AServer
        >>>
        >>> agent = ReActAgent(llm=my_llm, tools=[...])
        >>>
        >>> server = AgentA2AServer(
        ...     agent=agent,
        ...     agent_id="react-001",
        ...     capabilities=["question-answering"]
        ... )
        >>>
        >>> await server.run(transport="http", port=8080)
    """

    def __init__(
        self,
        agent: "Agent",
        agent_id: str | None = None,
        capabilities: list[str] | None = None,
        server_name: str | None = None,
    ):
        """
        Initialize agent A2A server wrapper.

        Args:
            agent: Agenkit agent
            agent_id: Optional agent ID (defaults to agent.name)
            capabilities: Optional capabilities (defaults to agent.capabilities)
            server_name: Optional server name
        """
        self.agent = agent

        # Generate agent_id from agent name
        if agent_id is None:
            agent_id = getattr(agent, "name", "agenkit-agent")
            # Make it A2A compliant (alphanumeric + hyphens)
            agent_id = agent_id.replace("_", "-").replace(" ", "-").lower()

        # Get capabilities from agent if available
        if capabilities is None:
            capabilities = getattr(agent, "capabilities", ["general"])

        # Create server
        self.server = A2AServer(
            agent_id=agent_id, agent=agent, capabilities=capabilities, name=server_name or agent_id
        )

    async def run(
        self,
        transport: str = "http",
        host: str = "0.0.0.0",  # noqa: S104 - Server must bind to all interfaces for deployment
        port: int = 8080,
        **kwargs,
    ):
        """
        Run server.

        Args:
            transport: Transport type
            host: Host to bind to
            port: Port to bind to
            **kwargs: Additional options
        """
        await self.server.start(transport=transport, host=host, port=port, **kwargs)

        # Keep running until stop event is set
        try:
            await self.server._stop_event.wait()
        except KeyboardInterrupt:
            await self.server.stop()

    def info(self) -> dict:
        """Get server info."""
        info = self.server.info()
        return {
            "agent_id": info.agent_id,
            "name": info.name,
            "capabilities": info.capabilities,
            "transport": info.transport,
            "status": info.status,
        }
