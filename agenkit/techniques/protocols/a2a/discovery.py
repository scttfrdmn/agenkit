"""
A2A Discovery Service Client.

Provides agent discovery and registration capabilities.
"""

from typing import List, Optional, Dict, Any
from .message import AgentInfo
from .protocol import validate_capability


class A2ADiscoveryClient:
    """
    Client for A2A discovery service.

    Enables agent registration and capability-based discovery.

    Example:
        >>> discovery = A2ADiscoveryClient("http://discovery:8080")
        >>>
        >>> # Register agent
        >>> agent_info = AgentInfo(
        ...     agent_id="analyzer-001",
        ...     name="Text Analyzer",
        ...     capabilities=["text-analysis", "sentiment"],
        ...     endpoint="http://analyzer:8080/a2a",
        ...     transport="http"
        ... )
        >>> await discovery.register(agent_info)
        >>>
        >>> # Discover agents by capability
        >>> agents = await discovery.discover("summarization")
    """

    def __init__(self, service_url: str, timeout: float = 30.0):
        """
        Initialize discovery client.

        Args:
            service_url: Discovery service URL
            timeout: Request timeout in seconds
        """
        self.service_url = service_url.rstrip('/')
        self.timeout = timeout

    async def register(self, agent_info: AgentInfo):
        """
        Register agent with discovery service.

        Args:
            agent_info: Agent information

        Raises:
            Exception: If registration fails
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for discovery client. "
                "Install with: pip install httpx"
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.service_url}/register",
                json=agent_info.to_dict(),
                timeout=self.timeout
            )
            response.raise_for_status()

    async def unregister(self, agent_id: str):
        """
        Unregister agent from discovery service.

        Args:
            agent_id: Agent identifier

        Raises:
            Exception: If unregistration fails
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for discovery client. "
                "Install with: pip install httpx"
            )

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.service_url}/agents/{agent_id}",
                timeout=self.timeout
            )
            response.raise_for_status()

    async def discover(self, capability: str) -> List[AgentInfo]:
        """
        Discover agents by capability.

        Args:
            capability: Capability to search for

        Returns:
            List of matching agents

        Raises:
            ValueError: If capability format is invalid
        """
        if not validate_capability(capability):
            raise ValueError(f"Invalid capability format: {capability}")

        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for discovery client. "
                "Install with: pip install httpx"
            )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.service_url}/discover",
                params={"capability": capability},
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            agents = data.get("agents", [])

            return [AgentInfo.from_dict(agent) for agent in agents]

    async def find_by_id(self, agent_id: str) -> List[AgentInfo]:
        """
        Find agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            List with matching agent (or empty if not found)
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for discovery client. "
                "Install with: pip install httpx"
            )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.service_url}/agents/{agent_id}",
                    timeout=self.timeout
                )
                response.raise_for_status()

                agent_data = response.json()
                return [AgentInfo.from_dict(agent_data)]

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return []
                raise

    async def list_all(self) -> List[AgentInfo]:
        """
        List all registered agents.

        Returns:
            List of all agents
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for discovery client. "
                "Install with: pip install httpx"
            )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.service_url}/agents",
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            agents = data.get("agents", [])

            return [AgentInfo.from_dict(agent) for agent in agents]

    async def update_status(self, agent_id: str, status: str):
        """
        Update agent status.

        Args:
            agent_id: Agent identifier
            status: New status ("online", "offline", "busy")
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for discovery client. "
                "Install with: pip install httpx"
            )

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.service_url}/agents/{agent_id}/status",
                json={"status": status},
                timeout=self.timeout
            )
            response.raise_for_status()

    async def heartbeat(self, agent_id: str):
        """
        Send heartbeat for agent.

        Args:
            agent_id: Agent identifier
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for discovery client. "
                "Install with: pip install httpx"
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.service_url}/agents/{agent_id}/heartbeat",
                timeout=self.timeout
            )
            response.raise_for_status()


class InMemoryDiscoveryService:
    """
    Simple in-memory discovery service for testing and development.

    Note: This is not suitable for production use. Use a proper
    discovery service (e.g., Consul, etcd, Redis) in production.

    Example:
        >>> service = InMemoryDiscoveryService()
        >>>
        >>> # Register agents
        >>> await service.register(agent_info_1)
        >>> await service.register(agent_info_2)
        >>>
        >>> # Discover
        >>> agents = await service.discover("summarization")
    """

    def __init__(self):
        """Initialize in-memory discovery service."""
        self._agents: Dict[str, AgentInfo] = {}
        self._capability_index: Dict[str, List[str]] = {}  # capability -> [agent_ids]

    async def register(self, agent_info: AgentInfo):
        """Register agent."""
        agent_id = agent_info.agent_id

        # Store agent
        self._agents[agent_id] = agent_info

        # Index by capabilities
        for capability in agent_info.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            if agent_id not in self._capability_index[capability]:
                self._capability_index[capability].append(agent_id)

    async def unregister(self, agent_id: str):
        """Unregister agent."""
        if agent_id in self._agents:
            agent_info = self._agents[agent_id]

            # Remove from capability index
            for capability in agent_info.capabilities:
                if capability in self._capability_index:
                    if agent_id in self._capability_index[capability]:
                        self._capability_index[capability].remove(agent_id)

            # Remove agent
            del self._agents[agent_id]

    async def discover(self, capability: str) -> List[AgentInfo]:
        """Discover agents by capability."""
        if capability not in self._capability_index:
            return []

        agent_ids = self._capability_index[capability]
        return [self._agents[agent_id] for agent_id in agent_ids if agent_id in self._agents]

    async def find_by_id(self, agent_id: str) -> List[AgentInfo]:
        """Find agent by ID."""
        if agent_id in self._agents:
            return [self._agents[agent_id]]
        return []

    async def list_all(self) -> List[AgentInfo]:
        """List all agents."""
        return list(self._agents.values())

    async def update_status(self, agent_id: str, status: str):
        """Update agent status."""
        if agent_id in self._agents:
            self._agents[agent_id].status = status

    async def heartbeat(self, agent_id: str):
        """Receive heartbeat."""
        # In production, this would update last_seen timestamp
        # For in-memory service, just ensure agent exists
        if agent_id not in self._agents:
            raise KeyError(f"Agent not found: {agent_id}")

    def clear(self):
        """Clear all registrations (for testing)."""
        self._agents.clear()
        self._capability_index.clear()
