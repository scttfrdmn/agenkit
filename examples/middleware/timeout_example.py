"""
Timeout Middleware Example

This example demonstrates WHY and HOW to use timeout middleware for preventing
long-running requests from blocking resources.

WHY USE TIMEOUT MIDDLEWARE?
---------------------------
- Prevent hung requests: Stop operations that take too long
- Resource protection: Free up resources from slow/stuck operations
- Predictable latency: Ensure requests complete within SLA requirements
- Fault isolation: Prevent one slow operation from affecting others

WHEN TO USE:
- External API calls with unpredictable response times
- LLM requests that may hang or take too long
- Network operations prone to hanging
- Any operation with strict latency requirements

WHEN NOT TO USE:
- Known long-running operations (use higher timeout or streaming instead)
- Operations where partial results aren't acceptable
- When timeout would cause data corruption
- Real-time systems where timeout handling adds overhead

TRADE-OFFS:
- Incomplete work: Operations are cancelled mid-execution
- Resource cleanup: May need to handle cleanup of timed-out operations
- Tuning required: Finding the right timeout value can be challenging
- False positives: Legitimate slow operations may be cancelled
"""

import asyncio
import random
from agenkit.interfaces import Agent, Message
from agenkit.middleware import TimeoutConfig, TimeoutDecorator, TimeoutError


# Simulate a slow LLM API
class SlowLLMAgent(Agent):
    """Simulates an LLM that sometimes takes too long to respond."""

    def __init__(self, response_time: float = 2.0):
        self.response_time = response_time

    @property
    def name(self) -> str:
        return "slow-llm"

    @property
    def capabilities(self) -> list[str]:
        return ["text-generation"]

    async def process(self, message: Message) -> Message:
        print(f"   LLM processing (will take {self.response_time:.1f}s)...")
        await asyncio.sleep(self.response_time)
        return Message(
            role="agent",
            content=f"Generated response for: {message.content}",
            metadata={"processing_time": self.response_time}
        )


# Simulate an unpredictable agent
class UnpredictableAgent(Agent):
    """Simulates an agent with highly variable response times."""

    def __init__(self):
        self.call_count = 0

    @property
    def name(self) -> str:
        return "unpredictable-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["analysis"]

    async def process(self, message: Message) -> Message:
        self.call_count += 1
        # Sometimes fast, sometimes slow
        response_time = random.choice([0.1, 0.5, 3.0, 10.0])

        print(f"   Request #{self.call_count}: will take {response_time:.1f}s")
        await asyncio.sleep(response_time)

        return Message(
            role="agent",
            content=f"Analysis complete for: {message.content}",
            metadata={"response_time": response_time}
        )


async def example_basic_timeout():
    """Example 1: Basic timeout protection."""
    print("\n=== Example 1: Basic Timeout ===")
    print("Use case: Protect against slow LLM responses\n")

    # Create a slow agent (takes 2 seconds)
    agent = SlowLLMAgent(response_time=2.0)

    # Wrap with timeout middleware (1 second limit)
    timeout_agent = TimeoutDecorator(
        agent,
        TimeoutConfig(timeout=1.0)
    )

    message = Message(role="user", content="Explain quantum computing")

    try:
        print("Sending request with 1s timeout...")
        response = await timeout_agent.process(message)
        print(f"✅ Response received: {response.content}")
    except TimeoutError as e:
        print(f"❌ Request timed out: {e}")
        print("   The request was cancelled to prevent blocking")


async def example_successful_with_timeout():
    """Example 2: Fast requests complete successfully."""
    print("\n=== Example 2: Fast Request Success ===")
    print("Use case: Normal operations complete within timeout\n")

    # Create a fast agent (takes 0.5 seconds)
    agent = SlowLLMAgent(response_time=0.5)

    # Wrap with timeout middleware (2 second limit)
    timeout_agent = TimeoutDecorator(
        agent,
        TimeoutConfig(timeout=2.0)
    )

    message = Message(role="user", content="Hello!")

    try:
        print("Sending request with 2s timeout...")
        response = await timeout_agent.process(message)
        print(f"✅ Response received: {response.content}")
        print(f"   Processing time: {response.metadata['processing_time']:.1f}s")
    except TimeoutError as e:
        print(f"❌ Unexpected timeout: {e}")


async def example_multiple_requests_with_metrics():
    """Example 3: Handling multiple requests and tracking metrics."""
    print("\n=== Example 3: Multiple Requests with Metrics ===")
    print("Use case: Track success/timeout rates across many requests\n")

    agent = UnpredictableAgent()

    # Set timeout at 2 seconds
    timeout_agent = TimeoutDecorator(
        agent,
        TimeoutConfig(timeout=2.0)
    )

    message = Message(role="user", content="Analyze this data")

    # Send 5 requests
    print("Sending 5 requests with unpredictable response times...")
    for i in range(5):
        try:
            response = await timeout_agent.process(message)
            print(f"   ✅ Request {i+1}: Success")
        except TimeoutError:
            print(f"   ❌ Request {i+1}: Timeout")

    # Check metrics
    metrics = timeout_agent.metrics
    print("\n📊 Metrics Summary:")
    print(f"   Total requests: {metrics.total_requests}")
    print(f"   Successful: {metrics.successful_requests}")
    print(f"   Timed out: {metrics.timed_out_requests}")
    print(f"   Success rate: {metrics.successful_requests/metrics.total_requests*100:.1f}%")

    if metrics.min_duration:
        print(f"   Min duration: {metrics.min_duration:.3f}s")
        print(f"   Max duration: {metrics.max_duration:.3f}s")
        print(f"   Avg duration: {metrics.avg_duration:.3f}s")


