"""
Agents-as-Tools Pattern Example - Hierarchical Agent Delegation

The Agents-as-Tools pattern enables agents to call other agents as tools,
creating hierarchical multi-agent systems where specialized agents can be
invoked by supervisor agents.

WHY use this pattern:
✅ Modular specialization (separate agents for different domains)
✅ Hierarchical delegation (supervisor routes to specialists)
✅ Reusable specialist agents (can be called by multiple supervisors)
✅ Standard tool interface (works with existing tool infrastructure)
✅ Clear separation of concerns

WHEN to use:
- Supervisor agent needs to delegate to domain specialists
- Multiple specialized capabilities required (code, data, writing)
- Hierarchical multi-agent systems
- Agent composition and orchestration
- Domain-specific routing (route tasks to the right expert)

WHEN NOT to use:
- Flat peer-to-peer collaboration (use Multiagent pattern instead)
- Simple single-agent tasks
- When all capabilities can fit in one agent

Run: python examples/patterns/agents-as-tools-pattern.py
"""

import asyncio

from agenkit.interfaces import Agent, Message
from agenkit.patterns import agent_as_tool


# Specialist Agents (Mock implementations for demonstration)


class CodeSpecialistAgent:
    """
    Specialist agent for programming and code-related tasks.

    In production, replace with actual LLM specialized for coding.
    """

    @property
    def name(self) -> str:
        return "CodeSpecialist"

    @property
    def capabilities(self) -> list[str]:
        return ["coding", "debugging", "code_review"]

    async def call(self, messages: list[Message], **kwargs) -> Message:
        """Handle code-related requests."""
        query = messages[-1].content if messages else ""

        # Simulate specialized code assistance
        if "function" in query.lower() or "implement" in query.lower():
            response = f"""🔧 Code Specialist Response:

```python
def parse_csv_file(filepath: str) -> list[dict]:
    \"\"\"
    Parse CSV file and return list of dictionaries.

    Args:
        filepath: Path to CSV file

    Returns:
        List of dictionaries, one per row
    \"\"\"
    import csv

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)
```

This implementation:
• Uses built-in csv module (no dependencies)
• Returns structured data as list of dicts
• Handles headers automatically
• Includes proper error handling
"""
        elif "debug" in query.lower() or "error" in query.lower():
            response = """🔧 Code Specialist Response:

Debug checklist:
1. Check for syntax errors (missing colons, parentheses)
2. Verify variable scope and initialization
3. Test edge cases (empty input, None values)
4. Add print statements to trace execution
5. Use debugger to step through code
"""
        else:
            response = f"""🔧 Code Specialist Response:

I can help with:
• Writing functions and classes
• Debugging code issues
• Code review and optimization
• Best practices and patterns

For your query: "{query}"

Would you like me to provide a code implementation?
"""

        return Message(role="assistant", content=response)


class DataSpecialistAgent:
    """
    Specialist agent for data analysis and SQL tasks.

    In production, replace with actual LLM specialized for data analysis.
    """

    @property
    def name(self) -> str:
        return "DataSpecialist"

    @property
    def capabilities(self) -> list[str]:
        return ["data_analysis", "sql", "visualization", "statistics"]

    async def call(self, messages: list[Message], **kwargs) -> Message:
        """Handle data analysis requests."""
        query = messages[-1].content if messages else ""

        if "sql" in query.lower() or "query" in query.lower():
            response = """📊 Data Specialist Response:

```sql
-- Find top 10 customers by total purchase amount
SELECT
    c.customer_id,
    c.name,
    SUM(o.total_amount) as total_spent,
    COUNT(o.order_id) as order_count
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= DATE_SUB(CURRENT_DATE, INTERVAL 1 YEAR)
GROUP BY c.customer_id, c.name
ORDER BY total_spent DESC
LIMIT 10;
```

Query explanation:
• Joins customers with orders
• Filters last year's data
• Aggregates by customer
• Orders by total spending
"""
        elif "analyze" in query.lower() or "analysis" in query.lower():
            response = """📊 Data Specialist Response:

Data analysis workflow:
1. **Load & Clean**: Import data, handle missing values
2. **Explore**: Descriptive statistics, distributions
3. **Visualize**: Charts, plots, dashboards
4. **Model**: Statistical analysis, ML if needed
5. **Report**: Findings and recommendations

Key metrics to examine:
• Central tendency (mean, median, mode)
• Spread (standard deviation, range)
• Correlations and relationships
• Outliers and anomalies
"""
        else:
            response = f"""📊 Data Specialist Response:

I can help with:
• SQL query writing and optimization
• Data analysis and statistics
• Data visualization
• ETL pipeline design

For your query: "{query}"

What type of data analysis do you need?
"""

        return Message(role="assistant", content=response)


