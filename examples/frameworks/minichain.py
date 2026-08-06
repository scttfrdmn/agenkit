#!/usr/bin/env python3
"""
MiniChain - LangChain/LangGraph Equivalent Built on Agenkit

Demonstrates how LangChain-style abstractions can be built ON TOP of Agenkit
primitives, showing that Agenkit is a toolkit, not a framework.

Pattern Mappings: LangChain Chain → SequentialAgent, LLMChain → Agent + LLM,
ConversationChain → ConversationalAgent, RouterChain → RouterAgent

Migration guide: docs/migrations/langchain-to-agenkit.md

Usage: uv run python examples/frameworks/minichain.py
"""

import asyncio
from typing import Any, Protocol, cast

from agenkit import Agent, Message
from agenkit.adapters.llm import LLM, OpenAILLM
from agenkit.patterns import (
    ConversationalAgent,
    ConversationalAgentConfig,
    RouterAgent,
    RouterConfig,
    SequentialAgent,
)


class Chain(Protocol):
    """Base interface for chains (mirrors LangChain.Chain)."""

    async def run(self, input: str, **kwargs: Any) -> str:
        """Run the chain with the given input."""
        ...


class LLMChain:
    """
    Simple LLM chain with prompt template (mirrors LangChain.LLMChain).
    Pattern: LangChain.LLMChain → Agenkit LLM with prompt template
    """

    def __init__(self, llm: LLM, prompt: str) -> None:
        """Create LLM chain with LLM and prompt template."""
        self.llm = llm
        self.prompt = prompt

    async def run(self, **kwargs: Any) -> str:
        """Run chain with template variables."""
        prompt_text = self.prompt.format(**kwargs)
        messages = [Message(role="user", content=prompt_text)]
        response = await self.llm.complete(messages)
        return cast(str, response.content)


class ConversationChain:
    """
    Conversational chain with automatic memory management.
    Pattern: LangChain.ConversationChain → Agenkit ConversationalAgent
    """

    def __init__(self, llm: LLM, max_history: int = 10, system_prompt: str | None = None) -> None:
        """Create conversation chain with built-in memory."""

        class LLMClientAdapter:
            def __init__(self, llm_instance: LLM):
                self.llm_instance = llm_instance

            async def chat(self, messages: list[Message]) -> Message:
                if not messages:
                    raise ValueError("messages cannot be empty")
                return await self.llm_instance.complete(messages)

        llm_client = LLMClientAdapter(llm)
        config = ConversationalAgentConfig(
            llm_client=llm_client, max_history=max_history, system_prompt=system_prompt
        )
        self.agent = ConversationalAgent(config)

    async def run(self, input: str) -> str:
        """Process input with conversation context."""
        message = Message(role="user", content=input)
        response = await self.agent.process(message)
        return cast(str, response.content)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.agent.clear_history()

    def get_history(self) -> list[Message]:
        """Get conversation history."""
        return self.agent.get_history()


class RouterChain:
    """
    Router chain for conditional agent selection.
    Pattern: LangChain.MultiPromptChain → Agenkit RouterAgent
    """

    def __init__(
        self, classifier: Any, routes: dict[str, Agent], default_route: str | None = None
    ) -> None:
        """Create router chain with classifier and routes."""
        config = RouterConfig(classifier=classifier, agents=routes, default_key=default_route)
        self.router = RouterAgent(config)

    async def run(self, input: str) -> str:
        """Classify input and route to appropriate agent."""
        message = Message(role="user", content=input)
        response = await self.router.process(message)
        return cast(str, response.content)


class SequentialChain:
    """
    Sequential chain for multi-agent pipelines.
    Pattern: LangChain.SequentialChain → Agenkit SequentialAgent
    """

    def __init__(self, agents: list[Agent]) -> None:
        """Create sequential chain with list of agents."""
        self.pipeline = SequentialAgent(agents)

    async def run(self, input: str) -> str:
        """Process input through the agent pipeline."""
        message = Message(role="user", content=input)
        response = await self.pipeline.process(message)
        return cast(str, response.content)


