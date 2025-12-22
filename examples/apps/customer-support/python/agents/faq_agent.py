"""FAQ agent that handles common questions with caching."""

import logging

from agenkit.adapters.llm import AnthropicLLM
from agenkit.interfaces import Agent, Message

logger = logging.getLogger(__name__)

# Sample FAQ knowledge base
FAQ_DATABASE = {
    "password reset": "To reset your password, go to Settings > Security > Change Password. You'll need to verify your email address.",
    "login issues": "If you're having trouble logging in, try: 1) Clear your browser cache, 2) Reset your password, 3) Check if Caps Lock is on.",
    "account settings": "Access your account settings by clicking your profile icon in the top right, then selecting 'Settings'.",
    "premium plan": "Our Premium plan includes: unlimited storage, priority support, advanced analytics, and team collaboration features for $29/month.",
    "cancel subscription": "To cancel your subscription, go to Settings > Billing > Cancel Plan. You'll retain access until the end of your billing period.",
    "export data": "You can export your data by going to Settings > Data & Privacy > Export Data. We'll email you a download link within 24 hours.",
    "two-factor auth": "Enable two-factor authentication in Settings > Security > Two-Factor Authentication. We support SMS, authenticator apps, and hardware keys.",
    "file sharing": "Share files by clicking the Share button, entering email addresses, and setting permissions (view, edit, or admin).",
    "mobile app": "Our mobile app is available for iOS and Android. Download from the App Store or Google Play Store.",
    "api access": "API documentation is available at docs.example.com/api. Generate an API key in Settings > Developer > API Keys.",
}


class FAQAgent(Agent):
    """
    FAQ agent that answers common questions.

    Uses a knowledge base for instant responses and Claude for
    questions not in the database.
    """

    def __init__(self, anthropic_api_key: str):
        """
        Initialize FAQ agent.

        Args:
            anthropic_api_key: Anthropic API key for Claude
        """
        self._llm = AnthropicLLM(api_key=anthropic_api_key, model="claude-3-haiku-20240307")
        self._name = "faq"

    @property
    def name(self) -> str:
        """Return agent name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return ["faq", "knowledge_base"]

    async def process(self, message: Message) -> Message:
        """
        Answer FAQ question.

        Args:
            message: User question

        Returns:
            Message with answer and metadata
        """
        query = str(message.content).lower()

        # Try to find answer in FAQ database
        answer = self._search_faq_database(query)

        if answer:
            logger.info("Found FAQ answer in database")
            return Message(
                role="assistant",
                content=answer,
                metadata={
                    "source": "faq_database",
                    "confidence": 0.95,
                    "cached": True,
                },
            )

        # If not in database, use Claude to generate answer
        logger.info("FAQ not in database, using Claude")

        try:
            faq_prompt = f"""You are a helpful customer support agent. Answer this question concisely and accurately:

Question: {query}

Provide a clear, friendly answer in 2-3 sentences. If you're not certain, say so."""

            response = await self._llm.complete(
                [Message(role="user", content=faq_prompt)], max_tokens=200, temperature=0.7
            )

            return Message(
                role="assistant",
                content=str(response.content),
                metadata={
                    "source": "llm",
                    "confidence": 0.7,
                    "cached": False,
                },
            )

        except Exception as e:
            logger.error(f"Error generating FAQ answer: {e}")
            return Message(
                role="assistant",
                content="I apologize, but I'm having trouble answering your question right now. Please try again or contact our support team.",
                metadata={
                    "source": "error",
                    "error": str(e),
                    "confidence": 0.0,
                },
            )

    def _search_faq_database(self, query: str) -> str | None:
        """
        Search FAQ database for matching answer.

        Args:
            query: User query (lowercased)

        Returns:
            FAQ answer if found, None otherwise
        """
        # Simple keyword matching
        for topic, answer in FAQ_DATABASE.items():
            if topic in query:
                return answer

        return None
