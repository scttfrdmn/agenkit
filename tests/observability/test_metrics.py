"""Tests for metrics collection functionality."""

import pytest
from opentelemetry import metrics as otel_metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from agenkit.interfaces import Agent, Message
from agenkit.observability import MetricsMiddleware, init_metrics


class SimpleAgent(Agent):
    """Simple agent for testing."""

    def __init__(self, name: str = "test-agent", response: str = "response"):
        self._name = name
        self._response = response

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["test"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=self._response,
            metadata={"processed_by": self._name},
        )


class ErrorAgent(Agent):
    """Agent that raises an error."""

    @property
    def name(self) -> str:
        return "error-agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        raise ValueError("Test error")


@pytest.fixture(scope="module")
def metric_reader():
    """Create an in-memory metric reader for testing (module-scoped)."""
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    otel_metrics.set_meter_provider(provider)

    yield reader

    # Shutdown at end of module
    provider.shutdown()


@pytest.mark.asyncio
async def test_metrics_middleware_collects_request_count(metric_reader):
    """Test that MetricsMiddleware counts requests."""
    agent = SimpleAgent(name="agent1")
    metrics_agent = MetricsMiddleware(agent)

    message = Message(role="user", content="test")
    await metrics_agent.process(message)

    # Get metrics
    metrics_data = metric_reader.get_metrics_data()

    # Find request counter
    request_counter = None
    for resource_metric in metrics_data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                if metric.name == "agenkit.agent.requests":
                    request_counter = metric
                    break

    assert request_counter is not None
    assert len(request_counter.data.data_points) > 0

    # Check attributes
    data_point = request_counter.data.data_points[0]
    attrs = dict(data_point.attributes)
    assert attrs["agent.name"] == "agent1"
    assert attrs["status"] == "success"
    assert data_point.value >= 1


@pytest.mark.asyncio
async def test_metrics_middleware_records_latency(metric_reader):
    """Test that MetricsMiddleware records latency."""
    agent = SimpleAgent(name="agent1")
    metrics_agent = MetricsMiddleware(agent)

    message = Message(role="user", content="test")
    await metrics_agent.process(message)

    # Get metrics
    metrics_data = metric_reader.get_metrics_data()

    # Find latency histogram
    latency_histogram = None
    for resource_metric in metrics_data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                if metric.name == "agenkit.agent.latency":
                    latency_histogram = metric
                    break

    assert latency_histogram is not None
    assert len(latency_histogram.data.data_points) > 0

    # Check that latency was recorded (should be > 0)
    data_point = latency_histogram.data.data_points[0]
    assert data_point.count >= 1
    assert data_point.sum >= 0  # Latency should be non-negative


@pytest.mark.asyncio
async def test_metrics_middleware_records_message_size(metric_reader):
    """Test that MetricsMiddleware records message size."""
    agent = SimpleAgent(name="agent1")
    metrics_agent = MetricsMiddleware(agent)

    message = Message(role="user", content="test message content")
    await metrics_agent.process(message)

    # Get metrics
    metrics_data = metric_reader.get_metrics_data()

    # Find message size histogram
    message_size_histogram = None
    for resource_metric in metrics_data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                if metric.name == "agenkit.agent.message_size":
                    message_size_histogram = metric
                    break

    assert message_size_histogram is not None
    assert len(message_size_histogram.data.data_points) > 0

    # Check that message size was recorded
    data_point = message_size_histogram.data.data_points[0]
    assert data_point.count >= 1
    # Sum accumulates across tests, so just check it's at least our message size
    assert data_point.sum >= len("test message content")


@pytest.mark.asyncio
async def test_metrics_middleware_records_errors(metric_reader):
    """Test that MetricsMiddleware records errors."""
    agent = ErrorAgent()
    metrics_agent = MetricsMiddleware(agent)

    message = Message(role="user", content="test")

    with pytest.raises(ValueError, match="Test error"):
        await metrics_agent.process(message)

    # Get metrics
    metrics_data = metric_reader.get_metrics_data()

    # Find error counter
    error_counter = None
    for resource_metric in metrics_data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                if metric.name == "agenkit.agent.errors":
                    error_counter = metric
                    break

    assert error_counter is not None
    assert len(error_counter.data.data_points) > 0

    # Check error attributes
    data_point = error_counter.data.data_points[0]
    attrs = dict(data_point.attributes)
    assert attrs["agent.name"] == "error-agent"
    assert attrs["status"] == "error"
    assert "ValueError" in attrs["error.type"]
    assert data_point.value >= 1


@pytest.mark.asyncio
async def test_metrics_middleware_sets_correct_attributes(metric_reader):
    """Test that MetricsMiddleware sets correct metric attributes."""
    agent = SimpleAgent(name="test-agent")
    metrics_agent = MetricsMiddleware(agent)

    message = Message(role="user", content="test")
    await metrics_agent.process(message)

    # Get metrics
    metrics_data = metric_reader.get_metrics_data()

    # Find request counter
    request_counter = None
    for resource_metric in metrics_data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                if metric.name == "agenkit.agent.requests":
                    request_counter = metric
                    break

    assert request_counter is not None

    # Check attributes on data points
    for data_point in request_counter.data.data_points:
        attrs = dict(data_point.attributes)
        if attrs.get("agent.name") == "test-agent":
            assert attrs["message.role"] == "user"
            assert attrs["status"] == "success"
            break
    else:
        pytest.fail("Did not find expected data point with correct attributes")


@pytest.mark.asyncio
async def test_metrics_middleware_multiple_requests(metric_reader):
    """Test that MetricsMiddleware handles multiple requests."""
    agent = SimpleAgent(name="agent1")
    metrics_agent = MetricsMiddleware(agent)

    # Process multiple messages
    for i in range(5):
        message = Message(role="user", content=f"test {i}")
        await metrics_agent.process(message)

    # Get metrics
    metrics_data = metric_reader.get_metrics_data()

    # Find request counter
    request_counter = None
    for resource_metric in metrics_data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                if metric.name == "agenkit.agent.requests":
                    request_counter = metric
                    break

    assert request_counter is not None

    # Check that count is at least 5
    total_count = 0
    for data_point in request_counter.data.data_points:
        attrs = dict(data_point.attributes)
        if attrs.get("agent.name") == "agent1" and attrs.get("status") == "success":
            total_count += data_point.value

    assert total_count >= 5


@pytest.mark.asyncio
async def test_metrics_middleware_preserves_agent_interface(metric_reader):
    """Test that MetricsMiddleware preserves Agent interface."""
    agent = SimpleAgent(name="agent1")
    metrics_agent = MetricsMiddleware(agent)

    # Check that agent interface is preserved
    assert metrics_agent.name == "agent1"
    assert metrics_agent.capabilities == ["test"]

    # Check that process works
    message = Message(role="user", content="test")
    response = await metrics_agent.process(message)
    assert response.content == "response"


@pytest.mark.asyncio
async def test_init_metrics():
    """Test init_metrics function."""
    # This will use a prometheus exporter, but we just test that it initializes
    provider = init_metrics(service_name="test-service", port=0)
    assert isinstance(provider, MeterProvider)

    # Verify meter works
    meter = otel_metrics.get_meter(__name__)
    counter = meter.create_counter("test_counter")
    counter.add(1)

    provider.shutdown()
