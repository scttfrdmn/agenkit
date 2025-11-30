"""
Pattern Library with Anthropic/Claude Integration.

Demonstrates using pattern classes with Anthropic Claude models.

This example shows:
- Patterns with Claude models
- Sequential processing with Claude
- Parallel execution with different Claude variants
- Supervisor pattern with Claude
- Production-ready patterns

Requirements:
- pip install anthropic
- ANTHROPIC_API_KEY environment variable
"""

import asyncio
import os

from agenkit.adapters.llm import AnthropicLLM
from agenkit.core import Agent, Message
from agenkit.patterns import (
    ParallelAgent,
    SequentialAgent,
    SimplePlanner,
    Subtask,
    SupervisorAgent,
    default_aggregators,
)


class ClaudeAgent(Agent):
    """Base agent using Anthropic Claude."""

    def __init__(self, name: str, system_prompt: str, model: str = "claude-3-haiku-20240307"):
        self._name = name
        self._system_prompt = system_prompt
        self._llm = None
        self._model = model

    def name(self) -> str:
        return self._name

    def capabilities(self) -> list[str]:
        return ["llm", "claude", "text-generation"]

    def _get_llm(self) -> AnthropicLLM:
        """Lazy initialize LLM."""
        if self._llm is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            self._llm = AnthropicLLM(api_key=api_key, model=self._model)
        return self._llm

    async def process(self, message: Message) -> Message:
        """Process message using Claude."""
        llm = self._get_llm()

        messages = [
            Message(role="system", content=self._system_prompt),
            message,
        ]

        response = await llm.complete(messages, max_tokens=200, temperature=0.7)
        return response


async def sequential_with_claude():
    """Demonstrate sequential pattern with Claude."""
    print("=" * 60)
    print("Example 1: Sequential Pattern with Claude")
    print("=" * 60)

    # Create a research pipeline
    pipeline = SequentialAgent([
        ClaudeAgent(
            name="Researcher",
            system_prompt="You are a research assistant. Identify 3 key research "
            "questions for the given topic. Be concise.",
        ),
        ClaudeAgent(
            name="Analyst",
            system_prompt="You are an analyst. For the given research questions, "
            "suggest methodologies. Keep it brief (3-4 sentences).",
        ),
        ClaudeAgent(
            name="Synthesizer",
            system_prompt="You are a synthesis expert. Create a concise research "
            "plan from the questions and methodologies. 2-3 sentences.",
        ),
    ])

    message = Message(
        role="user",
        content="AI safety in production systems",
    )

    print(f"\n📥 Research Topic: {message.content}\n")
    print("Processing through pipeline (Research -> Analyze -> Synthesize)...\n")

    try:
        result = await pipeline.process(message)

        print("📤 Research Plan:")
        print(result.content)
        print(f"\n✓ Completed {result.metadata.get('pipeline_length', 0)} stages")

    except ValueError as e:
        print(f"⚠️  {e}")
        print("Please set ANTHROPIC_API_KEY environment variable to run this example.")


async def parallel_with_claude():
    """Demonstrate parallel pattern with multiple Claude perspectives."""
    print("\n\n" + "=" * 60)
    print("Example 2: Parallel Pattern with Multiple Claude Agents")
    print("=" * 60)

    # Create multiple reviewers with different perspectives
    reviewer = ParallelAgent(
        agents=[
            ClaudeAgent(
                name="SecurityReviewer",
                system_prompt="You are a security expert. Review for security concerns. "
                "Give a 2-sentence assessment focusing on risks.",
            ),
            ClaudeAgent(
                name="PerformanceReviewer",
                system_prompt="You are a performance expert. Review for performance "
                "implications. Give a 2-sentence assessment.",
            ),
            ClaudeAgent(
                name="MaintainabilityReviewer",
                system_prompt="You are a maintainability expert. Review for code "
                "maintainability. Give a 2-sentence assessment.",
            ),
        ],
        aggregator=default_aggregators["concatenate"],
    )

    message = Message(
        role="user",
        content="Design decision: Using a global state manager for agent coordination",
    )

    print(f"\n📥 Design Decision: {message.content}\n")
    print("Running parallel review from 3 experts...\n")

    try:
        import time
        start = time.time()
        result = await reviewer.process(message)
        elapsed = time.time() - start

        print("📤 Combined Review:")
        print(result.content)
        print(f"\n⏱️  Completed in {elapsed:.2f}s (parallel execution)")
        print(f"   Reviewers: {result.metadata.get('successful_agents', 0)}")

    except ValueError as e:
        print(f"⚠️  {e}")
        print("Please set ANTHROPIC_API_KEY environment variable to run this example.")


