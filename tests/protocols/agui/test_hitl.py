#!/usr/bin/env python3
"""Tests for AG-UI Human-in-the-Loop integration."""

import pytest

from agenkit import Message
from agenkit.patterns.human_in_loop import (
    ApprovalRequest,
    ApprovalResponse,
    HumanInLoopAgent,
    HumanInLoopConfig,
)
from agenkit.protocols.agui.events import (
    Interrupt,
    InterruptReason,
    MetadataEvent,
)
from agenkit.protocols.agui.hitl import AGUIHumanInLoopAdapter


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, name="mock", response="Success", confidence=0.9):
        self._name = name
        self.response = response
        self.confidence = confidence

    @property
    def name(self):
        return self._name

    @property
    def capabilities(self):
        return ["chat"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content=self.response,
            metadata={"confidence": self.confidence},
        )


class TestAGUIHumanInLoopAdapter:
    """Test AG-UI Human-in-Loop adapter."""

    @pytest.mark.asyncio
    async def test_regular_agent_no_interrupts(self):
        """Test that regular agents stream normally without interrupts."""
        agent = MockAgent(response="Hello", confidence=0.95)
        adapter = AGUIHumanInLoopAdapter(agent)

        message = Message(role="user", content="Hi")
        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # Should have standard events, no interrupts
        event_types = [e.__class__.__name__ for e in events]
        assert "MetadataEvent" in event_types
        assert "TextMessageStart" in event_types
        assert "TextMessageComplete" in event_types
        assert "Interrupt" not in event_types

    @pytest.mark.asyncio
    async def test_high_confidence_no_interrupt(self):
        """Test that high confidence responses don't emit interrupts."""

        async def auto_approve(request: ApprovalRequest) -> ApprovalResponse:
            return ApprovalResponse(approved=True)

        agent = MockAgent(confidence=0.95)
        hil_agent = HumanInLoopAgent(
            HumanInLoopConfig(agent=agent, approval_func=auto_approve, approval_threshold=0.8)
        )

        adapter = AGUIHumanInLoopAdapter(hil_agent)

        message = Message(role="user", content="Test")
        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # High confidence should bypass approval, no interrupt
        event_types = [e.__class__.__name__ for e in events]
        assert "Interrupt" not in event_types

    @pytest.mark.asyncio
    async def test_low_confidence_emits_interrupt(self):
        """Test that low confidence responses emit Interrupt events."""

        async def auto_approve(request: ApprovalRequest) -> ApprovalResponse:
            return ApprovalResponse(approved=True)

        agent = MockAgent(confidence=0.5)
        hil_agent = HumanInLoopAgent(
            HumanInLoopConfig(agent=agent, approval_func=auto_approve, approval_threshold=0.8)
        )

        adapter = AGUIHumanInLoopAdapter(hil_agent)

        message = Message(role="user", content="Test")
        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # Should emit Interrupt for approval notification
        interrupts = [e for e in events if isinstance(e, Interrupt)]
        assert len(interrupts) == 1

        interrupt = interrupts[0]
        assert interrupt.reason == InterruptReason.APPROVAL_REQUIRED
        assert "confidence" in interrupt.message.lower()
        assert interrupt.context["confidence"] == 0.5
        assert interrupt.context["approval_needed"] is True
        assert interrupt.context["approval_status"] == "approved"

    @pytest.mark.asyncio
    async def test_interrupt_context_includes_approval_info(self):
        """Test that interrupt context includes approval information."""

        async def auto_approve(request: ApprovalRequest) -> ApprovalResponse:
            return ApprovalResponse(approved=True)

        agent = MockAgent(response="Test response", confidence=0.6)
        hil_agent = HumanInLoopAgent(
            HumanInLoopConfig(agent=agent, approval_func=auto_approve, approval_threshold=0.8)
        )

        adapter = AGUIHumanInLoopAdapter(hil_agent)

        message = Message(role="user", content="Test")
        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        interrupts = [e for e in events if isinstance(e, Interrupt)]
        assert len(interrupts) == 1

        interrupt = interrupts[0]
        assert interrupt.context["confidence"] == 0.6
        assert interrupt.context["approval_status"] == "approved"
        assert "approval_threshold" in interrupt.context
        assert interrupt.context["approval_needed"] is True

    @pytest.mark.asyncio
    async def test_rejected_approval_emits_interrupt(self):
        """Test that rejected approvals emit Interrupt events."""

        async def auto_reject(request: ApprovalRequest) -> ApprovalResponse:
            return ApprovalResponse(approved=False, feedback="Too risky")

        agent = MockAgent(confidence=0.5)
        hil_agent = HumanInLoopAgent(
            HumanInLoopConfig(agent=agent, approval_func=auto_reject, approval_threshold=0.8)
        )

        adapter = AGUIHumanInLoopAdapter(hil_agent)

        message = Message(role="user", content="Test")
        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        interrupts = [e for e in events if isinstance(e, Interrupt)]
        assert len(interrupts) == 1

        interrupt = interrupts[0]
        assert interrupt.context["approval_status"] == "rejected"
        assert interrupt.context["approval_needed"] is True

    @pytest.mark.asyncio
    async def test_metadata_event_includes_hitl_capabilities(self):
        """Test that metadata event includes HITL capabilities."""

        async def auto_approve(request: ApprovalRequest) -> ApprovalResponse:
            return ApprovalResponse(approved=True)

        agent = MockAgent()
        hil_agent = HumanInLoopAgent(HumanInLoopConfig(agent=agent, approval_func=auto_approve))

        adapter = AGUIHumanInLoopAdapter(hil_agent, agent_name="TestAgent")

        message = Message(role="user", content="Test")
        events = []
        async for event in adapter.stream_events(message, emit_metadata=True):
            events.append(event)
            if isinstance(event, MetadataEvent):
                break

        metadata_events = [e for e in events if isinstance(e, MetadataEvent)]
        assert len(metadata_events) == 1

        metadata = metadata_events[0]
        assert metadata.data.get("agent_name") == "TestAgent"
        assert "human-in-loop" in metadata.data.get("capabilities", [])
        assert "approval" in metadata.data.get("capabilities", [])
        assert "interrupts" in metadata.data.get("capabilities", [])
        assert metadata.data.get("supports_hitl") is True

    @pytest.mark.asyncio
    async def test_emit_interrupts_disabled(self):
        """Test that interrupts can be disabled."""

        async def auto_approve(request: ApprovalRequest) -> ApprovalResponse:
            return ApprovalResponse(approved=True)

        agent = MockAgent(confidence=0.5)
        hil_agent = HumanInLoopAgent(
            HumanInLoopConfig(agent=agent, approval_func=auto_approve, approval_threshold=0.8)
        )

        adapter = AGUIHumanInLoopAdapter(hil_agent, emit_interrupts=False)

        message = Message(role="user", content="Test")
        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # Should not emit interrupts when disabled
        event_types = [e.__class__.__name__ for e in events]
        assert "Interrupt" not in event_types

    @pytest.mark.asyncio
    async def test_multiple_pending_interrupts(self):
        """Test handling multiple pending interrupts."""

        async def auto_approve(request: ApprovalRequest) -> ApprovalResponse:
            return ApprovalResponse(approved=True)

        agent1 = MockAgent(confidence=0.5)
        agent2 = MockAgent(confidence=0.4)

        hil_agent1 = HumanInLoopAgent(
            HumanInLoopConfig(agent=agent1, approval_func=auto_approve, approval_threshold=0.8)
        )
        hil_agent2 = HumanInLoopAgent(
            HumanInLoopConfig(agent=agent2, approval_func=auto_approve, approval_threshold=0.8)
        )

        adapter1 = AGUIHumanInLoopAdapter(hil_agent1)
        adapter2 = AGUIHumanInLoopAdapter(hil_agent2)

        message = Message(role="user", content="Test")

        # Generate interrupts from both adapters
        events1 = []
        async for event in adapter1.stream_events(message):
            events1.append(event)

        events2 = []
        async for event in adapter2.stream_events(message):
            events2.append(event)

        interrupts1 = [e for e in events1 if isinstance(e, Interrupt)]
        interrupts2 = [e for e in events2 if isinstance(e, Interrupt)]

        assert len(interrupts1) == 1
        assert len(interrupts2) == 1
        assert interrupts1[0].interrupt_id != interrupts2[0].interrupt_id


