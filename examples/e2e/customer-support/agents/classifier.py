"""
Classifier Agent - Routes tickets to appropriate categories.

Determines the category and priority of incoming support tickets.
"""

from typing import Dict, Any
from agenkit import Agent, Message


class ClassifierAgent(Agent):
    """
    Classifies customer support tickets into categories.

    Categories:
    - account: Login, password, profile issues
    - billing: Payments, subscriptions, refunds
    - technical: Bugs, performance, errors
    - feature: Feature requests, suggestions
    - general: General inquiries

    Priority levels:
    - critical: Service down, data loss
    - high: Cannot complete key tasks
    - medium: Inconvenient but has workaround
    - low: Questions, minor issues
    """

    CATEGORIES = ["account", "billing", "technical", "feature", "general"]
    PRIORITIES = ["critical", "high", "medium", "low"]

    @property
    def name(self) -> str:
        return "ClassifierAgent"

    async def process(self, message: Message) -> Message:
        """
        Classify a support ticket.

        Args:
            message: User message containing ticket content

        Returns:
            Message with classification results
        """
        content = message.content.lower()

        # Classify category
        category = self._classify_category(content)

        # Determine priority
        priority = self._classify_priority(content)

        # Create structured response
        classification = {
            "category": category,
            "priority": priority,
            "confidence": self._calculate_confidence(content, category),
        }

        return Message(
            role="assistant",
            content=f"Classification: {category} (priority: {priority})",
            metadata=classification,
        )

    def _classify_category(self, content: str) -> str:
        """Classify ticket category based on keywords."""
        # Account-related keywords
        if any(
            word in content
            for word in [
                "password",
                "login",
                "sign in",
                "account",
                "profile",
                "username",
            ]
        ):
            return "account"

        # Billing-related keywords
        if any(
            word in content
            for word in [
                "billing",
                "payment",
                "credit card",
                "subscription",
                "invoice",
                "refund",
                "charge",
            ]
        ):
            return "billing"

        # Technical issue keywords
        if any(
            word in content
            for word in [
                "error",
                "bug",
                "broken",
                "not working",
                "crash",
                "slow",
                "performance",
            ]
        ):
            return "technical"

        # Feature request keywords
        if any(
            word in content
            for word in ["feature", "request", "add", "could you", "would be nice"]
        ):
            return "feature"

        # Default to general
        return "general"

    def _classify_priority(self, content: str) -> str:
        """Determine priority level."""
        # Critical keywords
        if any(
            word in content
            for word in ["down", "broken", "urgent", "asap", "critical", "lost data"]
        ):
            return "critical"

        # High priority keywords
        if any(
            word in content
            for word in ["cannot", "can't", "unable", "need help", "not working"]
        ):
            return "high"

        # Low priority keywords
        if any(
            word in content for word in ["question", "how do i", "curious", "wondering"]
        ):
            return "low"

        # Default to medium
        return "medium"

    def _calculate_confidence(self, content: str, category: str) -> float:
        """
        Calculate confidence score for classification.

        Returns:
            Confidence score between 0 and 1
        """
        # Simple confidence based on keyword matches
        # In production, use ML model confidence scores
        words = content.split()
        if len(words) < 3:
            return 0.6  # Low confidence for very short messages

        return 0.85  # Default confidence
