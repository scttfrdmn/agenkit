"""
Human-in-Loop Pattern Usage Example.

Demonstrates the Human-in-Loop pattern for integrating human approval gates
into agent workflows for high-stakes decisions.

Use cases:
- Financial transaction approval
- Content moderation decisions
- Critical system changes
- Compliance verification

This example shows:
- Simple approval gates
- Confidence-based approval
- Custom approval logic
- Approval with context
"""

import asyncio

from agenkit.core import Agent, Message
from agenkit.patterns import (ApprovalRequest, ApprovalResponse,
                              HumanInLoopAgent, HumanInLoopConfig)


class TransactionAgent(Agent):
    """Processes financial transactions."""

    def name(self) -> str:
        return "TransactionAgent"

    def capabilities(self) -> list[str]:
        return ["transactions", "payments"]

    async def process(self, message: Message) -> Message:
        """Process a transaction."""
        print("   💳 Processing transaction...")
        await asyncio.sleep(0.1)

        # Extract amount from message
        content = message.content.lower()
        amount = 1000  # Default
        if "$" in content:
            try:
                amount = int(content.split("$")[1].split()[0].replace(",", ""))
            except (IndexError, ValueError):
                pass

        result = Message(
            role="agent",
            content=f"Transaction processed: ${amount:,}",
        )
        result.metadata["amount"] = amount
        result.metadata["confidence"] = 0.95 if amount < 10000 else 0.7
        return result


class ContentModerationAgent(Agent):
    """Moderates user-generated content."""

    def name(self) -> str:
        return "ContentModerator"

    def capabilities(self) -> list[str]:
        return ["moderation", "safety"]

    async def process(self, message: Message) -> Message:
        """Moderate content."""
        print("   🛡️  Moderating content...")
        await asyncio.sleep(0.08)

        # Simplified moderation
        content = message.content.lower()
        flags = []
        if "controversial" in content:
            flags.append("controversial")
        if "sensitive" in content:
            flags.append("sensitive")

        decision = "allow" if not flags else "review"
        confidence = 0.95 if not flags else 0.6

        result = Message(
            role="agent",
            content=f"Moderation decision: {decision}",
        )
        result.metadata["flags"] = flags
        result.metadata["confidence"] = confidence
        return result


class DeploymentAgent(Agent):
    """Manages system deployments."""

    def name(self) -> str:
        return "DeploymentAgent"

    def capabilities(self) -> list[str]:
        return ["deployment", "operations"]

    async def process(self, message: Message) -> Message:
        """Plan deployment."""
        print("   🚀 Planning deployment...")
        await asyncio.sleep(0.12)

        # Extract environment
        content = message.content.lower()
        environment = "production" if "prod" in content else "staging"

        result = Message(
            role="agent",
            content=f"Deployment planned for {environment}",
        )
        result.metadata["environment"] = environment
        result.metadata["risk_level"] = "high" if environment == "production" else "medium"
        result.metadata["confidence"] = 0.85
        return result


# Simulated approval functions for demonstration
async def auto_approve_small(request: ApprovalRequest) -> ApprovalResponse:
    """Auto-approve small transactions."""
    amount = request.metadata.get("amount", 0)

    if amount < 1000:
        print(f"   ✓ Auto-approved (${amount} < $1,000)")
        return ApprovalResponse(approved=True, feedback="Auto-approved")

    # Simulate human approval for larger amounts
    print(f"   👤 Human approval requested for ${amount:,}...")
    await asyncio.sleep(0.2)  # Simulate human review time

    # For demo, approve amounts under 50k
    approved = amount < 50000
    feedback = "Approved by manager" if approved else "Exceeds approval limit"

    print(f"   {'✓' if approved else '✗'} {feedback}")
    return ApprovalResponse(approved=approved, feedback=feedback)


async def content_approval(request: ApprovalRequest) -> ApprovalResponse:
    """Approve content moderation decisions."""
    flags = request.metadata.get("flags", [])

    if not flags:
        print("   ✓ Auto-approved (no flags)")
        return ApprovalResponse(approved=True, feedback="No issues detected")

    # Simulate human review
    print(f"   👤 Human review requested (flags: {', '.join(flags)})...")
    await asyncio.sleep(0.2)

    # For demo, approve non-sensitive content
    approved = "sensitive" not in flags
    feedback = "Approved by moderator" if approved else "Flagged for revision"

    print(f"   {'✓' if approved else '✗'} {feedback}")
    return ApprovalResponse(approved=approved, feedback=feedback)


async def deployment_approval(request: ApprovalRequest) -> ApprovalResponse:
    """Approve deployment operations."""
    environment = request.metadata.get("environment", "unknown")
    risk_level = request.metadata.get("risk_level", "unknown")

    if environment != "production":
        print(f"   ✓ Auto-approved ({environment} deployment)")
        return ApprovalResponse(approved=True, feedback="Non-prod auto-approved")

    # Production deployments require approval
    print(f"   👤 Production deployment approval requested (risk: {risk_level})...")
    await asyncio.sleep(0.3)

    # For demo, approve all
    approved = True
    feedback = "Approved by ops team"

    print(f"   ✓ {feedback}")
    return ApprovalResponse(approved=approved, feedback=feedback)


