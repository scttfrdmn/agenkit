#!/usr/bin/env python3
"""gRPC Transport Example.

This example demonstrates the gRPC transport for Agenkit, showing:
- Setting up gRPC server and client
- Regular request/response communication
- Streaming responses
- Concurrent clients
- Metadata handling
- Error handling and recovery

WHY USE GRPC?
==============

gRPC is ideal when you need:

1. **High Performance**: gRPC uses HTTP/2 and Protocol Buffers for efficient
   binary encoding, making it significantly faster than JSON-based protocols.

2. **Strong Typing**: Protocol Buffers provide strongly-typed schemas that are
   validated at compile time, reducing runtime errors.

3. **Bidirectional Streaming**: Built-in support for client streaming, server
   streaming, and bidirectional streaming over a single connection.

4. **Language Interoperability**: gRPC has native support for many languages,
   making it perfect for polyglot microservices.

5. **Built-in Features**: Native support for authentication, load balancing,
   retries, timeouts, and health checks.

6. **Connection Multiplexing**: HTTP/2 enables multiple concurrent RPC calls
   over a single TCP connection.

WHEN TO USE EACH TRANSPORT:
============================

Use **gRPC** when:
- You need high-performance RPC for microservices
- You're building polyglot systems (Python, Go, Java, etc.)
- You want strong typing and code generation
- You need advanced features like streaming, retries, load balancing
- Performance and scalability are critical

Use **WebSocket** when:
- You need real-time bidirectional communication
- You're building browser-based applications
- You want simpler deployment (works through HTTP proxies)

Use **HTTP** when:
- You need simple REST APIs
- You want maximum compatibility
- You're exposing public APIs

Use **TCP/Unix Sockets** when:
- You need raw socket communication
- You're building internal tools
- You don't need gRPC's advanced features
"""

import asyncio
import time
from agenkit import Agent, Message
from agenkit.adapters.python import GRPCServer, GRPCTransport, RemoteAgent


class EchoAgent(Agent):
    """Simple echo agent that responds to messages."""

    @property
    def name(self) -> str:
        return "echo"

    async def process(self, message: Message) -> Message:
        """Echo the message back."""
        return Message(
            role="agent",
            content=f"Echo: {message.content}",
            metadata={"original": message.content}
        )


class StreamingEchoAgent(Agent):
    """Echo agent that streams response word-by-word."""

    @property
    def name(self) -> str:
        return "streaming_echo"

    async def process(self, message: Message) -> Message:
        """Return complete echoed message."""
        return Message(
            role="agent",
            content=f"Echo: {message.content}"
        )

    async def stream(self, message: Message):
        """Stream the echo word by word."""
        words = str(message.content).split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.1)  # Simulate processing delay
            yield Message(
                role="agent",
                content=word,
                metadata={"word_index": i, "total_words": len(words)}
            )


class MetadataAgent(Agent):
    """Agent that processes and returns metadata."""

    @property
    def name(self) -> str:
        return "metadata"

    async def process(self, message: Message) -> Message:
        """Process message and include metadata in response."""
        metadata = message.metadata or {}

        # Add response metadata
        response_metadata = {
            "received_at": time.time(),
            "message_length": len(str(message.content)),
            "user_metadata": metadata,
            "processed_by": self.name
        }

        return Message(
            role="agent",
            content=f"Processed: {message.content}",
            metadata=response_metadata
        )


async def scenario_1_basic_communication():
    """Scenario 1: Basic gRPC Communication.

    WHY: Demonstrate the simplest gRPC usage pattern - unary RPC where
    the client sends a single request and receives a single response.
    This is the foundation of gRPC communication.
    """
    print("=" * 70)
    print("SCENARIO 1: Basic gRPC Communication")
    print("=" * 70)
    print()
    print("Starting gRPC server on localhost:50051...")

    # Create and start gRPC server
    agent = EchoAgent()
    server = GRPCServer(agent, "localhost:50051")
    await server.start()

    try:
        print("Server started! Creating client...\n")

        # Create gRPC transport
        transport = GRPCTransport("grpc://localhost:50051")
        await transport.connect()

        # Create remote agent using the transport
        remote = RemoteAgent("echo", transport=transport)

        # Send messages
        messages = [
            "Hello, gRPC!",
            "This is fast and efficient.",
            "Protocol Buffers are awesome!",
        ]

        for msg_content in messages:
            print(f"User: {msg_content}")
            message = Message(role="user", content=msg_content)
            response = await remote.process(message)
            print(f"Agent: {response.content}")
            print(f"Metadata: {response.metadata}\n")

        # Clean up transport
        await transport.close()

        print("Benefits demonstrated:")
        print("  - Simple request/response pattern")
        print("  - Efficient binary encoding (Protocol Buffers)")
        print("  - Type-safe communication")
        print()

    finally:
        await server.stop()
        print("Server stopped.\n")


