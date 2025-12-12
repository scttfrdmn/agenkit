"""
Chain-of-Thought (CoT) Reasoning Example

Demonstrates how to use Chain-of-Thought prompting to encourage
step-by-step reasoning from an LLM.

This example shows:
- Basic CoT usage with default prompting
- Custom prompt templates
- Step parsing and tracking
- Integration with different LLM interfaces

Requirements:
    pip install agenkit openai  # or your preferred LLM provider
"""

import asyncio
from agenkit import Message
from agenkit.techniques.reasoning import ChainOfThought


# Example 1: Mock LLM for demonstration
class MockLLM:
    """Simple mock LLM that demonstrates CoT reasoning."""

    async def complete(self, prompt: str) -> str:
        """Return a mock response with step-by-step reasoning."""
        if "15 * 24" in prompt:
            return """Let me solve this step by step:

1. First, I'll break down 24 into 20 + 4
2. Multiply 15 × 20 = 300
3. Multiply 15 × 4 = 60
4. Add the results: 300 + 60 = 360

Therefore, 15 × 24 = 360"""

        if "prime" in prompt.lower():
            return """Let me check if 17 is prime:

1. A prime number is only divisible by 1 and itself
2. Check if 17 is divisible by 2: 17 ÷ 2 = 8.5 (not divisible)
3. Check if 17 is divisible by 3: 17 ÷ 3 = 5.67 (not divisible)
4. Check if 17 is divisible by 5: 17 ÷ 5 = 3.4 (not divisible)
5. We only need to check up to √17 ≈ 4.1

Therefore, 17 is prime."""

        return "I need to think through this carefully."


async def basic_example():
    """Basic Chain-of-Thought example."""
    print("=" * 60)
    print("Example 1: Basic Chain-of-Thought Reasoning")
    print("=" * 60)

    # Create CoT agent with default "Let's think step by step" prompt
    llm = MockLLM()
    cot = ChainOfThought(llm=llm)

    # Process a math problem
    query = "What is 15 * 24?"
    response = await cot.process(Message(role="user", content=query))

    print(f"\nQuery: {query}")
    print(f"\nResponse:\n{response.content}")
    print(f"\nExtracted Steps ({response.metadata['num_steps']}):")
    for i, step in enumerate(response.metadata["reasoning_steps"], 1):
        print(f"  {i}. {step}")


async def custom_template_example():
    """Example with custom prompt template."""
    print("\n" + "=" * 60)
    print("Example 2: Custom Prompt Template")
    print("=" * 60)

    llm = MockLLM()

    # Use a custom prompt template
    custom_prompt = """Analyze this problem carefully and solve it step by step:

{query}

Show your reasoning process:"""

    cot = ChainOfThought(llm=llm, prompt_template=custom_prompt)

    query = "Is 17 a prime number?"
    response = await cot.process(Message(role="user", content=query))

    print(f"\nQuery: {query}")
    print(f"\nResponse:\n{response.content}")
    print(f"\nExtracted Steps: {response.metadata['num_steps']}")


async def limiting_steps_example():
    """Example with max_steps limiting."""
    print("\n" + "=" * 60)
    print("Example 3: Limiting Number of Steps")
    print("=" * 60)

    llm = MockLLM()

    # Limit to first 3 steps only
    cot = ChainOfThought(llm=llm, max_steps=3)

    query = "Is 17 a prime number?"
    response = await cot.process(Message(role="user", content=query))

    print(f"\nQuery: {query}")
    print(f"Max steps configured: 3")
    print(f"Steps extracted: {response.metadata['num_steps']}")
    print("\nFirst 3 steps only:")
    for i, step in enumerate(response.metadata["reasoning_steps"], 1):
        print(f"  {i}. {step}")


async def no_parsing_example():
    """Example without step parsing."""
    print("\n" + "=" * 60)
    print("Example 4: Without Step Parsing")
    print("=" * 60)

    llm = MockLLM()

    # Disable step parsing - just apply CoT prompting
    cot = ChainOfThought(llm=llm, parse_steps=False)

    query = "What is 15 * 24?"
    response = await cot.process(Message(role="user", content=query))

    print(f"\nQuery: {query}")
    print(f"\nResponse:\n{response.content}")
    print(f"\nMetadata: {response.metadata}")
    print("(Note: No step parsing, just technique marker)")


async def real_llm_example():
    """Example with a real LLM (OpenAI)."""
    print("\n" + "=" * 60)
    print("Example 5: With Real LLM (OpenAI)")
    print("=" * 60)

    try:
        from openai import AsyncOpenAI

        # Initialize OpenAI client
        client = AsyncOpenAI()  # Uses OPENAI_API_KEY env var

        # Create a simple LLM wrapper
        class OpenAILLM:
            def __init__(self, client):
                self.client = client

            async def complete(self, prompt: str) -> str:
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
                return response.choices[0].message.content

        llm = OpenAILLM(client)
        cot = ChainOfThought(llm=llm)

        query = "If a train travels 120 miles in 2 hours, what is its average speed?"
        response = await cot.process(Message(role="user", content=query))

        print(f"\nQuery: {query}")
        print(f"\nResponse:\n{response.content}")
        print(f"\nExtracted Steps: {response.metadata['num_steps']}")

    except ImportError:
        print("\nSkipping - OpenAI not installed")
        print("Install with: pip install openai")
    except Exception as e:
        print(f"\nSkipping - Error: {e}")
        print("Make sure OPENAI_API_KEY is set in your environment")


async def main():
    """Run all examples."""
    await basic_example()
    await custom_template_example()
    await limiting_steps_example()
    await no_parsing_example()
    await real_llm_example()

    print("\n" + "=" * 60)
    print("Chain-of-Thought Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
