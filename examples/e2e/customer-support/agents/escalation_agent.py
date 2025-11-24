"""Escalation Agent - Determines when to escalate to human agents."""

from agenkit import Agent, Message


class EscalationAgent(Agent):
    """
    Decides whether a ticket should be escalated to a human agent.

    Escalation criteria:
    - Low confidence answers
    - Critical priority issues
    - Complex or sensitive topics
    - Customer explicitly requests human
    """

    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold

    @property
    def name(self) -> str:
        return "EscalationAgent"

    async def process(self, message: Message) -> Message:
        """
        Determine if ticket should be escalated.

        Expects message.metadata to contain:
        - confidence: float (0-1)
        - priority: str
        - category: str
        """
        metadata = message.metadata or {}
        confidence = metadata.get("confidence", 0.5)
        priority = metadata.get("priority", "medium")
        content = message.content.lower()

        should_escalate, reason = self._should_escalate(confidence, priority, content)

        return Message(
            role="assistant",
            content=f"Escalation {'required' if should_escalate else 'not needed'}: {reason}",
            metadata={
                "should_escalate": should_escalate,
                "reason": reason,
                "escalation_priority": priority if should_escalate else None,
            },
        )

    def _should_escalate(self, confidence: float, priority: str, content: str) -> tuple[bool, str]:
        """Determine escalation with reasoning."""
        # Critical issues always escalate
        if priority == "critical":
            return True, "Critical priority issue requires immediate human attention"

        # Low confidence answers
        if confidence < self.confidence_threshold:
            return True, f"Low confidence ({confidence:.2f}) in automated response"

        # Explicit requests for human
        if any(phrase in content for phrase in ["speak to human", "talk to person", "real person"]):
            return True, "Customer explicitly requested human agent"

        # Sensitive topics
        if any(word in content for word in ["refund", "cancel", "complaint", "legal"]):
            return True, "Sensitive topic requires human judgment"

        return False, "Issue can be handled by automated system"
