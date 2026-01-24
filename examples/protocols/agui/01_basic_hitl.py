#!/usr/bin/env python3
"""
Basic AG-UI Human-in-the-Loop Example.

Demonstrates the AG-UI HITL adapter with Interrupt events for approval notifications.
Shows how HumanInLoopAgent integrates with AG-UI protocol to emit Interrupt events
when approval is required.

Key concepts:
- AGUIHumanInLoopAdapter wraps HumanInLoopAgent
- Interrupt events emitted for approval decisions
- Metadata includes HITL capabilities
- Confidence-based approval thresholds

This example shows:
- Basic HITL integration with AG-UI
- Interrupt event structure
- High vs low confidence handling
- Approval status in event context
"""

import asyncio

from agenkit import Agent, Message
from agenkit.patterns.human_in_loop import (
    ApprovalRequest,
    ApprovalResponse,
    HumanInLoopAgent,
    HumanInLoopConfig,
)
from agenkit.protocols.agui.events import Interrupt, InterruptReason, MetadataEvent
from agenkit.protocols.agui.hitl import AGUIHumanInLoopAdapter


class SimpleAgent(Agent):
    """Simple agent that returns responses with varying confidence."""

    def __init__(self, name: str = "SimpleAgent", confidence: float = 0.9):
        self._name = name
        self._confidence = confidence

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["chat", "analysis"]

    async def process(self, message: Message) -> Message:
        """Process message and return response with confidence."""
        print(f"   🤖 {self._name} processing: {message.content}")
        await asyncio.sleep(0.1)

        return Message(
            role="assistant",
            content=f"Processed: {message.content}",
            metadata={"confidence": self._confidence},
        )


async def simple_approval_func(request: ApprovalRequest) -> ApprovalResponse:
    """Simple approval function that logs and auto-approves."""
    confidence = request.confidence
    print(f"   👤 Approval requested - Confidence: {confidence:.2f}")
    print(f"      Message: {request.message.content}")
    print(f"      Context: {request.context}")

    # For demo, auto-approve after short delay
    await asyncio.sleep(0.1)
    print("   ✅ Approved")

    return ApprovalResponse(
        approved=True,
        feedback=f"Approved with confidence {confidence:.2f}",
    )


async def example_high_confidence() -> None:
    """Example 1: High confidence - no approval needed."""
    print("=" * 70)
    print("Example 1: High Confidence (No Approval)")
    print("=" * 70)

    # Create agent with high confidence
    agent = SimpleAgent(name="HighConfidenceAgent", confidence=0.95)

    # Wrap with HumanInLoopAgent (threshold 0.8)
    hil_agent = HumanInLoopAgent(
        HumanInLoopConfig(
            agent=agent,
            approval_func=simple_approval_func,
            approval_threshold=0.8,
        )
    )

    # Wrap with AG-UI adapter
    adapter = AGUIHumanInLoopAdapter(hil_agent, agent_name="HighConfidenceDemo")

    # Stream events
    message = Message(role="user", content="What is 2+2?")
    print(f"\n📥 User: {message.content}\n")

    events = []
    async for event in adapter.stream_events(message):
        events.append(event)
        print(f"📡 Event: {event.__class__.__name__}")

        if isinstance(event, MetadataEvent):
            print(f"   Agent: {event.data.get('agent_name')}")
            print(f"   Capabilities: {event.data.get('capabilities')}")
            print(f"   Supports HITL: {event.data.get('supports_hitl')}")

        elif isinstance(event, Interrupt):
            print(f"   ⚠️  Interrupt! Reason: {event.reason}")
            print(f"   Message: {event.message}")
            print(f"   Context: {event.context}")

    # Analysis
    interrupt_count = sum(1 for e in events if isinstance(e, Interrupt))
    print("\n📊 Analysis:")
    print(f"   Total events: {len(events)}")
    print(f"   Interrupts: {interrupt_count}")
    print("   ✓ High confidence bypassed approval (no interrupt)")


async def example_low_confidence() -> None:
    """Example 2: Low confidence - approval required."""
    print("\n\n" + "=" * 70)
    print("Example 2: Low Confidence (Approval Required)")
    print("=" * 70)

    # Create agent with low confidence
    agent = SimpleAgent(name="LowConfidenceAgent", confidence=0.5)

    # Wrap with HumanInLoopAgent (threshold 0.8)
    hil_agent = HumanInLoopAgent(
        HumanInLoopConfig(
            agent=agent,
            approval_func=simple_approval_func,
            approval_threshold=0.8,
        )
    )

    # Wrap with AG-UI adapter
    adapter = AGUIHumanInLoopAdapter(hil_agent, agent_name="LowConfidenceDemo")

    # Stream events
    message = Message(role="user", content="Make a critical decision")
    print(f"\n📥 User: {message.content}\n")

    events = []
    async for event in adapter.stream_events(message):
        events.append(event)
        print(f"📡 Event: {event.__class__.__name__}")

        if isinstance(event, Interrupt):
            print(f"   ⚠️  Interrupt! Reason: {event.reason}")
            print(f"   Message: {event.message}")
            print(f"   Approval Status: {event.context.get('approval_status')}")
            print(f"   Confidence: {event.context.get('confidence')}")
            print(f"   Threshold: {event.context.get('approval_threshold')}")
            print(f"   Approval Needed: {event.context.get('approval_needed')}")

    # Analysis
    interrupts = [e for e in events if isinstance(e, Interrupt)]
    print("\n📊 Analysis:")
    print(f"   Total events: {len(events)}")
    print(f"   Interrupts: {len(interrupts)}")
    if interrupts:
        interrupt = interrupts[0]
        print("   ✓ Low confidence triggered approval")
        print("   ✓ Interrupt emitted with approval status")
        print(f"   Reason: {interrupt.reason.value}")


