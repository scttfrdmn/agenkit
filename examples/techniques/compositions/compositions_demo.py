"""
Composition Techniques Demo

Demonstrates all 9 composition techniques in Agenkit. These compositions show
that many "features" marketed by frameworks are just simple wiring of primitives.

This demo includes:
1. Simple Human Approval
2. RAG (Retrieval-Augmented Generation)
3. RAG with Citations
4. Context Optimization
5. Prioritization
6. Goal Monitoring
7. Exploration Strategy
8. Learning from Feedback
9. Actor-Critic Variation

Requirements:
    pip install agenkit

Note: These are intentionally simple (10-80 LOC) to show patterns vs compositions.
For production systems, use the full patterns from agenkit.patterns.
"""

import asyncio

from agenkit import Message
from agenkit.techniques.compositions import (ActorCriticVariation, CitedRAG,
                                             ContextOptimizer, Document,
                                             ExplorationStrategy, GoalMonitor,
                                             LearningFromFeedback,
                                             SimpleApprovalTool, SimpleRAG,
                                             TaskQueue)


# Mock LLM for demonstration
class MockLLM:
    """Simple mock LLM for demonstration."""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.call_count = 0

    async def process(self, message: Message) -> Message:
        """Return appropriate mock response based on content."""
        self.call_count += 1
        content = message.content.lower()

        # Pattern matching for different scenarios
        if "summarize" in content:
            return Message(role="assistant", content="This is a concise summary of the content.")

        if "critique" in content or "evaluate" in content:
            return Message(
                role="assistant",
                content="Score: 8/10\nThis is good but could be improved with more detail.",
            )

        if "quantum" in content:
            return Message(
                role="assistant",
                content="Quantum computing uses quantum mechanics for computation.",
            )

        if "similar" in content:
            return Message(
                role="assistant",
                content="These concepts are related through their mathematical foundations.",
            )

        # Default response
        return Message(role="assistant", content=f"Response to query (call {self.call_count})")


async def demo_simple_approval():
    """Demo 1: Simple Human Approval."""
    print("=" * 70)
    print("Demo 1: Simple Human Approval")
    print("=" * 70)
    print("\nA minimal composition for basic approval workflows.")
    print("Use case: Quick prototypes, non-critical decisions\n")

    tool = SimpleApprovalTool()

    # Simulate approval (in real use, this would prompt the user)
    print("Example: Approving a database deletion")
    print("Tool asks: 'Approve delete database? (y/n):'")
    print("User enters: 'n' (rejected)")

    # Mock the input
    import unittest.mock

    with unittest.mock.patch("builtins.input", return_value="n"):
        result = await tool.execute(
            action="delete database", details="Will delete 'users' table with 1000 records"
        )

    print(f"\nResult: approved={result['approved']}")
    print("\nNote: For production, use agenkit.patterns.human_in_loop.HumanInLoopAgent")
    print("which provides confidence thresholds, timeouts, and audit trails.\n")


async def demo_simple_rag():
    """Demo 2: Simple RAG."""
    print("=" * 70)
    print("Demo 2: RAG (Retrieval-Augmented Generation)")
    print("=" * 70)
    print("\nBasic RAG is just: retrieval + generation.")
    print("Use case: Simple question-answering with context\n")

    # Mock retriever
    def mock_retriever(query: str):
        return [
            "Quantum computing uses qubits which can be in superposition.",
            "Quantum algorithms like Shor's algorithm can factor large numbers.",
            "Quantum computers require extreme cooling to operate.",
        ]

    llm = MockLLM()
    rag = SimpleRAG(retriever=mock_retriever, answerer=llm, max_docs=3)

    response = await rag.process(Message(role="user", content="What is quantum computing?"))

    print("Query: What is quantum computing?")
    print(f"\nRetrieved {response.metadata['num_sources']} documents")
    print(f"Answer: {response.content}")
    print("\nNote: This is ~40 LOC. Frameworks market this as 'advanced RAG'.")
    print("For production, add caching, reranking, and error handling.\n")


