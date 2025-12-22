"""
Basic Agent-to-Agent (A2A) Communication Example.

Demonstrates:
- Creating A2A-enabled agents
- Sending messages between agents
- Standard protocol actions (ping, capabilities, status)
"""

import asyncio

from agenkit import Message
from agenkit.techniques.protocols.a2a import A2AAction, A2AAgent, A2AServer, create_request

# ==============================================================================
# Simple Echo Agent
# ==============================================================================

class EchoAgent:
    """
    Simple echo agent that returns messages with a prefix.
    """

    def __init__(self, name: str = "echo_agent"):
        self.name = name
        self.capabilities = ["echo", "text-processing"]

    async def process(self, message: Message) -> Message:
        """Echo back the message with a prefix."""
        content = message.content
        response = f"Echo from {self.name}: {content}"

        return Message(
            role="assistant",
            content=response,
            metadata={"echoed": True}
        )


# ==============================================================================
# Example: Basic Communication
# ==============================================================================

async def basic_communication_example():
    """Demonstrate basic A2A communication."""

    print("=" * 70)
    print("Basic A2A Communication Example")
    print("=" * 70)

    # Create echo agent
    echo_agent = EchoAgent(name="echo-001")

    # Wrap as A2A server
    server = A2AServer(
        agent_id="echo-001",
        agent=echo_agent,
        capabilities=["echo", "text-processing"],
        name="Echo Server"
    )

    print("\n1. Starting A2A server...")
    # Note: In real usage, you'd start the server and it would listen for connections
    # For this example, we'll use the server directly

    print(f"   Server: {server.name}")
    print(f"   Agent ID: {server.agent_id}")
    print(f"   Capabilities: {', '.join(server.capabilities)}")

    # Create A2A client agent
    client = A2AAgent(
        agent_id="client-001",
        capabilities=["general"],
        transport="http"
    )

    print(f"\n2. Created client agent: {client.agent_id}")

    # Test ping
    print("\n3. Testing PING action...")
    ping_request = create_request(
        from_agent=client.agent_id,
        to_agent=server.agent_id,
        action=A2AAction.PING.value,
        content={}
    )

    ping_response = await server.handle_message(ping_request)
    print(f"   Response: {ping_response.content}")

    # Test capabilities
    print("\n4. Getting server capabilities...")
    capabilities_request = create_request(
        from_agent=client.agent_id,
        to_agent=server.agent_id,
        action=A2AAction.CAPABILITIES.value,
        content={}
    )

    capabilities_response = await server.handle_message(capabilities_request)
    print(f"   Server capabilities: {capabilities_response.content['capabilities']}")

    # Test status
    print("\n5. Getting server status...")
    status_request = create_request(
        from_agent=client.agent_id,
        to_agent=server.agent_id,
        action=A2AAction.STATUS.value,
        content={}
    )

    status_response = await server.handle_message(status_request)
    print(f"   Status: {status_response.content['status']}")

    # Test process (send message to echo agent)
    print("\n6. Sending message to echo agent...")
    process_request = create_request(
        from_agent=client.agent_id,
        to_agent=server.agent_id,
        action=A2AAction.PROCESS.value,
        content={"text": "Hello, A2A!"}
    )

    process_response = await server.handle_message(process_request)
    print("   Request: Hello, A2A!")
    print(f"   Response: {process_response.content['content']}")

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


# ==============================================================================
# Run Example
# ==============================================================================

if __name__ == "__main__":
    asyncio.run(basic_communication_example())
