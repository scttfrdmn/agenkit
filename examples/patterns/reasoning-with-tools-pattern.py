"""
Reasoning with Tools Pattern Examples

Demonstrates using tools DURING reasoning (not just after reasoning).
This pattern enables models to interleave thinking and tool use for more
accurate and dynamic problem solving.

Key differences from ReAct:
- ReAct: Observe → Think → Act → Observe (sequential)
- This: Think ↔ Act (interleaved, tools available while thinking)

Run: python examples/patterns/09_reasoning_with_tools.py
"""

import asyncio
import json
from datetime import datetime

from agenkit.interfaces import Agent, Message, Tool, ToolResult
from agenkit.patterns.reasoning_with_tools import (
    ReasoningStepType,
    ReasoningWithToolsAgent,
)


# ============================================================================
# Mock Tools for Examples
# ============================================================================


class CalculatorTool(Tool):
    """Calculator that performs basic arithmetic."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Performs arithmetic operations: add, subtract, multiply, divide"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["operation", "a", "b"],
        }

    async def execute(self, operation: str, a: float, b: float) -> ToolResult:
        """Execute calculation."""
        operations = {
            "add": a + b,
            "subtract": a - b,
            "multiply": a * b,
            "divide": a / b if b != 0 else None,
        }

        result = operations.get(operation)
        if result is None:
            return ToolResult(success=False, data=None, error="Division by zero")

        return ToolResult(success=True, data=result, error=None)


class DatabaseTool(Tool):
    """Mock database for looking up prices."""

    def __init__(self):
        """Initialize with sample data."""
        self.prices = {
            "apple": 1.50,
            "banana": 0.80,
            "orange": 1.20,
            "coffee": 4.99,
            "laptop": 999.00,
            "mouse": 29.99,
        }

    @property
    def name(self) -> str:
        return "database"

    @property
    def description(self) -> str:
        return "Look up product prices from database"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "product": {"type": "string"},
            },
            "required": ["product"],
        }

    async def execute(self, product: str) -> ToolResult:
        """Look up price."""
        price = self.prices.get(product.lower())

        if price is None:
            return ToolResult(
                success=False,
                data=None,
                error=f"Product '{product}' not found",
            )

        return ToolResult(
            success=True,
            data={"product": product, "price": price},
            error=None,
        )


class WebSearchTool(Tool):
    """Mock web search for fact checking."""

    def __init__(self):
        """Initialize with sample facts."""
        self.facts = {
            "python version": "Python 3.12 is the latest stable version",
            "speed of light": "The speed of light is 299,792,458 meters per second",
            "earth distance sun": "Earth is approximately 149.6 million km from the Sun",
            "population": "World population is approximately 8 billion people",
        }

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        }

    async def execute(self, query: str) -> ToolResult:
        """Search for information."""
        # Simple keyword matching
        query_lower = query.lower()
        for key, fact in self.facts.items():
            if key in query_lower:
                return ToolResult(success=True, data=fact, error=None)

        return ToolResult(
            success=False,
            data=None,
            error="No results found",
        )


# ============================================================================
# Mock LLM (simulates reasoning with tool calls)
# ============================================================================


class MockReasoningLLM(Agent):
    """Mock LLM that demonstrates reasoning with tools."""

    def __init__(self, scenario: str = "basic"):
        """Initialize with scenario."""
        self.scenario = scenario
        self.call_count = 0

    @property
    def name(self) -> str:
        return "mock_reasoning_llm"

    @property
    def capabilities(self) -> list[str]:
        return ["text_generation", "tool_use"]

    async def process(self, message: Message) -> Message:
        """Generate reasoning with tool calls."""
        self.call_count += 1
        content_lower = message.content.lower()

        # Scenario 1: Basic calculation
        if self.scenario == "basic":
            if self.call_count == 1:
                return Message(
                    role="assistant",
                    content="""Let me calculate this step by step.
First, I need to multiply 15.99 by 3.

TOOL_CALL: calculator
PARAMETERS: {"operation": "multiply", "a": 15.99, "b": 3}""",
                )
            elif self.call_count == 2:
                if "47.97" in content_lower or "result" in content_lower:
                    return Message(
                        role="assistant",
                        content="""Good, the subtotal is $47.97.
Now I need to calculate the tax (8.5%).

