"""
Tests for ConversationalAgent pattern.
"""

import pytest

from agenkit import Message
from agenkit.patterns import ConversationalAgent, StreamingConversationalAgent


class MockLLM:
    """Mock LLM client for testing.

    Implements ``complete(messages, **kwargs)`` — the contract in
    ``agenkit.adapters.llm.base.LLM`` that all seven shipped adapters implement.
    This double used to implement ``chat(messages)``, which no adapter has, so it
    kept this file green while ``ConversationalAgent`` was unusable with any real
    LLM (#805).
    """

    def __init__(self, response: str = "Test response"):
        self.response = response
        self.call_count = 0
        self.last_messages = None

    async def complete(self, messages, **kwargs):
        """Generate a mock response."""
        self.call_count += 1
        # Store a copy to avoid reference issues
        self.last_messages = messages.copy()
        return Message(role="assistant", content=self.response)


class MockStreamingLLM(MockLLM):
    """Mock streaming LLM client."""

    async def stream(self, messages, **kwargs):
        """Generate a mock streaming response."""
        self.call_count += 1
        self.last_messages = messages
        # Split response into chunks
        words = self.response.split()
        for word in words:
            yield Message(role="assistant", content=word + " ")


@pytest.mark.asyncio
async def test_conversational_agent_basic():
    """Test basic conversational agent functionality."""
    llm = MockLLM()
    agent = ConversationalAgent(llm_client=llm, max_history=10)

    # Send a message
    response = await agent.process(Message(role="user", content="Hello"))

    assert response.content == "Test response"
    assert llm.call_count == 1
    assert agent.get_context_length() == 2  # user + assistant


@pytest.mark.asyncio
async def test_conversational_agent_with_system_prompt():
    """Test agent with system prompt."""
    llm = MockLLM()
    agent = ConversationalAgent(
        llm_client=llm, max_history=10, system_prompt="You are a helpful assistant."
    )

    # System prompt should be in history
    assert agent.get_context_length() == 1
    history = agent.get_history()
    assert history[0].role == "system"
    assert history[0].content == "You are a helpful assistant."

    # Send a message
    await agent.process(Message(role="user", content="Hello"))

    # System prompt + user + assistant
    assert agent.get_context_length() == 3


@pytest.mark.asyncio
async def test_conversational_agent_history_pruning():
    """Test history pruning when limit is reached."""
    llm = MockLLM()
    agent = ConversationalAgent(llm_client=llm, max_history=5)

    # Fill history beyond limit
    for i in range(4):
        await agent.process(Message(role="user", content=f"Message {i}"))

    # Should have pruned to max_history
    assert agent.get_context_length() == 5  # Oldest pruned, keeping most recent
    history = agent.get_history()

    # Most recent messages should be preserved
    assert "Message 3" in history[-2].content


@pytest.mark.asyncio
async def test_conversational_agent_preserves_system_prompt():
    """Test that system prompts are preserved during pruning."""
    llm = MockLLM()
    agent = ConversationalAgent(llm_client=llm, max_history=5, system_prompt="System instruction")

    # Fill history beyond limit
    for i in range(5):
        await agent.process(Message(role="user", content=f"Message {i}"))

    # System prompt should still be there
    history = agent.get_history()
    assert history[0].role == "system"
    assert history[0].content == "System instruction"


@pytest.mark.asyncio
async def test_conversational_agent_clear_history():
    """Test clearing conversation history."""
    llm = MockLLM()
    agent = ConversationalAgent(llm_client=llm, max_history=10, system_prompt="System instruction")

    # Add some messages
    await agent.process(Message(role="user", content="Hello"))
    assert agent.get_context_length() > 1

    # Clear history, keeping system prompt
    agent.clear_history(keep_system=True)
    assert agent.get_context_length() == 1
    assert agent.get_history()[0].role == "system"

    # Clear history completely
    agent.clear_history(keep_system=False)
    assert agent.get_context_length() == 0


@pytest.mark.asyncio
async def test_conversational_agent_export_import():
    """Test exporting and importing conversation history."""
    llm = MockLLM()
    agent = ConversationalAgent(llm_client=llm, max_history=10)

    # Add some messages
    await agent.process(Message(role="user", content="Hello"))
    await agent.process(Message(role="user", content="How are you?"))

    # Export history
    exported = agent.export_history()
    assert len(exported) == 4  # 2 user + 2 assistant

    # Create new agent and import
    new_agent = ConversationalAgent(llm_client=llm, max_history=10)
    new_agent.import_history(exported)

    assert new_agent.get_context_length() == 4
    assert new_agent.get_history()[0].content == "Hello"


