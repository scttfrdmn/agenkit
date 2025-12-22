"""
Memory Hierarchy Pattern Example - Multi-Tier Memory Management

The Memory Hierarchy pattern provides a multi-tier memory system for agents,
automatically managing memory across working (in-context), short-term (session),
and long-term (persistent) storage tiers.

WHY use this pattern:
✅ Automatic memory management across tiers
✅ Importance-based routing to appropriate tiers
✅ TTL expiration and LRU eviction
✅ Cross-tier search and deduplication
✅ Scalable for long-running agents

WHEN to use:
- Conversational agents needing context
- Personalization and user preferences
- Session continuity across interactions
- Long-term knowledge retention
- Multi-session agents

Run: python examples/patterns/08_memory_hierarchy.py
"""

import asyncio
from datetime import datetime, timedelta, timezone

from agenkit.patterns import (
    LongTermMemory,
    MemoryEntry,
    MemoryHierarchy,
    ShortTermMemory,
    WorkingMemory,
)


async def demo_basic_hierarchy():
    """Demo 1: Basic memory hierarchy with all 3 tiers."""
    print("=" * 70)
    print("Demo 1: Basic Memory Hierarchy - 3-Tier Storage")
    print("=" * 70)

    # Create 3-tier memory system
    hierarchy = MemoryHierarchy(
        working_memory=WorkingMemory(max_messages=5),  # Last 5 messages
        short_term_memory=ShortTermMemory(max_messages=20, ttl_seconds=3600),  # 1 hour TTL
        long_term_memory=LongTermMemory(min_importance=0.7),  # High importance only
    )

    print("\n🧠 Memory System Created:")
    print("  • Working Memory: 5 messages (current context)")
    print("  • Short-Term Memory: 20 messages, 1 hour TTL")
    print("  • Long-Term Memory: importance >= 0.7")

    print("\n📝 Storing memories with different importance levels...\n")

    # Store low-importance memory (working + short-term only)
    id1 = await hierarchy.store(
        content="User asked about the weather today", importance=0.3, session_id="session-1"
    )
    print(f"✓ Stored low-importance memory (0.3): {id1[:8]}...")

    # Store medium-importance memory (working + short-term only)
    id2 = await hierarchy.store(
        content="User prefers metric units over imperial",
        importance=0.5,
        metadata={"preference": "units"},
        session_id="session-1",
    )
    print(f"✓ Stored medium-importance memory (0.5): {id2[:8]}...")

    # Store high-importance memory (all 3 tiers)
    id3 = await hierarchy.store(
        content="User's name is Alice and works as a software engineer",
        importance=0.9,
        metadata={"category": "personal_info"},
        session_id="session-1",
    )
    print(f"✓ Stored high-importance memory (0.9): {id3[:8]}...")

    # Get statistics
    stats = hierarchy.get_stats()

    print("\n📊 Memory Distribution:")
    print(f"  Working Memory: {stats['working']['size']} entries")
    print(f"  Short-Term Memory: {stats['short_term']['size']} entries")
    print(f"  Long-Term Memory: {stats['long_term']['size']} entries")

    print("\n💡 Tier Routing Logic:")
    print("  • Low importance (0.3): Working + Short-Term only")
    print("  • Medium importance (0.5): Working + Short-Term only")
    print("  • High importance (0.9): All 3 tiers (includes Long-Term)")


