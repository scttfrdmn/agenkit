"""
Customer Support Bot Agent

An AI agent that provides customer support with:
- Context-aware conversation tracking
- Issue classification and routing
- Escalation to human agents
- Knowledge base integration
- Resolution tracking
"""

import asyncio
from datetime import datetime
from typing import Any
from uuid import uuid4

from agenkit import Agent, Message


class SupportTicket:
    """Represents a customer support ticket."""

    def __init__(self, customer_id: str, issue_type: str, priority: str):
        self.ticket_id = str(uuid4())[:8]
        self.customer_id = customer_id
        self.issue_type = issue_type
        self.priority = priority
        self.status = "open"
        self.created_at = datetime.utcnow()
        self.messages = []
        self.resolution = None
        self.escalated = False

    def add_message(self, role: str, content: str):
        """Add message to ticket history."""
        self.messages.append(
            {"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()}
        )

    def escalate(self, reason: str):
        """Escalate ticket to human agent."""
        self.escalated = True
        self.status = "escalated"
        self.add_message("system", f"Ticket escalated: {reason}")

    def resolve(self, resolution: str):
        """Mark ticket as resolved."""
        self.status = "resolved"
        self.resolution = resolution
        self.add_message("system", f"Ticket resolved: {resolution}")


class CustomerSupportAgent(Agent):
    """
    Customer support agent with context tracking and escalation.

    Handles common support scenarios:
    - Technical issues
    - Billing questions
    - Account management
    - Product inquiries
    - Bug reports
    """

    def __init__(self, name: str = "SupportBot"):
        self._name = name
        self._tickets = {}  # ticket_id -> SupportTicket
        self._customer_sessions = {}  # customer_id -> current_ticket_id
        self._interaction_count = 0

        # Knowledge base (simplified)
        self._knowledge_base = {
            "login": {
                "solution": "Try resetting your password using the 'Forgot Password' link. "
                "If that doesn't work, clear your browser cache and cookies.",
                "priority": "medium",
                "category": "technical",
            },
            "billing": {
                "solution": "You can view and download invoices from your account dashboard. "
                "For billing disputes, please contact billing@example.com.",
                "priority": "high",
                "category": "billing",
            },
            "feature": {
                "solution": "That feature is available in our Pro plan. "
                "You can upgrade from your account settings.",
                "priority": "low",
                "category": "product",
            },
            "bug": {
                "solution": "Thank you for reporting this issue. I'll create a bug report "
                "for our engineering team. Can you provide steps to reproduce?",
                "priority": "high",
                "category": "technical",
            },
            "slow": {
                "solution": "Performance issues can be caused by network congestion or "
                "server load. Try refreshing the page or clearing your cache.",
                "priority": "medium",
                "category": "technical",
            },
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return [
            "customer_support",
            "context_tracking",
            "issue_classification",
            "escalation",
            "knowledge_base",
            "conversation_history",
        ]

    async def process(self, message: Message) -> Message:
        """
        Process customer support query with context awareness.

        Maintains conversation history, classifies issues, provides
        solutions from knowledge base, and escalates when needed.
        """
        self._interaction_count += 1
        content = str(message.content).lower().strip()
        metadata = message.metadata or {}

        # Get or create customer session
        customer_id = metadata.get("customer_id", "anonymous")
        ticket = self._get_or_create_ticket(customer_id, content)

        # Add customer message to history
        ticket.add_message("customer", content)

        # Classify issue and determine response
        classification = self._classify_issue(content, ticket)

        # Check if escalation is needed
        if self._should_escalate(content, ticket, classification):
            response = await self._handle_escalation(ticket, classification)
        else:
            response = await self._generate_response(content, ticket, classification)

        # Add response to history
        ticket.add_message("agent", response["content"])

        # Check for resolution
        if response.get("resolved"):
            ticket.resolve(response.get("resolution_summary", "Issue resolved"))

        return Message(
            role="assistant",
            content=response["content"],
            metadata={
                "ticket_id": ticket.ticket_id,
                "customer_id": customer_id,
                "issue_type": classification["issue_type"],
                "priority": classification["priority"],
                "status": ticket.status,
                "escalated": ticket.escalated,
                "interaction_count": len(ticket.messages),
                "conversation_history": ticket.messages[-5:],  # Last 5 messages
            },
        )

    def _get_or_create_ticket(self, customer_id: str, content: str) -> SupportTicket:
        """Get existing ticket or create new one for customer."""
        # Check if customer has active ticket
        if customer_id in self._customer_sessions:
            ticket_id = self._customer_sessions[customer_id]
            if ticket_id in self._tickets and self._tickets[ticket_id].status == "open":
                return self._tickets[ticket_id]

        # Create new ticket
        classification = self._classify_issue(content, None)
        ticket = SupportTicket(
            customer_id=customer_id,
            issue_type=classification["issue_type"],
            priority=classification["priority"],
        )

        self._tickets[ticket.ticket_id] = ticket
        self._customer_sessions[customer_id] = ticket.ticket_id

        return ticket

    def _classify_issue(self, content: str, ticket: SupportTicket | None) -> dict[str, Any]:
        """Classify customer issue based on content and history."""
        # Check knowledge base keywords
        for keyword, info in self._knowledge_base.items():
            if keyword in content:
                return {
                    "issue_type": info["category"],
                    "priority": info["priority"],
                    "keyword": keyword,
                    "has_solution": True,
                }

        # Fallback classification
        if any(word in content for word in ["urgent", "emergency", "critical", "immediately"]):
            priority = "high"
        elif any(word in content for word in ["slow", "annoying", "frustrating"]):
            priority = "medium"
        else:
            priority = "low"

        # Determine issue type
        if any(word in content for word in ["pay", "charge", "invoice", "refund", "billing"]):
            issue_type = "billing"
        elif any(word in content for word in ["error", "crash", "broken", "bug", "issue"]):
            issue_type = "technical"
        elif any(word in content for word in ["how", "what", "where", "can i"]):
            issue_type = "inquiry"
        else:
            issue_type = "general"

        return {"issue_type": issue_type, "priority": priority, "has_solution": False}

    def _should_escalate(
        self, content: str, ticket: SupportTicket, classification: dict[str, Any]
    ) -> bool:
        """Determine if ticket should be escalated to human agent."""
        # Escalate if customer explicitly requests it
        if any(
            word in content for word in ["human", "person", "agent", "representative", "manager"]
        ):
            return True

        # Escalate high-priority billing issues
        if classification["issue_type"] == "billing" and classification["priority"] == "high":
            return True

        # Escalate if conversation is too long without resolution
        if len(ticket.messages) > 10 and ticket.status == "open":
            return True

        # Escalate if customer expresses frustration
        return any(
            word in content for word in ["angry", "frustrated", "terrible", "awful", "unacceptable"]
        )

    async def _handle_escalation(
        self, ticket: SupportTicket, classification: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle ticket escalation."""
        await asyncio.sleep(0.2)  # Simulate processing

        reason = "Customer requested human assistance"
        if classification["priority"] == "high":
            reason = "High-priority issue requiring human expertise"
        elif len(ticket.messages) > 10:
            reason = "Extended conversation without resolution"

        ticket.escalate(reason)

        content = f"""
I understand this situation requires specialized assistance. I'm escalating your case
to a human support agent who will help you shortly.

**Ticket Details:**
- Ticket ID: {ticket.ticket_id}
- Issue Type: {classification["issue_type"].title()}
- Priority: {classification["priority"].upper()}
- Created: {ticket.created_at.strftime("%Y-%m-%d %H:%M UTC")}

**What happens next:**
1. A support specialist will review your case
2. You'll receive an email when they're ready to assist
3. Average response time: {self._get_response_time(classification["priority"])}

In the meantime, you can check your ticket status at support.example.com/tickets/{ticket.ticket_id}

Is there anything else I can help you with while you wait?
"""

        return {"content": content, "resolved": False, "escalated": True}

    async def _generate_response(
        self, content: str, ticket: SupportTicket, classification: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate contextual support response."""
        await asyncio.sleep(0.3)  # Simulate processing

        # Check knowledge base
        if classification.get("has_solution"):
            keyword = classification["keyword"]
            kb_info = self._knowledge_base[keyword]

            # First-time response with solution
            if len(ticket.messages) <= 2:
                response_content = f"""
Thank you for contacting support! I can help you with that.

**Issue Identified:** {keyword.title()} Issue
**Priority:** {classification["priority"].upper()}
**Ticket ID:** {ticket.ticket_id}

**Solution:**
{kb_info["solution"]}

**Additional Resources:**
- Help Center: https://help.example.com/{keyword}
- Video Tutorial: https://videos.example.com/{keyword}-guide
- Community Forum: https://community.example.com/t/{keyword}

Did this resolve your issue?
"""

                return {
                    "content": response_content,
                    "resolved": False,
                    "has_solution": True,
                }

            # Follow-up response
            else:
                response_content = f"""
I see you're still experiencing difficulties. Let me provide additional guidance:

**Alternative Solutions:**
1. Try accessing from a different browser or device
2. Check if there are any system status updates at status.example.com
3. Verify your account settings are configured correctly

**If the issue persists:**
I can escalate this to our technical team or connect you with a specialist.
Just let me know how you'd like to proceed!

Is there specific aspect of the {keyword} issue that's not working?
"""

                return {
                    "content": response_content,
                    "resolved": False,
                }

        # General support response
        else:
            response_content = f"""
Thank you for reaching out! I'd be happy to assist you.

**Ticket Information:**
- Ticket ID: {ticket.ticket_id}
- Category: {classification["issue_type"].title()}
- Priority: {classification["priority"].upper()}

To better help you, could you provide:
- What you were trying to do
- What actually happened
- Any error messages you saw
- When the issue started

**While you provide those details, here are some quick resources:**
- Status page: https://status.example.com
- FAQ: https://help.example.com/faq
- Getting started: https://help.example.com/getting-started

I'm here to help resolve this quickly!
"""

            return {
                "content": response_content,
                "resolved": False,
            }

    def _get_response_time(self, priority: str) -> str:
        """Get expected response time based on priority."""
        times = {
            "high": "15-30 minutes",
            "medium": "2-4 hours",
            "low": "24 hours",
        }
        return times.get(priority, "4-8 hours")

    def get_ticket(self, ticket_id: str) -> SupportTicket | None:
        """Retrieve ticket by ID."""
        return self._tickets.get(ticket_id)

    def get_customer_tickets(self, customer_id: str) -> list[SupportTicket]:
        """Get all tickets for a customer."""
        return [t for t in self._tickets.values() if t.customer_id == customer_id]

    def get_statistics(self) -> dict[str, Any]:
        """Get support statistics."""
        total = len(self._tickets)
        if total == 0:
            return {"total_tickets": 0}

        open_tickets = sum(1 for t in self._tickets.values() if t.status == "open")
        resolved = sum(1 for t in self._tickets.values() if t.status == "resolved")
        escalated = sum(1 for t in self._tickets.values() if t.escalated)

        return {
            "total_tickets": total,
            "open": open_tickets,
            "resolved": resolved,
            "escalated": escalated,
            "resolution_rate": resolved / total if total > 0 else 0,
            "escalation_rate": escalated / total if total > 0 else 0,
        }