@pytest.mark.asyncio
async def test_conversational_agent_context_passed_to_llm():
    """Test that full context is passed to LLM."""
    llm = MockLLM()
    agent = ConversationalAgent(llm_client=llm, max_history=10, system_prompt="System")

    # First message
    await agent.process(Message(role="user", content="First"))
    assert len(llm.last_messages) == 2  # system + user

    # Second message
    await agent.process(Message(role="user", content="Second"))
    assert len(llm.last_messages) == 4  # system + user + assistant + user


@pytest.mark.asyncio
async def test_conversational_agent_no_system_prompt():
    """Test agent without system prompt."""
    llm = MockLLM()
    agent = ConversationalAgent(llm_client=llm, max_history=10)

    assert agent.get_context_length() == 0

    await agent.process(Message(role="user", content="Hello"))
    assert agent.get_context_length() == 2


@pytest.mark.asyncio
async def test_conversational_agent_system_prompt_not_included():
    """Test agent with system prompt but not included in history."""
    llm = MockLLM()
    agent = ConversationalAgent(
        llm_client=llm,
        max_history=10,
        system_prompt="System instruction",
        include_system=False,
    )

    # System prompt should not be in history
    assert agent.get_context_length() == 0

    await agent.process(Message(role="user", content="Hello"))
    assert agent.get_context_length() == 2


@pytest.mark.asyncio
async def test_streaming_conversational_agent():
    """Test streaming conversational agent."""
    llm = MockStreamingLLM(response="Hello world test")
    agent = StreamingConversationalAgent(llm_client=llm, max_history=10)

    # Stream a response
    chunks = []
    async for chunk in agent.stream(Message(role="user", content="Test")):
        chunks.append(chunk.content)

    # Should have streamed 3 words
    assert len(chunks) == 3
    assert "".join(chunks).strip() == "Hello world test"

    # Full response should be in history
    history = agent.get_history()
    assert len(history) == 2  # user + assistant
    assert history[1].content.strip() == "Hello world test"


@pytest.mark.asyncio
async def test_streaming_agent_preserves_context():
    """Test that streaming agent preserves context across turns."""
    llm = MockStreamingLLM(response="Response")
    agent = StreamingConversationalAgent(llm_client=llm, max_history=10)

    # First turn
    async for _ in agent.stream(Message(role="user", content="First")):
        pass

    # Second turn
    async for _ in agent.stream(Message(role="user", content="Second")):
        pass

    # Should have both turns in history
    assert agent.get_context_length() == 4
    history = agent.get_history()
    assert history[0].content == "First"
    assert history[2].content == "Second"


@pytest.mark.asyncio
async def test_conversational_agent_with_metadata():
    """Test that message metadata is preserved."""
    llm = MockLLM()
    agent = ConversationalAgent(llm_client=llm, max_history=10)

    # Add message with metadata
    msg = Message(role="user", content="Hello", metadata={"user_id": "123"})
    await agent.process(msg)

    # Export and check metadata
    exported = agent.export_history()
    assert exported[0]["metadata"]["user_id"] == "123"


@pytest.mark.asyncio
async def test_conversational_agent_edge_case_max_history_zero():
    """Test edge case with max_history=0."""
    llm = MockLLM()
    agent = ConversationalAgent(llm_client=llm, max_history=0)

    await agent.process(Message(role="user", content="Hello"))

    # Should still prune to 0
    assert agent.get_context_length() == 0


@pytest.mark.asyncio
async def test_conversational_agent_edge_case_max_history_one():
    """Test edge case with max_history=1."""
    llm = MockLLM()
    agent = ConversationalAgent(llm_client=llm, max_history=1)

    await agent.process(Message(role="user", content="Hello"))

    # Should keep only 1 message (most recent)
    assert agent.get_context_length() == 1


@pytest.mark.asyncio
async def test_conversational_agent_name_property():
    """Test that agent has a name property."""
    llm = MockLLM()
    agent = ConversationalAgent(llm_client=llm, max_history=10)

    assert agent.name == "ConversationalAgent"


@pytest.mark.asyncio
async def test_get_history_returns_copy():
    """Test that get_history returns a copy, not reference."""
    llm = MockLLM()
    agent = ConversationalAgent(llm_client=llm, max_history=10)

    await agent.process(Message(role="user", content="Hello"))

    history = agent.get_history()
    original_length = len(history)

    # Modify the returned history
    history.append(Message(role="user", content="Extra"))

    # Agent's history should not be affected
    assert agent.get_context_length() == original_length
