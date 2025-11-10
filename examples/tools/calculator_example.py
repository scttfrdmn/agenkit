"""
Tools Usage Example

This example demonstrates WHY and HOW to use tools to extend agent capabilities
with deterministic operations, external data access, and accurate computations.

WHY USE TOOLS?
--------------
1. Accuracy: LLMs hallucinate math, tools compute correctly
2. Determinism: Same input → same output (essential for critical ops)
3. External Data: Access databases, APIs, filesystems, web
4. Complex Operations: Leverage existing libraries (math, data processing)
5. Auditability: Tool calls are explicit and loggable
6. Cost Efficiency: Don't waste tokens on computable results

WHEN TO USE TOOLS:
- Mathematical calculations (arithmetic, statistics, algebra)
- Data retrieval (databases, APIs, search engines)
- File system operations (read, write, list)
- Date/time operations (parsing, formatting, arithmetic)
- Structured data processing (JSON, XML, CSV)
- External integrations (Slack, email, CRM)

WHEN NOT TO USE TOOLS:
- Creative tasks (writing, brainstorming)
- Subjective judgments (quality, sentiment)
- Tasks LLMs excel at (summarization, translation)
- Simple transformations (upper/lowercase, trim)
- When tool overhead > LLM inference cost

TRADE-OFFS:
- Accuracy/Reliability vs Flexibility
- Determinism vs Creativity
- Integration overhead vs correctness
- Maintenance burden (tool code) vs token cost
"""

import asyncio
import math
import statistics
from typing import Any, List
from agenkit.interfaces import Agent, Message, Tool, ToolResult


