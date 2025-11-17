"""
Research Assistant - Autonomous Agent Example

End-to-end example demonstrating:
- Autonomous planning and execution
- Tool orchestration (search, calculator, document reader, notes)
- Memory management (working, short-term, long-term)
- Budget tracking
- Checkpointing and recovery

Usage:
    # Run demo
    python main.py

    # Interactive mode
    python main.py interactive

Or programmatically:
    from main import ResearchAssistant
    assistant = ResearchAssistant()
    result = await assistant.research("What is quantum computing?")
"""

import asyncio
from typing import Optional
from agents import ResearchAgent, ResearchConfig
from memory import MemoryStore
from tools import ToolRegistry, create_default_tools


class ResearchAssistant:
    """
    Complete autonomous research assistant system.

    Features:
    - Autonomous multi-step planning
    - Tool use (search, calculator, document reader, notes)
    - Memory management with three tiers
    - Budget tracking
    - Checkpoint save/load

    Example:
        ```python
        assistant = ResearchAssistant()

        # Execute research task
        result = await assistant.research(
            "What are the key differences between Python and Go?"
        )

        print(f"Answer: {result.answer}")
        print(f"Cost: ${result.cost:.4f}")
        print(f"Iterations: {result.iterations}")

        # Save checkpoint
        assistant.save_checkpoint("research_checkpoint.json")

        # View status
        status = assistant.get_status()
        print(f"Memory: {status['memory_summary']}")
        ```
    """

    def __init__(
        self,
        config: Optional[ResearchConfig] = None,
        enable_verbose: bool = True,
    ):
        """
        Initialize research assistant.

        Args:
            config: Research agent configuration
            enable_verbose: Print detailed logs
        """
        # Initialize memory store
        self.memory = MemoryStore(
            short_term_limit=100,
            long_term_consolidation_threshold=0.7,
        )

        # Initialize tool registry
        self.tools = ToolRegistry()

        # Register default tools
        for tool in create_default_tools():
            self.tools.register_tool(tool)

        # Initialize research agent
        self.config = config or ResearchConfig(verbose=enable_verbose)
        self.agent = ResearchAgent(
            tools=self.tools,
            memory=self.memory,
            config=self.config,
        )

        if enable_verbose:
            print("✓ Research Assistant initialized")
            print(f"  Tools available: {len(self.tools)}")
            print(f"  Memory capacity: {self.memory.short_term_limit} short-term entries")
            print(
                f"  Budget: ${self.config.max_budget:.2f}, Max iterations: {self.config.max_iterations}"
            )

    async def research(self, task: str, **kwargs):
        """
        Execute a research task.

        Args:
            task: Research question or task
            **kwargs: Additional arguments for the agent

        Returns:
            ResearchResult with answer and metadata
        """
        return await self.agent.research(task, **kwargs)

    def save_checkpoint(self, filepath: str):
        """
        Save system state to checkpoint.

        Args:
            filepath: Path to save checkpoint
        """
        self.agent.save_checkpoint(filepath)
        print(f"✓ Checkpoint saved: {filepath}")

    def load_checkpoint(self, filepath: str):
        """
        Load system state from checkpoint.

        Args:
            filepath: Path to checkpoint file
        """
        self.agent.load_checkpoint(filepath)
        print(f"✓ Checkpoint loaded: {filepath}")

    def get_status(self):
        """Get current system status."""
        return self.agent.get_status()

    def clear_memory(self):
        """Clear all memory."""
        self.memory.clear_all()
        print("✓ Memory cleared")


async def demo_tasks():
    """Demonstrate the system with various research tasks."""
    print("\n" + "=" * 70)
    print("AUTONOMOUS RESEARCH ASSISTANT - DEMO")
    print("=" * 70)

    # Initialize assistant
    assistant = ResearchAssistant(
        config=ResearchConfig(
            max_iterations=8,
            max_budget=0.1,
            enable_planning=True,
            enable_reflection=True,
            verbose=True,
        )
    )

    # Test tasks covering different scenarios
    test_tasks = [
        {
            "task": "What are the key differences between Python and Go?",
            "description": "Research task requiring search and synthesis",
        },
        {
            "task": "Calculate the compound interest on $10,000 at 5% for 10 years",
            "description": "Calculation task",
        },
        {
            "task": "Explain how machine learning models are trained",
            "description": "Complex research requiring multiple sources",
        },
    ]

    # Process each task
    for i, test_case in enumerate(test_tasks, 1):
        print(f"\n\n{'*' * 70}")
        print(f"DEMO TASK #{i}: {test_case['description']}")
        print(f"{'*' * 70}")
        print(f"Task: {test_case['task']}")

        result = await assistant.research(test_case["task"])

        # Print summary
        print(f"\n{'=' * 70}")
        print(f"RESULT:")
        print(f"{'=' * 70}")
        print(f"\n{result.answer}")
        print(f"\n{'=' * 70}")
        print(f"SUMMARY:")
        print(f"  Success: {result.success}")
        print(f"  Iterations: {result.iterations}")
        print(f"  Cost: ${result.cost:.4f}")
        print(f"  Tools used: {', '.join(set(result.tools_used)) if result.tools_used else 'None'}")
        print(f"{'=' * 70}")

        # Small delay between tasks
        await asyncio.sleep(0.5)

    # Show final system status
    print(f"\n\n{'=' * 70}")
    print("SYSTEM STATUS")
    print(f"{'=' * 70}")

    status = assistant.get_status()
    print(f"\nMemory:")
    for mem_type, stats in status["memory_summary"]["by_type"].items():
        print(f"  {mem_type}: {stats['count']} entries")

    print(f"\nTools:")
    for tool_name, stats in status["tool_stats"]["by_tool"].items():
        if stats["usage_count"] > 0:
            print(
                f"  {tool_name}: used {stats['usage_count']}x, avg time: {stats['avg_time']:.3f}s"
            )

    print(f"\nTotal cost: ${status['tool_stats']['total_cost']:.4f}")

    print(f"\n{'=' * 70}")
    print("DEMO COMPLETE")
    print(f"{'=' * 70}")


