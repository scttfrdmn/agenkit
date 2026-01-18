"""
Simplified RLM API test - focuses on core pattern functionality.

This script tests RLM with a real API using a small example to verify:
- Code execution works with real LLM
- Recursive sub-calls work
- FINAL() answer extraction works
- Pattern produces correct results

Usage:
    export ANTHROPIC_API_KEY="your-key-here"
    uv run python examples/experimental/long_context_rlm/test_with_api_simple.py

Expected cost: $0.01-0.05 (very small test)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from basic_rlm import RecursiveREPLAgent

from agenkit.adapters.llm.anthropic import AnthropicLLM
from agenkit.interfaces import Agent, Message


class LLMAgent(Agent):
    """Simple agent wrapper around LLM adapter."""

    def __init__(self, llm: AnthropicLLM, name: str):
        self.llm = llm
        self._name = name

    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        """Process message using LLM."""
        print(f"   [{self._name}] Processing ({len(message.content)} chars)...")
        response = await self.llm.complete(
            messages=[message],
            temperature=0.7,
            max_tokens=2048,
        )
        print(f"   [{self._name}] Response: {len(response.content)} chars")
        print(f"   [{self._name}] Content preview: {response.content[:200]}...")
        return response


async def main():
    """Run simplified RLM test."""
    print("=" * 70)
    print("RLM Simple API Test")
    print("=" * 70)

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n❌ Error: ANTHROPIC_API_KEY not set")
        print("   export ANTHROPIC_API_KEY='your-key-here'")
        return

    # Small test context with clear query
    context = """Company Information:
Document 1: Acme Corp was founded in 2015.
Document 2: The CEO is Alice Johnson.
Document 3: Headquarters are in Boston.
Document 4: Revenue grew 300% in 2023.
Document 5: Product Widget X launched in 2018.

QUERY: Based on these documents, answer:
1. What year was Acme Corp founded?
2. What was their revenue growth percentage in 2023?

Your task: Write Python code to extract this information and provide FINAL(answer) when done.
"""

    print(f"\n📄 Context: {len(context)} characters")
    print(f"\n🤖 Using: claude-3-haiku-20240307")

    # Create agents
    root_llm = AnthropicLLM(api_key=api_key, model="claude-3-haiku-20240307")
    sub_llm = AnthropicLLM(api_key=api_key, model="claude-3-haiku-20240307")

    root_agent = LLMAgent(root_llm, "root")
    sub_agent = LLMAgent(sub_llm, "sub")

    # Create RLM (no budget for simplicity)
    rlm = RecursiveREPLAgent(
        agent=root_agent,
        sub_agent=sub_agent,
        max_iterations=5,
    )

    # Run
    print("\n🔄 Processing with RLM...\n")
    message = Message(role="user", content=context)

    try:
        result = await rlm.process(message)

        print("\n" + "=" * 70)
        print("✅ SUCCESS - Final Answer:")
        print("=" * 70)
        print(result.content)
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
