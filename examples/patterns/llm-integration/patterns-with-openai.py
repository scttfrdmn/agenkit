"""
Pattern Library with OpenAI Integration.

Demonstrates using pattern classes with real OpenAI LLM agents instead
of mock agents.

This example shows:
- Patterns with real LLM agents
- Sequential processing with GPT
- Parallel execution with multiple models
- Router with LLM-based classification
- Practical production patterns

Requirements:
- pip install openai
- OPENAI_API_KEY environment variable
"""

import asyncio
import os

from agenkit.adapters.llm import OpenAILLM
from agenkit.core import Agent, Message
from agenkit.patterns import (
    ParallelAgent,
    RouterAgent,
    SequentialAgent,
    SimpleClassifier,
    default_aggregators,
)


class LLMAgent(Agent):
    """Base agent using OpenAI LLM."""

    def __init__(self, name: str, system_prompt: str, model: str = "gpt-4o-mini"):
        self._name = name
        self._system_prompt = system_prompt
        self._llm = None
        self._model = model

    def name(self) -> str:
        return self._name

    def capabilities(self) -> list[str]:
        return ["llm", "text-generation"]

    def _get_llm(self) -> OpenAILLM:
        """Lazy initialize LLM."""
        if self._llm is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self._llm = OpenAILLM(api_key=api_key, model=self._model)
        return self._llm

    async def process(self, message: Message) -> Message:
        """Process message using LLM."""
        llm = self._get_llm()

        messages = [
            Message(role="system", content=self._system_prompt),
            message,
        ]

        response = await llm.complete(messages, max_tokens=200, temperature=0.7)
        return response


async def sequential_with_llm():
    """Demonstrate sequential pattern with LLM agents."""
    print("=" * 60)
    print("Example 1: Sequential Pattern with OpenAI")
    print("=" * 60)

    # Create a content pipeline: Draft -> Review -> Polish
    pipeline = SequentialAgent([
        LLMAgent(
            name="Drafter",
            system_prompt="You are a content drafter. Create a brief outline or draft "
            "for the given topic. Keep it concise (2-3 sentences).",
        ),
        LLMAgent(
            name="Reviewer",
            system_prompt="You are a content reviewer. Review the draft and suggest "
            "2-3 specific improvements. Be constructive and brief.",
        ),
        LLMAgent(
            name="Polisher",
            system_prompt="You are a content polisher. Take the draft and review, "
            "then create a final polished version. Keep it concise.",
        ),
    ])

    message = Message(
        role="user",
        content="Write about the benefits of modular agent design",
    )

    print(f"\n📥 Topic: {message.content}\n")
    print("Processing through pipeline (Draft -> Review -> Polish)...\n")

    try:
        result = await pipeline.process(message)

        print("📤 Final Result:")
        print(result.content)
        print(f"\n✓ Completed {result.metadata.get('pipeline_length', 0)} stages")

    except ValueError as e:
        print(f"⚠️  {e}")
        print("Please set OPENAI_API_KEY environment variable to run this example.")


async def parallel_with_llm():
    """Demonstrate parallel pattern with multiple LLM perspectives."""
    print("\n\n" + "=" * 60)
    print("Example 2: Parallel Pattern with Multiple Perspectives")
    print("=" * 60)

    # Create multiple analyzers with different perspectives
    analyzer = ParallelAgent(
        agents=[
            LLMAgent(
                name="TechnicalAnalyst",
                system_prompt="You are a technical analyst. Analyze the technical "
                "aspects and feasibility. Give a 2-sentence assessment.",
            ),
            LLMAgent(
                name="BusinessAnalyst",
                system_prompt="You are a business analyst. Analyze the business value "
                "and ROI. Give a 2-sentence assessment.",
            ),
            LLMAgent(
                name="UserExperienceAnalyst",
                system_prompt="You are a UX analyst. Analyze the user experience "
                "implications. Give a 2-sentence assessment.",
            ),
        ],
        aggregator=default_aggregators["concatenate"],
    )

    message = Message(
        role="user",
        content="Evaluate: Building a multi-agent system with automatic failover",
    )

    print(f"\n📥 Topic: {message.content}\n")
    print("Running parallel analysis from 3 perspectives...\n")

    try:
        import time
        start = time.time()
        result = await analyzer.process(message)
        elapsed = time.time() - start

        print("📤 Combined Analysis:")
        print(result.content)
        print(f"\n⏱️  Completed in {elapsed:.2f}s (parallel execution)")
        print(f"   Perspectives: {result.metadata.get('successful_agents', 0)}")

    except ValueError as e:
        print(f"⚠️  {e}")
        print("Please set OPENAI_API_KEY environment variable to run this example.")