TOOL_CALL: calculator
PARAMETERS: {"operation": "multiply", "a": 47.97, "b": 0.085}""",
                    )
            elif self.call_count == 3:
                return Message(
                    role="assistant",
                    content="""The tax is $4.08.
Now let me add the tax to the subtotal.

TOOL_CALL: calculator
PARAMETERS: {"operation": "add", "a": 47.97, "b": 4.08}""",
                )
            else:
                return Message(
                    role="assistant",
                    content="FINAL ANSWER: The total cost is $52.05",
                )

        # Scenario 2: Database lookup with calculation
        elif self.scenario == "database":
            if self.call_count == 1:
                return Message(
                    role="assistant",
                    content="""I need to find the price of a laptop first.

TOOL_CALL: database
PARAMETERS: {"product": "laptop"}""",
                )
            elif self.call_count == 2:
                if "999" in content_lower:
                    return Message(
                        role="assistant",
                        content="""The laptop costs $999.00. Now let me check the mouse price.

TOOL_CALL: database
PARAMETERS: {"product": "mouse"}""",
                    )
            elif self.call_count == 3:
                return Message(
                    role="assistant",
                    content="""Mouse is $29.99. Now let me calculate the total.

TOOL_CALL: calculator
PARAMETERS: {"operation": "add", "a": 999.00, "b": 29.99}""",
                )
            else:
                return Message(
                    role="assistant",
                    content="FINAL ANSWER: The total for a laptop and mouse is $1,028.99",
                )

        # Scenario 3: Research with fact-checking
        elif self.scenario == "research":
            if self.call_count == 1:
                return Message(
                    role="assistant",
                    content="""Let me search for information about the speed of light.

TOOL_CALL: web_search
PARAMETERS: {"query": "speed of light meters per second"}""",
                )
            elif self.call_count == 2:
                if "299,792,458" in message.content:
                    return Message(
                        role="assistant",
                        content="""Great! I found that the speed of light is 299,792,458 m/s.
Now let me convert this to kilometers per second.

TOOL_CALL: calculator
PARAMETERS: {"operation": "divide", "a": 299792458, "b": 1000"}""",
                    )
            else:
                return Message(
                    role="assistant",
                    content="FINAL ANSWER: The speed of light is approximately 299,792 km/s",
                )

        # Scenario 4: Error handling
        elif self.scenario == "error":
            if self.call_count == 1:
                return Message(
                    role="assistant",
                    content="""Let me look up the price of a spaceship.

TOOL_CALL: database
PARAMETERS: {"product": "spaceship"}""",
                )
            else:
                return Message(
                    role="assistant",
                    content="""CONCLUSION: Sorry, I couldn't find the product you're looking for.
The database doesn't have that item.""",
                )

        return Message(role="assistant", content="I'm not sure how to proceed.")


# ============================================================================
# Example Demonstrations
# ============================================================================


async def demo_basic_calculation():
    """Demo 1: Basic multi-step calculation with tool use."""
    print("\n" + "=" * 70)
    print("DEMO 1: Basic Multi-Step Calculation")
    print("=" * 70)
    print("\nScenario: Calculate total cost of 3 items at $15.99 each with 8.5% tax")
    print("Demonstrates: Interleaved reasoning and calculation\n")

    llm = MockReasoningLLM(scenario="basic")
    calculator = CalculatorTool()

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[calculator],
        max_reasoning_steps=10,
    )

    response = await agent.process(
        Message(
            role="user",
            content="What's the total cost if I buy 3 items at $15.99 each with 8.5% tax?",
        )
    )

    print(f"✓ Final Answer: {response.content}")
    print(f"✓ Reasoning Steps: {response.metadata['reasoning_steps']}")
    print(f"✓ Tools Used: {response.metadata['tools_used']}")

    # Show reasoning trace
    print("\nReasoning Trace:")
    for i, step in enumerate(response.metadata["reasoning_trace"]["steps"], 1):
        step_type = step["step_type"]
        if step_type == "thinking":
            print(f"  {i}. 💭 THINKING: {step['content'][:60]}...")
        elif step_type == "tool_call":
            print(f"  {i}. 🔧 TOOL CALL: {step['tool_name']} with {step['tool_parameters']}")
        elif step_type == "tool_result":
            print(f"  {i}. ✓ TOOL RESULT: {step['content']}")
        elif step_type == "conclusion":
            print(f"  {i}. 🎯 CONCLUSION: {step['content']}")


