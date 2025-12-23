"""
Anomaly detection for agent behavior monitoring.

Detects:
- Unusual request patterns
- Rate anomalies
- Suspicious behavior
- Resource usage anomalies
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from agenkit import Agent, Message


class SecurityEvent(Enum):
    """Types of security events."""

    # Rate anomalies
    HIGH_REQUEST_RATE = "high_request_rate"
    BURST_DETECTED = "burst_detected"

    # Pattern anomalies
    REPEATED_FAILURES = "repeated_failures"
    PERMISSION_DENIED_SPIKE = "permission_denied_spike"
    VALIDATION_FAILURES = "validation_failures"

    # Behavior anomalies
    UNUSUAL_INPUT_SIZE = "unusual_input_size"
    UNUSUAL_OUTPUT_SIZE = "unusual_output_size"
    UNUSUAL_PROCESSING_TIME = "unusual_processing_time"

    # Content anomalies
    SUSPICIOUS_CONTENT_PATTERN = "suspicious_content_pattern"
    REPETITIVE_CONTENT = "repetitive_content"


@dataclass
class AnomalyDetector:
    """
    Detects anomalous agent behavior.

    Uses statistical methods and heuristics to identify:
    - Rate-based anomalies
    - Pattern-based anomalies
    - Content-based anomalies
    """

    # Rate limiting thresholds
    max_requests_per_minute: int = 60
    max_burst_size: int = 10  # requests in 1 second

    # Size thresholds (standard deviations)
    input_size_threshold: float = 3.0  # 3 sigma
    output_size_threshold: float = 3.0

    # Processing time threshold (seconds)
    processing_time_threshold: float = 30.0

    # Failure rate threshold (percentage)
    failure_rate_threshold: float = 0.5  # 50%

    # Tracking data structures
    request_timestamps: dict[str, deque] = field(
        default_factory=lambda: defaultdict(lambda: deque(maxlen=1000))
    )
    failure_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    success_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Statistics (rolling averages)
    input_sizes: deque = field(default_factory=lambda: deque(maxlen=100))
    output_sizes: deque = field(default_factory=lambda: deque(maxlen=100))
    processing_times: deque = field(default_factory=lambda: deque(maxlen=100))

    # Content tracking (for repetition detection)
    recent_content: dict[str, deque] = field(
        default_factory=lambda: defaultdict(lambda: deque(maxlen=10))
    )

    def detect_rate_anomaly(self, user_id: str) -> tuple[SecurityEvent, dict[str, Any]] | None:
        """
        Detect rate-based anomalies.

        Args:
            user_id: User identifier

        Returns:
            (SecurityEvent, details) if anomaly detected, else None
        """
        now = time.time()

        # Record request
        self.request_timestamps[user_id].append(now)

        # Clean old timestamps (> 60 seconds)
        while self.request_timestamps[user_id] and (now - self.request_timestamps[user_id][0] > 60):
            self.request_timestamps[user_id].popleft()

        # Check request rate (per minute)
        requests_per_minute = len(self.request_timestamps[user_id])
        if requests_per_minute > self.max_requests_per_minute:
            return SecurityEvent.HIGH_REQUEST_RATE, {
                "user_id": user_id,
                "requests_per_minute": requests_per_minute,
                "threshold": self.max_requests_per_minute,
            }

        # Check burst rate (per second)
        recent = sum(1 for ts in self.request_timestamps[user_id] if now - ts < 1.0)
        if recent > self.max_burst_size:
            return SecurityEvent.BURST_DETECTED, {
                "user_id": user_id,
                "burst_size": recent,
                "threshold": self.max_burst_size,
            }

        return None

    def detect_failure_anomaly(
        self, user_id: str, is_failure: bool
    ) -> tuple[SecurityEvent, dict[str, Any]] | None:
        """
        Detect failure rate anomalies.

        Args:
            user_id: User identifier
            is_failure: Whether current request failed

        Returns:
            (SecurityEvent, details) if anomaly detected, else None
        """
        # Update counts
        if is_failure:
            self.failure_counts[user_id] += 1
        else:
            self.success_counts[user_id] += 1

        # Calculate failure rate
        total = self.failure_counts[user_id] + self.success_counts[user_id]
        if total >= 10:  # Need at least 10 requests for meaningful rate
            failure_rate = self.failure_counts[user_id] / total

            if failure_rate > self.failure_rate_threshold:
                return SecurityEvent.REPEATED_FAILURES, {
                    "user_id": user_id,
                    "failure_rate": failure_rate,
                    "failures": self.failure_counts[user_id],
                    "total": total,
                }

        return None

    def detect_size_anomaly(
        self, input_size: int, output_size: int
    ) -> tuple[SecurityEvent, dict[str, Any]] | None:
        """
        Detect unusual input/output sizes.

        Args:
            input_size: Input message size
            output_size: Output message size

        Returns:
            (SecurityEvent, details) if anomaly detected, else None
        """
        # Track sizes
        self.input_sizes.append(input_size)
        self.output_sizes.append(output_size)

        # Need enough data points for statistics
        if len(self.input_sizes) < 20:
            return None

        # Calculate mean and std dev
        import statistics

        input_mean = statistics.mean(self.input_sizes)
        input_stdev = statistics.stdev(self.input_sizes)

        output_mean = statistics.mean(self.output_sizes)
        output_stdev = statistics.stdev(self.output_sizes)

        # Check input size anomaly (> threshold std devs from mean)
        if input_stdev > 0:
            input_z_score = abs(input_size - input_mean) / input_stdev
            if input_z_score > self.input_size_threshold:
                return SecurityEvent.UNUSUAL_INPUT_SIZE, {
                    "input_size": input_size,
                    "mean": input_mean,
                    "stdev": input_stdev,
                    "z_score": input_z_score,
                }

        # Check output size anomaly
        if output_stdev > 0:
            output_z_score = abs(output_size - output_mean) / output_stdev
            if output_z_score > self.output_size_threshold:
                return SecurityEvent.UNUSUAL_OUTPUT_SIZE, {
                    "output_size": output_size,
                    "mean": output_mean,
                    "stdev": output_stdev,
                    "z_score": output_z_score,
                }

        return None

    def detect_content_anomaly(
        self, user_id: str, content: str
    ) -> tuple[SecurityEvent, dict[str, Any]] | None:
        """
        Detect content-based anomalies.

        Args:
            user_id: User identifier
            content: Message content

        Returns:
            (SecurityEvent, details) if anomaly detected, else None
        """
        # Track recent content
        content_hash = hash(content[:500])  # Hash first 500 chars
        self.recent_content[user_id].append(content_hash)

        # Check for repetitive content (same content repeated)
        if len(self.recent_content[user_id]) >= 5:
            recent_5 = list(self.recent_content[user_id])[-5:]
            if len(set(recent_5)) == 1:  # All 5 are same
                return SecurityEvent.REPETITIVE_CONTENT, {
                    "user_id": user_id,
                    "repetitions": 5,
                }

        return None


class AnomalyDetectionMiddleware(Agent):
    """
    Middleware for anomaly detection.

    Monitors agent interactions and detects:
    - Rate anomalies
    - Failure patterns
    - Size anomalies
    - Content anomalies

    Usage:
        detector = AnomalyDetector(
            max_requests_per_minute=100,
            max_burst_size=20
        )

        agent = AnomalyDetectionMiddleware(
            base_agent,
            detector=detector,
            user_id="user_123"
        )
    """

    def __init__(
        self,
        agent: Agent,
        detector: AnomalyDetector | None = None,
        user_id: str = "default",
        on_anomaly: Callable | None = None,
    ):
        """
        Initialize anomaly detection middleware.

        Args:
            agent: Agent to wrap
            detector: Anomaly detector (default: standard detector)
            user_id: User identifier for tracking
            on_anomaly: Callback function for anomaly events
        """
        self._agent = agent
        self.detector = detector or AnomalyDetector()
        self.user_id = user_id
        self.on_anomaly = on_anomaly or self._default_anomaly_handler

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    def _default_anomaly_handler(self, event: SecurityEvent, details: dict[str, Any]):
        """Default handler: log to console."""
        print(f"SECURITY ANOMALY DETECTED: {event.value}")
        print(f"Details: {details}")

    async def process(self, message: Message) -> Message:
        """Process with anomaly detection."""
        start_time = time.time()

        # 1. Check rate anomaly
        rate_anomaly = self.detector.detect_rate_anomaly(self.user_id)
        if rate_anomaly:
            self.on_anomaly(*rate_anomaly)

        # 2. Check content anomaly
        content_str = str(message.content) if message.content else ""
        content_anomaly = self.detector.detect_content_anomaly(self.user_id, content_str)
        if content_anomaly:
            self.on_anomaly(*content_anomaly)

        # 3. Process with wrapped agent
        is_failure = False
        response = None
        try:
            response = await self._agent.process(message)
        except Exception:
            is_failure = True
            raise
        finally:
            # 4. Check failure anomaly
            failure_anomaly = self.detector.detect_failure_anomaly(self.user_id, is_failure)
            if failure_anomaly:
                self.on_anomaly(*failure_anomaly)

            # 5. Check size and timing anomalies (if succeeded)
            if response:
                processing_time = time.time() - start_time
                input_size = len(content_str)
                output_size = len(str(response.content) if response.content else "")

                size_anomaly = self.detector.detect_size_anomaly(input_size, output_size)
                if size_anomaly:
                    self.on_anomaly(*size_anomaly)

                # Check processing time
                if processing_time > self.detector.processing_time_threshold:
                    self.on_anomaly(
                        SecurityEvent.UNUSUAL_PROCESSING_TIME,
                        {
                            "user_id": self.user_id,
                            "processing_time": processing_time,
                            "threshold": self.detector.processing_time_threshold,
                        },
                    )

        return response


def anomaly_detection(
    detector: AnomalyDetector | None = None,
    user_id: str = "default",
    on_anomaly: callable | None = None,
):
    """
    Create anomaly detection middleware function.

    Args:
        detector: Anomaly detector
        user_id: User identifier
        on_anomaly: Callback for anomaly events

    Returns:
        Middleware function

    Usage:
        def my_anomaly_handler(event, details):
            alert_security_team(event, details)

        agent = applyMiddleware(base_agent, [
            anomaly_detection(user_id="user_123", on_anomaly=my_anomaly_handler),
        ])
    """

    def middleware(agent: Agent) -> Agent:
        return AnomalyDetectionMiddleware(agent, detector, user_id, on_anomaly)

    return middleware