async def financial_approval():
    """Demonstrate financial transaction approval."""
    print("=" * 60)
    print("Example 1: Financial Transaction Approval")
    print("=" * 60)

    config = HumanInLoopConfig(
        require_approval=True,
        timeout_seconds=10,
    )

    agent = HumanInLoopAgent(
        agent=TransactionAgent(),
        approval_func=auto_approve_small,
        config=config,
    )

    # Small transaction (auto-approved)
    message1 = Message(role="user", content="Process payment of $500")
    print(f"\n📥 Request 1: {message1.content}")
    result1 = await agent.process(message1)
    print(f"📤 Result: {result1.content}\n")

    # Large transaction (requires approval)
    message2 = Message(role="user", content="Process payment of $25,000")
    print(f"📥 Request 2: {message2.content}")
    result2 = await agent.process(message2)
    print(f"📤 Result: {result2.content}")
    print(f"   Approval feedback: {result2.metadata.get('approval_feedback')}")


async def content_moderation():
    """Demonstrate content moderation approval."""
    print("\n\n" + "=" * 60)
    print("Example 2: Content Moderation Approval")
    print("=" * 60)

    config = HumanInLoopConfig(
        require_approval=True,
        timeout_seconds=5,
    )

    agent = HumanInLoopAgent(
        agent=ContentModerationAgent(),
        approval_func=content_approval,
        config=config,
    )

    # Clean content
    message1 = Message(role="user", content="This is a normal post about technology")
    print(f"\n📥 Content 1: {message1.content}")
    result1 = await agent.process(message1)
    print(f"📤 Decision: {result1.content}\n")

    # Flagged content
    message2 = Message(role="user", content="This is controversial and sensitive content")
    print(f"📥 Content 2: {message2.content}")
    result2 = await agent.process(message2)
    print(f"📤 Decision: {result2.content}")
    print(f"   Approval: {'Yes' if result2.metadata.get('approved') else 'No'}")


async def confidence_based():
    """Demonstrate confidence-based approval."""
    print("\n\n" + "=" * 60)
    print("Example 3: Confidence-Based Approval")
    print("=" * 60)

    # Only require approval for low-confidence decisions
    async def confidence_approval(request: ApprovalRequest) -> ApprovalResponse:
        confidence = request.metadata.get("confidence", 0.5)

        if confidence >= 0.9:
            print(f"   ✓ Auto-approved (high confidence: {confidence:.2f})")
            return ApprovalResponse(approved=True, feedback="High confidence")

        print(f"   👤 Human review requested (low confidence: {confidence:.2f})...")
        await asyncio.sleep(0.2)

        # For demo, approve all after review
        print("   ✓ Approved after review")
        return ApprovalResponse(approved=True, feedback="Approved by reviewer")

    config = HumanInLoopConfig(
        require_approval=True,
        timeout_seconds=10,
    )

    agent = HumanInLoopAgent(
        agent=TransactionAgent(),
        approval_func=confidence_approval,
        config=config,
    )

    # High confidence (auto)
    message1 = Message(role="user", content="Process payment of $500")
    print(f"\n📥 Transaction 1: {message1.content}")
    result1 = await agent.process(message1)
    print(f"📤 {result1.content}\n")

    # Low confidence (requires approval)
    message2 = Message(role="user", content="Process payment of $75,000")
    print(f"📥 Transaction 2: {message2.content}")
    result2 = await agent.process(message2)
    print(f"📤 {result2.content}")


async def deployment_workflow():
    """Demonstrate deployment approval workflow."""
    print("\n\n" + "=" * 60)
    print("Example 4: Deployment Approval Workflow")
    print("=" * 60)

    config = HumanInLoopConfig(
        require_approval=True,
        timeout_seconds=15,
    )

    agent = HumanInLoopAgent(
        agent=DeploymentAgent(),
        approval_func=deployment_approval,
        config=config,
    )

    # Staging deployment
    message1 = Message(role="user", content="Deploy to staging environment")
    print(f"\n📥 Request 1: {message1.content}")
    result1 = await agent.process(message1)
    print(f"📤 {result1.content}\n")

    # Production deployment
    message2 = Message(role="user", content="Deploy to production")
    print(f"📥 Request 2: {message2.content}")
    result2 = await agent.process(message2)
    print(f"📤 {result2.content}")
    print(f"   Risk level: {result2.metadata.get('risk_level')}")


async def main():
    """Run all examples."""
    print("\n👤 Human-in-Loop Pattern Usage Examples\n")

    await financial_approval()
    await content_moderation()
    await confidence_based()
    await deployment_workflow()

    print("\n✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
