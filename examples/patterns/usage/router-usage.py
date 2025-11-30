"""
Router Pattern Usage Example.

Demonstrates the Router pattern for conditional agent selection based on
input classification.

Use cases:
- Intent-based routing
- Specialized agent dispatch
- Dynamic workflow selection
- Load distribution

This example shows:
- Simple rule-based routing
- LLM-based classification
- Multi-route handling
- Fallback routing
"""

import asyncio

from agenkit.core import Agent, Message
from agenkit.patterns import RouterAgent, SimpleClassifier


class TechnicalSupportAgent(Agent):
    """Handles technical support requests."""

    def name(self) -> str:
        return "TechnicalSupport"

    def capabilities(self) -> list[str]:
        return ["technical", "troubleshooting"]

    async def process(self, message: Message) -> Message:
        """Handle technical support."""
        print("   🔧 Technical Support handling request...")
        await asyncio.sleep(0.1)

        response = "Technical Support Response:\n"
        response += "- Issue logged: #TS-" + str(hash(message.content) % 10000) + "\n"
        response += "- Troubleshooting steps provided\n"
        response += "- Estimated resolution: 24 hours\n"

        result = Message(role="agent", content=response)
        result.metadata["department"] = "technical"
        return result


class BillingSupportAgent(Agent):
    """Handles billing and payment questions."""

    def name(self) -> str:
        return "BillingSupport"

    def capabilities(self) -> list[str]:
        return ["billing", "payments"]

    async def process(self, message: Message) -> Message:
        """Handle billing support."""
        print("   💳 Billing Support handling request...")
        await asyncio.sleep(0.1)

        response = "Billing Support Response:\n"
        response += "- Account reviewed\n"
        response += "- Payment status: Current\n"
        response += "- Invoice sent to email\n"

        result = Message(role="agent", content=response)
        result.metadata["department"] = "billing"
        return result


class GeneralSupportAgent(Agent):
    """Handles general inquiries."""

    def name(self) -> str:
        return "GeneralSupport"

    def capabilities(self) -> list[str]:
        return ["general", "information"]

    async def process(self, message: Message) -> Message:
        """Handle general support."""
        print("   📞 General Support handling request...")
        await asyncio.sleep(0.1)

        response = "General Support Response:\n"
        response += "- Information provided\n"
        response += "- Additional resources: docs.example.com\n"
        response += "- Follow-up scheduled if needed\n"

        result = Message(role="agent", content=response)
        result.metadata["department"] = "general"
        return result


class SupportClassifier(SimpleClassifier):
    """Classifies support requests by type."""

    def classify(self, message: Message) -> str:
        """Classify the support request."""
        content = message.content.lower()

        # Technical keywords
        if any(word in content for word in ["error", "bug", "crash", "not working", "broken"]):
            return "technical"

        # Billing keywords
        if any(word in content for word in ["bill", "payment", "invoice", "charge", "refund"]):
            return "billing"

        # Default to general
        return "general"


async def basic_routing():
    """Demonstrate basic intent-based routing."""
    print("=" * 60)
    print("Example 1: Intent-Based Routing")
    print("=" * 60)

    # Create router with classifier
    router = RouterAgent(
        classifier=SupportClassifier(),
        routes={
            "technical": TechnicalSupportAgent(),
            "billing": BillingSupportAgent(),
            "general": GeneralSupportAgent(),
        },
    )

    # Test different request types
    requests = [
        "My application keeps crashing when I try to save files",
        "I was charged twice for my subscription",
        "What features are included in the premium plan?",
    ]

    for i, req in enumerate(requests, 1):
        print(f"\n📥 Request {i}: {req}")

        message = Message(role="user", content=req)
        result = await router.process(message)

        print(f"\n📤 Response:\n{result.content}")
        print(f"   Routed to: {result.metadata.get('department')}")


