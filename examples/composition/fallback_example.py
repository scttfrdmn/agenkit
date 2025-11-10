"""
Fallback Composition Example

This example demonstrates WHY and HOW to use fallback composition for reliability,
cost optimization, and graceful degradation.

WHY USE FALLBACK COMPOSITION?
-----------------------------
1. Reliability: Handle service outages gracefully
2. Cost Optimization: Try cheap options before expensive ones
3. Graceful Degradation: Maintain functionality when primary fails
4. Quality Tiers: Premium → Standard → Basic fallback chain
5. Geographic Failover: Primary region → Secondary region
6. Rate Limit Handling: Switch to alternative when quota exceeded

WHEN TO USE:
- High-availability requirements (99.9%+ uptime)
- Multi-tier service offerings (premium/standard/free)
- Cost-sensitive applications (try free options first)
- Services with rate limits
- Multi-region deployments
- External API dependencies

WHEN NOT TO USE:
- All options must succeed (use SequentialAgent with validation)
- Need results from all options (use ParallelAgent)
- Fallback masks underlying issues (fix root cause instead)
- Performance requirements don't allow retry latency

TRADE-OFFS:
- Reliability: Much higher availability vs complexity
- Cost: Try cheaper options first vs potential quality reduction
- Latency: Additional retries add delay vs maintained functionality
- Complexity: Need to maintain multiple fallback implementations
"""

import asyncio
import random
from agenkit.interfaces import Agent, Message
from agenkit.composition import FallbackAgent


# Example 1: Cost-Optimized Fallback Chain
class PremiumLLMAgent(Agent):
    """Premium LLM (expensive, high quality, rate limited)."""

    def __init__(self):
        self.requests = 0
        self.quota = 5  # Limited quota

    @property
    def name(self) -> str:
        return "gpt-4"

    @property
    def capabilities(self) -> list[str]:
        return ["text_generation", "premium"]

    async def process(self, message: Message) -> Message:
        """Process with premium model."""
        self.requests += 1

        # Simulate rate limiting
        if self.requests > self.quota:
            raise Exception("Rate limit exceeded: GPT-4 quota exhausted")

        # Simulate premium processing
        await asyncio.sleep(0.3)

        return Message(
            role="agent",
            content=f"Premium response: High-quality analysis with detailed reasoning.",
            metadata={
                "model": "gpt-4",
                "cost": 0.03,
                "quality": 0.95
            }
        )


class StandardLLMAgent(Agent):
    """Standard LLM (moderate cost and quality)."""

    def __init__(self):
        self.failure_rate = 0.2  # Sometimes fails

    @property
    def name(self) -> str:
        return "gpt-3.5-turbo"

    @property
    def capabilities(self) -> list[str]:
        return ["text_generation", "standard"]

    async def process(self, message: Message) -> Message:
        """Process with standard model."""
        # Simulate occasional failures
        if random.random() < self.failure_rate:
            raise Exception("Service temporarily unavailable: 503")

        await asyncio.sleep(0.15)

        return Message(
            role="agent",
            content=f"Standard response: Good quality answer.",
            metadata={
                "model": "gpt-3.5-turbo",
                "cost": 0.002,
                "quality": 0.80
            }
        )


class BasicLLMAgent(Agent):
    """Basic LLM (cheap, always available, lower quality)."""

    @property
    def name(self) -> str:
        return "llama-3-8b"

    @property
    def capabilities(self) -> list[str]:
        return ["text_generation", "basic"]

    async def process(self, message: Message) -> Message:
        """Process with basic model."""
        # Always succeeds (local model)
        await asyncio.sleep(0.05)

        return Message(
            role="agent",
            content=f"Basic response: Simple answer.",
            metadata={
                "model": "llama-3-8b",
                "cost": 0.0,  # Self-hosted
                "quality": 0.65
            }
        )


