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
