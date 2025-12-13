"""
Tests for RouterAgent pattern - conditional agent selection via classification.
"""

import pytest

from agenkit import Message
from agenkit.patterns import RouterAgent, RouterConfig, SimpleClassifier, LLMClassifier


# ============================================================================
# Mock Agents
# ============================================================================


class MockAgent:
    """Simple mock agent for testing."""

    def __init__(self, name="mock", response="Success", capabilities=None):
        self._name = name
        self.response = response
        self._capabilities = capabilities or []
        self.call_count = 0
        self.last_message = None

    @property
    def name(self):
        return self._name

    def capabilities(self):
        return self._capabilities

    async def process(self, message: Message) -> Message:
        """Process message."""
        self.call_count += 1
        self.last_message = message
        return Message(
            role="assistant",
            content=f"{self._name}: {self.response}",
            metadata={"agent": self._name}
        )


class FailingAgent:
    """Agent that always fails."""

    def __init__(self, name="failing"):
        self._name = name

    @property
    def name(self):
        return self._name

    def capabilities(self):
        return ["fail"]

    async def process(self, message: Message) -> Message:
        """Always raises an error."""
        raise RuntimeError(f"{self._name} failed")


# ============================================================================
# Mock Classifiers
# ============================================================================


class MockClassifier:
    """Simple mock classifier for testing."""

    def __init__(self, return_category="category1"):
        self.return_category = return_category
        self.call_count = 0
        self.last_message = None

    @property
    def name(self):
        return "MockClassifier"

    def capabilities(self):
        return ["classification"]

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content="classified")

    async def classify(self, message: Message) -> str:
        """Return pre-programmed category."""
        self.call_count += 1
        self.last_message = message
        return self.return_category


class FailingClassifier:
    """Classifier that always fails."""

    @property
    def name(self):
        return "FailingClassifier"

    def capabilities(self):
        return ["fail"]

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content="error")

    async def classify(self, message: Message) -> str:
        """Always raises an error."""
        raise RuntimeError("Classification failed")


# ============================================================================
# RouterAgent Creation Tests
# ============================================================================


def test_router_creation():
    """Test basic router agent creation."""
    classifier = MockClassifier("cat1")
    agent1 = MockAgent("agent1")

    config = RouterConfig(classifier=classifier, agents={"cat1": agent1})
    router = RouterAgent(config)

    assert router._classifier is classifier
    assert router._agents == {"cat1": agent1}
    assert router.name == "RouterAgent"


def test_router_none_config_raises():
    """Test that None config raises ValueError."""
    with pytest.raises(ValueError, match="config is required"):
        RouterAgent(None)  # type: ignore


def test_router_none_classifier_raises():
    """Test that None classifier raises ValueError."""
    agent = MockAgent("agent")
    config = RouterConfig(classifier=None, agents={"cat1": agent})  # type: ignore

    with pytest.raises(ValueError, match="classifier is required"):
        RouterAgent(config)


def test_router_empty_agents_raises():
    """Test that empty agents dict raises ValueError."""
    classifier = MockClassifier()
    config = RouterConfig(classifier=classifier, agents={})

    with pytest.raises(ValueError, match="at least one agent is required"):
        RouterAgent(config)


def test_router_invalid_default_key_raises():
    """Test that invalid default_key raises ValueError."""
    classifier = MockClassifier()
    agent = MockAgent("agent")
    config = RouterConfig(
        classifier=classifier,
        agents={"cat1": agent},
        default_key="nonexistent"
    )

    with pytest.raises(ValueError, match="default key .* not found"):
        RouterAgent(config)


def test_router_valid_default_key():
    """Test router with valid default_key."""
    classifier = MockClassifier()
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    config = RouterConfig(
        classifier=classifier,
        agents={"cat1": agent1, "cat2": agent2},
        default_key="cat1"
    )
    router = RouterAgent(config)

    assert router._default_key == "cat1"


# ============================================================================
# Capabilities Tests
# ============================================================================


def test_router_capabilities_combined():
    """Test that capabilities are combined from classifier and agents."""
    classifier = MockClassifier()
    agent1 = MockAgent("agent1", capabilities=["search"])
    agent2 = MockAgent("agent2", capabilities=["write"])

    config = RouterConfig(classifier=classifier, agents={"cat1": agent1, "cat2": agent2})
    router = RouterAgent(config)
    caps = router.capabilities()

    # Should have all capabilities plus router-specific
    assert "classification" in caps
    assert "search" in caps
    assert "write" in caps
    assert "router" in caps
    assert "conditional" in caps


# ============================================================================
# Processing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_router_basic_routing():
    """Test basic routing to correct agent."""
    classifier = MockClassifier("billing")
    billing_agent = MockAgent("billing_agent", response="Billing handled")
    tech_agent = MockAgent("tech_agent", response="Tech handled")

    config = RouterConfig(
        classifier=classifier,
        agents={"billing": billing_agent, "technical": tech_agent}
    )
    router = RouterAgent(config)

    message = Message(role="user", content="payment question")
    result = await router.process(message)

    # Should route to billing agent
    assert billing_agent.call_count == 1
    assert tech_agent.call_count == 0
    assert "Billing handled" in result.content