async def example_cost_optimization():
    """Example 1: Cost-optimized fallback chain."""
    print("\n=== Example 1: Cost Optimization ===")
    print("Use case: Try cheap options before expensive ones\n")

    # Create fallback chain: Premium → Standard → Basic
    cost_optimizer = FallbackAgent(
        name="cost-optimized-llm",
        agents=[
            PremiumLLMAgent(),
            StandardLLMAgent(),
            BasicLLMAgent()
        ]
    )

    # Process multiple requests
    print("Processing 10 requests with cost optimization...")
    print("Strategy: Try GPT-4 → GPT-3.5 → Llama-3\n")

    total_cost = 0.0
    results = []

    for i in range(10):
        try:
            result = await cost_optimizer.process(
                Message(role="user", content=f"Request {i+1}: Analyze this")
            )
            model = result.metadata.get("model")
            cost = result.metadata.get("cost", 0)
            quality = result.metadata.get("quality", 0)

            total_cost += cost
            results.append((model, cost, quality))

            print(f"Request {i+1}: {model} (cost: ${cost:.4f}, quality: {quality:.2f})")

        except Exception as e:
            print(f"Request {i+1}: All fallbacks failed: {e}")

    # Analysis
    print(f"\n📊 Cost Analysis:")
    print(f"   Total Cost: ${total_cost:.4f}")
    print(f"   Average Cost per Request: ${total_cost/10:.4f}")

    # Count model usage
    model_usage = {}
    for model, _, _ in results:
        model_usage[model] = model_usage.get(model, 0) + 1

    print(f"\n   Model Distribution:")
    for model, count in sorted(model_usage.items()):
        print(f"     {model}: {count}/10 requests")

    print("\n💡 Cost Optimization Strategy:")
    print("   - First 5 requests: Use GPT-4 (within quota)")
    print("   - After quota: Fallback to GPT-3.5 (15× cheaper)")
    print("   - If GPT-3.5 fails: Fallback to local Llama (free)")
    print("   - Result: Maintain service with 50-90% cost savings")


# Example 2: High Availability with Geographic Failover
class RegionalServiceAgent(Agent):
    """Service in a specific region."""

    def __init__(self, region: str, failure_rate: float):
        self.region = region
        self.failure_rate = failure_rate

    @property
    def name(self) -> str:
        return f"service-{self.region}"

    @property
    def capabilities(self) -> list[str]:
        return ["processing"]

    async def process(self, message: Message) -> Message:
        """Process in specific region."""
        # Simulate regional outage
        if random.random() < self.failure_rate:
            raise Exception(f"Region {self.region} unavailable: Network timeout")

        await asyncio.sleep(0.1)

        return Message(
            role="agent",
            content=f"Processed in {self.region}",
            metadata={"region": self.region}
        )


async def example_geographic_failover():
    """Example 2: Geographic failover for high availability."""
    print("\n=== Example 2: Geographic Failover ===")
    print("Use case: Multi-region deployment for reliability\n")

    # Create geographic fallback: Primary → Secondary → Tertiary
    ha_service = FallbackAgent(
        name="ha-service",
        agents=[
            RegionalServiceAgent("us-east-1", failure_rate=0.3),
            RegionalServiceAgent("us-west-2", failure_rate=0.3),
            RegionalServiceAgent("eu-west-1", failure_rate=0.3)
        ]
    )

    print("Simulating 20 requests with 30% regional failure rate...")
    print("Regions: us-east-1 → us-west-2 → eu-west-1\n")

    region_usage = {}
    successes = 0

    for i in range(20):
        try:
            result = await ha_service.process(
                Message(role="user", content=f"Request {i+1}")
            )
            region = result.metadata.get("region")
            region_usage[region] = region_usage.get(region, 0) + 1
            successes += 1
        except Exception:
            pass

    print(f"📊 Availability Analysis:")
    print(f"   Successful Requests: {successes}/20 ({successes/20:.0%})")
    print(f"\n   Region Distribution:")
    for region, count in sorted(region_usage.items()):
        print(f"     {region}: {count} requests")

    # Calculate theoretical availability
    single_region_availability = 0.7  # 1 - 0.3 failure rate
    multi_region_availability = 1 - (0.3 ** 3)  # Probability at least one works

    print(f"\n💡 High Availability Benefits:")
    print(f"   Single Region: ~70% availability")
    print(f"   3 Regions:     ~97% availability")
    print(f"   Improvement:   27% → 99.9% uptime SLA achievable")


# Example 3: Quality Tiers with Graceful Degradation
class HighQualityAgent(Agent):
    """High quality but resource intensive."""

    @property
    def name(self) -> str:
        return "high-quality"

    @property
    def capabilities(self) -> list[str]:
        return ["analysis"]

    async def process(self, message: Message) -> Message:
        """High quality processing."""
        # Fail if system is under load
        if random.random() < 0.4:  # 40% failure under load
            raise Exception("System overloaded: High quality service unavailable")

        await asyncio.sleep(0.5)  # Expensive

        return Message(
            role="agent",
            content="Detailed analysis with citations, reasoning, and examples.",
            metadata={"quality": "high", "detail_level": 5}
        )


