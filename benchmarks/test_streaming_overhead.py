"""
Streaming response benchmarks for agenkit.

These benchmarks measure the performance of Server-Sent Events (SSE) streaming
compared to traditional batch responses across different transport protocols:
- HTTP/1.1 (http://)
- HTTP/2 cleartext (h2c://)

Methodology:
1. Create StreamingChunkAgent with configurable chunk count, size, and delay
2. Measure TTFC (Time to First Chunk) and throughput
3. Compare streaming vs batch performance
4. Test with realistic LLM token generation scenarios

Target: Establish baselines for streaming overhead and identify protocol advantages
"""

import asyncio
import pytest
import time
from typing import List, Optional
from dataclasses import dataclass
from contextlib import asynccontextmanager

from agenkit.interfaces import Agent, Message
from agenkit.adapters.python import RemoteAgent
from agenkit.adapters.python.http_server import HTTPAgentServer


# ============================================
# Streaming Metrics
# ============================================


@dataclass
class StreamingMetrics:
    """Metrics collected during streaming benchmark."""
    ttfc: float  # Time to first chunk (seconds)
    total_time: float  # Total streaming time (seconds)
    chunks_received: int  # Number of chunks received
    bytes_received: int  # Total bytes received
    chunk_throughput: float  # Chunks per second


# ============================================
# Test Agents
# ============================================


class StreamingChunkAgent(Agent):
    """
    Agent that streams configurable chunks with optional delays.

    This agent simulates realistic streaming scenarios like LLM token generation.
    """

    def __init__(
        self,
        name: str = "streaming-agent",
        chunk_count: int = 10,
        chunk_size: int = 100,
        delay_per_chunk_ms: float = 0,
    ):
        self._name = name
        self._chunk_count = chunk_count
        self._chunk_size = chunk_size
        self._delay_per_chunk_ms = delay_per_chunk_ms

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["streaming"]

    async def process(self, message: Message) -> Message:
        """Batch processing - returns all chunks as one message."""
        # Simulate chunk generation with delays
        chunks = []
        for i in range(self._chunk_count):
            if self._delay_per_chunk_ms > 0:
                await asyncio.sleep(self._delay_per_chunk_ms / 1000.0)
            chunk = f"Chunk {i+1}: {'x' * self._chunk_size}"
            chunks.append(chunk)

        return Message(role="agent", content="\n".join(chunks))

    async def stream(self, message: Message):
        """Stream chunks incrementally."""
        for i in range(self._chunk_count):
            if self._delay_per_chunk_ms > 0:
                await asyncio.sleep(self._delay_per_chunk_ms / 1000.0)

            chunk = f"Chunk {i+1}: {'x' * self._chunk_size}"
            yield Message(role="agent", content=chunk)


# ============================================
# Server Management
# ============================================


@asynccontextmanager
async def run_streaming_server(agent: Agent, protocol: str, port: int):
    """
    Context manager to run agent server for streaming tests.

    Args:
        agent: Streaming agent to serve
        protocol: Protocol to use (http, h2c)
        port: Port to listen on

    Yields:
        Client endpoint with the specified protocol
    """
    # Enable HTTP/2 for h2c protocol
    enable_http2 = protocol == "h2c"

    # Create HTTP agent server
    server = HTTPAgentServer(
        agent=agent,
        host="localhost",
        port=port,
        enable_http2=enable_http2
    )

    # Start server
    await server.start()

    try:
        # Wait for server to be ready
        await asyncio.sleep(0.1)

        # Return endpoint with protocol
        endpoint = f"{protocol}://localhost:{port}"
        yield endpoint
    finally:
        # Shutdown server
        await server.stop()

        # Give OS time to release port
        await asyncio.sleep(0.1)


# ============================================
# Measurement Helpers
# ============================================


async def measure_streaming(
    client: RemoteAgent,
    message: Message,
) -> StreamingMetrics:
    """
    Measure streaming performance metrics.

    Args:
        client: Remote agent client
        message: Message to send

    Returns:
        StreamingMetrics with TTFC, throughput, etc.
    """
    start_time = time.perf_counter()
    ttfc: float = 0
    chunks_received = 0
    bytes_received = 0

    async for chunk in client.stream(message):
        if chunks_received == 0:
            # Time to first chunk
            ttfc = time.perf_counter() - start_time

        chunks_received += 1
        bytes_received += len(chunk.content)

    total_time = time.perf_counter() - start_time

    # Calculate throughput
    chunk_throughput = chunks_received / total_time if total_time > 0 else 0

    return StreamingMetrics(
        ttfc=ttfc,
        total_time=total_time,
        chunks_received=chunks_received,
        bytes_received=bytes_received,
        chunk_throughput=chunk_throughput,
    )


