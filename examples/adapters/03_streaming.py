"""Streaming example.

This example demonstrates how to use streaming with the protocol adapter.
Streaming allows agents to send responses incrementally, which is useful for:
- Long-running operations (progress updates)
- LLM streaming (tokens as they're generated)
- Real-time data processing
"""

import asyncio
import tempfile
from pathlib import Path

from agenkit import Agent, Message
from agenkit.adapters.python import LocalAgent, RemoteAgent


class NewsAgent(Agent):
    """Agent that streams news articles one at a time."""

    @property
    def name(self) -> str:
        return "news"

    async def process(self, message: Message) -> Message:
        """Non-streaming response with all articles."""
        articles = [
            "Breaking: Python 4.0 announced",
            "AI agent frameworks gain popularity",
            "Streaming protocols improve user experience",
        ]
        return Message(role="agent", content="\n".join(articles))

    async def stream(self, message: Message):
        """Stream articles one at a time."""
        articles = [
            "Breaking: Python 4.0 announced with major improvements",
            "AI agent frameworks gain popularity in enterprise",
            "Streaming protocols improve user experience dramatically",
        ]

        for i, article in enumerate(articles, 1):
            # Simulate fetching/processing delay
            await asyncio.sleep(0.5)

            # Yield article with metadata
            yield Message(
                role="agent",
                content=article,
                metadata={"article_number": i, "total": len(articles)},
            )


class LLMAgent(Agent):
    """Agent that simulates LLM token streaming."""

    @property
    def name(self) -> str:
        return "llm"

    async def process(self, message: Message) -> Message:
        """Return complete response."""
        response = f"This is a complete response to: {message.content}"
        return Message(role="agent", content=response)

    async def stream(self, message: Message):
        """Stream response token by token."""
        response = f"This is a simulated streaming response to your message: {message.content}"
        words = response.split()

        for i, word in enumerate(words):
            # Simulate token generation delay
            await asyncio.sleep(0.1)

            # Yield word as a token
            # In real LLM streaming, you'd yield partial text
            yield Message(role="agent", content=word + " ", metadata={"token_index": i})


async def main():
    """Run streaming examples."""
    print("=== Streaming Examples ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Example 1: News streaming
        print("1. News Agent - Streaming Articles")
        print("-" * 50)

        news_agent = NewsAgent()
        news_socket = tmppath / "news.sock"
        news_server = LocalAgent(news_agent, endpoint=f"unix://{news_socket}")
        await news_server.start()

        # Connect remote client
        remote_news = RemoteAgent("news", endpoint=f"unix://{news_socket}")

        # Stream articles
        message = Message(role="user", content="Get me the latest news")
        print(f"User: {message.content}\n")

        async for article in remote_news.stream(message):
            print(f"Article {article.metadata['article_number']}/{article.metadata['total']}:")
            print(f"  {article.content}\n")

        await news_server.stop()

        # Example 2: LLM token streaming
        print("\n2. LLM Agent - Streaming Tokens")
        print("-" * 50)

        llm_agent = LLMAgent()
        llm_socket = tmppath / "llm.sock"
        llm_server = LocalAgent(llm_agent, endpoint=f"unix://{llm_socket}")
        await llm_server.start()

        # Connect remote client
        remote_llm = RemoteAgent("llm", endpoint=f"unix://{llm_socket}")

        # Stream tokens
        message = Message(role="user", content="explain streaming")
        print(f"User: {message.content}\n")
        print("Agent: ", end="", flush=True)

        async for token in remote_llm.stream(message):
            print(token.content, end="", flush=True)

        print("\n")
        await llm_server.stop()

        # Example 3: Comparing streaming vs non-streaming
        print("\n3. Streaming vs Non-Streaming Comparison")
        print("-" * 50)

        news_agent = NewsAgent()
        news_socket = tmppath / "news2.sock"
        news_server = LocalAgent(news_agent, endpoint=f"unix://{news_socket}")
        await news_server.start()

        remote_news = RemoteAgent("news", endpoint=f"unix://{news_socket}")
        message = Message(role="user", content="Get news")

        # Non-streaming (wait for complete response)
        print("Non-streaming: Waiting for complete response...")
        import time

        start = time.time()
        response = await remote_news.process(message)
        end = time.time()

        print(f"Received after {end - start:.1f}s:")
        print(response.content)

        print("\nStreaming: Receiving as available...")
        start = time.time()
        first_chunk_time = None
        i = 0

        async for chunk in remote_news.stream(message):
            if i == 0:
                first_chunk_time = time.time() - start
            print(f"  [{time.time() - start:.1f}s] {chunk.content}")
            i += 1

        print(f"\nFirst chunk after {first_chunk_time:.1f}s")
        print(f"All chunks after {time.time() - start:.1f}s")

        await news_server.stop()

    print("\nDone!\n")


if __name__ == "__main__":
    asyncio.run(main())
