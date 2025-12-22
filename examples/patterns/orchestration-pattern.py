"""
Agents-as-Tools Pattern Example - Hierarchical Agent Delegation

The Agents-as-Tools pattern enables agents to call other agents as tools,
creating hierarchical multi-agent systems where specialized agents can be
invoked by supervisor agents.

WHY use this pattern:
✅ Enable specialization (domain experts)
✅ Hierarchical organization (supervisor → specialists)
✅ Reuse agents across contexts
✅ Seamless integration with ReAct pattern
✅ Clear separation of concerns

WHEN to use:
- Complex tasks requiring multiple specialties
- Routing to domain-specific agents
- Building agent hierarchies
- Delegating subtasks to specialists
- Multi-agent orchestration

Run: python examples/patterns/07_hierarchical_agents.py
"""

import asyncio

from agenkit.interfaces import Message
from agenkit.patterns import ReActAgent, ToolRegistry, agent_as_tool


# Mock specialist agents (replace with real LLM agents in production)
class CodeSpecialistAgent:
    """Specialist for programming tasks."""

    def __init__(self):
        self.name = "CodeSpecialist"
        self.capabilities = ["python", "javascript", "code_review"]
        self.tasks_handled = 0

    async def process(self, message: Message) -> Message:
        """Handle programming-related requests."""
        self.tasks_handled += 1

        # Simulate code generation
        if "fibonacci" in message.content.lower():
            response = """Here's a Python function to calculate Fibonacci numbers:

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

This is a recursive implementation. For better performance with large n,
consider using memoization or an iterative approach."""

        elif "sort" in message.content.lower():
            response = """Here's a sorting function:

```python
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
```

This implements the quicksort algorithm with O(n log n) average complexity."""

        else:
            response = f"I'm a code specialist. I can help with: {message.content}"

        return Message(
            role="assistant",
            content=response,
            metadata={"specialist": "code", "tasks_handled": self.tasks_handled},
        )


class DataSpecialistAgent:
    """Specialist for data analysis tasks."""

    def __init__(self):
        self.name = "DataSpecialist"
        self.capabilities = ["data_analysis", "sql", "statistics"]
        self.tasks_handled = 0

    async def process(self, message: Message) -> Message:
        """Handle data-related requests."""
        self.tasks_handled += 1

        if "average" in message.content.lower() or "mean" in message.content.lower():
            response = """To calculate the average (mean) of a dataset:

1. Sum all values: total = sum(data)
2. Count values: n = len(data)
3. Divide: average = total / n

Example:
```python
data = [10, 20, 30, 40, 50]
average = sum(data) / len(data)  # Result: 30.0
```

For more robust calculation, use: `import statistics; statistics.mean(data)`"""

        elif "sql" in message.content.lower():
            response = """Here's a SQL query template:

```sql
SELECT column1, column2, AVG(column3) as avg_value
FROM table_name
WHERE condition
GROUP BY column1, column2
HAVING AVG(column3) > threshold
ORDER BY avg_value DESC
LIMIT 10;
```

This query groups data, calculates averages, filters, and returns top 10 results."""

        else:
            response = f"I'm a data specialist. I can help with: {message.content}"

        return Message(
            role="assistant",
            content=response,
            metadata={"specialist": "data", "tasks_handled": self.tasks_handled},
        )


class ResearchSpecialistAgent:
    """Specialist for research and information tasks."""

    def __init__(self):
        self.name = "ResearchSpecialist"
        self.capabilities = ["research", "fact_checking", "summarization"]
        self.tasks_handled = 0

    async def process(self, message: Message) -> Message:
        """Handle research-related requests."""
        self.tasks_handled += 1

        response = f"""I specialize in research and information gathering.

For your query: "{message.content}"

I would:
1. Search authoritative sources (academic papers, documentation)
2. Cross-reference multiple sources
3. Verify facts and dates
4. Summarize findings
5. Provide citations

(This is a mock response - in production, integrate with search APIs,
databases, or knowledge bases for actual research.)"""

        return Message(
            role="assistant",
            content=response,
            metadata={"specialist": "research", "tasks_handled": self.tasks_handled},
        )


