"""Agent registry example.

This example demonstrates how to use the agent registry for agent discovery
and health monitoring.
"""

import asyncio
import tempfile
from pathlib import Path

from agenkit import Agent, Message
from agenkit.adapters.python import (
    AgentRegistration,
    AgentRegistry,
    LocalAgent,
    RemoteAgent,
    heartbeat_loop,
)


class MathAgent(Agent):
    """Agent that does math operations."""

    @property
    def name(self) -> str:
        return "math"

    async def process(self, message: Message) -> Message:
        """Process math request."""
        try:
            # Simple eval (don't do this in production!)
            result = eval(message.content)
            return Message(role="agent", content=f"Result: {result}")
        except Exception as e:
            return Message(role="agent", content=f"Error: {e}")


class EchoAgent(Agent):
    """Agent that echoes messages."""

    @property
    def name(self) -> str:
        return "echo"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Echo: {message.content}")


async def main() -> None:
    """Run the example."""
    print("=== Agent Registry Example ===\n")

    # Create temporary directory for sockets
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # 1. Create registry
        print("1. Creating registry...")
        registry = AgentRegistry(heartbeat_interval=10.0, heartbeat_timeout=30.0)
        await registry.start()
        print("   Registry started\n")

        # 2. Start agents and register them
        print("2. Starting and registering agents...")

        # Start math agent
        math_agent = MathAgent()
        math_socket = tmppath / "math.sock"
        math_server = LocalAgent(math_agent, endpoint=f"unix://{math_socket}")
        await math_server.start()

        # Register math agent
        await registry.register(
            AgentRegistration(
                name="math",
                endpoint=f"unix://{math_socket}",
                capabilities={"operations": ["add", "subtract", "multiply", "divide"]},
                metadata={"version": "1.0.0", "language": "python"},
            )
        )
        print("   Registered: math agent")

        # Start echo agent
        echo_agent = EchoAgent()
        echo_socket = tmppath / "echo.sock"
        echo_server = LocalAgent(echo_agent, endpoint=f"unix://{echo_socket}")
        await echo_server.start()

        # Register echo agent
        await registry.register(
            AgentRegistration(
                name="echo",
                endpoint=f"unix://{echo_socket}",
                capabilities={"streaming": False},
                metadata={"version": "1.0.0"},
            )
        )
        print("   Registered: echo agent\n")

        # 3. List all agents
        print("3. Listing all agents:")
        agents = await registry.list_agents()
        for agent in agents:
            print(f"   - {agent.name}: {agent.endpoint}")
            print(f"     Capabilities: {agent.capabilities}")
            print(f"     Metadata: {agent.metadata}")
        print()

        # 4. Discover and use agents
        print("4. Discovering and using agents...\n")

        # Look up math agent
        math_reg = await registry.lookup("math")
        if math_reg:
            print(f"   Found math agent at: {math_reg.endpoint}")
            remote_math = RemoteAgent("math", endpoint=math_reg.endpoint)
            response = await remote_math.process(Message(role="user", content="2 + 2"))
            print(f"   Math result: {response.content}\n")

        # Look up echo agent
        echo_reg = await registry.lookup("echo")
        if echo_reg:
            print(f"   Found echo agent at: {echo_reg.endpoint}")
            remote_echo = RemoteAgent("echo", endpoint=echo_reg.endpoint)
            response = await remote_echo.process(Message(role="user", content="Hello!"))
            print(f"   Echo result: {response.content}\n")

        # 5. Start heartbeat loops for health monitoring
        print("5. Starting heartbeat monitoring...")
        math_heartbeat_task = asyncio.create_task(heartbeat_loop(registry, "math", interval=5.0))
        echo_heartbeat_task = asyncio.create_task(heartbeat_loop(registry, "echo", interval=5.0))
        print("   Heartbeats started\n")

        # Wait a bit to see heartbeats
        await asyncio.sleep(1.0)

        # 6. Verify agents are healthy
        print("6. Checking agent health...")
        agents = await registry.list_agents()
        for agent in agents:
            time_since_heartbeat = (
                asyncio.get_event_loop().time() - agent.last_heartbeat.timestamp()
            )
            print(f"   {agent.name}: last heartbeat {time_since_heartbeat:.1f}s ago")
        print()

        # 7. Simulate agent failure by unregistering
        print("7. Simulating agent failure (unregister math agent)...")
        await registry.unregister("math")
        print("   Math agent unregistered\n")

        # 8. Try to look up failed agent
        print("8. Attempting to find unregistered agent...")
        math_reg = await registry.lookup("math")
        if math_reg is None:
            print("   Math agent not found (as expected)\n")

        # 9. Prune stale agents
        print("9. Pruning stale agents...")
        pruned = await registry.prune_stale_agents()
        print(f"   Pruned {pruned} stale agent(s)\n")

        # 10. Final agent list
        print("10. Final agent list:")
        agents = await registry.list_agents()
        for agent in agents:
            print(f"   - {agent.name}")
        print()

        # Clean up
        print("Cleaning up...")
        math_heartbeat_task.cancel()
        echo_heartbeat_task.cancel()
        try:
            await asyncio.gather(math_heartbeat_task, echo_heartbeat_task)
        except asyncio.CancelledError:
            pass

        await math_server.stop()
        await echo_server.stop()
        await registry.stop()
        print("Done!\n")


if __name__ == "__main__":
    asyncio.run(main())
