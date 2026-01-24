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
- Bidirectional HITL: Agent pauses, frontend responds, agent resumes

Example:
    from agenkit.protocols.agui.hitl import AGUIHumanInLoopAdapter
    from agenkit.patterns.human_in_loop import HumanInLoopConfig, HumanInLoopAgent

    # Create adapter (bidirectional mode)
    adapter = AGUIHumanInLoopAdapter(
        my_agent,
        approval_threshold=0.8,
        bidirectional=True,
        timeout=300.0
    )

    # Stream events (includes Interrupt events for approval requests)
    async for event in adapter.stream_events(user_message):
        if isinstance(event, Interrupt):
            # Frontend displays approval request
            # User responds via handle_interrupt_response()
            pass
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from agenkit.core import Agent

from agenkit import Message
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

    This adapter supports two modes:

    1. **Legacy Mode** (bidirectional=False): Works with HumanInLoopAgent, emits
       informational Interrupt events after approval decisions are made.

    2. **Bidirectional Mode** (bidirectional=True): Implements true interactive HITL
       where the agent pauses execution, emits an Interrupt event, waits for the
       frontend's InterruptResponse, then resumes based on user's decision.

    The adapter handles:
    - Converting approval requests to Interrupt events
    - Processing InterruptResponse from frontend
    - Streaming approval workflow with async coordination
    - Timeout handling for unresponsive users
    - Metadata about approval decisions

    Example (Bidirectional Mode):
        >>> from agenkit.protocols.agui.hitl import AGUIHumanInLoopAdapter
        >>>
        >>> # Create bidirectional HITL adapter
        >>> adapter = AGUIHumanInLoopAdapter(
        ...     my_agent,
        ...     approval_threshold=0.8,
        ...     bidirectional=True,
        ...     timeout=300.0  # 5 minute timeout
        ... )
        >>>
        >>> # Stream events
        >>> async for event in adapter.stream_events(message):
        ...     if isinstance(event, Interrupt):
        ...         # Display approval UI to user
        ...         # User responds via adapter.handle_interrupt_response()
        ...         pass

    Example (Legacy Mode):
        >>> from agenkit.patterns.human_in_loop import HumanInLoopAgent, HumanInLoopConfig
        >>> from agenkit.protocols.agui.hitl import AGUIHumanInLoopAdapter
        >>>
        >>> hil_agent = HumanInLoopAgent(HumanInLoopConfig(
        ...     agent=my_agent,
        ...     approval_func=my_approval_func,
        ...     approval_threshold=0.8
        ... ))
        >>>
        >>> adapter = AGUIHumanInLoopAdapter(hil_agent, bidirectional=False)
        >>> async for event in adapter.stream_events(message):
        ...     if isinstance(event, Interrupt):
        ...         # Informational - approval already decided
        ...         pass
    """

    def __init__(
        self,
        agent: Agent,
        agent_name: str | None = None,
        emit_interrupts: bool = True,
        bidirectional: bool = False,
        approval_threshold: float = 0.8,
        confidence_key: str = "confidence",
        timeout: float = 300.0,
    ) -> None:
        """
        Initialize AG-UI human-in-loop adapter.

        Args:
            agent: Agent to wrap (HumanInLoopAgent for legacy mode, any Agent for bidirectional)
            agent_name: Optional agent name for metadata
            emit_interrupts: Whether to emit Interrupt events for approval requests
            bidirectional: Enable true bidirectional HITL (agent pauses, waits for response)
            approval_threshold: Confidence threshold for requiring approval (0.0-1.0)
            confidence_key: Metadata key to extract confidence from agent response
            timeout: Timeout in seconds for waiting for InterruptResponse (default: 300s)
        """
        super().__init__(agent, agent_name=agent_name)
        self._emit_interrupts = emit_interrupts
        self._bidirectional = bidirectional
        self._approval_threshold = approval_threshold
        self._confidence_key = confidence_key
        self._timeout = timeout

        # State management for bidirectional mode
        self._pending_interrupts: dict[str, asyncio.Event] = {}  # interrupt_id -> Event
        self._interrupt_responses: dict[str, InterruptResponse] = {}  # interrupt_id -> response
        self._interrupt_contexts: dict[str, dict[str, Any]] = {}  # interrupt_id -> context

    async def stream_events(
        self,
        message: Message,
        message_id: str | None = None,
        emit_metadata: bool = True,
    ) -> AsyncIterator[AGUIEvent]:
        """
        Stream AG-UI events with interrupt support.

        Supports two modes:

        **Bidirectional Mode** (bidirectional=True):
        - Agent execution pauses when approval is needed (confidence < threshold)
        - Emits Interrupt event with available actions [APPROVE, REJECT, EDIT]
        - Waits for frontend's InterruptResponse (with timeout)
        - Resumes or rejects based on user's decision

        **Legacy Mode** (bidirectional=False):
        - Works with HumanInLoopAgent
        - Emits informational Interrupt events after approval decisions

        Args:
            message: Input message to process
            emit_metadata: Whether to emit MetadataEvent first

        Yields:
            AG-UI events (includes Interrupt events for approval requests)

        Raises:
            RuntimeError: If approval timeout occurs and no default action configured

        Example (Bidirectional):
            >>> async for event in adapter.stream_events(message):
            ...     if isinstance(event, Interrupt):
            ...         # Display approval UI
            ...         # Call adapter.handle_interrupt_response() with user's decision
            ...         pass
        """
        # Emit metadata if requested
        if emit_metadata:
            yield self._create_metadata_event()

        # Branch based on mode
        if self._bidirectional:
            # True bidirectional HITL workflow
            async for event in self._stream_bidirectional(message):
                yield event
        else:
            # Legacy mode (informational interrupts)
            async for event in self._stream_legacy(message):
                yield event

    async def _stream_bidirectional(self, message: Message) -> AsyncIterator[AGUIEvent]:
        """
        Bidirectional HITL workflow: pause, wait for approval, resume.

        This implements true interactive HITL where the agent pauses execution
        to wait for user approval before continuing.
        """
        # Get initial agent response to extract confidence
        response = await self._agent.process(message)
        confidence = self._extract_confidence(response)

        # If high confidence, proceed without approval
        if confidence >= self._approval_threshold:
            msg_id = self._generate_message_id()
            async for event in self._stream_text_message(response, msg_id):
                yield event
            return

        # Approval needed - emit interrupt and wait
        interrupt_id = str(uuid4())
        approval_event = self._setup_interrupt(interrupt_id, message, response, confidence)

        # Emit Interrupt
        interrupt = self._create_interrupt_event(interrupt_id, confidence, message, response)
        yield interrupt

        # Wait for response
        interrupt_response = await self._wait_for_interrupt_response(
            interrupt_id, approval_event, confidence
        )
        if interrupt_response is None:
            # Timeout occurred - emit rejection message
            timeout_msg = Message(
                role="agent",
                content="Action timed out waiting for approval",
                metadata={
                    "approval_status": "timeout",
                    "confidence": confidence,
                    "timeout_seconds": self._timeout,
                },
            )
            msg_id = self._generate_message_id()
            async for event in self._stream_text_message(timeout_msg, msg_id):
                yield event
            return

        # Process user's decision
        async for event in self._process_interrupt_action(interrupt_response, response, confidence):
            yield event

    def _setup_interrupt(
        self,
        interrupt_id: str,
        message: Message,
        response: Message,
        confidence: float,
    ) -> asyncio.Event:
        """Set up interrupt state for bidirectional HITL."""
        approval_event = asyncio.Event()
        self._pending_interrupts[interrupt_id] = approval_event
        self._interrupt_contexts[interrupt_id] = {
            "message": message,
            "response": response,
            "confidence": confidence,
        }
        return approval_event

    def _create_interrupt_event(
        self,
        interrupt_id: str,
        confidence: float,
        message: Message,
        response: Message,
    ) -> Interrupt:
        """Create Interrupt event for approval request."""
        return Interrupt(
            interrupt_id=interrupt_id,
            reason=InterruptReason.APPROVAL_REQUIRED,
            message=f"Agent confidence ({confidence:.2f}) below threshold ({self._approval_threshold:.2f}). "
            f"Approval required to proceed.",
            context={
                "confidence": confidence,
                "approval_threshold": self._approval_threshold,
                "agent_name": self._agent_name or self._agent.name,
                "original_message": str(message.content),
                "proposed_response": str(response.content),
            },
            actions=[
                InterruptAction.APPROVE,
                InterruptAction.REJECT,
                InterruptAction.EDIT,
            ],
            timeout_seconds=self._timeout,
        )

    async def _wait_for_interrupt_response(
        self,
        interrupt_id: str,
        approval_event: asyncio.Event,
        confidence: float,
    ) -> InterruptResponse | None:
        """
        Wait for InterruptResponse with timeout.

        Returns None if timeout occurs (caller should handle rejection).
        """
        try:
            await asyncio.wait_for(approval_event.wait(), timeout=self._timeout)
            # Get and return user's decision
            interrupt_response = self._interrupt_responses.pop(interrupt_id, None)
            self._cleanup_interrupt(interrupt_id)
            return interrupt_response
        except TimeoutError:
            # Timeout - clean up and return None
            self._cleanup_interrupt(interrupt_id)
            return None

    async def _process_interrupt_action(
        self,
        interrupt_response: InterruptResponse,
        response: Message,
        confidence: float,
    ) -> AsyncIterator[AGUIEvent]:
        """Process user's interrupt response action."""
        if interrupt_response.action == InterruptAction.APPROVE:
            async for event in self._handle_approve_action(
                interrupt_response, response, confidence
            ):
                yield event
        elif interrupt_response.action == InterruptAction.REJECT:
            async for event in self._handle_reject_action(interrupt_response, response, confidence):
                yield event
        elif interrupt_response.action == InterruptAction.EDIT:
            async for event in self._handle_edit_action(interrupt_response, response, confidence):
                yield event
        else:
            # Unknown action - reject
            rejection_msg = Message(
                role="agent",
                content=f"Unknown interrupt action: {interrupt_response.action}",
                metadata={"approval_status": "rejected", "confidence": confidence},
            )
            msg_id = self._generate_message_id()
            async for event in self._stream_text_message(rejection_msg, msg_id):
                yield event

    async def _handle_approve_action(
        self,
        interrupt_response: InterruptResponse,
        response: Message,
        confidence: float,
    ) -> AsyncIterator[AGUIEvent]:
        """Handle APPROVE action."""
        # Create new metadata dict
        metadata = {**(response.metadata or {})}
        metadata["approval_status"] = "approved"
        metadata["confidence"] = confidence

        # Add feedback if provided
        if interrupt_response.context:
            feedback = interrupt_response.context.get("feedback")
            if feedback:
                metadata["approval_feedback"] = feedback

        # Create new message with updated metadata
        approved_response = Message(
            role=response.role,
            content=response.content,
            metadata=metadata,
        )

        msg_id = self._generate_message_id()
        async for event in self._stream_text_message(approved_response, msg_id):
            yield event

    async def _handle_reject_action(
        self,
        interrupt_response: InterruptResponse,
        response: Message,
        confidence: float,
    ) -> AsyncIterator[AGUIEvent]:
        """Handle REJECT action."""
        rejection_reason = "Action rejected by user"
        if interrupt_response.context:
            rejection_reason = interrupt_response.context.get("reason", rejection_reason)

        rejection_msg = Message(
            role="agent",
            content=rejection_reason,
            metadata={
                "approval_status": "rejected",
                "confidence": confidence,
                "original_response": str(response.content),
            },
        )
        msg_id = self._generate_message_id()
        async for event in self._stream_text_message(rejection_msg, msg_id):
            yield event

    async def _handle_edit_action(
        self,
        interrupt_response: InterruptResponse,
        response: Message,
        confidence: float,
    ) -> AsyncIterator[AGUIEvent]:
        """Handle EDIT action."""
        if interrupt_response.context:
            modified_content = interrupt_response.context.get("modified_content")
            if modified_content:
                # Create new metadata dict
                metadata = {**(response.metadata or {})}
                metadata["approval_status"] = "approved_with_modifications"
                metadata["original_response"] = str(response.content)
                metadata["confidence"] = confidence

                # Create new message with modified content
                edited_response = Message(
                    role=response.role,
                    content=modified_content,
                    metadata=metadata,
                )

                msg_id = self._generate_message_id()
                async for event in self._stream_text_message(edited_response, msg_id):
                    yield event
                return

        # No modified content provided - reject
        rejection_msg = Message(
            role="agent",
            content="Edit action requires modified_content in data",
            metadata={"approval_status": "rejected", "confidence": confidence},
        )
        msg_id = self._generate_message_id()
        async for event in self._stream_text_message(rejection_msg, msg_id):
            yield event

    async def _stream_legacy(self, message: Message) -> AsyncIterator[AGUIEvent]:
        """
        Legacy mode: informational interrupts after approval (for HumanInLoopAgent).
        """
        # Check if agent is a HumanInLoopAgent
        from agenkit.patterns.human_in_loop import HumanInLoopAgent

        is_hil_agent = isinstance(self._agent, HumanInLoopAgent)

        # For regular agents or if interrupts disabled, use standard streaming
        if not is_hil_agent or not self._emit_interrupts:
            async for event in super().stream_events(message, emit_metadata=False):
                yield event
            return

        # Process message (HumanInLoopAgent handles approval synchronously)
        response = await self._agent.process(message)

        # Check if approval was involved
        approval_status = response.metadata.get("approval_status") if response.metadata else None

        # Emit Interrupt event if approval was part of the flow
        if approval_status in ("approved", "rejected", "approved_with_modifications"):
            interrupt_id = str(uuid4())
            confidence = response.metadata.get("confidence", 0.0)

            # Emit informational Interrupt event
            interrupt = Interrupt(
                interrupt_id=interrupt_id,
                reason=InterruptReason.APPROVAL_REQUIRED,
                message=f"Approval {approval_status} (confidence: {confidence:.2f})",
                context={
                    "approval_status": approval_status,
                    "confidence": confidence,
                    "approval_threshold": response.metadata.get("approval_threshold"),
                    "approval_needed": True,
                },
                actions=[],  # No actions - already decided
                timeout_seconds=None,
            )
            yield interrupt

        # Stream the response
        msg_id = self._generate_message_id()
        async for event in self._stream_text_message(response, msg_id):
            yield event

    async def _stream_text_message(
        self, response: Message, msg_id: str
    ) -> AsyncIterator[AGUIEvent]:
        """Stream a message as TextMessage events (Start, Chunk, Complete)."""
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
                **(response.metadata or {}),
            },
        )

    async def handle_interrupt_response(self, interrupt_response: InterruptResponse) -> None:
        """
        Handle InterruptResponse from frontend.

        This is called when the frontend responds to an Interrupt event.
        In bidirectional mode, signals the waiting coroutine to resume.
        In legacy mode, updates the pending interrupt context.

        Args:
            interrupt_response: Response from frontend with approval decision

        Raises:
            ValueError: If interrupt_id not found in pending interrupts
        """
        interrupt_id = interrupt_response.interrupt_id

        if self._bidirectional:
            # Bidirectional mode: signal waiting coroutine
            if interrupt_id not in self._pending_interrupts:
                raise ValueError(f"Unknown interrupt_id: {interrupt_id}")

            # Store response for stream_events to process
            self._interrupt_responses[interrupt_id] = interrupt_response

            # Signal the waiting coroutine
            event = self._pending_interrupts[interrupt_id]
            event.set()

        else:
            # Legacy mode: update context (not used in current implementation)
            if interrupt_id not in self._interrupt_contexts:
                raise ValueError(f"Unknown interrupt_id: {interrupt_id}")

            # Context updates would go here if needed
            del self._interrupt_contexts[interrupt_id]

    def _extract_confidence(self, message: Message) -> float:
        """Extract confidence value from message metadata."""
        if not message.metadata:
            return 0.0

        confidence = message.metadata.get(self._confidence_key)
        if confidence is None:
            return 0.0

        try:
            return float(confidence)
        except (ValueError, TypeError):
            return 0.0

    def _cleanup_interrupt(self, interrupt_id: str) -> None:
        """Clean up interrupt state after resolution or timeout."""
        self._pending_interrupts.pop(interrupt_id, None)
        self._interrupt_responses.pop(interrupt_id, None)
        self._interrupt_contexts.pop(interrupt_id, None)

    def _create_metadata_event(self) -> MetadataEvent:
        """Create metadata event with HITL capabilities."""
        # Get base metadata from parent
        base_metadata = super()._create_metadata_event()

        # Add HITL capabilities
        if "capabilities" not in base_metadata.data:
            base_metadata.data["capabilities"] = []

        # Add capabilities based on mode
        if self._bidirectional:
            base_metadata.data["capabilities"].extend(
                [
                    "human-in-loop",
                    "approval",
                    "interrupts",
                    "bidirectional-hitl",
                ]
            )
            base_metadata.data["supports_hitl"] = True
            base_metadata.data["hitl_mode"] = "bidirectional"
            base_metadata.data["approval_threshold"] = self._approval_threshold
            base_metadata.data["approval_timeout"] = self._timeout
        else:
            # Legacy mode
            from agenkit.patterns.human_in_loop import HumanInLoopAgent

            if isinstance(self._agent, HumanInLoopAgent):
                base_metadata.data["capabilities"].extend(
                    [
                        "human-in-loop",
                        "approval",
                        "interrupts",
                    ]
                )
                base_metadata.data["supports_hitl"] = True
                base_metadata.data["hitl_mode"] = "legacy"

        return base_metadata


__all__ = [
    "AGUIHumanInLoopAdapter",
]
