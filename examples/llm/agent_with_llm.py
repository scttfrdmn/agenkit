"""
Building agents with LLMs.

Shows:
- Conversational agents with state
- Agent patterns with LLMs
- Provider swapping in agents
- Production-ready patterns
"""

import asyncio
import os
from typing import Any

from agenkit.adapters.llm import LLM, AnthropicLLM, OpenAILLM
from agenkit.interfaces import Message
from agenkit.patterns import Task


class ChatAgent:
    """Simple conversational agent powered by an LLM."""

    def __init__(self, llm: LLM):
        self.llm = llm
        self.history: list[Message] = []
        self.system_prompt = "You are a helpful AI assistant. Keep responses concise and friendly."

    async def chat(self, user_message: str) -> str:
        """Send a message and get a response."""
        # Add system prompt on first message
        if not self.history:
            self.history.append(Message(role="system", content=self.system_prompt))

        # Add user message
        self.history.append(Message(role="user", content=user_message))

        # Get LLM response
        response = await self.llm.complete(self.history, max_tokens=200)

        # Add to history
        self.history.append(response)

        return response.content

    def clear_history(self):
        """Clear conversation history."""
        self.history.clear()


async def basic_chat_agent():
    """Basic conversational agent."""
    print("=" * 60)
    print("Basic Chat Agent")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    # Create agent with Anthropic
    llm = AnthropicLLM(api_key=api_key, model="claude-3-haiku-20240307")
    agent = ChatAgent(llm)

    # Have a conversation
    questions = [
        "What is an agent?",
        "Can you give an example?",
        "How would I build one in Python?",
    ]

    for question in questions:
        print(f"User: {question}")
        response = await agent.chat(question)
        print(f"Agent: {response}\n")


async def swappable_agent():
    """Agent that can swap LLM providers."""
    print("=" * 60)
    print("Swappable Agent")
    print("=" * 60)

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key or not openai_key:
        print("❌ Both ANTHROPIC_API_KEY and OPENAI_API_KEY required")
        return

    # Start with Anthropic
    print("Starting with Anthropic Claude...")
    llm = AnthropicLLM(api_key=anthropic_key, model="claude-3-haiku-20240307")
    agent = ChatAgent(llm)

    response = await agent.chat("What is 2+2?")
    print(f"Claude: {response}\n")

    # Switch to OpenAI (agent code stays the same!)
    print("Switching to OpenAI GPT...")
    agent.llm = OpenAILLM(api_key=openai_key, model="gpt-4o-mini")

    response = await agent.chat("What about 3+3?")
    print(f"GPT: {response}\n")

    print("✅ Same agent, different providers!\n")


class SpecializedAgent:
    """Agent specialized for a specific task."""

    def __init__(self, llm: LLM, expertise: str):
        self.llm = llm
        self.expertise = expertise
        self.system_prompt = f"You are an expert in {expertise}. Provide detailed, accurate information. Keep responses under 100 words."

    async def ask(self, question: str) -> str:
        """Ask a question within the agent's expertise."""
        messages = [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=question),
        ]

        response = await self.llm.complete(messages, max_tokens=200)
        return response.content


async def specialized_agents():
    """Multiple specialized agents."""
    print("=" * 60)
    print("Specialized Agents")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create specialized agents
    python_expert = SpecializedAgent(llm, "Python programming")
    math_expert = SpecializedAgent(llm, "mathematics")

    # Ask each agent
    print("Python Expert:")
    response = await python_expert.ask("What are decorators?")
    print(f"  {response}\n")

    print("Math Expert:")
    response = await math_expert.ask("Explain the Pythagorean theorem.")
    print(f"  {response}\n")


async def agent_with_task_pattern():
    """Use Task pattern for one-shot agent execution."""
    print("=" * 60)
    print("Agent with Task Pattern")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    # Wrap LLM in an agent-like interface
    class SimpleLLMAgent:
        def __init__(self, llm: LLM):
            self.llm = llm

        async def call(self, messages: list[Message], **kwargs: Any) -> Message:
            return await self.llm.complete(messages, **kwargs)

    llm = AnthropicLLM(api_key=api_key, model="claude-3-haiku-20240307")
    agent = SimpleLLMAgent(llm)

    messages = [Message(role="user", content="Explain the Task pattern in one sentence.")]

    # Use Task pattern with timeout
    print("Executing with Task pattern (5s timeout)...")
    try:
        async with Task(agent, timeout=5.0) as task:
            result = await task.execute(messages, max_tokens=100)
            print(f"Result: {result.content}\n")
    except asyncio.TimeoutError:
        print("❌ Task timed out\n")


class ProductionAgent:
    """Production-ready agent with error handling and retries."""

    def __init__(self, primary_llm: LLM, fallback_llm: LLM | None = None):
        self.primary_llm = primary_llm
        self.fallback_llm = fallback_llm
        self.history: list[Message] = []

    async def chat(self, user_message: str, max_retries: int = 2) -> str:
        """Chat with automatic retry and fallback."""
        self.history.append(Message(role="user", content=user_message))

        # Try primary LLM
        for attempt in range(max_retries):
            try:
                response = await self.primary_llm.complete(
                    self.history,
                    max_tokens=200,
                )
                self.history.append(response)
                return response.content

            except Exception as e:
                if attempt == max_retries - 1:
                    # Last attempt, try fallback
                    if self.fallback_llm:
                        print("Primary failed, using fallback...")
                        try:
                            response = await self.fallback_llm.complete(
                                self.history,
                                max_tokens=200,
                            )
                            self.history.append(response)
                            return response.content
                        except Exception as fallback_error:
                            raise Exception(f"Both providers failed: {fallback_error}") from e
                    raise

                # Retry with exponential backoff
                wait_time = 2**attempt
                print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

        raise Exception("All retries exhausted")


async def production_agent_example():
    """Production-ready agent with fallback."""
    print("=" * 60)
    print("Production Agent (with fallback)")
    print("=" * 60)

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key or not openai_key:
        print("❌ Both ANTHROPIC_API_KEY and OPENAI_API_KEY required")
        return

    # Primary and fallback LLMs
    primary = AnthropicLLM(api_key=anthropic_key, model="claude-3-haiku-20240307")
    fallback = OpenAILLM(api_key=openai_key, model="gpt-4o-mini")

    agent = ProductionAgent(primary_llm=primary, fallback_llm=fallback)

    # Normal operation
    response = await agent.chat("What is reliability in software?")
    print(f"Response: {response}\n")

    # Test with invalid primary (will use fallback)
    print("Testing fallback mechanism...")
    invalid_primary = AnthropicLLM(api_key="invalid-key")
    agent2 = ProductionAgent(primary_llm=invalid_primary, fallback_llm=fallback)

    try:
        response = await agent2.chat("Hello!")
        print(f"Fallback worked: {response}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")


async def main():
    """Run all examples."""
    print("\n🤖 Agent with LLM Examples\n")

    await basic_chat_agent()
    await swappable_agent()
    await specialized_agents()
    await agent_with_task_pattern()
    await production_agent_example()

    print("✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
