"""Autonomous Research Agent with planning, tool use, and memory."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
from agenkit import Agent, Message
from memory import MemoryStore, MemoryType
from tools import ToolRegistry


@dataclass
class ResearchConfig:
    """Configuration for research agent."""

    max_iterations: int = 10  # Max autonomous steps
    max_budget: float = 1.0  # Max cost allowed
    max_tool_failures: int = 3  # Max consecutive tool failures
    enable_planning: bool = True  # Whether to create plans before executing
    enable_reflection: bool = True  # Whether to reflect after each step
    verbose: bool = True  # Print detailed logs


@dataclass
class ResearchResult:
    """Result from research task."""

    success: bool
    answer: str
    iterations: int
    cost: float
    tools_used: List[str]
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResearchAgent(Agent):
    """
    Autonomous research agent with planning, tool use, and memory.

    The agent can:
    - Create multi-step plans to answer questions
    - Use tools autonomously (search, calculator, document reader, notes)
    - Manage working memory, short-term, and long-term memory
    - Track budget and costs
    - Save/load checkpoints
    - Reflect on progress and adjust strategy

    Example:
        ```python
        # Initialize agent
        agent = ResearchAgent(
            tools=tool_registry,
            memory=memory_store,
            config=ResearchConfig(max_iterations=10, max_budget=0.5)
        )

        # Execute research task
        result = await agent.research("What are the latest developments in quantum computing?")

        print(f"Answer: {result.answer}")
        print(f"Cost: ${result.cost:.4f}")
        print(f"Iterations: {result.iterations}")
        ```
    """

    def __init__(
        self,
        tools: ToolRegistry,
        memory: MemoryStore,
        config: Optional[ResearchConfig] = None,
    ):
        """
        Initialize research agent.

        Args:
            tools: Tool registry with available tools
            memory: Memory store for context
            config: Agent configuration
        """
        self.tools = tools
        self.memory = memory
        self.config = config or ResearchConfig()
        self._current_cost = 0.0
        self._current_iteration = 0

    @property
    def name(self) -> str:
        return "ResearchAgent"

    async def process(self, message: Message) -> Message:
        """
        Process a message (required by Agent interface).

        For research agent, use the `research()` method instead for full functionality.
        """
        result = await self.research(message.content)

        return Message(
            role="assistant",
            content=result.answer,
            metadata={
                "success": result.success,
                "cost": result.cost,
                "iterations": result.iterations,
                "tools_used": result.tools_used,
            },
        )

    async def research(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> ResearchResult:
        """
        Execute an autonomous research task.

        The agent will:
        1. Create a plan (if enabled)
        2. Execute steps using tools
        3. Reflect and adjust (if enabled)
        4. Return final answer

        Args:
            task: Research question or task
            context: Optional additional context

        Returns:
            ResearchResult with answer and metadata
        """
        if self.config.verbose:
            print(f"\n{'='*70}")
            print(f"RESEARCH TASK: {task}")
            print(f"{'='*70}")

        # Reset state
        self._current_cost = 0.0
        self._current_iteration = 0
        self.memory.clear_working_memory()

        # Store task in memory
        self.memory.store(
            "current_task",
            task,
            MemoryType.WORKING,
            metadata={"started_at": datetime.now().isoformat()},
            importance=1.0,
        )

        # Create plan
        if self.config.enable_planning:
            plan = self._create_plan(task)
            if self.config.verbose:
                print(f"\nPLAN:")
                for i, step in enumerate(plan, 1):
                    print(f"  {i}. {step}")

            self.memory.store(
                "plan",
                "\n".join(f"{i}. {step}" for i, step in enumerate(plan, 1)),
                MemoryType.WORKING,
                importance=0.9,
            )
        else:
            plan = [task]

        # Execute research loop
        tools_used = []
        error = None

        try:
            answer = await self._execute_research_loop(task, plan, tools_used)
            success = True

        except Exception as e:
            error = str(e)
            answer = f"Research failed: {error}"
            success = False

            if self.config.verbose:
                print(f"\n❌ ERROR: {error}")

        # Store result in long-term memory if successful
        if success:
            self.memory.store(
                f"research_result_{datetime.now().timestamp()}",
                f"Task: {task}\nAnswer: {answer}",
                MemoryType.LONG_TERM,
                metadata={
                    "task": task,
                    "cost": self._current_cost,
                    "iterations": self._current_iteration,
                },
                importance=0.8,
            )

        if self.config.verbose:
            print(f"\n{'='*70}")
            print(f"RESEARCH COMPLETE")
            print(f"  Success: {success}")
            print(f"  Iterations: {self._current_iteration}")
            print(f"  Cost: ${self._current_cost:.4f}")
            print(f"  Tools used: {', '.join(set(tools_used)) if tools_used else 'None'}")
            print(f"{'='*70}\n")

        return ResearchResult(
            success=success,
            answer=answer,
            iterations=self._current_iteration,
            cost=self._current_cost,
            tools_used=tools_used,
            error=error,
            metadata={
                "task": task,
                "plan": plan if self.config.enable_planning else None,
            },
        )

    async def _execute_research_loop(
        self, task: str, plan: List[str], tools_used: List[str]
    ) -> str:
        """Execute the main research loop."""
        consecutive_failures = 0
        findings = []

        for step_num, step in enumerate(plan, 1):
            self._current_iteration = step_num

            if self._current_iteration > self.config.max_iterations:
                if self.config.verbose:
                    print(f"\n⚠ Reached max iterations ({self.config.max_iterations})")
                break

            if self._current_cost >= self.config.max_budget:
                if self.config.verbose:
                    print(f"\n⚠ Reached budget limit (${self.config.max_budget:.4f})")
                break

            if self.config.verbose:
                print(f"\n[Step {step_num}/{len(plan)}] {step}")

            # Decide which tool to use for this step
            tool_name, tool_params = self._decide_tool(step, task)

            if tool_name is None:
                # No tool needed, just reasoning
                finding = self._reason_about(step, findings)
                findings.append(finding)

                if self.config.verbose:
                    print(f"  💭 Reasoning: {finding}")

                continue

            # Execute tool
            if self.config.verbose:
                print(f"  🔧 Using tool: {tool_name}")
                print(f"     Parameters: {tool_params}")

            result = await self.tools.execute(tool_name, **tool_params)
            tools_used.append(tool_name)

            # Track cost
            tool = self.tools.get(tool_name)
            if tool:
                self._current_cost += tool.cost

            if result.success:
                consecutive_failures = 0

                # Store finding
                finding = f"Used {tool_name}: {result.output}"
                findings.append(finding)

                # Store in memory
                self.memory.store(
                    f"finding_{step_num}",
                    str(result.output),
                    MemoryType.SHORT_TERM,
                    metadata={
                        "step": step_num,
                        "tool": tool_name,
                        "cost": tool.cost if tool else 0.0,
                    },
                    importance=0.6,
                )

                if self.config.verbose:
                    print(f"  ✓ Result: {result.output}")

            else:
                consecutive_failures += 1

                if self.config.verbose:
                    print(f"  ✗ Failed: {result.error}")

                if consecutive_failures >= self.config.max_tool_failures:
                    raise RuntimeError(
                        f"Too many consecutive tool failures ({consecutive_failures})"
                    )

            # Reflect on progress
            if self.config.enable_reflection and step_num % 2 == 0:
                reflection = self._reflect_on_progress(task, findings)
                if self.config.verbose:
                    print(f"  💭 Reflection: {reflection}")

        # Synthesize final answer
        answer = self._synthesize_answer(task, findings)
        return answer

    def _create_plan(self, task: str) -> List[str]:
        """
        Create a multi-step plan to answer the task.

        In production, use an LLM to generate the plan.
        Here we use simple heuristics.
        """
        task_lower = task.lower()

        # Check if task involves search
        if any(
            word in task_lower
            for word in ["what", "how", "why", "explain", "find", "research"]
        ):
            # Research-type task
            return [
                f"Search for information about: {task}",
                "Read the most relevant document",
                "Take notes on key findings",
                "Synthesize answer from findings",
            ]

        # Check if task involves calculation
        elif any(
            word in task_lower for word in ["calculate", "compute", "math", "number"]
        ):
            return [
                "Identify the calculation needed",
                "Perform the calculation",
                "Verify the result",
            ]

        # Default plan
        else:
            return [
                f"Understand the task: {task}",
                "Gather relevant information",
                "Formulate answer",
            ]

    def _decide_tool(
        self, step: str, context: str
    ) -> tuple[Optional[str], Dict[str, Any]]:
        """
        Decide which tool to use for a step.

        In production, use an LLM with function calling.
        Here we use keyword matching.
        """
        step_lower = step.lower()

        # Search tool
        if any(word in step_lower for word in ["search", "find", "look up"]):
            query = context  # Simplified
            return "search", {"query": query, "num_results": 3}

        # Document reader
        elif "read" in step_lower and "document" in step_lower:
            # In a real system, we'd extract the URL from previous search results
            return "read_document", {"url": "https://example.com/article"}

        # Calculator
        elif any(
            word in step_lower for word in ["calculate", "compute", "math"]
        ):
            # In a real system, extract the expression
            return "calculator", {"expression": "2 + 2"}

        # Notes
        elif "note" in step_lower or "remember" in step_lower:
            return "notes", {"action": "list"}

        # No tool needed
        return None, {}

    def _reason_about(self, step: str, findings: List[str]) -> str:
        """
        Perform reasoning without tools.

        In production, use an LLM.
        """
        if not findings:
            return f"Considering: {step}"

        return f"Based on {len(findings)} findings, continuing with: {step}"

    def _reflect_on_progress(self, task: str, findings: List[str]) -> str:
        """
        Reflect on progress so far.

        In production, use an LLM to assess progress and adjust strategy.
        """
        if not findings:
            return "Just starting, no findings yet"

        return f"Made progress: {len(findings)} findings so far. Continuing research."

    def _synthesize_answer(self, task: str, findings: List[str]) -> str:
        """
        Synthesize final answer from findings.

        In production, use an LLM to create coherent answer.
        """
        if not findings:
            return "Unable to find sufficient information to answer the task."

        # Simple synthesis
        answer_parts = [
            f"Based on research with {len(findings)} steps:",
            "",
        ]

        for i, finding in enumerate(findings, 1):
            # Truncate long findings
            finding_short = (
                finding[:100] + "..." if len(finding) > 100 else finding
            )
            answer_parts.append(f"{i}. {finding_short}")

        answer_parts.append("")
        answer_parts.append(
            f"In summary, the research indicates that {task.lower()} involves multiple factors and considerations as shown above."
        )

        return "\n".join(answer_parts)

    def save_checkpoint(self, filepath: str):
        """
        Save agent state to checkpoint.

        Args:
            filepath: Path to save checkpoint
        """
        import json

        checkpoint = {
            "cost": self._current_cost,
            "iteration": self._current_iteration,
            "config": {
                "max_iterations": self.config.max_iterations,
                "max_budget": self.config.max_budget,
                "max_tool_failures": self.config.max_tool_failures,
                "enable_planning": self.config.enable_planning,
                "enable_reflection": self.config.enable_reflection,
            },
            "timestamp": datetime.now().isoformat(),
        }

        with open(filepath, "w") as f:
            json.dump(checkpoint, f, indent=2)

        # Save memory separately
        memory_file = filepath.replace(".json", "_memory.json")
        self.memory.save_checkpoint(memory_file)

        if self.config.verbose:
            print(f"✓ Checkpoint saved to {filepath}")

    def load_checkpoint(self, filepath: str):
        """
        Load agent state from checkpoint.

        Args:
            filepath: Path to checkpoint file
        """
        import json

        with open(filepath, "r") as f:
            checkpoint = json.load(f)

        self._current_cost = checkpoint["cost"]
        self._current_iteration = checkpoint["iteration"]

        # Restore config
        config_data = checkpoint["config"]
        self.config.max_iterations = config_data["max_iterations"]
        self.config.max_budget = config_data["max_budget"]
        self.config.max_tool_failures = config_data["max_tool_failures"]
        self.config.enable_planning = config_data["enable_planning"]
        self.config.enable_reflection = config_data["enable_reflection"]

        # Load memory
        memory_file = filepath.replace(".json", "_memory.json")
        self.memory.load_checkpoint(memory_file)

        if self.config.verbose:
            print(f"✓ Checkpoint loaded from {filepath}")

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "current_iteration": self._current_iteration,
            "current_cost": self._current_cost,
            "budget_remaining": self.config.max_budget - self._current_cost,
            "memory_summary": self.memory.get_summary(),
            "tool_stats": self.tools.get_statistics(),
        }
