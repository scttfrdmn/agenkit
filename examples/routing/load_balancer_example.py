"""
Load Balancer Router Example

Demonstrates distributing requests across multiple agent instances for:
- Better resource utilization
- Higher throughput
- Fault tolerance
- Scalability

This example shows:
1. Round-robin load balancing
2. Least-connections strategy
3. Weighted distribution
4. Health monitoring and metrics
"""

import asyncio
import time

from agenkit.interfaces import Message
from agenkit.routing.load_balancer import (
    AgentInstance,
    LoadBalancerRouter,
    LoadBalancingStrategy,
)


# Simple echo agent for demonstration
class EchoAgent:
    """Mock agent that echoes messages with simulated delay."""

    def __init__(self, name: str, processing_delay: float = 0.1):
        self._name = name
        self.processing_delay = processing_delay
        self.processed_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["echo"]

    async def process(self, message: Message) -> Message:
        """Process message with simulated work."""
        self.processed_count += 1
        await asyncio.sleep(self.processing_delay)
        return Message(
            role="assistant",
            content=f"[{self._name}] Processed: {message.content}",
        )


async def example_1_round_robin():
    """Example 1: Round-robin load balancing."""
    print("=" * 60)
    print("Example 1: Round-Robin Load Balancing")
    print("=" * 60)

    # Create 3 agent instances
    instances = [
        AgentInstance(
            agent=EchoAgent("agent-1", processing_delay=0.05),
            weight=1.0,
            max_concurrent=5,
        ),
        AgentInstance(
            agent=EchoAgent("agent-2", processing_delay=0.05),
            weight=1.0,
            max_concurrent=5,
        ),
        AgentInstance(
            agent=EchoAgent("agent-3", processing_delay=0.05),
            weight=1.0,
            max_concurrent=5,
        ),
    ]

    # Create load balancer
    balancer = LoadBalancerRouter(instances=instances, strategy=LoadBalancingStrategy.ROUND_ROBIN)

    print("\n🔄 Sending 9 requests with round-robin distribution...")

    # Send requests
    for i in range(9):
        message = Message(role="user", content=f"Request {i + 1}")
        await balancer.process(message)

    # Show distribution
    print("\n📊 Request Distribution:")
    for instance in instances:
        agent = instance.agent
        print(f"  {agent.name}: {agent.processed_count} requests")

    print("\n✅ Round-robin ensures even distribution (3 requests per instance)")


async def example_2_least_connections():
    """Example 2: Least-connections strategy."""
    print("\n" + "=" * 60)
    print("Example 2: Least-Connections Strategy")
    print("=" * 60)

    # Create instances with different speeds
    instances = [
        AgentInstance(
            agent=EchoAgent("fast-1", processing_delay=0.01),
            max_concurrent=10,
        ),
        AgentInstance(
            agent=EchoAgent("fast-2", processing_delay=0.01),
            max_concurrent=10,
        ),
        AgentInstance(
            agent=EchoAgent("slow-1", processing_delay=0.2),
            max_concurrent=10,
        ),
    ]

    balancer = LoadBalancerRouter(
        instances=instances, strategy=LoadBalancingStrategy.LEAST_CONNECTIONS
    )

    print("\n⚡ Sending 20 concurrent requests...")
    print("Least-connections routes to instances with fewest active requests")

    # Send concurrent requests
    tasks = []
    for i in range(20):
        message = Message(role="user", content=f"Request {i + 1}")
        tasks.append(balancer.process(message))

    start = time.time()
    await asyncio.gather(*tasks)
    elapsed = time.time() - start

    # Show results
    print(f"\n✓ Completed all requests in {elapsed:.2f}s")
    print("\n📊 Request Distribution:")
    for instance in instances:
        agent = instance.agent
        print(f"  {agent.name}: {agent.processed_count} requests")

    print("\n✅ Fast agents processed more requests (better utilization)")


async def example_3_weighted_distribution():
    """Example 3: Weighted round-robin."""
    print("\n" + "=" * 60)
    print("Example 3: Weighted Distribution")
    print("=" * 60)

    # Create instances with different capacities
    instances = [
        AgentInstance(
            agent=EchoAgent("small", processing_delay=0.05),
            weight=1.0,  # Standard capacity
            max_concurrent=10,
        ),
        AgentInstance(
            agent=EchoAgent("large", processing_delay=0.05),
            weight=3.0,  # 3x capacity
            max_concurrent=30,
        ),
        AgentInstance(
            agent=EchoAgent("medium", processing_delay=0.05),
            weight=2.0,  # 2x capacity
            max_concurrent=20,
        ),
    ]

    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
    )

    print("\n⚖️  Instance Capacities:")
    print("  small:  weight=1.0 (baseline)")
    print("  large:  weight=3.0 (3x more powerful)")
    print("  medium: weight=2.0 (2x more powerful)")

    print("\n📨 Sending 60 requests...")

    for i in range(60):
        message = Message(role="user", content=f"Request {i + 1}")
        await balancer.process(message)

    # Show distribution
    print("\n📊 Request Distribution:")
    for instance in instances:
        agent = instance.agent
        percentage = (agent.processed_count / 60) * 100
        print(
            f"  {agent.name:8} (weight={instance.weight}): {agent.processed_count:2} requests ({percentage:.0f}%)"
        )

    print("\n✅ Weighted distribution matches capacity (1:2:3 ratio)")


