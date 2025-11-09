"""Tests for agent registry."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from agenkit.adapters.python import AgentRegistration, AgentRegistry, heartbeat_loop


@pytest.mark.asyncio
class TestAgentRegistry:
    """Tests for AgentRegistry."""

    async def test_register_agent(self):
        """Test registering an agent."""
        registry = AgentRegistry()

        registration = AgentRegistration(
            name="test_agent",
            endpoint="unix:///tmp/test.sock",
            capabilities={"streaming": True},
            metadata={"version": "1.0.0"},
        )

        await registry.register(registration)

        # Should be able to look up the agent
        found = await registry.lookup("test_agent")
        assert found is not None
        assert found.name == "test_agent"
        assert found.endpoint == "unix:///tmp/test.sock"
        assert found.capabilities == {"streaming": True}
        assert found.metadata == {"version": "1.0.0"}

    async def test_register_duplicate_agent(self):
        """Test re-registering an agent updates it."""
        registry = AgentRegistry()

        # Register first time
        registration1 = AgentRegistration(
            name="agent",
            endpoint="unix:///tmp/v1.sock",
            metadata={"version": "1.0"},
        )
        await registry.register(registration1)

        # Register again with different endpoint
        registration2 = AgentRegistration(
            name="agent",
            endpoint="unix:///tmp/v2.sock",
            metadata={"version": "2.0"},
        )
        await registry.register(registration2)

        # Should have the new registration
        found = await registry.lookup("agent")
        assert found is not None
        assert found.endpoint == "unix:///tmp/v2.sock"
        assert found.metadata == {"version": "2.0"}

    async def test_register_empty_name(self):
        """Test registering agent with empty name raises error."""
        registry = AgentRegistry()

        registration = AgentRegistration(name="", endpoint="unix:///tmp/test.sock")

        with pytest.raises(ValueError) as exc_info:
            await registry.register(registration)

        assert "name" in str(exc_info.value).lower()

    async def test_unregister_agent(self):
        """Test unregistering an agent."""
        registry = AgentRegistry()

        registration = AgentRegistration(name="agent", endpoint="unix:///tmp/test.sock")
        await registry.register(registration)

        # Agent should exist
        assert await registry.lookup("agent") is not None

        # Unregister
        await registry.unregister("agent")

        # Agent should be gone
        assert await registry.lookup("agent") is None

    async def test_unregister_nonexistent_agent(self):
        """Test unregistering non-existent agent doesn't raise error."""
        registry = AgentRegistry()

        # Should not raise
        await registry.unregister("nonexistent")

    async def test_lookup_nonexistent_agent(self):
        """Test looking up non-existent agent returns None."""
        registry = AgentRegistry()

        found = await registry.lookup("nonexistent")
        assert found is None

    async def test_list_agents(self):
        """Test listing all registered agents."""
        registry = AgentRegistry()

        # Initially empty
        agents = await registry.list_agents()
        assert len(agents) == 0

        # Register some agents
        for i in range(3):
            registration = AgentRegistration(
                name=f"agent{i}", endpoint=f"unix:///tmp/agent{i}.sock"
            )
            await registry.register(registration)

        # Should list all agents
        agents = await registry.list_agents()
        assert len(agents) == 3
        agent_names = {agent.name for agent in agents}
        assert agent_names == {"agent0", "agent1", "agent2"}

    async def test_heartbeat(self):
        """Test updating agent heartbeat."""
        registry = AgentRegistry()

        registration = AgentRegistration(name="agent", endpoint="unix:///tmp/test.sock")
        await registry.register(registration)

        # Get initial heartbeat time
        found = await registry.lookup("agent")
        assert found is not None
        initial_heartbeat = found.last_heartbeat

        # Wait a bit
        await asyncio.sleep(0.1)

        # Send heartbeat
        await registry.heartbeat("agent")

        # Heartbeat should be updated
        found = await registry.lookup("agent")
        assert found is not None
        assert found.last_heartbeat > initial_heartbeat

    async def test_heartbeat_unregistered_agent(self):
        """Test heartbeat for unregistered agent raises error."""
        registry = AgentRegistry()

        with pytest.raises(KeyError):
            await registry.heartbeat("nonexistent")

    async def test_prune_stale_agents(self):
        """Test pruning agents with expired heartbeats."""
        # Use short timeout for testing
        registry = AgentRegistry(heartbeat_timeout=0.2)

        # Register agents
        for i in range(3):
            registration = AgentRegistration(
                name=f"agent{i}", endpoint=f"unix:///tmp/agent{i}.sock"
            )
            await registry.register(registration)

        # Send heartbeat to agent1 only
        await asyncio.sleep(0.1)
        await registry.heartbeat("agent1")

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Prune stale agents
        pruned = await registry.prune_stale_agents()

        # agent0 and agent2 should be pruned (no recent heartbeat)
        # agent1 should remain (recent heartbeat)
        assert pruned == 2
        assert await registry.lookup("agent0") is None
        assert await registry.lookup("agent1") is not None
        assert await registry.lookup("agent2") is None

    async def test_prune_no_stale_agents(self):
        """Test pruning when no agents are stale."""
        registry = AgentRegistry(heartbeat_timeout=1.0)

        registration = AgentRegistration(name="agent", endpoint="unix:///tmp/test.sock")
        await registry.register(registration)

        # Immediately prune - agent should not be stale
        pruned = await registry.prune_stale_agents()
        assert pruned == 0
        assert await registry.lookup("agent") is not None

    async def test_registry_start_stop(self):
        """Test starting and stopping registry."""
        registry = AgentRegistry(heartbeat_timeout=0.5)

        # Start registry
        await registry.start()

        # Register agent
        registration = AgentRegistration(name="agent", endpoint="unix:///tmp/test.sock")
        await registry.register(registration)

        # Wait for potential prune cycle
        await asyncio.sleep(0.1)

        # Agent should still exist (not stale yet)
        assert await registry.lookup("agent") is not None

        # Stop registry
        await registry.stop()

    async def test_len(self):
        """Test getting number of registered agents."""
        registry = AgentRegistry()

        assert len(registry) == 0

        # Register some agents
        for i in range(5):
            registration = AgentRegistration(name=f"agent{i}", endpoint=f"unix:///tmp/{i}.sock")
            await registry.register(registration)

        assert len(registry) == 5

        # Unregister one
        await registry.unregister("agent2")
        assert len(registry) == 4

    async def test_concurrent_operations(self):
        """Test concurrent registry operations are safe."""
        registry = AgentRegistry()

        # Register agents concurrently
        async def register_agent(i: int) -> None:
            registration = AgentRegistration(name=f"agent{i}", endpoint=f"unix:///tmp/{i}.sock")
            await registry.register(registration)

        await asyncio.gather(*[register_agent(i) for i in range(10)])

        # All agents should be registered
        assert len(registry) == 10

        # Concurrent lookups
        results = await asyncio.gather(*[registry.lookup(f"agent{i}") for i in range(10)])
        assert all(r is not None for r in results)

        # Concurrent heartbeats
        await asyncio.gather(*[registry.heartbeat(f"agent{i}") for i in range(10)])


