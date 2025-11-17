"""
Customer Support Agent System - Main Application

End-to-end example demonstrating:
- Multi-agent orchestration
- RAG with vector store
- Production patterns (classification, QA, escalation, synthesis)
- Sequential agent workflow

Usage:
    python main.py

Or programmatically:
    from main import CustomerSupportSystem
    system = CustomerSupportSystem()
    result = await system.handle_ticket("How do I reset my password?")
"""

import asyncio
from typing import Dict, Any
from agenkit import Message

# Import our components
from knowledge_base import create_sample_knowledge_base
from agents import (
    ClassifierAgent,
    QAAgent,
    EscalationAgent,
    SynthesisAgent,
)


class CustomerSupportSystem:
    """
    Complete customer support system with multi-agent workflow.

    Architecture:
        1. ClassifierAgent: Categorize and prioritize tickets
        2. QAAgent: Answer questions using knowledge base (RAG)
        3. EscalationAgent: Decide if human intervention needed
        4. SynthesisAgent: Create final customer-facing response

    Example:
        ```python
        system = CustomerSupportSystem()
        result = await system.handle_ticket("I forgot my password")

        print(f"Response: {result['response']}")
        print(f"Escalated: {result['escalated']}")
        print(f"Category: {result['category']}")
        ```
    """

    def __init__(self):
        """Initialize the support system."""
        # Create knowledge base
        self.knowledge_base = create_sample_knowledge_base()
        print(f"✓ Knowledge base loaded ({self.knowledge_base.count()} documents)")

        # Initialize agents
        self.classifier = ClassifierAgent()
        self.qa_agent = QAAgent(self.knowledge_base, top_k=3)
        self.escalation_agent = EscalationAgent(confidence_threshold=0.5)
        self.synthesis_agent = SynthesisAgent()

        print("✓ All agents initialized")

    async def handle_ticket(
        self, ticket_content: str, verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Process a customer support ticket through the agent pipeline.

        Args:
            ticket_content: The customer's message/question
            verbose: Print detailed step-by-step information

        Returns:
            Dict containing:
            - response: Final customer-facing response
            - escalated: Whether ticket was escalated to human
            - category: Ticket category
            - priority: Ticket priority
            - confidence: System confidence in answer
            - sources: Knowledge base sources used
        """
        if verbose:
            print("\n" + "=" * 70)
            print(f"Processing ticket: {ticket_content}")
            print("=" * 70)

        # Step 1: Classify the ticket
        if verbose:
            print("\n[1/4] Classifying ticket...")

        classification_result = await self.classifier.process(
            Message(role="user", content=ticket_content)
        )

        category = classification_result.metadata["category"]
        priority = classification_result.metadata["priority"]
        confidence = classification_result.metadata["confidence"]

        if verbose:
            print(f"      Category: {category}")
            print(f"      Priority: {priority}")
            print(f"      Confidence: {confidence:.2f}")

        # Step 2: Get answer from QA agent
        if verbose:
            print("\n[2/4] Searching knowledge base...")

        qa_result = await self.qa_agent.process(
            Message(role="user", content=ticket_content)
        )

        qa_response = qa_result.content
        qa_confidence = qa_result.metadata.get("confidence", 0.0)
        sources = qa_result.metadata.get("sources", [])

        if verbose:
            print(f"      Found {len(sources)} relevant documents")
            print(f"      Answer confidence: {qa_confidence:.2f}")

        # Step 3: Check if escalation needed
        if verbose:
            print("\n[3/4] Checking escalation criteria...")

        escalation_result = await self.escalation_agent.process(
            Message(
                role="assistant",
                content=qa_response,
                metadata={
                    "confidence": qa_confidence,
                    "priority": priority,
                    "category": category,
                },
            )
        )

        should_escalate = escalation_result.metadata["should_escalate"]
        escalation_reason = escalation_result.metadata["reason"]

        if verbose:
            if should_escalate:
                print(f"      ⚠ Escalation required: {escalation_reason}")
            else:
                print(f"      ✓ No escalation needed: {escalation_reason}")

        # Step 4: Synthesize final response
        if verbose:
            print("\n[4/4] Creating final response...")

        final_result = await self.synthesis_agent.process(
            Message(
                role="assistant",
                content="",
                metadata={
                    "classification": classification_result.metadata,
                    "qa_response": qa_response,
                    "escalation": escalation_result.metadata,
                    "confidence": qa_confidence,
                },
            )
        )

        final_response = final_result.content

        if verbose:
            print("\n" + "=" * 70)
            print("FINAL RESPONSE:")
            print("=" * 70)
            print(final_response)
            print("=" * 70)

        # Return comprehensive result
        return {
            "response": final_response,
            "escalated": should_escalate,
            "escalation_reason": escalation_reason if should_escalate else None,
            "category": category,
            "priority": priority,
            "confidence": qa_confidence,
            "sources": sources,
            "num_sources": len(sources),
        }


async def demo_tickets():
    """Demonstrate the system with various ticket examples."""
    print("\n" + "=" * 70)
    print("CUSTOMER SUPPORT SYSTEM - DEMO")
    print("=" * 70)

    # Initialize system
    system = CustomerSupportSystem()

    # Test tickets covering different scenarios
    test_tickets = [
        {
            "content": "How do I reset my password?",
            "description": "Common account question",
        },
        {
            "content": "I need to cancel my subscription immediately!",
            "description": "Sensitive billing issue (should escalate)",
        },
        {
            "content": "What's included in the Premium plan?",
            "description": "Product information query",
        },
        {
            "content": "The app is completely broken and I can't access my data!",
            "description": "Critical technical issue (should escalate)",
        },
        {
            "content": "How do I share a file with my team?",
            "description": "Collaboration feature question",
        },
    ]

    # Process each ticket
    for i, ticket in enumerate(test_tickets, 1):
        print(f"\n\n{'*' * 70}")
        print(f"DEMO TICKET #{i}: {ticket['description']}")
        print(f"{'*' * 70}")

        result = await system.handle_ticket(ticket["content"], verbose=True)

        # Print summary
        print("\nSUMMARY:")
        print(f"  Escalated: {'Yes' if result['escalated'] else 'No'}")
        print(f"  Category: {result['category']}")
        print(f"  Priority: {result['priority']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Sources used: {result['num_sources']}")

        # Small delay between tickets for readability
        await asyncio.sleep(0.5)

    print("\n\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


async def interactive_mode():
    """Interactive mode for testing the system."""
    print("\n" + "=" * 70)
    print("CUSTOMER SUPPORT SYSTEM - INTERACTIVE MODE")
    print("=" * 70)
    print("\nType your support questions (or 'quit' to exit)")
    print("=" * 70)

    system = CustomerSupportSystem()

    while True:
        print("\n")
        ticket = input("Your question: ").strip()

        if ticket.lower() in ["quit", "exit", "q"]:
            print("\nGoodbye!")
            break

        if not ticket:
            continue

        result = await system.handle_ticket(ticket, verbose=True)


async def main():
    """Main entry point."""
    import sys

    # Check for command-line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "interactive":
            await interactive_mode()
            return

    # Default: run demo
    await demo_tickets()


if __name__ == "__main__":
    asyncio.run(main())