async def example_rejection() -> None:
    """Example 3: Approval rejection."""
    print("\n\n" + "=" * 70)
    print("Example 3: Approval Rejection")
    print("=" * 70)

    # Rejection approval function
    async def reject_approval_func(request: ApprovalRequest) -> ApprovalResponse:
        confidence = request.confidence
        print(f"   👤 Approval requested - Confidence: {confidence:.2f}")
        await asyncio.sleep(0.1)
        print("   ❌ Rejected - Too risky")
        return ApprovalResponse(
            approved=False,
            feedback="Confidence too low for this operation",
        )

    # Create agent with low confidence
    agent = SimpleAgent(name="RiskyAgent", confidence=0.4)

    # Wrap with HumanInLoopAgent
    hil_agent = HumanInLoopAgent(
        HumanInLoopConfig(
            agent=agent,
            approval_func=reject_approval_func,
            approval_threshold=0.8,
        )
    )

    # Wrap with AG-UI adapter
    adapter = AGUIHumanInLoopAdapter(hil_agent, agent_name="RejectionDemo")

    # Stream events
    message = Message(role="user", content="Execute risky operation")
    print(f"\n📥 User: {message.content}\n")

    events = []
    async for event in adapter.stream_events(message):
        events.append(event)
        print(f"📡 Event: {event.__class__.__name__}")

        if isinstance(event, Interrupt):
            print(f"   ⚠️  Interrupt! Status: {event.context.get('approval_status')}")
            print(f"   Message: {event.message}")

    # Analysis
    interrupts = [e for e in events if isinstance(e, Interrupt)]
    print("\n📊 Analysis:")
    print(f"   Total events: {len(events)}")
    print(f"   Interrupts: {len(interrupts)}")
    if interrupts:
        status = interrupts[0].context.get("approval_status")
        print(f"   ✓ Approval was {status}")
        print(f"   Reason: {InterruptReason.APPROVAL_REQUIRED.value}")


async def example_disabled_interrupts() -> None:
    """Example 4: Disabling interrupt events."""
    print("\n\n" + "=" * 70)
    print("Example 4: Disabled Interrupts")
    print("=" * 70)

    # Create agent with low confidence
    agent = SimpleAgent(name="QuietAgent", confidence=0.5)

    # Wrap with HumanInLoopAgent
    hil_agent = HumanInLoopAgent(
        HumanInLoopConfig(
            agent=agent,
            approval_func=simple_approval_func,
            approval_threshold=0.8,
        )
    )

    # Wrap with AG-UI adapter - interrupts disabled
    adapter = AGUIHumanInLoopAdapter(
        hil_agent,
        agent_name="DisabledInterruptsDemo",
        emit_interrupts=False,  # Disable interrupts
    )

    # Stream events
    message = Message(role="user", content="Process quietly")
    print(f"\n📥 User: {message.content}\n")

    events = []
    async for event in adapter.stream_events(message):
        events.append(event)
        print(f"📡 Event: {event.__class__.__name__}")

    # Analysis
    interrupt_count = sum(1 for e in events if isinstance(e, Interrupt))
    print("\n📊 Analysis:")
    print(f"   Total events: {len(events)}")
    print(f"   Interrupts: {interrupt_count}")
    print("   ✓ Interrupts disabled - no Interrupt events emitted")
    print("   Note: Approval still happened, just not broadcasted via events")


async def main() -> None:
    """Run all examples."""
    print("\n🎯 AG-UI Human-in-the-Loop Basic Examples\n")

    await example_high_confidence()
    await example_low_confidence()
    await example_rejection()
    await example_disabled_interrupts()

    print("\n\n✅ All examples complete!")
    print("\nKey Takeaways:")
    print("• High confidence (>= threshold) bypasses approval, no interrupt")
    print("• Low confidence (< threshold) triggers approval, emits interrupt")
    print("• Interrupt context includes approval_status, confidence, threshold")
    print("• Interrupts can be disabled with emit_interrupts=False")
    print("• MetadataEvent includes HITL capabilities")


if __name__ == "__main__":
    asyncio.run(main())
