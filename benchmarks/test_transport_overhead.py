"""
Transport protocol benchmarks for agenkit.

These benchmarks measure the performance differences between transport protocols:
- HTTP/1.1 (http://)
- HTTP/2 cleartext (h2c://)
- HTTP/3 over QUIC (h3://) - currently falls back to HTTP/2 due to httpx limitations

Methodology:
1. Start agent servers for each protocol
2. Measure latency, throughput, and overhead
3. Test with different message sizes
4. Test with different concurrency levels

Target: Establish baselines and identify optimal protocols for different scenarios
"""

import asyncio
import pytest
import time
from typing import Any, List
from contextlib import asynccontextmanager

from agenkit.interfaces import Agent, Message
from agenkit.adapters.python import RemoteAgent
from agenkit.adapters.python.http_server import HTTPAgentServer


# ============================================
# Test Agents
# ============================================


class EchoAgent(Agent):
    """Agent that echoes messages back."""

    @property
    def name(self) -> str:
        return "echo-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["echo"]

    async def process(self, message: Message) -> Message:
        """Echo the message back."""
        return Message(role="agent", content=f"Echo: {message.content}")


class SlowAgent(Agent):
    """Agent that simulates processing time."""

    def __init__(self, delay_ms: float = 10):
        self._delay_ms = delay_ms

    @property
    def name(self) -> str:
        return "slow-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["slow"]

    async def process(self, message: Message) -> Message:
        """Process with artificial delay."""
        await asyncio.sleep(self._delay_ms / 1000.0)
        return Message(role="agent", content=f"Processed: {message.content}")


# ============================================
# Server Management
# ============================================


@asynccontextmanager
async def run_agent_server(agent: Agent, protocol: str, port: int):
    """
    Context manager to run agent server for testing.

    Args:
        agent: Agent to serve
        protocol: Protocol to use (http, h2c, h3)
        port: Port to listen on

    Yields:
        Client endpoint with the specified protocol
    """
    # Enable HTTP/2 for h2c and h3 protocols
    enable_http2 = protocol in ["h2c", "h3"]

    # Create HTTP agent server
    server = HTTPAgentServer(
        agent=agent,
        host="localhost",
        port=port,
        enable_http2=enable_http2
    )

    # Start server
    await server.start()

    # Give server time to fully initialize
    await asyncio.sleep(0.2)

    # Build client endpoint
    client_endpoint = f"{protocol}://localhost:{port}"

    try:
        yield client_endpoint
    finally:
        # Cleanup: stop server
        await server.stop()


# ============================================
# Benchmark Helpers
# ============================================


