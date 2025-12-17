"""Writer agent that synthesizes research into reports."""

import logging
from agenkit.adapters.llm import OpenAILLM
from agenkit.interfaces import Agent, Message

logger = logging.getLogger(__name__)


class WriterAgent(Agent):
    """Synthesizes research findings into comprehensive reports."""

    def __init__(self, openai_api_key: str):
        self._llm = OpenAILLM(api_key=openai_api_key, model="gpt-4-turbo")
        self._name = "writer"

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["writing", "synthesis", "reporting"]

    async def process(self, message: Message) -> Message:
        """Synthesize findings into report."""
        findings = message.metadata.get("findings", [])
        query = message.metadata.get("query", "")

        prompt = f"""Synthesize these research findings into a comprehensive report on: "{query}"

Findings:
{self._format_findings(findings)}

Create a well-structured report with:
1. Executive Summary
2. Key Findings
3. Detailed Analysis
4. Conclusions
5. Sources

Use markdown formatting."""

        try:
            response = await self._llm.complete(
                [Message(role="user", content=prompt)],
                max_tokens=2000,
                temperature=0.7
            )

            return Message(
                role="assistant",
                content=str(response.content),
                metadata={"type": "research_report", "query": query, "num_findings": len(findings)}
            )
        except Exception as e:
            logger.error(f"Writing error: {e}")
            return Message(
                role="assistant",
                content=f"# Research Report: {query}\n\nError synthesizing findings: {str(e)}",
                metadata={"type": "error"}
            )

    def _format_findings(self, findings: list) -> str:
        """Format findings for prompt."""
        return "\n\n".join([f"- {f}" for f in findings])
