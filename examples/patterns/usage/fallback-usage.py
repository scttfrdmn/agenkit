"""
Fallback Pattern Usage Example.

Demonstrates the Fallback pattern for sequential retry across multiple agents
with automatic failover and recovery strategies.

Use cases:
- Resilient service calls
- Multi-provider fallback
- Progressive degradation
- Error recovery

This example shows:
- Sequential fallback chain
- Recovery strategies
- Partial failure handling
- Fallback metadata tracking
"""

import asyncio
import random

from agenkit.core import Agent, Message
from agenkit.patterns import FallbackAgent, default_recovery, with_recovery


class PrimaryServiceAgent(Agent):
    """Primary service that may fail."""

    def __init__(self, failure_rate: float = 0.5):
        self._failure_rate = failure_rate

    def name(self) -> str:
        return "PrimaryService"

    def capabilities(self) -> list[str]:
        return ["primary", "high-quality"]

    async def process(self, message: Message) -> Message:
        """Process with possible failure."""
        print("   🎯 Trying primary service...")
        await asyncio.sleep(0.1)

        # Simulate intermittent failures
        if random.random() < self._failure_rate:
            raise RuntimeError("Primary service unavailable")

        result = Message(
            role="agent",
            content=f"Primary service response: High quality result for '{message.content}'",
        )
        result.metadata["service"] = "primary"
        result.metadata["quality"] = "high"
        return result


class SecondaryServiceAgent(Agent):
    """Secondary backup service."""

    def __init__(self, failure_rate: float = 0.3):
        self._failure_rate = failure_rate

    def name(self) -> str:
        return "SecondaryService"

    def capabilities(self) -> list[str]:
        return ["secondary", "medium-quality"]

    async def process(self, message: Message) -> Message:
        """Process with lower failure rate."""
        print("   🔄 Trying secondary service...")
        await asyncio.sleep(0.08)

        if random.random() < self._failure_rate:
            raise RuntimeError("Secondary service unavailable")

        result = Message(
            role="agent",
            content=f"Secondary service response: Medium quality result for '{message.content}'",
        )
        result.metadata["service"] = "secondary"
        result.metadata["quality"] = "medium"
        return result


class FallbackServiceAgent(Agent):
    """Last resort fallback service."""

    def name(self) -> str:
        return "FallbackService"

    def capabilities(self) -> list[str]:
        return ["fallback", "basic"]

    async def process(self, message: Message) -> Message:
        """Always succeeds with basic result."""
        print("   ⚠️  Using fallback service...")
        await asyncio.sleep(0.05)

        result = Message(
            role="agent",
            content=f"Fallback service response: Basic result for '{message.content}'",
        )
        result.metadata["service"] = "fallback"
        result.metadata["quality"] = "basic"
        return result


class CachedAgent(Agent):
    """Agent with caching capability."""

    def __init__(self):
        self._cache = {}

    def name(self) -> str:
        return "CachedAgent"

    def capabilities(self) -> list[str]:
        return ["caching", "fast"]

    async def process(self, message: Message) -> Message:
        """Check cache first."""
        cache_key = message.content[:20]  # Simple key

        if cache_key in self._cache:
            print("   💾 Cache hit!")
            result = Message(
                role="agent",
                content=self._cache[cache_key],
            )
            result.metadata["cached"] = True
            return result

        # Cache miss - fail to trigger fallback
        print("   ❌ Cache miss - no data available")
        raise RuntimeError("Cache miss")


class APIAgent(Agent):
    """API service agent."""

    def __init__(self, name_suffix: str, success_rate: float = 0.7):
        self._name_suffix = name_suffix
        self._success_rate = success_rate

    def name(self) -> str:
        return f"API_{self._name_suffix}"

    def capabilities(self) -> list[str]:
        return ["api", "external"]

    async def process(self, message: Message) -> Message:
        """Call external API."""
        print(f"   🌐 Calling {self.name()}...")
        await asyncio.sleep(0.1)

        if random.random() > self._success_rate:
            raise RuntimeError(f"{self.name()} timeout")

        result = Message(
            role="agent",
            content=f"{self.name()} response: Data retrieved",
        )
        result.metadata["api"] = self._name_suffix
        return result


async def basic_fallback():
    """Demonstrate basic fallback chain."""
    print("=" * 60)
    print("Example 1: Basic Fallback Chain")
    print("=" * 60)

    # Create fallback chain
    fallback = FallbackAgent([
        PrimaryServiceAgent(failure_rate=0.8),  # High failure rate
        SecondaryServiceAgent(failure_rate=0.5),  # Medium failure rate
        FallbackServiceAgent(),  # Always succeeds
    ])

    message = Message(role="user", content="Process this request")

    print(f"\n📥 Request: {message.content}\n")

    result = await fallback.process(message)

    print(f"\n📤 Result: {result.content}")
    print("\nFallback Details:")
    print(f"   Service used: {result.metadata.get('service')}")
    print(f"   Quality: {result.metadata.get('quality')}")
    print(f"   Attempts: {result.metadata.get('attempts', 0)}")