class MediumQualityAgent(Agent):
    """Medium quality, faster."""

    @property
    def name(self) -> str:
        return "medium-quality"

    @property
    def capabilities(self) -> list[str]:
        return ["analysis"]

    async def process(self, message: Message) -> Message:
        """Medium quality processing."""
        # More reliable
        if random.random() < 0.2:
            raise Exception("Service degraded")

        await asyncio.sleep(0.2)

        return Message(
            role="agent",
            content="Good analysis with key points.",
            metadata={"quality": "medium", "detail_level": 3}
        )


class LowQualityAgent(Agent):
    """Low quality but always available."""

    @property
    def name(self) -> str:
        return "low-quality"

    @property
    def capabilities(self) -> list[str]:
        return ["analysis"]

    async def process(self, message: Message) -> Message:
        """Low quality processing."""
        # Always succeeds
        await asyncio.sleep(0.05)

        return Message(
            role="agent",
            content="Basic summary.",
            metadata={"quality": "low", "detail_level": 1}
        )


async def example_graceful_degradation():
    """Example 3: Graceful degradation with quality tiers."""
    print("\n=== Example 3: Graceful Degradation ===")
    print("Use case: Maintain service quality during high load\n")

    quality_fallback = FallbackAgent(
        name="adaptive-quality",
        agents=[
            HighQualityAgent(),
            MediumQualityAgent(),
            LowQualityAgent()
        ]
    )

    print("Processing 15 requests under variable load...")
    print("Quality tiers: High → Medium → Low\n")

    quality_counts = {"high": 0, "medium": 0, "low": 0}

    for i in range(15):
        result = await quality_fallback.process(
            Message(role="user", content=f"Request {i+1}")
        )
        quality = result.metadata.get("quality")
        quality_counts[quality] += 1
        detail = result.metadata.get("detail_level")

        print(f"Request {i+1}: {quality} quality (detail level: {detail})")

    print(f"\n📊 Quality Distribution:")
    print(f"   High:   {quality_counts['high']}/15 ({quality_counts['high']/15:.0%})")
    print(f"   Medium: {quality_counts['medium']}/15 ({quality_counts['medium']/15:.0%})")
    print(f"   Low:    {quality_counts['low']}/15 ({quality_counts['low']/15:.0%})")

    print("\n💡 Graceful Degradation:")
    print("   - System overload → Reduce quality, not availability")
    print("   - Users get *some* response (better than error)")
    print("   - Can show quality indicator to user")
    print("   - Automatically recovers when load decreases")


# Example 4: Handling Different Failure Modes
class AuthenticatedAgent(Agent):
    """Agent that requires authentication."""

    @property
    def name(self) -> str:
        return "authenticated-service"

    @property
    def capabilities(self) -> list[str]:
        return ["secure_processing"]

    async def process(self, message: Message) -> Message:
        """Process with authentication."""
        # Check authentication
        if not message.metadata.get("auth_token"):
            raise Exception("Authentication failed: Missing token")

        await asyncio.sleep(0.1)

        return Message(
            role="agent",
            content="Secure response from authenticated service",
            metadata={"authenticated": True}
        )


class PublicAgent(Agent):
    """Public agent, no auth required."""

    @property
    def name(self) -> str:
        return "public-service"

    @property
    def capabilities(self) -> list[str]:
        return ["public_processing"]

    async def process(self, message: Message) -> Message:
        """Process without authentication."""
        await asyncio.sleep(0.1)

        return Message(
            role="agent",
            content="Public response (limited functionality)",
            metadata={"authenticated": False}
        )


async def example_auth_fallback():
    """Example 4: Fallback on authentication failure."""
    print("\n=== Example 4: Authentication Fallback ===")
    print("Use case: Graceful degradation for unauthenticated users\n")

    auth_fallback = FallbackAgent(
        name="auth-fallback",
        agents=[
            AuthenticatedAgent(),
            PublicAgent()
        ]
    )

    # Test with auth token
    print("Test 1: With authentication")
    result = await auth_fallback.process(
        Message(
            role="user",
            content="Request",
            metadata={"auth_token": "valid_token"}
        )
    )
    print(f"  Result: {result.content}")
    print(f"  Authenticated: {result.metadata.get('authenticated')}")

    # Test without auth token
    print("\nTest 2: Without authentication")
    result = await auth_fallback.process(
        Message(role="user", content="Request")
    )
    print(f"  Result: {result.content}")
    print(f"  Authenticated: {result.metadata.get('authenticated')}")

    print("\n💡 Auth Fallback Pattern:")
    print("   - Try authenticated service first (full features)")
    print("   - Fallback to public service (limited features)")
    print("   - Better than showing error to user")
    print("   - Can prompt user to authenticate for full access")


