"""Router agent that classifies queries and routes to appropriate handlers."""

import logging
from typing import Literal

from agenkit.adapters.llm import AnthropicLLM
from agenkit.interfaces import Agent, Message

logger = logging.getLogger(__name__)

QueryType = Literal["faq", "specialist", "escalation"]


class RouterAgent(Agent):
    """
    Router agent that classifies customer queries using Claude.

    Routes queries to:
    - FAQ agent: Simple,

 common questions
    - Specialist agent: Complex queries requiring RAG or analysis
    - Escalation: Issues requiring human intervention
    """

    def __init__(self, anthropic_api_key: str):
        """
        Initialize router agent.

        Args:
            anthropic_api_key: Anthropic API key for Claude
        """
        self._llm = AnthropicLLM(api_key=anthropic_api_key, model="claude-3-haiku-20240307")
        self._name = "router"

    @property
    def name(self) -> str:
        """Return agent name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return ["routing", "classification"]

    async def process(self, message: Message) -> Message:
        """
        Classify query and determine routing.

        Args:
            message: User query

        Returns:
            Message with routing decision in metadata
        """
        query = str(message.content)

        # Use Claude to classify the query
        classification_prompt = f"""Classify this customer support query into one of these categories:
- "faq": Simple, common question (password reset, account settings, basic features)
- "specialist": Complex technical question requiring detailed analysis
- "escalation": Urgent issue, refund request, or complaint requiring human intervention

Query: {query}

Respond with ONLY the category name (faq, specialist, or escalation) and a confidence score 0-1.
Format: category|confidence
Example: faq|0.95"""

        try:
            classification_msg = await self._llm.complete(
                [Message(role="user", content=classification_prompt)], max_tokens=50, temperature=0.3
            )

            # Parse response
            response_text = str(classification_msg.content).strip().lower()
            parts = response_text.split("|")

            if len(parts) >= 2:
                category = parts[0].strip()
                confidence = float(parts[1].strip())
            else:
                # Fallback: simple keyword matching
                logger.warning(f"Failed to parse LLM response: {response_text}, using fallback")
                category, confidence = self._fallback_classification(query)

            # Validate category
            if category not in ["faq", "specialist", "escalation"]:
                logger.warning(f"Invalid category {category}, defaulting to specialist")
                category = "specialist"
                confidence = 0.5

        except Exception as e:
            logger.error(f"Error classifying query: {e}, using fallback")
            category, confidence = self._fallback_classification(query)

        logger.info(f"Classified query as '{category}' with confidence {confidence:.2f}")

        # Return routing decision
        return Message(
            role="assistant",
            content=f"Routing to {category}",
            metadata={
                "route": category,
                "confidence": confidence,
                "original_query": query,
            },
        )

    def _fallback_classification(self, query: str) -> tuple[QueryType, float]:
        """
        Fallback keyword-based classification.

        Args:
            query: User query

        Returns:
            Tuple of (category, confidence)
        """
        query_lower = query.lower()

        # Escalation keywords
        if any(
            word in query_lower
            for word in ["refund", "cancel", "complaint", "urgent", "angry", "terrible", "worst"]
        ):
            return ("escalation", 0.8)

        # FAQ keywords
        if any(word in query_lower for word in ["password", "reset", "how do i", "how to", "login", "sign in"]):
            return ("faq", 0.7)

        # Default to specialist for complex queries
        return ("specialist", 0.6)
