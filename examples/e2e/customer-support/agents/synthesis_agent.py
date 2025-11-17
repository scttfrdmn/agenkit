"""Synthesis Agent - Creates final customer-facing response."""

from typing import Dict, Any
from agenkit import Agent, Message


class SynthesisAgent(Agent):
    """
    Synthesizes final response from classification, QA, and escalation results.

    Combines outputs from other agents into a coherent customer response.
    """

    @property
    def name(self) -> str:
        return "SynthesisAgent"

    async def process(self, message: Message) -> Message:
        """
        Create final response from agent outputs.

        Expects message.metadata to contain results from other agents:
        - classification: dict
        - qa_response: str
        - escalation: dict
        """
        metadata = message.metadata or {}
        classification = metadata.get("classification", {})
        qa_response = metadata.get("qa_response", "")
        escalation = metadata.get("escalation", {})

        # Build final response
        response_parts = []

        # Add response or escalation message
        if escalation.get("should_escalate"):
            response_parts.append(
                f"I understand your {classification.get('category', 'inquiry')}. {escalation.get('reason', 'This requires human attention')}."
            )
            response_parts.append(
                "\nI'm connecting you with a specialist who can help. Expected wait time: 2-3 minutes."
            )
        else:
            response_parts.append(qa_response)
            response_parts.append("\n\nIs there anything else I can help you with?")

        final_response = "".join(response_parts)

        return Message(
            role="assistant",
            content=final_response,
            metadata={
                "final_response": True,
                "escalated": escalation.get("should_escalate", False),
                "category": classification.get("category"),
                "confidence": metadata.get("confidence", 0.5),
            },
        )
