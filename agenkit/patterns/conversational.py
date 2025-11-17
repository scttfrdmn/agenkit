"""
Conversational Agent Pattern

A conversational agent maintains context across multiple turns of conversation,
managing message history and ensuring responses take into account previous exchanges.

Key Features:
- Message history management
- Context window limiting
- Automatic history pruning
- Support for different history strategies
"""

from typing import List, Optional, Protocol
import asyncio

from agenkit import Agent, Message


class LLMClient(Protocol):
    """Protocol for LLM clients that can be used with ConversationalAgent."""

    async def chat(self, messages: List[Message]) -> Message:
        """Generate a response given a conversation history."""
        ...


class ConversationalAgent(Agent):
    """
    Agent that maintains conversation history for context-aware responses.

    This agent stores previous messages and includes them when processing new messages,
    allowing the LLM to maintain context across multiple turns.

    Example:
        ```python
        from agenkit.patterns import ConversationalAgent
        from my_llm import MyLLMClient

        llm = MyLLMClient(model="gpt-4")
        agent = ConversationalAgent(
            llm_client=llm,
            max_history=10,
            system_prompt="You are a helpful assistant."
        )

        # First turn
        response1 = await agent.process(
            Message(role="user", content="My name is Alice")
        )
        # Response: "Nice to meet you, Alice!"

        # Second turn - agent remembers the name
        response2 = await agent.process(
            Message(role="user", content="What's my name?")
        )
        # Response: "Your name is Alice."
        ```

    Args:
        llm_client: LLM client that implements the chat interface
        max_history: Maximum number of messages to retain (default: 10)
        system_prompt: Optional system prompt to prepend to conversations
        include_system: Whether to include system prompt in history (default: True)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        max_history: int = 10,
        system_prompt: Optional[str] = None,
        include_system: bool = True,
    ):
        self.llm = llm_client
        self.max_history = max_history
        self.system_prompt = system_prompt
        self.include_system = include_system
        self.history: List[Message] = []

        # Add system prompt to history if provided
        if system_prompt and include_system:
            self.history.append(Message(role="system", content=system_prompt))

    @property
    def name(self) -> str:
        """Return the agent's name."""
        return "ConversationalAgent"

    async def process(self, message: Message) -> Message:
        """
        Process a message with full conversation context.

        The message is added to history, and the LLM generates a response
        considering all previous messages within the history limit.

        Args:
            message: The incoming user message

        Returns:
            The agent's response message

        Note:
            Both the input message and the response are added to history.
            If history exceeds max_history, oldest non-system messages are removed.
        """
        # Add user message to history
        self.history.append(message)

        # Prune history if needed (keep system prompt if present)
        self._prune_history()

        # Generate response with full context
        response = await self.llm.chat(self.history)

        # Add response to history
        self.history.append(response)

        # Prune again after adding response
        self._prune_history()

        return response

    def _prune_history(self) -> None:
        """
        Prune history to stay within max_history limit.

        System messages are preserved, and oldest user/assistant messages
        are removed first.
        """
        if len(self.history) <= self.max_history:
            return

        # Separate system messages from conversation
        system_messages = [msg for msg in self.history if msg.role == "system"]
        conversation_messages = [msg for msg in self.history if msg.role != "system"]

        # Keep only the most recent conversation messages
        messages_to_keep = self.max_history - len(system_messages)
        if messages_to_keep > 0:
            conversation_messages = conversation_messages[-messages_to_keep:]
        else:
            conversation_messages = []

        # Rebuild history with system messages first
        self.history = system_messages + conversation_messages

    def clear_history(self, keep_system: bool = True) -> None:
        """
        Clear conversation history.

        Args:
            keep_system: If True, preserves system prompt (default: True)
        """
        if keep_system and self.system_prompt and self.include_system:
            self.history = [Message(role="system", content=self.system_prompt)]
        else:
            self.history = []

    def get_history(self) -> List[Message]:
        """
        Get a copy of the current conversation history.

        Returns:
            List of messages in conversation history
        """
        return self.history.copy()

    def get_context_length(self) -> int:
        """
        Get the current number of messages in history.

        Returns:
            Number of messages in history
        """
        return len(self.history)

    def export_history(self) -> List[dict]:
        """
        Export history in a serializable format.

        Returns:
            List of message dictionaries
        """
        return [
            {"role": msg.role, "content": msg.content, "metadata": msg.metadata}
            for msg in self.history
        ]

    def import_history(self, history: List[dict]) -> None:
        """
        Import conversation history from serialized format.

        Useful for resuming conversations or testing.

        Args:
            history: List of message dictionaries with role and content
        """
        self.history = [
            Message(
                role=msg["role"],
                content=msg["content"],
                metadata=msg.get("metadata", {}),
            )
            for msg in history
        ]


class StreamingConversationalAgent(ConversationalAgent):
    """
    Conversational agent with streaming response support.

    Extends ConversationalAgent to support streaming responses from the LLM,
    useful for providing real-time feedback to users.

    Example:
        ```python
        agent = StreamingConversationalAgent(llm_client=llm)

        async for chunk in agent.stream(
            Message(role="user", content="Tell me a story")
        ):
            print(chunk.content, end="", flush=True)
        ```
    """

    async def stream(self, message: Message):
        """
        Process message and stream response chunks.

        Args:
            message: The incoming user message

        Yields:
            Message chunks as they are generated

        Note:
            The complete response is added to history after streaming completes.
        """
        # Add user message to history
        self.history.append(message)
        self._prune_history()

        # Collect chunks for history
        response_chunks = []

        # Stream response
        async for chunk in self.llm.stream(self.history):
            response_chunks.append(chunk)
            yield chunk

        # Combine chunks into full response
        full_content = "".join(chunk.content for chunk in response_chunks)
        full_response = Message(role="assistant", content=full_content)

        # Add to history
        self.history.append(full_response)
        self._prune_history()