@pytest.mark.asyncio
async def test_router_classification_called():
    """Test that classifier is called during routing."""
    classifier = MockClassifier("cat1")
    agent = MockAgent("agent1")

    config = RouterConfig(classifier=classifier, agents={"cat1": agent})
    router = RouterAgent(config)

    message = Message(role="user", content="test message")
    await router.process(message)

    # Classifier should have been called
    assert classifier.call_count == 1
    assert classifier.last_message.content == "test message"


@pytest.mark.asyncio
async def test_router_metadata():
    """Test that routing metadata is added."""
    classifier = MockClassifier("cat1")
    agent = MockAgent("agent1")

    config = RouterConfig(classifier=classifier, agents={"cat1": agent})
    router = RouterAgent(config)

    message = Message(role="user", content="input")
    result = await router.process(message)

    # Should have routing metadata
    assert "routed_category" in result.metadata
    assert "routed_agent" in result.metadata
    assert "available_routes" in result.metadata
    assert result.metadata["routed_category"] == "cat1"
    assert result.metadata["routed_agent"] == "agent1"
    assert result.metadata["available_routes"] == 1


@pytest.mark.asyncio
async def test_router_multiple_categories():
    """Test routing with multiple categories."""
    classifier = MockClassifier("technical")
    billing = MockAgent("billing", response="Billing response")
    technical = MockAgent("technical", response="Tech response")
    account = MockAgent("account", response="Account response")

    config = RouterConfig(
        classifier=classifier,
        agents={"billing": billing, "technical": technical, "account": account}
    )
    router = RouterAgent(config)

    message = Message(role="user", content="error message")
    result = await router.process(message)

    # Only technical agent should be called
    assert billing.call_count == 0
    assert technical.call_count == 1
    assert account.call_count == 0
    assert "Tech response" in result.content


# ============================================================================
# Default Key Tests
# ============================================================================


@pytest.mark.asyncio
async def test_router_default_key_used():
    """Test that default_key is used for unmatched categories."""
    classifier = MockClassifier("unknown_category")
    agent1 = MockAgent("agent1")
    default_agent = MockAgent("default")

    config = RouterConfig(
        classifier=classifier,
        agents={"cat1": agent1, "default": default_agent},
        default_key="default"
    )
    router = RouterAgent(config)

    message = Message(role="user", content="input")
    result = await router.process(message)

    # Should route to default agent
    assert agent1.call_count == 0
    assert default_agent.call_count == 1
    assert result.metadata["routed_category"] == "default"


@pytest.mark.asyncio
async def test_router_no_match_no_default_raises():
    """Test that unmatched category without default raises error."""
    classifier = MockClassifier("nonexistent")
    agent = MockAgent("agent1")

    config = RouterConfig(classifier=classifier, agents={"cat1": agent})
    router = RouterAgent(config)

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="no agent found for category"):
        await router.process(message)


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_router_none_message_raises():
    """Test that None message raises ValueError."""
    classifier = MockClassifier()
    agent = MockAgent("agent")

    config = RouterConfig(classifier=classifier, agents={"cat1": agent})
    router = RouterAgent(config)

    with pytest.raises(ValueError, match="message cannot be None"):
        await router.process(None)  # type: ignore


@pytest.mark.asyncio
async def test_router_classification_failure():
    """Test that classification failure is handled."""
    classifier = FailingClassifier()
    agent = MockAgent("agent")

    config = RouterConfig(classifier=classifier, agents={"cat1": agent})
    router = RouterAgent(config)

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="classification failed"):
        await router.process(message)


@pytest.mark.asyncio
async def test_router_agent_execution_failure():
    """Test that agent execution failure is handled."""
    classifier = MockClassifier("failing_cat")
    failing = FailingAgent("failing_agent")

    config = RouterConfig(classifier=classifier, agents={"failing_cat": failing})
    router = RouterAgent(config)

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="agent .* failed"):
        await router.process(message)


# ============================================================================
# SimpleClassifier Tests
# ============================================================================


@pytest.mark.asyncio
async def test_simple_classifier_keyword_match():
    """Test SimpleClassifier with keyword matching."""
    base_agent = MockAgent("base")
    classifier = SimpleClassifier(
        agent=base_agent,
        keywords={
            "billing": ["payment", "invoice", "charge"],
            "technical": ["error", "bug", "issue"]
        }
    )

    message = Message(role="user", content="I have a payment problem")
    category = await classifier.classify(message)

    assert category == "billing"


@pytest.mark.asyncio
async def test_simple_classifier_case_insensitive():
    """Test SimpleClassifier is case insensitive."""
    base_agent = MockAgent("base")
    classifier = SimpleClassifier(
        agent=base_agent,
        keywords={"billing": ["PAYMENT", "Invoice"]}
    )

    message = Message(role="user", content="payment issue")
    category = await classifier.classify(message)

    assert category == "billing"


