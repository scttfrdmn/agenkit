"""Tool visualization UI example with MiniCopilotKit.

This example demonstrates:
- Tool call visualization (like CopilotKit's tool cards)
- Real-time tool execution progress
- Tool arguments and results display
- Multiple concurrent tool calls

Compare with CopilotKit:
- CopilotKit: Automatic tool card UI rendering
- MiniCopilotKit: ToolCard tracking with AG-UI events
- Both: Real-time updates, progress tracking, results
"""

import asyncio
from typing import Optional

from agenkit import Agent, Message, Tool, ToolResult
from agenkit.protocols.agui import ProgressReporter

from minicopilotkit import CopilotAgent


# ============================================
# Sample Tools
# ============================================


class SearchTool(Tool):
    """Search tool with progress reporting."""

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search for information"

    async def execute(
        self, query: str, progress_reporter: Optional[ProgressReporter] = None, **kwargs
    ) -> ToolResult:
        """Execute search with progress."""
        # Simulate search phases
        if progress_reporter:
            progress_reporter.report(0.3, "Indexing query...")
        await asyncio.sleep(0.3)

        if progress_reporter:
            progress_reporter.report(0.6, "Searching databases...")
        await asyncio.sleep(0.3)

        if progress_reporter:
            progress_reporter.report(1.0, "Complete")

        results = [
            f"Result 1 for '{query}'",
            f"Result 2 for '{query}'",
            f"Result 3 for '{query}'",
        ]

        return ToolResult(success=True, data={"query": query, "results": results})


