"""Planner agent that breaks down research questions."""

import logging
from agenkit.adapters.llm import OpenAILLM
from agenkit.interfaces import Agent, Message

logger = logging.getLogger(__name__)


class PlannerAgent(Agent):
    """Breaks research questions into steps."""

    def __init__(self, openai_api_key: str):
        self._llm = OpenAILLM(api_key=openai_api_key, model="gpt-4-turbo")
        self._name = "planner"

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["planning", "research_strategy"]

    async def process(self, message: Message) -> Message:
        """Create research plan."""
        query = str(message.content)

        prompt = f"""Create a research plan for this topic: "{query}"

Break this into 3-5 specific research steps. For each step, provide:
1. Action (search, analyze, compare)
2. Specific question to answer
3. Information sources needed

Format as JSON array:
[{{"step": 1, "action": "search", "question": "...", "sources": ["..."]}}, ...]"""

        try:
            response = await self._llm.complete(
                [Message(role="user", content=prompt)],
                max_tokens=1000,
                temperature=0.7
            )

            return Message(
                role="assistant",
                content=str(response.content),
                metadata={"type": "research_plan", "query": query}
            )
        except Exception as e:
            logger.error(f"Planning error: {e}")
            # Fallback plan
            return Message(
                role="assistant",
                content=f'[{{"step": 1, "action": "search", "question": "{query}", "sources": ["web"]}}]',
                metadata={"type": "research_plan", "fallback": True}
            )
