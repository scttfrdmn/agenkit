"""
Experimental: Basic Recursive Language Model (RLM) Example

Demonstrates the core RLM pattern by composing existing Agenkit patterns:
- ReasoningWithToolsAgent for REPL code execution
- AgentTool for recursive sub-agent calls
- ReActAgent for iterative reasoning loops
- BudgetLimiter for cost protection (RLM has high cost variance!)

Based on "Recursive Language Models" (Zhang et al., 2025)
https://arxiv.org/abs/2512.24601

Status: EXPERIMENTAL - For research validation, not production use.
"""

import asyncio
import re
from pathlib import Path
from typing import Any

from agenkit.budget import BudgetLimiter, CostTracker
from agenkit.interfaces import Agent, Message


class RecursiveREPLAgent:
    """
    Experimental recursive agent that treats long contexts as REPL variables.

    Composes:
    - REPL environment for code execution
    - Recursive sub-agent calls via llm_query()
    - Iterative refinement until FINAL() answer

    WARNING: High cost variance. Models not trained for this pattern.
    """

    def __init__(
        self,
        agent: Agent,
        sub_agent: Agent | None = None,
        max_iterations: int = 20,
        max_recursion_depth: int = 1,
        session_budget: float | None = None,
        cost_tracker: CostTracker | None = None,
    ):
        """
        Initialize RLM agent.

        Args:
            agent: Root agent for orchestration (e.g., GPT-5, Claude Opus)
            sub_agent: Sub-agent for recursive calls (e.g., GPT-5-mini)
                      If None, uses same agent for recursion
            max_iterations: Max REPL iterations before forcing answer
            max_recursion_depth: Max recursion depth (paper uses 1)
            session_budget: Optional budget limit ($) for this session
                          Recommended: $5-10 for RLM due to high cost variance
            cost_tracker: Optional CostTracker for monitoring costs
                        If None, creates new tracker when budget specified
        """
        # Wrap agents with budget protection if specified
        if session_budget is not None:
            tracker = cost_tracker or CostTracker()
            limiter = BudgetLimiter(
                tracker,
                session_budget=session_budget,
                action="error",  # Stop if budget exceeded
            )
            self.agent = limiter(agent)
            self.sub_agent = limiter(sub_agent or agent)
            self.cost_tracker = tracker
        else:
            self.agent = agent
            self.sub_agent = sub_agent or agent
            self.cost_tracker = cost_tracker

        self.max_iterations = max_iterations
        self.max_recursion_depth = max_recursion_depth

    async def process(self, message: Message) -> Message:
        """
        Process message using RLM pattern.

        Loads message content into REPL as 'context' variable,
        iteratively executes agent-generated code, and returns
        final answer when agent outputs FINAL() or FINAL_VAR().

        Args:
            message: Message with content to process

        Returns:
            Message with final answer
        """
        context = message.content
        context_length = len(context)

        # Load system prompt with context metadata
        system_prompt = self._build_system_prompt(context_length)

        # Initialize REPL namespace with context and llm_query function
        repl_namespace = {
            "context": context,
            "llm_query": self._make_llm_query_func(),
            "print": print,  # Allow print for debugging
        }

        # Iterative REPL loop
        conversation_history = []
        for iteration in range(self.max_iterations):
            # Get agent's next action (code or final answer)
            prompt = self._build_iteration_prompt(system_prompt, conversation_history, iteration)

            response = await self.agent.process(Message(role="user", content=prompt))
            conversation_history.append(("assistant", response.content))

            # Execute any code blocks FIRST (so variables are available for FINAL_VAR)
            code_blocks = self._extract_code_blocks(response.content)
            if code_blocks:
                for code in code_blocks:
                    try:
                        # Execute code in sandboxed namespace
                        exec(code, {"__builtins__": __builtins__}, repl_namespace)
                        output = "Code executed successfully"
                    except Exception as e:
                        output = f"Error: {e}"

                    conversation_history.append(("execution", output))

            # Check for final answer AFTER code execution
            final_answer = self._extract_final_answer(response.content, repl_namespace)
            if final_answer is not None:
                return Message(role="assistant", content=final_answer)

        # Max iterations reached - force final answer
        return Message(
            role="assistant",
            content="Maximum iterations reached. Unable to generate final answer.",
        )

    def _build_system_prompt(self, context_length: int) -> str:
        """Build system prompt with context metadata."""
        # Load from prompts/gpt5_system.txt or use inline version
        prompt_file = Path(__file__).parent / "prompts" / "gpt5_system.txt"

        if prompt_file.exists():
            return prompt_file.read_text().format(
                context_length=context_length,
            )

        # Minimal inline version if file not found
        return f"""You are an agent that processes extremely long contexts by examining them programmatically in a Python REPL.

Context size: {context_length:,} characters

The REPL environment provides:
1. 'context' variable containing the full input
2. 'llm_query(prompt)' function to recursively call a sub-LLM (can handle ~100K chars)
3. Standard Python built-ins

Your task:
1. Write Python code (in ```python blocks) to examine, filter, and decompose the context
2. Use llm_query() to process chunks recursively
3. Aggregate results programmatically
4. When done, output FINAL(answer) or FINAL_VAR(variable_name)

Example strategy:
```python
# Chunk the context and query sub-LLM on each chunk
chunks = [context[i:i+50000] for i in range(0, len(context), 50000)]
results = []
for i, chunk in enumerate(chunks):
    result = llm_query(f"Extract key information from this chunk: {{chunk}}")
    results.append(result)
    print(f"Processed chunk {{i+1}}/{{len(chunks)}}")

# Aggregate results
final = llm_query(f"Synthesize these findings: {{results}}")
```

Then output: FINAL(final)

Think step-by-step and use code to solve the problem systematically.
"""

    def _build_iteration_prompt(
        self, system_prompt: str, history: list[tuple[str, str]], iteration: int
    ) -> str:
        """Build prompt for current iteration including history."""
        prompt_parts = [system_prompt, "\n\n=== Iteration History ===\n"]

        for role, content in history[-10:]:  # Last 10 turns for context
            if role == "assistant":
                prompt_parts.append(f"\nYou: {content[:500]}...")
            elif role == "execution":
                prompt_parts.append(f"\nExecution: {content}")

        prompt_parts.append(f"\n\n=== Iteration {iteration + 1}/{self.max_iterations} ===")
        prompt_parts.append("\nWhat's your next action? (Write Python code or output FINAL answer)")

        return "".join(prompt_parts)

    def _make_llm_query_func(self):
        """Create llm_query() function for REPL namespace."""

        async def llm_query_async(prompt: str) -> str:
            """Recursively query sub-agent."""
            response = await self.sub_agent.process(Message(role="user", content=prompt))
            return response.content

        # Wrap async function for sync REPL context
        def llm_query_sync(prompt: str) -> str:
            """
            Synchronous wrapper for async llm_query.

            Creates new event loop if needed to properly handle async calls
            from the synchronous REPL environment.
            """
            try:
                # Try to get existing loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Loop is already running, we're inside an async context
                    # This shouldn't happen in REPL, but handle it
                    import nest_asyncio

                    nest_asyncio.apply()
                    return loop.run_until_complete(llm_query_async(prompt))
            except RuntimeError:
                # No event loop, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                return loop.run_until_complete(llm_query_async(prompt))
            finally:
                # Don't close the loop as we might reuse it
                pass

        return llm_query_sync

    def _extract_code_blocks(self, text: str) -> list[str]:
        """Extract Python code blocks from agent response."""
        # Match ```python or ```repl code blocks
        pattern = r"```(?:python|repl)\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        return matches

    def _extract_final_answer(self, text: str, namespace: dict[str, Any]) -> str | None:
        """
        Extract final answer if agent outputs FINAL() or FINAL_VAR().

        Args:
            text: Agent's response text
            namespace: REPL namespace for variable lookup

        Returns:
            Final answer string, or None if not ready
        """
        # Check for FINAL(answer)
        final_match = re.search(r"FINAL\((.*?)\)", text, re.DOTALL)
        if final_match:
            return final_match.group(1).strip().strip('"').strip("'")

        # Check for FINAL_VAR(variable_name)
        var_match = re.search(r"FINAL_VAR\((\w+)\)", text)
        if var_match:
            var_name = var_match.group(1)
            if var_name in namespace:
                return str(namespace[var_name])

        return None