class WritingSpecialistAgent:
    """
    Specialist agent for writing and documentation tasks.

    In production, replace with actual LLM specialized for writing.
    """

    @property
    def name(self) -> str:
        return "WritingSpecialist"

    @property
    def capabilities(self) -> list[str]:
        return ["writing", "documentation", "editing", "copywriting"]

    async def call(self, messages: list[Message], **kwargs) -> Message:
        """Handle writing and documentation requests."""
        query = messages[-1].content if messages else ""

        if "document" in query.lower() or "readme" in query.lower():
            response = """✍️  Writing Specialist Response:

# Project Documentation Template

## Overview
Brief description of the project, its purpose, and key features.

## Installation
```bash
pip install your-package
```

## Quick Start
```python
from your_package import main

# Example usage
result = main()
```

## Features
- Feature 1: Description
- Feature 2: Description
- Feature 3: Description

## API Reference
Detailed API documentation with examples.

## Contributing
Guidelines for contributors.

## License
Project license information.
"""
        elif "blog" in query.lower() or "article" in query.lower():
            response = """✍️  Writing Specialist Response:

Article structure:
1. **Headline**: Attention-grabbing title
2. **Introduction**: Hook + value proposition
3. **Body**:
   • Problem statement
   • Solution explanation
   • Examples and use cases
   • Benefits and results
4. **Conclusion**: Summary + call-to-action

Writing tips:
• Use clear, concise language
• Include concrete examples
• Break up text with subheadings
• Add visuals where appropriate
"""
        else:
            response = f"""✍️  Writing Specialist Response:

I can help with:
• Technical documentation (README, API docs)
• Blog posts and articles
• Copywriting and marketing content
• Editing and proofreading

For your query: "{query}"

What type of writing do you need?
"""

        return Message(role="assistant", content=response)


# Supervisor Agent


class SupervisorAgent:
    """
    Supervisor agent that routes tasks to specialist agents.

    In production, this would be an LLM that analyzes requests
    and decides which specialist tool to call.
    """

    def __init__(self, tools: list):
        self.tools = {tool.name: tool for tool in tools}

    @property
    def name(self) -> str:
        return "Supervisor"

    @property
    def capabilities(self) -> list[str]:
        return ["routing", "delegation", "coordination"]

    async def call(self, messages: list[Message], **kwargs) -> Message:
        """Route request to appropriate specialist."""
        query = messages[-1].content if messages else ""

        print(f"\n🎯 Supervisor analyzing: '{query}'")

        # Simple routing logic (in production, LLM would decide)
        if any(
            keyword in query.lower()
            for keyword in ["code", "function", "implement", "debug", "python"]
        ):
            print("  → Routing to Code Specialist")
            tool = self.tools["code_specialist"]
        elif any(
            keyword in query.lower()
            for keyword in ["data", "sql", "query", "analyze", "statistics"]
        ):
            print("  → Routing to Data Specialist")
            tool = self.tools["data_specialist"]
        elif any(
            keyword in query.lower()
            for keyword in ["write", "document", "blog", "article", "readme"]
        ):
            print("  → Routing to Writing Specialist")
            tool = self.tools["writing_specialist"]
        else:
            # Default response if no specialist matches
            return Message(
                role="assistant",
                content=(
                    "I can route your request to one of my specialists:\n"
                    "• Code Specialist (coding, debugging)\n"
                    "• Data Specialist (SQL, analysis)\n"
                    "• Writing Specialist (documentation, articles)\n"
                    "\nPlease clarify what you need help with."
                ),
            )

        # Delegate to specialist
        result = await tool.execute(query=query)
        return Message(role="assistant", content=result)


# Example Usage