async def demo_database_with_calculation():
    """Demo 2: Database lookups with calculation."""
    print("\n" + "=" * 70)
    print("DEMO 2: Database Lookup with Calculation")
    print("=" * 70)
    print("\nScenario: Find prices from database and calculate total")
    print("Demonstrates: Multiple tools (database + calculator)\n")

    llm = MockReasoningLLM(scenario="database")
    database = DatabaseTool()
    calculator = CalculatorTool()

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[database, calculator],
        max_reasoning_steps=10,
    )

    response = await agent.process(
        Message(
            role="user",
            content="What's the total cost for a laptop and a mouse?",
        )
    )

    print(f"✓ Final Answer: {response.content}")
    print(f"✓ Tools Used: {response.metadata['tools_used']}")

    # Tool usage breakdown
    trace = response.metadata["reasoning_trace"]
    tool_calls = [s for s in trace["steps"] if s["step_type"] == "tool_call"]

    print("\nTool Usage:")
    for call in tool_calls:
        print(f"  • {call['tool_name']}: {call['tool_parameters']}")


async def demo_research_with_fact_checking():
    """Demo 3: Research with web search and calculation."""
    print("\n" + "=" * 70)
    print("DEMO 3: Research with Fact-Checking")
    print("=" * 70)
    print("\nScenario: Look up scientific fact and perform conversion")
    print("Demonstrates: Web search + calculation for research\n")

    llm = MockReasoningLLM(scenario="research")
    search = WebSearchTool()
    calculator = CalculatorTool()

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[search, calculator],
        max_reasoning_steps=10,
    )

    response = await agent.process(
        Message(
            role="user",
            content="What is the speed of light in kilometers per second?",
        )
    )

    print(f"✓ Final Answer: {response.content}")
    print(f"✓ Duration: {response.metadata['reasoning_trace']['duration_seconds']:.2f}s")

    # Show interleaving of tools
    trace = response.metadata["reasoning_trace"]
    print("\nStep-by-Step Process:")
    for step in trace["steps"]:
        if step["step_type"] == "tool_call":
            print(f"  → Used {step['tool_name']}: {step['tool_parameters']}")
        elif step["step_type"] == "conclusion":
            print(f"  → Concluded: {step['content']}")


async def demo_error_handling():
    """Demo 4: Handling tool execution errors."""
    print("\n" + "=" * 70)
    print("DEMO 4: Error Handling")
    print("=" * 70)
    print("\nScenario: Tool returns error (product not found)")
    print("Demonstrates: Graceful error handling during reasoning\n")

    llm = MockReasoningLLM(scenario="error")
    database = DatabaseTool()

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[database],
        max_reasoning_steps=5,
    )

    response = await agent.process(
        Message(
            role="user",
            content="What's the price of a spaceship?",
        )
    )

    print(f"✓ Response: {response.content}")

    # Check for error in trace
    trace = response.metadata["reasoning_trace"]
    error_steps = [s for s in trace["steps"] if "error" in s["content"].lower() or "not found" in s["content"].lower()]

    if error_steps:
        print("\nError Detected:")
        for step in error_steps:
            print(f"  ⚠️ {step['content']}")


async def demo_trace_analysis():
    """Demo 5: Analyzing reasoning traces."""
    print("\n" + "=" * 70)
    print("DEMO 5: Reasoning Trace Analysis")
    print("=" * 70)
    print("\nScenario: Analyze the reasoning process")
    print("Demonstrates: Introspecting agent's reasoning\n")

    llm = MockReasoningLLM(scenario="basic")
    calculator = CalculatorTool()

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[calculator],
        max_reasoning_steps=10,
    )

    response = await agent.process(
        Message(
            role="user",
            content="Calculate 5 * 10 + 20",
        )
    )

    trace = response.metadata["reasoning_trace"]

    print("📊 Reasoning Statistics:")
    print(f"  • Total Steps: {len(trace['steps'])}")
    print(f"  • Thinking Steps: {trace['total_thinking_steps']}")
    print(f"  • Tools Used: {trace['total_tools_used']}")
    print(f"  • Duration: {trace['duration_seconds']:.3f}s")

    # Step type distribution
    step_types = {}
    for step in trace["steps"]:
        st = step["step_type"]
        step_types[st] = step_types.get(st, 0) + 1

    print("\n  Step Distribution:")
    for step_type, count in step_types.items():
        print(f"    - {step_type}: {count}")

    # Timeline
    print("\n  Timeline:")
    for step in trace["steps"]:
        timestamp = step.get("timestamp", 0)
        rel_time = timestamp - trace["steps"][0]["timestamp"] if trace["steps"] else 0
        print(f"    [{rel_time:.2f}s] {step['step_type']}: {step['content'][:40]}...")