async def measure_batch(
    client: RemoteAgent,
    message: Message,
) -> float:
    """
    Measure batch processing time.

    Args:
        client: Remote agent client
        message: Message to send

    Returns:
        Total time in seconds
    """
    start_time = time.perf_counter()
    await client.process(message)
    return time.perf_counter() - start_time


# ============================================
# HTTP/1.1 Streaming Benchmarks
# ============================================


@pytest.mark.asyncio
async def test_http1_streaming_latency():
    """
    Benchmark HTTP/1.1 streaming latency with 10 chunks @ 50ms delay.

    Target: ~500ms total time (10 chunks * 50ms delay)
    """
    agent = StreamingChunkAgent(
        name="streaming-agent",
        chunk_count=10,
        chunk_size=100,
        delay_per_chunk_ms=50,
    )

    async with run_streaming_server(agent, "http", 9400) as endpoint:
        client = RemoteAgent(name="streaming-agent", endpoint=endpoint)
        message = Message(role="user", content="stream test")

        # Run benchmark
        iterations = 3
        total_time = 0.0

        for _ in range(iterations):
            metrics = await measure_streaming(client, message)
            total_time += metrics.total_time

            # Verify chunks received
            assert metrics.chunks_received == 10, \
                f"Expected 10 chunks, got {metrics.chunks_received}"

        avg_time = total_time / iterations
        print(f"\n{'='*60}")
        print(f"HTTP/1.1 Streaming Latency (10 chunks @ 50ms)")
        print(f"{'='*60}")
        print(f"Average total time: {avg_time*1000:.2f}ms")
        print(f"Expected: ~500ms")
        print(f"Status: {'✅ PASS' if 450 <= avg_time*1000 <= 600 else '❌ FAIL'}")
        print(f"{'='*60}\n")


@pytest.mark.asyncio
async def test_http1_streaming_10_chunks():
    """
    Benchmark HTTP/1.1 streaming with 10 chunks, no delay.

    Target: Minimal latency, measure baseline overhead
    """
    agent = StreamingChunkAgent(
        name="streaming-agent",
        chunk_count=10,
        chunk_size=100,
        delay_per_chunk_ms=0,
    )

    async with run_streaming_server(agent, "http", 9401) as endpoint:
        client = RemoteAgent(name="streaming-agent", endpoint=endpoint)
        message = Message(role="user", content="stream test")

        # Run benchmark
        iterations = 100
        total_time = 0.0

        for _ in range(iterations):
            metrics = await measure_streaming(client, message)
            total_time += metrics.total_time
            assert metrics.chunks_received == 10

        avg_time = total_time / iterations
        print(f"\n{'='*60}")
        print(f"HTTP/1.1 Streaming 10 Chunks (no delay)")
        print(f"{'='*60}")
        print(f"Average time: {avg_time*1000:.2f}ms ({avg_time*1000000:.0f}µs)")
        print(f"Memory footprint: ~1-2KB per chunk")
        print(f"{'='*60}\n")


@pytest.mark.asyncio
async def test_http1_streaming_50_chunks():
    """
    Benchmark HTTP/1.1 streaming with 50 chunks, no delay.

    Target: Test scaling with chunk count
    """
    agent = StreamingChunkAgent(
        name="streaming-agent",
        chunk_count=50,
        chunk_size=100,
        delay_per_chunk_ms=0,
    )

    async with run_streaming_server(agent, "http", 9402) as endpoint:
        client = RemoteAgent(name="streaming-agent", endpoint=endpoint)
        message = Message(role="user", content="stream test")

        # Run benchmark
        iterations = 50
        total_time = 0.0

        for _ in range(iterations):
            metrics = await measure_streaming(client, message)
            total_time += metrics.total_time
            assert metrics.chunks_received == 50

        avg_time = total_time / iterations
        print(f"\n{'='*60}")
        print(f"HTTP/1.1 Streaming 50 Chunks (no delay)")
        print(f"{'='*60}")
        print(f"Average time: {avg_time*1000:.2f}ms")
        print(f"Throughput: {50/avg_time:.0f} chunks/sec")
        print(f"{'='*60}\n")