# Example 5: Circuit Breaker Pattern
class UnstableServiceAgent(Agent):
    """Service that degrades over time."""

    def __init__(self):
        self.failures = 0

    @property
    def name(self) -> str:
        return "unstable-service"

    @property
    def capabilities(self) -> list[str]:
        return ["processing"]

    async def process(self, message: Message) -> Message:
        """Process with increasing failure rate."""
        self.failures += 1

        # Increase failure rate over time
        failure_rate = min(0.8, self.failures * 0.1)

        if random.random() < failure_rate:
            raise Exception(f"Service degrading: {failure_rate:.0%} failure rate")

        await asyncio.sleep(0.1)

        return Message(
            role="agent",
            content="Response from primary service",
            metadata={"service": "primary"}
        )


class StableBackupAgent(Agent):
    """Stable backup service."""

    @property
    def name(self) -> str:
        return "backup-service"

    @property
    def capabilities(self) -> list[str]:
        return ["processing"]

    async def process(self, message: Message) -> Message:
        """Reliable backup processing."""
        await asyncio.sleep(0.15)

        return Message(
            role="agent",
            content="Response from backup service",
            metadata={"service": "backup"}
        )


async def example_circuit_breaker():
    """Example 5: Circuit breaker pattern with fallback."""
    print("\n=== Example 5: Circuit Breaker Pattern ===")
    print("Use case: Protect system from cascading failures\n")

    circuit_breaker = FallbackAgent(
        name="circuit-breaker",
        agents=[
            UnstableServiceAgent(),
            StableBackupAgent()
        ]
    )

    print("Processing requests as primary service degrades...")
    print("Primary service failure rate increases: 10% → 20% → ... → 80%\n")

    primary_count = 0
    backup_count = 0

    for i in range(10):
        result = await circuit_breaker.process(
            Message(role="user", content=f"Request {i+1}")
        )
        service = result.metadata.get("service")

        if service == "primary":
            primary_count += 1
            print(f"Request {i+1}: ✅ Primary service")
        else:
            backup_count += 1
            print(f"Request {i+1}: 🔄 Backup service (primary failed)")

    print(f"\n📊 Service Usage:")
    print(f"   Primary: {primary_count}/10 requests")
    print(f"   Backup:  {backup_count}/10 requests")

    print("\n💡 Circuit Breaker Benefits:")
    print("   - Automatically routes to healthy service")
    print("   - Prevents cascading failures")
    print("   - System remains operational despite primary failure")
    print("   - Can add smart circuit breaker logic (failure thresholds)")


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("FALLBACK COMPOSITION EXAMPLES")
    print("="*70)
    print("\nFallback composition builds reliable systems through redundancy.")
    print("Try agents in order until one succeeds.\n")

    await example_cost_optimization()
    await example_geographic_failover()
    await example_graceful_degradation()
    await example_auth_fallback()
    await example_circuit_breaker()

    print("\n" + "="*70)
    print("KEY TAKEAWAYS")
    print("="*70)
    print("""
1. Use fallback composition when:
   - High availability is critical (99.9%+ uptime)
   - Have multiple tiers of service quality
   - Cost optimization through cheaper alternatives
   - External dependencies may fail
   - Geographic redundancy needed

2. Fallback ordering strategies:
   - Cost: Cheap → Expensive (optimize cost)
   - Quality: High → Low (graceful degradation)
   - Reliability: Primary → Secondary → Tertiary (HA)
   - Speed: Fast → Slow (optimize latency first)

3. Reliability math:
   - Single service: 90% → 90% availability
   - 2-tier fallback: 90% + 10% × 90% = 99% availability
   - 3-tier fallback: 99% + 1% × 90% = 99.9% availability
   - Each tier adds "nines" to your SLA

4. When NOT to use:
   - Fallback masks root cause issues
   - All options must execute (use ParallelAgent)
   - Latency from retries unacceptable
   - No meaningful alternatives available

5. Best practices:
   - Order by: cost, quality, or reliability (pick one)
   - Monitor which tier is used (detect degradation)
   - Set up alerts when using fallbacks frequently
   - Log why primary failed (debug root cause)
   - Consider circuit breaker for repeated failures

REAL-WORLD PATTERNS:
✅ Multi-region: us-east → us-west → eu-west
✅ Cost tiers: GPT-4 → GPT-3.5 → local model
✅ Quality: Premium → standard → basic
✅ Auth: Authenticated → public service
✅ Circuit breaker: Primary → backup

TRADE-OFF SUMMARY:
✅ Pros: High availability, cost optimization, graceful degradation
❌ Cons: Latency from retries, masks underlying issues
🎯 Choose when: Reliability requirements > latency sensitivity
    """)


if __name__ == "__main__":
    asyncio.run(main())
