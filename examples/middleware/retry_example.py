"""
Retry Middleware Example

This example demonstrates WHY and HOW to use retry middleware for handling
transient failures in agent communication.

WHY USE RETRY MIDDLEWARE?
-------------------------
- API rate limits: External services may temporarily reject requests
- Network instability: Transient network issues are common in distributed systems
- Service restarts: Backend services may be briefly unavailable during deployments
- Cost efficiency: Retrying is cheaper than failing and requiring manual intervention

WHEN TO USE:
- External API calls (LLM providers, databases, web services)
- Network-based agent communication
- Any operation with transient failure modes

WHEN NOT TO USE:
- Permanent errors (authentication failures, invalid input)
- Non-idempotent operations without safeguards
- Real-time systems where latency is critical
- Operations where failure is the expected result

TRADE-OFFS:
- Latency: Retries add delay (but exponential backoff minimizes this)
- Resource usage: Failed attempts consume resources
- Complexity: Need to distinguish transient vs permanent failures
"""

import asyncio
from agenkit.interfaces import Agent, Message
from agenkit.middleware import RetryConfig, RetryDecorator


# Simulate an unreliable external API
class UnreliableAPIAgent(Agent):
    """Simulates an agent that fails intermittently (like a real API)."""

    def __init__(self):
        self.attempt_count = 0

    @property
    def name(self) -> str:
        return "unreliable-api"

    @property
    def capabilities(self) -> list[str]:
        return ["translation"]

    async def process(self, message: Message) -> Message:
        self.attempt_count += 1

        # Simulate rate limiting on first 2 attempts
        if self.attempt_count <= 2:
            raise Exception("RateLimitError: Too many requests (429)")

        # Success on 3rd attempt
        return Message(
            role="agent",
            content=f"Translated: {message.content}",
            metadata={"attempts": self.attempt_count}
        )


async def example_basic_retry():
    """Example 1: Basic retry with exponential backoff."""
    print("\n=== Example 1: Basic Retry ===")
    print("Use case: External API with rate limiting\n")

    agent = UnreliableAPIAgent()

    # Wrap with retry middleware
    retry_agent = RetryDecorator(
        agent,
        RetryConfig(
            max_attempts=5,
            initial_backoff=0.5,  # Start with 500ms
            max_backoff=5.0,      # Cap at 5 seconds
            backoff_multiplier=2.0 # Double each time: 500ms, 1s, 2s, 4s, 5s
        )
    )

    message = Message(role="user", content="Hello, world!")

    try:
        print("Sending request (will fail twice, then succeed)...")
        response = await retry_agent.process(message)
        print(f"✅ Success: {response.content}")
        print(f"   Took {response.metadata.get('attempts', 0)} attempts")
    except Exception as e:
        print(f"❌ Failed after all retries: {e}")


async def example_custom_retry_logic():
    """Example 2: Custom retry logic for specific error types."""
    print("\n=== Example 2: Custom Retry Logic ===")
    print("Use case: Only retry on specific error types\n")

    class SmartAPIAgent(Agent):
        """Agent that returns different error types."""

        def __init__(self):
            self.call_count = 0

        @property
        def name(self) -> str:
            return "smart-api"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            self.call_count += 1

            if self.call_count == 1:
                # Transient error - should retry
                raise Exception("NetworkError: Connection timeout")
            elif self.call_count == 2:
                # Another transient error - should retry
                raise Exception("ServiceUnavailable: 503")
            else:
                # Success
                return Message(role="agent", content="Success!")

    # Custom retry predicate: only retry on specific errors
    def should_retry_error(error: Exception) -> bool:
        error_str = str(error)
        # Retry on network/service errors
        transient_errors = ["NetworkError", "ServiceUnavailable", "RateLimitError"]

        # Don't retry on auth/validation errors
        permanent_errors = ["AuthenticationError", "ValidationError", "NotFoundError"]

        # Check if it's a transient error
        is_transient = any(err in error_str for err in transient_errors)
        is_permanent = any(err in error_str for err in permanent_errors)

        if is_permanent:
            print(f"   ❌ Permanent error detected: {error_str}")
            return False
        elif is_transient:
            print(f"   🔄 Transient error detected: {error_str}")
            return True
        else:
            # Default: retry on unknown errors (conservative approach)
            print(f"   ⚠️  Unknown error, will retry: {error_str}")
            return True

    agent = SmartAPIAgent()
    retry_agent = RetryDecorator(
        agent,
        RetryConfig(
            max_attempts=3,
            initial_backoff=0.1,
            backoff_multiplier=2.0,
            should_retry=should_retry_error
        )
    )

    message = Message(role="user", content="test")

    print("Sending request with custom retry logic...")
    response = await retry_agent.process(message)
    print(f"✅ {response.content}")


async def example_no_retry_on_auth_error():
    """Example 3: Don't retry on authentication errors."""
    print("\n=== Example 3: No Retry on Auth Errors ===")
    print("Use case: Fail fast on permanent errors\n")

    class AuthFailAgent(Agent):
        @property
        def name(self) -> str:
            return "auth-fail"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            raise Exception("AuthenticationError: Invalid API key")

    def should_retry_error(error: Exception) -> bool:
        # Never retry authentication errors
        if "AuthenticationError" in str(error):
            return False
        return True

    agent = AuthFailAgent()
    retry_agent = RetryDecorator(
        agent,
        RetryConfig(
            max_attempts=3,
            initial_backoff=0.1,
            should_retry=should_retry_error
        )
    )

    message = Message(role="user", content="test")

    try:
        print("Sending request with auth error (should fail immediately)...")
        await retry_agent.process(message)
    except Exception as e:
        print(f"✅ Failed fast (no retries): {e}")
        print("   This is correct behavior - no point retrying auth errors!")


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("RETRY MIDDLEWARE EXAMPLES")
    print("="*60)
    print("\nThese examples show why retry middleware is essential for")
    print("building resilient distributed systems.\n")

    await example_basic_retry()
    await example_custom_retry_logic()
    await example_no_retry_on_auth_error()

    print("\n" + "="*60)
    print("KEY TAKEAWAYS")
    print("="*60)
    print("""
1. Always use retry for external API calls (LLMs, databases, web services)
2. Use exponential backoff to avoid overwhelming failing services
3. Implement custom retry logic to distinguish transient vs permanent errors
4. Fail fast on permanent errors (auth, validation) - don't waste retries
5. Configure max_backoff to prevent excessive delays
6. Monitor retry metrics to detect systemic issues
    """)


if __name__ == "__main__":
    asyncio.run(main())