async def scenario_2_streaming_responses():
    """Scenario 2: Streaming Responses over gRPC.

    WHY: Show how gRPC efficiently handles streaming data. Unlike HTTP
    where you'd need SSE or polling, gRPC has native streaming support
    with HTTP/2, making it perfect for real-time data delivery.
    """
    print("=" * 70)
    print("SCENARIO 2: Streaming Responses over gRPC")
    print("=" * 70)
    print()
    print("Starting gRPC server on localhost:50052...")

    # Create and start gRPC server
    agent = StreamingEchoAgent()
    server = GRPCServer(agent, "localhost:50052")
    await server.start()

    try:
        print("Server started! Creating client...\n")

        # Create gRPC transport
        transport = GRPCTransport("grpc://localhost:50052")
        await transport.connect()

        # Create remote agent
        remote = RemoteAgent("streaming_echo", transport=transport)

        # Test non-streaming first
        print("--- Non-Streaming Mode ---")
        message = Message(role="user", content="The quick brown fox jumps")
        print(f"User: {message.content}")
        response = await remote.process(message)
        print(f"Agent: {response.content}\n")

        await asyncio.sleep(0.5)

        # Test streaming
        print("--- Streaming Mode ---")
        message = Message(role="user", content="gRPC streaming is efficient and fast")
        print(f"User: {message.content}")
        print("Agent: ", end="", flush=True)

        start_time = time.time()
        async for chunk in remote.stream(message):
            print(f"{chunk.content} ", end="", flush=True)
        elapsed = time.time() - start_time
        print(f"\n\nStreaming completed in {elapsed:.2f}s")

        # Clean up transport
        await transport.close()

        print("\nBenefits demonstrated:")
        print("  - Native streaming support over HTTP/2")
        print("  - Low latency for real-time data")
        print("  - Single connection for entire stream")
        print("  - Efficient for large responses")
        print()

    finally:
        await server.stop()
        print("Server stopped.\n")


async def scenario_3_concurrent_clients():
    """Scenario 3: Multiple Concurrent Clients.

    WHY: Demonstrate gRPC's ability to handle multiple concurrent requests
    efficiently. HTTP/2 connection multiplexing allows many concurrent RPCs
    over a single TCP connection, reducing overhead.
    """
    print("=" * 70)
    print("SCENARIO 3: Multiple Concurrent Clients")
    print("=" * 70)
    print()
    print("Starting gRPC server on localhost:50053...")

    # Create and start gRPC server
    agent = EchoAgent()
    server = GRPCServer(agent, "localhost:50053")
    await server.start()

    try:
        print("Server started! Creating multiple concurrent clients...\n")

        # Create multiple clients
        num_clients = 10

        async def send_request(client_id: int):
            """Send a request from a client."""
            # Each client creates its own transport
            transport = GRPCTransport("grpc://localhost:50053")
            await transport.connect()

            remote = RemoteAgent("echo", transport=transport)

            message = Message(
                role="user",
                content=f"Message from client {client_id}"
            )

            start = time.time()
            response = await remote.process(message)
            elapsed = time.time() - start

            print(f"Client {client_id:2d}: {response.content} (took {elapsed*1000:.1f}ms)")

            await transport.close()

        # Send concurrent requests
        start_time = time.time()
        tasks = [send_request(i) for i in range(num_clients)]
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        print(f"\nAll {num_clients} clients completed in {total_time:.2f}s")
        print(f"Average time per request: {(total_time/num_clients)*1000:.1f}ms")

        print("\nBenefits demonstrated:")
        print("  - Connection multiplexing over HTTP/2")
        print("  - Efficient handling of concurrent requests")
        print("  - Low per-request overhead")
        print("  - Scalable for many clients")
        print()

    finally:
        await server.stop()
        print("Server stopped.\n")


async def scenario_4_metadata_handling():
    """Scenario 4: Metadata Handling.

    WHY: Show how gRPC preserves and propagates metadata through calls.
    This is useful for tracing, authentication, request context, and
    passing additional information without modifying the message schema.
    """
    print("=" * 70)
    print("SCENARIO 4: Metadata Handling")
    print("=" * 70)
    print()
    print("Starting gRPC server on localhost:50054...")

    # Create and start gRPC server
    agent = MetadataAgent()
    server = GRPCServer(agent, "localhost:50054")
    await server.start()

    try:
        print("Server started! Creating client...\n")

        # Create gRPC transport
        transport = GRPCTransport("grpc://localhost:50054")
        await transport.connect()

        # Create remote agent
        remote = RemoteAgent("metadata", transport=transport)

        # Send messages with metadata
        test_cases = [
            {
                "content": "Request with user ID",
                "metadata": {"user_id": "user123", "session": "abc-def"}
            },
            {
                "content": "Request with trace ID",
                "metadata": {"trace_id": "trace-456", "priority": "high"}
            },
            {
                "content": "Request with custom headers",
                "metadata": {"custom": "value", "version": "1.0"}
            },
        ]

        for i, test in enumerate(test_cases, 1):
            print(f"--- Test {i} ---")
            print(f"User: {test['content']}")
            print(f"Input metadata: {test['metadata']}")

            message = Message(
                role="user",
                content=test["content"],
                metadata=test["metadata"]
            )

            response = await remote.process(message)
            print(f"Agent: {response.content}")
            print(f"Response metadata: {response.metadata}\n")

        # Clean up transport
        await transport.close()

        print("Benefits demonstrated:")
        print("  - Metadata propagation through gRPC calls")
        print("  - Useful for tracing, authentication, context")
        print("  - Preserved across the call chain")
        print()

    finally:
        await server.stop()
        print("Server stopped.\n")


