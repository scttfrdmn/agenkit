"""
MiniChain API compatibility tests (Issue #478).

Validates that MiniChain's LangChain-compatible abstractions behave correctly
when built on top of Agenkit primitives.
"""

import pytest

# minichain is importable via the sys.path injection in conftest.py
from minichain import ConversationChain, LLMChain, RouterChain, SequentialChain, SimpleMemory

from tests.frameworks.fixtures.mock_providers import MockAgent, MockClassifier, MockLLM

pytestmark = pytest.mark.frameworks


# ---------------------------------------------------------------------------
# Group 1: LLMChain (6 tests)
# ---------------------------------------------------------------------------


class TestLLMChain:
    """Tests for LLMChain — LangChain.LLMChain equivalent."""

    def test_instantiation(self, mock_llm: MockLLM) -> None:
        """LLMChain can be created with an LLM and prompt template."""
        chain = LLMChain(llm=mock_llm, prompt="Hello {name}")
        assert chain is not None
        assert chain.llm is mock_llm
        assert chain.prompt == "Hello {name}"

    @pytest.mark.asyncio
    async def test_template_substitution(self, mock_llm: MockLLM) -> None:
        """run() substitutes template variables into the prompt."""
        chain = LLMChain(llm=mock_llm, prompt="Translate to French: {text}")
        await chain.run(text="Hello world")
        last_content = mock_llm.last_messages[0].content
        assert "Hello world" in last_content
        assert "Translate to French" in last_content

    @pytest.mark.asyncio
    async def test_call_count(self, mock_llm: MockLLM) -> None:
        """Each run() call increments the LLM call count."""
        chain = LLMChain(llm=mock_llm, prompt="{input}")
        await chain.run(input="first")
        await chain.run(input="second")
        assert mock_llm.call_count == 2

    @pytest.mark.asyncio
    async def test_multiple_template_vars(self, mock_llm: MockLLM) -> None:
        """run() handles templates with multiple variables."""
        chain = LLMChain(llm=mock_llm, prompt="Write a {length} {style} about {topic}")
        await chain.run(length="short", style="poem", topic="AI")
        content = mock_llm.last_messages[0].content
        assert "short" in content
        assert "poem" in content
        assert "AI" in content

    @pytest.mark.asyncio
    async def test_return_type_is_str(self, mock_llm: MockLLM) -> None:
        """run() returns a str."""
        chain = LLMChain(llm=mock_llm, prompt="{input}")
        result = await chain.run(input="test")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_returns_llm_response(self) -> None:
        """run() returns the LLM's response content."""
        llm = MockLLM(default_response="Bonjour le monde")
        chain = LLMChain(llm=llm, prompt="Translate: {text}")
        result = await chain.run(text="Hello world")
        assert result == "Bonjour le monde"


# ---------------------------------------------------------------------------
# Group 2: ConversationChain (6 tests)
# ---------------------------------------------------------------------------


class TestConversationChain:
    """Tests for ConversationChain — LangChain.ConversationChain equivalent."""

    def test_instantiation(self, mock_llm: MockLLM) -> None:
        """ConversationChain can be created with an LLM."""
        chain = ConversationChain(llm=mock_llm)
        assert chain is not None

    @pytest.mark.asyncio
    async def test_return_type_is_str(self, mock_llm: MockLLM) -> None:
        """run() returns a str."""
        chain = ConversationChain(llm=mock_llm)
        result = await chain.run("Hello")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_history_grows_with_turns(self, mock_llm: MockLLM) -> None:
        """History accumulates messages across turns."""
        chain = ConversationChain(llm=mock_llm)
        await chain.run("Hello")
        await chain.run("How are you?")
        history = chain.get_history()
        assert len(history) >= 2

    @pytest.mark.asyncio
    async def test_clear_history(self, mock_llm: MockLLM) -> None:
        """clear_history() resets the conversation."""
        chain = ConversationChain(llm=mock_llm)
        await chain.run("Hello")
        chain.clear_history()
        assert chain.get_history() == []

    def test_system_prompt_accepted(self, mock_llm: MockLLM) -> None:
        """ConversationChain accepts an optional system_prompt."""
        chain = ConversationChain(llm=mock_llm, system_prompt="You are helpful.")
        assert chain is not None

    @pytest.mark.asyncio
    async def test_max_history_cap(self) -> None:
        """History is capped at max_history messages."""
        llm = MockLLM(default_response="ok")
        chain = ConversationChain(llm=llm, max_history=3)
        for i in range(10):
            await chain.run(f"message {i}")
        history = chain.get_history()
        assert len(history) <= 3


# ---------------------------------------------------------------------------
# Group 3: SequentialChain (4 tests)
# ---------------------------------------------------------------------------


