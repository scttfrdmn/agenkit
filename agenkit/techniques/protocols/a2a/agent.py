"""
A2A Agent Implementation.

Provides agent capabilities for sending/receiving A2A messages.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from .message import A2AMessage, AgentInfo, create_request
from .protocol import A2AAction, AgentNotFoundError, validate_agent_id
from .transport import Transport, create_transport


class A2AAgent:
    """
    Agent-to-Agent protocol agent.

    Enables agents to send/receive messages and participate in A2A network.

    Example:
        >>> agent = A2AAgent(
        ...     agent_id="analyzer-001",
        ...     capabilities=["text-analysis", "sentiment"],
        ...     transport="http"
        ... )
        >>>
        >>> # Send message to another agent
        >>> message = create_request(
        ...     from_agent=agent.agent_id,
        ...     to_agent="summarizer-001",
        ...     action="summarize",
        ...     content={"text": "Document..."}
        ... )
        >>> response = await agent.send(message, "http://summarizer:8080/a2a")
    """

    def __init__(
        self,
        agent_id: str,
        capabilities: list[str],
        transport: str = "http",
        name: str | None = None,
        discovery_url: str | None = None,
        timeout: float = 30.0,
    ):
        """
        Initialize A2A agent.

        Args:
            agent_id: Unique agent identifier
            capabilities: List of capabilities
            transport: Transport type ("http", "websocket", "grpc")
            name: Optional human-readable name
            discovery_url: Optional discovery service URL
            timeout: Request timeout in seconds

        Raises:
            ValueError: If agent_id is invalid
        """
        if not validate_agent_id(agent_id):
            raise ValueError(f"Invalid agent ID: {agent_id}")

        self.agent_id = agent_id
        self.name = name or agent_id
        self.capabilities = capabilities
        self.transport_type = transport
        self.discovery_url = discovery_url
        self.timeout = timeout

        # Create transport
        self.transport: Transport = create_transport(transport, timeout=timeout)

        # Known agents cache
        self._known_agents: dict[str, AgentInfo] = {}

        # Message handlers
        self._handlers: dict[str, Callable[[A2AMessage], Awaitable[A2AMessage]]] = {}

    def info(self) -> AgentInfo:
        """
        Get agent information.

        Returns:
            AgentInfo object
        """
        return AgentInfo(
            agent_id=self.agent_id,
            name=self.name,
            capabilities=self.capabilities,
            endpoint="",  # Set by server
            transport=self.transport_type,
            status="online",
        )

    async def send(self, message: A2AMessage, endpoint: str) -> A2AMessage:
        """
        Send message to another agent.

        Args:
            message: Message to send
            endpoint: Destination endpoint URL

        Returns:
            Response message

        Raises:
            TimeoutError: If request times out
            Exception: If send fails
        """
        # Ensure from_agent is set
        if not message.from_agent:
            message.from_agent = self.agent_id

        # Send via transport
        response = await self.transport.send(message, endpoint)

        return response

    async def send_to_agent(
        self, to_agent: str, action: str, content: dict[str, Any], **kwargs
    ) -> A2AMessage:
        """
        Send message to agent by ID.

        Args:
            to_agent: Target agent ID
            action: Action to perform
            content: Message content
            **kwargs: Additional message parameters

        Returns:
            Response message

        Raises:
            AgentNotFoundError: If agent not found
        """
        # Look up agent endpoint
        if to_agent not in self._known_agents:
            # Try discovery if available
            if self.discovery_url:
                from .discovery import A2ADiscoveryClient

                discovery = A2ADiscoveryClient(self.discovery_url)
                agents = await discovery.find_by_id(to_agent)
                if agents:
                    self._known_agents[to_agent] = agents[0]
                else:
                    raise AgentNotFoundError(to_agent)
            else:
                raise AgentNotFoundError(to_agent)

        agent_info = self._known_agents[to_agent]

        # Create message
        message = create_request(
            from_agent=self.agent_id, to_agent=to_agent, action=action, content=content, **kwargs
        )

        # Send to endpoint
        return await self.send(message, agent_info.endpoint)

    def add_agent(self, agent_info: AgentInfo):
        """
        Add agent to known agents.

        Args:
            agent_info: Agent information
        """
        self._known_agents[agent_info.agent_id] = agent_info

    def on_action(self, action: str, handler: Callable[[A2AMessage], Awaitable[A2AMessage]]):
        """
        Register handler for action.

        Args:
            action: Action name
            handler: Handler function

        Example:
            >>> @agent.on_action("summarize")
            >>> async def handle_summarize(message):
            ...     # Process message
            ...     return message.create_response({"summary": "..."})
        """
        self._handlers[action] = handler

    async def handle_message(self, message: A2AMessage) -> A2AMessage:
        """
        Handle incoming message.

        Args:
            message: Incoming message

        Returns:
            Response message
        """
        # Check if we have a handler for this action
        if message.action in self._handlers:
            handler = self._handlers[message.action]
            return await handler(message)

        # Default: echo back
        return message.create_response(
            {"message": "No handler registered", "action": message.action}
        )

    async def ping(self, endpoint: str) -> float:
        """
        Ping another agent.

        Args:
            endpoint: Agent endpoint

        Returns:
            Round-trip latency in milliseconds
        """
        import time

        message = create_request(
            from_agent=self.agent_id,
            to_agent="",  # Will be filled by server
            action=A2AAction.PING.value,
            content={},
        )

        start = time.time()
        await self.send(message, endpoint)
        latency_ms = (time.time() - start) * 1000

        return latency_ms

    async def get_capabilities(self, endpoint: str) -> list[str]:
        """
        Get capabilities from another agent.

        Args:
            endpoint: Agent endpoint

        Returns:
            List of capabilities
        """
        message = create_request(
            from_agent=self.agent_id, to_agent="", action=A2AAction.CAPABILITIES.value, content={}
        )

        response = await self.send(message, endpoint)
        return response.content.get("capabilities", [])

    async def discover(self, capability: str) -> list[AgentInfo]:
        """
        Discover agents by capability.

        Args:
            capability: Capability to search for

        Returns:
            List of matching agents

        Raises:
            ValueError: If discovery service not configured
        """
        if not self.discovery_url:
            raise ValueError("Discovery service not configured")

        from .discovery import A2ADiscoveryClient

        discovery = A2ADiscoveryClient(self.discovery_url)
        agents = await discovery.discover(capability)

        # Cache discovered agents
        for agent in agents:
            self._known_agents[agent.agent_id] = agent

        return agents

    async def register_discovery(self, endpoint: str):
        """
        Register with discovery service.

        Args:
            endpoint: This agent's endpoint

        Raises:
            ValueError: If discovery service not configured
        """
        if not self.discovery_url:
            raise ValueError("Discovery service not configured")

        from .discovery import A2ADiscoveryClient

        discovery = A2ADiscoveryClient(self.discovery_url)

        info = AgentInfo(
            agent_id=self.agent_id,
            name=self.name,
            capabilities=self.capabilities,
            endpoint=endpoint,
            transport=self.transport_type,
            status="online",
        )

        await discovery.register(info)

    async def unregister_discovery(self):
        """
        Unregister from discovery service.

        Raises:
            ValueError: If discovery service not configured
        """
        if not self.discovery_url:
            raise ValueError("Discovery service not configured")

        from .discovery import A2ADiscoveryClient

        discovery = A2ADiscoveryClient(self.discovery_url)
        await discovery.unregister(self.agent_id)