async def multi_attempt_fallback():
    """Demonstrate multiple fallback attempts."""
    print("\n\n" + "=" * 60)
    print("Example 2: Multiple Retry Attempts")
    print("=" * 60)

    # Try multiple times with fallback
    attempts = 3
    for i in range(attempts):
        print(f"\n--- Attempt {i + 1} of {attempts} ---")

        fallback = FallbackAgent([
            PrimaryServiceAgent(failure_rate=0.7),
            SecondaryServiceAgent(failure_rate=0.4),
            FallbackServiceAgent(),
        ])

        message = Message(role="user", content=f"Request {i + 1}")
        result = await fallback.process(message)

        print(f"✓ Success using: {result.metadata.get('service')}")


async def cache_with_fallback():
    """Demonstrate cache with API fallback."""
    print("\n\n" + "=" * 60)
    print("Example 3: Cache with API Fallback")
    print("=" * 60)

    # Cache -> API fallback
    fallback = FallbackAgent([
        CachedAgent(),
        APIAgent("Primary", success_rate=0.8),
        APIAgent("Backup", success_rate=0.9),
    ])

    # First request (cache miss, will use API)
    message1 = Message(role="user", content="Get user data for ID:12345")

    print(f"\n📥 Request 1: {message1.content}")
    result1 = await fallback.process(message1)

    print(f"📤 {result1.content}")
    print(f"   Cached: {result1.metadata.get('cached', False)}")
    print(f"   API: {result1.metadata.get('api', 'none')}")


async def recovery_strategies():
    """Demonstrate custom recovery strategies."""
    print("\n\n" + "=" * 60)
    print("Example 4: Custom Recovery Strategies")
    print("=" * 60)

    class RetryWithBackoffAgent(Agent):
        """Agent that fails but can be retried."""

        def __init__(self):
            self.attempts = 0

        def name(self) -> str:
            return "RetryAgent"

        def capabilities(self) -> list[str]:
            return ["retry", "backoff"]

        async def process(self, message: Message) -> Message:
            self.attempts += 1
            print(f"   🔄 Retry attempt {self.attempts}...")

            if self.attempts < 2:
                # Fail first attempt
                raise RuntimeError("Temporary failure")

            # Succeed on retry
            result = Message(
                role="agent",
                content=f"Success after {self.attempts} attempts",
            )
            result.metadata["attempts"] = self.attempts
            return result

    # Wrap with recovery
    retry_agent = RetryWithBackoffAgent()
    recovered = with_recovery(retry_agent, default_recovery)

    # Add fallback chain
    fallback = FallbackAgent([
        recovered,  # Will retry
        FallbackServiceAgent(),  # Ultimate fallback
    ])

    message = Message(role="user", content="Retry this request")

    print(f"\n📥 Request: {message.content}\n")

    result = await fallback.process(message)

    print(f"\n📤 {result.content}")


async def error_aggregation():
    """Demonstrate error tracking across fallbacks."""
    print("\n\n" + "=" * 60)
    print("Example 5: Error Tracking")
    print("=" * 60)

    # All services fail except last one
    fallback = FallbackAgent([
        PrimaryServiceAgent(failure_rate=1.0),  # Always fails
        SecondaryServiceAgent(failure_rate=1.0),  # Always fails
        FallbackServiceAgent(),  # Succeeds
    ])

    message = Message(role="user", content="Test error tracking")

    print(f"\n📥 Request: {message.content}\n")

    result = await fallback.process(message)

    print(f"\n📤 Final result: {result.content}")
    print("\nError Summary:")
    print(f"   Total attempts: {result.metadata.get('attempts', 0)}")
    print(f"   Successful service: {result.metadata.get('service')}")
    if "errors" in result.metadata:
        print(f"   Errors encountered: {len(result.metadata['errors'])}")
        for error in result.metadata["errors"]:
            print(f"     - {error.get('agent')}: {error.get('error')}")


async def main():
    """Run all examples."""
    print("\n⚡ Fallback Pattern Usage Examples\n")

    # Set random seed for reproducibility
    random.seed(42)

    await basic_fallback()
    await multi_attempt_fallback()
    await cache_with_fallback()
    await recovery_strategies()
    await error_aggregation()

    print("\n✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