class TestBidirectionalHITL:
    """Test bidirectional HITL functionality."""

    @pytest.mark.asyncio
    async def test_bidirectional_high_confidence_no_interrupt(self):
        """Test that high confidence bypasses approval in bidirectional mode."""
        agent = MockAgent(response="Success", confidence=0.95)
        adapter = AGUIHumanInLoopAdapter(
            agent,
            bidirectional=True,
            approval_threshold=0.8,
        )

        message = Message(role="user", content="Test")
        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # High confidence should skip approval
        event_types = [e.__class__.__name__ for e in events]
        assert "Interrupt" not in event_types
        assert "TextMessageComplete" in event_types

    @pytest.mark.asyncio
    async def test_bidirectional_low_confidence_emits_interrupt(self):
        """Test that low confidence emits Interrupt with available actions."""
        from agenkit.protocols.agui.events import InterruptAction, InterruptResponse

        agent = MockAgent(response="Uncertain response", confidence=0.5)
        adapter = AGUIHumanInLoopAdapter(
            agent,
            bidirectional=True,
            approval_threshold=0.8,
        )

        message = Message(role="user", content="Test")

        # Collect events asynchronously
        import asyncio

        events = []
        event_task = None

        async def collect_events():
            async for event in adapter.stream_events(message):
                events.append(event)

        # Start streaming
        event_task = asyncio.create_task(collect_events())

        # Wait for Interrupt event
        await asyncio.sleep(0.1)

        # Should have interrupt with actions
        interrupts = [e for e in events if isinstance(e, Interrupt)]
        assert len(interrupts) == 1

        interrupt = interrupts[0]
        assert interrupt.reason == InterruptReason.APPROVAL_REQUIRED
        assert InterruptAction.APPROVE in interrupt.actions
        assert InterruptAction.REJECT in interrupt.actions
        assert InterruptAction.EDIT in interrupt.actions
        assert interrupt.timeout_seconds == 300.0
        assert interrupt.context["confidence"] == 0.5

        # Respond with approval
        response = InterruptResponse(
            interrupt_id=interrupt.interrupt_id,
            action=InterruptAction.APPROVE,
        )
        await adapter.handle_interrupt_response(response)

        # Wait for streaming to complete
        await event_task

        # Should complete successfully
        text_events = [e for e in events if e.__class__.__name__ == "TextMessageComplete"]
        assert len(text_events) == 1
        assert text_events[0].metadata["approval_status"] == "approved"

    @pytest.mark.asyncio
    async def test_bidirectional_approve_action(self):
        """Test APPROVE action in bidirectional mode."""
        from agenkit.protocols.agui.events import InterruptAction, InterruptResponse

        agent = MockAgent(response="Proceed", confidence=0.6)
        adapter = AGUIHumanInLoopAdapter(
            agent,
            bidirectional=True,
            approval_threshold=0.8,
        )

        message = Message(role="user", content="Test")

        import asyncio

        events = []

        async def collect_events():
            async for event in adapter.stream_events(message):
                events.append(event)

        event_task = asyncio.create_task(collect_events())
        await asyncio.sleep(0.1)

        interrupts = [e for e in events if isinstance(e, Interrupt)]
        assert len(interrupts) == 1

        # Approve with feedback
        response = InterruptResponse(
            interrupt_id=interrupts[0].interrupt_id,
            action=InterruptAction.APPROVE,
            context={"feedback": "Looks good"},
        )
        await adapter.handle_interrupt_response(response)
        await event_task

        # Check approved response
        complete_events = [e for e in events if e.__class__.__name__ == "TextMessageComplete"]
        assert len(complete_events) == 1
        assert complete_events[0].metadata["approval_status"] == "approved"
        assert complete_events[0].metadata["approval_feedback"] == "Looks good"
        assert complete_events[0].content == "Proceed"

    @pytest.mark.asyncio
    async def test_bidirectional_reject_action(self):
        """Test REJECT action in bidirectional mode."""
        from agenkit.protocols.agui.events import InterruptAction, InterruptResponse

        agent = MockAgent(response="Risky action", confidence=0.4)
        adapter = AGUIHumanInLoopAdapter(
            agent,
            bidirectional=True,
            approval_threshold=0.8,
        )

        message = Message(role="user", content="Test")

        import asyncio

        events = []

        async def collect_events():
            async for event in adapter.stream_events(message):
                events.append(event)

        event_task = asyncio.create_task(collect_events())
        await asyncio.sleep(0.1)

        interrupts = [e for e in events if isinstance(e, Interrupt)]
        assert len(interrupts) == 1

        # Reject with reason
        response = InterruptResponse(
            interrupt_id=interrupts[0].interrupt_id,
            action=InterruptAction.REJECT,
            context={"reason": "Too risky to proceed"},
        )
        await adapter.handle_interrupt_response(response)
        await event_task

        # Check rejection response
        complete_events = [e for e in events if e.__class__.__name__ == "TextMessageComplete"]
        assert len(complete_events) == 1
        assert complete_events[0].metadata["approval_status"] == "rejected"
        assert complete_events[0].content == "Too risky to proceed"

    @pytest.mark.asyncio
    async def test_bidirectional_edit_action(self):
        """Test EDIT action in bidirectional mode."""
        from agenkit.protocols.agui.events import InterruptAction, InterruptResponse

        agent = MockAgent(response="Original response", confidence=0.5)
        adapter = AGUIHumanInLoopAdapter(
            agent,
            bidirectional=True,
            approval_threshold=0.8,
        )

        message = Message(role="user", content="Test")

        import asyncio

        events = []

        async def collect_events():
            async for event in adapter.stream_events(message):
                events.append(event)

        event_task = asyncio.create_task(collect_events())
        await asyncio.sleep(0.1)

        interrupts = [e for e in events if isinstance(e, Interrupt)]
        assert len(interrupts) == 1

        # Edit with modified content
        response = InterruptResponse(
            interrupt_id=interrupts[0].interrupt_id,
            action=InterruptAction.EDIT,
            context={"modified_content": "Modified response"},
        )
        await adapter.handle_interrupt_response(response)
        await event_task

        # Check edited response
        complete_events = [e for e in events if e.__class__.__name__ == "TextMessageComplete"]
        assert len(complete_events) == 1
        assert complete_events[0].metadata["approval_status"] == "approved_with_modifications"
        assert complete_events[0].metadata["original_response"] == "Original response"
        assert complete_events[0].content == "Modified response"

    @pytest.mark.asyncio
    async def test_bidirectional_timeout(self):
        """Test timeout handling in bidirectional mode."""
        agent = MockAgent(response="Waiting", confidence=0.3)
        adapter = AGUIHumanInLoopAdapter(
            agent,
            bidirectional=True,
            approval_threshold=0.8,
            timeout=0.2,  # Short timeout for testing
        )

        message = Message(role="user", content="Test")

        # Don't respond - let it timeout
        events = []
        async for event in adapter.stream_events(message):
            events.append(event)

        # Should have interrupt and timeout rejection
        interrupts = [e for e in events if isinstance(e, Interrupt)]
        assert len(interrupts) == 1
        assert interrupts[0].timeout_seconds == 0.2

        # Should have timeout rejection message
        complete_events = [e for e in events if e.__class__.__name__ == "TextMessageComplete"]
        assert len(complete_events) == 1
        assert complete_events[0].metadata["approval_status"] == "timeout"
        assert "timed out" in complete_events[0].content.lower()

    @pytest.mark.asyncio
    async def test_bidirectional_unknown_action(self):
        """Test handling of unknown interrupt action."""
        from agenkit.protocols.agui.events import InterruptResponse

        agent = MockAgent(response="Test", confidence=0.5)
        adapter = AGUIHumanInLoopAdapter(
            agent,
            bidirectional=True,
            approval_threshold=0.8,
        )

        message = Message(role="user", content="Test")

        import asyncio

        events = []

        async def collect_events():
            async for event in adapter.stream_events(message):
                events.append(event)

        event_task = asyncio.create_task(collect_events())
        await asyncio.sleep(0.1)

        interrupts = [e for e in events if isinstance(e, Interrupt)]
        assert len(interrupts) == 1

        # Respond with unknown action
        response = InterruptResponse(
            interrupt_id=interrupts[0].interrupt_id,
            action="UNKNOWN_ACTION",  # Invalid action
        )
        await adapter.handle_interrupt_response(response)
        await event_task

        # Should reject with error message
        complete_events = [e for e in events if e.__class__.__name__ == "TextMessageComplete"]
        assert len(complete_events) == 1
        assert complete_events[0].metadata["approval_status"] == "rejected"
        assert "unknown" in complete_events[0].content.lower()

    @pytest.mark.asyncio
    async def test_bidirectional_metadata_capabilities(self):
        """Test that bidirectional mode adds correct metadata."""
        agent = MockAgent()
        adapter = AGUIHumanInLoopAdapter(
            agent,
            bidirectional=True,
            approval_threshold=0.75,
            timeout=600.0,
        )

        message = Message(role="user", content="Test")
        events = []
        async for event in adapter.stream_events(message, emit_metadata=True):
            events.append(event)
            if isinstance(event, MetadataEvent):
                break

        metadata_events = [e for e in events if isinstance(e, MetadataEvent)]
        assert len(metadata_events) == 1

        metadata = metadata_events[0]
        assert "bidirectional-hitl" in metadata.data.get("capabilities", [])
        assert metadata.data.get("supports_hitl") is True
        assert metadata.data.get("hitl_mode") == "bidirectional"
        assert metadata.data.get("approval_threshold") == 0.75
        assert metadata.data.get("approval_timeout") == 600.0

    @pytest.mark.asyncio
    async def test_bidirectional_edit_without_content(self):
        """Test that EDIT action without modified_content is rejected."""
        from agenkit.protocols.agui.events import InterruptAction, InterruptResponse

        agent = MockAgent(response="Original", confidence=0.5)
        adapter = AGUIHumanInLoopAdapter(
            agent,
            bidirectional=True,
            approval_threshold=0.8,
        )

        message = Message(role="user", content="Test")

        import asyncio

        events = []

        async def collect_events():
            async for event in adapter.stream_events(message):
                events.append(event)

        event_task = asyncio.create_task(collect_events())
        await asyncio.sleep(0.1)

        interrupts = [e for e in events if isinstance(e, Interrupt)]
        assert len(interrupts) == 1

        # Edit without modified content
        response = InterruptResponse(
            interrupt_id=interrupts[0].interrupt_id,
            action=InterruptAction.EDIT,
            context={},  # No modified_content
        )
        await adapter.handle_interrupt_response(response)
        await event_task

        # Should reject
        complete_events = [e for e in events if e.__class__.__name__ == "TextMessageComplete"]
        assert len(complete_events) == 1
        assert complete_events[0].metadata["approval_status"] == "rejected"
        assert "modified_content" in complete_events[0].content.lower()

    @pytest.mark.asyncio
    async def test_bidirectional_invalid_interrupt_id(self):
        """Test error handling for invalid interrupt ID."""
        from agenkit.protocols.agui.events import InterruptAction, InterruptResponse

        agent = MockAgent()
        adapter = AGUIHumanInLoopAdapter(
            agent,
            bidirectional=True,
        )

        # Try to respond to non-existent interrupt
        response = InterruptResponse(
            interrupt_id="invalid-id",
            action=InterruptAction.APPROVE,
        )

        with pytest.raises(ValueError, match="Unknown interrupt_id"):
            await adapter.handle_interrupt_response(response)
