#!/usr/bin/env python3
"""
AG-UI Human-in-the-Loop Integration

Integrates the HumanInLoopAgent pattern with AG-UI protocol using Interrupt events.
Provides streaming approval workflow where agents can request human approval via
Interrupt events, and frontends can respond with InterruptResponse messages.

Key concepts:
- Interrupt events for approval requests
- InterruptResponse for approval decisions
- Streaming approval workflow
- Integration with HumanInLoopAgent pattern

Example:
    from agenkit.protocols.agui.hitl import AGUIHumanInLoopAdapter
    from agenkit.patterns.human_in_loop import HumanInLoopConfig, HumanInLoopAgent

    # Create human-in-loop agent
    hil_agent = HumanInLoopAgent(HumanInLoopConfig(
        agent=my_agent,
        approval_func=my_approval_func,
        approval_threshold=0.8
    ))

    # Wrap with AG-UI adapter
    adapter = AGUIHumanInLoopAdapter(hil_agent)

    # Stream events (includes Interrupt events for approval requests)
    async for event in adapter.stream_events(user_message):
        if isinstance(event, Interrupt):
            # Frontend displays approval request
            # User responds via InterruptResponse
            pass
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from agenkit.core import Message

from agenkit.protocols.agui.adapter import AGUIAdapter
from agenkit.protocols.agui.events import (
    AGUIEvent,
    Interrupt,
    InterruptAction,
    InterruptReason,
    InterruptResponse,
    MetadataEvent,
    TextMessageChunk,
    TextMessageComplete,
    TextMessageStart,
)


class AGUIHumanInLoopAdapter(AGUIAdapter):
    """
    AG-UI adapter with human-in-the-loop support via Interrupt events.

    This adapter integrates the HumanInLoopAgent pattern with AG-UI protocol.
    When an agent requires approval (confidence < threshold), an Interrupt event
    is emitted to request human approval. The frontend can respond via
    InterruptResponse.

    The adapter handles:
    - Converting approval requests to Interrupt events
    - Processing InterruptResponse from frontend
    - Streaming approval workflow
    - Metadata about approval decisions

    Example:
        >>> from agenkit.patterns.human_in_loop import HumanInLoopAgent, HumanInLoopConfig
        >>> from agenkit.protocols.agui.hitl import AGUIHumanInLoopAdapter
        >>>
        >>> # Create approval function that emits interrupts
        >>> async def agui_approval_func(request):
        ...     # This will be called by HumanInLoopAgent
        ...     # In practice, you'd use interrupt_callback to emit Interrupt event
        ...     return ApprovalResponse(approved=True)
        ...
        >>> hil_agent = HumanInLoopAgent(HumanInLoopConfig(
        ...     agent=my_agent,
        ...     approval_func=agui_approval_func,
        ...     approval_threshold=0.8
        ... ))
        ...
        >>> adapter = AGUIHumanInLoopAdapter(hil_agent)
        >>> async for event in adapter.stream_events(message):
        ...     if isinstance(event, Interrupt):
        ...         # Display approval request to user
        ...         pass
    """

    def __init__(
        self,
        agent: Any,  # HumanInLoopAgent or regular Agent
        agent_name: str | None = None,
        emit_interrupts: bool = True,
    ) -> None:
        """
        Initialize AG-UI human-in-loop adapter.

        Args:
            agent: Agent to wrap (HumanInLoopAgent or regular Agent)
            agent_name: Optional agent name for metadata
            emit_interrupts: Whether to emit Interrupt events for approval requests
        """
        super().__init__(agent, agent_name=agent_name)
        self._emit_interrupts = emit_interrupts
        self._pending_interrupts: dict[str, Any] = {}  # interrupt_id -> context

    async def stream_events(
        self,
        message: Message,
        emit_metadata: bool = True,
    ) -> AsyncIterator[AGUIEvent]:
        """
        Stream AG-UI events with interrupt support.

        When the agent requires approval, emits an Interrupt event to notify
        the frontend about the approval decision.

        Note: This implementation emits Interrupt events after the approval
        decision has been made (informational). For true bidirectional HITL,
        use a custom approval_func that integrates with your transport layer.

        Args:
            message: Input message to process
            emit_metadata: Whether to emit MetadataEvent first

        Yields:
            AG-UI events (includes Interrupt events for approval notifications)

        Example:
            >>> async for event in adapter.stream_events(message):
            ...     if isinstance(event, Interrupt):
            ...         # Approval decision was made
            ...         print(f"Approval: {event.context['approval_status']}")
        """
        # Check if agent is a HumanInLoopAgent
        from agenkit.patterns.human_in_loop import HumanInLoopAgent

        is_hil_agent = isinstance(self._agent, HumanInLoopAgent)

        # For regular agents or if interrupts disabled, use standard streaming
        if not is_hil_agent or not self._emit_interrupts:
            async for event in super().stream_events(message, emit_metadata):
                yield event
            return

        # Emit metadata if requested
        if emit_metadata:
            yield self._create_metadata_event()

        # Process message (HumanInLoopAgent will handle approval synchronously)
        response = await self._agent.process(message)

        # Check if approval was involved (approved, rejected, or bypassed)
        # approval_status indicates approval workflow was used
        approval_status = (
            response.metadata.get("approval_status") if response.metadata else None
        )

        # Emit Interrupt event if approval was part of the flow (not bypassed)
        if approval_status in ("approved", "rejected", "approved_with_modifications"):
            interrupt_id = str(uuid4())
            confidence = response.metadata.get("confidence", 0.0)

            # Emit informational Interrupt event about the approval
            interrupt = Interrupt(
                interrupt_id=interrupt_id,
                reason=InterruptReason.APPROVAL_REQUIRED,
                message=f"Approval {approval_status} (confidence: {confidence:.2f})",
                context={
                    "approval_status": approval_status,
                    "confidence": confidence,
                    "approval_threshold": response.metadata.get("approval_threshold"),
                    "approval_needed": True,  # Was needed based on status
                },
                actions=[],  # No actions - already decided
                timeout_seconds=None,
            )
            yield interrupt

        # Stream the response content as text message events
        msg_id = self._generate_message_id()

        yield TextMessageStart(
            message_id=msg_id,
            role="assistant",
            metadata={"agent_name": self._agent_name or self._agent.name},
        )

        # Extract content
        content = str(response.content) if response.content else ""

        # Stream content in chunks
        chunk_size = 50
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
                "agent_name": self._agent_name or self._agent.name,
                **response.metadata,
            },
        )

    async def handle_interrupt_response(self, interrupt_response: InterruptResponse) -> None:
        """
        Handle InterruptResponse from frontend.

        This is called when the frontend responds to an Interrupt event.
        Updates the pending interrupt context with the approval decision.

        Args:
            interrupt_response: Response from frontend with approval decision

        Raises:
            ValueError: If interrupt_id not found in pending interrupts
        """
        interrupt_id = interrupt_response.interrupt_id
        if interrupt_id not in self._pending_interrupts:
            raise ValueError(f"Unknown interrupt_id: {interrupt_id}")

        context = self._pending_interrupts[interrupt_id]
        response = context["response"]

        # Update response metadata based on user action
        if not response.metadata:
            response.metadata = {}

        if interrupt_response.action == InterruptAction.APPROVE:
            response.metadata["approval_status"] = "approved"
            if interrupt_response.data and isinstance(interrupt_response.data, dict):
                feedback = interrupt_response.data.get("feedback")
                if feedback:
                    response.metadata["approval_feedback"] = feedback

        elif interrupt_response.action == InterruptAction.REJECT:
            response.metadata["approval_status"] = "rejected"
            if interrupt_response.data and isinstance(interrupt_response.data, dict):
                reason = interrupt_response.data.get("reason")
                if reason:
                    response.metadata["rejection_reason"] = reason

        elif interrupt_response.action == InterruptAction.EDIT:
            response.metadata["approval_status"] = "approved_with_modifications"
            response.metadata["original_response"] = response.content
            if interrupt_response.data and isinstance(interrupt_response.data, dict):
                modified_content = interrupt_response.data.get("modified_content")
                if modified_content:
                    response.content = modified_content

        # Remove from pending
        del self._pending_interrupts[interrupt_id]

    def _create_metadata_event(self) -> MetadataEvent:
        """Create metadata event with HITL capabilities."""
        # Get base metadata from parent
        base_metadata = super()._create_metadata_event()

        # Add HITL capabilities if agent supports it
        from agenkit.patterns.human_in_loop import HumanInLoopAgent

        if isinstance(self._agent, HumanInLoopAgent):
            # Extend capabilities
            if "capabilities" not in base_metadata.data:
                base_metadata.data["capabilities"] = []
            base_metadata.data["capabilities"].extend(["human-in-loop", "approval", "interrupts"])

            # Add HITL metadata
            base_metadata.data["supports_hitl"] = True

        return base_metadata


__all__ = [
    "AGUIHumanInLoopAdapter",
]