async def interactive_mode():
    """Interactive mode for testing the system."""
    print("\n" + "=" * 70)
    print("AUTONOMOUS RESEARCH ASSISTANT - INTERACTIVE MODE")
    print("=" * 70)
    print("\nCommands:")
    print("  - Type your research question")
    print("  - 'save <file>' - Save checkpoint")
    print("  - 'load <file>' - Load checkpoint")
    print("  - 'status' - View system status")
    print("  - 'clear' - Clear memory")
    print("  - 'quit' - Exit")
    print("=" * 70)

    assistant = ResearchAssistant(
        config=ResearchConfig(
            max_iterations=10,
            max_budget=0.5,
            enable_planning=True,
            enable_reflection=True,
            verbose=True,
        )
    )

    while True:
        print("\n")
        user_input = input("Research > ").strip()

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "q"]:
            print("\nGoodbye!")
            break

        # Handle commands
        if user_input.startswith("save "):
            filepath = user_input[5:].strip()
            assistant.save_checkpoint(filepath)
            continue

        if user_input.startswith("load "):
            filepath = user_input[5:].strip()
            try:
                assistant.load_checkpoint(filepath)
            except Exception as e:
                print(f"❌ Failed to load checkpoint: {e}")
            continue

        if user_input.lower() == "status":
            status = assistant.get_status()
            print(f"\nSystem Status:")
            print(f"  Memory: {status['memory_summary']['total_memories']} entries")
            print(f"  Tools: {status['tool_stats']['total_tools']} available")
            print(f"  Total cost: ${status['tool_stats']['total_cost']:.4f}")
            print(f"  Budget remaining: ${status['budget_remaining']:.4f}")
            continue

        if user_input.lower() == "clear":
            assistant.clear_memory()
            continue

        # Execute research task
        try:
            result = await assistant.research(user_input)

            if not result.success:
                print(f"\n❌ Research failed: {result.error}")

        except Exception as e:
            print(f"\n❌ Error: {e}")


async def checkpoint_demo():
    """Demonstrate checkpoint save/load functionality."""
    print("\n" + "=" * 70)
    print("CHECKPOINT DEMO")
    print("=" * 70)

    # Create assistant and do some research
    print("\n1. Creating assistant and executing research...")
    assistant = ResearchAssistant(enable_verbose=False)

    result1 = await assistant.research("What is Python?")
    print(f"   First research complete: {result1.iterations} iterations, ${result1.cost:.4f}")

    # Save checkpoint
    print("\n2. Saving checkpoint...")
    checkpoint_file = "/tmp/research_checkpoint.json"
    assistant.save_checkpoint(checkpoint_file)

    # Do more research
    result2 = await assistant.research("What is Go?")
    print(f"   Second research complete: {result2.iterations} iterations, ${result2.cost:.4f}")

    status_before = assistant.get_status()
    print(f"   Memory before load: {status_before['memory_summary']['total_memories']} entries")

    # Load checkpoint (restores state from after first research)
    print("\n3. Loading checkpoint (rolls back to first research state)...")
    assistant.load_checkpoint(checkpoint_file)

    status_after = assistant.get_status()
    print(f"   Memory after load: {status_after['memory_summary']['total_memories']} entries")

    print("\n✓ Checkpoint demo complete")
    print("=" * 70)


async def main():
    """Main entry point."""
    import sys

    # Check for command-line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

        if mode == "interactive":
            await interactive_mode()
            return

        if mode == "checkpoint":
            await checkpoint_demo()
            return

    # Default: run demo
    await demo_tasks()


if __name__ == "__main__":
    asyncio.run(main())
