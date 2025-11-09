"""Agent registry for discovery and health monitoring."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentRegistration:
    """Agent registration information."""

    name: str
    endpoint: str  # e.g., "unix:///tmp/agent.sock" or "tcp://localhost:8080"
    capabilities: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AgentRegistry:
    """Central registry for agent discovery and health monitoring.

    This is an in-process registry suitable for single-process scenarios
    and testing. For production distributed systems, use a Redis or etcd
    backed registry.
    """

    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 90.0,
    ):
        """Initialize agent registry.

        Args:
            heartbeat_interval: Expected interval between heartbeats (seconds)
            heartbeat_timeout: Time before marking agent as stale (seconds)
        """
        self._agents: dict[str, AgentRegistration] = {}
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_timeout = heartbeat_timeout
        self._lock = asyncio.Lock()
        self._prune_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the registry and background tasks."""
        if self._prune_task is None:
            self._prune_task = asyncio.create_task(self._prune_loop())
            logger.info("Agent registry started")

    async def stop(self) -> None:
        """Stop the registry and background tasks."""
        if self._prune_task:
            self._prune_task.cancel()
            try:
                await self._prune_task
            except asyncio.CancelledError:
                pass
            self._prune_task = None
            logger.info("Agent registry stopped")

    async def register(self, registration: AgentRegistration) -> None:
        """Register an agent.

        Args:
            registration: Agent registration information

        Raises:
            ValueError: If agent name is empty
        """
        if not registration.name:
            raise ValueError("Agent name cannot be empty")

        async with self._lock:
            if registration.name in self._agents:
                # Update existing registration
                logger.info(f"Re-registering agent: {registration.name}")
            else:
                logger.info(f"Registering new agent: {registration.name}")

            self._agents[registration.name] = registration

    async def unregister(self, agent_name: str) -> None:
        """Unregister an agent.

        Args:
            agent_name: Name of agent to unregister
        """
        async with self._lock:
            if agent_name in self._agents:
                del self._agents[agent_name]
                logger.info(f"Unregistered agent: {agent_name}")
            else:
                logger.warning(f"Attempted to unregister unknown agent: {agent_name}")

    async def lookup(self, agent_name: str) -> AgentRegistration | None:
        """Find an agent by name.

        Args:
            agent_name: Name of agent to find

        Returns:
            Agent registration if found, None otherwise
        """
        async with self._lock:
            return self._agents.get(agent_name)

    async def list_agents(self) -> list[AgentRegistration]:
        """List all registered agents.

        Returns:
            List of all agent registrations
        """
        async with self._lock:
            return list(self._agents.values())

    async def heartbeat(self, agent_name: str) -> None:
        """Update agent heartbeat timestamp.

        Args:
            agent_name: Name of agent sending heartbeat

        Raises:
            KeyError: If agent is not registered
        """
        async with self._lock:
            if agent_name not in self._agents:
                raise KeyError(f"Agent '{agent_name}' is not registered")

            self._agents[agent_name].last_heartbeat = datetime.now(timezone.utc)
            logger.debug(f"Heartbeat received from agent: {agent_name}")

    async def prune_stale_agents(self) -> int:
        """Remove agents with expired heartbeats.

        Returns:
            Number of agents pruned
        """
        now = datetime.now(timezone.utc)
        pruned = 0

        async with self._lock:
            stale_agents = []

            for name, registration in self._agents.items():
                time_since_heartbeat = (now - registration.last_heartbeat).total_seconds()
                if time_since_heartbeat > self._heartbeat_timeout:
                    stale_agents.append(name)

            for name in stale_agents:
                del self._agents[name]
                logger.warning(
                    f"Pruned stale agent: {name} "
                    f"(no heartbeat for {time_since_heartbeat:.1f}s)"
                )
                pruned += 1

        return pruned

    async def _prune_loop(self) -> None:
        """Background task to periodically prune stale agents."""
        while True:
            try:
                await asyncio.sleep(60.0)  # Check every minute
                pruned = await self.prune_stale_agents()
                if pruned > 0:
                    logger.info(f"Pruned {pruned} stale agent(s)")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in prune loop: {e}", exc_info=True)

    def __len__(self) -> int:
        """Get number of registered agents.

        Returns:
            Number of registered agents
        """
        return len(self._agents)


async def heartbeat_loop(
    registry: AgentRegistry, agent_name: str, interval: float = 30.0
) -> None:
    """Background task to send periodic heartbeats.

    Args:
        registry: Agent registry to send heartbeats to
        agent_name: Name of agent sending heartbeats
        interval: Interval between heartbeats (seconds)
    """
    while True:
        try:
            await registry.heartbeat(agent_name)
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except KeyError:
            # Agent not registered - stop sending heartbeats
            logger.warning(f"Agent {agent_name} not registered, stopping heartbeats")
            break
        except Exception as e:
            logger.error(f"Heartbeat failed for {agent_name}: {e}")
            # Retry quickly
            await asyncio.sleep(5.0)
