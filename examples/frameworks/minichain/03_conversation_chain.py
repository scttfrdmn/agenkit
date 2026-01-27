"""
MiniChain Example 3: Conversation Chain

Demonstrates:
- Conversational chain with memory
- Context window management
- Multi-turn conversations
- History clearing

~150 LOC
"""

import asyncio
import os

from agenkit.adapters.llm import OpenAILLM
from minichain import ConversationChain


async def basic_conversation():
    """Basic multi-turn conversation with memory."""
    print("=" * 60)
    print("Example 1: Basic Conversation")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create conversation chain
    chain = ConversationChain(
        agent=llm,
        system_message="You are a helpful assistant.",
    )

    # Multi-turn conversation
    conversation = [
        "My name is Alice.",
        "What's my name?",  # Tests memory
        "I like Python programming.",
        "What do I like?",  # Tests memory
    ]

    print("\n💬 Starting conversation...\n")

    for user_input in conversation:
        response = await chain.invoke(user_input)
        print(f"User: {user_input}")
        print(f"Assistant: {response}\n")


async def context_window_management():
    """Demonstrate context window limits and history management."""
    print("=" * 60)
    print("Example 2: Context Window Management")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create chain with small history limit
    chain = ConversationChain(
        agent=llm,
        system_message="You are a helpful assistant.",
        max_history=4,  # Only keep last 4 messages (2 turns)
    )

    print("\n💬 Testing with max_history=4...\n")

    # Send 3 messages
    await chain.invoke("Remember: My favorite color is blue.")
    print("User: Remember: My favorite color is blue.")
    print("Assistant: [Acknowledged]\n")

    await chain.invoke("Remember: I live in San Francisco.")
    print("User: Remember: I live in San Francisco.")
    print("Assistant: [Acknowledged]\n")

    await chain.invoke("Remember: My favorite food is pizza.")
    print("User: Remember: My favorite food is pizza.")
    print("Assistant: [Acknowledged]\n")

    # This should only remember recent messages (pizza and SF)
    # First message (blue) should be forgotten
    response = await chain.invoke("What's my favorite color?")
    print("User: What's my favorite color?")
    print(f"Assistant: {response}")
    print("(Should not remember - outside context window)\n")

    response = await chain.invoke("What's my favorite food?")
    print("User: What's my favorite food?")
    print(f"Assistant: {response}")
    print("(Should remember - within context window)\n")


async def specialized_assistant():
    """Create a specialized conversational assistant."""
    print("=" * 60)
    print("Example 3: Specialized Assistant")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create coding tutor
    tutor = ConversationChain(
        agent=llm,
        system_message="""You are a patient coding tutor.
- Explain concepts simply
- Provide code examples
- Remember the student's level and previous questions
- Build on previous topics""",
        max_history=10,
    )

    print("\n👨‍💻 Coding Tutor Session...\n")

    questions = [
        "I'm new to Python. Can you explain variables?",
        "Can you show me an example?",
        "How do I use those variables in a function?",
        "What if I want to return multiple values?",
    ]

    for question in questions:
        response = await tutor.invoke(question)
        print(f"Student: {question}")
        print(f"Tutor: {response}\n")


async def history_management():
    """Demonstrate history clearing and management."""
    print("=" * 60)
    print("Example 4: History Management")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    chain = ConversationChain(
        agent=llm,
        system_message="You are a helpful assistant.",
    )

    print("\n💬 Conversation 1...\n")

    # First conversation
    await chain.invoke("My name is Bob.")
    response = await chain.invoke("What's my name?")
    print("User: What's my name?")
    print(f"Assistant: {response}")
    print("(Should remember: Bob)\n")

    # Clear history
    print("🧹 Clearing history...\n")
    chain.clear_history()

    # New conversation - should not remember
    print("💬 Conversation 2 (after clearing)...\n")
    response = await chain.invoke("What's my name?")
    print("User: What's my name?")
    print(f"Assistant: {response}")
    print("(Should NOT remember - history cleared)\n")


async def personality_conversations():
    """Different personalities for different contexts."""
    print("=" * 60)
    print("Example 5: Different Personalities")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Pirate assistant
    pirate = ConversationChain(
        agent=llm,
        system_message="You are a pirate captain. Always stay in character!",
    )

    # Shakespeare assistant
    shakespeare = ConversationChain(
        agent=llm,
        system_message="You speak like Shakespeare. Use thou, thee, and flowery language!",
    )

    print("\n🏴‍☠️ Pirate Captain:\n")
    response = await pirate.invoke("What's the weather like?")
    print(f"User: What's the weather like?")
    print(f"Captain: {response}\n")

    print("📜 Shakespeare:\n")
    response = await shakespeare.invoke("What's the weather like?")
    print(f"User: What's the weather like?")
    print(f"Bard: {response}\n")


async def main():
    """Run all conversation examples."""
    try:
        await basic_conversation()
        await context_window_management()
        await specialized_assistant()
        await history_management()
        await personality_conversations()

        print("=" * 60)
        print("✅ All conversation examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