@pytest.mark.asyncio
async def test_simple_classifier_no_match_raises():
    """Test SimpleClassifier raises when no keywords match."""
    base_agent = MockAgent("base")
    classifier = SimpleClassifier(
        agent=base_agent,
        keywords={"billing": ["payment"]}
    )

    message = Message(role="user", content="hello there")

    with pytest.raises(RuntimeError, match="unable to classify"):
        await classifier.classify(message)


@pytest.mark.asyncio
async def test_simple_classifier_multiple_matches():
    """Test SimpleClassifier chooses category with most matches."""
    base_agent = MockAgent("base")
    classifier = SimpleClassifier(
        agent=base_agent,
        keywords={
            "billing": ["payment", "invoice"],
            "technical": ["error", "bug", "issue", "problem"]
        }
    )

    # "error" and "issue" match technical (2 matches)
    # Only "payment" matches billing (1 match)
    message = Message(role="user", content="payment error issue")
    category = await classifier.classify(message)

    assert category == "technical"


# ============================================================================
# LLMClassifier Tests
# ============================================================================


@pytest.mark.asyncio
async def test_llm_classifier_valid_category():
    """Test LLMClassifier with valid response."""
    # Create agent that returns just the category
    class LLMAgent:
        @property
        def name(self):
            return "llm"

        def capabilities(self):
            return []

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="billing")

    base_agent = LLMAgent()
    classifier = LLMClassifier(
        agent=base_agent,
        categories=["billing", "technical", "account"]
    )

    message = Message(role="user", content="payment question")
    category = await classifier.classify(message)

    assert category == "billing"


@pytest.mark.asyncio
async def test_llm_classifier_case_insensitive_match():
    """Test LLMClassifier handles case variations."""
    # Create agent that returns uppercase category
    class LLMAgent:
        @property
        def name(self):
            return "llm"

        def capabilities(self):
            return []

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="BILLING")

    base_agent = LLMAgent()
    classifier = LLMClassifier(
        agent=base_agent,
        categories=["billing", "technical"]
    )

    message = Message(role="user", content="question")
    category = await classifier.classify(message)

    assert category == "billing"


@pytest.mark.asyncio
async def test_llm_classifier_invalid_category_raises():
    """Test LLMClassifier raises on invalid category."""
    base_agent = MockAgent("base", response="unknown_category")
    classifier = LLMClassifier(
        agent=base_agent,
        categories=["billing", "technical"]
    )

    message = Message(role="user", content="question")

    with pytest.raises(RuntimeError, match="invalid category"):
        await classifier.classify(message)


@pytest.mark.asyncio
async def test_llm_classifier_custom_prompt():
    """Test LLMClassifier with custom prompt."""
    # Create agent that tracks last message and returns category
    class LLMAgent:
        def __init__(self):
            self.last_message = None

        @property
        def name(self):
            return "llm"

        def capabilities(self):
            return []

        async def process(self, message: Message) -> Message:
            self.last_message = message
            return Message(role="assistant", content="billing")

    base_agent = LLMAgent()
    custom_prompt = "Custom classification prompt: "

    classifier = LLMClassifier(
        agent=base_agent,
        categories=["billing", "technical"],
        prompt=custom_prompt
    )

    message = Message(role="user", content="payment")
    await classifier.classify(message)

    # Check that custom prompt was used
    assert base_agent.last_message.content.startswith("Custom classification")


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_router_with_simple_classifier_integration():
    """Test RouterAgent with SimpleClassifier integration."""
    base_agent = MockAgent("base")
    classifier = SimpleClassifier(
        agent=base_agent,
        keywords={
            "billing": ["payment", "invoice"],
            "technical": ["error", "bug"]
        }
    )

    billing_agent = MockAgent("billing", response="Billing handled")
    tech_agent = MockAgent("technical", response="Tech handled")

    config = RouterConfig(
        classifier=classifier,
        agents={"billing": billing_agent, "technical": tech_agent}
    )
    router = RouterAgent(config)

    # Test billing routing
    message1 = Message(role="user", content="payment issue")
    result1 = await router.process(message1)
    assert "Billing handled" in result1.content

    # Test technical routing
    message2 = Message(role="user", content="error occurred")
    result2 = await router.process(message2)
    assert "Tech handled" in result2.content


@pytest.mark.asyncio
async def test_router_reuse():
    """Test that router can be reused for multiple calls."""
    classifier = MockClassifier("cat1")
    agent = MockAgent("agent1")

    config = RouterConfig(classifier=classifier, agents={"cat1": agent})
    router = RouterAgent(config)

    # First call
    message1 = Message(role="user", content="first")
    await router.process(message1)

    # Second call
    message2 = Message(role="user", content="second")
    await router.process(message2)

    # Agent should have been called twice
    assert agent.call_count == 2