# Mock supervisor LLM (simulates routing decisions)
class MockSupervisorLLM:
    """Mock LLM that simulates a supervisor making routing decisions."""

    def __init__(self):
        self.call_count = 0

    async def chat(self, messages: list[Message]) -> Message:
        """Simulate supervisor deciding which specialist to use."""
        self.call_count += 1

        # Get the user's query
        user_query = messages[-1].content.lower()

        # Simulate reasoning and tool selection
        if "code" in user_query or "function" in user_query or "python" in user_query:
            # Route to code specialist
            response = """Thought: This is a programming question. I should use the code specialist.
Action: code_specialist
Action Input: {"query": "Write a function to calculate Fibonacci numbers"}"""

        elif "data" in user_query or "average" in user_query or "sql" in user_query:
            # Route to data specialist
            response = """Thought: This is a data analysis question. I should use the data specialist.
Action: data_specialist
Action Input: {"query": "How do I calculate the average of a dataset?"}"""

        elif "research" in user_query or "find" in user_query or "information" in user_query:
            # Route to research specialist
            response = """Thought: This requires research. I should use the research specialist.
Action: research_specialist
Action Input: {"query": "Research information about AI agents"}"""

        else:
            # Provide final answer
            response = """Thought: I can answer this directly.
Action: Final Answer
Action Input: I'm a supervisor agent that delegates to specialists. Ask me about code, data, or research!"""

        return Message(role="assistant", content=response)


async def demo_basic_hierarchy():
    """Demo 1: Basic hierarchical delegation."""
    print("=" * 70)
    print("Demo 1: Basic Hierarchical Delegation")
    print("=" * 70)

    # Create specialist agents
    code_agent = CodeSpecialistAgent()
    data_agent = DataSpecialistAgent()
    research_agent = ResearchSpecialistAgent()

    # Wrap specialists as tools
    code_tool = agent_as_tool(
        agent=code_agent,
        name="code_specialist",
        description="Expert in programming, algorithms, and code. Use for coding questions.",
    )

    data_tool = agent_as_tool(
        agent=data_agent,
        name="data_specialist",
        description="Expert in data analysis, SQL, and statistics. Use for data questions.",
    )

    research_tool = agent_as_tool(
        agent=research_agent,
        name="research_specialist",
        description="Expert in research and information gathering. Use for research questions.",
    )

    # Create tool registry
    registry = ToolRegistry()
    registry.register(code_tool)
    registry.register(data_tool)
    registry.register(research_tool)

    # Create supervisor with access to specialist tools
    supervisor = ReActAgent(
        llm_client=MockSupervisorLLM(), tool_registry=registry, max_iterations=5
    )

    print("\n🎯 Supervisor agent created with 3 specialist tools:")
    print("  • code_specialist - Programming expert")
    print("  • data_specialist - Data analysis expert")
    print("  • research_specialist - Research expert")

    # Test 1: Code question
    print("\n" + "-" * 70)
    print("📝 Task 1: 'Write a function to calculate Fibonacci numbers'")
    print("-" * 70)

    result1 = await supervisor.process(
        Message(role="user", content="Write a function to calculate Fibonacci numbers")
    )

    print(f"\n✅ Response (delegated to {result1.metadata.get('specialist', 'supervisor')}):")
    print(result1.content[:200] + "..." if len(result1.content) > 200 else result1.content)

    # Test 2: Data question
    print("\n" + "-" * 70)
    print("📝 Task 2: 'How do I calculate the average of a dataset?'")
    print("-" * 70)

    result2 = await supervisor.process(
        Message(role="user", content="How do I calculate the average of a dataset?")
    )

    print(f"\n✅ Response (delegated to {result2.metadata.get('specialist', 'supervisor')}):")
    print(result2.content[:200] + "..." if len(result2.content) > 200 else result2.content)

    print("\n📊 Statistics:")
    print(f"  Code specialist tasks: {code_agent.tasks_handled}")
    print(f"  Data specialist tasks: {data_agent.tasks_handled}")
    print(f"  Research specialist tasks: {research_agent.tasks_handled}")


async def demo_tool_output_formats():
    """Demo 2: Different output formats."""
    print("\n\n" + "=" * 70)
    print("Demo 2: Output Format Options")
    print("=" * 70)

    specialist = CodeSpecialistAgent()

    # Format 1: String (default)
    tool_str = agent_as_tool(
        agent=specialist, name="code_str", description="Returns string", output_format="str"
    )

    result_str = await tool_str.execute(query="Write a sort function")
    print("\n📝 String format (default):")
    print(f"  Type: {type(result_str)}")
    print(f"  Content: {result_str[:80]}...")

    # Format 2: Dictionary
    specialist2 = CodeSpecialistAgent()
    tool_dict = agent_as_tool(
        agent=specialist2,
        name="code_dict",
        description="Returns dict",
        output_format="dict",
        include_metadata=True,
    )

    result_dict = await tool_dict.execute(query="Write a sort function")
    print("\n📝 Dictionary format (with metadata):")
    print(f"  Type: {type(result_dict)}")
    print(f"  Keys: {list(result_dict.keys())}")
    print(f"  Metadata: {result_dict.get('metadata')}")

    # Format 3: Message
    specialist3 = CodeSpecialistAgent()
    tool_msg = agent_as_tool(
        agent=specialist3, name="code_msg", description="Returns message", output_format="message"
    )

    result_msg = await tool_msg.execute(query="Write a sort function")
    print("\n📝 Message format:")
    print(f"  Type: {type(result_msg)}")
    print(f"  Role: {result_msg.role}")
    print(f"  Has metadata: {bool(result_msg.metadata)}")


