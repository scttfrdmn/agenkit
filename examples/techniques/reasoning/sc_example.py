"""
Self-Consistency Reasoning Example

Demonstrates how to use Self-Consistency to improve reliability by sampling
multiple times and using consensus voting.

This example shows:
- Basic Self-Consistency with majority voting
- Different voting strategies (majority, weighted, first)
- Custom answer extractors
- Combining with other techniques (CoT + SC)
- Consistency metrics

Requirements:
    pip install agenkit
"""

import asyncio
from agenkit import Message
from agenkit.techniques.reasoning import SelfConsistency, ChainOfThought


# Mock LLM for demonstration
class MockLLM:
    """Simple mock LLM with variability in responses."""

    def __init__(self, variability=True):
        self.variability = variability
        self.call_count = 0

    async def complete(self, prompt: str) -> str:
        """Return mock responses with some variation."""
        self.call_count += 1

        if "capital of France" in prompt:
            # Most agree on Paris
            responses = ["Paris", "Paris", "Paris", "Lyon", "Paris"]
            return f"The answer is {responses[self.call_count % len(responses)]}"

        if "2 + 2" in prompt:
            # Perfect agreement
            return "Therefore, 2 + 2 = 4"

        if "best programming language" in prompt:
            # High variability
            languages = ["Python", "JavaScript", "Rust", "Go", "Python"]
            return f"I think the answer is {languages[self.call_count % len(languages)]}"

        return "Generic answer"


class VariableAgent:
    """Agent with variable responses for demonstration."""

    def __init__(self):
        self.name = "variable_agent"
        self.responses = [
            "Thinking carefully, the result is 42",
            "After analysis, I conclude 42",
            "My answer is 42",
            "The solution is 43",  # Outlier
            "Therefore, 42",
        ]
        self.call_count = 0

    async def process(self, message: Message) -> Message:
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return Message(role="assistant", content=response)


async def basic_example():
    """Basic Self-Consistency with majority voting."""
    print("=" * 60)
    print("Example 1: Basic Self-Consistency (Majority Voting)")
    print("=" * 60)

    agent = VariableAgent()
    sc = SelfConsistency(
        agent=agent,
        num_samples=5,
        voting_strategy="majority"
    )

    query = "What is the answer?"
    response = await sc.process(Message(role="user", content=query))

    print(f"\nQuery: {query}")
    print(f"\nAll Samples:")
    for i, sample in enumerate(response.metadata['extracted_answers'], 1):
        print(f"  {i}. {sample}")

    print(f"\nAnswer Counts: {response.metadata['answer_counts']}")
    print(f"\nConsensus Answer: {response.content}")
    print(f"Consistency Score: {response.metadata['consistency_score']:.2f}")
    print(f"  (4 out of 5 agree = 0.80)")


async def weighted_voting_example():
    """Example with weighted voting strategy."""
    print("\n" + "=" * 60)
    print("Example 2: Weighted Voting (by response length)")
    print("=" * 60)

    class DetailedAgent:
        def __init__(self):
            self.name = "detailed_agent"
            self.responses = [
                "A",  # Short
                "After extensive analysis and consideration of multiple factors, the answer is B",  # Long
                "A",  # Short
            ]
            self.call_count = 0

        async def process(self, message: Message) -> Message:
            response = self.responses[self.call_count % len(self.responses)]
            self.call_count += 1
            return Message(role="assistant", content=response)

    agent = DetailedAgent()
    sc = SelfConsistency(
        agent=agent,
        num_samples=3,
        voting_strategy="weighted"
    )

    response = await sc.process(Message(role="user", content="Question?"))

    print(f"\nSamples:")
    for i, (answer, full) in enumerate(zip(
        response.metadata['extracted_answers'],
        response.metadata['samples']
    ), 1):
        print(f"  {i}. '{answer}' (length: {len(full)})")

    print(f"\nWeighted Winner: {response.content}")
    print(f"  (Longer response gets more weight)")


