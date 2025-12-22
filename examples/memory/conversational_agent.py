"""
Conversational Agent with Memory

Demonstrates how to build agents with persistent memory and different
memory management strategies.

This example shows:
1. Basic agent with memory
2. Different memory strategies (sliding window, importance, summarization)
3. Multi-session management
4. Memory usage patterns
"""

import asyncio

from agenkit.interfaces import Message
from agenkit.memory import (
    ImportanceWeightingStrategy,
    InMemoryMemory,
    SlidingWindowStrategy,
    SummarizationStrategy,
)


class ConversationalAgent:
    """
    Agent with memory support.

    This agent maintains conversation history using a Memory implementation
    and selects context using a MemoryStrategy.
    """

    def __init__(self, name: str, memory, strategy=None, context_limit: int = 10):
        """
        Initialize conversational agent.

        Args:
            name: Agent name
            memory: Memory implementation (InMemoryMemory, RedisMemory, etc.)
            strategy: MemoryStrategy for context selection (defaults to sliding window)
            context_limit: Maximum messages to include in context
        """
        self.name = name
        self.memory = memory
        self.strategy = strategy or SlidingWindowStrategy(window_size=10)
        self.context_limit = context_limit

    async def process(self, message: Message, session_id: str) -> Message:
        """
        Process message with memory.

        Args:
            message: Input message
            session_id: Session identifier for memory isolation

        Returns:
            Response message
        """
        # Store incoming message
        await self.memory.store(session_id, message)

        # Retrieve context using strategy
        context = await self.strategy.select(
            memory=self.memory, session_id=session_id, context_limit=self.context_limit
        )

        # Generate response (simplified - in real agent, would use LLM)
        response_content = (
            f"[{self.name}] Received: '{message.content}' (with {len(context)} messages in context)"
        )

        response = Message(role="assistant", content=response_content)

        # Store response
        await self.memory.store(session_id, response)

        return response


# ===== Example 1: Basic Conversational Agent =====


async def example_basic_conversation():
    """Example: Basic conversation with memory."""
    print("\n=== Example 1: Basic Conversation ===\n")

    # Create agent with memory
    memory = InMemoryMemory(max_size=100)
    agent = ConversationalAgent(
        name="Assistant", memory=memory, strategy=SlidingWindowStrategy(window_size=5)
    )

    # Simulate conversation
    messages = [
        "Hello!",
        "How are you?",
        "Can you help me?",
        "I need to solve a bug",
        "The app crashes on startup",
    ]

    session_id = "user-123"

    for msg_content in messages:
        user_msg = Message(role="user", content=msg_content)
        response = await agent.process(user_msg, session_id)
        print(f"User: {msg_content}")
        print(f"Agent: {response.content}\n")

    # Check memory usage
    print(f"Total messages in memory: {memory.get_session_count(session_id)}")


# ===== Example 2: Importance-Based Memory =====


async def example_importance_memory():
    """Example: Using importance weighting strategy."""
    print("\n=== Example 2: Importance-Based Memory ===\n")

    memory = InMemoryMemory(max_size=100)
    agent = ConversationalAgent(
        name="PriorityAssistant",
        memory=memory,
        strategy=ImportanceWeightingStrategy(
            importance_threshold=0.5, recency_weight=0.3, min_recent=2
        ),
        context_limit=5,
    )

    session_id = "priority-session"

    # Simulate conversation with different importance levels
    conversation = [
        ("Hello", 0.3),
        ("I have a critical issue", 0.9),
        ("The database is down", 0.9),
        ("How's the weather?", 0.1),
        ("Can you fix the database?", 0.8),
        ("Thanks", 0.2),
    ]

    for content, importance in conversation:
        user_msg = Message(role="user", content=content)
        # Store with importance metadata
        await memory.store(session_id, user_msg, metadata={"importance": importance})

        # Get context (will prioritize high-importance messages)
        context = await agent.strategy.select(
            memory=memory, session_id=session_id, context_limit=agent.context_limit
        )

        # Generate simple response
        response = Message(role="assistant", content=f"Understood (context size: {len(context)})")
        await memory.store(session_id, response, metadata={"importance": 0.5})

        print(f"User: {content} [importance: {importance}]")
        print(f"Context size: {len(context)}")
        print(f"Agent: {response.content}\n")


