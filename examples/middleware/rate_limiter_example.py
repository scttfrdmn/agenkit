"""
Rate Limiter Middleware Example

This example demonstrates WHY and HOW to use rate limiter middleware for protecting
APIs and controlling costs in agent systems.

WHY USE RATE LIMITER MIDDLEWARE?
--------------------------------
- API quota protection: Stay within provider limits (OpenAI: 3500 RPM, Anthropic: 50 RPM)
- Cost control: Prevent runaway costs from aggressive agents or bugs
- Fair resource allocation: Ensure equal access across multiple tenants/users
- System stability: Prevent overwhelming downstream services
- SLA compliance: Maintain predictable performance under load

WHEN TO USE:
- LLM API calls with strict rate limits
- Multi-tenant systems requiring fair resource sharing
- Cost-sensitive operations (expensive embeddings, large context windows)
- Protecting third-party APIs from overload
- Systems with bursty traffic patterns

WHEN NOT TO USE:
- Single-user applications with generous quotas
- Internal services with no rate limits
- Latency-critical real-time systems
- Operations that must never wait

TRADE-OFFS:
- Latency: Requests may wait for tokens (but prevents hard failures)
- Complexity: Need to tune rate/capacity for each use case
- Throughput: Enforces maximum request rate (by design)
- Burst capacity: Balance between flexibility and protection
"""

import asyncio
from agenkit.interfaces import Agent, Message
from agenkit.middleware import RateLimiterConfig, RateLimiterDecorator


# Simulate a high-volume agent making many requests
class HighVolumeAgent(Agent):
    """Simulates an agent that makes many rapid requests."""

    def __init__(self, name: str = "high-volume-agent"):
        self._name = name
        self.request_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["text-generation"]

    async def process(self, message: Message) -> Message:
        self.request_count += 1
        # Simulate some processing time
        await asyncio.sleep(0.01)
        return Message(
            role="agent",
            content=f"Response {self.request_count}: {message.content}",
            metadata={"request_number": self.request_count}
        )


async def example_basic_rate_limiting():
    """Example 1: Basic rate limiting to protect API quotas."""
    print("\n=== Example 1: Basic Rate Limiting ===")
    print("Use case: OpenAI API with 3500 RPM limit (~58 RPS)\n")

    agent = HighVolumeAgent(name="openai-gpt4")

    # Configure for OpenAI's rate limit
    # 58 RPS = 58 tokens/second, with burst capacity of 100
    rate_limiter = RateLimiterDecorator(
        agent,
        RateLimiterConfig(
            rate=58.0,           # 58 tokens per second
            capacity=100,        # Allow bursts up to 100 requests
            tokens_per_request=1 # 1 token per request
        )
    )

    print("Sending 10 rapid requests to OpenAI API...")
    print("Rate limit: 58 RPS with burst capacity of 100\n")

    start_time = asyncio.get_event_loop().time()

    # Send 10 requests rapidly
    tasks = []
    for i in range(10):
        message = Message(role="user", content=f"Request {i+1}")
        tasks.append(rate_limiter.process(message))

    responses = await asyncio.gather(*tasks)

    elapsed = asyncio.get_event_loop().time() - start_time

    print(f"✅ Completed {len(responses)} requests in {elapsed:.2f}s")
    print(f"   Average: {len(responses)/elapsed:.1f} RPS")
    print(f"   Metrics: {rate_limiter.metrics.total_requests} total, "
          f"{rate_limiter.metrics.allowed_requests} allowed")
    print(f"   Current tokens: {rate_limiter.metrics.current_tokens:.1f}/{rate_limiter._config.capacity}")


async def example_burst_handling():
    """Example 2: Handling burst traffic with token bucket."""
    print("\n=== Example 2: Burst Handling ===")
    print("Use case: Anthropic API with 50 RPM limit (~0.83 RPS) but allowing bursts\n")

    agent = HighVolumeAgent(name="anthropic-claude")

    # Configure for Anthropic's rate limit
    # 50 RPM = 0.83 RPS, but allow bursts of 10 requests
    rate_limiter = RateLimiterDecorator(
        agent,
        RateLimiterConfig(
            rate=5.0,           # 5 requests per second for demo purposes
            capacity=10,        # Allow burst of 10 requests
            tokens_per_request=1
        )
    )

    print("Sending burst of 8 requests (should succeed immediately)...")
    start_time = asyncio.get_event_loop().time()

    # First burst - should succeed immediately (under capacity)
    tasks = [
        rate_limiter.process(Message(role="user", content=f"Burst {i+1}"))
        for i in range(8)
    ]
    responses = await asyncio.gather(*tasks)
    burst_time = asyncio.get_event_loop().time() - start_time

    print(f"✅ Burst completed in {burst_time:.2f}s (no waiting!)")
    print(f"   Tokens remaining: {rate_limiter.metrics.current_tokens:.1f}/{rate_limiter._config.capacity}")

    print("\nWaiting 2 seconds for token refill...")
    await asyncio.sleep(2)

    print("Sending 15 sequential requests (will rate limit)...")
    start_time = asyncio.get_event_loop().time()

    # Second burst - send sequentially to avoid race condition
    for i in range(15):
        await rate_limiter.process(Message(role="user", content=f"Request {i+1}"))

    wait_time = asyncio.get_event_loop().time() - start_time

    print(f"✅ Completed 15 requests in {wait_time:.2f}s (rate limited)")
    print(f"   Average: {15/wait_time:.2f} RPS (respects 5.0 RPS limit)")
    print(f"   Total wait time: {rate_limiter.metrics.total_wait_time:.2f}s")