async def demo_cited_rag():
    """Demo 3: RAG with Citations."""
    print("=" * 70)
    print("Demo 3: RAG with Citations")
    print("=" * 70)
    print("\nAdds source attribution to basic RAG.")
    print("Use case: Legal, medical, research applications\n")

    # Mock retriever with metadata
    def mock_retriever(query: str):
        return [
            Document("Aspirin reduces fever", "Smith et al. 2020", {"page": 42}),
            Document("Aspirin has anti-inflammatory effects", "Jones 2021", {"page": 15}),
        ]

    llm = MockLLM()
    rag = CitedRAG(retriever=mock_retriever, answerer=llm, citation_format="numeric")

    response = await rag.process(Message(role="user", content="What are the effects of aspirin?"))

    print("Query: What are the effects of aspirin?")
    print(f"\nAnswer: {response.content}")
    print("\nCitations:")
    for citation in response.metadata["citations"]:
        print(f"  {citation}")
    print("\nNote: This is ~50 LOC. Books call this 'high-fidelity context engineering'.\n")


async def demo_context_optimization():
    """Demo 4: Context Optimization."""
    print("=" * 70)
    print("Demo 4: Context Optimization")
    print("=" * 70)
    print("\nAutomatically summarizes when context exceeds token limit.")
    print("Use case: Cost reduction, staying within model limits\n")

    base_llm = MockLLM()
    summarizer_llm = MockLLM()

    optimizer = ContextOptimizer(
        agent=base_llm,
        summarizer=summarizer_llm,
        max_tokens=50,  # Very low for demo
    )

    long_text = " ".join(["This is a long document with many words"] * 20)
    response = await optimizer.process(Message(role="user", content=long_text))

    print(f"Original tokens: {response.metadata['original_tokens']}")
    print(f"Optimized: {response.metadata['optimized']}")

    if response.metadata["optimized"]:
        print(f"Compressed tokens: {response.metadata['compressed_tokens']}")
        print(f"Compression ratio: {response.metadata['compression_ratio']:.1f}x")

    print("\nNote: This is ~60 LOC. Frameworks call this 'intelligent token management'.\n")


async def demo_prioritization():
    """Demo 5: Prioritization."""
    print("=" * 70)
    print("Demo 5: Prioritization")
    print("=" * 70)
    print("\nPriority queue for task management.")
    print("Use case: Simple task ordering\n")

    # Priority function based on urgency
    def urgency_priority(task):
        return task.get("urgency", 0)

    queue = TaskQueue(priority_fn=urgency_priority)

    # Add tasks
    tasks = [
        {"name": "Low priority task", "urgency": 1},
        {"name": "Critical bug fix", "urgency": 10},
        {"name": "Medium priority feature", "urgency": 5},
    ]

    for task in tasks:
        queue.add_task(task)
        print(f"Added: {task['name']} (urgency={task['urgency']})")

    print("\nProcessing in priority order:")
    while not queue.is_empty():
        task = queue.get_next_task()
        print(f"  → {task['name']}")

    print("\nNote: This is ~50 LOC using Python's heapq.")
    print("For distributed systems, use Celery or RQ.\n")


async def demo_goal_monitoring():
    """Demo 6: Goal Monitoring."""
    print("=" * 70)
    print("Demo 6: Goal Monitoring")
    print("=" * 70)
    print("\nMonitors progress and stops when goal is reached.")
    print("Use case: Simple goal-driven tasks\n")

    llm = MockLLM()

    # Goal function: stop when progress >= 3 iterations
    iterations_completed = {"count": 0}

    def goal_fn(state):
        iterations_completed["count"] += 1
        print(f"  Iteration {iterations_completed['count']}: Checking progress...")
        return iterations_completed["count"] >= 3

    monitor = GoalMonitor(agent=llm, goal_fn=goal_fn, max_iterations=10)

    print("Starting goal-directed task...\n")
    result = await monitor.achieve_goal(
        initial_message=Message(role="user", content="Build a web application")
    )

    print(f"\nGoal reached: {result.metadata['goal_reached']}")
    print(f"Iterations taken: {result.metadata['iterations']}")
    print("\nNote: This is ~60 LOC. For production, use AutonomousAgent pattern.\n")