async def demo_nested_hierarchy():
    """Demo 3: Multi-level hierarchy (supervisor → manager → specialist)."""
    print("\n\n" + "=" * 70)
    print("Demo 3: Multi-Level Hierarchy (3 levels)")
    print("=" * 70)

    # Level 3: Specialists
    python_specialist = CodeSpecialistAgent()
    javascript_specialist = CodeSpecialistAgent()

    # Level 2: Domain managers (agents that manage specialists)
    python_tool = agent_as_tool(
        agent=python_specialist, name="python_expert", description="Python programming expert"
    )

    js_tool = agent_as_tool(
        agent=javascript_specialist, name="js_expert", description="JavaScript programming expert"
    )

    # Level 1: Top-level supervisor
    code_registry = ToolRegistry()
    code_registry.register(python_tool)
    code_registry.register(js_tool)

    print("\n🏗️ Hierarchy:")
    print("  Level 1: Supervisor Agent")
    print("  ├─ Level 2: Code Manager")
    print("  │  ├─ Level 3: Python Specialist")
    print("  │  └─ Level 3: JavaScript Specialist")
    print("  └─ Level 2: Data Manager")
    print("     └─ Level 3: SQL Specialist")

    print("\n💡 This pattern enables:")
    print("  • Clear separation of responsibilities")
    print("  • Scalable organization (add specialists easily)")
    print("  • Specialized expertise at each level")
    print("  • Reusable components")


async def demo_direct_invocation():
    """Demo 4: Using agent tools directly (without supervisor)."""
    print("\n\n" + "=" * 70)
    print("Demo 4: Direct Tool Invocation (No Supervisor)")
    print("=" * 70)

    # Create specialist as tool
    specialist = CodeSpecialistAgent()
    tool = agent_as_tool(
        agent=specialist, name="code_expert", description="Programming expert", input_key="task"
    )

    print("\n📝 Calling specialist tool directly (bypassing supervisor):")

    # Call tool directly
    result = await tool.execute(task="Write a Fibonacci function")

    print("\n✅ Result:")
    print(result[:200] + "..." if len(result) > 200 else result)

    print("\n💡 Direct invocation useful for:")
    print("  • Testing specialist agents")
    print("  • Programmatic routing (you control delegation)")
    print("  • Integration with existing systems")
    print("  • Simpler use cases without LLM routing")


async def main():
    """Run all demos."""
    print("\n" + "🏗️" * 35)
    print("AGENTS-AS-TOOLS PATTERN DEMONSTRATION")
    print("🏗️" * 35 + "\n")

    await demo_basic_hierarchy()
    await demo_tool_output_formats()
    await demo_nested_hierarchy()
    await demo_direct_invocation()

    print("\n" + "=" * 70)
    print("🎉 All demos completed!")
    print("=" * 70)

    print("\n📚 Key Takeaways:")
    print("  • Wrap any agent as a tool with agent_as_tool()")
    print("  • Tools integrate seamlessly with ReActAgent")
    print("  • Enables hierarchical multi-agent systems")
    print("  • Flexible output formats (str, dict, message)")
    print("  • Can be invoked by supervisor or directly")

    print("\n💡 Production Usage:")
    print("  from agenkit.patterns import agent_as_tool, ReActAgent, ToolRegistry")
    print()
    print("  # Create specialists")
    print("  code_agent = AnthropicAgent(system_prompt='You are a code expert...')")
    print("  data_agent = AnthropicAgent(system_prompt='You are a data expert...')")
    print()
    print("  # Wrap as tools")
    print("  code_tool = agent_as_tool(code_agent, 'code_expert', 'Programming specialist')")
    print("  data_tool = agent_as_tool(data_agent, 'data_expert', 'Data specialist')")
    print()
    print("  # Create supervisor with specialists")
    print("  registry = ToolRegistry()")
    print("  registry.register(code_tool)")
    print("  registry.register(data_tool)")
    print()
    print("  supervisor = ReActAgent(llm_client=llm, tool_registry=registry)")
    print("  result = await supervisor.process(user_message)")
    print()

    print("\n🔗 See also:")
    print("  • docs/patterns/HIERARCHICAL.md - Detailed pattern guide")
    print("  • examples/patterns/02_react_agent.py - ReAct pattern")
    print("  • examples/patterns/04_multiagent.py - Multi-agent patterns")
    print()


if __name__ == "__main__":
    asyncio.run(main())
