"""
Router + Supervisor Pattern Composition.

Demonstrates routing requests to specialized supervisors that decompose
and coordinate complex tasks.

Use case: Customer support system with specialized departments.

This example shows:
- Intent-based routing to supervisors
- Each supervisor decomposes domain-specific tasks
- Specialized worker agents per department
- Hierarchical coordination
"""

import asyncio

from agenkit.core import Agent, Message
from agenkit.patterns import (
    RouterAgent,
    SimpleClassifier,
    SimplePlanner,
    Subtask,
    SupervisorAgent,
)


# Technical Support Workers
class DiagnosticAgent(Agent):
    """Diagnoses technical issues."""

    def name(self) -> str:
        return "DiagnosticAgent"

    def capabilities(self) -> list[str]:
        return ["diagnosis"]

    async def process(self, message: Message) -> Message:
        print("     🔍 Running diagnostics...")
        await asyncio.sleep(0.08)
        return Message(
            role="agent",
            content="Diagnostics complete: Issue identified",
        )


class RepairAgent(Agent):
    """Repairs technical issues."""

    def name(self) -> str:
        return "RepairAgent"

    def capabilities(self) -> list[str]:
        return ["repair"]

    async def process(self, message: Message) -> Message:
        print("     🔧 Applying fix...")
        await asyncio.sleep(0.1)
        return Message(
            role="agent",
            content="Fix applied successfully",
        )


class ValidationAgent(Agent):
    """Validates repairs."""

    def name(self) -> str:
        return "ValidationAgent"

    def capabilities(self) -> list[str]:
        return ["validation"]

    async def process(self, message: Message) -> Message:
        print("     ✓ Validating fix...")
        await asyncio.sleep(0.06)
        return Message(
            role="agent",
            content="Validation passed",
        )


# Billing Support Workers
class AccountLookupAgent(Agent):
    """Looks up account information."""

    def name(self) -> str:
        return "AccountLookup"

    def capabilities(self) -> list[str]:
        return ["lookup"]

    async def process(self, message: Message) -> Message:
        print("     🔎 Looking up account...")
        await asyncio.sleep(0.07)
        return Message(
            role="agent",
            content="Account found: #12345",
        )


class BillingCalculationAgent(Agent):
    """Calculates billing adjustments."""

    def name(self) -> str:
        return "BillingCalculation"

    def capabilities(self) -> list[str]:
        return ["calculation"]

    async def process(self, message: Message) -> Message:
        print("     💰 Calculating adjustment...")
        await asyncio.sleep(0.09)
        return Message(
            role="agent",
            content="Adjustment: -$25.00",
        )


class RefundProcessingAgent(Agent):
    """Processes refunds."""

    def name(self) -> str:
        return "RefundProcessing"

    def capabilities(self) -> list[str]:
        return ["processing"]

    async def process(self, message: Message) -> Message:
        print("     💳 Processing refund...")
        await asyncio.sleep(0.1)
        return Message(
            role="agent",
            content="Refund processed: $25.00",
        )


# Planners for each supervisor
class TechnicalPlanner(SimplePlanner):
    """Plans technical support tasks."""

    def plan(self, message: Message) -> list[Subtask]:
        return [
            Subtask("Diagnose the issue", "diagnosis"),
            Subtask("Apply repair", "repair"),
            Subtask("Validate fix", "validation"),
        ]


class BillingPlanner(SimplePlanner):
    """Plans billing support tasks."""

    def plan(self, message: Message) -> list[Subtask]:
        return [
            Subtask("Look up account", "lookup"),
            Subtask("Calculate adjustment", "calculation"),
            Subtask("Process refund", "processing"),
        ]


# Intent classifier
class SupportClassifier(SimpleClassifier):
    """Classifies support requests."""

    def classify(self, message: Message) -> str:
        content = message.content.lower()

        if any(word in content for word in ["error", "bug", "broken", "not working"]):
            return "technical"
        elif any(word in content for word in ["bill", "charge", "refund", "payment"]):
            return "billing"
        else:
            return "general"


# General support (simple handler)
class GeneralSupportAgent(Agent):
    """Handles general inquiries."""

    def name(self) -> str:
        return "GeneralSupport"

    def capabilities(self) -> list[str]:
        return ["general"]

    async def process(self, message: Message) -> Message:
        print("   📞 General Support handling inquiry...")
        await asyncio.sleep(0.1)
        return Message(
            role="agent",
            content="General inquiry answered: See documentation at docs.example.com",
        )


async def main():
    """Demonstrate router + supervisor composition."""
    print("=" * 60)
    print("Router + Supervisor Pattern Composition")
    print("Customer Support System")
    print("=" * 60)

    # Create specialized supervisors
    technical_supervisor = SupervisorAgent(
        planner=TechnicalPlanner(),
        workers=[
            DiagnosticAgent(),
            RepairAgent(),
            ValidationAgent(),
        ],
    )

    billing_supervisor = SupervisorAgent(
        planner=BillingPlanner(),
        workers=[
            AccountLookupAgent(),
            BillingCalculationAgent(),
            RefundProcessingAgent(),
        ],
    )

    # Create router to supervisors
    support_router = RouterAgent(
        classifier=SupportClassifier(),
        routes={
            "technical": technical_supervisor,
            "billing": billing_supervisor,
            "general": GeneralSupportAgent(),
        },
    )

    # Test different request types
    requests = [
        "My application is showing an error when I try to save",
        "I was charged twice for my subscription this month",
        "What features are available in the premium plan?",
    ]

    for i, req in enumerate(requests, 1):
        print(f"\n{'=' * 60}")
        print(f"\n📥 Request {i}: {req}\n")

        message = Message(role="user", content=req)
        result = await support_router.process(message)

        print(f"\n📤 Resolution:\n{result.content}")

        if "subtasks_completed" in result.metadata:
            print("\n   Workflow: Supervised task decomposition")
            print(f"   Subtasks: {result.metadata['subtasks_completed']}")
        else:
            print("\n   Workflow: Direct handling")

    print(f"\n{'=' * 60}")
    print("\n✅ All support requests handled!")
    print("\nArchitecture:")
    print("  Router -> [Technical Supervisor, Billing Supervisor, General Agent]")
    print("  Each supervisor coordinates specialized workers")


if __name__ == "__main__":
    asyncio.run(main())