async def main():
    """Demonstrate basic RLM on a synthetic long-context task with budget protection."""
    # Simulate a long context (in production, this would be 1M+ tokens)
    # For this demo, we'll use a smaller example

    long_context = (
        """
    Document 1: The company was founded in 2015.
    Document 2: The CEO's name is Alice Johnson.
    Document 3: Revenue grew 300% in 2023.
    Document 4: The product launched in March 2024.
    Document 5: Headquarters moved to Seattle in 2022.
    """
        * 100
    )  # Repeat to simulate longer context

    query = """
    Based on the documents above, answer:
    1. When was the company founded?
    2. Who is the CEO?
    3. What was the revenue growth in 2023?
    """

    message = Message(role="user", content=f"{long_context}\n\nQuery: {query}")

    # Create cost tracker for monitoring
    tracker = CostTracker()

    # In production, you'd use real LLM agents here
    # For demo purposes, we'll use a mock agent
    from agenkit.interfaces import Agent

    class MockAgent(Agent):
        def __init__(self):
            self.iteration = 0

        def name(self) -> str:
            return "mock-llm"

        async def process(self, message: Message) -> Message:
            self.iteration += 1

            # First iteration: generate code to process context
            if self.iteration == 1:
                code = """
```python
# Extract key facts from context
facts = []
for line in context.split('\\n'):
    if 'founded' in line.lower():
        facts.append(line)
    if 'CEO' in line or 'Alice' in line:
        facts.append(line)
    if 'revenue' in line.lower():
        facts.append(line)

print(f"Found {len(facts)} relevant facts")
```

Let me now query the sub-LLM to summarize the findings.
"""
                return Message(role="assistant", content=code)

            # Second iteration: output final answer
            else:
                return Message(
                    role="assistant",
                    content="Based on the facts extracted: FINAL(The company was founded in 2015, CEO is Alice Johnson, and revenue grew 300% in 2023)",
                )

    root_agent = MockAgent()
    sub_agent = MockAgent()

    # Create RLM with budget protection
    # Note: Paper shows 95th percentile costs 3-10x higher than median
    # Always set budget limits for production use!
    rlm = RecursiveREPLAgent(
        agent=root_agent,
        sub_agent=sub_agent,
        max_iterations=10,
        session_budget=5.00,  # $5 budget limit
        cost_tracker=tracker,
    )

    print("Processing long context with RLM pattern...")
    print(f"Budget limit: $5.00")
    print("-" * 50)

    try:
        result = await rlm.process(message)

        print("\n=== Final Answer ===")
        print(result.content)

        # Show cost statistics
        if tracker:
            total_cost = sum(cost.total_cost for cost in tracker.storage.costs)
            print(f"\n=== Cost Summary ===")
            print(f"Total cost: ${total_cost:.4f}")
            print(f"Budget remaining: ${5.00 - total_cost:.4f}")

    except Exception as e:
        if "budget" in str(e).lower():
            print(f"\n⚠️  Budget exceeded: {e}")
            print("RLM stopped to prevent runaway costs")
        else:
            raise


if __name__ == "__main__":
    asyncio.run(main())
