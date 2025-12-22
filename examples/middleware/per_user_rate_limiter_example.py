"""
Example demonstrating per-user rate limiting.

Shows how to use per-user rate limiting to prevent individual users from
consuming the entire system quota while maintaining fair access for all users.
"""

import asyncio

from agenkit.interfaces import Message
from agenkit.middleware import (
    PerUserRateLimiterConfig,
    PerUserRateLimiterDecorator,
    PerUserRateLimitError,
)


# Simple echo agent for demonstration
class EchoAgent:
    """Simple agent that echoes back messages."""

    @property
    def name(self):
        return "echo"

    @property
    def capabilities(self):
        return ["echo"]

    async def process(self, message):
        return Message(role="assistant", content=f"Echo: {message.content}")


async def main():
    """Demonstrate per-user rate limiting."""
    print("=== Per-User Rate Limiting Example ===\n")

    # Define user identifier function
    def get_user_id(message):
        return message.metadata.get("user_id", "anonymous")

    # Example 1: Basic per-user rate limiting
    print("1. Basic Per-User Rate Limiting")
    print("-" * 50)

    config = PerUserRateLimiterConfig(
        user_rate=2.0,  # 2 requests per second per user
        user_capacity=3,  # Burst of 3 requests
        identifier_fn=get_user_id,
        cleanup_interval=0,  # Disable cleanup for demo
    )

    agent = EchoAgent()
    limited_agent = PerUserRateLimiterDecorator(agent, config)

    # Alice makes requests (should work up to capacity)
    print("Alice making 3 requests (within limit)...")
    for i in range(3):
        message = Message(
            role="user",
            content=f"Request {i+1}",
            metadata={"user_id": "alice"},
        )
        response = await limited_agent.process(message)
        print(f"  ✓ {response.content}")

    # Alice's 4th request should be rate limited
    print("\nAlice making 4th request (should fail)...")
    try:
        message = Message(
            role="user",
            content="Request 4",
            metadata={"user_id": "alice"},
        )
        await limited_agent.process(message)
        print("  ✗ Should have been rate limited!")
    except PerUserRateLimitError as e:
        print(f"  ✓ Rate limited: {e}")

    # Bob should have separate limit
    print("\nBob making request (separate limit)...")
    message = Message(
        role="user",
        content="Hello",
        metadata={"user_id": "bob"},
    )
    response = await limited_agent.process(message)
    print(f"  ✓ {response.content}")

    print("\nMetrics:")
    print(f"  Total requests: {limited_agent.metrics.total_requests}")
    print(f"  Allowed: {limited_agent.metrics.allowed_requests}")
    print(f"  Rejected (user limit): {limited_agent.metrics.rejected_user_limit}")
    print(f"  Active users: {limited_agent.metrics.active_users}")
    print()

    # Example 2: Per-user + global rate limiting
    print("2. Per-User + Global Rate Limiting")
    print("-" * 50)

    config2 = PerUserRateLimiterConfig(
        user_rate=5.0,  # 5 requests/sec per user
        user_capacity=10,
        global_rate=8.0,  # 8 requests/sec total across all users
        global_capacity=12,
        identifier_fn=get_user_id,
        cleanup_interval=0,
    )

    limited_agent2 = PerUserRateLimiterDecorator(EchoAgent(), config2)

    # Multiple users making requests rapidly
    print("Alice, Bob, and Charlie making requests simultaneously...")

    users = ["alice", "bob", "charlie"]
    allowed = 0
    rate_limited = 0

    for i in range(15):  # Try 15 requests total
        user = users[i % 3]
        message = Message(
            role="user",
            content=f"Request {i+1}",
            metadata={"user_id": user},
        )

        try:
            await limited_agent2.process(message)
            allowed += 1
            print(f"  ✓ {user}: Request {i+1} allowed")
        except Exception as e:
            rate_limited += 1
            print(f"  ✗ {user}: Request {i+1} rate limited ({type(e).__name__})")

    print(f"\nResults: {allowed} allowed, {rate_limited} rate limited")
    print("Metrics:")
    print(f"  Per-user rejections: {limited_agent2.metrics.rejected_user_limit}")
    print(f"  Global rejections: {limited_agent2.metrics.rejected_global_limit}")
    print()

    # Example 3: Different identifiers (API key, IP address)
    print("3. Rate Limiting by API Key")
    print("-" * 50)

    def get_api_key(message):
        return message.metadata.get("api_key", "no_key")

    config3 = PerUserRateLimiterConfig(
        user_rate=3.0,
        user_capacity=3,
        identifier_fn=get_api_key,
        cleanup_interval=0,
    )

    limited_agent3 = PerUserRateLimiterDecorator(EchoAgent(), config3)

    # Different API keys
    print("Requests from different API keys...")
    for api_key in ["key_123", "key_456", "key_123"]:
        message = Message(
            role="user",
            content="Hello",
            metadata={"api_key": api_key},
        )
        try:
            response = await limited_agent3.process(message)
            print(f"  ✓ {api_key}: {response.content}")
        except PerUserRateLimitError as e:
            print(f"  ✗ {api_key}: Rate limited")

    print()

    # Example 4: Integration with audit logging
    print("4. Integration with Audit Logging")
    print("-" * 50)

    from agenkit.observability import AuditLogger

    # Create audit logger
    audit = AuditLogger()  # Uses console adapter by default

    config4 = PerUserRateLimiterConfig(
        user_rate=1.0,  # Very strict limit for demo
        user_capacity=1,
        identifier_fn=get_user_id,
        cleanup_interval=0,
    )

    limited_agent4 = PerUserRateLimiterDecorator(EchoAgent(), config4, audit_logger=audit)

    print("Making requests that will be rate limited...")
    message1 = Message(role="user", content="First", metadata={"user_id": "alice"})
    await limited_agent4.process(message1)  # Should work
    print("  ✓ First request allowed")

    try:
        message2 = Message(role="user", content="Second", metadata={"user_id": "alice"})
        await limited_agent4.process(message2)  # Should fail
    except PerUserRateLimitError:
        print("  ✓ Second request rate limited (logged to audit)")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