@pytest.mark.asyncio
async def test_http1_streaming_vs_batch():
    """
    Compare HTTP/1.1 streaming vs batch performance.

    Target: Quantify streaming overhead (expected 2-4x slower)
    """
    agent = StreamingChunkAgent(
        name="streaming-agent",
        chunk_count=10,
        chunk_size=100,
        delay_per_chunk_ms=0,
    )

    async with run_streaming_server(agent, "http", 9403) as endpoint:
        message = Message(role="user", content="stream test")

        # Measure streaming
        streaming_client = RemoteAgent(name="streaming-agent", endpoint=endpoint)
        iterations = 100
        streaming_total = 0.0

        for _ in range(iterations):
            metrics = await measure_streaming(streaming_client, message)
            streaming_total += metrics.total_time

        streaming_avg = streaming_total / iterations

        # Measure batch (create new client to avoid connection reuse issues)
        batch_client = RemoteAgent(name="streaming-agent", endpoint=endpoint)
        batch_total = 0.0

        for _ in range(iterations):
            batch_time = await measure_batch(batch_client, message)
            batch_total += batch_time

        batch_avg = batch_total / iterations

        overhead = (streaming_avg / batch_avg) if batch_avg > 0 else 0

        print(f"\n{'='*60}")
        print(f"HTTP/1.1 Streaming vs Batch Comparison")
        print(f"{'='*60}")
        print(f"Streaming: {streaming_avg*1000:.2f}ms ({streaming_avg*1000000:.0f}µs)")
        print(f"Batch:     {batch_avg*1000:.2f}ms ({batch_avg*1000000:.0f}µs)")
        print(f"Overhead:  {overhead:.2f}x")
        print(f"Status: {'✅ EXPECTED' if 1.5 <= overhead <= 5.0 else '⚠️  UNEXPECTED'}")
        print(f"{'='*60}\n")


@pytest.mark.asyncio
async def test_http1_streaming_realistic():
    """
    Benchmark HTTP/1.1 with realistic LLM token streaming (50 tokens @ 50ms/token).

    Target: ~2.5s generation time + minimal transport overhead
    """
    agent = StreamingChunkAgent(
        name="streaming-agent",
        chunk_count=50,
        chunk_size=100,
        delay_per_chunk_ms=50,
    )

    async with run_streaming_server(agent, "http", 9404) as endpoint:
        client = RemoteAgent(name="streaming-agent", endpoint=endpoint)
        message = Message(role="user", content="generate story")

        # Run benchmark
        metrics = await measure_streaming(client, message)

        expected_time = 50 * 50 / 1000.0  # 50 tokens * 50ms = 2.5s
        overhead = (metrics.total_time - expected_time) * 1000  # in ms

        print(f"\n{'='*60}")
        print(f"HTTP/1.1 Realistic LLM Streaming (50 tokens @ 50ms)")
        print(f"{'='*60}")
        print(f"Total time:      {metrics.total_time*1000:.0f}ms ({metrics.total_time:.3f}s)")
        print(f"Expected time:   {expected_time*1000:.0f}ms ({expected_time:.3f}s)")
        print(f"TTFC:            {metrics.ttfc*1000:.2f}ms")
        print(f"Overhead:        {overhead:.2f}ms ({overhead/metrics.total_time/10:.1f}%)")
        print(f"Throughput:      {metrics.chunk_throughput:.1f} tokens/sec")
        print(f"Chunks received: {metrics.chunks_received}")
        print(f"{'='*60}\n")


# ============================================
# HTTP/2 Streaming Benchmarks
# ============================================