# ===== Example 3: Summarization Strategy =====


async def example_summarization():
    """Example: Using summarization strategy for long conversations."""
    print("\n=== Example 3: Summarization Strategy ===\n")

    memory = InMemoryMemory(max_size=100)
    agent = ConversationalAgent(
        name="SummarizingAssistant",
        memory=memory,
        strategy=SummarizationStrategy(recent_count=3, summarize_older=True),
        context_limit=10,
    )

    session_id = "long-conversation"

    # Simulate long conversation
    for i in range(10):
        user_msg = Message(role="user", content=f"Message {i}")
        response = await agent.process(user_msg, session_id)

        if i == 9:  # Last message
            print(f"User: Message {i}")
            print(f"Agent: {response.content}")

            # Show context
            context = await agent.strategy.select(
                memory=memory, session_id=session_id, context_limit=agent.context_limit
            )

            print(f"\nFinal context ({len(context)} messages):")
            for idx, msg in enumerate(context, 1):
                preview = msg.content[:60]
                if len(msg.content) > 60:
                    preview += "..."
                print(f"  {idx}. [{msg.role}] {preview}")


# ===== Example 4: Multi-Session Management =====


async def example_multi_session():
    """Example: Managing multiple sessions with isolated memory."""
    print("\n=== Example 4: Multi-Session Management ===\n")

    # Shared memory across sessions
    memory = InMemoryMemory(max_size=1000)

    # Create agents for different sessions
    sessions = {"user-alice": "Alice", "user-bob": "Bob", "user-charlie": "Charlie"}

    agent = ConversationalAgent(
        name="MultiSessionAssistant", memory=memory, strategy=SlidingWindowStrategy(window_size=5)
    )

    # Simulate conversations in different sessions
    for session_id, user_name in sessions.items():
        user_msg = Message(role="user", content=f"Hello, I'm {user_name}")
        response = await agent.process(user_msg, session_id)
        print(f"[{session_id}] User: {user_msg.content}")
        print(f"[{session_id}] Agent: {response.content}\n")

    # Check memory usage
    usage = memory.get_memory_usage()
    print("Memory usage:")
    print(f"  Total sessions: {usage['total_sessions']}")
    print(f"  Total messages: {usage['total_messages']}")
    print(f"  Sessions: {memory.get_all_sessions()}")


# ===== Example 5: Strategy Comparison =====


async def example_strategy_comparison():
    """Example: Comparing different memory strategies."""
    print("\n=== Example 5: Strategy Comparison ===\n")

    memory = InMemoryMemory(max_size=100)
    session_id = "comparison"

    # Add test messages
    for i in range(10):
        importance = 0.1 * (i + 1)  # 0.1 to 1.0
        await memory.store(
            session_id,
            Message(role="user", content=f"Message {i}"),
            metadata={"importance": importance},
        )

    # Try different strategies
    strategies = {
        "Sliding Window": SlidingWindowStrategy(window_size=5),
        "Importance Weighting": ImportanceWeightingStrategy(importance_threshold=0.5, min_recent=2),
        "Summarization": SummarizationStrategy(recent_count=5, summarize_older=True),
    }

    for name, strategy in strategies.items():
        context = await strategy.select(memory=memory, session_id=session_id, context_limit=6)

        print(f"{name}:")
        print(f"  Selected {len(context)} messages")
        messages = [msg.content[:30] for msg in context]
        print(f"  Messages: {messages}\n")


# ===== Main =====


async def main():
    """Run all examples."""
    await example_basic_conversation()
    await example_importance_memory()
    await example_summarization()
    await example_multi_session()
    await example_strategy_comparison()


if __name__ == "__main__":
    asyncio.run(main())
