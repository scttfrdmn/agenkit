"""MiniPydantic example using the @agent.tool decorator pattern."""

import asyncio
from typing import Annotated

from pydantic import BaseModel, Field

from minipydantic import TypeSafeAgent


# ============================================================================
# Define Models
# ============================================================================


class CalculationResult(BaseModel):
    """Validated calculation result."""

    expression: str
    result: float
    steps: list[str] = Field(default_factory=list)


class DataSummary(BaseModel):
    """Statistical summary with validation."""

    count: int = Field(ge=0)
    mean: float
    min_value: float
    max_value: float


# ============================================================================
# Create Agent with Decorator Pattern
# ============================================================================


async def main():
    """Run decorator example."""
    # Create agent
    agent = TypeSafeAgent(name="DataAgent")

    # Register tools using decorator
    @agent.tool(description="Perform mathematical calculation")
    def calculate(
        expression: Annotated[str, Field(description="Math expression to evaluate")],
        show_steps: bool = False,
    ) -> CalculationResult:
        """Calculate with type-safe inputs."""
        try:
            # Evaluate safely (simplified for demo)
            result = eval(expression, {"__builtins__": {}})

            steps = []
            if show_steps:
                steps.append(f"Expression: {expression}")
                steps.append(f"Evaluated to: {result}")

            return CalculationResult(
                expression=expression,
                result=float(result),
                steps=steps,
            )
        except Exception as e:
            raise ValueError(f"Invalid expression: {e}")

    @agent.tool(description="Compute statistical summary")
    def summarize(
        values: Annotated[list[float], Field(min_length=1)],
    ) -> DataSummary:
        """Summarize data with validation."""
        if not values:
            raise ValueError("Cannot summarize empty list")

        return DataSummary(
            count=len(values),
            mean=sum(values) / len(values),
            min_value=min(values),
            max_value=max(values),
        )

    # Test 1: Calculate tool
    print("=" * 60)
    print("Test 1: Calculate (Decorator Pattern)")
    print("=" * 60)

    calc_tool = agent.tools["calculate"]
    result = await calc_tool.execute(expression="2 + 3 * 4", show_steps=True)

    if result.success:
        data = CalculationResult(**result.data)
        print(f"Expression: {data.expression}")
        print(f"Result: {data.result}")
        print(f"Steps: {data.steps}\n")

    # Test 2: Summarize tool
    print("=" * 60)
    print("Test 2: Summarize Statistics")
    print("=" * 60)

    summary_tool = agent.tools["summarize"]
    result = await summary_tool.execute(values=[1.5, 2.7, 3.2, 4.9, 2.1])

    if result.success:
        summary = DataSummary(**result.data)
        print(f"Count: {summary.count}")
        print(f"Mean: {summary.mean:.2f}")
        print(f"Range: {summary.min_value} - {summary.max_value}\n")

    # Test 3: Validation error
    print("=" * 60)
    print("Test 3: Validation Error (Empty List)")
    print("=" * 60)

    result = await summary_tool.execute(values=[])  # Invalid
    print(f"Success: {result.success}")
    print(f"Error: {result.error}\n")

    # Test 4: Input schema inspection
    print("=" * 60)
    print("Test 4: Tool Schema Inspection")
    print("=" * 60)

    print("Calculate tool schema:")
    print(calc_tool.input_schema)
    print("\nSummarize tool schema:")
    print(summary_tool.input_schema)


if __name__ == "__main__":
    asyncio.run(main())