async def demo_tool_management():
    """Demo 6: Dynamic tool management."""
    print("\n" + "=" * 70)
    print("DEMO 6: Dynamic Tool Management")
    print("=" * 70)
    print("\nScenario: Add/remove tools dynamically")
    print("Demonstrates: Runtime tool configuration\n")

    llm = MockReasoningLLM(scenario="basic")
    calculator = CalculatorTool()

    agent = ReasoningWithToolsAgent(
        llm=llm,
        tools=[calculator],
        max_reasoning_steps=10,
    )

    print(f"Initial tools: {list(agent.tools.keys())}")

    # Add new tools
    database = DatabaseTool()
    agent.add_tool(database)
    print(f"After adding database: {list(agent.tools.keys())}")

    # Add web search
    search = WebSearchTool()
    agent.add_tool(search)
    print(f"After adding web search: {list(agent.tools.keys())}")

    # Remove a tool
    agent.remove_tool("calculator")
    print(f"After removing calculator: {list(agent.tools.keys())}")

    # Get specific tool
    db_tool = agent.get_tool("database")
    print(f"\nRetrieved tool: {db_tool.name if db_tool else 'None'}")
    print(f"Tool description: {db_tool.description if db_tool else 'None'}")


# ============================================================================
# Key Concepts Summary
# ============================================================================


def print_key_concepts():
    """Print key concepts about reasoning with tools."""
    print("\n" + "=" * 70)
    print("KEY CONCEPTS: Reasoning with Tools")
    print("=" * 70)

    concepts = [
        ("🔄 Interleaved Execution", "Tools are called DURING reasoning, not just after"),
        ("🧠 Dynamic Tool Use", "Agent decides when tools are needed while thinking"),
        ("📊 Reasoning Trace", "Complete record of thinking + tool usage"),
        ("🎯 Real-time Refinement", "Tool results immediately inform next reasoning step"),
        ("⚡ Different from ReAct", "ReAct is sequential (think→act→observe), this is interleaved"),
        ("🛠️ Tool Management", "Add/remove tools dynamically at runtime"),
        ("❌ Error Handling", "Gracefully handles tool execution failures"),
        ("📈 Introspection", "Analyze reasoning process through detailed traces"),
    ]

    print("\n")
    for concept, description in concepts:
        print(f"  {concept}")
        print(f"    → {description}\n")


def print_use_cases():
    """Print common use cases."""
    print("\n" + "=" * 70)
    print("COMMON USE CASES")
    print("=" * 70)

    use_cases = [
        "📊 Data Analysis: Query databases while analyzing patterns",
        "🧮 Complex Calculations: Break down math problems with calculator",
        "🔬 Research: Fact-check and verify information in real-time",
        "💰 Financial Planning: Look up prices while calculating budgets",
        "🌐 Multi-Source Aggregation: Combine data from multiple tools",
        "🤖 Scientific Computing: Use specialized tools during problem-solving",
    ]

    print("\n")
    for use_case in use_cases:
        print(f"  {use_case}")


# ============================================================================
# Main
# ============================================================================


async def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("🤖 REASONING WITH TOOLS PATTERN")
    print("=" * 70)
    print("\nDemonstrates interleaved reasoning and tool usage where tools")
    print("are called DURING the thinking process (not just after).")

    # Run all demos
    await demo_basic_calculation()
    await demo_database_with_calculation()
    await demo_research_with_fact_checking()
    await demo_error_handling()
    await demo_trace_analysis()
    await demo_tool_management()

    # Show concepts and use cases
    print_key_concepts()
    print_use_cases()

    print("\n" + "=" * 70)
    print("✅ All Demonstrations Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