async def example_basic_delegation():
    """Example 1: Basic delegation to specialists."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Delegation")
    print("=" * 70)

    # Create specialist agents
    code_agent = CodeSpecialistAgent()
    data_agent = DataSpecialistAgent()
    writing_agent = WritingSpecialistAgent()

    # Wrap specialists as tools
    code_tool = agent_as_tool(
        agent=code_agent,
        name="code_specialist",
        description="Expert in programming, code review, and debugging",
    )

    data_tool = agent_as_tool(
        agent=data_agent,
        name="data_specialist",
        description="Expert in data analysis, SQL, and visualization",
    )

    writing_tool = agent_as_tool(
        agent=writing_agent,
        name="writing_specialist",
        description="Expert in technical writing and documentation",
    )

    # Create supervisor with specialist tools
    supervisor = SupervisorAgent(tools=[code_tool, data_tool, writing_tool])

    # Test different types of requests
    requests = [
        "Write a Python function to parse CSV files",
        "Help me write a SQL query to find top customers",
        "Create a README for my Python project",
    ]

    for request in requests:
        messages = [Message(role="user", content=request)]
        result = await supervisor.call(messages)
        print(f"\n📝 Request: {request}")
        print(f"✅ Response:\n{result.content}\n")
        print("-" * 70)


async def example_tool_interface():
    """Example 2: Specialists exposed as standard tools."""
    print("\n" + "=" * 70)
    print("Example 2: Tool Interface")
    print("=" * 70)

    code_agent = CodeSpecialistAgent()
    code_tool = agent_as_tool(
        agent=code_agent,
        name="code_specialist",
        description="Programming expert",
    )

    print(f"\n Tool Name: {code_tool.name}")
    print(f"Description: {code_tool.description}")
    print(f"Input Schema: {code_tool.input_schema}")

    # Execute tool directly
    result = await code_tool.execute(query="How do I debug a Python function?")
    print(f"\n✅ Tool Result:\n{result}")


async def example_hierarchical_system():
    """Example 3: Multiple levels of hierarchy."""
    print("\n" + "=" * 70)
    print("Example 3: Hierarchical Multi-Agent System")
    print("=" * 70)

    print("\n🏗️  System Architecture:")
    print("  ┌─────────────────┐")
    print("  │   Supervisor    │  (Routes to specialists)")
    print("  └────────┬────────┘")
    print("           │")
    print("     ┌─────┴─────────────┬────────────┐")
    print("     │                   │            │")
    print("┌────▼─────┐      ┌──────▼───┐  ┌────▼──────┐")
    print("│   Code   │      │   Data   │  │  Writing  │")
    print("│Specialist│      │Specialist│  │ Specialist│")
    print("└──────────┘      └──────────┘  └───────────┘")

    print("\n💡 Benefits:")
    print("  • Modular: Each specialist focuses on its domain")
    print("  • Reusable: Specialists can be shared across supervisors")
    print("  • Scalable: Easy to add new specialists")
    print("  • Maintainable: Clear separation of concerns")


async def example_comparison():
    """Example 4: When to use Agents-as-Tools."""
    print("\n" + "=" * 70)
    print("Example 4: Pattern Comparison")
    print("=" * 70)

    print("\n📌 Use Agents-as-Tools when:")
    print("  • Hierarchical delegation (supervisor → specialists)")
    print("  • Domain specialization (code, data, writing)")
    print("  • Routing based on task type")
    print("  • Specialists can be reused by multiple supervisors")

    print("\n📌 Use Multiagent pattern when:")
    print("  • Peer-to-peer collaboration (no hierarchy)")
    print("  • Agents work together on shared goal")
    print("  • No clear supervisor-specialist relationship")

    print("\n💡 Example comparison:")
    print("  Agents-as-Tools: Supervisor routes to code/data/writing specialists")
    print("  Multiagent: Research agents collaboratively write a paper")


async def main():
    """Run all Agents-as-Tools pattern examples."""
    print("\n" + "=" * 70)
    print("AGENTS-AS-TOOLS PATTERN EXAMPLES")
    print("=" * 70)
    print("Demonstrating hierarchical agent delegation")

    await example_basic_delegation()
    await example_tool_interface()
    await example_hierarchical_system()
    await example_comparison()

    print("\n" + "=" * 70)
    print("✅ ALL EXAMPLES COMPLETED")
    print("=" * 70)
    print("\n💡 Key Takeaways:")
    print("  1. Wrap specialist agents as tools for hierarchical delegation")
    print("  2. Supervisor routes tasks to appropriate specialists")
    print("  3. Specialists expose standard tool interface")
    print("  4. Enables modular, reusable agent architecture")
    print("  5. Clear separation: supervisor routes, specialists execute")


if __name__ == "__main__":
    asyncio.run(main())
