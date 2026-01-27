#!/usr/bin/env python3
"""
AG-UI Core Adapter

Wraps any Agenkit agent and translates Agent.process() calls into AG-UI event streams.
Enables agents to communicate with frontends using the AG-UI protocol.

Reference: https://docs.ag-ui.com/protocol

Example:
    from agenkit import Agent, Message
    from agenkit.protocols.agui import AGUIAdapter, TextMessageChunk

    # Wrap any agent
    agent = MyAgent()
    agui_agent = AGUIAdapter(agent)

    # Process returns AG-UI events
    async for event in agui_agent.stream_events(message):
        if isinstance(event, TextMessageChunk):
            print(event.content, end="", flush=True)
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from agenkit import Agent, Message
from agenkit.protocols.agui.events import (
    AGUIEvent,
    ErrorEvent,
    HeartbeatEvent,
    MetadataEvent,
    TextMessageChunk,
    TextMessageComplete,
    TextMessageStart,
)


class AGUIAdapter:
    """
    Wraps an Agenkit agent to produce AG-UI protocol events.

    Converts standard Agent.process() calls into streaming AG-UI events
    that can be consumed by frontends implementing the AG-UI protocol.

    Features:
    - Automatic event generation from agent responses
    - Streaming text message support
    - Error handling with ErrorEvents
    - Metadata emission for agent capabilities
    - Message ID tracking for correlation

    Example:
        # Wrap any agent
        agent = MyReActAgent(llm=llm, tools=tools)
        agui = AGUIAdapter(agent)

        # Stream events to frontend
        message = Message(role="user", content="What's the weather?")
        async for event in agui.stream_events(message):
            # Send event to frontend via HTTP/SSE or WebSocket
            await send_to_frontend(event.to_json_line())
    """

    def __init__(
        self,
        agent: Agent,
        agent_name: str | None = None,
        emit_heartbeats: bool = False,
        heartbeat_interval: float = 30.0,
    ) -> None:
        """
        Initialize AG-UI adapter for an agent.

        Args:
            agent: The Agenkit agent to wrap
            agent_name: Optional name for the agent (defaults to agent.name)
            emit_heartbeats: Whether to emit heartbeat events
            heartbeat_interval: Seconds between heartbeat events (if enabled)
        """
        self._agent = agent
        self._agent_name = agent_name or agent.name
        self._emit_heartbeats = emit_heartbeats
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_sequence = 0

    @property
    def agent(self) -> Agent:
        """Return the wrapped agent."""
        return self._agent

    @property
    def agent_name(self) -> str:
        """Return the agent's name."""
        return self._agent_name

    async def stream_events(
        self,
        message: Message,
        message_id: str | None = None,
        emit_metadata: bool = True,
    ) -> AsyncIterator[AGUIEvent]:
        """
        Process message and stream AG-UI events.

        Converts agent's response into a stream of AG-UI events:
        1. MetadataEvent (optional) - Agent capabilities
        2. TextMessageStart - Beginning of response
        3. TextMessageChunk(s) - Streaming content
        4. TextMessageComplete - End of response

        Args:
            message: Input message to process
            message_id: Optional message ID (auto-generated if not provided)
            emit_metadata: Whether to emit metadata event first

        Yields:
            AG-UI events representing the agent's response

        Example:
            async for event in adapter.stream_events(user_message):
                if isinstance(event, TextMessageChunk):
                    print(event.content, end="", flush=True)
                elif isinstance(event, TextMessageComplete):
                    print(f"\n[Finished: {event.finish_reason}]")
        """
        msg_id = message_id or self._generate_message_id()

        # Emit metadata about agent capabilities
        if emit_metadata:
            yield self._create_metadata_event()

        # Emit text message start
        yield TextMessageStart(
            message_id=msg_id,
            role="assistant",
            metadata={"agent_name": self._agent_name},
        )

        try:
            # Process message with agent
            response = await self._agent.process(message)

            # Extract content
            content = str(response.content) if response.content else ""

            # Stream content in chunks (simulating streaming)
            # In a real streaming implementation, this would yield as content arrives
            chunk_size = 50  # Characters per chunk
            for i in range(0, len(content), chunk_size):
                chunk = content[i : i + chunk_size]
                yield TextMessageChunk(
                    message_id=msg_id,
                    content=chunk,
                    metadata={"chunk_index": i // chunk_size},
                )

            # Emit completion
            yield TextMessageComplete(
                message_id=msg_id,
                content=content,
                finish_reason="stop",
                metadata={
                    "agent_name": self._agent_name,
                    "response_metadata": response.metadata,
                },
            )

        except Exception as e:
            # Convert exceptions to error events
            yield self._create_error_event(msg_id, e)

            # Also emit a completion with error
            yield TextMessageComplete(
                message_id=msg_id,
                content="",
                finish_reason="error",
                metadata={"error": str(e)},
            )

    async def process(
        self,
        message: Message,
        message_id: str | None = None,
    ) -> Message:
        """
        Process message and return final result (non-streaming).

        Convenience method that consumes all events and returns the
        final message. Use stream_events() if you need streaming.

        Args:
            message: Input message to process
            message_id: Optional message ID

        Returns:
            Final message with complete response
        """
        final_content = ""
        final_metadata: dict[str, Any] = {}

        async for event in self.stream_events(message, message_id, emit_metadata=False):
            if isinstance(event, TextMessageComplete):
                final_content = event.content
                final_metadata = event.metadata

        return Message(
            role="assistant",
            content=final_content,
            metadata=final_metadata,
        )

    def _generate_message_id(self) -> str:
        """Generate a unique message ID."""
        return f"msg-{uuid.uuid4().hex[:12]}"

    def _create_metadata_event(self) -> MetadataEvent:
        """Create metadata event with agent capabilities."""
        return MetadataEvent(
            data={
                "agent_name": self._agent_name,
                "agent_type": self._agent.__class__.__name__,
                "capabilities": self._agent.capabilities,
                "protocol_version": "1.0",
            }
        )

    def _create_error_event(self, message_id: str, exception: Exception) -> ErrorEvent:
        """Create error event from exception."""
        error_type = exception.__class__.__name__

        return ErrorEvent(
            error_code=error_type,
            error_message=str(exception),
            error_details={
                "message_id": message_id,
                "agent_name": self._agent_name,
                "exception_type": error_type,
            },
            recoverable=not isinstance(exception, (SystemError, MemoryError)),
        )

    def _create_heartbeat_event(self) -> HeartbeatEvent:
        """Create heartbeat event."""
        event = HeartbeatEvent(sequence=self._heartbeat_sequence)
        self._heartbeat_sequence += 1
        return event


class StreamingAGUIAdapter(AGUIAdapter):
    """
    AG-UI adapter with native streaming support.

    For agents that support streaming (via a stream() method or similar),
    this adapter provides true streaming instead of chunking complete responses.

    Note: Requires the wrapped agent to support streaming. If the agent doesn't
    have a stream() method, falls back to AGUIAdapter behavior.
    """

    async def stream_events(
        self,
        message: Message,
        message_id: str | None = None,
        emit_metadata: bool = True,
    ) -> AsyncIterator[AGUIEvent]:
        """
        Stream events with native agent streaming support.

        If the agent has a stream() method, uses it for true streaming.
        Otherwise, falls back to standard chunked streaming.
        """
        msg_id = message_id or self._generate_message_id()

        # Emit metadata
        if emit_metadata:
            yield self._create_metadata_event()

        # Emit start
        yield TextMessageStart(
            message_id=msg_id,
            role="assistant",
            metadata={"agent_name": self._agent_name},
        )

        # Check if agent supports streaming
        if hasattr(self._agent, "stream") and callable(self._agent.stream):
            # Native streaming
            try:
                full_content = ""
                chunk_index = 0

                async for chunk in self._agent.stream(message):
                    content = str(chunk) if chunk else ""
                    full_content += content

                    yield TextMessageChunk(
                        message_id=msg_id,
                        content=content,
                        metadata={"chunk_index": chunk_index},
                    )
                    chunk_index += 1

                # Emit completion
                yield TextMessageComplete(
                    message_id=msg_id,
                    content=full_content,
                    finish_reason="stop",
                    metadata={"agent_name": self._agent_name, "streamed": True},
                )

            except Exception as e:
                yield self._create_error_event(msg_id, e)
                yield TextMessageComplete(
                    message_id=msg_id,
                    content="",
                    finish_reason="error",
                    metadata={"error": str(e)},
                )
        else:
            # Fallback to parent implementation
            async for event in super().stream_events(message, msg_id, emit_metadata=False):
                yield event


async def wrap_agent_as_agui(
    agent: Agent,
    message: Message,
    agent_name: str | None = None,
) -> AsyncIterator[AGUIEvent]:
    """
    Convenience function to wrap an agent and stream events.

    Quick way to convert any agent to AG-UI without creating an adapter instance.

    Args:
        agent: Agent to wrap
        message: Message to process
        agent_name: Optional agent name

    Yields:
        AG-UI events from agent's response

    Example:
        async for event in wrap_agent_as_agui(my_agent, user_message):
            print(event.to_json_line())
    """
    adapter = AGUIAdapter(agent, agent_name=agent_name)
    async for event in adapter.stream_events(message):
        yield event
