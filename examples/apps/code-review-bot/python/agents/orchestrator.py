"""Orchestrator for multi-LLM code review with consensus."""

import asyncio
import logging

from agenkit.adapters.llm import LiteLLMLLM
from agenkit.interfaces import Agent, Message

logger = logging.getLogger(__name__)


class ReviewOrchestrator(Agent):
    """Orchestrates parallel reviews from multiple LLMs."""

    def __init__(self, anthropic_key: str, openai_key: str, google_key: str):
        self._name = "orchestrator"

        # Initialize LiteLLM for each provider
        self._reviewers = {
            "claude": LiteLLMLLM(model="claude-3-5-sonnet-20241022", api_key=anthropic_key),
            "gpt4": LiteLLMLLM(model="gpt-4-turbo", api_key=openai_key),
            "gemini": LiteLLMLLM(model="gemini-pro", api_key=google_key),
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["code_review", "consensus", "multi_llm"]

    async def process(self, message: Message) -> Message:
        """Conduct parallel code reviews and calculate consensus."""
        code = str(message.content)
        review_type = message.metadata.get("review_type", "general")

        # Create review prompts for each LLM
        prompts = {
            "claude": self._create_security_prompt(code),
            "gpt4": self._create_architecture_prompt(code),
            "gemini": self._create_style_prompt(code),
        }

        # Run reviews in parallel
        logger.info("Starting parallel reviews from 3 LLMs")
        review_tasks = [
            self._review_with_llm(name, llm, prompt)
            for (name, llm), prompt in zip(self._reviewers.items(), prompts.values(), strict=False)
        ]

        reviews = await asyncio.gather(*review_tasks, return_exceptions=True)

        # Calculate consensus
        successful_reviews = [r for r in reviews if not isinstance(r, Exception)]
        consensus = self._calculate_consensus(successful_reviews)

        return Message(
            role="assistant",
            content=self._synthesize_reviews(successful_reviews, consensus),
            metadata={
                "num_reviews": len(successful_reviews),
                "consensus_score": consensus,
                "review_type": review_type,
            },
        )

    async def _review_with_llm(self, name: str, llm: LiteLLMLLM, prompt: str) -> dict:
        """Conduct review with single LLM."""
        try:
            response = await llm.complete(
                [Message(role="user", content=prompt)], max_tokens=1000, temperature=0.3
            )
            return {"reviewer": name, "content": str(response.content), "success": True}
        except Exception as e:
            logger.error(f"Review failed for {name}: {e}")
            return {"reviewer": name, "error": str(e), "success": False}

    def _create_security_prompt(self, code: str) -> str:
        return f"""Review this code for security vulnerabilities:

{code}

Focus on: SQL injection, XSS, auth issues, secrets, input validation.
Provide specific issues found and severity (critical/high/medium/low)."""

    def _create_architecture_prompt(self, code: str) -> str:
        return f"""Review this code for architectural issues:

{code}

Focus on: design patterns, coupling, complexity, maintainability, scalability.
Provide specific recommendations."""

    def _create_style_prompt(self, code: str) -> str:
        return f"""Review this code for style and best practices:

{code}

Focus on: naming, formatting, documentation, idioms, error handling.
Provide specific suggestions."""

    def _calculate_consensus(self, reviews: list[dict]) -> float:
        """Calculate consensus score from reviews."""
        if not reviews:
            return 0.0

        # Simple consensus: proportion of successful reviews
        successful = sum(1 for r in reviews if r.get("success", False))
        return successful / len(reviews)

    def _synthesize_reviews(self, reviews: list[dict], consensus: float) -> str:
        """Synthesize multiple reviews into single report."""
        report = f"# Code Review Report\n\n**Consensus Score**: {consensus:.2f}\n\n"

        for review in reviews:
            if review.get("success"):
                report += f"## {review['reviewer'].upper()} Review\n\n{review['content']}\n\n"

        if consensus < 0.7:
            report += "\n⚠️  **Low consensus** - Manual review recommended.\n"

        return report
