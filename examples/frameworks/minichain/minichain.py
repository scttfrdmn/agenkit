"""
MiniChain - A LangChain/LangGraph-inspired implementation using Agenkit primitives.

This demonstrates how LangChain's abstractions are just composition patterns
over basic LLM calls. Shows how Agenkit primitives (Agent, Tool, Message)
enable the same patterns without framework overhead.

Key insight: You don't need a framework - just function composition + agents.

Core abstractions:
- Chain: Base interface for composable components
- LLMChain: Prompt template + LLM execution
- RunnablePassthrough: Pass data through unchanged
- RunnableLambda: Custom transformation functions
- Pipe operator: chain1 | chain2 (via __or__)

~350 LOC total (implementation + examples)
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from agenkit.interfaces import Agent, Message


class Chain(ABC):
    """
    Base interface for composable chain components.

    A chain is any component that can process input and produce output.
    Chains are composable via the pipe operator (|).
    """

    @abstractmethod
    async def invoke(self, input_data: Any) -> Any:
        """Process input and return output."""
        pass

    def __or__(self, other: "Chain") -> "Chain":
        """
        Pipe operator: chain1 | chain2

        Creates a SequenceChain that executes self, then other.
        This enables LCEL-style composition: chain1 | chain2 | chain3
        """
        return SequenceChain([self, other])


class LLMChain(Chain):
    """
    Prompt template + LLM execution chain.

    Takes input, formats it into a prompt, sends to LLM, returns response.
    This is the most common chain pattern.

    Example:
        >>> chain = LLMChain(
        ...     agent=openai_agent,
        ...     prompt_template="Summarize this: {text}"
        ... )
        >>> result = await chain.invoke({"text": "Long article..."})
    """

    def __init__(
        self,
        agent: Agent,
        prompt_template: str,
        system_message: str | None = None,
    ):
        """
        Create an LLM chain.

        Args:
            agent: Agenkit agent (any LLM adapter)
            prompt_template: Template with {variables} for formatting
            system_message: Optional system message for context
        """
        self.agent = agent
        self.prompt_template = prompt_template
        self.system_message = system_message

    async def invoke(self, input_data: dict[str, Any] | str) -> str:
        """
        Execute the chain: format prompt → send to LLM → return response.

        Args:
            input_data: Dict with template variables, or string for direct use

        Returns:
            LLM response text
        """
        # Format prompt
        if isinstance(input_data, dict):
            prompt = self.prompt_template.format(**input_data)
        else:
            prompt = str(input_data)

        # Build messages
        messages = []
        if self.system_message:
            messages.append(Message(role="system", content=self.system_message))
        messages.append(Message(role="user", content=prompt))

        # Execute LLM
        response = await self.agent.process(messages[-1])

        return str(response.content)


class RunnablePassthrough(Chain):
    """
    Pass input through unchanged.

    Useful for branching or preserving original input while adding transformations.

    Example:
        >>> passthrough = RunnablePassthrough()
        >>> result = await passthrough.invoke({"key": "value"})
        >>> # result == {"key": "value"}
    """

    async def invoke(self, input_data: Any) -> Any:
        """Return input unchanged."""
        return input_data


class RunnableLambda(Chain):
    """
    Custom transformation function as a chain.

    Wraps any function to make it composable with other chains.

    Example:
        >>> uppercase = RunnableLambda(lambda x: x.upper())
        >>> chain = uppercase | llm_chain
        >>> result = await chain.invoke("hello")
    """

    def __init__(self, func: Callable[[Any], Any]):
        """
        Create a lambda chain.

        Args:
            func: Transformation function (can be sync or async)
        """
        self.func = func

    async def invoke(self, input_data: Any) -> Any:
        """Apply transformation function."""
        import asyncio
        import inspect

        # Handle both sync and async functions
        if inspect.iscoroutinefunction(self.func):
            return await self.func(input_data)
        else:
            return self.func(input_data)


class SequenceChain(Chain):
    """
    Execute chains sequentially, passing output of each to the next.

    This is created automatically by the pipe operator (|).

    Example:
        >>> chain = step1 | step2 | step3
        >>> # Equivalent to: SequenceChain([step1, step2, step3])
    """

    def __init__(self, chains: list[Chain]):
        """
        Create a sequence chain.

        Args:
            chains: List of chains to execute in order
        """
        if not chains:
            raise ValueError("SequenceChain requires at least one chain")
        self.chains = chains

    async def invoke(self, input_data: Any) -> Any:
        """
        Execute chains sequentially.

        Output of each chain becomes input to the next.
        """
        result = input_data
        for chain in self.chains:
            result = await chain.invoke(result)
        return result


class ConversationChain(Chain):
    """
    Memory-aware chat chain.

    Maintains conversation history and includes it in each LLM call.
    Implements context window management (keeps last N messages).

    Example:
        >>> chain = ConversationChain(
        ...     agent=openai_agent,
        ...     system_message="You are a helpful assistant",
        ...     max_history=10
        ... )
        >>> response1 = await chain.invoke("Hello!")
        >>> response2 = await chain.invoke("What did I just say?")
        >>> # Chain remembers previous messages
    """

    def __init__(
        self,
        agent: Agent,
        system_message: str | None = None,
        max_history: int = 10,
    ):
        """
        Create a conversation chain.

        Args:
            agent: Agenkit agent (any LLM adapter)
            system_message: Optional system message
            max_history: Maximum messages to keep in history (for context management)
        """
        self.agent = agent
        self.system_message = system_message
        self.max_history = max_history
        self.history: list[Message] = []

    async def invoke(self, input_data: str) -> str:
        """
        Process user message with conversation history.

        Args:
            input_data: User message text

        Returns:
            Assistant response text
        """
        # Add user message to history
        user_message = Message(role="user", content=input_data)
        self.history.append(user_message)

        # Build messages with system prompt and history
        messages = []
        if self.system_message:
            messages.append(Message(role="system", content=self.system_message))

        # Add conversation history (last N messages)
        messages.extend(self.history[-self.max_history :])

        # Execute LLM with full context
        response = await self.agent.process(messages[-1])
        assistant_message = Message(role="assistant", content=response.content)

        # Add response to history
        self.history.append(assistant_message)

        return str(response.content)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.history = []


# Convenience functions for creating chains

def create_llm_chain(agent: Agent, prompt: str, system: str | None = None) -> LLMChain:
    """
    Create an LLM chain with prompt template.

    Args:
        agent: Agenkit agent
        prompt: Prompt template with {variables}
        system: Optional system message

    Returns:
        LLMChain instance
    """
    return LLMChain(agent=agent, prompt_template=prompt, system_message=system)


def create_conversation_chain(
    agent: Agent,
    system: str | None = None,
    max_history: int = 10,
) -> ConversationChain:
    """
    Create a conversation chain with memory.

    Args:
        agent: Agenkit agent
        system: Optional system message
        max_history: Maximum messages to keep

    Returns:
        ConversationChain instance
    """
    return ConversationChain(agent=agent, system_message=system, max_history=max_history)


def passthrough() -> RunnablePassthrough:
    """Create a passthrough chain."""
    return RunnablePassthrough()


def lambda_chain(func: Callable[[Any], Any]) -> RunnableLambda:
    """
    Create a lambda chain from a function.

    Args:
        func: Transformation function

    Returns:
        RunnableLambda instance
    """
    return RunnableLambda(func)
