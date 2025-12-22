"""
Custom Message Handlers Example.

Demonstrates:
- Registering custom action handlers
- Handling different message types
- Agent collaboration via custom actions
- Error handling and responses
"""

import asyncio

from agenkit import Message
from agenkit.techniques.protocols.a2a import (A2AAgent, AgentInfo,
                                              InMemoryDiscoveryService,
                                              create_notification,
                                              create_request)

# ==============================================================================
# Agent with Custom Handlers
# ==============================================================================


class DataProcessingAgent:
    """
    Agent with custom handlers for different data operations.
    """

    def __init__(self):
        self.name = "data_processor"
        self.capabilities = ["data-processing", "aggregation", "validation"]
        self.data_store = {}

    async def process(self, message: Message) -> Message:
        """Default process method."""
        return Message(
            role="assistant",
            content="Please use specific actions: store, retrieve, aggregate",
            metadata={},
        )


# ==============================================================================
# Example: Custom Handlers
# ==============================================================================


async def custom_handlers_example():
    """Demonstrate custom message handlers."""

    print("=" * 70)
    print("Custom Message Handlers Example")
    print("=" * 70)

    # Create agent
    agent = DataProcessingAgent()

    # Create A2A agent wrapper
    a2a_agent = A2AAgent(
        agent_id="processor-001", capabilities=agent.capabilities, transport="http"
    )

    print("\n1. Registering custom action handlers...")

    # Register custom handlers
    @a2a_agent.on_action("store")
    async def handle_store(message):
        """Store data."""
        data = message.content.get("data", {})
        key = message.content.get("key", "default")

        # Store in agent's data store
        agent.data_store[key] = data

        print(f"   [HANDLER] Stored data with key: {key}")

        return message.create_response({"status": "stored", "key": key, "size": len(str(data))})

    @a2a_agent.on_action("retrieve")
    async def handle_retrieve(message):
        """Retrieve stored data."""
        key = message.content.get("key", "default")

        # Retrieve from data store
        data = agent.data_store.get(key)

        if data is None:
            print(f"   [HANDLER] Key not found: {key}")
            return message.create_error(error_code="404", error_message=f"Key not found: {key}")

        print(f"   [HANDLER] Retrieved data for key: {key}")

        return message.create_response({"status": "retrieved", "key": key, "data": data})

    @a2a_agent.on_action("aggregate")
    async def handle_aggregate(message):
        """Aggregate all stored data."""
        total_items = len(agent.data_store)
        total_size = sum(len(str(v)) for v in agent.data_store.values())

        print(f"   [HANDLER] Aggregated {total_items} items")

        return message.create_response(
            {
                "status": "aggregated",
                "total_items": total_items,
                "total_size": total_size,
                "keys": list(agent.data_store.keys()),
            }
        )

    print("   Registered handlers: store, retrieve, aggregate")

    # Create discovery service
    discovery = InMemoryDiscoveryService()

    # Register agent
    agent_info = AgentInfo(
        agent_id=a2a_agent.agent_id,
        name=agent.name,
        capabilities=agent.capabilities,
        endpoint="http://localhost:8080/a2a",
        transport="http",
    )
    await discovery.register(agent_info)

    print(f"\n2. Agent registered: {agent.name}")
    print(f"   Agent ID: {a2a_agent.agent_id}")
    print(f"   Capabilities: {', '.join(agent.capabilities)}")

    # Test custom handlers
    print("\n3. Testing custom handlers...")

    # Test 1: Store data
    print("\n   Test 1: Storing data")
    store_request = create_request(
        from_agent="client",
        to_agent=a2a_agent.agent_id,
        action="store",
        content={"key": "user-001", "data": {"name": "Alice", "age": 30, "role": "engineer"}},
    )

    store_response = await a2a_agent.handle_message(store_request)
    print(f"   Response: {store_response.content}")

    # Test 2: Store more data
    print("\n   Test 2: Storing more data")
    store_request2 = create_request(
        from_agent="client",
        to_agent=a2a_agent.agent_id,
        action="store",
        content={"key": "user-002", "data": {"name": "Bob", "age": 25, "role": "designer"}},
    )

    store_response2 = await a2a_agent.handle_message(store_request2)
    print(f"   Response: {store_response2.content}")

    # Test 3: Retrieve data
    print("\n   Test 3: Retrieving data")
    retrieve_request = create_request(
        from_agent="client",
        to_agent=a2a_agent.agent_id,
        action="retrieve",
        content={"key": "user-001"},
    )

    retrieve_response = await a2a_agent.handle_message(retrieve_request)
    print(f"   Response: {retrieve_response.content}")

    # Test 4: Retrieve non-existent key (error handling)
    print("\n   Test 4: Retrieving non-existent key (error handling)")
    retrieve_error_request = create_request(
        from_agent="client",
        to_agent=a2a_agent.agent_id,
        action="retrieve",
        content={"key": "user-999"},
    )

    retrieve_error_response = await a2a_agent.handle_message(retrieve_error_request)
    print(f"   Response type: {retrieve_error_response.message_type}")
    print(f"   Error: {retrieve_error_response.content}")

    # Test 5: Aggregate data
    print("\n   Test 5: Aggregating data")
    aggregate_request = create_request(
        from_agent="client", to_agent=a2a_agent.agent_id, action="aggregate", content={}
    )

    aggregate_response = await a2a_agent.handle_message(aggregate_request)
    print(f"   Response: {aggregate_response.content}")

    # Test 6: Notifications (fire-and-forget)
    print("\n4. Testing notifications (fire-and-forget)...")

    notification = create_notification(
        from_agent="client",
        to_agent=a2a_agent.agent_id,
        action="status_update",
        content={"status": "processing_complete"},
    )

    print(f"   Sent notification: {notification.action}")
    print(f"   Message type: {notification.message_type}")

    # Test 7: Unregistered action (default handler)
    print("\n5. Testing unregistered action (default handler)...")

    unregistered_request = create_request(
        from_agent="client", to_agent=a2a_agent.agent_id, action="unknown_action", content={}
    )

    unregistered_response = await a2a_agent.handle_message(unregistered_request)
    print(f"   Response: {unregistered_response.content}")

    # Demonstrate agent collaboration
    print("\n" + "=" * 70)
    print("AGENT COLLABORATION PATTERN")
    print("=" * 70)

    print(
        """
Custom handlers enable sophisticated agent collaboration:

1. Data Pipeline Pattern:
   Agent A (collector) → store → Agent B (processor) → aggregate → Agent C (reporter)

2. Request-Response Pattern:
   Client → query → Agent → retrieve → Client

3. Event-Driven Pattern:
   Agent A → notification → Agent B (no response expected)

4. Command Pattern:
   Coordinator → command → Worker Agents → status updates

5. Delegate Pattern:
   Main Agent → delegate → Specialist Agent → result

Example workflow:

   # Collector stores data
   await collector.send_to_agent(
       to_agent="processor-001",
       action="store",
       content={"key": "batch-1", "data": [...]}
   )

   # Processor aggregates
   result = await processor.send_to_agent(
       to_agent="processor-001",
       action="aggregate",
       content={}
   )

   # Reporter retrieves and formats
   report = await reporter.send_to_agent(
       to_agent="processor-001",
       action="retrieve",
       content={"key": "batch-1"}
   )
"""
    )

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


# ==============================================================================
# Run Example
# ==============================================================================

if __name__ == "__main__":
    asyncio.run(custom_handlers_example())
