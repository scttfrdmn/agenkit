#!/usr/bin/env python3
"""
Bidirectional Human-in-the-Loop (HITL) Example

Demonstrates the new bidirectional HITL feature where agents pause execution
to wait for user approval before proceeding with sensitive actions.

Key features:
- Agent pauses when confidence is low
- Interrupt event emitted with available actions (APPROVE, REJECT, EDIT)
- Frontend receives interrupt and displays approval UI
- User makes decision
- Agent resumes based on user's decision

This example simulates a financial trading agent that requires approval
for trades with low confidence.
"""

import asyncio
from dataclasses import dataclass

from agenkit import Agent, Message
from agenkit.protocols.agui.events import InterruptAction, InterruptResponse
from agenkit.protocols.agui.hitl import AGUIHumanInLoopAdapter


@dataclass
class Trade:
    """Represents a proposed trade."""

    symbol: str
    action: str  # "buy" or "sell"
    quantity: int
    price: float
    confidence: float


class TradingAgent(Agent):
    """
    Mock trading agent that proposes trades with varying confidence levels.
    """

    @property
    def name(self) -> str:
        return "TradingAgent"

    @property
    def capabilities(self) -> list[str]:
        return ["trading", "analysis"]

    async def process(self, message: Message) -> Message:
        """Process trading request and return proposal with confidence."""
        # Parse request (simplified)
        content = str(message.content).lower()

        if "conservative" in content:
            # High confidence trade
            trade = Trade(
                symbol="AAPL",
                action="buy",
                quantity=10,
                price=175.50,
                confidence=0.92,
            )
            return Message(
                role="assistant",
                content=f"Proposing conservative trade: {trade.action.upper()} "
                f"{trade.quantity} shares of {trade.symbol} at ${trade.price}",
                metadata={"confidence": trade.confidence, "trade": trade.__dict__},
            )
        elif "aggressive" in content:
            # Low confidence trade - will trigger approval
            trade = Trade(
                symbol="TSLA",
                action="buy",
                quantity=100,
                price=850.00,
                confidence=0.45,
            )
            return Message(
                role="assistant",
                content=f"Proposing aggressive trade: {trade.action.upper()} "
                f"{trade.quantity} shares of {trade.symbol} at ${trade.price}",
                metadata={"confidence": trade.confidence, "trade": trade.__dict__},
            )
        else:
            # Medium confidence trade
            trade = Trade(
                symbol="MSFT",
                action="sell",
                quantity=50,
                price=420.00,
                confidence=0.75,
            )
            return Message(
                role="assistant",
                content=f"Proposing moderate trade: {trade.action.upper()} "
                f"{trade.quantity} shares of {trade.symbol} at ${trade.price}",
                metadata={"confidence": trade.confidence, "trade": trade.__dict__},
            )


async def simulate_user_approval(interrupt_id: str, action: InterruptAction) -> InterruptResponse:
    """
    Simulate user making an approval decision.

    In a real application, this would be the frontend sending back the user's decision.
    """
    # Simulate user thinking time
    await asyncio.sleep(0.1)

    if action == InterruptAction.APPROVE:
        return InterruptResponse(
            interrupt_id=interrupt_id,
            action=action,
            context={"feedback": "Trade approved by risk manager"},
        )
    elif action == InterruptAction.REJECT:
        return InterruptResponse(
            interrupt_id=interrupt_id,
            action=action,
            context={"reason": "Trade exceeds risk tolerance"},
        )
    elif action == InterruptAction.EDIT:
        return InterruptResponse(
            interrupt_id=interrupt_id,
            action=action,
            context={
                "modified_content": "Proposing modified trade: BUY 50 shares of TSLA at $850.00 "
                "(reduced quantity for lower risk)"
            },
        )
    else:
        raise ValueError(f"Unknown action: {action}")


