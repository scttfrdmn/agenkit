"""
Collaborative Pattern Usage Example.

Demonstrates the Collaborative pattern for peer-to-peer agent collaboration
with iterative refinement.

Use cases:
- Peer review and feedback
- Iterative refinement
- Consensus building
- Multi-agent brainstorming

This example shows:
- Peer collaboration workflow
- Iterative refinement
- Consensus mechanisms
- Merge strategies
"""

import asyncio

from agenkit.core import Agent, Message
from agenkit.patterns import (CollaborativeAgent, CollaborativeConfig,
                              default_consensus_funcs, default_merge_funcs)


class DraftAgent(Agent):
    """Creates initial drafts."""

    def name(self) -> str:
        return "DraftAgent"

    def capabilities(self) -> list[str]:
        return ["drafting", "writing"]

    async def process(self, message: Message) -> Message:
        """Create a draft."""
        print("   📝 Creating initial draft...")
        await asyncio.sleep(0.1)

        draft = "Draft Document:\n\n"
        draft += f"Topic: {message.content}\n\n"
        draft += "Introduction:\n"
        draft += "[Initial draft content based on the topic]\n\n"
        draft += "Main Points:\n"
        draft += "- Point 1: [content]\n"
        draft += "- Point 2: [content]\n"

        result = Message(role="agent", content=draft)
        result.metadata["iteration"] = 1
        result.metadata["confidence"] = 0.6
        return result


class ReviewerAgent(Agent):
    """Reviews and provides feedback."""

    def __init__(self, name_suffix: str):
        self._name_suffix = name_suffix

    def name(self) -> str:
        return f"Reviewer{self._name_suffix}"

    def capabilities(self) -> list[str]:
        return ["review", "feedback"]

    async def process(self, message: Message) -> Message:
        """Review and suggest improvements."""
        print(f"   👁️  {self.name()} reviewing draft...")
        await asyncio.sleep(0.12)

        feedback = f"Review from {self.name()}:\n\n"
        feedback += "Strengths:\n"
        feedback += "- Clear structure\n"
        feedback += "- Good topic coverage\n\n"
        feedback += "Suggestions:\n"
        feedback += "- Add more examples\n"
        feedback += "- Expand on point 2\n"
        feedback += "- Consider adding conclusion\n"

        result = Message(role="agent", content=feedback)
        result.metadata["review_from"] = self.name()
        result.metadata["confidence"] = 0.8
        return result


class EditorAgent(Agent):
    """Edits and refines content."""

    def name(self) -> str:
        return "EditorAgent"

    def capabilities(self) -> list[str]:
        return ["editing", "refinement"]

    async def process(self, message: Message) -> Message:
        """Edit and refine content."""
        print("   ✏️  Editing and refining...")
        await asyncio.sleep(0.15)

        # Extract iteration from metadata
        iteration = message.metadata.get("iteration", 1) + 1

        refined = f"Refined Document (v{iteration}):\n\n"
        refined += "Topic: [Enhanced topic description]\n\n"
        refined += "Introduction:\n"
        refined += "[Improved introduction with context]\n\n"
        refined += "Main Points:\n"
        refined += "- Point 1: [expanded with examples]\n"
        refined += "- Point 2: [expanded based on feedback]\n"
        refined += "- Point 3: [new point added]\n\n"
        refined += "Conclusion:\n"
        refined += "[Summary and key takeaways]\n"

        result = Message(role="agent", content=refined)
        result.metadata["iteration"] = iteration
        result.metadata["confidence"] = 0.9
        return result


async def basic_collaboration():
    """Demonstrate basic peer collaboration."""
    print("=" * 60)
    print("Example 1: Basic Peer Collaboration")
    print("=" * 60)

    # Create collaborative workflow
    config = CollaborativeConfig(
        max_rounds=2,
        min_consensus=0.8,
    )

    collaborators = CollaborativeAgent(
        agents=[
            DraftAgent(),
            ReviewerAgent("A"),
            EditorAgent(),
        ],
        config=config,
        consensus_func=default_consensus_funcs["confidence_threshold"],
        merge_func=default_merge_funcs["weighted_merge"],
    )

    message = Message(
        role="user",
        content="AI Agent Design Patterns",
    )

    print(f"\n📥 Topic: {message.content}\n")
    print("Starting collaborative process...")

    result = await collaborators.process(message)

    print(f"\n📤 Final Result:\n{result.content}")
    print("\nCollaboration Stats:")
    print(f"   Rounds: {result.metadata.get('rounds', 0)}")
    print(f"   Consensus: {result.metadata.get('consensus', 0):.2f}")