async def example_weighted_rate_limiting():
    """Example 3: Weighted rate limiting for different request sizes."""
    print("\n=== Example 3: Weighted Rate Limiting ===")
    print("Use case: Cost-based limiting for different model sizes\n")

    class MultiModelAgent(Agent):
        """Agent that handles different model sizes."""

        def __init__(self):
            self.request_count = 0

        @property
        def name(self) -> str:
            return "multi-model"

        @property
        def capabilities(self) -> list[str]:
            return ["text-generation"]

        async def process(self, message: Message) -> Message:
            self.request_count += 1
            model = message.metadata.get("model", "small")
            await asyncio.sleep(0.01)
            return Message(
                role="agent",
                content=f"Response from {model} model",
                metadata={"model": model, "request_number": self.request_count}
            )

    # Small model: 1 token per request (fast, cheap)
    small_agent = MultiModelAgent()
    small_limiter = RateLimiterDecorator(
        small_agent,
        RateLimiterConfig(
            rate=10.0,           # 10 tokens/second
            capacity=20,         # Burst of 20
            tokens_per_request=1 # Small model = 1 token
        )
    )

    # Large model: 5 tokens per request (slow, expensive)
    large_agent = MultiModelAgent()
    large_limiter = RateLimiterDecorator(
        large_agent,
        RateLimiterConfig(
            rate=10.0,           # Same token rate
            capacity=20,         # Same capacity
            tokens_per_request=5 # Large model = 5 tokens (5x cost)
        )
    )

    print("Sending 10 requests to SMALL model (1 token each)...")
    start_time = asyncio.get_event_loop().time()
    for i in range(10):
        await small_limiter.process(Message(
            role="user",
            content=f"Small {i}",
            metadata={"model": "small"}
        ))
    small_time = asyncio.get_event_loop().time() - start_time

    print(f"✅ Small model: 10 requests in {small_time:.2f}s")

    print("\nSending 10 requests to LARGE model (5 tokens each)...")
    start_time = asyncio.get_event_loop().time()
    for i in range(10):
        await large_limiter.process(Message(
            role="user",
            content=f"Large {i}",
            metadata={"model": "large"}
        ))
    large_time = asyncio.get_event_loop().time() - start_time

    print(f"✅ Large model: 10 requests in {large_time:.2f}s")
    print(f"\n💡 Large model took {large_time/small_time:.1f}x longer due to 5x token cost")
    print("   This prevents expensive operations from consuming all resources!")


async def example_multi_tenant_fairness():
    """Example 4: Fair resource allocation across multiple tenants."""
    print("\n=== Example 4: Multi-Tenant Fairness ===")
    print("Use case: SaaS platform with different user tiers\n")

    base_agent = HighVolumeAgent()

    # Free tier: 5 requests per second, small burst
    free_tier = RateLimiterDecorator(
        base_agent,
        RateLimiterConfig(
            rate=5.0,            # 5 requests/second
            capacity=10,         # Small burst capacity
            tokens_per_request=1
        )
    )

    # Pro tier: 50 requests per second, large burst
    pro_tier = RateLimiterDecorator(
        base_agent,
        RateLimiterConfig(
            rate=50.0,           # 10x faster
            capacity=100,        # 10x burst capacity
            tokens_per_request=1
        )
    )

    print("Free tier user sending 20 requests...")
    start_time = asyncio.get_event_loop().time()
    for i in range(20):
        await free_tier.process(Message(role="user", content=f"Free {i}"))
    free_time = asyncio.get_event_loop().time() - start_time

    print(f"✅ Free tier: {free_time:.2f}s ({20/free_time:.1f} RPS)")

    print("\nPro tier user sending 20 requests...")
    start_time = asyncio.get_event_loop().time()
    for i in range(20):
        await pro_tier.process(Message(role="user", content=f"Pro {i}"))
    pro_time = asyncio.get_event_loop().time() - start_time

    print(f"✅ Pro tier: {pro_time:.2f}s ({20/pro_time:.1f} RPS)")
    print(f"\n💡 Pro tier is {free_time/pro_time:.1f}x faster - fair resource allocation!")
    print("   Free tier metrics:", free_tier.metrics)
    print("   Pro tier metrics: ", pro_tier.metrics)


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("RATE LIMITER MIDDLEWARE EXAMPLES")
    print("="*60)
    print("\nThese examples show how rate limiting protects APIs,")
    print("controls costs, and ensures fair resource allocation.\n")

    await example_basic_rate_limiting()
    await example_burst_handling()
    await example_weighted_rate_limiting()
    await example_multi_tenant_fairness()

    print("\n" + "="*60)
    print("KEY TAKEAWAYS")
    print("="*60)
    print("""
1. Rate limiting prevents API quota exhaustion and cost overruns
2. Token bucket algorithm allows bursts while maintaining average rate
3. Configure rate based on provider limits (OpenAI: 58 RPS, Anthropic: 0.83 RPS)
4. Use weighted tokens for cost-based limiting (expensive ops = more tokens)
5. Implement per-tenant limiters for fair multi-tenant resource sharing
6. Set capacity = 2-3x rate for good burst handling without over-provisioning
7. Monitor metrics (wait_time, rejected_requests) to tune configuration
8. Combine with retry middleware for complete resilience

RECOMMENDED CONFIGURATIONS:
- OpenAI GPT-4: rate=58, capacity=100, tokens_per_request=1
- Anthropic Claude: rate=0.83, capacity=10, tokens_per_request=1
- Embeddings (expensive): rate=10, capacity=20, tokens_per_request=5
- Free tier: rate=5, capacity=10, tokens_per_request=1
- Pro tier: rate=50, capacity=100, tokens_per_request=1
    """)


if __name__ == "__main__":
    asyncio.run(main())
