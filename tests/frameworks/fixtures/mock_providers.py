"""Mock LLM and classifier providers for framework compatibility tests."""

from collections.abc import AsyncIterator
from typing import Any

from agenkit import Agent, Message
from agenkit.adapters.llm import LLM


class MockLLM(LLM):
    """Mock LLM that returns pre-configured responses without API calls."""

    def __init__(
        self, responses: list[str] | None = None, default_response: str = "mock response"
    ) -> None:
        """Create mock LLM with configurable responses."""
        self._responses = responses or []
        self._default_response = default_response
        self.call_count = 0
        self.last_messages: list[Message] = []

    async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
        """Return next configured response or default."""
        self.call_count += 1
        self.last_messages = list(messages)

        if self._responses:
            idx = min(self.call_count - 1, len(self._responses) - 1)
            content = self._responses[idx]
        else:
            content = self._default_response

        return Message(role="agent", content=content)

    async def stream(self, messages: list[Message], **kwargs: Any) -> AsyncIterator[Message]:
        """Stream single chunk with the complete response."""
        response = await self.complete(messages, **kwargs)
        yield response

    @property
    def model(self) -> str:
        """Return mock model name."""
        return "mock-llm"


class MockAgent(Agent):
    """Simple mock agent that returns a configurable response."""

    def __init__(self, name_: str = "mock_agent", response: str = "mock agent response") -> None:
        """Create mock agent with configurable name and response."""
        self._name = name_
        self._response = response
        self.received_messages: list[Message] = []

    @property
    def name(self) -> str:
        """Return agent name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return [self._name]

    async def process(self, message: Message) -> Message:
        """Return configured response."""
        self.received_messages.append(message)
        return Message(role="agent", content=self._response)


class MockClassifier:
    """Keyword-based classifier implementing the ClassifierAgent protocol."""

    def __init__(self, rules: dict[str, list[str]], default_category: str = "general") -> None:
        """
        Create mock classifier with keyword routing rules.

        Args:
            rules: Map of category -> list of keywords that trigger it
            default_category: Category to return when no keywords match
        """
        self._rules = rules
        self._default_category = default_category

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "MockClassifier"

    def capabilities(self) -> list[str]:
        """Return classifier capabilities."""
        return ["classification", "keyword-matching"]

    async def process(self, message: Message) -> Message:
        """Process message by classifying and returning category as content."""
        category = await self.classify(message)
        return Message(role="agent", content=category)

    async def classify(self, message: Message) -> str:
        """Classify message using keyword matching."""
        content = message.content.lower()

        for category, keywords in self._rules.items():
            for keyword in keywords:
                if keyword.lower() in content:
                    return category

        return self._default_category