async def example_4_health_monitoring():
    """Example 4: Health monitoring and metrics."""
    print("\n" + "=" * 60)
    print("Example 4: Health Monitoring & Metrics")
    print("=" * 60)

    instances = [
        AgentInstance(
            agent=EchoAgent("instance-1", processing_delay=0.05),
            max_concurrent=5,
        ),
        AgentInstance(
            agent=EchoAgent("instance-2", processing_delay=0.1),
            max_concurrent=5,
        ),
    ]

    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.LEAST_RESPONSE_TIME,
    )

    print("\n📊 Initial Statistics:")
    stats = balancer.get_statistics()
    print(f"  Total instances: {stats['total_instances']}")
    print(f"  Enabled: {stats['enabled_instances']}")
    print(f"  Strategy: {stats['strategy']}")

    print("\n📨 Processing requests...")
    for i in range(10):
        message = Message(role="user", content=f"Request {i + 1}")
        await balancer.process(message)

    print("\n📈 Per-Instance Metrics:")
    stats = balancer.get_statistics()
    for inst_stats in stats["instances"]:
        print(f"\n  {inst_stats['name']}:")
        print(f"    Total requests: {inst_stats['total_requests']}")
        print(f"    Success rate: {inst_stats['success_rate']:.2%}")
        print(f"    Avg response time: {inst_stats['avg_response_time']:.3f}s")
        print(f"    Load factor: {inst_stats['load_factor']:.2f}")

    print(f"\n📊 Overall Success Rate: {stats['overall_success_rate']:.2%}")


async def example_5_dynamic_scaling():
    """Example 5: Dynamic instance management."""
    print("\n" + "=" * 60)
    print("Example 5: Dynamic Scaling")
    print("=" * 60)

    # Start with 2 instances
    instances = [
        AgentInstance(agent=EchoAgent("instance-1"), max_concurrent=5),
        AgentInstance(agent=EchoAgent("instance-2"), max_concurrent=5),
    ]

    balancer = LoadBalancerRouter(
        instances=instances, strategy=LoadBalancingStrategy.LEAST_CONNECTIONS
    )

    print(f"\n📦 Starting with {len(balancer.instances)} instances")

    # Process some requests
    print("📨 Processing initial batch...")
    for i in range(10):
        await balancer.process(Message(role="user", content=f"Request {i + 1}"))

    # Scale up - add instance
    print("\n⬆️  Scaling up: Adding instance-3...")
    new_instance = AgentInstance(agent=EchoAgent("instance-3"), max_concurrent=5)
    balancer.add_instance(new_instance)

    print(f"✓ Now have {len(balancer.instances)} instances")

    # Process more requests
    print("\n📨 Processing with scaled infrastructure...")
    for i in range(15):
        await balancer.process(Message(role="user", content=f"Request {i + 1}"))

    # Show distribution
    print("\n📊 Final Distribution:")
    for instance in balancer.instances:
        agent = instance.agent
        print(f"  {agent.name}: {agent.processed_count} requests")

    # Scale down - remove instance
    print("\n⬇️  Scaling down: Removing instance-2...")
    balancer.remove_instance("instance-2")

    print(f"✓ Now have {len(balancer.instances)} instances")


async def example_6_production_patterns():
    """Example 6: Production deployment patterns."""
    print("\n" + "=" * 60)
    print("Example 6: Production Patterns")
    print("=" * 60)

    print(
        """
💡 Production Best Practices:

1. **Configure Appropriate Capacities**:
   instances = [
       AgentInstance(
           agent=gpu_agent,
           weight=2.0,          # More powerful
           max_concurrent=20,   # Higher capacity
       ),
       AgentInstance(
           agent=cpu_agent,
           weight=1.0,          # Standard
           max_concurrent=10,
       ),
   ]

2. **Choose Right Strategy**:
   - LEAST_CONNECTIONS: Best for long-running requests
   - LEAST_RESPONSE_TIME: Best when agents have different speeds
   - WEIGHTED_ROUND_ROBIN: Best for known capacity differences
   - ROUND_ROBIN: Simple and fair

3. **Enable Health Checks**:
   balancer = LoadBalancerRouter(instances, strategy)
   await balancer.start_health_checks()  # Background monitoring

   # Disable failing instances automatically
   # Re-enable when they recover

4. **Monitor Metrics**:
   stats = balancer.get_statistics()

   # Alert on:
   # - Low success rate
   # - High response times
   # - Disabled instances
   # - Uneven load distribution

5. **Handle Instance Failures**:
   try:
       response = await balancer.process(message)
   except LoadBalancerError:
       # No instances available
       log.error("All instances unavailable")
       # Fallback to queue or retry later

6. **Dynamic Scaling**:
   # Scale up under load
   if stats['total_active_requests'] > threshold:
       new_instance = create_new_instance()
       balancer.add_instance(new_instance)

   # Scale down when idle
   if stats['total_active_requests'] < threshold:
       balancer.remove_instance(least_used_instance)
"""
    )

    print("\n✅ Load balancing enables:")
    print("  - Horizontal scaling")
    print("  - Better resource utilization")
    print("  - Fault tolerance")
    print("  - Higher throughput")


async def main():
    """Run all examples."""
    print("\n🚀 Load Balancer Router Examples")
    print("=" * 60)

    await example_1_round_robin()
    await example_2_least_connections()
    await example_3_weighted_distribution()
    await example_4_health_monitoring()
    await example_5_dynamic_scaling()
    await example_6_production_patterns()

    print("\n" + "=" * 60)
    print("✅ Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
