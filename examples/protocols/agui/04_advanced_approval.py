#!/usr/bin/env python3
"""
Advanced AG-UI HITL Approval Patterns.

Demonstrates advanced Human-in-the-Loop patterns with custom approval logic,
multi-stage approval, approval with modifications, and complex decision workflows.

Key concepts:
- Multi-level approval thresholds
- Approval with content modifications
- Contextual approval decisions
- Custom approval UI patterns
- Approval audit trails

This example shows:
- Dynamic approval thresholds
- Approval with modifications
- Multi-stage approval workflow
- Approval context and metadata
- Custom approval UI integration
"""

import asyncio
from datetime import datetime
from typing import Any

from agenkit import Agent, Message
from agenkit.patterns.human_in_loop import (
    ApprovalRequest,
    ApprovalResponse,
    HumanInLoopAgent,
    HumanInLoopConfig,
)
from agenkit.protocols.agui.events import Interrupt
from agenkit.protocols.agui.hitl import AGUIHumanInLoopAdapter

# Approval audit log
approval_log: list[dict[str, Any]] = []


class FinancialAgent(Agent):
    """Agent that processes financial transactions."""

    def __init__(self, name: str = "FinancialAgent"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["finance", "transactions", "risk-assessment"]

    async def process(self, message: Message) -> Message:
        """Process financial transaction."""
        content = message.content.lower()

        # Extract amount
        amount = 1000  # Default
        if "$" in content:
            try:
                amount = int(content.split("$")[1].split()[0].replace(",", ""))
            except (IndexError, ValueError):
                pass

        # Calculate confidence based on amount and type
        if amount < 1000:
            confidence = 0.95
        elif amount < 10000:
            confidence = 0.85
        elif amount < 50000:
            confidence = 0.7
        else:
            confidence = 0.4

        # Determine transaction type
        if "wire" in content or "international" in content:
            confidence *= 0.8  # Lower confidence for wire transfers
            tx_type = "wire_transfer"
        elif "payment" in content:
            tx_type = "payment"
        else:
            tx_type = "transaction"

        return Message(
            role="assistant",
            content=f"Processing {tx_type} for ${amount:,}",
            metadata={
                "confidence": confidence,
                "amount": amount,
                "transaction_type": tx_type,
                "risk_level": "high" if amount > 25000 else "medium" if amount > 5000 else "low",
            },
        )


async def tiered_approval_func(request: ApprovalRequest) -> ApprovalResponse:
    """
    Multi-tiered approval based on amount and risk.

    Approval tiers:
    - < $1,000: Auto-approve
    - $1,000 - $10,000: Manager approval
    - $10,000 - $50,000: Director approval
    - > $50,000: Executive approval + modifications
    """
    amount = request.message.metadata.get("amount", 0)
    confidence = request.confidence
    risk_level = request.message.metadata.get("risk_level", "unknown")

    print(f"\n{'='*60}")
    print("Tiered Approval Request")
    print(f"{'='*60}")
    print(f"Amount:      ${amount:,}")
    print(f"Confidence:  {confidence:.2f}")
    print(f"Risk Level:  {risk_level}")

    # Log approval request
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "amount": amount,
        "confidence": confidence,
        "risk_level": risk_level,
    }

    # Simulate review time
    await asyncio.sleep(0.2)

    if amount < 1000:
        print("✓ Auto-approved (Tier 0: < $1,000)")
        log_entry["decision"] = "auto_approved"
        log_entry["tier"] = 0
        approval_log.append(log_entry)
        return ApprovalResponse(approved=True, feedback="Auto-approved")

    elif amount < 10000:
        print("✓ Manager approved (Tier 1: $1K-$10K)")
        log_entry["decision"] = "manager_approved"
        log_entry["tier"] = 1
        approval_log.append(log_entry)
        return ApprovalResponse(approved=True, feedback="Approved by Manager")

    elif amount < 50000:
        print("✓ Director approved (Tier 2: $10K-$50K)")
        log_entry["decision"] = "director_approved"
        log_entry["tier"] = 2
        approval_log.append(log_entry)
        return ApprovalResponse(approved=True, feedback="Approved by Director")

    else:
        # High-value transactions require modifications
        print("⚠️  Executive review required (Tier 3: > $50K)")
        print("   Adding transaction monitoring...")

        # Modify message to include additional safeguards
        modified_msg = Message(
            role="assistant",
            content=f"{request.message.content} [WITH MONITORING AND AUDIT TRAIL]",
            metadata={
                **request.message.metadata,
                "monitoring_enabled": True,
                "audit_trail_required": True,
                "executive_approved": True,
            },
        )

        log_entry["decision"] = "executive_approved_with_modifications"
        log_entry["tier"] = 3
        log_entry["modifications"] = ["monitoring", "audit_trail"]
        approval_log.append(log_entry)

        print("✓ Executive approved with modifications")
        return ApprovalResponse(
            approved=True,
            feedback="Executive approved with enhanced monitoring",
            modified_message=modified_msg,
        )