async def fallback_routing():
    """Demonstrate fallback when no route matches."""
    print("\n\n" + "=" * 60)
    print("Example 2: Fallback Routing")
    print("=" * 60)

    # Create router with default route
    router = RouterAgent(
        classifier=SupportClassifier(),
        routes={
            "technical": TechnicalSupportAgent(),
            "billing": BillingSupportAgent(),
        },
        default_route=GeneralSupportAgent(),  # Fallback
    )

    message = Message(
        role="user",
        content="What are your business hours?",
    )

    print(f"\n📥 Request: {message.content}")
    print("   (No specific technical or billing keywords)")

    result = await router.process(message)

    print(f"\n📤 Response:\n{result.content}")
    print(f"   Routed to: {result.metadata.get('department')} (fallback)")


async def metadata_based_routing():
    """Demonstrate routing based on metadata."""
    print("\n\n" + "=" * 60)
    print("Example 3: Metadata-Based Classification")
    print("=" * 60)

    class MetadataClassifier(SimpleClassifier):
        """Classifier that uses metadata in addition to content."""

        def classify(self, message: Message) -> str:
            # Check if priority is set in metadata
            if message.metadata.get("priority") == "urgent":
                return "technical"  # Route urgent to technical

            # Otherwise use content
            content = message.content.lower()
            if "payment" in content:
                return "billing"
            return "general"

    router = RouterAgent(
        classifier=MetadataClassifier(),
        routes={
            "technical": TechnicalSupportAgent(),
            "billing": BillingSupportAgent(),
            "general": GeneralSupportAgent(),
        },
    )

    # Normal priority
    message1 = Message(role="user", content="I have a question about features")
    message1.metadata["priority"] = "normal"

    print(f"\n📥 Request 1: {message1.content}")
    print(f"   Priority: {message1.metadata['priority']}")

    result1 = await router.process(message1)
    print(f"   Routed to: {result1.metadata.get('department')}")

    # Urgent priority
    message2 = Message(role="user", content="I have a question about features")
    message2.metadata["priority"] = "urgent"

    print(f"\n📥 Request 2: {message2.content}")
    print(f"   Priority: {message2.metadata['priority']}")

    result2 = await router.process(message2)
    print(f"   Routed to: {result2.metadata.get('department')}")


async def multi_classifier():
    """Demonstrate routing with multiple classification criteria."""
    print("\n\n" + "=" * 60)
    print("Example 4: Complex Classification")
    print("=" * 60)

    class ComplexClassifier(SimpleClassifier):
        """Classifier with multiple criteria."""

        def classify(self, message: Message) -> str:
            content = message.content.lower()

            # Check customer tier
            tier = message.metadata.get("customer_tier", "standard")

            # VIP customers go to technical for anything important
            if tier == "vip" and any(word in content for word in
                                      ["urgent", "critical", "important"]):
                return "technical"

            # Standard classification
            if "payment" in content or "bill" in content:
                return "billing"
            elif "error" in content or "bug" in content:
                return "technical"
            else:
                return "general"

    router = RouterAgent(
        classifier=ComplexClassifier(),
        routes={
            "technical": TechnicalSupportAgent(),
            "billing": BillingSupportAgent(),
            "general": GeneralSupportAgent(),
        },
    )

    # VIP customer with urgent issue
    message = Message(
        role="user",
        content="This is urgent - I need help with my account",
    )
    message.metadata["customer_tier"] = "vip"

    print(f"\n📥 Request: {message.content}")
    print(f"   Customer tier: {message.metadata['customer_tier']}")

    result = await router.process(message)

    print(f"\n📤 Response preview:\n{result.content[:100]}...")
    print(f"   Routed to: {result.metadata.get('department')}")
    print("   (VIP customer routed to technical for urgent requests)")


async def main():
    """Run all examples."""
    print("\n🔀 Router Pattern Usage Examples\n")

    await basic_routing()
    await fallback_routing()
    await metadata_based_routing()
    await multi_classifier()

    print("\n✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
