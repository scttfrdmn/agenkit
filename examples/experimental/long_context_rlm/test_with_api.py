"""
Test RLM with real LLM API (Anthropic Claude or OpenAI).

This script demonstrates the RLM pattern working with real APIs:
- Uses Claude Haiku (cheapest, fast) for cost-effective testing
- Moderate context size (~50K chars) to stay within budget
- Budget protection set to $1.00 to prevent runaway costs
- Shows recursive sub-calls happening
- Tracks actual API costs

Usage:
    export ANTHROPIC_API_KEY="your-key-here"
    uv run python examples/experimental/long_context_rlm/test_with_api.py

Expected cost: $0.05-0.20 (depending on model and trajectory)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from basic_rlm import RecursiveREPLAgent

from agenkit.adapters.llm.anthropic import AnthropicLLM
from agenkit.budget import CostTracker
from agenkit.interfaces import Agent, Message


class LLMAgent(Agent):
    """Simple agent wrapper around LLM adapter."""

    def __init__(self, llm: AnthropicLLM):
        self.llm = llm
        self._name = f"agent-{llm.model}"

    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        """Process message using LLM."""
        response = await self.llm.complete(
            messages=[message],
            temperature=0.7,
            max_tokens=2048,
        )
        return response


def generate_test_context() -> str:
    """
    Generate a test context that's large enough to be interesting
    but small enough to be cost-effective.

    ~50K characters, simulates a collection of documents that
    need multi-hop reasoning.
    """
    # Simulate a dataset with mixed information that requires reasoning
    documents = []

    # Dataset 1: Company information (scattered across docs)
    companies = [
        ("Acme Corp", "2015", "Alice Johnson", "Boston", "Widget X", "2018", "300%"),
        ("Beta Inc", "2010", "Bob Smith", "Seattle", "Gadget Y", "2020", "150%"),
        ("Gamma LLC", "2018", "Carol Davis", "Austin", "Tool Z", "2021", "200%"),
        ("Delta Co", "2012", "David Lee", "Portland", "Device A", "2019", "400%"),
        ("Epsilon Ltd", "2016", "Eve Martinez", "Denver", "Product B", "2022", "250%"),
    ]

    for i, (name, founded, ceo, city, product, launch, growth) in enumerate(companies):
        documents.extend(
            [
                f"Document {i * 5 + 1}: {name} was founded in {founded}.",
                f"Document {i * 5 + 2}: The CEO of {name} is {ceo}.",
                f"Document {i * 5 + 3}: {name} is headquartered in {city}.",
                f"Document {i * 5 + 4}: {name}'s flagship product {product} launched in {launch}.",
                f"Document {i * 5 + 5}: {name} reported {growth} revenue growth in 2023.",
            ]
        )

    # Dataset 2: Research papers (need to find connections)
    papers = [
        ("Neural Scaling Laws", "Kaplan et al.", "2020", "compute, parameters, data scaling"),
        (
            "Attention Is All You Need",
            "Vaswani et al.",
            "2017",
            "transformers, attention mechanism",
        ),
        (
            "GPT-3: Language Models are Few-Shot Learners",
            "Brown et al.",
            "2020",
            "in-context learning, scaling",
        ),
        (
            "BERT: Bidirectional Encoder Representations",
            "Devlin et al.",
            "2019",
            "pre-training, bidirectional",
        ),
        ("Chain-of-Thought Prompting", "Wei et al.", "2022", "reasoning, multi-step problems"),
    ]

    for i, (title, authors, year, keywords) in enumerate(papers):
        documents.append(
            f"Paper {i + 1}: '{title}' by {authors} ({year}) - Key concepts: {keywords}."
        )

    # Dataset 3: Events timeline (need to order and reason about)
    events = [
        "2017: First transformer paper published",
        "2018: BERT introduces bidirectional pre-training",
        "2019: GPT-2 demonstrates language generation capabilities",
        "2020: GPT-3 shows in-context learning at scale",
        "2021: Codex applies transformers to code generation",
        "2022: ChatGPT launches, bringing LLMs to mainstream",
        "2023: GPT-4 achieves human-level performance on many tasks",
    ]

    for event in events:
        documents.append(f"Timeline: {event}")

    # Repeat documents to increase context size (simulate redundancy in real data)
    context = "\n".join(documents * 20)  # ~50K characters

    return context


async def main():
    """Run RLM test with real API."""
    print("=" * 70)
    print("RLM API Test with Anthropic Claude")
    print("=" * 70)

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("\nTo run this test:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print("  uv run python examples/experimental/long_context_rlm/test_with_api.py")
        return

    # Generate test context
    print("\n📄 Generating test context...")
    context = generate_test_context()
    print(f"   Context size: {len(context):,} characters")

    # Define test query requiring multi-hop reasoning
    query = """
    Based on the documents, answer these questions:
    1. Which company was founded in 2015, and who is their CEO?
    2. What year did transformers first appear in research papers?
    3. What was the revenue growth percentage for the company founded in 2015?

    Be concise and cite specific documents when possible.
    """

    print(f"\n❓ Query: {query.strip()[:100]}...")

    # Create cost tracker
    tracker = CostTracker()

    # Initialize LLM agents
    print("\n🤖 Initializing agents...")
    print("   Root agent: claude-haiku-3 (orchestration)")
    print("   Sub agent: claude-haiku-3 (sub-queries)")

    root_llm = AnthropicLLM(api_key=api_key, model="claude-3-haiku-20240307")
    sub_llm = AnthropicLLM(api_key=api_key, model="claude-3-haiku-20240307")

    root_agent = LLMAgent(root_llm)
    sub_agent = LLMAgent(sub_llm)

    # Create RLM with budget protection
    print("\n💰 Budget protection: $1.00 limit")
    rlm = RecursiveREPLAgent(
        agent=root_agent,
        sub_agent=sub_agent,
        max_iterations=10,
        session_budget=1.00,  # $1 budget limit
        cost_tracker=tracker,
    )

    # Run RLM
    print("\n🔄 Processing with RLM pattern...")
    print("-" * 70)

    try:
        message = Message(role="user", content=f"{context}\n\nQuery: {query}")
        result = await rlm.process(message)

        print("\n✅ RLM completed successfully!")
        print("\n" + "=" * 70)
        print("FINAL ANSWER")
        print("=" * 70)
        print(result.content)
        print("=" * 70)

        # Show cost breakdown
        total_cost = sum(cost.total_cost for cost in tracker.storage.costs)
        print(f"\n💵 Cost Summary:")
        print(f"   Total API calls: {len(tracker.storage.costs)}")
        print(f"   Total cost: ${total_cost:.4f}")
        print(f"   Budget remaining: ${1.00 - total_cost:.4f}")

        # Show per-call breakdown
        if tracker.storage.costs:
            print(f"\n📊 Per-call breakdown:")
            for i, cost in enumerate(tracker.storage.costs, 1):
                print(
                    f"   Call {i}: {cost.input_tokens:,} in + {cost.output_tokens:,} out = ${cost.total_cost:.4f}"
                )

    except Exception as e:
        if "budget" in str(e).lower():
            print(f"\n⚠️  Budget exceeded: {e}")
            print("   RLM stopped to prevent runaway costs")

            # Show partial results
            total_cost = sum(cost.total_cost for cost in tracker.storage.costs)
            print(f"\n💵 Cost at stop:")
            print(f"   Total API calls: {len(tracker.storage.costs)}")
            print(f"   Total cost: ${total_cost:.4f}")
        else:
            print(f"\n❌ Error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
