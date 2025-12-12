"""
Context Optimization Composition

A simple wrapper that optimizes context length by summarizing when it
exceeds a token limit. This is useful for cost optimization and staying
within model context windows.

This composition demonstrates that "context optimization" is just:
1. Token counting
2. Conditional summarization
3. Agent wrapping

For production systems with sophisticated chunking, hierarchical
summarization, and caching, build a custom pattern.

This composition is perfect for:
- Cost reduction for long conversations
- Staying within model context limits
- Quick optimization for MVPs
- Learning context management

References:
    Source: Rothman "Context Engineering for Multi-Agent Systems" Ch. 6 (2025)
    Technique: Summarization

Example:
    Basic usage::

        from agenkit.techniques.compositions import ContextOptimizer
        from agenkit import Message

        optimizer = ContextOptimizer(
            agent=my_base_agent,
            summarizer=my_summary_agent,
            max_tokens=4000
        )

        response = await optimizer.process(long_message)
        print(f"Compressed {response.metadata['compression_ratio']:.1f}x")
"""

from typing import Callable, Optional
from agenkit import Agent, Message


class ContextOptimizer(Agent):
    """
    Context optimization composition.

    Wraps an agent and automatically summarizes context when it exceeds
    a token limit. This is a simple composition (~60 LOC) showing that
    context optimization is just conditional summarization.

    For production systems, consider:
    - Hierarchical summarization
    - Semantic chunking
    - Sliding window with caching
    - Token-aware conversation history management

    Attributes:
        name: Agent name (always "context_optimizer")
        agent: Base agent to wrap
        summarizer: Agent that performs summarization
        max_tokens: Maximum tokens before summarization
        token_counter: Function to count tokens
    """

    def __init__(
        self,
        agent: Agent,
        summarizer: Agent,
        max_tokens: int = 4000,
        token_counter: Optional[Callable[[str], int]] = None
    ):
        """
        Initialize context optimizer.

        Args:
            agent: Base agent to wrap with optimization
            summarizer: Agent that performs summarization.
                Should accept messages like "Summarize: {text}"
            max_tokens: Maximum tokens before triggering summarization.
                Default 4000.
            token_counter: Optional function to count tokens in a string.
                If None, uses simple word-based approximation (words * 1.3).

        Example:
            >>> optimizer = ContextOptimizer(
            ...     agent=my_agent,
            ...     summarizer=my_summary_agent,
            ...     max_tokens=2000
            ... )
        """
        self.agent = agent
        self.summarizer = summarizer
        self.max_tokens = max_tokens
        self.token_counter = token_counter or self._default_token_counter

    @property
    def name(self) -> str:
        """Return agent name."""
        return "context_optimizer"

    def _default_token_counter(self, text: str) -> int:
        """
        Simple token counter approximation.

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count (words * 1.3)
        """
        # Rough approximation: 1 word ≈ 1.3 tokens
        # For production, use tiktoken or similar
        word_count = len(text.split())
        return int(word_count * 1.3)

    async def _summarize_content(self, content: str) -> str:
        """
        Summarize content to reduce token count.

        Args:
            content: Content to summarize

        Returns:
            Summarized content
        """
        summary_request = f"""Summarize the following text concisely while preserving key information:

{content}

Summary:"""

        response = await self.summarizer.process(
            Message(role="user", content=summary_request)
        )

        return response.content

    async def process(self, message: Message) -> Message:
        """
        Process message with context optimization.

        If the message content exceeds max_tokens, it will be summarized
        before passing to the base agent.

        Args:
            message: Input message

        Returns:
            Message from base agent. Metadata includes:
                - optimized: Whether optimization was applied
                - original_tokens: Original token count
                - compressed_tokens: Token count after optimization (if applied)
                - compression_ratio: Reduction ratio (if applied)
                - technique: Always "context_optimization"

        Example:
            >>> response = await optimizer.process(Message(
            ...     role="user",
            ...     content=very_long_text
            ... ))
            >>> if response.metadata['optimized']:
            ...     print(f"Saved {response.metadata['compression_ratio']:.1f}x tokens")
        """
        original_content = message.content
        original_tokens = self.token_counter(original_content)

        metadata = {
            "technique": "context_optimization",
            "optimized": False,
            "original_tokens": original_tokens
        }

        # Check if optimization needed
        if original_tokens > self.max_tokens:
            # Summarize content
            summarized_content = await self._summarize_content(original_content)
            compressed_tokens = self.token_counter(summarized_content)

            # Update metadata
            metadata.update({
                "optimized": True,
                "compressed_tokens": compressed_tokens,
                "compression_ratio": original_tokens / compressed_tokens if compressed_tokens > 0 else 1.0
            })

            # Process with summarized content
            optimized_message = Message(
                role=message.role,
                content=summarized_content,
                metadata=message.metadata
            )
            response = await self.agent.process(optimized_message)
        else:
            # No optimization needed
            response = await self.agent.process(message)

        # Add optimization metadata
        if response.metadata:
            metadata.update(response.metadata)

        return Message(
            role=response.role,
            content=response.content,
            metadata=metadata
        )

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        base_caps = self.agent.capabilities if hasattr(self.agent, 'capabilities') else []
        return base_caps + [
            "context_optimization",
            "summarization",
            "token_management"
        ]