async def demo_working_memory_eviction():
    """Demo 2: Working memory FIFO eviction."""
    print("\n\n" + "=" * 70)
    print("Demo 2: Working Memory Eviction (FIFO)")
    print("=" * 70)

    working = WorkingMemory(max_messages=3)  # Very small for demo

    print("\n📝 Storing 5 messages (capacity: 3)...\n")

    for i in range(1, 6):
        entry = MemoryEntry(
            id=f"msg-{i}",
            content=f"Message {i}",
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        await working.store(entry)
        print(f"Stored: Message {i} | Working Memory size: {len(working)}")

    print("\n✅ Result: Only last 3 messages retained (FIFO eviction)")

    # Retrieve all
    all_memories = await working.retrieve(query="")
    print("\n📋 Current Working Memory Contents:")
    for mem in all_memories:
        print(f"  • {mem.content}")

    print("\n💡 First 2 messages (1, 2) were evicted automatically")


async def demo_short_term_memory_ttl():
    """Demo 3: Short-term memory TTL expiration."""
    print("\n\n" + "=" * 70)
    print("Demo 3: Short-Term Memory TTL Expiration")
    print("=" * 70)

    short_term = ShortTermMemory(max_messages=100, ttl_seconds=2)  # 2-second TTL for demo

    print("\n📝 Storing memories with timestamps...\n")

    # Store old memory (expired)
    old_entry = MemoryEntry(
        id="old-msg",
        content="This message is from 5 seconds ago",
        metadata={},
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=5),
    )
    short_term._messages.append(old_entry)
    print(f"✓ Added old memory (5 seconds ago) | Size: {len(short_term)}")

    # Store fresh memory - will trigger cleanup
    fresh_entry = MemoryEntry(
        id="fresh-msg",
        content="This message is fresh (just now)",
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    await short_term.store(fresh_entry)
    print(f"✓ Stored fresh memory | Size: {len(short_term)}")

    print("\n📊 Result: Old memory automatically expired")

    # Verify only fresh memory remains
    memories = await short_term.retrieve(query="")
    print("\n📋 Current Short-Term Memory:")
    for mem in memories:
        age = (datetime.now(timezone.utc) - mem.timestamp).total_seconds()
        print(f"  • {mem.content} (age: {age:.1f}s)")

    print("\n💡 TTL-based expiration keeps memory fresh and relevant")


async def demo_cross_tier_search():
    """Demo 4: Cross-tier search and deduplication."""
    print("\n\n" + "=" * 70)
    print("Demo 4: Cross-Tier Search & Deduplication")
    print("=" * 70)

    hierarchy = MemoryHierarchy(
        working_memory=WorkingMemory(max_messages=10),
        short_term_memory=ShortTermMemory(max_messages=50),
        long_term_memory=LongTermMemory(min_importance=0.7),
    )

    print("\n📝 Populating memory with various content...\n")

    # Store memories across tiers
    await hierarchy.store(
        content="Python is a high-level programming language", importance=0.9, session_id="s1"
    )
    await hierarchy.store(
        content="JavaScript is used for web development", importance=0.8, session_id="s1"
    )
    await hierarchy.store(
        content="The user prefers Python over JavaScript", importance=0.6, session_id="s1"
    )
    await hierarchy.store(
        content="Machine learning uses Python extensively", importance=0.9, session_id="s1"
    )
    await hierarchy.store(content="Today's weather is sunny", importance=0.2, session_id="s1")

    print("✓ Stored 5 memories across tiers")

    print("\n🔍 Searching for 'Python' across all tiers...\n")

    # Search across all tiers
    results = await hierarchy.retrieve(query="Python", limit=10)

    print(f"📊 Found {len(results)} memories (deduplicated):\n")
    for i, mem in enumerate(results, 1):
        relevance = mem.metadata.get("relevance_score", 0.0)
        print(f"{i}. {mem.content}")
        print(f"   Relevance: {relevance:.2f} | Importance: {mem.importance:.2f}")
        print()

    print("💡 Results are ranked by relevance and deduplicated across tiers")


async def demo_session_continuity():
    """Demo 5: Session continuity and personalization."""
    print("\n\n" + "=" * 70)
    print("Demo 5: Session Continuity - Real-World Use Case")
    print("=" * 70)

    # Simulate conversational agent with memory
    hierarchy = MemoryHierarchy(
        working_memory=WorkingMemory(max_messages=10),
        short_term_memory=ShortTermMemory(max_messages=100, ttl_seconds=7200),  # 2 hours
        long_term_memory=LongTermMemory(min_importance=0.7),
    )

    print("\n🤖 Conversational Agent - Session 1")
    print("-" * 70)

    # Session 1: Initial conversation
    session_1 = "session-001"

    print("\n👤 User: Hi, my name is Bob")
    await hierarchy.store(
        content="User's name is Bob",
        importance=0.95,
        metadata={"category": "identity"},
        session_id=session_1,
    )
    print("🤖 Agent: Nice to meet you, Bob! (stored in all tiers)")

    print("\n👤 User: I'm interested in learning Python")
    await hierarchy.store(
        content="User wants to learn Python programming",
        importance=0.85,
        metadata={"category": "interest"},
        session_id=session_1,
    )
    print("🤖 Agent: Great choice! Python is versatile. (stored in all tiers)")

    print("\n👤 User: What's the weather like?")
    await hierarchy.store(
        content="User asked about weather",
        importance=0.2,
        metadata={"category": "casual"},
        session_id=session_1,
    )
    print("🤖 Agent: Let me check... (stored in working + short-term only)")

    # Simulate session end and new session
    print("\n\n🤖 Conversational Agent - Session 2 (2 hours later)")
    print("-" * 70)

    session_2 = "session-002"

    print("\n👤 User: Hello again!")

    # Retrieve user context from memory
    user_memories = await hierarchy.retrieve(query="", limit=5)

    print("🤖 Agent: (retrieving context from memory...)")
    print("\n📋 Retrieved Context:")
    for mem in user_memories[:3]:
        print(f"  • {mem.content} (importance: {mem.importance:.2f})")

    print("\n🤖 Agent: Welcome back, Bob! Ready to continue learning Python?")
    print("   (Agent remembered user's name and interest from previous session)")

    # Get statistics
    stats = hierarchy.get_stats()

    print("\n📊 Memory Statistics:")
    print(f"  Working: {stats['working']['size']}/{stats['working']['capacity']}")
    print(f"  Short-Term: {stats['short_term']['size']}/{stats['short_term']['capacity']}")
    print(
        f"  Long-Term: {stats['long_term']['size']} (min importance: {stats['long_term']['min_importance']})"
    )

    print("\n💡 High-importance memories (name, interests) persist across sessions")
    print("💡 Low-importance memories (casual questions) expire naturally")


async def demo_memory_consolidation():
    """Demo 6: Memory consolidation and importance."""
    print("\n\n" + "=" * 70)
    print("Demo 6: Memory Consolidation & Importance Scoring")
    print("=" * 70)

    hierarchy = MemoryHierarchy(
        working_memory=WorkingMemory(max_messages=10),
        short_term_memory=ShortTermMemory(max_messages=50),
        long_term_memory=LongTermMemory(min_importance=0.7),
    )

    print("\n📝 Storing memories with different importance levels...\n")

    memories = [
        ("User lives in San Francisco", 0.95, "personal_info"),
        ("User is vegetarian", 0.9, "personal_info"),
        ("User likes hiking", 0.8, "interest"),
        ("User prefers dark mode", 0.7, "preference"),
        ("User asked about a restaurant", 0.4, "casual"),
        ("User said 'thanks'", 0.1, "casual"),
    ]

    for content, importance, category in memories:
        await hierarchy.store(
            content=content, importance=importance, metadata={"category": category}, session_id="s1"
        )
        tier_info = "ALL TIERS" if importance >= 0.7 else "Working + Short-Term"
        print(f"[{importance:.2f}] {content}")
        print(f"       → {tier_info}")

    print("\n📊 Memory Tier Distribution:")

    stats = hierarchy.get_stats()
    print(f"  Working Memory: {stats['working']['size']} entries")
    print(f"  Short-Term Memory: {stats['short_term']['size']} entries")
    print(f"  Long-Term Memory: {stats['long_term']['size']} entries")

    print("\n💡 Importance-Based Consolidation:")
    print("  • High importance (≥0.7): Permanent long-term storage")
    print("  • Medium importance (0.3-0.7): Short-term session storage")
    print("  • Low importance (<0.3): Working memory only (ephemeral)")

    # Demonstrate retrieval prioritization
    print("\n🔍 Retrieving most important memories...\n")

    important_memories = await hierarchy.retrieve(query="", limit=3)

    print("📋 Top 3 Most Important Memories:")
    for i, mem in enumerate(important_memories, 1):
        print(f"{i}. {mem.content}")
        print(f"   Importance: {mem.importance:.2f} | Category: {mem.metadata.get('category')}")


async def main():
    """Run all demos."""
    print("\n" + "🧠" * 35)
    print("MEMORY HIERARCHY PATTERN DEMONSTRATION")
    print("🧠" * 35 + "\n")

    await demo_basic_hierarchy()
    await demo_working_memory_eviction()
    await demo_short_term_memory_ttl()
    await demo_cross_tier_search()
    await demo_session_continuity()
    await demo_memory_consolidation()

    print("\n" + "=" * 70)
    print("🎉 All demos completed!")
    print("=" * 70)

    print("\n📚 Key Takeaways:")
    print(
        "  • 3-tier memory system: Working (context), Short-Term (session), Long-Term (persistent)"
    )
    print("  • Automatic tier routing based on importance")
    print("  • FIFO eviction (working), LRU + TTL (short-term)")
    print("  • Cross-tier search with deduplication")
    print("  • Perfect for conversational agents and personalization")

    print("\n💡 Production Usage:")
    print("  from agenkit.patterns import (")
    print("      MemoryHierarchy, WorkingMemory, ShortTermMemory, LongTermMemory")
    print("  )")
    print()
    print("  # Create memory system")
    print("  memory = MemoryHierarchy(")
    print("      working_memory=WorkingMemory(max_messages=10),")
    print("      short_term_memory=ShortTermMemory(max_messages=100, ttl_seconds=3600),")
    print("      long_term_memory=LongTermMemory(min_importance=0.7),")
    print("  )")
    print()
    print("  # Store memories")
    print('  await memory.store("User prefers dark mode", importance=0.8)')
    print()
    print("  # Retrieve relevant memories")
    print('  memories = await memory.retrieve(query="user preferences", limit=5)')
    print()
    print("  # Get statistics")
    print("  stats = memory.get_stats()")
    print()

    print("\n🔗 See also:")
    print("  • docs/patterns/MEMORY.md - Detailed pattern guide")
    print("  • examples/patterns/02_react_agent.py - ReAct pattern")
    print("  • examples/patterns/06_reflection_agent.py - Reflection pattern")
    print()


if __name__ == "__main__":
    asyncio.run(main())