class CalculatorTool(Tool):
    """Calculator tool with progress reporting."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform calculations"

    async def execute(
        self,
        expression: str,
        progress_reporter: Optional[ProgressReporter] = None,
        **kwargs,
    ) -> ToolResult:
        """Execute calculation with progress."""
        if progress_reporter:
            progress_reporter.report(0.5, "Evaluating expression...")
        await asyncio.sleep(0.2)

        try:
            result = eval(expression, {"__builtins__": {}}, {})
            if progress_reporter:
                progress_reporter.report(1.0, "Complete")
            return ToolResult(success=True, data={"expression": expression, "result": result})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ToolAgent(Agent):
    """Agent that uses tools."""

    def __init__(self, search_tool: SearchTool, calc_tool: CalculatorTool):
        self.search_tool = search_tool
        self.calc_tool = calc_tool

    @property
    def name(self) -> str:
        return "ToolAgent"

    async def process(self, message: Message) -> Message:
        """Process message with tools."""
        content = message.content.lower()

        if "search" in content:
            # Extract query
            query = content.replace("search", "").replace("for", "").strip()
            if not query:
                query = "information"

            # Execute tool
            result = await self.search_tool.execute(query=query)
            if result.success:
                results = result.data["results"]
                response = f"Found {len(results)} results:\n" + "\n".join(
                    f"  • {r}" for r in results
                )
            else:
                response = f"Search failed: {result.error}"

        elif "calculate" in content or "compute" in content:
            # Extract expression
            expr = content.replace("calculate", "").replace("compute", "").strip()
            if not expr:
                expr = "2+2"

            # Execute tool
            result = await self.calc_tool.execute(expression=expr)
            if result.success:
                response = f"Result: {expr} = {result.data['result']}"
            else:
                response = f"Calculation failed: {result.error}"

        else:
            response = (
                "I can help with:\n"
                "  • Search for <query>\n"
                "  • Calculate <expression>\n"
                "\nWhat would you like to do?"
            )

        return Message(role="assistant", content=response)


# ============================================
# Demos
# ============================================


async def demo_tool_visualization():
    """Demonstrate tool call visualization."""
    print("=" * 60)
    print("Tool Visualization Demo")
    print("=" * 60)
    print()

    # Create agent with tools
    search_tool = SearchTool()
    calc_tool = CalculatorTool()
    agent = ToolAgent(search_tool, calc_tool)

    # Wrap with CopilotAgent
    copilot = CopilotAgent(agent, tools=[search_tool, calc_tool])

    # Send message that uses tools
    message = Message(role="user", content="search for machine learning")

    print("User: search for machine learning")
    print()

    # Stream events and visualize tools
    async for event in copilot.stream_chat(message, "tool-demo"):
        if event.type == "tool_call_start":
            print(f"🔧 Tool started: {event.tool_call_name}")
            print(f"   ID: {event.tool_call_id}")

        elif event.type == "tool_call_progress":
            percentage = int(event.progress * 100)
            bar = "█" * (percentage // 5) + "░" * (20 - percentage // 5)
            print(f"   [{bar}] {percentage}% - {event.status or ''}")

        elif event.type == "tool_call_result":
            print(f"   ✅ Complete")
            print(f"   Result: {event.content}")
            print()

        elif event.type == "text_message_content":
            print(event.delta, end="", flush=True)

    print("\n")

    # Show active tool cards
    print("\nActive Tool Cards:")
    for card in copilot.get_active_tools():
        print(f"  • {card['tool_name']}: {card['status']} ({card['progress']*100:.0f}%)")


async def demo_concurrent_tools():
    """Demonstrate multiple concurrent tool calls."""
    print("\n" + "=" * 60)
    print("Concurrent Tools Demo")
    print("=" * 60)
    print()

    search_tool = SearchTool()
    calc_tool = CalculatorTool()
    agent = ToolAgent(search_tool, calc_tool)
    copilot = CopilotAgent(agent, tools=[search_tool, calc_tool])

    # First tool call
    print("1. Search Query:")
    message1 = Message(role="user", content="search for AI")

    async for event in copilot.stream_chat(message1, "concurrent-1"):
        if event.type == "tool_call_start":
            print(f"   🔧 {event.tool_call_name}")
        elif event.type == "tool_call_progress":
            print(f"   Progress: {event.progress*100:.0f}%")

    print()

    # Second tool call
    print("2. Calculation:")
    message2 = Message(role="user", content="calculate 42 * 137")

    async for event in copilot.stream_chat(message2, "concurrent-2"):
        if event.type == "tool_call_start":
            print(f"   🔧 {event.tool_call_name}")
        elif event.type == "tool_call_progress":
            print(f"   Progress: {event.progress*100:.0f}%")

    print()


async def demo_tool_card_state():
    """Demonstrate tool card state tracking."""
    print("\n" + "=" * 60)
    print("Tool Card State Tracking")
    print("=" * 60)
    print()

    search_tool = SearchTool()
    calc_tool = CalculatorTool()
    agent = ToolAgent(search_tool, calc_tool)
    copilot = CopilotAgent(agent, tools=[search_tool, calc_tool])

    message = Message(role="user", content="search for Python programming")

    print("Tracking tool execution states:")
    print()

    async for event in copilot.stream_chat(message, "card-state"):
        if event.type == "tool_call_start":
            print(f"State: PENDING → EXECUTING")
            print(f"Tool: {event.tool_call_name}")

        elif event.type == "tool_call_progress":
            print(f"State: EXECUTING (progress: {event.progress*100:.0f}%)")

        elif event.type == "tool_call_result":
            print(f"State: EXECUTING → COMPLETED")
            print()

    # Show final tool cards
    print("Final Tool Cards:")
    for card in copilot.get_active_tools():
        print(f"\n  Tool: {card['tool_name']}")
        print(f"  Status: {card['status']}")
        print(f"  Progress: {card['progress']*100:.0f}%")
        if card['result']:
            print(f"  Result: {card['result']}")


async def main():
    """Run all tool visualization demos."""
    print("🔧 MiniCopilotKit - Tool Visualization\n")

    await demo_tool_visualization()
    await demo_concurrent_tools()
    await demo_tool_card_state()

    print("\n\n" + "=" * 60)
    print("Key Concepts:")
    print("=" * 60)
    print("""
1. **ToolCard Class**:
   - Similar to CopilotKit's tool cards
   - Tracks tool execution state
   - Shows progress and results

2. **Tool States**:
   - pending: Tool queued
   - executing: Tool running
   - completed: Tool finished
   - failed: Tool errored

3. **Progress Tracking**:
   - ToolCallProgressEvent: Real-time updates
   - 0.0 to 1.0 progress scale
   - Status messages for context

4. **Comparison**:
   CopilotKit:
   - Automatic tool card rendering
   - Built-in progress bars
   - React components

   MiniCopilotKit:
   - ToolCard data structure
   - AG-UI progress events
   - Python-based tracking

   Both: Real-time tool visualization!

5. **Frontend Integration**:
   - Tool cards render in UI
   - Progress bars update live
   - Results display when complete
   - Multiple tools tracked concurrently
""")


if __name__ == "__main__":
    asyncio.run(main())