class SimpleMemory:
    """
    Simple memory for conversation history.
    Pattern: LangChain.ChatMessageHistory → Agenkit ConversationalAgent.history
    Note: In Agenkit, memory is built into ConversationalAgent.
    """

    def __init__(self, max_messages: int = 10) -> None:
        """Create memory store."""
        self.max_messages = max_messages
        self.messages: list[Message] = []

    def add_message(self, role: str, content: str) -> None:
        """Add message to history."""
        self.messages.append(Message(role=role, content=content))
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def get_messages(self) -> list[Message]:
        """Get all messages."""
        return self.messages.copy()

    def clear(self) -> None:
        """Clear all messages."""
        self.messages = []

    def __len__(self) -> int:
        """Get message count."""
        return len(self.messages)


async def example_llm_chain() -> None:
    """Example: Simple LLM chain with prompt template."""
    print("=" * 60)
    print("Example 1: LLMChain (LangChain-style API)")
    print("=" * 60)
    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")
    chain = LLMChain(llm=llm, prompt="Translate to French: {text}")
    print("\n📝 chain = LLMChain(llm=llm, prompt='Translate to French: {text}')")
    print("   result = await chain.run(text='Hello, world!')")
    print("\n✅ Pattern: LangChain.LLMChain → Agenkit Agent with prompt")


async def example_conversation_chain() -> None:
    """Example: Conversational chain with memory."""
    print("\n\n" + "=" * 60)
    print("Example 2: ConversationChain (automatic memory)")
    print("=" * 60)
    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")
    chain = ConversationChain(llm=llm, max_history=10, system_prompt="You are helpful.")
    print("\n📝 chain = ConversationChain(llm=llm, max_history=10)")
    print("   await chain.run('My name is Alice')")
    print("   await chain.run('What is my name?')  # Remembers!")
    print("\n✅ Pattern: LangChain.ConversationChain → Agenkit ConversationalAgent")


async def example_sequential_chain() -> None:
    """Example: Sequential chain for multi-stage processing."""
    print("\n\n" + "=" * 60)
    print("Example 3: SequentialChain (multi-agent pipeline)")
    print("=" * 60)
    print("\n📝 chain = SequentialChain([summarizer, translator, adjuster])")
    print("   result = await chain.run('Long article...')")
    print("\n✅ Pattern: LangChain.SequentialChain → Agenkit SequentialAgent")


async def example_router_chain() -> None:
    """Example: Router chain for conditional routing."""
    print("\n\n" + "=" * 60)
    print("Example 4: RouterChain (conditional routing)")
    print("=" * 60)
    print("\n📝 router = RouterChain(classifier, routes={'billing': ..., 'tech': ...})")
    print("   result = await router.run('I have a payment question')")
    print("\n✅ Pattern: LangChain.MultiPromptChain → Agenkit RouterAgent")


async def main() -> None:
    """Run all examples."""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "MiniChain - LangChain Built on Agenkit" + " " * 9 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n🎯 Demonstrate: LangChain abstractions built ON TOP of Agenkit")

    await example_llm_chain()
    await example_conversation_chain()
    await example_sequential_chain()
    await example_router_chain()

    print("\n\n" + "=" * 60)
    print("✅ MiniChain Examples Complete")
    print("=" * 60)
    print("\n🔑 Key Takeaways:")
    print("   • Agenkit is a TOOLKIT, not a framework")
    print("   • LangChain patterns map to Agenkit primitives:")
    print("     - LLMChain → Agent + LLM, ConversationChain → ConversationalAgent")
    print("     - SequentialChain → SequentialAgent, RouterChain → RouterAgent")
    print("     - Memory → ConversationalAgent.history (built-in)")
    print("\n📚 Migration guide: docs/migrations/langchain-to-agenkit.md")
    print("\n💡 Why Agenkit over LangChain?")
    print("   ✓ 6 languages (Python, Go, TypeScript, Rust, C++, Zig)")
    print("   ✓ 18x faster (Go), 22x (Rust), 25x (C++)")
    print("   ✓ Production middleware (retry, circuit breaker, timeout)")
    print("   ✓ OpenTelemetry observability, explicit control")


if __name__ == "__main__":
    asyncio.run(main())