async def cot_plus_sc_example():
    """Combine Chain-of-Thought with Self-Consistency."""
    print("\n" + "=" * 60)
    print("Example 3: Chain-of-Thought + Self-Consistency")
    print("=" * 60)

    llm = MockLLM()
    cot = ChainOfThought(llm=llm)
    sc = SelfConsistency(agent=cot, num_samples=5)

    query = "What is the capital of France?"
    response = await sc.process(Message(role="user", content=query))

    print(f"\nQuery: {query}")
    print(f"\nBase Agent: {response.metadata['base_agent']}")
    print(f"Samples: {response.metadata['num_samples']}")

    print(f"\nExtracted Answers:")
    for i, answer in enumerate(response.metadata['extracted_answers'], 1):
        print(f"  {i}. {answer}")

    print(f"\nConsensus: {response.content}")
    print(f"Consistency: {response.metadata['consistency_score']:.2f}")


async def custom_extractor_example():
    """Example with custom answer extractor."""
    print("\n" + "=" * 60)
    print("Example 4: Custom Answer Extractor")
    print("=" * 60)

    def extract_number(text: str) -> str:
        """Extract first number from text."""
        import re
        match = re.search(r'\d+', text)
        return match.group(0) if match else text

    class NumericAgent:
        def __init__(self):
            self.name = "numeric_agent"
            self.responses = [
                "The result is approximately 100 units",
                "I calculate 100 as the answer",
                "Answer: 100",
                "It's 99 actually",  # Outlier
                "100 is correct",
            ]
            self.call_count = 0

        async def process(self, message: Message) -> Message:
            response = self.responses[self.call_count % len(self.responses)]
            self.call_count += 1
            return Message(role="assistant", content=response)

    agent = NumericAgent()
    sc = SelfConsistency(
        agent=agent,
        num_samples=5,
        answer_extractor=extract_number
    )

    response = await sc.process(Message(role="user", content="Calculate"))

    print(f"\nFull Responses:")
    for i, sample in enumerate(response.metadata['samples'], 1):
        print(f"  {i}. {sample}")

    print(f"\nExtracted Numbers: {response.metadata['extracted_answers']}")
    print(f"\nConsensus: {response.content}")
    print(f"Consistency: {response.metadata['consistency_score']:.2f}")


async def reliability_comparison():
    """Compare single sample vs Self-Consistency."""
    print("\n" + "=" * 60)
    print("Example 5: Reliability Comparison")
    print("=" * 60)

    llm = MockLLM()

    # Single sample (no self-consistency)
    cot_single = ChainOfThought(llm=llm)
    response_single = await cot_single.process(
        Message(role="user", content="What's the best programming language?")
    )

    # Multiple samples with consensus
    cot_multi = ChainOfThought(llm=MockLLM())
    sc = SelfConsistency(agent=cot_multi, num_samples=5)
    response_sc = await sc.process(
        Message(role="user", content="What's the best programming language?")
    )

    print("\nSingle Sample:")
    print(f"  Answer: {response_single.content}")
    print(f"  Reliability: Unknown (single data point)")

    print("\nSelf-Consistency (5 samples):")
    print(f"  Answers: {response_sc.metadata['extracted_answers']}")
    print(f"  Consensus: {response_sc.content}")
    print(f"  Consistency Score: {response_sc.metadata['consistency_score']:.2f}")
    print(f"  Reliability: {response_sc.metadata['consistency_score'] * 100:.0f}% agreement")

    print("\n💡 Higher consistency = more reliable answer")
    print("💡 Use SC when accuracy is critical")


async def main():
    """Run all examples."""
    await basic_example()
    await weighted_voting_example()
    await cot_plus_sc_example()
    await custom_extractor_example()
    await reliability_comparison()

    print("\n" + "=" * 60)
    print("Self-Consistency Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
