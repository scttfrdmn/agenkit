"""
Shared mock LLM helpers for agenkit tests.

Provides reusable mock clients that can be configured with fixed or cycling
responses, avoiding duplicated mock definitions across test files.

Usage::

    from tests.helpers import MockLLMClient, MockStreamingLLMClient, MockAgent

    # Fixed response
    llm = MockLLMClient("The answer is 42")

    # Cycling responses (repeats after exhausted)
    llm = MockLLMClient(["step 1", "step 2", "step 3"])

    # Raise on first call, succeed on second
    llm = MockLLMClient(["error", "ok"], fail_calls={0})
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agenkit import Message

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence


class MockLLMClient:
    """
    Configurable mock LLM client for testing.

    Supports ``complete()``, ``chat()``, and ``process()`` interfaces so it
    works with techniques, patterns, and adapters that use different method
    signatures.
    """

    def __init__(
        self,
        responses: str | Sequence[str] = "Mock response",
        *,
        fail_calls: set[int] | None = None,
        fail_with: Exception | None = None,
    ) -> None:
        """
        Args:
            responses: Fixed string or list of strings cycled on each call.
            fail_calls: Set of 0-based call indices that should raise.
            fail_with: Exception to raise on failing calls (default: RuntimeError).
        """
        if isinstance(responses, str):
            self._responses = [responses]
        else:
            self._responses = list(responses)
        self._fail_calls = fail_calls or set()
        self._fail_with = fail_with or RuntimeError("mock failure")
        self.call_count = 0
        self.calls: list[object] = []

    def _next_response(self, arg: object) -> str:
        idx = self.call_count
        self.calls.append(arg)
        self.call_count += 1
        if idx in self._fail_calls:
            raise self._fail_with
        return self._responses[idx % len(self._responses)]

    async def complete(self, messages: list[Message], **kwargs: object) -> Message:
        """LLM adapter interface (``list[Message]`` → ``Message``).

        This is the contract in ``agenkit.adapters.llm.base.LLM`` that all seven
        shipped adapters implement. It used to be spelled two wrong ways here at
        once: ``complete(prompt: str)`` (the #802 shape — no adapter takes a bare
        string) and ``chat(messages)`` (the #805 shape — no adapter has a ``chat``).
        Prefer ``tests.techniques.reasoning.conftest.ContractLLM`` when a test needs
        a double that actively rejects the wrong argument type.
        """
        content = self._next_response(messages)
        return Message(role="assistant", content=content)

    async def process(self, message: Message) -> Message:
        """Agent interface (Message → Message)."""
        content = self._next_response(message)
        return Message(role="assistant", content=content)


class MockStreamingLLMClient(MockLLMClient):
    """Mock LLM that supports async streaming."""

    async def stream(self, messages: list[Message], **kwargs: object) -> AsyncIterator[Message]:
        """Yield response word-by-word for streaming tests."""
        content = self._next_response(messages)
        for word in content.split():
            yield Message(role="assistant", content=word + " ")


class MockAgent:
    """
    Minimal mock implementing the agenkit Agent duck-type interface.

    Useful when tests need an object with ``name()``, ``capabilities()``,
    and ``process()`` but do not want to depend on the full agent hierarchy.
    """

    def __init__(
        self,
        name: str = "mock_agent",
        responses: str | Sequence[str] = "Mock agent response",
        capabilities: Sequence[str] | None = None,
        *,
        fail_calls: set[int] | None = None,
    ) -> None:
        self._name = name
        self._capabilities = list(capabilities or ["mock"])
        self._llm = MockLLMClient(responses, fail_calls=fail_calls)

    def name(self) -> str:
        return self._name

    def capabilities(self) -> list[str]:
        return list(self._capabilities)

    async def process(self, message: Message) -> Message:
        return await self._llm.process(message)

    @property
    def call_count(self) -> int:
        return self._llm.call_count