async def supervisor_with_claude():
    """Demonstrate supervisor pattern with Claude workers."""
    print("\n\n" + "=" * 60)
    print("Example 3: Supervisor Pattern with Claude")
    print("=" * 60)

    # Create specialized workers
    class ResearchWorker(ClaudeAgent):
        def __init__(self):
            super().__init__(
                name="ResearchWorker",
                system_prompt="You are a researcher. Gather key information. "
                "Provide 2-3 key points.",
            )

        def capabilities(self) -> list[str]:
            return ["research"]

    class AnalysisWorker(ClaudeAgent):
        def __init__(self):
            super().__init__(
                name="AnalysisWorker",
                system_prompt="You are an analyst. Analyze information and identify "
                "patterns. Provide 2-3 insights.",
            )

        def capabilities(self) -> list[str]:
            return ["analysis"]

    class WritingWorker(ClaudeAgent):
        def __init__(self):
            super().__init__(
                name="WritingWorker",
                system_prompt="You are a writer. Create a clear, concise summary. "
                "2-3 sentences maximum.",
            )

        def capabilities(self) -> list[str]:
            return ["writing"]

    # Create planner
    class ReportPlanner(SimplePlanner):
        def plan(self, message: Message) -> list[Subtask]:
            return [
                Subtask("Research the topic", "research"),
                Subtask("Analyze findings", "analysis"),
                Subtask("Write summary", "writing"),
            ]

    # Create supervisor
    supervisor = SupervisorAgent(
        planner=ReportPlanner(),
        workers=[
            ResearchWorker(),
            AnalysisWorker(),
            WritingWorker(),
        ],
    )

    message = Message(
        role="user",
        content="Create a report on agent pattern best practices",
    )

    print(f"\n📥 Task: {message.content}\n")
    print("Supervisor coordinating workers...\n")

    try:
        result = await supervisor.process(message)

        print("📤 Final Report:")
        print(result.content)
        print(f"\n✓ Subtasks completed: {result.metadata.get('subtasks_completed', 0)}")

    except ValueError as e:
        print(f"⚠️  {e}")
        print("Please set ANTHROPIC_API_KEY environment variable to run this example.")


async def multi_model_ensemble():
    """Demonstrate ensemble with different Claude models."""
    print("\n\n" + "=" * 60)
    print("Example 4: Multi-Model Ensemble")
    print("=" * 60)

    # Use different Claude models for ensemble
    ensemble = ParallelAgent(
        agents=[
            ClaudeAgent(
                name="Haiku_Fast",
                system_prompt="Provide a quick, concise answer (1-2 sentences).",
                model="claude-3-haiku-20240307",
            ),
            ClaudeAgent(
                name="Sonnet_Balanced",
                system_prompt="Provide a balanced, detailed answer (2-3 sentences).",
                model="claude-3-5-sonnet-20241022",
            ),
        ],
        aggregator=default_aggregators["concatenate"],
    )

    message = Message(
        role="user",
        content="What are the key benefits of using agent patterns?",
    )

    print(f"\n📥 Question: {message.content}\n")
    print("Running ensemble with Haiku (fast) and Sonnet (detailed)...\n")

    try:
        result = await ensemble.process(message)

        print("📤 Ensemble Responses:")
        print(result.content)

    except ValueError as e:
        print(f"⚠️  {e}")
        print("Please set ANTHROPIC_API_KEY environment variable to run this example.")


async def main():
    """Run all examples."""
    print("\n🤖 Pattern Library with Anthropic/Claude Integration\n")

    await sequential_with_claude()
    await parallel_with_claude()
    await supervisor_with_claude()
    await multi_model_ensemble()

    print("\n✅ All examples complete!")
    print("\nNote: Examples use claude-3-haiku for cost-effectiveness.")
    print("For production, consider claude-3-5-sonnet or claude-opus.")


if __name__ == "__main__":
    asyncio.run(main())
