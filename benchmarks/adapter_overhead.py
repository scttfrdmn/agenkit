"""Benchmark adapter overhead.

This script measures the overhead of the protocol adapter compared to direct
local agent calls. Target: <5% overhead as specified in Issue #2.

Run with: python benchmarks/adapter_overhead.py
"""

import asyncio
import tempfile
import time
from pathlib import Path

from agenkit import Agent, Message
from agenkit.adapters.python import LocalAgent, RemoteAgent


class SimpleAgent(Agent):
    """Minimal agent for benchmarking."""

    @property
    def name(self) -> str:
        return "simple"

    async def process(self, message: Message) -> Message:
        # Minimal processing to isolate adapter overhead
        return Message(role="agent", content=f"Processed: {message.content}")


class RealisticAgent(Agent):
    """Agent with realistic processing time (simulates LLM call)."""

    @property
    def name(self) -> str:
        return "realistic"

    async def process(self, message: Message) -> Message:
        # Simulate a typical LLM API call (100ms)
        await asyncio.sleep(0.1)
        return Message(role="agent", content=f"Processed: {message.content}")


async def benchmark_direct(agent: Agent, iterations: int = 1000) -> float:
    """Benchmark direct agent calls."""
    message = Message(role="user", content="test")

    start = time.perf_counter()
    for _ in range(iterations):
        await agent.process(message)
    end = time.perf_counter()

    return (end - start) / iterations * 1000  # ms per call


async def benchmark_remote(remote: RemoteAgent, iterations: int = 1000) -> float:
    """Benchmark remote agent calls."""
    message = Message(role="user", content="test")

    start = time.perf_counter()
    for _ in range(iterations):
        await remote.process(message)
    end = time.perf_counter()

    return (end - start) / iterations * 1000  # ms per call


async def benchmark_message_sizes():
    """Benchmark different message sizes."""
    agent = SimpleAgent()

    with tempfile.TemporaryDirectory() as tmpdir:
        socket_path = Path(tmpdir) / "bench.sock"
        endpoint = f"unix://{socket_path}"

        # Start server
        server = LocalAgent(agent, endpoint=endpoint)
        await server.start()

        # Create client
        remote = RemoteAgent("simple", endpoint=endpoint)

        print("\n📊 Message Size Benchmarks")
        print("=" * 60)

        sizes = [
            ("Small (100B)", 100),
            ("Medium (10KB)", 10 * 1024),
            ("Large (100KB)", 100 * 1024),
            ("XLarge (1MB)", 1024 * 1024),
        ]

        for label, size in sizes:
            message = Message(role="user", content="x" * size)

            # Direct
            start = time.perf_counter()
            for _ in range(100):
                await agent.process(message)
            direct_time = (time.perf_counter() - start) / 100 * 1000

            # Remote
            start = time.perf_counter()
            for _ in range(100):
                await remote.process(message)
            remote_time = (time.perf_counter() - start) / 100 * 1000

            overhead = ((remote_time - direct_time) / direct_time) * 100

            print(f"\n{label}:")
            print(f"  Direct:  {direct_time:8.3f} ms")
            print(f"  Remote:  {remote_time:8.3f} ms")
            print(f"  Overhead: {overhead:6.1f}%")

        await server.stop()


async def main():
    """Run all benchmarks."""
    print("\n🚀 Protocol Adapter Overhead Benchmarks")
    print("=" * 60)
    print("Target: <5% overhead (Issue #2)")
    print()

    agent = SimpleAgent()

    # Create temporary socket
    with tempfile.TemporaryDirectory() as tmpdir:
        socket_path = Path(tmpdir) / "bench.sock"
        endpoint = f"unix://{socket_path}"

        # Start server
        server = LocalAgent(agent, endpoint=endpoint)
        await server.start()

        # Create client
        remote = RemoteAgent("simple", endpoint=endpoint)

        # Warm up
        print("Warming up...")
        for _ in range(100):
            await agent.process(Message(role="user", content="warmup"))
            await remote.process(Message(role="user", content="warmup"))

        print("\n📊 Core Overhead Benchmark (1000 iterations)")
        print("=" * 60)

        # Benchmark direct calls
        direct_time = await benchmark_direct(agent, iterations=1000)
        print(f"Direct (baseline):  {direct_time:.4f} ms per call")

        # Benchmark remote calls
        remote_time = await benchmark_remote(remote, iterations=1000)
        print(f"Remote (adapter):   {remote_time:.4f} ms per call")

        # Calculate overhead
        overhead_ms = remote_time - direct_time
        overhead_pct = (overhead_ms / direct_time) * 100

        print(f"\nAbsolute overhead:  {overhead_ms:.4f} ms")
        print(f"Relative overhead:  {overhead_pct:.1f}%")

        if overhead_pct < 5.0:
            print(f"\n✅ PASS: Overhead {overhead_pct:.1f}% < 5% target")
        else:
            print(f"\n⚠️  WARN: Overhead {overhead_pct:.1f}% > 5% target")

        print(f"\n💡 Note: This measures microsecond-level overhead.")
        print(f"   Absolute overhead is only {overhead_ms:.3f}ms ({overhead_ms * 1000:.1f}μs)")

        await server.stop()

    # Realistic agent benchmark (simulates LLM call)
    print("\n📊 Realistic Agent Benchmark (simulates 100ms LLM call)")
    print("=" * 60)

    realistic_agent = RealisticAgent()

    with tempfile.TemporaryDirectory() as tmpdir:
        socket_path = Path(tmpdir) / "realistic.sock"
        endpoint = f"unix://{socket_path}"

        # Start server
        server = LocalAgent(realistic_agent, endpoint=endpoint)
        await server.start()

        # Create client
        remote = RemoteAgent("realistic", endpoint=endpoint)

        # Benchmark (fewer iterations since each call takes 100ms)
        direct_time = await benchmark_direct(realistic_agent, iterations=10)
        remote_time = await benchmark_remote(remote, iterations=10)

        overhead_ms = remote_time - direct_time
        overhead_pct = (overhead_ms / direct_time) * 100

        print(f"Direct (baseline):  {direct_time:.2f} ms per call")
        print(f"Remote (adapter):   {remote_time:.2f} ms per call")
        print(f"\nAbsolute overhead:  {overhead_ms:.2f} ms")
        print(f"Relative overhead:  {overhead_pct:.2f}%")

        if overhead_pct < 5.0:
            print(f"\n✅ PASS: Overhead {overhead_pct:.2f}% < 5% target")
        else:
            print(f"\n⚠️  WARN: Overhead {overhead_pct:.2f}% > 5% target")

        print(f"\n💡 Production context:")
        print(f"   - Protocol overhead: ~0.1ms")
        print(f"   - Typical LLM call: 100-1000ms")
        print(f"   - Real impact: <0.1% of total latency")

        await server.stop()

    # Message size benchmarks
    await benchmark_message_sizes()

    print("\n" + "=" * 60)
    print("Benchmarks complete!")
    print()


if __name__ == "__main__":
    asyncio.run(main())
