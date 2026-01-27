"""Frontend visualization example for tool calls.

This example demonstrates:
- Real-time tool call visualization
- Progress bars and status updates
- Tool execution timeline
- Result formatting
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

from agenkit import Agent, Message, Tool, ToolResult
from agenkit.protocols.agui import AGUIAdapter, ProgressReporter, ToolCallTracker


class SearchTool(Tool):
    """Simulates search with progress."""

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search for information"

    async def execute(self, **kwargs) -> ToolResult:
        """Execute search."""
        query = kwargs.get("query", "")
        progress_reporter: Optional[ProgressReporter] = kwargs.get("progress_reporter")

        results = []

        # Simulate search phases
        phases = [
            (0.2, "Indexing query..."),
            (0.4, "Searching databases..."),
            (0.6, "Ranking results..."),
            (0.8, "Applying filters..."),
            (1.0, "Formatting output..."),
        ]

        for progress, status in phases:
            await asyncio.sleep(0.3)
            if progress_reporter:
                progress_reporter.report(progress, status)

        results = [
            {"title": f"Result {i+1}", "snippet": f"Information about {query}"}
            for i in range(3)
        ]

        return ToolResult(
            success=True,
            data={"query": query, "count": len(results), "results": results},
        )


class CalculatorTool(Tool):
    """Simulates calculation with steps."""

    @property
    def name(self) -> str:
        return "calculate"

    @property
    def description(self) -> str:
        return "Perform calculations"

    async def execute(self, **kwargs) -> ToolResult:
        """Execute calculation."""
        expression = kwargs.get("expression", "1+1")
        progress_reporter: Optional[ProgressReporter] = kwargs.get("progress_reporter")

        # Simulate calculation steps
        if progress_reporter:
            progress_reporter.report(0.3, "Parsing expression...")
        await asyncio.sleep(0.2)

        if progress_reporter:
            progress_reporter.report(0.6, "Evaluating...")
        await asyncio.sleep(0.2)

        if progress_reporter:
            progress_reporter.report(0.9, "Formatting result...")
        await asyncio.sleep(0.2)

        # Safely evaluate simple expressions
        try:
            result = eval(expression, {"__builtins__": {}}, {})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

        if progress_reporter:
            progress_reporter.report(1.0, "Complete")

        return ToolResult(success=True, data={"expression": expression, "result": result})


class VisualizationAgent(Agent):
    """Agent that demonstrates tool visualization."""

    def __init__(self):
        self._search_tool = SearchTool()
        self._calc_tool = CalculatorTool()
        self._tracker = ToolCallTracker()

    @property
    def name(self) -> str:
        return "VisualizationAgent"

    async def process(self, message: Message) -> Message:
        """Process with visualized tool calls."""
        content = message.content.lower()

        if "search" in content:
            # Extract query
            query = content.replace("search", "").replace("for", "").strip()
            if not query:
                query = "information"

            async for event in self._tracker.track_call(
                tool=self._search_tool,
                args={"query": query},
                stream_args=False,
                on_progress=True,
            ):
                if event.type == "tool_call_result" and event.content.get("results"):
                    results = event.content["results"]
                    return Message(
                        role="assistant",
                        content=f"Found {len(results)} results for '{query}':\n"
                        + "\n".join(f"  • {r['title']}" for r in results),
                    )

            return Message(role="assistant", content="Search completed")

        elif "calculate" in content:
            # Extract expression
            expr = content.replace("calculate", "").strip()
            if not expr:
                expr = "2+2"

            async for event in self._tracker.track_call(
                tool=self._calc_tool,
                args={"expression": expr},
                stream_args=False,
                on_progress=True,
            ):
                if event.type == "tool_call_result":
                    if event.content:
                        return Message(
                            role="assistant",
                            content=f"Result: {expr} = {event.content.get('result')}",
                        )

            return Message(role="assistant", content="Calculation completed")

        else:
            return Message(
                role="assistant",
                content=(
                    "Try:\n"
                    "  • 'search for python'\n"
                    "  • 'calculate 42 * 3.14'"
                ),
            )


async def visualize_tool_execution():
    """Demonstrate tool execution visualization."""
    print("=" * 60)
    print("Tool Call Visualization Example")
    print("=" * 60)
    print()

    agent = VisualizationAgent()
    adapter = AGUIAdapter(agent, chunk_size=40)

    # Track tool execution timeline
    timeline = []

    # Scenario 1: Search with progress visualization
    print("Scenario 1: Search Tool")
    print("-" * 60)

    start_time = datetime.now()

    async for event in adapter.stream_events(
        message=Message(role="user", content="search for machine learning"),
        thread_id="viz-1",
    ):
        elapsed = (datetime.now() - start_time).total_seconds()
        timeline.append((elapsed, event.type))

        if event.type == "tool_call_start":
            print(f"\n🔧 Tool: {event.tool_call_name}")
            print(f"├─ Started at: {elapsed:.2f}s")

        elif event.type == "tool_call_progress":
            percentage = int(event.progress * 100)
            bar = "█" * (percentage // 5) + "░" * (20 - percentage // 5)
            print(f"├─ [{bar}] {percentage}% - {event.status or ''}")

        elif event.type == "tool_call_result":
            print(f"└─ Completed at: {elapsed:.2f}s")
            print(f"\n📊 Result: {event.content}")

        elif event.type == "text_message_content":
            print(f"\n💬 ", end="")
            print(event.delta, end="", flush=True)

    print("\n\n")

    # Scenario 2: Calculator with step visualization
    print("Scenario 2: Calculator Tool")
    print("-" * 60)

    timeline = []
    start_time = datetime.now()

    async for event in adapter.stream_events(
        message=Message(role="user", content="calculate 123 * 456"),
        thread_id="viz-2",
    ):
        elapsed = (datetime.now() - start_time).total_seconds()
        timeline.append((elapsed, event.type))

        if event.type == "tool_call_start":
            print(f"\n🔧 Tool: {event.tool_call_name}")
            print(f"├─ Started at: {elapsed:.2f}s")

        elif event.type == "tool_call_progress":
            percentage = int(event.progress * 100)
            # Visual progress with timing
            bar = "█" * (percentage // 5) + "░" * (20 - percentage // 5)
            print(f"├─ [{bar}] {percentage}% @ {elapsed:.2f}s - {event.status or ''}")

        elif event.type == "tool_call_result":
            print(f"└─ Completed at: {elapsed:.2f}s")
            print(f"\n📊 Result: {event.content}")

        elif event.type == "text_message_content":
            print(f"\n💬 ", end="")
            print(event.delta, end="", flush=True)

    # Show timeline summary
    print("\n\n")
    print("Timeline Summary:")
    print("-" * 60)
    for elapsed, event_type in timeline:
        if event_type in ["tool_call_start", "tool_call_progress", "tool_call_result"]:
            print(f"  {elapsed:6.2f}s  {event_type}")

    print()


async def main():
    """Run frontend visualization example."""
    await visualize_tool_execution()

    print("\n" + "=" * 60)
    print("Frontend Integration Notes")
    print("=" * 60)
    print("""
This example shows how to visualize tool execution in real-time:

1. **Progress Bars**: Use tool_call_progress events
   - event.progress: 0.0 to 1.0
   - event.status: Human-readable message
   - event.metadata: Additional context

2. **Timeline**: Track event.timestamp for each event
   - Show relative timing
   - Visualize execution phases

3. **Status Updates**: Display event.status messages
   - "Indexing query..."
   - "Searching databases..."
   - etc.

4. **Result Formatting**: Parse tool_call_result
   - Show structured data
   - Format for readability

Frontend Implementation (React example):

```jsx
function ToolCallVisualizer({ events }) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("");

  useEffect(() => {
    events.forEach(event => {
      if (event.type === 'tool_call_progress') {
        setProgress(event.progress * 100);
        setStatus(event.status);
      }
    });
  }, [events]);

  return (
    <div className="tool-call">
      <div className="progress-bar">
        <div style={{ width: `${progress}%` }} />
      </div>
      <p>{status}</p>
    </div>
  );
}
```
""")


if __name__ == "__main__":
    asyncio.run(main())
