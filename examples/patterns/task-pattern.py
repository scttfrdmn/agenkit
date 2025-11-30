"""
Task Pattern Example - One-Shot Agent Execution with Lifecycle Management

The Task pattern wraps an Agent for single-use execution with automatic
resource cleanup and lifecycle management.

WHY use this pattern:
✅ Explicit one-shot semantics (execute once, then cleanup)
✅ Automatic resource cleanup after completion
✅ Built-in timeout and retry support
✅ Prevention of accidental reuse after completion
✅ Context manager for guaranteed cleanup

WHEN to use:
- One-time operations (summarize document, classify text, extract entities)
- Tasks requiring resource cleanup (close connections, release memory)
- Operations with timeout requirements
- Tasks that need retry logic
- Anywhere you need guaranteed cleanup after execution

WHEN NOT to use:
- Multi-turn conversations (use Agent directly)
- Stateful interactions across multiple calls
- Long-running background processes

Run: python examples/patterns/task-pattern.py
"""

import asyncio

from agenkit.interfaces import Agent, Message
from agenkit.patterns import Task


# Mock agent for demonstration (replace with real LLM agent in production)
class DocumentSummarizationAgent:
    """
    Mock document summarization agent.

    In production, replace with actual LLM (OpenAI, Anthropic, etc.)
    """

    def __init__(self, model: str = "gpt-4"):
        self.model = model
        self._connections = []  # Simulated resources

    @property
    def name(self) -> str:
        return "DocumentSummarizer"

    @property
    def capabilities(self) -> list[str]:
        return ["summarization", "text-processing"]

    async def call(self, messages: list[Message], **kwargs) -> Message:
        """Summarize a document."""
        # Simulate API connection
        self._connections.append("connection-1")

        # Get the document content from the last message
        content = messages[-1].content if messages else ""

        # Simulate processing time
        await asyncio.sleep(0.1)

        # Generate summary based on content type
        if "technical" in content.lower():
            summary = (
                f"[{self.model}] Technical Summary:\n"
                "This document discusses software architecture patterns, "
                "best practices, and implementation guidelines. Key topics "
                "include modularity, scalability, and maintainability."
            )
        elif "research" in content.lower():
            summary = (
                f"[{self.model}] Research Summary:\n"
                "This research paper presents findings on recent developments "
                "in the field, including methodology, results, and implications "
                "for future work."
            )
        else:
            summary = (
                f"[{self.model}] Summary:\n"
                "This document provides an overview of key concepts, examples, "
                "and practical applications."
            )

        return Message(role="assistant", content=summary)

    async def cleanup(self):
        """Clean up resources."""
        # Simulate closing connections
        self._connections.clear()
        print(f"  🧹 Cleaned up {self.name} resources")


class UnreliableAgent:
    """
    Mock agent that fails on first attempt but succeeds on retry.

    Demonstrates Task pattern's built-in retry support.
    """

    def __init__(self):
        self.attempt_count = 0

    @property
    def name(self) -> str:
        return "UnreliableAgent"

    @property
    def capabilities(self) -> list[str]:
        return ["unreliable-operation"]

    async def call(self, messages: list[Message], **kwargs) -> Message:
        """Process with potential failure."""
        self.attempt_count += 1

        # Fail on first attempt, succeed on retry
        if self.attempt_count == 1:
            print(f"  ❌ Attempt {self.attempt_count}: Simulated failure (network error)")
            raise ConnectionError("Simulated network error")

        print(f"  ✅ Attempt {self.attempt_count}: Success!")
        return Message(
            role="assistant",
            content=f"Successfully processed after {self.attempt_count} attempts",
        )