@pytest.mark.asyncio
class TestHeartbeatLoop:
    """Tests for heartbeat_loop function."""

    async def test_heartbeat_loop_sends_heartbeats(self):
        """Test that heartbeat loop sends periodic heartbeats."""
        registry = AgentRegistry()

        registration = AgentRegistration(name="agent", endpoint="unix:///tmp/test.sock")
        await registry.register(registration)

        # Get initial heartbeat
        found = await registry.lookup("agent")
        assert found is not None
        initial_heartbeat = found.last_heartbeat

        # Start heartbeat loop with short interval
        heartbeat_task = asyncio.create_task(heartbeat_loop(registry, "agent", interval=0.1))

        try:
            # Wait for a few heartbeats
            await asyncio.sleep(0.35)

            # Heartbeat should be updated
            found = await registry.lookup("agent")
            assert found is not None
            assert found.last_heartbeat > initial_heartbeat

        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    async def test_heartbeat_loop_stops_when_unregistered(self):
        """Test that heartbeat loop stops when agent is unregistered."""
        registry = AgentRegistry()

        registration = AgentRegistration(name="agent", endpoint="unix:///tmp/test.sock")
        await registry.register(registration)

        # Start heartbeat loop
        heartbeat_task = asyncio.create_task(heartbeat_loop(registry, "agent", interval=0.1))

        # Wait a bit
        await asyncio.sleep(0.15)

        # Unregister agent
        await registry.unregister("agent")

        # Wait a bit more - heartbeat loop should detect and stop
        await asyncio.sleep(0.15)

        # Task should be done
        assert heartbeat_task.done()
