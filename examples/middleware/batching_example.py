"""
Batching Middleware Example

This example demonstrates WHY and HOW to use batching middleware for improving
throughput by processing multiple concurrent requests together.

WHY USE BATCHING MIDDLEWARE?
----------------------------
- Improve throughput: Process multiple requests together for better efficiency
- Reduce costs: Use batch API endpoints (e.g., OpenAI batch API) for lower per-request costs
- Amortize overhead: Spread per-request setup costs across multiple requests
- Better resource utilization: Maximize use of available processing capacity
- Reduce network round-trips: Send multiple operations in one call (databases, APIs)

WHEN TO USE:
- LLM batch processing endpoints (OpenAI, Anthropic batch APIs)
- Database bulk operations (INSERT, UPDATE, DELETE multiple records)
- High-throughput data pipelines (log processing, analytics)
- API aggregation services (combining multiple API calls)
- Image/video processing pipelines (batch GPU operations)

WHEN NOT TO USE:
- Real-time interactive applications (adds latency)
- Low-volume APIs (batching overhead not worth it)
- Operations requiring immediate feedback
- When request interdependencies make batching complex
- Single-threaded/sequential processing patterns

TRADE-OFFS:
- Latency vs throughput: Adds wait time but improves overall throughput
- Memory usage: Buffers requests in queue (configure max_queue_size)
- Complexity: Need to handle partial failures within batches
- Tuning required: Finding optimal batch_size and wait_time

CONFIGURATION:
- max_batch_size: Process when this many requests collected (default: 10)
- max_wait_time: Process after this much time (default: 100ms)
- max_queue_size: Maximum pending requests (default: 1000)
"""

import asyncio
import time
from typing import List
from agenkit.interfaces import Agent, Message
from agenkit.middleware import BatchingConfig, BatchingDecorator


# Example 1: LLM Batch Processing Agent
class MockLLMBatchAgent(Agent):
    """
    Simulates an LLM that benefits from batch processing.

    Real-world example: OpenAI Batch API offers 50% cost savings.
    https://platform.openai.com/docs/guides/batch
    """

    def __init__(self):
        self.batch_count = 0
        self.total_processed = 0

    @property
    def name(self) -> str:
        return "llm-batch-processor"

    @property
    def capabilities(self) -> list[str]:
        return ["text-generation", "batch-processing"]

    async def process(self, message: Message) -> Message:
        """Simulate batch-optimized LLM processing."""
        # Simulate per-batch setup overhead (amortized across batch)
        await asyncio.sleep(0.05)

        # Simulate per-request processing
        await asyncio.sleep(0.01)

        self.total_processed += 1

        return Message(
            role="agent",
            content=f"Generated: {message.content}",
            metadata={
                "model": "gpt-4-batch",
                "cost_savings": "50%",  # Batch API pricing
            }
        )


# Example 2: Database Bulk Operations Agent
class MockDatabaseAgent(Agent):
    """
    Simulates database bulk INSERT operations.

    Real-world example: PostgreSQL bulk INSERT is 10-100x faster than
    individual INSERTs due to reduced round-trips and transaction overhead.
    """

    def __init__(self):
        self.db_calls = 0
        self.records_inserted = 0

    @property
    def name(self) -> str:
        return "database-bulk-inserter"

    @property
    def capabilities(self) -> list[str]:
        return ["database", "bulk-operations"]

    async def process(self, message: Message) -> Message:
        """Simulate database record insertion."""
        # Simulate network + connection overhead (amortized in batch)
        await asyncio.sleep(0.02)

        # Simulate actual insert
        await asyncio.sleep(0.001)

        self.db_calls += 1
        self.records_inserted += 1

        return Message(
            role="agent",
            content=f"Inserted: {message.content}",
            metadata={
                "table": "users",
                "operation": "INSERT",
            }
        )


# Example 3: High-Throughput Analytics Agent
class MockAnalyticsAgent(Agent):
    """
    Simulates high-throughput log/event processing.

    Real-world example: Processing millions of events per second in
    analytics pipelines by batching writes to data warehouses.
    """

    def __init__(self):
        self.events_processed = 0

    @property
    def name(self) -> str:
        return "analytics-processor"

    @property
    def capabilities(self) -> list[str]:
        return ["analytics", "stream-processing"]

    async def process(self, message: Message) -> Message:
        """Simulate event processing."""
        # Simulate very fast processing per event
        await asyncio.sleep(0.005)

        self.events_processed += 1

        return Message(
            role="agent",
            content=f"Processed event: {message.content}",
            metadata={
                "pipeline": "clickstream",
                "timestamp": time.time(),
            }
        )