async def example_basic_task():
    """Example 1: Basic Task usage with context manager."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Task Usage")
    print("=" * 70)

    agent = DocumentSummarizationAgent()

    # Using context manager for automatic cleanup
    async with Task(agent) as task:
        messages = [
            Message(
                role="user",
                content="Please summarize this technical document about software architecture.",
            )
        ]

        result = await task.execute(messages)
        print(f"\n📋 Summary:\n{result.content}\n")

        print(f"✓ Task completed: {task.completed}")
        print(f"✓ Result available: {task.result is not None}")

    # Cleanup happens automatically when exiting context manager
    print("✓ Context manager exited - resources cleaned up")


async def example_task_with_timeout():
    """Example 2: Task with timeout protection."""
    print("\n" + "=" * 70)
    print("Example 2: Task with Timeout")
    print("=" * 70)

    agent = DocumentSummarizationAgent()

    # Task with 30 second timeout
    async with Task(agent, timeout=30.0) as task:
        messages = [
            Message(
                role="user",
                content="Summarize this research paper on machine learning.",
            )
        ]

        try:
            result = await task.execute(messages)
            print(f"\n📋 Summary (completed within timeout):\n{result.content}\n")
        except asyncio.TimeoutError:
            print("❌ Task exceeded 30 second timeout")


async def example_task_with_retries():
    """Example 3: Task with automatic retries on failure."""
    print("\n" + "=" * 70)
    print("Example 3: Task with Retries")
    print("=" * 70)

    agent = UnreliableAgent()

    # Task with 2 retries (3 total attempts)
    async with Task(agent, retries=2) as task:
        messages = [Message(role="user", content="Process this request")]

        try:
            result = await task.execute(messages)
            print(f"\n✅ {result.content}\n")
        except Exception as e:
            print(f"❌ Task failed after all retries: {e}")


async def example_task_reuse_prevention():
    """Example 4: Task prevents reuse after completion."""
    print("\n" + "=" * 70)
    print("Example 4: Task Reuse Prevention")
    print("=" * 70)

    agent = DocumentSummarizationAgent()
    task = Task(agent)

    messages = [Message(role="user", content="Summarize this document.")]

    # First execution
    result1 = await task.execute(messages)
    print(f"✓ First execution completed: {result1.content[:50]}...")

    # Attempt to reuse the same task
    try:
        result2 = await task.execute(messages)
        print(f"✓ Second execution: {result2.content}")
    except RuntimeError as e:
        print(f"❌ Reuse prevented: {e}")

    print("\n💡 To execute again, create a new Task instance:")
    task2 = Task(agent)
    result2 = await task2.execute(messages)
    print(f"✓ New task executed successfully: {result2.content[:50]}...")

    # Cleanup both tasks
    await task.cleanup()
    await task2.cleanup()


async def example_manual_cleanup():
    """Example 5: Manual cleanup without context manager."""
    print("\n" + "=" * 70)
    print("Example 5: Manual Cleanup")
    print("=" * 70)

    agent = DocumentSummarizationAgent()
    task = Task(agent, timeout=10.0, retries=1)

    try:
        messages = [Message(role="user", content="Quick summary needed.")]
        result = await task.execute(messages)
        print(f"\n✅ Result: {result.content[:50]}...\n")
    finally:
        # Always cleanup in finally block
        await task.cleanup()
        print("✓ Manual cleanup completed")


async def example_comparison():
    """Example 6: When to use Task vs Agent directly."""
    print("\n" + "=" * 70)
    print("Example 6: Task vs Agent Comparison")
    print("=" * 70)

    print("\n📌 Use Task when:")
    print("  • One-shot operation (summarize, classify, extract)")
    print("  • Need automatic resource cleanup")
    print("  • Need timeout or retry support")
    print("  • Want to prevent accidental reuse")
    print("  • Have cleanup requirements")

    print("\n📌 Use Agent directly when:")
    print("  • Multi-turn conversation")
    print("  • Stateful interaction")
    print("  • Need to maintain context across calls")
    print("  • Don't need explicit one-shot semantics")

    print("\n💡 Example use cases:")
    print("  Task: Summarize document, classify email, extract entities")
    print("  Agent: Chatbot, assistant, multi-step workflow")


async def main():
    """Run all Task pattern examples."""
    print("\n" + "=" * 70)
    print("TASK PATTERN EXAMPLES")
    print("=" * 70)
    print("Demonstrating one-shot agent execution with lifecycle management")

    await example_basic_task()
    await example_task_with_timeout()
    await example_task_with_retries()
    await example_task_reuse_prevention()
    await example_manual_cleanup()
    await example_comparison()

    print("\n" + "=" * 70)
    print("✅ ALL EXAMPLES COMPLETED")
    print("=" * 70)
    print("\n💡 Key Takeaways:")
    print("  1. Task provides one-shot execution with automatic cleanup")
    print("  2. Use context manager for guaranteed resource cleanup")
    print("  3. Built-in timeout and retry support")
    print("  4. Prevents accidental reuse after completion")
    print("  5. Choose Task for one-shot operations, Agent for multi-turn")


if __name__ == "__main__":
    asyncio.run(main())