async def contextual_approval_func(request: ApprovalRequest) -> ApprovalResponse:
    """
    Contextual approval based on transaction type, time, and history.
    """
    confidence = request.confidence
    tx_type = request.message.metadata.get("transaction_type", "unknown")
    amount = request.message.metadata.get("amount", 0)
    risk_level = request.message.metadata.get("risk_level", "unknown")

    print(f"\n{'='*60}")
    print("Contextual Approval Analysis")
    print(f"{'='*60}")
    print(f"Type:        {tx_type}")
    print(f"Amount:      ${amount:,}")
    print(f"Confidence:  {confidence:.2f}")
    print(f"Risk:        {risk_level}")

    await asyncio.sleep(0.2)

    # Check transaction type
    if tx_type == "wire_transfer":
        if amount > 10000:
            print("⚠️  High-value wire transfer requires enhanced verification")
            print("   Adding 2FA requirement...")

            modified_msg = Message(
                role="assistant",
                content=f"{request.message.content} [2FA VERIFICATION REQUIRED]",
                metadata={
                    **request.message.metadata,
                    "requires_2fa": True,
                    "verification_level": "enhanced",
                },
            )

            return ApprovalResponse(
                approved=True,
                feedback="Approved with 2FA requirement",
                modified_message=modified_msg,
            )

    # Check recent approval history
    recent_approvals = [log for log in approval_log[-5:] if log["amount"] > 5000]
    if len(recent_approvals) >= 3:
        print("⚠️  Multiple high-value transactions detected")
        print("   Adding fraud review flag...")

        modified_msg = Message(
            role="assistant",
            content=f"{request.message.content} [FLAGGED FOR FRAUD REVIEW]",
            metadata={
                **request.message.metadata,
                "fraud_review_required": True,
                "pattern_detected": "high_frequency",
            },
        )

        return ApprovalResponse(
            approved=True,
            feedback="Approved pending fraud review",
            modified_message=modified_msg,
        )

    # Standard approval
    print("✓ Standard approval")
    return ApprovalResponse(approved=True, feedback="Standard approval")


async def rejection_scenarios() -> None:
    """Demonstrate rejection scenarios with detailed feedback."""
    print("=" * 70)
    print("Example 1: Rejection Scenarios")
    print("=" * 70)

    # Rejection approval function
    async def strict_approval_func(request: ApprovalRequest) -> ApprovalResponse:
        confidence = request.confidence
        amount = request.message.metadata.get("amount", 0)

        print(f"\n[Strict Approval] Amount: ${amount:,}, Confidence: {confidence:.2f}")
        await asyncio.sleep(0.15)

        # Reject very low confidence
        if confidence < 0.5:
            print("   ❌ Rejected - Confidence too low")
            return ApprovalResponse(
                approved=False,
                feedback=f"Confidence {confidence:.2f} below minimum threshold 0.5",
            )

        # Reject suspicious amounts
        if amount in [9999, 10000, 50000]:  # Structured amounts
            print("   ❌ Rejected - Suspicious amount pattern")
            return ApprovalResponse(
                approved=False,
                feedback="Amount appears to be structured to avoid reporting thresholds",
            )

        print("   ✓ Approved")
        return ApprovalResponse(approved=True, feedback="Approved")

    agent = FinancialAgent()
    hil_agent = HumanInLoopAgent(
        HumanInLoopConfig(
            agent=agent,
            approval_func=strict_approval_func,
            approval_threshold=0.8,
        )
    )

    adapter = AGUIHumanInLoopAdapter(hil_agent, agent_name="StrictFinancialAgent")

    # Test rejection cases
    test_cases = [
        "Process payment of $100,000",  # Low confidence
        "Wire transfer of $10,000",  # Suspicious amount
        "Payment of $25,000",  # Normal (approved)
    ]

    for i, test_content in enumerate(test_cases, 1):
        print(f"\n📥 Test {i}: {test_content}")

        message = Message(role="user", content=test_content)
        events = []

        async for event in adapter.stream_events(message):
            events.append(event)
            if isinstance(event, Interrupt):
                status = event.context.get("approval_status")
                print(f"   📡 Interrupt: {status}")

        interrupts = [e for e in events if isinstance(e, Interrupt)]
        print(f"   Result: {len(interrupts)} interrupt(s)")