async def example_1_llm_batch_processing():
    """
    Example 1: LLM Batch Processing

    Demonstrates cost savings with batch LLM API endpoints.
    OpenAI Batch API: 50% cost reduction, 24-hour turnaround.
    """
    print("\n" + "="*70)
    print("Example 1: LLM Batch Processing (Cost Optimization)")
    print("="*70)

    print("\nScenario: Processing 20 LLM requests")
    print("Real-world: OpenAI Batch API offers 50% cost savings")
    print("Trade-off: Adds latency but reduces costs significantly\n")

    agent = MockLLMBatchAgent()

    # Configure batching for LLM: larger batches, willing to wait longer
    config = BatchingConfig(
        max_batch_size=5,       # Batch up to 5 requests
        max_wait_time=0.1,      # Wait up to 100ms to fill batch
        max_queue_size=100
    )

    batching_agent = BatchingDecorator(agent, config)

    # Simulate 20 concurrent LLM requests
    print("Sending 20 concurrent LLM requests...")
    start_time = time.time()

    tasks = []
    for i in range(20):
        msg = Message(
            role="user",
            content=f"Summarize document {i+1}"
        )
        tasks.append(batching_agent.process(msg))

    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time

    print(f"✅ Completed in {elapsed:.2f}s")
    print(f"   Total requests: {len(results)}")
    print(f"   Sample result: {results[0].content}")

    # Show batching metrics
    metrics = batching_agent.metrics
    print(f"\n📊 Batching Metrics:")
    print(f"   Total batches: {metrics.total_batches}")
    print(f"   Avg batch size: {metrics.avg_batch_size:.1f}")
    print(f"   Requests/batch ratio: {metrics.total_requests}/{metrics.total_batches}")
    print(f"   💰 Cost savings: ~50% (batch API pricing)")

    await batching_agent.shutdown()


async def example_2_database_bulk_operations():
    """
    Example 2: Database Bulk Operations

    Demonstrates throughput improvement for database operations.
    Bulk INSERT can be 10-100x faster than individual INSERTs.
    """
    print("\n" + "="*70)
    print("Example 2: Database Bulk Operations (Throughput Optimization)")
    print("="*70)

    print("\nScenario: Inserting 50 database records")
    print("Real-world: Bulk INSERT 10-100x faster than individual INSERTs")
    print("Trade-off: Small latency increase, huge throughput gain\n")

    agent = MockDatabaseAgent()

    # Configure batching for database: medium batches, short wait time
    config = BatchingConfig(
        max_batch_size=10,      # Batch up to 10 records
        max_wait_time=0.05,     # Wait max 50ms
        max_queue_size=200
    )

    batching_agent = BatchingDecorator(agent, config)

    # Simulate 50 concurrent database inserts
    print("Inserting 50 user records...")
    start_time = time.time()

    tasks = []
    for i in range(50):
        msg = Message(
            role="user",
            content=f"user_{i+1}@example.com"
        )
        tasks.append(batching_agent.process(msg))

    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time

    print(f"✅ Completed in {elapsed:.2f}s")
    print(f"   Records inserted: {agent.records_inserted}")
    print(f"   DB calls made: {agent.db_calls}")

    # Show batching efficiency
    metrics = batching_agent.metrics
    print(f"\n📊 Batching Metrics:")
    print(f"   Total batches: {metrics.total_batches}")
    print(f"   Avg batch size: {metrics.avg_batch_size:.1f}")
    print(f"   Efficiency gain: ~{50/agent.db_calls:.1f}x fewer DB round-trips")
    print(f"   ⚡ Throughput: {agent.records_inserted/elapsed:.0f} records/sec")

    await batching_agent.shutdown()


async def example_3_high_throughput_analytics():
    """
    Example 3: High-Throughput Analytics

    Demonstrates batching for high-volume event processing.
    Real streaming systems process millions of events per second.
    """
    print("\n" + "="*70)
    print("Example 3: High-Throughput Analytics (Stream Processing)")
    print("="*70)

    print("\nScenario: Processing 100 analytics events")
    print("Real-world: Data pipelines batch events for warehouse writes")
    print("Trade-off: Slight delay acceptable for massive throughput\n")

    agent = MockAnalyticsAgent()

    # Configure batching for analytics: aggressive batching
    config = BatchingConfig(
        max_batch_size=20,      # Large batches for throughput
        max_wait_time=0.05,     # Quick batching
        max_queue_size=500
    )

    batching_agent = BatchingDecorator(agent, config)

    # Simulate 100 concurrent analytics events
    print("Processing 100 clickstream events...")
    start_time = time.time()

    tasks = []
    for i in range(100):
        msg = Message(
            role="user",
            content=f"click_event_{i+1}"
        )
        tasks.append(batching_agent.process(msg))

    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time

    print(f"✅ Completed in {elapsed:.2f}s")
    print(f"   Events processed: {agent.events_processed}")

    # Show batching performance
    metrics = batching_agent.metrics
    print(f"\n📊 Batching Metrics:")
    print(f"   Total batches: {metrics.total_batches}")
    print(f"   Avg batch size: {metrics.avg_batch_size:.1f}")
    print(f"   Avg wait time: {metrics.avg_wait_time*1000:.1f}ms")
    print(f"   ⚡ Throughput: {agent.events_processed/elapsed:.0f} events/sec")

    await batching_agent.shutdown()