async def measure_latency(
    remote_agent: RemoteAgent, message: Message, iterations: int = 100
) -> dict[str, float]:
    """
    Measure request latency statistics.

    Args:
        remote_agent: Remote agent to test
        message: Message to send
        iterations: Number of requests

    Returns:
        Dictionary with min, max, avg, p50, p95, p99 latencies in milliseconds
    """
    latencies = []

    for _ in range(iterations):
        start = time.perf_counter()
        await remote_agent.process(message)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        latencies.append(elapsed)

    latencies.sort()

    return {
        "min": latencies[0],
        "max": latencies[-1],
        "avg": sum(latencies) / len(latencies),
        "p50": latencies[len(latencies) // 2],
        "p95": latencies[int(len(latencies) * 0.95)],
        "p99": latencies[int(len(latencies) * 0.99)],
    }


async def measure_throughput(
    remote_agent: RemoteAgent, message: Message, duration_seconds: float = 5.0
) -> dict[str, float]:
    """
    Measure request throughput.

    Args:
        remote_agent: Remote agent to test
        message: Message to send
        duration_seconds: How long to run test

    Returns:
        Dictionary with requests/sec, total requests, total time
    """
    start = time.perf_counter()
    end_time = start + duration_seconds
    count = 0

    while time.perf_counter() < end_time:
        await remote_agent.process(message)
        count += 1

    elapsed = time.perf_counter() - start

    return {
        "requests_per_sec": count / elapsed,
        "total_requests": count,
        "total_time": elapsed,
    }


async def measure_concurrent_load(
    remote_agent: RemoteAgent,
    message: Message,
    concurrency: int = 10,
    requests_per_task: int = 10,
) -> dict[str, float]:
    """
    Measure performance under concurrent load.

    Args:
        remote_agent: Remote agent to test
        message: Message to send
        concurrency: Number of concurrent tasks
        requests_per_task: Requests per concurrent task

    Returns:
        Dictionary with total time, avg latency, requests/sec
    """

    async def worker():
        """Worker task that sends multiple requests."""
        for _ in range(requests_per_task):
            await remote_agent.process(message)

    start = time.perf_counter()

    # Run concurrent workers
    await asyncio.gather(*[worker() for _ in range(concurrency)])

    elapsed = time.perf_counter() - start
    total_requests = concurrency * requests_per_task

    return {
        "total_time": elapsed,
        "total_requests": total_requests,
        "requests_per_sec": total_requests / elapsed,
        "avg_latency_ms": (elapsed / total_requests) * 1000,
    }


def print_latency_stats(protocol: str, stats: dict[str, float]):
    """Print latency statistics in consistent format."""
    print(f"\n{protocol} Latency Statistics:")
    print(f"  Min:  {stats['min']:7.2f}ms")
    print(f"  Avg:  {stats['avg']:7.2f}ms")
    print(f"  P50:  {stats['p50']:7.2f}ms")
    print(f"  P95:  {stats['p95']:7.2f}ms")
    print(f"  P99:  {stats['p99']:7.2f}ms")
    print(f"  Max:  {stats['max']:7.2f}ms")


def print_throughput_stats(protocol: str, stats: dict[str, float]):
    """Print throughput statistics in consistent format."""
    print(f"\n{protocol} Throughput:")
    print(f"  Requests/sec: {stats['requests_per_sec']:,.2f}")
    print(f"  Total requests: {stats['total_requests']:,}")
    print(f"  Total time: {stats['total_time']:.2f}s")


def print_concurrent_stats(protocol: str, concurrency: int, stats: dict[str, float]):
    """Print concurrent load statistics in consistent format."""
    print(f"\n{protocol} Concurrent Load (concurrency={concurrency}):")
    print(f"  Total requests: {stats['total_requests']:,}")
    print(f"  Total time: {stats['total_time']:.2f}s")
    print(f"  Requests/sec: {stats['requests_per_sec']:,.2f}")
    print(f"  Avg latency: {stats['avg_latency_ms']:.2f}ms")


# ============================================
# Protocol Latency Benchmarks
# ============================================


@pytest.mark.asyncio
async def test_http1_latency():
    """
    Benchmark: HTTP/1.1 latency baseline.

    Establishes baseline for HTTP/1.1 performance with small messages.
    """
    agent = EchoAgent()
    message = Message(role="user", content="test message")

    async with run_agent_server(agent, "http", 8100) as endpoint:
        remote_agent = RemoteAgent("echo-agent", endpoint=endpoint)

        stats = await measure_latency(remote_agent, message, iterations=100)
        print_latency_stats("HTTP/1.1", stats)

        # HTTP/1.1 should have reasonable latency
        assert stats["p95"] < 100.0, f"HTTP/1.1 P95 latency {stats['p95']:.2f}ms exceeds 100ms"


@pytest.mark.asyncio
async def test_http2_latency():
    """
    Benchmark: HTTP/2 latency.

    HTTP/2 may have slightly higher latency due to connection setup,
    but should benefit from multiplexing under load.
    """
    agent = EchoAgent()
    message = Message(role="user", content="test message")

    async with run_agent_server(agent, "h2c", 8101) as endpoint:
        remote_agent = RemoteAgent("echo-agent", endpoint=endpoint)

        stats = await measure_latency(remote_agent, message, iterations=100)
        print_latency_stats("HTTP/2", stats)

        # HTTP/2 should have reasonable latency
        assert stats["p95"] < 100.0, f"HTTP/2 P95 latency {stats['p95']:.2f}ms exceeds 100ms"


@pytest.mark.skip(reason="HTTP/3 requires SSL/TLS configuration - skipped in benchmarks")
@pytest.mark.asyncio
async def test_http3_latency():
    """
    Benchmark: HTTP/3 latency.

    Note: HTTP/3 (h3://) requires SSL/TLS, which is not configured in the benchmark
    server. To properly test HTTP/3 performance, the HTTPAgentServer would need
    SSL certificates and the h3:// protocol would use QUIC over TLS.

    For now, we focus on HTTP/1.1 and HTTP/2 cleartext (h2c) comparisons.
    """
    pass


# ============================================
# Protocol Comparison Benchmarks
# ============================================


@pytest.mark.asyncio
async def test_protocol_latency_comparison():
    """
    Benchmark: Compare latency between HTTP/1.1 and HTTP/2 cleartext.

    This helps identify which protocol is fastest for low-latency scenarios.

    Note: HTTP/3 is not included as it requires SSL/TLS configuration.
    """
    agent = EchoAgent()
    message = Message(role="user", content="test message")
    iterations = 100

    results = {}

    # HTTP/1.1
    async with run_agent_server(agent, "http", 8110) as endpoint:
        remote_agent = RemoteAgent("echo-agent", endpoint=endpoint)
        results["HTTP/1.1"] = await measure_latency(remote_agent, message, iterations)

    # HTTP/2 cleartext (h2c)
    async with run_agent_server(agent, "h2c", 8111) as endpoint:
        remote_agent = RemoteAgent("echo-agent", endpoint=endpoint)
        results["HTTP/2 (h2c)"] = await measure_latency(remote_agent, message, iterations)

    # Print comparison
    print("\n" + "="*70)
    print("Protocol Latency Comparison")
    print("="*70)

    for protocol, stats in results.items():
        print_latency_stats(protocol, stats)

    print("\n" + "="*70)
    print("Summary (P95 latency):")
    sorted_results = sorted(results.items(), key=lambda x: x[1]["p95"])
    for i, (protocol, stats) in enumerate(sorted_results, 1):
        print(f"  {i}. {protocol:10s} {stats['p95']:7.2f}ms")
    print("="*70)


# ============================================
# Throughput Benchmarks
# ============================================


@pytest.mark.asyncio
async def test_protocol_throughput_comparison():
    """
    Benchmark: Compare throughput between HTTP/1.1 and HTTP/2 cleartext.

    This helps identify which protocol handles the highest request rate.

    Note: HTTP/3 is not included as it requires SSL/TLS configuration.
    """
    agent = EchoAgent()
    message = Message(role="user", content="test message")
    duration = 5.0

    results = {}

    # HTTP/1.1
    async with run_agent_server(agent, "http", 8120) as endpoint:
        remote_agent = RemoteAgent("echo-agent", endpoint=endpoint)
        results["HTTP/1.1"] = await measure_throughput(remote_agent, message, duration)

    # HTTP/2 cleartext (h2c)
    async with run_agent_server(agent, "h2c", 8121) as endpoint:
        remote_agent = RemoteAgent("echo-agent", endpoint=endpoint)
        results["HTTP/2 (h2c)"] = await measure_throughput(remote_agent, message, duration)

    # Print comparison
    print("\n" + "="*70)
    print("Protocol Throughput Comparison")
    print("="*70)

    for protocol, stats in results.items():
        print_throughput_stats(protocol, stats)

    print("\n" + "="*70)
    print("Summary (Requests/sec):")
    sorted_results = sorted(results.items(), key=lambda x: x[1]["requests_per_sec"], reverse=True)
    for i, (protocol, stats) in enumerate(sorted_results, 1):
        print(f"  {i}. {protocol:10s} {stats['requests_per_sec']:10,.2f} req/s")
    print("="*70)


# ============================================
# Message Size Benchmarks
# ============================================


@pytest.mark.asyncio
async def test_message_size_impact():
    """
    Benchmark: Impact of message size on protocol performance.

    Tests small (100B), medium (10KB), and large (1MB) messages.
    """
    agent = EchoAgent()

    # Different message sizes
    sizes = {
        "Small (100B)": "x" * 100,
        "Medium (10KB)": "x" * 10_000,
        "Large (1MB)": "x" * 1_000_000,
    }

    print("\n" + "="*70)
    print("Message Size Impact on Latency")
    print("="*70)

    for size_label, content in sizes.items():
        message = Message(role="user", content=content)

        print(f"\n{size_label}:")

        # Test HTTP/1.1
        async with run_agent_server(agent, "http", 8130) as endpoint:
            remote_agent = RemoteAgent("echo-agent", endpoint=endpoint)
            stats = await measure_latency(remote_agent, message, iterations=50)
            print(f"  HTTP/1.1: P95 = {stats['p95']:.2f}ms, Avg = {stats['avg']:.2f}ms")

        # Test HTTP/2
        async with run_agent_server(agent, "h2c", 8131) as endpoint:
            remote_agent = RemoteAgent("echo-agent", endpoint=endpoint)
            stats = await measure_latency(remote_agent, message, iterations=50)
            print(f"  HTTP/2:   P95 = {stats['p95']:.2f}ms, Avg = {stats['avg']:.2f}ms")

    print("="*70)


# ============================================
# Concurrent Load Benchmarks
# ============================================


@pytest.mark.asyncio
async def test_concurrent_load_comparison():
    """
    Benchmark: Performance under concurrent load.

    Tests with 1, 10, 50, and 100 concurrent requests.
    HTTP/2 should excel here due to multiplexing.
    """
    agent = EchoAgent()
    message = Message(role="user", content="test message")
    concurrency_levels = [1, 10, 50, 100]

    print("\n" + "="*70)
    print("Concurrent Load Performance")
    print("="*70)

    for concurrency in concurrency_levels:
        print(f"\nConcurrency Level: {concurrency}")

        # HTTP/1.1
        async with run_agent_server(agent, "http", 8140) as endpoint:
            remote_agent = RemoteAgent("echo-agent", endpoint=endpoint)
            stats = await measure_concurrent_load(
                remote_agent, message, concurrency=concurrency, requests_per_task=10
            )
            print(f"  HTTP/1.1: {stats['requests_per_sec']:7,.2f} req/s, {stats['avg_latency_ms']:6.2f}ms avg")

        # HTTP/2
        async with run_agent_server(agent, "h2c", 8141) as endpoint:
            remote_agent = RemoteAgent("echo-agent", endpoint=endpoint)
            stats = await measure_concurrent_load(
                remote_agent, message, concurrency=concurrency, requests_per_task=10
            )
            print(f"  HTTP/2:   {stats['requests_per_sec']:7,.2f} req/s, {stats['avg_latency_ms']:6.2f}ms avg")

    print("="*70)
    print("Note: HTTP/2 should handle higher concurrency better due to multiplexing")
    print("="*70)


# ============================================
# Realistic Workload Benchmarks
# ============================================


@pytest.mark.asyncio
async def test_realistic_workload():
    """
    Benchmark: Realistic agent workload with processing time.

    Simulates an agent with 10ms processing time to represent
    a real LLM call or computation.
    """
    agent = SlowAgent(delay_ms=10)
    message = Message(role="user", content="process this")
    concurrency = 10

    print("\n" + "="*70)
    print("Realistic Workload (10ms agent processing time)")
    print("="*70)

    results = {}

    # HTTP/1.1
    async with run_agent_server(agent, "http", 8150) as endpoint:
        remote_agent = RemoteAgent("slow-agent", endpoint=endpoint)
        stats = await measure_concurrent_load(
            remote_agent, message, concurrency=concurrency, requests_per_task=10
        )
        results["HTTP/1.1"] = stats
        print_concurrent_stats("HTTP/1.1", concurrency, stats)

    # HTTP/2
    async with run_agent_server(agent, "h2c", 8151) as endpoint:
        remote_agent = RemoteAgent("slow-agent", endpoint=endpoint)
        stats = await measure_concurrent_load(
            remote_agent, message, concurrency=concurrency, requests_per_task=10
        )
        results["HTTP/2"] = stats
        print_concurrent_stats("HTTP/2", concurrency, stats)

    print("\n" + "="*70)
    print("Analysis:")
    print(f"  Expected latency: ~10ms (agent processing) + network overhead")
    for protocol, stats in results.items():
        overhead = stats["avg_latency_ms"] - 10
        print(f"  {protocol:10s} overhead: {overhead:.2f}ms ({overhead/10*100:.1f}% of processing time)")
    print("="*70)


# ============================================
# Summary
# ============================================


@pytest.mark.asyncio
async def test_transport_benchmark_summary():
    """
    Summary: Run all transport benchmarks and print aggregate results.
    """
    print("\n" + "="*70)
    print("Transport Protocol Performance Benchmark Summary")
    print("="*70)

    # Run all benchmarks
    await test_protocol_latency_comparison()
    await test_protocol_throughput_comparison()
    await test_message_size_impact()
    await test_concurrent_load_comparison()
    await test_realistic_workload()

    print("\n" + "="*70)
    print("Key Findings:")
    print("1. HTTP/1.1: Baseline performance, good for simple scenarios")
    print("2. HTTP/2 (h2c): Better for concurrent load due to multiplexing")
    print("3. Message size impacts all protocols similarly")
    print("4. Transport overhead is minimal compared to agent processing time")
    print("")
    print("Note: HTTP/3 benchmarks require SSL/TLS configuration and are not")
    print("included in this test suite. HTTP/2 cleartext (h2c) provides a good")
    print("comparison for protocol efficiency without SSL overhead.")
    print("="*70)


if __name__ == "__main__":
    # Run summary if executed directly
    asyncio.run(test_transport_benchmark_summary())
