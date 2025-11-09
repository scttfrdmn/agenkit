"""Tests for streaming support in protocol adapter."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from agenkit import Agent, Message
from agenkit.adapters.python import LocalAgent, RemoteAgent


class StreamingAgent(Agent):
    """Test agent that supports streaming."""

    @property
    def name(self) -> str:
        return "streaming"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Processed: {message.content}")

    async def stream(self, message: Message):
        """Stream multiple response chunks."""
        # Simulate streaming multiple chunks
        for i in range(5):
            await asyncio.sleep(0.01)  # Simulate processing delay
            yield Message(role="agent", content=f"Chunk {i}: {message.content}")


class NonStreamingAgent(Agent):
    """Test agent that does NOT support streaming."""

    @property
    def name(self) -> str:
        return "non_streaming"

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Processed: {message.content}")


@pytest.mark.asyncio
class TestStreaming:
    """Tests for streaming functionality."""

    async def test_basic_streaming(self):
        """Test basic streaming with Unix socket."""
        # Start server
        agent = StreamingAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "stream.sock"
            server = LocalAgent(agent, endpoint=f"unix://{socket_path}")
            await server.start()

            try:
                # Create client
                remote = RemoteAgent("streaming", endpoint=f"unix://{socket_path}")

                # Test streaming
                message = Message(role="user", content="test")
                chunks = []
                async for chunk in remote.stream(message):
                    chunks.append(chunk)

                # Verify we got all chunks
                assert len(chunks) == 5
                for i, chunk in enumerate(chunks):
                    assert chunk.role == "agent"
                    assert f"Chunk {i}:" in chunk.content
                    assert "test" in chunk.content

            finally:
                await server.stop()

    async def test_streaming_tcp(self):
        """Test streaming over TCP transport."""
        # Start server
        agent = StreamingAgent()
        server = LocalAgent(agent, endpoint="tcp://127.0.0.1:9900")
        await server.start()

        try:
            # Create client
            remote = RemoteAgent("streaming", endpoint="tcp://127.0.0.1:9900")

            # Test streaming
            message = Message(role="user", content="tcp_test")
            chunks = []
            async for chunk in remote.stream(message):
                chunks.append(chunk)

            # Verify chunks
            assert len(chunks) == 5
            for i, chunk in enumerate(chunks):
                assert f"Chunk {i}:" in chunk.content
                assert "tcp_test" in chunk.content

        finally:
            await server.stop()

    async def test_streaming_empty(self):
        """Test agent that yields no chunks."""

        class EmptyStreamAgent(Agent):
            @property
            def name(self) -> str:
                return "empty"

            async def process(self, message: Message) -> Message:
                return Message(role="agent", content="done")

            async def stream(self, message: Message):
                # Yield nothing
                if False:
                    yield Message(role="agent", content="never")

        agent = EmptyStreamAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "empty.sock"
            server = LocalAgent(agent, endpoint=f"unix://{socket_path}")
            await server.start()

            try:
                remote = RemoteAgent("empty", endpoint=f"unix://{socket_path}")

                # Should complete without yielding anything
                message = Message(role="user", content="test")
                chunks = []
                async for chunk in remote.stream(message):
                    chunks.append(chunk)

                assert len(chunks) == 0

            finally:
                await server.stop()

    async def test_streaming_large_chunks(self):
        """Test streaming with large message chunks."""

        class LargeChunkAgent(Agent):
            @property
            def name(self) -> str:
                return "large"

            async def process(self, message: Message) -> Message:
                return Message(role="agent", content="done")

            async def stream(self, message: Message):
                # Yield large chunks
                for i in range(3):
                    large_content = f"Chunk {i}: " + ("x" * 10000)  # 10KB per chunk
                    yield Message(role="agent", content=large_content)

        agent = LargeChunkAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "large.sock"
            server = LocalAgent(agent, endpoint=f"unix://{socket_path}")
            await server.start()

            try:
                remote = RemoteAgent("large", endpoint=f"unix://{socket_path}")

                message = Message(role="user", content="test")
                chunks = []
                async for chunk in remote.stream(message):
                    chunks.append(chunk)

                assert len(chunks) == 3
                for i, chunk in enumerate(chunks):
                    assert f"Chunk {i}:" in chunk.content
                    assert len(chunk.content) > 10000

            finally:
                await server.stop()

    async def test_streaming_error_in_stream(self):
        """Test error handling during streaming."""

        class ErrorStreamAgent(Agent):
            @property
            def name(self) -> str:
                return "error"

            async def process(self, message: Message) -> Message:
                return Message(role="agent", content="done")

            async def stream(self, message: Message):
                # Yield one chunk, then raise error
                yield Message(role="agent", content="Chunk 0")
                raise ValueError("Stream error!")

        agent = ErrorStreamAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "error.sock"
            server = LocalAgent(agent, endpoint=f"unix://{socket_path}")
            await server.start()

            try:
                remote = RemoteAgent("error", endpoint=f"unix://{socket_path}")

                message = Message(role="user", content="test")
                chunks = []

                with pytest.raises(Exception):  # Should raise error from agent
                    async for chunk in remote.stream(message):
                        chunks.append(chunk)

                # Should have gotten at least the first chunk
                assert len(chunks) >= 1

            finally:
                await server.stop()

    async def test_streaming_multiple_clients(self):
        """Test multiple clients streaming concurrently."""
        agent = StreamingAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "multi.sock"
            server = LocalAgent(agent, endpoint=f"unix://{socket_path}")
            await server.start()

            try:
                # Create multiple clients
                remotes = [
                    RemoteAgent("streaming", endpoint=f"unix://{socket_path}")
                    for _ in range(3)
                ]

                # Stream from all clients concurrently
                async def collect_chunks(remote, msg):
                    chunks = []
                    async for chunk in remote.stream(msg):
                        chunks.append(chunk)
                    return chunks

                messages = [Message(role="user", content=f"client_{i}") for i in range(3)]
                results = await asyncio.gather(
                    *[collect_chunks(r, m) for r, m in zip(remotes, messages)]
                )

                # Each client should get all chunks
                for i, chunks in enumerate(results):
                    assert len(chunks) == 5
                    for chunk in chunks:
                        assert f"client_{i}" in chunk.content

            finally:
                await server.stop()

    async def test_non_streaming_agent_error(self):
        """Test calling stream() on agent that doesn't support it."""
        agent = NonStreamingAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "nostream.sock"
            server = LocalAgent(agent, endpoint=f"unix://{socket_path}")
            await server.start()

            try:
                remote = RemoteAgent("non_streaming", endpoint=f"unix://{socket_path}")

                message = Message(role="user", content="test")

                # Should raise NotImplementedError from the agent
                with pytest.raises(Exception):  # RemoteExecutionError wrapping NotImplementedError
                    async for chunk in remote.stream(message):
                        pass

            finally:
                await server.stop()

    async def test_streaming_metadata_preserved(self):
        """Test that message metadata is preserved in streaming."""

        class MetadataStreamAgent(Agent):
            @property
            def name(self) -> str:
                return "metadata"

            async def process(self, message: Message) -> Message:
                return Message(role="agent", content="done")

            async def stream(self, message: Message):
                # Yield chunks with metadata
                for i in range(3):
                    yield Message(
                        role="agent",
                        content=f"Chunk {i}",
                        metadata={"chunk_id": i, "original": message.metadata},
                    )

        agent = MetadataStreamAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "meta.sock"
            server = LocalAgent(agent, endpoint=f"unix://{socket_path}")
            await server.start()

            try:
                remote = RemoteAgent("metadata", endpoint=f"unix://{socket_path}")

                message = Message(role="user", content="test", metadata={"key": "value"})
                chunks = []
                async for chunk in remote.stream(message):
                    chunks.append(chunk)

                assert len(chunks) == 3
                for i, chunk in enumerate(chunks):
                    assert chunk.metadata["chunk_id"] == i
                    assert chunk.metadata["original"]["key"] == "value"

            finally:
                await server.stop()