async def example_4_partial_failures():
    """
    Example 4: Handling Partial Failures

    Demonstrates how batching handles individual request failures
    without affecting other requests in the batch.
    """
    print("\n" + "="*70)
    print("Example 4: Partial Failure Handling")
    print("="*70)

    print("\nScenario: Batch with some failing requests")
    print("Real-world: Individual requests can fail independently")
    print("Batching isolates failures - only failed requests error out\n")

    # Agent that fails on specific inputs
    class PartialFailAgent(Agent):
        @property
        def name(self) -> str:
            return "partial-fail-agent"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            await asyncio.sleep(0.01)

            # Fail on messages containing "fail"
            if "fail" in message.content.lower():
                raise ValueError(f"Processing failed for: {message.content}")

            return Message(
                role="agent",
                content=f"Success: {message.content}"
            )

    agent = PartialFailAgent()
    config = BatchingConfig(max_batch_size=5, max_wait_time=0.05)
    batching_agent = BatchingDecorator(agent, config)

    # Mix of successful and failing requests
    messages = [
        Message(role="user", content="request_1"),
        Message(role="user", content="FAIL_2"),
        Message(role="user", content="request_3"),
        Message(role="user", content="FAIL_4"),
        Message(role="user", content="request_5"),
    ]

    print("Processing batch with mixed success/failure...")

    results = await asyncio.gather(
        *[batching_agent.process(msg) for msg in messages],
        return_exceptions=True
    )

    # Show results
    print("\nResults:")
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"   ❌ Request {i+1}: {type(result).__name__} - {result}")
        else:
            print(f"   ✅ Request {i+1}: {result.content}")

    metrics = batching_agent.metrics
    print(f"\n📊 Batch Metrics:")
    print(f"   Partial batches: {metrics.partial_batches}")
    print(f"   ℹ️  Only failed requests raised errors - others succeeded")

    await batching_agent.shutdown()


async def example_5_configuration_tuning():
    """
    Example 5: Configuration Tuning

    Demonstrates the impact of different configuration settings
    on latency and throughput.
    """
    print("\n" + "="*70)
    print("Example 5: Configuration Tuning (Latency vs Throughput)")
    print("="*70)

    print("\nComparing different batching configurations:\n")

    # Test configurations
    configs = [
        ("Aggressive (low latency)", BatchingConfig(
            max_batch_size=3,
            max_wait_time=0.01,  # 10ms
        )),
        ("Balanced (default)", BatchingConfig(
            max_batch_size=10,
            max_wait_time=0.1,   # 100ms
        )),
        ("Throughput-optimized", BatchingConfig(
            max_batch_size=20,
            max_wait_time=0.2,   # 200ms
        )),
    ]

    for name, config in configs:
        agent = MockAnalyticsAgent()
        batching_agent = BatchingDecorator(agent, config)

        # Send 30 requests
        start = time.time()
        tasks = [
            batching_agent.process(Message(role="user", content=f"event_{i}"))
            for i in range(30)
        ]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start

        metrics = batching_agent.metrics
        print(f"{name}:")
        print(f"   Total time: {elapsed:.3f}s")
        print(f"   Batches: {metrics.total_batches}")
        print(f"   Avg batch: {metrics.avg_batch_size:.1f} requests")
        print(f"   Avg wait: {metrics.avg_wait_time*1000:.1f}ms")
        print(f"   Throughput: {30/elapsed:.0f} req/sec\n")

        await batching_agent.shutdown()


async def main():
    """Run all batching examples."""
    print("\n" + "="*70)
    print("BATCHING MIDDLEWARE EXAMPLES")
    print("="*70)
    print("\nBatching collects concurrent requests and processes them together")
    print("to improve throughput at the cost of added latency.")
    print("\nKey benefits: Lower costs, better throughput, fewer round-trips")
    print("Key trade-off: Adds wait time (tune max_wait_time to control)")

    # Run all examples
    await example_1_llm_batch_processing()
    await example_2_database_bulk_operations()
    await example_3_high_throughput_analytics()
    await example_4_partial_failures()
    await example_5_configuration_tuning()

    print("\n" + "="*70)
    print("BATCHING BEST PRACTICES")
    print("="*70)
    print("""
1. Choose batch size based on your use case:
   - LLM APIs: 5-50 (API limits vary)
   - Database: 10-100 (balance transaction size)
   - Analytics: 100-1000 (maximize throughput)

2. Tune wait time for your latency requirements:
   - Interactive: 10-50ms (responsive UX)
   - Background: 100-500ms (balanced)
   - Batch jobs: 1-5s (maximize efficiency)

3. Handle partial failures gracefully:
   - Use return_exceptions=True with asyncio.gather()
   - Check metrics.partial_batches to monitor health
   - Log failures for debugging

4. Monitor metrics:
   - avg_batch_size: Should be close to max_batch_size
   - avg_wait_time: Should match your SLA
   - partial_batches: Should be low

5. Set queue limits to prevent memory issues:
   - Set max_queue_size based on traffic patterns
   - Monitor queue depth in production
   - Use backpressure signals upstream if needed
""")


if __name__ == "__main__":
    asyncio.run(main())
