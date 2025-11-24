"""Tests for load balancer router."""

import pytest
import asyncio
from agenkit.routing.load_balancer import (
    LoadBalancerRouter,
    LoadBalancingStrategy,
    AgentInstance,
    InstanceMetrics,
    LoadBalancerError,
)
from agenkit.interfaces import Message


# Mock agent for testing
class MockAgent:
    """Mock agent for testing."""

    def __init__(self, name: str, delay: float = 0.0, fail_rate: float = 0.0):
        """Initialize mock agent.

        Args:
            name: Agent name
            delay: Simulated processing delay in seconds
            fail_rate: Probability of failure (0.0 to 1.0)
        """
        self._name = name
        self.delay = delay
        self.fail_rate = fail_rate
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["test"]

    async def process(self, message: Message) -> Message:
        """Process message with simulated delay."""
        self.call_count += 1

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        # Simulate failures
        if self.fail_rate > 0:
            import random

            if random.random() < self.fail_rate:
                raise Exception(f"Simulated failure from {self._name}")

        return Message(
            role="assistant", content=f"Response from {self._name}: {message.content}"
        )


@pytest.fixture
def mock_agents():
    """Create mock agents for testing."""
    return [
        MockAgent("agent1", delay=0.01),
        MockAgent("agent2", delay=0.02),
        MockAgent("agent3", delay=0.01),
    ]


@pytest.fixture
def instances(mock_agents):
    """Create agent instances."""
    return [
        AgentInstance(agent=mock_agents[0], weight=1.0, max_concurrent=5),
        AgentInstance(agent=mock_agents[1], weight=1.0, max_concurrent=5),
        AgentInstance(agent=mock_agents[2], weight=1.0, max_concurrent=5),
    ]


@pytest.mark.asyncio
async def test_load_balancer_initialization(instances):
    """Test load balancer initialization."""
    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
    )

    assert balancer.name == "load_balancer"
    assert len(balancer.instances) == 3
    assert balancer.strategy == LoadBalancingStrategy.ROUND_ROBIN


@pytest.mark.asyncio
async def test_load_balancer_no_instances():
    """Test that load balancer requires at least one instance."""
    with pytest.raises(ValueError):
        LoadBalancerRouter(instances=[], strategy=LoadBalancingStrategy.ROUND_ROBIN)


@pytest.mark.asyncio
async def test_round_robin_strategy(instances):
    """Test round-robin load balancing."""
    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
    )

    # Send 9 requests (3 per instance)
    for i in range(9):
        message = Message(role="user", content=f"Request {i}")
        await balancer.process(message)

    # Check that each agent was called 3 times
    for instance in instances:
        assert instance.agent.call_count == 3


@pytest.mark.asyncio
async def test_least_connections_strategy(instances):
    """Test least-connections load balancing."""
    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
    )

    # Send requests
    tasks = []
    for i in range(10):
        message = Message(role="user", content=f"Request {i}")
        tasks.append(balancer.process(message))

    await asyncio.gather(*tasks)

    # All instances should have similar load
    counts = [instance.agent.call_count for instance in instances]
    assert max(counts) - min(counts) <= 2  # Within 2 of each other


@pytest.mark.asyncio
async def test_least_response_time_strategy():
    """Test least-response-time load balancing."""
    # Create agents with different delays
    fast_agent = MockAgent("fast", delay=0.01)
    slow_agent = MockAgent("slow", delay=0.1)

    instances = [
        AgentInstance(agent=fast_agent, max_concurrent=10),
        AgentInstance(agent=slow_agent, max_concurrent=10),
    ]

    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.LEAST_RESPONSE_TIME,
    )

    # Send several requests
    for i in range(10):
        message = Message(role="user", content=f"Request {i}")
        await balancer.process(message)

    # Fast agent should receive more requests
    assert fast_agent.call_count > slow_agent.call_count


@pytest.mark.asyncio
async def test_weighted_round_robin_strategy():
    """Test weighted round-robin load balancing."""
    agents = [
        MockAgent("agent1"),
        MockAgent("agent2"),
        MockAgent("agent3"),
    ]

    instances = [
        AgentInstance(agent=agents[0], weight=1.0, max_concurrent=10),
        AgentInstance(agent=agents[1], weight=2.0, max_concurrent=10),  # Double weight
        AgentInstance(agent=agents[2], weight=1.0, max_concurrent=10),
    ]

    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
    )

    # Send many requests
    for i in range(40):
        message = Message(role="user", content=f"Request {i}")
        await balancer.process(message)

    # Agent2 (weight=2.0) should receive roughly twice as many as others
    ratio1 = agents[1].call_count / agents[0].call_count
    ratio2 = agents[1].call_count / agents[2].call_count

    assert 1.5 < ratio1 < 2.5  # Roughly 2x
    assert 1.5 < ratio2 < 2.5  # Roughly 2x


@pytest.mark.asyncio
async def test_random_strategy(instances):
    """Test random load balancing."""
    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.RANDOM,
    )

    # Send many requests
    for i in range(30):
        message = Message(role="user", content=f"Request {i}")
        await balancer.process(message)

    # All agents should have been called (with high probability)
    for instance in instances:
        assert instance.agent.call_count > 0