async def tiered_approval_example() -> None:
    """Demonstrate multi-tiered approval."""
    print("\n\n" + "=" * 70)
    print("Example 2: Multi-Tiered Approval")
    print("=" * 70)

    agent = FinancialAgent()
    hil_agent = HumanInLoopAgent(
        HumanInLoopConfig(
            agent=agent,
            approval_func=tiered_approval_func,
            approval_threshold=0.8,
        )
    )

    adapter = AGUIHumanInLoopAdapter(hil_agent, agent_name="TieredFinancialAgent")

    # Test different approval tiers
    test_cases = [
        ("$500 payment", "Tier 0 (auto)"),
        ("$5,000 transaction", "Tier 1 (manager)"),
        ("$25,000 wire transfer", "Tier 2 (director)"),
        ("$100,000 payment", "Tier 3 (executive + mods)"),
    ]

    for test_content, tier_desc in test_cases:
        print(f"\n📥 Test: {test_content} - Expected: {tier_desc}")

        message = Message(role="user", content=test_content)

        async for event in adapter.stream_events(message):
            if isinstance(event, Interrupt):
                print(f"   📡 Approval Status: {event.context.get('approval_status')}")
                if event.context.get("approval_status") == "approved_with_modifications":
                    print("   ✏️  Modifications applied")


async def contextual_approval_example() -> None:
    """Demonstrate contextual approval logic."""
    print("\n\n" + "=" * 70)
    print("Example 3: Contextual Approval")
    print("=" * 70)

    agent = FinancialAgent()
    hil_agent = HumanInLoopAgent(
        HumanInLoopConfig(
            agent=agent,
            approval_func=contextual_approval_func,
            approval_threshold=0.8,
        )
    )

    adapter = AGUIHumanInLoopAdapter(hil_agent, agent_name="ContextualFinancialAgent")

    # Trigger contextual checks
    test_cases = [
        "Wire transfer of $15,000",  # Triggers 2FA
        "Payment of $8,000",  # Track for pattern
        "Payment of $7,000",  # Track for pattern
        "Payment of $9,000",  # Should trigger fraud review
    ]

    for i, test_content in enumerate(test_cases, 1):
        print(f"\n📥 Test {i}: {test_content}")

        message = Message(role="user", content=test_content)

        async for event in adapter.stream_events(message):
            if isinstance(event, Interrupt):
                status = event.context.get("approval_status")
                print(f"   📡 Status: {status}")


async def approval_audit_report() -> None:
    """Display approval audit log."""
    print("\n\n" + "=" * 70)
    print("Approval Audit Trail")
    print("=" * 70)

    if not approval_log:
        print("No approvals logged")
        return

    print(f"\nTotal approvals: {len(approval_log)}\n")

    for i, entry in enumerate(approval_log, 1):
        print(f"{i}. {entry['timestamp']}")
        print(f"   Amount:   ${entry['amount']:,}")
        print(f"   Decision: {entry['decision']}")
        print(f"   Risk:     {entry.get('risk_level', 'N/A')}")
        if "tier" in entry:
            print(f"   Tier:     {entry['tier']}")
        if "modifications" in entry:
            print(f"   Mods:     {', '.join(entry['modifications'])}")
        print()


async def main() -> None:
    """Run all advanced approval examples."""
    print("\n🎯 Advanced AG-UI HITL Approval Patterns\n")

    await rejection_scenarios()
    await tiered_approval_example()
    await contextual_approval_example()
    await approval_audit_report()

    print("\n✅ All examples complete!")
    print("\nKey Takeaways:")
    print("• Multi-tiered approval based on amount and risk")
    print("• Contextual decisions based on transaction type and history")
    print("• Approval with modifications for high-risk transactions")
    print("• Rejection scenarios with detailed feedback")
    print("• Comprehensive audit trail for compliance")


if __name__ == "__main__":
    asyncio.run(main())