async def example_fallback_on_timeout():
    """Example 4: Implement fallback when timeout occurs."""
    print("\n=== Example 4: Fallback on Timeout ===")
    print("Use case: Provide cached/default response when primary agent times out\n")

    class CachedResponseAgent(Agent):
        """Fallback agent that returns cached responses."""

        @property
        def name(self) -> str:
            return "cached-response"

        @property
        def capabilities(self) -> list[str]:
            return ["text-generation"]

        async def process(self, message: Message) -> Message:
            return Message(
                role="agent",
                content="[Cached response] I'm a general assistant. How can I help?",
                metadata={"source": "cache"}
            )

    # Primary agent (slow)
    primary = SlowLLMAgent(response_time=5.0)
    primary_with_timeout = TimeoutDecorator(
        primary,
        TimeoutConfig(timeout=1.0)
    )

    # Fallback agent (fast)
    fallback = CachedResponseAgent()

    message = Message(role="user", content="Hello!")

    print("Trying primary agent with 1s timeout...")
    try:
        response = await primary_with_timeout.process(message)
        print(f"✅ Primary response: {response.content}")
    except TimeoutError as e:
        print(f"⚠️  Primary timed out: {e}")
        print("   Falling back to cached response...")
        response = await fallback.process(message)
        print(f"✅ Fallback response: {response.content}")


async def example_streaming_timeout():
    """Example 5: Timeout with streaming responses."""
    print("\n=== Example 5: Streaming with Timeout ===")
    print("Use case: Apply timeout to entire stream duration\n")

    class StreamingAgent(Agent):
        """Agent that streams responses over time."""

        def __init__(self, chunk_delay: float = 0.5, num_chunks: int = 5):
            self.chunk_delay = chunk_delay
            self.num_chunks = num_chunks

        @property
        def name(self) -> str:
            return "streaming-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["streaming", "text-generation"]

        async def process(self, message: Message) -> Message:
            return Message(role="agent", content="Full response")

        async def stream(self, message: Message):
            """Stream responses chunk by chunk."""
            for i in range(self.num_chunks):
                await asyncio.sleep(self.chunk_delay)
                yield Message(
                    role="agent",
                    content=f"Chunk {i+1}/{self.num_chunks}: Processing..."
                )

    # Create streaming agent (5 chunks × 0.5s = 2.5s total)
    agent = StreamingAgent(chunk_delay=0.5, num_chunks=5)

    # Wrap with 2-second timeout
    timeout_agent = TimeoutDecorator(
        agent,
        TimeoutConfig(timeout=2.0)
    )

    message = Message(role="user", content="Generate long response")

    try:
        print("Streaming with 2s timeout (should timeout after ~2s)...")
        async for chunk in timeout_agent.stream(message):
            print(f"   📦 {chunk.content}")
    except TimeoutError as e:
        print(f"❌ Stream timed out: {e}")
        print("   Timeout applies to entire stream duration")


async def example_different_timeout_strategies():
    """Example 6: Different timeout strategies for different use cases."""
    print("\n=== Example 6: Timeout Strategies ===")
    print("Use case: Choose appropriate timeout based on operation type\n")

    agent = SlowLLMAgent(response_time=1.5)

    # Strategy 1: Strict timeout for interactive responses
    interactive_agent = TimeoutDecorator(
        agent,
        TimeoutConfig(timeout=1.0)  # 1 second
    )

    # Strategy 2: Relaxed timeout for background processing
    background_agent = TimeoutDecorator(
        agent,
        TimeoutConfig(timeout=5.0)  # 5 seconds
    )

    message = Message(role="user", content="Process this")

    # Interactive request (strict timeout)
    print("Interactive request (1s timeout):")
    try:
        response = await interactive_agent.process(message)
        print(f"   ✅ Success: {response.content}")
    except TimeoutError:
        print("   ❌ Timeout: Too slow for interactive use")

    # Background request (relaxed timeout)
    print("\nBackground request (5s timeout):")
    try:
        response = await background_agent.process(message)
        print(f"   ✅ Success: {response.content}")
    except TimeoutError:
        print("   ❌ Timeout: Even background processing failed")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("Timeout Middleware Examples")
    print("=" * 60)

    await example_basic_timeout()
    await example_successful_with_timeout()
    await example_multiple_requests_with_metrics()
    await example_fallback_on_timeout()
    await example_streaming_timeout()
    await example_different_timeout_strategies()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. Set timeouts based on SLA requirements and operation type")
    print("2. Implement fallback strategies for timeout scenarios")
    print("3. Monitor metrics to tune timeout values")
    print("4. Use different timeouts for interactive vs background operations")
    print("5. Remember: timeout applies to entire stream duration")


if __name__ == "__main__":
    asyncio.run(main())