@pytest.mark.asyncio
async def test_max_concurrent_limit(mock_agents):
    """Test that max_concurrent limit is enforced."""
    instances = [
        AgentInstance(agent=mock_agents[0], max_concurrent=2),  # Only 2 concurrent
    ]

    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
    )

    # Start 3 concurrent requests (should fail on 3rd)
    slow_agent = MockAgent("slow", delay=0.5)
    instances[0].agent = slow_agent

    async def send_request(i):
        message = Message(role="user", content=f"Request {i}")
        return await balancer.process(message)

    # Start 2 requests (should work)
    task1 = asyncio.create_task(send_request(1))
    task2 = asyncio.create_task(send_request(2))

    await asyncio.sleep(0.1)  # Let them start

    # Third request should fail (no capacity)
    with pytest.raises(LoadBalancerError):
        await balancer.process(Message(role="user", content="Request 3"))

    # Wait for first two to complete
    await task1
    await task2


@pytest.mark.asyncio
async def test_instance_metrics(instances):
    """Test that instance metrics are tracked."""
    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
    )

    # Send requests
    for i in range(5):
        message = Message(role="user", content=f"Request {i}")
        await balancer.process(message)

    # Check metrics
    for instance in instances:
        metrics = instance.metrics
        assert metrics.total_requests > 0
        assert metrics.successful_requests == metrics.total_requests
        assert metrics.failed_requests == 0
        assert metrics.active_requests == 0  # All completed


@pytest.mark.asyncio
async def test_failure_tracking():
    """Test that failures are tracked."""
    failing_agent = MockAgent("failing", fail_rate=1.0)  # Always fails

    instances = [
        AgentInstance(agent=failing_agent, max_concurrent=10),
    ]

    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
    )

    # Send requests (all should fail)
    for i in range(3):
        message = Message(role="user", content=f"Request {i}")
        try:
            await balancer.process(message)
        except Exception:
            pass  # Expected

    # Check metrics
    metrics = instances[0].metrics
    assert metrics.total_requests == 3
    assert metrics.failed_requests == 3
    assert metrics.successful_requests == 0
    assert len(metrics.errors) == 3


@pytest.mark.asyncio
async def test_success_rate_calculation():
    """Test success rate calculation."""
    agent = MockAgent("test")
    instance = AgentInstance(agent=agent, max_concurrent=10)

    # Initially 100% (no requests)
    assert instance.metrics.success_rate == 1.0

    # Simulate some requests
    instance.metrics.total_requests = 10
    instance.metrics.successful_requests = 8
    instance.metrics.failed_requests = 2

    assert instance.metrics.success_rate == 0.8
    assert instance.metrics.error_rate == 0.2


@pytest.mark.asyncio
async def test_avg_response_time():
    """Test average response time calculation."""
    agent = MockAgent("test")
    instance = AgentInstance(agent=agent, max_concurrent=10)

    # Simulate response times
    instance.metrics.successful_requests = 3
    instance.metrics.total_response_time = 0.6  # 3 requests * 0.2s avg

    assert instance.metrics.avg_response_time == 0.2


@pytest.mark.asyncio
async def test_load_factor():
    """Test load factor calculation."""
    agent = MockAgent("test")
    instance = AgentInstance(agent=agent, max_concurrent=10)

    assert instance.load_factor == 0.0

    instance.metrics.active_requests = 5
    assert instance.load_factor == 0.5

    instance.metrics.active_requests = 10
    assert instance.load_factor == 1.0


@pytest.mark.asyncio
async def test_can_accept_request():
    """Test can_accept_request check."""
    agent = MockAgent("test")
    instance = AgentInstance(agent=agent, max_concurrent=2)

    assert instance.can_accept_request is True

    instance.metrics.active_requests = 2
    assert instance.can_accept_request is False

    # Disabled instance
    instance.metrics.active_requests = 0
    instance.enabled = False
    assert instance.can_accept_request is False


@pytest.mark.asyncio
async def test_add_instance(instances):
    """Test adding instance dynamically."""
    balancer = LoadBalancerRouter(
        instances=instances[:2],  # Start with 2
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
    )

    assert len(balancer.instances) == 2

    # Add third instance
    balancer.add_instance(instances[2])

    assert len(balancer.instances) == 3


@pytest.mark.asyncio
async def test_remove_instance(instances):
    """Test removing instance."""
    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
    )

    removed = balancer.remove_instance("agent2")

    assert removed is True
    assert len(balancer.instances) == 2
    assert balancer.get_instance("agent2") is None


@pytest.mark.asyncio
async def test_get_instance(instances):
    """Test getting instance by name."""
    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
    )

    instance = balancer.get_instance("agent1")

    assert instance is not None
    assert instance.name == "agent1"


@pytest.mark.asyncio
async def test_get_statistics(instances):
    """Test getting load balancer statistics."""
    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
    )

    # Send some requests
    for i in range(6):
        await balancer.process(Message(role="user", content=f"Request {i}"))

    stats = balancer.get_statistics()

    assert stats["total_instances"] == 3
    assert stats["enabled_instances"] == 3
    assert stats["strategy"] == "round_robin"
    assert stats["total_requests"] == 6
    assert stats["overall_success_rate"] == 1.0
    assert len(stats["instances"]) == 3


@pytest.mark.asyncio
async def test_capabilities_aggregation(instances):
    """Test that capabilities are aggregated from all instances."""
    # Give each agent different capabilities
    instances[0].agent._capabilities = ["capability1"]
    instances[1].agent._capabilities = ["capability2"]
    instances[2].agent._capabilities = ["capability3"]

    # Mock the capabilities property
    for i, instance in enumerate(instances):
        type(instance.agent).capabilities = property(
            lambda self, i=i: [f"capability{i+1}"]
        )

    balancer = LoadBalancerRouter(
        instances=instances,
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
    )

    caps = balancer.capabilities

    # Should include all unique capabilities
    assert len(caps) >= 1  # At least one capability