async def demo_exploration():
    """Demo 7: Exploration Strategy."""
    print("=" * 70)
    print("Demo 7: Exploration Strategy")
    print("=" * 70)
    print("\nUCB (Upper Confidence Bound) for action selection.")
    print("Use case: Exploration-exploitation tradeoff\n")

    llm = MockLLM()
    actions = ["search", "calculate", "reason"]

    explorer = ExplorationStrategy(agent=llm, actions=actions, exploration_constant=1.0)

    print("Running 5 iterations with UCB action selection...\n")
    for i in range(5):
        response = await explorer.process(Message(role="user", content=f"Task iteration {i + 1}"))

        selected = response.metadata["selected_action"]
        reward = response.metadata["reward"]
        print(f"Iteration {i + 1}: Selected '{selected}' (reward: {reward:.2f})")

    # Show statistics
    print("\nFinal action statistics:")
    for action, stats in explorer.stats.items():
        print(f"  {action}: {stats.trials} trials, {stats.mean_reward:.2f} avg reward")

    print("\nNote: This is ~70 LOC. For serious RL, use Stable-Baselines3 or Ray.\n")


async def demo_learning_feedback():
    """Demo 8: Learning from Feedback."""
    print("=" * 70)
    print("Demo 8: Learning from Feedback")
    print("=" * 70)
    print("\nStores interactions and retrieves similar ones for context.")
    print("Use case: Experience-based learning\n")

    llm = MockLLM()

    learner = LearningFromFeedback(agent=llm, max_context_examples=2)

    # First interaction
    print("Interaction 1: How do I sort a list in Python?")
    response1 = await learner.process(
        Message(role="user", content="How do I sort a list in Python?")
    )
    print(f"  Similar examples used: {response1.metadata['similar_examples']}")

    # Add feedback
    learner.add_feedback(response1, score=0.9)
    print("  Feedback added: 0.9/1.0\n")

    # Second interaction (similar query)
    print("Interaction 2: How do I sort a dictionary in Python?")
    response2 = await learner.process(
        Message(role="user", content="How do I sort a dictionary in Python?")
    )
    print(f"  Similar examples used: {response2.metadata['similar_examples']}")
    print("  Previous interaction was retrieved as context!\n")

    # Memory stats
    stats = learner.get_memory_stats()
    print(
        f"Memory: {stats['total_interactions']} interactions, {stats['average_feedback']:.1f} avg feedback"
    )
    print("\nNote: This is ~80 LOC. For production, use MemoryHierarchyAgent.\n")


async def demo_actor_critic():
    """Demo 9: Actor-Critic Variation."""
    print("=" * 70)
    print("Demo 9: Actor-Critic Variation")
    print("=" * 70)
    print("\nDemonstrates equivalence to Reflection pattern.")
    print("Use case: Educational - understanding terminology\n")

    actor = MockLLM()  # "Actor" = Generator
    critic = MockLLM()  # "Critic" = Evaluator

    ac = ActorCriticVariation(actor=actor, critic=critic, max_iterations=3)

    response = await ac.process(
        Message(role="user", content="Write a function to calculate fibonacci")
    )

    print(f"Actor-Critic completed in {response.metadata['iterations']} iterations")
    print(f"Final quality score: {response.metadata['final_score']:.1f}/1.0")
    print(f"\nScores history: {[f'{s:.1f}' for s in response.metadata['scores_history']]}")

    print("\nIMPORTANT: This is just ReflectionAgent with RL terminology!")
    print("For production, use agenkit.patterns.reflection.ReflectionAgent")
    print("\nTerminology mapping:")
    print("  Actor = Generator (proposes solutions)")
    print("  Critic = Evaluator (assesses quality)")
    print("  This is NOT true RL - no gradient updates or learned value functions\n")


async def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("COMPOSITION TECHNIQUES DEMO")
    print("=" * 70)
    print("\nThis demo shows 9 simple compositions (10-80 LOC each)")
    print("that many frameworks market as 'advanced features'.\n")
    print("Key insight: Compositions are great for prototyping!")
    print("For production, use Agenkit's full patterns.\n")

    await demo_simple_approval()
    await demo_simple_rag()
    await demo_cited_rag()
    await demo_context_optimization()
    await demo_prioritization()
    await demo_goal_monitoring()
    await demo_exploration()
    await demo_learning_feedback()
    await demo_actor_critic()

    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\n Summary:")
    print("  ✓ 9 compositions demonstrated")
    print("  ✓ Each is 10-80 LOC")
    print("  ✓ Perfect for prototypes and learning")
    print("  ✓ Upgrade to full patterns for production")
    print("\nKey takeaway: Many 'innovative features' are just simple wiring.")
    print("Agenkit is transparent about what's complex vs simple.\n")


if __name__ == "__main__":
    asyncio.run(main())