async def scenario_5_error_handling():
    """Scenario 5: Error Handling and Recovery.

    WHY: Demonstrate how gRPC errors are handled gracefully, with proper
    error codes and details. gRPC has rich error handling with standard
    status codes, making it easier to handle failures properly.
    """
    print("=" * 70)
    print("SCENARIO 5: Error Handling and Recovery")
    print("=" * 70)
    print()

    # Test 1: Connection refused (server not running)
    print("--- Test 1: Connection to unavailable server ---")
    try:
        transport = GRPCTransport("grpc://localhost:59999")  # Port with no server
        await transport.connect()

        remote = RemoteAgent("echo", transport=transport)
        message = Message(role="user", content="Hello")

        # This should work initially (gRPC channels are lazy)
        print("Connected to gRPC channel (lazy connection)")

        # But the actual RPC will fail
        try:
            response = await asyncio.wait_for(remote.process(message), timeout=2.0)
            print(f"Unexpected success: {response.content}")
        except asyncio.TimeoutError:
            print("ERROR: Request timed out (server unavailable)")
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")

        await transport.close()
    except Exception as e:
        print(f"ERROR during setup: {type(e).__name__}: {e}")

    print()

    # Test 2: Server shutdown during communication
    print("--- Test 2: Server shutdown during communication ---")
    agent = EchoAgent()
    server = GRPCServer(agent, "localhost:50055")
    await server.start()
    print("Server started")

    try:
        transport = GRPCTransport("grpc://localhost:50055")
        await transport.connect()

        remote = RemoteAgent("echo", transport=transport)

        # Send successful request
        message = Message(role="user", content="First request")
        response = await remote.process(message)
        print(f"Success: {response.content}")

        # Stop server
        print("Stopping server...")
        await server.stop()
        await asyncio.sleep(0.5)

        # Try to send another request
        print("Attempting request to stopped server...")
        try:
            message = Message(role="user", content="Second request")
            response = await asyncio.wait_for(remote.process(message), timeout=2.0)
            print(f"Unexpected success: {response.content}")
        except asyncio.TimeoutError:
            print("ERROR: Request timed out (server stopped)")
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")

        await transport.close()

    finally:
        # Ensure server is stopped
        await server.stop()

    print()

    # Test 3: Retry and recovery
    print("--- Test 3: Retry and recovery ---")
    server = GRPCServer(agent, "localhost:50056")
    await server.start()
    print("Server started")

    try:
        transport = GRPCTransport("grpc://localhost:50056")
        await transport.connect()

        remote = RemoteAgent("echo", transport=transport)

        # Implement simple retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                message = Message(role="user", content=f"Attempt {attempt + 1}")
                response = await asyncio.wait_for(remote.process(message), timeout=2.0)
                print(f"Success on attempt {attempt + 1}: {response.content}")
                break
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {type(e).__name__}")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    await asyncio.sleep(0.5)
                else:
                    print("Max retries reached")

        await transport.close()

    finally:
        await server.stop()

    print()
    print("Benefits demonstrated:")
    print("  - Graceful error handling with gRPC status codes")
    print("  - Clear error messages and details")
    print("  - Support for retry patterns")
    print("  - Connection state awareness")
    print()


async def main():
    """Run all gRPC examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 23 + "gRPC Transport Demo" + " " * 26 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    # Run scenarios
    await scenario_1_basic_communication()
    await asyncio.sleep(1)

    await scenario_2_streaming_responses()
    await asyncio.sleep(1)

    await scenario_3_concurrent_clients()
    await asyncio.sleep(1)

    await scenario_4_metadata_handling()
    await asyncio.sleep(1)

    await scenario_5_error_handling()

    # Print summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print("gRPC Benefits Demonstrated:")
    print("  ✓ High-performance binary protocol (Protocol Buffers)")
    print("  ✓ Strong typing and schema validation")
    print("  ✓ Native streaming support (Scenario 2)")
    print("  ✓ Efficient concurrent handling (Scenario 3)")
    print("  ✓ Metadata propagation (Scenario 4)")
    print("  ✓ Rich error handling (Scenario 5)")
    print("  ✓ HTTP/2 connection multiplexing")
    print("  ✓ Language interoperability")
    print()
    print("gRPC is perfect for:")
    print("  • High-performance microservices")
    print("  • Polyglot system architectures")
    print("  • Internal APIs requiring low latency")
    print("  • Streaming data (real-time updates, AI responses)")
    print("  • Service-to-service communication")
    print()
    print("Performance characteristics:")
    print("  • ~10x faster than JSON over HTTP for binary data")
    print("  • Lower CPU usage due to efficient encoding")
    print("  • Reduced network bandwidth")
    print("  • Better support for high concurrency")
    print()
    print("For browser-based apps, consider WebSocket.")
    print("For public REST APIs, consider HTTP.")
    print("For maximum performance in controlled environments, use gRPC.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
