"""Tests for anomaly detection and behavioral monitoring."""

import pytest
import asyncio
from agenkit.interfaces import Agent, Message
from agenkit.safety.anomaly_detection import (
    AnomalyDetectionMiddleware,
    AnomalyDetector,
    SecurityEvent,
)


class EchoAgent(Agent):
    """Simple echo agent for testing."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content=message.content)


class FailingAgent(Agent):
    """Agent that always fails."""

    @property
    def name(self) -> str:
        return "failing"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        raise ValueError("Simulated failure")


class SlowAgent(Agent):
    """Agent with slow processing."""

    @property
    def name(self) -> str:
        return "slow"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(0.1)
        return Message(role="assistant", content="slow response")


@pytest.fixture
def echo_agent():
    """Create a simple echo agent for testing."""
    return EchoAgent()


@pytest.fixture
def failing_agent():
    """Create an agent that always fails."""
    return FailingAgent()


@pytest.fixture
def slow_agent():
    """Create an agent with slow processing."""
    return SlowAgent()


class TestAnomalyDetector:
    """Tests for AnomalyDetector."""

    def test_detects_high_request_rate(self):
        """Test detection of high request rates."""
        detector = AnomalyDetector(max_requests_per_minute=10)

        # Simulate 11 requests in quick succession
        for i in range(11):
            result = detector.detect_rate_anomaly("user_123")

        # Last request should trigger anomaly
        assert result is not None
        event, details = result
        assert event == SecurityEvent.HIGH_REQUEST_RATE
        assert details["requests_per_minute"] > 10

    def test_detects_burst_traffic(self):
        """Test detection of burst traffic."""
        detector = AnomalyDetector(max_burst_size=5)

        # Simulate 6 requests in under 1 second
        for i in range(6):
            result = detector.detect_rate_anomaly("user_123")

        # Should detect burst
        assert result is not None
        event, details = result
        assert event == SecurityEvent.BURST_DETECTED
        assert details["burst_size"] > 5

    def test_rate_tracking_per_user(self):
        """Test that rate tracking is per-user."""
        detector = AnomalyDetector(max_requests_per_minute=10)

        # User 1 makes 5 requests
        for i in range(5):
            detector.detect_rate_anomaly("user_1")

        # User 2 makes 5 requests
        for i in range(5):
            detector.detect_rate_anomaly("user_2")

        # Neither should trigger anomaly (separate tracking)
        result1 = detector.detect_rate_anomaly("user_1")
        result2 = detector.detect_rate_anomaly("user_2")

        assert result1 is None
        assert result2 is None

    def test_detects_repeated_failures(self):
        """Test detection of repeated failures."""
        detector = AnomalyDetector(failure_rate_threshold=0.5)

        # Simulate 10 failures
        for i in range(10):
            result = detector.detect_failure_anomaly("user_123", is_failure=True)

        # Should detect high failure rate
        assert result is not None
        event, details = result
        assert event == SecurityEvent.REPEATED_FAILURES
        assert details["failure_rate"] > 0.5

    def test_failure_rate_calculation(self):
        """Test accurate failure rate calculation."""
        detector = AnomalyDetector(failure_rate_threshold=0.6)

        # 6 successes
        for i in range(6):
            detector.detect_failure_anomaly("user_123", is_failure=False)

        # 4 failures (total 10, rate = 0.4)
        for i in range(4):
            result = detector.detect_failure_anomaly("user_123", is_failure=True)

        # Should not trigger (0.4 < 0.6)
        assert result is None

    def test_requires_minimum_requests_for_failure_detection(self):
        """Test that failure detection requires minimum requests."""
        detector = AnomalyDetector()

        # Only 3 failures (below minimum of 10)
        for i in range(3):
            result = detector.detect_failure_anomaly("user_123", is_failure=True)

        # Should not trigger (not enough data)
        assert result is None

    def test_detects_unusual_input_size(self):
        """Test detection of unusual input sizes."""
        detector = AnomalyDetector(input_size_threshold=3.0)

        # Build baseline with normal sizes (around 100 bytes)
        for i in range(25):
            detector.detect_size_anomaly(100, 200)

        # Send very large input (10x normal)
        result = detector.detect_size_anomaly(1000, 200)

        # Should detect anomaly
        assert result is not None
        event, details = result
        assert event == SecurityEvent.UNUSUAL_INPUT_SIZE
        assert details["input_size"] == 1000

    def test_detects_unusual_output_size(self):
        """Test detection of unusual output sizes."""
        detector = AnomalyDetector(output_size_threshold=3.0)

        # Build baseline with normal sizes (around 200 bytes)
        for i in range(25):
            detector.detect_size_anomaly(100, 200)

        # Send very large output (10x normal)
        result = detector.detect_size_anomaly(100, 2000)

        # Should detect anomaly
        assert result is not None
        event, details = result
        assert event == SecurityEvent.UNUSUAL_OUTPUT_SIZE
        assert details["output_size"] == 2000

    def test_requires_minimum_data_for_size_detection(self):
        """Test that size detection requires minimum data points."""
        detector = AnomalyDetector()

        # Only 5 data points (below minimum of 20)
        for i in range(5):
            result = detector.detect_size_anomaly(100, 200)

        # Should not trigger (not enough data)
        assert result is None

    def test_detects_repetitive_content(self):
        """Test detection of repetitive content."""
        detector = AnomalyDetector()

        same_content = "This is the same message repeated"

        # Send same content 5 times
        for i in range(5):
            result = detector.detect_content_anomaly("user_123", same_content)

        # Last one should trigger
        assert result is not None
        event, details = result
        assert event == SecurityEvent.REPETITIVE_CONTENT
        assert details["repetitions"] == 5

    def test_content_tracking_per_user(self):
        """Test that content tracking is per-user."""
        detector = AnomalyDetector()

        # User 1 sends same content 5 times
        for i in range(5):
            detector.detect_content_anomaly("user_1", "content_a")

        # User 2 sends different content
        result = detector.detect_content_anomaly("user_2", "content_b")

        # User 2 should not trigger (different user)
        assert result is None

    def test_varied_content_not_flagged(self):
        """Test that varied content is not flagged."""
        detector = AnomalyDetector()

        # Send 5 different messages
        for i in range(5):
            result = detector.detect_content_anomaly("user_123", f"Message {i}")

        # Should not trigger
        assert result is None


class TestAnomalyDetectionMiddleware:
    """Tests for AnomalyDetectionMiddleware."""

    @pytest.mark.asyncio
    async def test_processes_normal_requests(self, echo_agent):
        """Test that normal requests pass through."""
        detector = AnomalyDetector(max_requests_per_minute=100)
        agent = AnomalyDetectionMiddleware(
            echo_agent,
            detector=detector,
            user_id="user_123"
        )

        message = Message(role="user", content="Hello")
        response = await agent.process(message)

        assert response.content == "Hello"

    @pytest.mark.asyncio
    async def test_detects_rate_anomalies(self, echo_agent):
        """Test detection of rate anomalies."""
        anomalies_detected = []

        def capture_anomaly(event, details):
            anomalies_detected.append((event, details))

        detector = AnomalyDetector(max_requests_per_minute=5)
        agent = AnomalyDetectionMiddleware(
            echo_agent,
            detector=detector,
            user_id="user_123",
            on_anomaly=capture_anomaly
        )

        # Send 6 requests quickly
        for i in range(6):
            await agent.process(Message(role="user", content=f"Request {i}"))

        # Should have detected rate anomaly
        assert len(anomalies_detected) > 0
        assert any(event == SecurityEvent.HIGH_REQUEST_RATE for event, _ in anomalies_detected)

    @pytest.mark.asyncio
    async def test_detects_content_anomalies(self, echo_agent):
        """Test detection of content anomalies."""
        anomalies_detected = []

        def capture_anomaly(event, details):
            anomalies_detected.append((event, details))

        agent = AnomalyDetectionMiddleware(
            echo_agent,
            user_id="user_123",
            on_anomaly=capture_anomaly
        )

        # Send same content 5 times
        for i in range(5):
            await agent.process(Message(role="user", content="Same message"))

        # Should have detected repetitive content
        assert any(event == SecurityEvent.REPETITIVE_CONTENT for event, _ in anomalies_detected)

    @pytest.mark.asyncio
    async def test_tracks_failures(self, failing_agent):
        """Test tracking of failures."""
        anomalies_detected = []

        def capture_anomaly(event, details):
            anomalies_detected.append((event, details))

        detector = AnomalyDetector(failure_rate_threshold=0.5)
        agent = AnomalyDetectionMiddleware(
            failing_agent,
            detector=detector,
            user_id="user_123",
            on_anomaly=capture_anomaly
        )

        # Try 10 requests (all will fail)
        for i in range(10):
            try:
                await agent.process(Message(role="user", content="Test"))
            except ValueError:
                pass  # Expected failure

        # Should detect high failure rate
        assert any(event == SecurityEvent.REPEATED_FAILURES for event, _ in anomalies_detected)

    @pytest.mark.asyncio
    async def test_detects_slow_processing(self, slow_agent):
        """Test detection of slow processing times."""
        anomalies_detected = []

        def capture_anomaly(event, details):
            anomalies_detected.append((event, details))

        detector = AnomalyDetector(processing_time_threshold=0.05)  # 50ms
        agent = AnomalyDetectionMiddleware(
            slow_agent,
            detector=detector,
            user_id="user_123",
            on_anomaly=capture_anomaly
        )

        # Process slow request
        await agent.process(Message(role="user", content="Test"))

        # Should detect slow processing
        assert any(event == SecurityEvent.UNUSUAL_PROCESSING_TIME for event, _ in anomalies_detected)

    @pytest.mark.asyncio
    async def test_default_anomaly_handler_prints(self, echo_agent, capsys):
        """Test that default handler prints to console."""
        detector = AnomalyDetector(max_requests_per_minute=2)
        agent = AnomalyDetectionMiddleware(
            echo_agent,
            detector=detector,
            user_id="user_123"
            # Using default handler
        )

        # Trigger rate anomaly
        for i in range(3):
            await agent.process(Message(role="user", content=f"Request {i}"))

        # Check console output
        captured = capsys.readouterr()
        assert "SECURITY ANOMALY DETECTED" in captured.out

    @pytest.mark.asyncio
    async def test_name_property_delegates(self, echo_agent):
        """Test that name property delegates to wrapped agent."""
        agent = AnomalyDetectionMiddleware(echo_agent, user_id="test")
        assert agent.name == echo_agent.name

    @pytest.mark.asyncio
    async def test_capabilities_property_delegates(self, echo_agent):
        """Test that capabilities property delegates to wrapped agent."""
        agent = AnomalyDetectionMiddleware(echo_agent, user_id="test")
        assert agent.capabilities == echo_agent.capabilities

    @pytest.mark.asyncio
    async def test_tracks_size_anomalies(self, echo_agent):
        """Test detection of size anomalies."""
        anomalies_detected = []

        def capture_anomaly(event, details):
            anomalies_detected.append((event, details))

        agent = AnomalyDetectionMiddleware(
            echo_agent,
            user_id="user_123",
            on_anomaly=capture_anomaly
        )

        # Build baseline with normal messages
        for i in range(25):
            await agent.process(Message(role="user", content="Normal message"))

        # Send very large message
        large_message = "x" * 10000
        await agent.process(Message(role="user", content=large_message))

        # Should detect size anomaly
        size_anomalies = [
            event for event, _ in anomalies_detected
            if event in [SecurityEvent.UNUSUAL_INPUT_SIZE, SecurityEvent.UNUSUAL_OUTPUT_SIZE]
        ]
        assert len(size_anomalies) > 0