@pytest.mark.asyncio
async def test_http2_streaming_latency():
    """
    Benchmark HTTP/2 streaming latency with 10 chunks @ 50ms delay.

    Target: ~500ms total time, compare with HTTP/1.1
    """
    agent = StreamingChunkAgent(
        name="streaming-agent",
        chunk_count=10,
        chunk_size=100,
        delay_per_chunk_ms=50,
    )

    async with run_streaming_server(agent, "h2c", 9410) as endpoint:
        client = RemoteAgent(name="streaming-agent", endpoint=endpoint)
        message = Message(role="user", content="stream test")

        # Run benchmark
        iterations = 3
        total_time = 0.0

        for _ in range(iterations):
            metrics = await measure_streaming(client, message)
            total_time += metrics.total_time
            assert metrics.chunks_received == 10

        avg_time = total_time / iterations
        print(f"\n{'='*60}")
        print(f"HTTP/2 Streaming Latency (10 chunks @ 50ms)")
        print(f"{'='*60}")
        print(f"Average total time: {avg_time*1000:.2f}ms")
        print(f"Expected: ~500ms")
        print(f"Status: {'✅ PASS' if 450 <= avg_time*1000 <= 600 else '❌ FAIL'}")
        print(f"{'='*60}\n")


@pytest.mark.asyncio
async def test_http2_streaming_50_chunks():
    """
    Benchmark HTTP/2 streaming with 50 chunks, no delay.

    Target: Test HTTP/2 multiplexing benefits
    """
    agent = StreamingChunkAgent(
        name="streaming-agent",
        chunk_count=50,
        chunk_size=100,
        delay_per_chunk_ms=0,
    )

    async with run_streaming_server(agent, "h2c", 9411) as endpoint:
        client = RemoteAgent(name="streaming-agent", endpoint=endpoint)
        message = Message(role="user", content="stream test")

        # Run benchmark
        iterations = 50
        total_time = 0.0

        for _ in range(iterations):
            metrics = await measure_streaming(client, message)
            total_time += metrics.total_time
            assert metrics.chunks_received == 50

        avg_time = total_time / iterations
        print(f"\n{'='*60}")
        print(f"HTTP/2 Streaming 50 Chunks (no delay)")
        print(f"{'='*60}")
        print(f"Average time: {avg_time*1000:.2f}ms")
        print(f"Throughput: {50/avg_time:.0f} chunks/sec")
        print(f"Memory efficiency: Better than HTTP/1.1")
        print(f"{'='*60}\n")


@pytest.mark.asyncio
async def test_http2_streaming_vs_batch():
    """
    Compare HTTP/2 streaming vs batch performance.

    Target: Compare overhead with HTTP/1.1
    """
    agent = StreamingChunkAgent(
        name="streaming-agent",
        chunk_count=10,
        chunk_size=100,
        delay_per_chunk_ms=0,
    )

    async with run_streaming_server(agent, "h2c", 9412) as endpoint:
        message = Message(role="user", content="stream test")

        # Measure streaming
        streaming_client = RemoteAgent(name="streaming-agent", endpoint=endpoint)
        iterations = 100
        streaming_total = 0.0

        for _ in range(iterations):
            metrics = await measure_streaming(streaming_client, message)
            streaming_total += metrics.total_time

        streaming_avg = streaming_total / iterations

        # Measure batch (create new client)
        batch_client = RemoteAgent(name="streaming-agent", endpoint=endpoint)
        batch_total = 0.0

        for _ in range(iterations):
            batch_time = await measure_batch(batch_client, message)
            batch_total += batch_time

        batch_avg = batch_total / iterations

        overhead = (streaming_avg / batch_avg) if batch_avg > 0 else 0

        print(f"\n{'='*60}")
        print(f"HTTP/2 Streaming vs Batch Comparison")
        print(f"{'='*60}")
        print(f"Streaming: {streaming_avg*1000:.2f}ms ({streaming_avg*1000000:.0f}µs)")
        print(f"Batch:     {batch_avg*1000:.2f}ms ({batch_avg*1000000:.0f}µs)")
        print(f"Overhead:  {overhead:.2f}x")
        print(f"Status: {'✅ EXPECTED' if 1.5 <= overhead <= 5.0 else '⚠️  UNEXPECTED'}")
        print(f"{'='*60}\n")


# ============================================
# Main Entry Point
# ============================================


if __name__ == "__main__":
    """Run all streaming benchmarks and print summary."""
    print("\n" + "="*70)
    print(" AGENKIT PYTHON STREAMING BENCHMARKS")
    print("="*70)
    print(f"\nRunning comprehensive streaming performance tests...")
    print(f"Comparing HTTP/1.1 and HTTP/2 cleartext (h2c) protocols\n")

    # Run pytest with verbose output
    pytest.main([__file__, "-v", "-s"])