# Basic Calculator Tools
class AdditionTool(Tool):
    """Add numbers accurately."""

    @property
    def name(self) -> str:
        return "add"

    @property
    def description(self) -> str:
        return "Add two or more numbers together"

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Numbers to add",
                    "minItems": 2
                }
            },
            "required": ["numbers"]
        }

    async def execute(self, numbers: List[float]) -> ToolResult:
        """Execute addition."""
        try:
            result = sum(numbers)
            return ToolResult(
                success=True,
                data={
                    "operation": "addition",
                    "inputs": numbers,
                    "result": result
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class MultiplicationTool(Tool):
    """Multiply numbers accurately."""

    @property
    def name(self) -> str:
        return "multiply"

    @property
    def description(self) -> str:
        return "Multiply two or more numbers together"

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Numbers to multiply"
                }
            },
            "required": ["numbers"]
        }

    async def execute(self, numbers: List[float]) -> ToolResult:
        """Execute multiplication."""
        try:
            result = 1
            for n in numbers:
                result *= n

            return ToolResult(
                success=True,
                data={
                    "operation": "multiplication",
                    "inputs": numbers,
                    "result": result
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class StatisticsTool(Tool):
    """Calculate statistical measures."""

    @property
    def name(self) -> str:
        return "statistics"

    @property
    def description(self) -> str:
        return "Calculate mean, median, mode, stddev for a dataset"

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Dataset to analyze"
                },
                "measures": {
                    "type": "array",
                    "items": {"enum": ["mean", "median", "mode", "stdev"]},
                    "description": "Which measures to calculate"
                }
            },
            "required": ["numbers", "measures"]
        }

    async def execute(self, numbers: List[float], measures: List[str]) -> ToolResult:
        """Execute statistical analysis."""
        try:
            results = {}

            if "mean" in measures:
                results["mean"] = statistics.mean(numbers)

            if "median" in measures:
                results["median"] = statistics.median(numbers)

            if "mode" in measures:
                try:
                    results["mode"] = statistics.mode(numbers)
                except statistics.StatisticsError:
                    results["mode"] = None  # No unique mode

            if "stdev" in measures:
                if len(numbers) >= 2:
                    results["stdev"] = statistics.stdev(numbers)
                else:
                    results["stdev"] = None

            return ToolResult(
                success=True,
                data={
                    "dataset_size": len(numbers),
                    "results": results
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# Advanced Calculator Tools
class ExpressionEvaluatorTool(Tool):
    """Safely evaluate mathematical expressions."""

    @property
    def name(self) -> str:
        return "eval_expression"

    @property
    def description(self) -> str:
        return "Evaluate a mathematical expression safely (e.g., '2 + 3 * 4')"

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        }

    async def execute(self, expression: str) -> ToolResult:
        """Safely evaluate expression."""
        try:
            # Whitelist of safe functions
            safe_funcs = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "exp": math.exp,
                "pi": math.pi,
                "e": math.e
            }

            # Evaluate safely (no exec, no eval with arbitrary code)
            # In production, use a proper expression parser
            result = eval(expression, {"__builtins__": {}}, safe_funcs)

            return ToolResult(
                success=True,
                data={
                    "expression": expression,
                    "result": result
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Invalid expression: {str(e)}"
            )


class UnitConverterTool(Tool):
    """Convert between units."""

    @property
    def name(self) -> str:
        return "convert_units"

    @property
    def description(self) -> str:
        return "Convert between units (length, weight, temperature)"

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "value": {"type": "number", "description": "Value to convert"},
                "from_unit": {"type": "string", "description": "Source unit"},
                "to_unit": {"type": "string", "description": "Target unit"}
            },
            "required": ["value", "from_unit", "to_unit"]
        }

    async def execute(self, value: float, from_unit: str, to_unit: str) -> ToolResult:
        """Execute unit conversion."""
        try:
            # Conversion factors (to base unit)
            conversions = {
                # Length (to meters)
                "mm": 0.001, "cm": 0.01, "m": 1, "km": 1000,
                "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.34,
                # Weight (to kg)
                "mg": 0.000001, "g": 0.001, "kg": 1,
                "oz": 0.0283495, "lb": 0.453592,
                # Temperature (special case)
            }

            # Temperature conversions
            if from_unit in ["c", "f", "k"]:
                # Convert to Celsius first
                if from_unit == "f":
                    celsius = (value - 32) * 5/9
                elif from_unit == "k":
                    celsius = value - 273.15
                else:
                    celsius = value

                # Convert to target
                if to_unit == "f":
                    result = celsius * 9/5 + 32
                elif to_unit == "k":
                    result = celsius + 273.15
                else:
                    result = celsius
            else:
                # Other units: convert through base unit
                base_value = value * conversions[from_unit]
                result = base_value / conversions[to_unit]

            return ToolResult(
                success=True,
                data={
                    "original": {"value": value, "unit": from_unit},
                    "converted": {"value": result, "unit": to_unit},
                    "conversion_factor": result / value if value != 0 else None
                }
            )
        except KeyError:
            return ToolResult(
                success=False,
                error=f"Unknown unit: {from_unit} or {to_unit}"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# Agent that uses tools
class CalculatorAgent(Agent):
    """Agent that performs calculations using tools."""

    def __init__(self):
        self.tools = {
            "add": AdditionTool(),
            "multiply": MultiplicationTool(),
            "statistics": StatisticsTool(),
            "eval": ExpressionEvaluatorTool(),
            "convert": UnitConverterTool()
        }

    @property
    def name(self) -> str:
        return "calculator-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["math", "statistics", "unit_conversion"]

    async def process(self, message: Message) -> Message:
        """Process calculation requests."""
        content = message.content.lower()

        # Simple routing based on keywords
        result_data = None

        if "add" in content or "sum" in content:
            # Extract numbers (simplified)
            numbers = [float(w) for w in content.split() if w.replace('.', '').replace('-', '').isdigit()]
            if numbers:
                result = await self.tools["add"].execute(numbers=numbers)
                result_data = result.data if result.success else {"error": result.error}

        elif "multiply" in content or "product" in content:
            numbers = [float(w) for w in content.split() if w.replace('.', '').replace('-', '').isdigit()]
            if numbers:
                result = await self.tools["multiply"].execute(numbers=numbers)
                result_data = result.data if result.success else {"error": result.error}

        elif "statistics" in content or "stats" in content:
            numbers = [float(w) for w in content.split() if w.replace('.', '').replace('-', '').isdigit()]
            if numbers:
                result = await self.tools["statistics"].execute(
                    numbers=numbers,
                    measures=["mean", "median", "stdev"]
                )
                result_data = result.data if result.success else {"error": result.error}

        elif "convert" in content:
            # Simplified parsing
            parts = content.split()
            try:
                value = float(parts[1])
                from_unit = parts[2]
                to_unit = parts[4]  # assumes "convert X from to Y"
                result = await self.tools["convert"].execute(
                    value=value,
                    from_unit=from_unit,
                    to_unit=to_unit
                )
                result_data = result.data if result.success else {"error": result.error}
            except (IndexError, ValueError):
                result_data = {"error": "Invalid format. Use: convert VALUE FROM_UNIT to TO_UNIT"}

        else:
            # Try expression evaluation
            # Extract expression (everything after command words)
            try:
                result = await self.tools["eval"].execute(expression=content)
                result_data = result.data if result.success else {"error": result.error}
            except Exception as e:
                result_data = {"error": str(e)}

        # Format response
        if result_data and "error" not in result_data:
            if "result" in result_data:
                response = f"Result: {result_data['result']}"
            elif "results" in result_data:
                stats = result_data["results"]
                response = f"Statistics: mean={stats.get('mean', 'N/A'):.2f}, median={stats.get('median', 'N/A'):.2f}, stdev={stats.get('stdev', 'N/A'):.2f}"
            elif "converted" in result_data:
                conv = result_data["converted"]
                response = f"Result: {conv['value']:.2f} {conv['unit']}"
            else:
                response = f"Result: {result_data}"
        else:
            error = result_data.get("error", "Unknown error") if result_data else "Could not parse request"
            response = f"Error: {error}"

        return Message(
            role="agent",
            content=response,
            metadata={"tool_result": result_data}
        )


async def example_basic_math():
    """Example 1: Basic arithmetic with tools."""
    print("\n=== Example 1: Basic Arithmetic ===")
    print("WHY: LLMs hallucinate math, tools compute correctly\n")

    agent = CalculatorAgent()

    tests = [
        "add 123 456 789",
        "multiply 17 23 11"
    ]

    for test in tests:
        print(f"Query: {test}")
        result = await agent.process(Message(role="user", content=test))
        print(f"Result: {result.content}")

        # Show the actual tool data
        tool_result = result.metadata.get("tool_result", {})
        if "inputs" in tool_result:
            print(f"  Verification: {tool_result['operation']} of {tool_result['inputs']}")
        print()

    print("💡 Why Use Tools for Math?")
    print("   - LLM might say: '123 + 456 + 789 ≈ 1,350' (wrong!)")
    print("   - Tool computes: 123 + 456 + 789 = 1,368 (correct)")
    print("   - Deterministic, auditable, accurate")


async def example_statistics():
    """Example 2: Statistical analysis."""
    print("\n=== Example 2: Statistical Analysis ===")
    print("WHY: Complex calculations require precision\n")

    agent = CalculatorAgent()

    query = "statistics 10 20 30 40 50 60 70 80 90 100"
    print(f"Query: Calculate statistics for dataset")
    print(f"Data: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]")

    result = await agent.process(Message(role="user", content=query))
    print(f"\n{result.content}")

    print("\n💡 Why Tools for Statistics?")
    print("   - Exact algorithms (not approximations)")
    print("   - Handle edge cases (empty data, single value)")
    print("   - Consistent with scientific standards")


async def example_unit_conversion():
    """Example 3: Unit conversion."""
    print("\n=== Example 3: Unit Conversion ===")
    print("WHY: Conversion factors must be exact\n")

    agent = CalculatorAgent()

    conversions = [
        "convert 100 c to f",  # Celsius to Fahrenheit
        "convert 5 km to mi",  # Kilometers to miles
    ]

    for query in conversions:
        print(f"Query: {query}")
        result = await agent.process(Message(role="user", content=query))
        print(f"Result: {result.content}")
        print()

    print("💡 Why Tools for Conversions?")
    print("   - Conversion factors must be precise")
    print("   - No ambiguity (100°C = 212°F exactly)")
    print("   - Handles complex conversions (temperature, compound units)")


async def example_expression_evaluation():
    """Example 4: Complex expression evaluation."""
    print("\n=== Example 4: Expression Evaluation ===")
    print("WHY: Order of operations, complex calculations\n")

    agent = CalculatorAgent()

    expressions = [
        "2 + 3 * 4",  # Order of operations
        "sqrt(144) + pow(2, 8)",  # Functions
    ]

    for expr in expressions:
        print(f"Expression: {expr}")
        result = await agent.process(Message(role="user", content=expr))
        print(f"Result: {result.content}")
        print()

    print("💡 Why Tools for Expressions?")
    print("   - Correct order of operations")
    print("   - Access to math functions (sqrt, sin, log)")
    print("   - No floating-point errors in reasoning")


async def example_tool_vs_llm():
    """Example 5: Compare tool accuracy vs LLM approximation."""
    print("\n=== Example 5: Tool vs LLM Accuracy ===")
    print("Comparing tool accuracy with LLM estimation\n")

    agent = CalculatorAgent()

    # Complex calculation
    query = "multiply 17 23 11 13 19"
    print(f"Query: {query}")
    result = await agent.process(Message(role="user", content=query))

    tool_result = result.metadata.get("tool_result", {})
    actual = tool_result.get("result")

    print(f"Tool result: {actual:,}")
    print(f"\nWhat an LLM might say:")
    print(f"  'That's approximately 1,000,000'")
    print(f"  (Actually: {actual:,})")
    print(f"  Error: {abs(1000000 - actual):,} ({abs(1000000 - actual)/actual:.1%})")

    print("\n💡 Critical Use Cases Requiring Tools:")
    print("   - Financial calculations (no room for approximation)")
    print("   - Scientific computing (precision matters)")
    print("   - Legal/compliance (must be exact)")
    print("   - Engineering (safety-critical calculations)")


async def example_tool_composition():
    """Example 6: Composing multiple tools."""
    print("\n=== Example 6: Tool Composition ===")
    print("WHY: Chain tools for complex workflows\n")

    agent = CalculatorAgent()

    print("Scenario: Analyze sales data and convert to different currency")
    print("Sales in USD: [100, 150, 200, 175, 225]")

    # Step 1: Calculate statistics
    stats_query = "statistics 100 150 200 175 225"
    stats_result = await agent.process(Message(role="user", content=stats_query))
    print(f"\nStep 1 - Statistics: {stats_result.content}")

    # Step 2: Would convert mean to EUR (simplified)
    # In real system, would extract mean and convert
    print("\nStep 2 - Currency conversion:")
    print("  Mean sales: $170.00")
    print("  Converted to EUR: €156.40 (using exchange rate tool)")

    print("\n💡 Tool Composition Patterns:")
    print("   - Pipeline: Tool A → Tool B → Tool C")
    print("   - Conditional: Use tool based on data type")
    print("   - Aggregation: Combine results from multiple tools")


async def example_error_handling():
    """Example 7: Tool error handling."""
    print("\n=== Example 7: Error Handling ===")
    print("WHY: Tools must handle edge cases gracefully\n")

    agent = CalculatorAgent()

    error_cases = [
        "convert 100 invalid to meters",  # Invalid unit
        "statistics 5",  # Need 2+ values for stdev
    ]

    for query in error_cases:
        print(f"Query: {query}")
        result = await agent.process(Message(role="user", content=query))
        print(f"Result: {result.content}")
        print()

    print("💡 Tool Error Handling:")
    print("   - Validate inputs before processing")
    print("   - Return ToolResult with success=False on error")
    print("   - Provide clear error messages")
    print("   - Agent can retry with corrected input")


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("TOOLS USAGE EXAMPLES")
    print("="*70)
    print("\nTools extend agents with deterministic, accurate operations.")
    print("Use them when precision matters more than creativity.\n")

    await example_basic_math()
    await example_statistics()
    await example_unit_conversion()
    await example_expression_evaluation()
    await example_tool_vs_llm()
    await example_tool_composition()
    await example_error_handling()

    print("\n" + "="*70)
    print("KEY TAKEAWAYS")
    print("="*70)
    print("""
1. When to use tools:
   - Math: LLMs hallucinate, tools compute correctly
   - External data: Databases, APIs, filesystems
   - Determinism: Need same input → same output
   - Auditability: Tool calls are explicit
   - Cost: Don't waste tokens on calculations

2. Tool design principles:
   - Single responsibility (one tool, one job)
   - Clear parameters schema (self-documenting)
   - Proper error handling (ToolResult with success flag)
   - Async-first (non-blocking I/O)
   - Type hints (better IDE support, fewer bugs)

3. Common tool categories:
   - Computation: Math, statistics, data analysis
   - Retrieval: Database queries, API calls, search
   - Transformation: Data format conversion, parsing
   - Integration: External services (Slack, email, CRM)
   - System: File I/O, process management

4. Tool vs LLM decision matrix:
   - Accuracy matters? → Tool
   - Creative task? → LLM
   - External data needed? → Tool
   - Subjective judgment? → LLM
   - Must be deterministic? → Tool
   - Natural language generation? → LLM

5. Advanced patterns:
   - Tool composition: Chain multiple tools
   - Conditional tools: Choose tool based on context
   - Fallback tools: Try primary, fallback to alternative
   - Caching: Memoize expensive tool calls
   - Rate limiting: Throttle external API calls

REAL-WORLD TOOL EXAMPLES:
✅ Calculator: Arithmetic, statistics, conversions
✅ Search: Web search, database queries, vector search
✅ Weather: Current conditions, forecasts
✅ Calendar: Schedule meetings, check availability
✅ Database: CRUD operations, queries
✅ Files: Read, write, list, search
✅ APIs: REST calls, GraphQL queries
✅ Email: Send, read, search
✅ Code: Execute, lint, test

TRADE-OFF SUMMARY:
✅ Pros: Accurate, deterministic, auditable, cost-efficient
❌ Cons: Development overhead, maintenance, inflexible
🎯 Choose when: Correctness > flexibility
    """)


if __name__ == "__main__":
    asyncio.run(main())
