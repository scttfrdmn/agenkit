"""Large argument streaming example.

This example demonstrates:
- Streaming large tool arguments in chunks
- Efficient transmission of large payloads
- Frontend buffering and reconstruction
"""

import asyncio
from typing import Any

from agenkit import Agent, Message, Tool, ToolResult
from agenkit.protocols.agui import AGUIAdapter, ToolCallTracker


class DataProcessingTool(Tool):
    """Tool that processes large data payloads."""

    @property
    def name(self) -> str:
        return "process_data"

    @property
    def description(self) -> str:
        return "Process large datasets"

    async def execute(self, **kwargs) -> ToolResult:
        """Process the data."""
        data = kwargs.get("data", [])
        filters = kwargs.get("filters", {})

        # Simulate processing
        await asyncio.sleep(0.5)

        processed_count = len(data)
        filtered_count = sum(
            1 for item in data if all(item.get(k) == v for k, v in filters.items())
        )

        return ToolResult(
            success=True,
            data={
                "total": processed_count,
                "filtered": filtered_count,
                "summary": f"Processed {processed_count} items, {filtered_count} matched filters",
            },
        )


class DataAgent(Agent):
    """Agent with data processing tool."""

    def __init__(self):
        self._tool = DataProcessingTool()
        self._tracker = ToolCallTracker()

    @property
    def name(self) -> str:
        return "DataAgent"

    async def process(self, message: Message) -> Message:
        """Process message with tool call."""
        # Generate large dataset
        large_dataset = [
            {"id": i, "value": i * 2, "category": "A" if i % 2 == 0 else "B"} for i in range(1000)
        ]

        response_parts = []

        # Track tool call and collect events
        async for event in self._tracker.track_call(
            tool=self._tool,
            args={
                "data": large_dataset,
                "filters": {"category": "A"},
            },
            stream_args=True,
            arg_chunk_size=200,  # Stream in 200-char chunks
        ):
            if event.type == "tool_call_args":
                response_parts.append(f"📤 Streaming args: {len(event.delta)} chars")
            elif event.type == "tool_call_result":
                result = event.content
                response_parts.append(f"✅ Result: {result['summary']}")

        return Message(role="assistant", content="\n".join(response_parts))


async def demo_direct_streaming():
    """Demonstrate direct tool streaming."""
    print("Direct Tool Call Streaming Demo")
    print("=" * 60)
    print()

    # Create tool and tracker
    tool = DataProcessingTool()
    tracker = ToolCallTracker()

    # Generate large dataset
    large_dataset = [
        {"id": i, "value": i * 2, "category": "A" if i % 2 == 0 else "B"} for i in range(1000)
    ]

    # Track tool call with streaming
    events = []

    async for event in tracker.track_call(
        tool=tool,
        args={"data": large_dataset, "filters": {"category": "A"}},
        stream_args=True,
        arg_chunk_size=200,
    ):
        events.append(event)

        if event.type == "tool_call_start":
            print(f"🔧 Tool: {event.tool_call_name}")

        elif event.type == "tool_call_args":
            print(f"  📤 Chunk: {len(event.delta)} chars")

        elif event.type == "tool_call_end":
            print(f"  ✓ Arguments transmitted")

        elif event.type == "tool_call_result":
            print(f"  ✅ Result: {event.content}")

    print()

    # Show statistics
    print("Statistics:")
    print("-" * 60)
    arg_events = [e for e in events if e.type == "tool_call_args"]
    total_arg_chars = sum(len(e.delta) for e in arg_events)
    print(f"  • Argument chunks: {len(arg_events)}")
    print(f"  • Total argument size: {total_arg_chars:,} chars")
    if len(arg_events) > 0:
        print(f"  • Average chunk size: {total_arg_chars // len(arg_events)} chars")
    print()


async def demo_via_adapter():
    """Demonstrate streaming via adapter."""
    print("\nVia AGUIAdapter")
    print("=" * 60)
    print()

    # Create agent and adapter
    agent = DataAgent()
    adapter = AGUIAdapter(agent, chunk_size=30)

    # Test with large arguments
    async for event in adapter.stream_events(
        message=Message(role="user", content="Process data"),
        thread_id="data-1",
    ):
        if event.type == "text_message_content":
            print(event.delta, end="", flush=True)

    print("\n")


async def main():
    """Run large argument streaming example."""
    print("=" * 60)
    print("Large Argument Streaming Example")
    print("=" * 60)
    print()

    # Demo 1: Direct tool call tracking
    await demo_direct_streaming()

    # Demo 2: Via adapter
    await demo_via_adapter()


if __name__ == "__main__":
    asyncio.run(main())