async def router_with_llm():
    """Demonstrate router pattern with LLM-based classification."""
    print("\n\n" + "=" * 60)
    print("Example 3: Router Pattern with LLM Agents")
    print("=" * 60)

    # Create specialized agents
    technical_agent = LLMAgent(
        name="TechnicalExpert",
        system_prompt="You are a technical expert. Provide detailed technical guidance. "
        "Keep response under 3 sentences.",
    )

    creative_agent = LLMAgent(
        name="CreativeExpert",
        system_prompt="You are a creative expert. Provide creative and innovative ideas. "
        "Keep response under 3 sentences.",
    )

    general_agent = LLMAgent(
        name="GeneralExpert",
        system_prompt="You are a helpful assistant. Provide clear, general guidance. "
        "Keep response under 3 sentences.",
    )

    # Create classifier
    class IntentClassifier(SimpleClassifier):
        """Classify queries by intent."""

        def classify(self, message: Message) -> str:
            content = message.content.lower()

            if any(word in content for word in
                   ["code", "implement", "technical", "api", "debug", "algorithm"]):
                return "technical"
            elif any(word in content for word in
                     ["design", "creative", "brainstorm", "idea", "innovative"]):
                return "creative"
            else:
                return "general"

    # Create router
    router = RouterAgent(
        classifier=IntentClassifier(),
        routes={
            "technical": technical_agent,
            "creative": creative_agent,
            "general": general_agent,
        },
    )

    # Test different query types
    queries = [
        "How do I implement error handling in async Python?",
        "What are some creative ways to visualize agent workflows?",
        "What is Agenkit?",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n📥 Query {i}: {query}")

        message = Message(role="user", content=query)

        try:
            result = await router.process(message)

            print("\n📤 Response:")
            print(result.content)
            print(f"   (routed to {result.metadata.get('route', 'unknown')})")

        except ValueError as e:
            if i == 1:  # Only show error once
                print(f"⚠️  {e}")
                print("Please set OPENAI_API_KEY to run this example.")
            break


async def composed_patterns():
    """Demonstrate composed patterns with LLM."""
    print("\n\n" + "=" * 60)
    print("Example 4: Composed Patterns (Sequential + Parallel)")
    print("=" * 60)

    # Stage 1: Parallel brainstorming
    brainstorm_stage = ParallelAgent(
        agents=[
            LLMAgent(
                name="IdeaGenerator1",
                system_prompt="Generate 2 creative ideas for the given topic. "
                "Be brief and innovative.",
            ),
            LLMAgent(
                name="IdeaGenerator2",
                system_prompt="Generate 2 practical ideas for the given topic. "
                "Focus on feasibility.",
            ),
        ],
        aggregator=default_aggregators["concatenate"],
    )

    # Stage 2: Synthesizer
    synthesizer = LLMAgent(
        name="Synthesizer",
        system_prompt="You are a synthesis expert. Take multiple ideas and create "
        "a coherent synthesis. Keep it under 4 sentences.",
    )

    # Compose
    pipeline = SequentialAgent([
        brainstorm_stage,
        synthesizer,
    ])

    message = Message(
        role="user",
        content="How can we improve agent observability?",
    )

    print(f"\n📥 Question: {message.content}\n")
    print("Processing: Brainstorm (parallel) -> Synthesize...\n")

    try:
        result = await pipeline.process(message)

        print("📤 Synthesized Result:")
        print(result.content)

    except ValueError as e:
        print(f"⚠️  {e}")
        print("Please set OPENAI_API_KEY environment variable to run this example.")


async def main():
    """Run all examples."""
    print("\n🤖 Pattern Library with OpenAI Integration\n")

    await sequential_with_llm()
    await parallel_with_llm()
    await router_with_llm()
    await composed_patterns()

    print("\n✅ All examples complete!")
    print("\nNote: These examples use gpt-4o-mini for cost-effectiveness.")
    print("For production, consider using gpt-4o or fine-tuned models.")


if __name__ == "__main__":
    asyncio.run(main())
