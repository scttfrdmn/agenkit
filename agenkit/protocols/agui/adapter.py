"""AG-UI Standard Adapter for Agenkit Agents.

This module provides the main adapter that wraps Agenkit agents and
emits AG-UI Standard protocol events.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Optional
from uuid import uuid4

from agenkit import Agent, Message
from agenkit.protocols.agui.events import (
    Event,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)


class AGUIAdapter:
    """Adapts Agenkit agents to emit AG-UI Standard protocol events.

    This adapter wraps any Agenkit agent and converts its responses into
    AG-UI Standard events for streaming to frontends.

    Args:
        agent: The Agenkit agent to wrap
        chunk_size: Number of characters per content event (default: 20)
        agent_name: Optional name for the agent (for metadata)

    Example:
        ```python
        from agenkit import Agent, Message
        from agenkit.protocols.agui import AGUIAdapter

        agent = MyAgent()
        adapter = AGUIAdapter(agent, chunk_size=10)

        async for event in adapter.stream_events(
            message=Message(role="user", content="Hello"),
            thread_id="thread-123",
            run_id="run-456"
        ):
            print(f"Event: {event.type}")
        ```
    """

    def __init__(
        self,
        agent: Agent,
        chunk_size: int = 20,
        agent_name: Optional[str] = None,
    ):
        """Initialize the AG-UI adapter.

        Args:
            agent: The agent to wrap
            chunk_size: Characters per content event
            agent_name: Optional agent name
        """
        self.agent = agent
        self.chunk_size = chunk_size
        self.agent_name = agent_name or agent.__class__.__name__

    async def stream_events(
        self,
        message: Message,
        thread_id: str,
        run_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        input_data: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[Event]:
        """Stream AG-UI events for a message.

        This method processes a message through the agent and yields
        AG-UI Standard protocol events.

        Args:
            message: The user message to process
            thread_id: Conversation thread identifier
            run_id: Run identifier (generated if not provided)
            parent_run_id: Parent run ID for nested executions
            input_data: Optional input parameters

        Yields:
            AG-UI Standard Event objects

        Example:
            ```python
            async for event in adapter.stream_events(
                message=Message(role="user", content="Hello"),
                thread_id="thread-abc",
            ):
                if event.type == EventType.TEXT_MESSAGE_CONTENT:
                    print(event.delta, end="", flush=True)
            ```
        """
        # Generate run ID if not provided
        if run_id is None:
            run_id = f"run-{uuid4()}"

        # Emit RunStarted
        yield RunStartedEvent(
            thread_id=thread_id,
            run_id=run_id,
            parent_run_id=parent_run_id,
            input=input_data or {"message": message.content},
        )

        try:
            # Process message through agent
            response = await self.agent.process(message)

            # Generate message ID
            message_id = f"msg-{uuid4()}"

            # Emit TextMessageStart
            yield TextMessageStartEvent(
                message_id=message_id,
                role="assistant",
                metadata=response.metadata if hasattr(response, "metadata") else None,
            )

            # Stream content in chunks
            content = response.content
            for i in range(0, len(content), self.chunk_size):
                chunk = content[i : i + self.chunk_size]
                yield TextMessageContentEvent(
                    message_id=message_id,
                    delta=chunk,
                )
                # Small delay for realistic streaming
                await asyncio.sleep(0.01)

            # Emit TextMessageEnd
            yield TextMessageEndEvent(
                message_id=message_id,
                metadata=response.metadata if hasattr(response, "metadata") else None,
            )

            # Emit RunFinished
            yield RunFinishedEvent(
                thread_id=thread_id,
                run_id=run_id,
                result={"message_id": message_id, "content": response.content},
            )

        except Exception as e:
            # Emit RunError on failure
            yield RunErrorEvent(
                message=str(e),
                code=type(e).__name__,
                details={"thread_id": thread_id, "run_id": run_id},
            )

    async def stream_with_steps(
        self,
        message: Message,
        thread_id: str,
        run_id: Optional[str] = None,
        steps: Optional[list[str]] = None,
    ) -> AsyncIterator[Event]:
        """Stream events with step tracking.

        This is useful for agents with multiple processing phases.

        Args:
            message: The user message
            thread_id: Thread identifier
            run_id: Run identifier
            steps: List of step names to track

        Yields:
            AG-UI Standard Event objects including StepStarted/StepFinished
        """
        # TODO: Implement step tracking
        # For now, delegate to basic streaming
        async for event in self.stream_events(message, thread_id, run_id):
            yield event


__all__ = ["AGUIAdapter"]