class TestSequentialChain:
    """Tests for SequentialChain — LangChain.SequentialChain equivalent."""

    def test_instantiation(self) -> None:
        """SequentialChain can be created with a list of agents."""
        agents = [MockAgent("agent1"), MockAgent("agent2")]
        chain = SequentialChain(agents=agents)
        assert chain is not None

    @pytest.mark.asyncio
    async def test_chaining_passes_output(self) -> None:
        """Output of each agent flows through the pipeline."""
        agent1 = MockAgent("step1", response="intermediate result")
        agent2 = MockAgent("step2", response="final result")
        chain = SequentialChain(agents=[agent1, agent2])
        result = await chain.run("start")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_single_agent(self) -> None:
        """SequentialChain works with a single agent."""
        agent = MockAgent("solo", response="solo output")
        chain = SequentialChain(agents=[agent])
        result = await chain.run("input")
        assert result == "solo output"

    @pytest.mark.asyncio
    async def test_output_passes_through(self) -> None:
        """Final output is the last agent's response."""
        agent1 = MockAgent("a1", response="step1 done")
        agent2 = MockAgent("a2", response="step2 done")
        agent3 = MockAgent("a3", response="final step")
        chain = SequentialChain(agents=[agent1, agent2, agent3])
        result = await chain.run("begin")
        assert result == "final step"


# ---------------------------------------------------------------------------
# Group 4: RouterChain (4 tests)
# ---------------------------------------------------------------------------


class TestRouterChain:
    """Tests for RouterChain — LangChain.MultiPromptChain equivalent."""

    def test_instantiation(self, mock_classifier: MockClassifier) -> None:
        """RouterChain can be created with a classifier and routes."""
        routes = {
            "billing": MockAgent("billing_agent"),
            "technical": MockAgent("tech_agent"),
        }
        chain = RouterChain(classifier=mock_classifier, routes=routes)
        assert chain is not None

    @pytest.mark.asyncio
    async def test_correct_routing(self, mock_classifier: MockClassifier) -> None:
        """RouterChain routes to the agent matching the classification."""
        billing_agent = MockAgent("billing", response="billing response")
        tech_agent = MockAgent("technical", response="tech response")
        routes = {"billing": billing_agent, "technical": tech_agent}
        chain = RouterChain(classifier=mock_classifier, routes=routes)
        result = await chain.run("I have an invoice question")
        assert result == "billing response"

    @pytest.mark.asyncio
    async def test_default_route(self) -> None:
        """RouterChain uses default_route when no keyword matches."""
        classifier = MockClassifier(rules={"billing": ["invoice"]}, default_category="general")
        general_agent = MockAgent("general", response="general response")
        billing_agent = MockAgent("billing", response="billing response")
        routes = {"billing": billing_agent, "general": general_agent}
        chain = RouterChain(classifier=classifier, routes=routes, default_route="general")
        result = await chain.run("what time is it")
        assert result == "general response"

    @pytest.mark.asyncio
    async def test_dynamic_routing(self, mock_classifier: MockClassifier) -> None:
        """RouterChain routes different inputs to different agents."""
        billing_agent = MockAgent("billing", response="billing answer")
        tech_agent = MockAgent("technical", response="tech answer")
        routes = {"billing": billing_agent, "technical": tech_agent}
        chain = RouterChain(classifier=mock_classifier, routes=routes)

        billing_result = await chain.run("I need help with my payment")
        tech_result = await chain.run("There is a bug in the system")

        assert billing_result == "billing answer"
        assert tech_result == "tech answer"


# ---------------------------------------------------------------------------
# Group 5: SimpleMemory (4 tests)
# ---------------------------------------------------------------------------


class TestSimpleMemory:
    """Tests for SimpleMemory — LangChain.ChatMessageHistory equivalent."""

    def test_add_and_get_messages(self) -> None:
        """Messages added are returned by get_messages()."""
        mem = SimpleMemory()
        mem.add_message("user", "Hello")
        mem.add_message("agent", "Hi there")
        messages = mem.get_messages()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"

    def test_max_messages_enforcement(self) -> None:
        """Messages are capped at max_messages."""
        mem = SimpleMemory(max_messages=3)
        for i in range(6):
            mem.add_message("user", f"message {i}")
        assert len(mem.get_messages()) == 3

    def test_clear(self) -> None:
        """clear() removes all messages."""
        mem = SimpleMemory()
        mem.add_message("user", "Hello")
        mem.clear()
        assert len(mem.get_messages()) == 0

    def test_len(self) -> None:
        """__len__ returns current message count."""
        mem = SimpleMemory()
        assert len(mem) == 0
        mem.add_message("user", "one")
        mem.add_message("agent", "two")
        assert len(mem) == 2
