"""
MiniChain Example 1: Basic Chain

Demonstrates:
- Simple LLMChain (prompt → LLM → output)
- Pipe operator for composition (|)
- RunnableLambda for transformations
- Basic chain operations

~100 LOC
"""

import asyncio
import os

from agenkit.adapters.llm import OpenAILLM
from minichain import LLMChain, RunnableLambda


async def basic_llm_chain():
    """Simple prompt → LLM → output."""
    print("=" * 60)
    print("Example 1: Basic LLM Chain")
    print("=" * 60)

    # Initialize LLM
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create a simple chain
    chain = LLMChain(
        agent=llm,
        prompt_template="Explain {topic} in one sentence.",
    )

    # Execute chain
    result = await chain.invoke({"topic": "quantum computing"})
    print(f"\nInput: quantum computing")
    print(f"Output: {result}\n")


async def chained_transformations():
    """Chain with pre/post-processing transformations."""
    print("=" * 60)
    print("Example 2: Chain with Transformations")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create transformation functions
    def uppercase_input(text: str) -> dict:
        """Convert to uppercase and wrap in dict."""
        return {"topic": text.upper()}

    def add_context(text: str) -> str:
        """Add context to output."""
        return f"📚 Explanation: {text}"

    # Compose chain with pipe operator
    chain = (
        RunnableLambda(uppercase_input)  # Pre-processing
        | LLMChain(agent=llm, prompt_template="Define {topic} simply.")  # LLM call
        | RunnableLambda(add_context)  # Post-processing
    )

    # Execute
    result = await chain.invoke("machine learning")
    print(f"\nInput: 'machine learning'")
    print(f"Output: {result}\n")


async def multiple_llm_calls():
    """Chain multiple LLM calls together."""
    print("=" * 60)
    print("Example 3: Multiple LLM Calls")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create a chain that generates, then refines
    generate = LLMChain(
        agent=llm,
        prompt_template="Write a creative title for an article about {topic}.",
    )

    # Transform output into format for next chain
    def prepare_refinement(title: str) -> dict:
        return {"title": title}

    refine = LLMChain(
        agent=llm,
        prompt_template="Make this title more professional: {title}",
    )

    # Compose: generate → transform → refine
    chain = generate | RunnableLambda(prepare_refinement) | refine

    # Execute
    result = await chain.invoke({"topic": "artificial intelligence"})
    print(f"\nInput: 'artificial intelligence'")
    print(f"Final Title: {result}\n")


async def with_system_message():
    """Chain with system message for context."""
    print("=" * 60)
    print("Example 4: Chain with System Message")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create chain with personality
    chain = LLMChain(
        agent=llm,
        prompt_template="{question}",
        system_message="You are a pirate who answers questions while staying in character.",
    )

    # Execute
    questions = [
        "What is cloud computing?",
        "How do databases work?",
    ]

    for question in questions:
        result = await chain.invoke({"question": question})
        print(f"\nQ: {question}")
        print(f"A: {result}")

    print()


async def main():
    """Run all examples."""
    try:
        await basic_llm_chain()
        await chained_transformations()
        await multiple_llm_calls()
        await with_system_message()

        print("=" * 60)
        print("✅ All basic chain examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