async def multi_reviewer_consensus():
    """Demonstrate multi-reviewer consensus building."""
    print("\n\n" + "=" * 60)
    print("Example 2: Multi-Reviewer Consensus")
    print("=" * 60)

    config = CollaborativeConfig(
        max_rounds=3,
        min_consensus=0.75,
    )

    collaborators = CollaborativeAgent(
        agents=[
            DraftAgent(),
            ReviewerAgent("1"),
            ReviewerAgent("2"),
            ReviewerAgent("3"),
            EditorAgent(),
        ],
        config=config,
        consensus_func=default_consensus_funcs["majority"],
        merge_func=default_merge_funcs["concatenate"],
    )

    message = Message(
        role="user",
        content="Best Practices for Agent Testing",
    )

    print(f"\n📥 Topic: {message.content}\n")
    print("Multiple reviewers collaborating...")

    result = await collaborators.process(message)

    print(f"\n📤 Result preview:\n{result.content[:200]}...")
    print("\nProcess Details:")
    print("   Reviewers: 3")
    print(f"   Rounds completed: {result.metadata.get('rounds', 0)}")
    print(f"   Final consensus: {result.metadata.get('consensus', 0):.2f}")


async def iterative_refinement():
    """Demonstrate iterative refinement process."""
    print("\n\n" + "=" * 60)
    print("Example 3: Iterative Refinement")
    print("=" * 60)

    # Custom consensus function that requires high confidence
    def high_confidence_consensus(messages: list[Message]) -> float:
        """Require high average confidence."""
        confidences = [m.metadata.get("confidence", 0.5) for m in messages]
        return sum(confidences) / len(confidences) if confidences else 0.0

    config = CollaborativeConfig(
        max_rounds=4,
        min_consensus=0.85,  # High threshold
    )

    collaborators = CollaborativeAgent(
        agents=[
            DraftAgent(),
            ReviewerAgent("Quality"),
            EditorAgent(),
        ],
        config=config,
        consensus_func=high_confidence_consensus,
        merge_func=default_merge_funcs["weighted_merge"],
    )

    message = Message(
        role="user",
        content="Production Deployment Checklist",
    )

    print(f"\n📥 Topic: {message.content}\n")
    print("High-quality refinement process...")

    result = await collaborators.process(message)

    print(f"\n📤 Final Quality Document:\n{result.content[:250]}...")
    print("\nQuality Metrics:")
    print(f"   Iterations: {result.metadata.get('rounds', 0)}")
    print(f"   Final confidence: {result.metadata.get('consensus', 0):.2f}")
    print("   Quality threshold: 0.85")


async def custom_merge_strategy():
    """Demonstrate custom merge strategy."""
    print("\n\n" + "=" * 60)
    print("Example 4: Custom Merge Strategy")
    print("=" * 60)

    def section_based_merge(messages: list[Message]) -> Message:
        """Merge by extracting and combining sections."""
        merged = "Collaborative Document:\n\n"

        # Extract sections from messages
        for i, msg in enumerate(messages, 1):
            merged += f"Contribution {i}:\n"
            merged += f"{msg.content[:100]}...\n\n"

        merged += "Synthesis:\n"
        merged += "[Combined insights from all contributors]\n"

        result = Message(role="agent", content=merged)
        result.metadata["contributions"] = len(messages)
        return result

    config = CollaborativeConfig(
        max_rounds=2,
        min_consensus=0.7,
    )

    collaborators = CollaborativeAgent(
        agents=[
            DraftAgent(),
            ReviewerAgent("Expert"),
            EditorAgent(),
        ],
        config=config,
        consensus_func=default_consensus_funcs["unanimous"],
        merge_func=section_based_merge,
    )

    message = Message(
        role="user",
        content="Collaborative AI Systems",
    )

    print(f"\n📥 Topic: {message.content}\n")
    print("Using custom merge strategy...")

    result = await collaborators.process(message)

    print(f"\n📤 Merged Result:\n{result.content}")
    print("\nMerge Details:")
    print(f"   Contributions: {result.metadata.get('contributions', 0)}")


async def main():
    """Run all examples."""
    print("\n🤝 Collaborative Pattern Usage Examples\n")

    await basic_collaboration()
    await multi_reviewer_consensus()
    await iterative_refinement()
    await custom_merge_strategy()

    print("\n✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