async def run_trading_scenario(
    scenario_name: str,
    message: str,
    approval_action: InterruptAction | None = None,
):
    """
    Run a trading scenario with bidirectional HITL.

    Args:
        scenario_name: Name of the scenario for display
        message: Trading request message
        approval_action: How to handle approval (if needed)
    """
    print(f"\n{'=' * 70}")
    print(f"Scenario: {scenario_name}")
    print(f"{'=' * 70}")

    # Create trading agent with bidirectional HITL adapter
    agent = TradingAgent()
    adapter = AGUIHumanInLoopAdapter(
        agent,
        bidirectional=True,
        approval_threshold=0.8,  # Trades < 80% confidence require approval
        timeout=300.0,  # 5 minute timeout
    )

    # Create user message
    user_message = Message(role="user", content=message)

    print(f"\n📨 User Request: {message}")
    print(f"\n🤖 Agent Processing...")

    # Stream events and collect them
    events = []
    interrupt_received = None

    async def collect_events():
        nonlocal interrupt_received
        async for event in adapter.stream_events(user_message):
            events.append(event)
            event_type = event.__class__.__name__

            if event_type == "MetadataEvent":
                print(f"   ℹ️  Metadata: Agent capabilities = {event.data.get('capabilities', [])}")
                if event.data.get("supports_hitl"):
                    print(
                        f"   ✅ HITL Enabled: mode={event.data.get('hitl_mode')}, "
                        f"threshold={event.data.get('approval_threshold')}"
                    )

            elif event_type == "Interrupt":
                interrupt_received = event
                print(f"\n⚠️  APPROVAL REQUIRED")
                print(f"   Interrupt ID: {event.interrupt_id}")
                print(f"   Reason: {event.message}")
                print(f"   Confidence: {event.context.get('confidence')}")
                print(f"   Available Actions: {[str(a) for a in event.actions]}")
                print(f"   Timeout: {event.timeout_seconds}s")

            elif event_type == "TextMessageStart":
                print(f"\n💬 Agent Response (streaming):")

            elif event_type == "TextMessageChunk":
                print(f"   {event.content}", end="", flush=True)

            elif event_type == "TextMessageComplete":
                print()  # Newline after streaming
                approval_status = event.metadata.get("approval_status")
                if approval_status:
                    print(f"\n✅ Status: {approval_status}")
                    if approval_status == "approved_with_modifications":
                        print(
                            f"   Original: {event.metadata.get('original_response', 'N/A')[:50]}..."
                        )

    # Start collecting events
    event_task = asyncio.create_task(collect_events())

    # Wait for interrupt or completion
    await asyncio.sleep(0.2)

    # Handle interrupt if received
    if interrupt_received and approval_action:
        print(f"\n👤 User Decision: {approval_action}")
        response = await simulate_user_approval(interrupt_received.interrupt_id, approval_action)
        await adapter.handle_interrupt_response(response)

    # Wait for completion
    await event_task

    print()


async def main():
    """Run bidirectional HITL demonstrations."""
    print("=" * 70)
    print("AG-UI Bidirectional Human-in-the-Loop (HITL) Demo")
    print("=" * 70)
    print(
        "\nThis example demonstrates how agents can pause execution to request\n"
        "user approval before proceeding with low-confidence actions.\n"
    )

    # Scenario 1: High confidence - no approval needed
    await run_trading_scenario(
        "High Confidence Trade (No Approval Required)",
        "Execute a conservative trade",
        approval_action=None,  # No approval needed
    )

    # Scenario 2: Low confidence - approval granted
    await run_trading_scenario(
        "Low Confidence Trade (Approved)",
        "Execute an aggressive trade",
        approval_action=InterruptAction.APPROVE,
    )

    # Scenario 3: Low confidence - approval rejected
    await run_trading_scenario(
        "Low Confidence Trade (Rejected)",
        "Execute an aggressive trade",
        approval_action=InterruptAction.REJECT,
    )

    # Scenario 4: Low confidence - modified by user
    await run_trading_scenario(
        "Low Confidence Trade (Modified)",
        "Execute an aggressive trade",
        approval_action=InterruptAction.EDIT,
    )

    print("\n" + "=" * 70)
    print("Demo Complete")
    print("=" * 70)
    print(
        "\nKey Takeaways:\n"
        "1. High confidence actions proceed automatically\n"
        "2. Low confidence actions pause and wait for approval\n"
        "3. Users can APPROVE, REJECT, or EDIT proposed actions\n"
        "4. Agent resumes execution based on user's decision\n"
        "5. Timeouts prevent indefinite blocking\n"
    )


if __name__ == "__main__":
    asyncio.run(main())
