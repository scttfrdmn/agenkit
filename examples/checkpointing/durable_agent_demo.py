"""
Durable Agent Demo - Checkpointing for Long-Running Agents

This example demonstrates how to use checkpointing for 30-hour autonomous agents:
- Automatic checkpointing every N steps
- Resume after crashes
- Time-travel debugging
- State persistence
"""

import asyncio
import random
from datetime import datetime

from agenkit.interfaces import Agent, Message
from agenkit.checkpointing import DurableAgent, make_durable


class CounterAgent(Agent):
    """Simple agent that counts messages and maintains state."""

    def __init__(self, agent_name: str = "counter"):
        self._name = agent_name

    @property
    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        """Process message and return response."""
        # Simulate some processing time
        await asyncio.sleep(0.1)

        return Message(
            role="assistant",
            content=f"Processed: {message.content}"
        )


class FailingAgent(Agent):
    """Agent that fails randomly to simulate crashes."""

    def __init__(self, agent_name: str = "failing", fail_probability: float = 0.3):
        self._name = agent_name
        self.fail_probability = fail_probability
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        """Process message, occasionally failing."""
        self.call_count += 1

        # Randomly fail
        if random.random() < self.fail_probability:
            raise RuntimeError(f"Simulated crash at call {self.call_count}")

        return Message(
            role="assistant",
            content=f"Call {self.call_count}: {message.content}"
        )


async def example_1_basic_checkpointing():
    """Example 1: Basic automatic checkpointing."""
    print("\n" + "="*70)
    print("Example 1: Basic Automatic Checkpointing")
    print("="*70)

    # Create durable agent that checkpoints every 3 steps
    agent = CounterAgent("basic-agent")
    durable = DurableAgent(
        agent=agent,
        checkpoint_dir="./checkpoints",
        checkpoint_interval=3,
        auto_resume=False  # Don't resume for this demo
    )

    print("\n📦 Processing 10 messages with checkpoint_interval=3...")

    # Process 10 messages
    for i in range(1, 11):
        message = Message(role="user", content=f"Message {i}")
        response = await durable.process(message, session_id="demo-1")
        print(f"  Step {i}: {response.content}")

    # Show checkpoints created
    checkpoints = await durable.list_checkpoints("demo-1")
    print(f"\n✅ Created {len(checkpoints)} checkpoints:")
    for cp in checkpoints:
        print(f"  - Step {cp.step_number}: {cp.checkpoint_id[:8]}...")

    # Get session stats
    stats = await durable.get_session_stats("demo-1")
    print(f"\n📊 Session Stats:")
    print(f"  Current step: {stats['current_step']}")
    print(f"  Message count: {stats['message_count']}")
    print(f"  Checkpoints: {stats['total_checkpoints']}")


async def example_2_resume_after_crash():
    """Example 2: Resume from checkpoint after simulated crash."""
    print("\n" + "="*70)
    print("Example 2: Resume After Crash")
    print("="*70)

    agent = FailingAgent("crash-agent", fail_probability=0.3)
    durable = DurableAgent(
        agent=agent,
        checkpoint_dir="./checkpoints",
        checkpoint_interval=2,
        auto_resume=False
    )

    session_id = "demo-2"

    print("\n🎲 Processing messages with random failures...")
    print("   (Agent has 30% chance of crashing on each call)\n")

    processed = 0
    max_attempts = 20

    for attempt in range(max_attempts):
        try:
            message = Message(role="user", content=f"Message {attempt + 1}")
            response = await durable.process(message, session_id=session_id)
            processed += 1
            print(f"  ✅ Step {processed}: {response.content}")

            if processed >= 10:
                break

        except RuntimeError as e:
            print(f"  💥 CRASH: {e}")
            print(f"     Resuming from checkpoint...")

            # Resume from last checkpoint
            state = await durable.resume(session_id)
            if state:
                print(f"     ↻ Restored to step {durable._session_steps[session_id]}")
            else:
                print(f"     ↻ Starting fresh (no checkpoint yet)")

    # Show final state
    checkpoints = await durable.list_checkpoints(session_id)
    print(f"\n✅ Successfully processed {processed} messages")
    print(f"📦 Created {len(checkpoints)} checkpoints")


async def example_3_persistence_across_restarts():
    """Example 3: State persists across agent restarts."""
    print("\n" + "="*70)
    print("Example 3: Persistence Across Restarts")
    print("="*70)

    session_id = "demo-3"

    # First run: Create durable agent and process some messages
    print("\n🚀 First Run: Creating agent and processing messages...")
    agent1 = CounterAgent("persistent-agent")
    durable1 = DurableAgent(
        agent=agent1,
        checkpoint_dir="./checkpoints",
        checkpoint_interval=2,
        auto_resume=False
    )

    for i in range(1, 6):
        message = Message(role="user", content=f"Run 1, Message {i}")
        response = await durable1.process(message, session_id=session_id)
        print(f"  Step {i}: Processed")

    checkpoints = await durable1.list_checkpoints(session_id)
    print(f"✅ Created {len(checkpoints)} checkpoints")
    print(f"📊 Final step: {durable1._session_steps[session_id]}")

    # Simulate restart: Create new agent instance
    print("\n🔄 Simulating Restart: Creating new agent instance...")
    agent2 = CounterAgent("persistent-agent")
    durable2 = DurableAgent(
        agent=agent2,
        checkpoint_dir="./checkpoints",  # Same checkpoint dir
        checkpoint_interval=2,
        auto_resume=True  # Auto-resume enabled
    )

    # First call will auto-resume
    print("📥 First call after restart (will auto-resume)...")
    message = Message(role="user", content="Run 2, Message 1")
    response = await durable2.process(message, session_id=session_id)

    print(f"✅ Resumed from step {durable2._session_steps[session_id] - 1}")
    print(f"📊 Current step: {durable2._session_steps[session_id]}")

    # Continue processing
    print("\n▶️  Continuing from where we left off...")
    for i in range(2, 5):
        message = Message(role="user", content=f"Run 2, Message {i}")
        response = await durable2.process(message, session_id=session_id)
        print(f"  Step {durable2._session_steps[session_id]}: Processed")


async def example_4_time_travel_debugging():
    """Example 4: Time-travel debugging with checkpoint replay."""
    print("\n" + "="*70)
    print("Example 4: Time-Travel Debugging")
    print("="*70)

    agent = CounterAgent("debug-agent")
    durable = DurableAgent(
        agent=agent,
        checkpoint_dir="./checkpoints",
        checkpoint_interval=2,
        auto_resume=False
    )

    session_id = "demo-4"

    print("\n📝 Processing messages and creating checkpoints...")
    for i in range(1, 11):
        message = Message(role="user", content=f"Message {i}")
        await durable.process(message, session_id=session_id)
        print(f"  Step {i}: Processed")

    # List all checkpoints
    checkpoints = await durable.list_checkpoints(session_id)
    print(f"\n📦 Created {len(checkpoints)} checkpoints")

    # Time-travel: Load checkpoint from step 6
    print("\n⏪ Time-traveling to step 6...")
    target_checkpoint = None
    for cp in checkpoints:
        if cp.step_number == 6:
            target_checkpoint = cp
            break

    if target_checkpoint:
        print(f"   Found checkpoint: {target_checkpoint.checkpoint_id[:8]}...")

        # Replay from that checkpoint
        async def replay_step(checkpoint, state):
            print(f"   🔄 Replaying step {checkpoint.step_number}")
            return checkpoint.state

        print("\n🎬 Replaying checkpoint history:")
        history = await durable.manager.get_checkpoint_history(
            target_checkpoint.checkpoint_id
        )
        print(f"   Found {len(history)} checkpoints in history")
        for cp in reversed(history):
            print(f"   - Step {cp.step_number}: {len(cp.messages)} messages")


async def example_5_checkpoint_pruning():
    """Example 5: Pruning old checkpoints to manage storage."""
    print("\n" + "="*70)
    print("Example 5: Checkpoint Pruning")
    print("="*70)

    agent = CounterAgent("prune-agent")
    durable = DurableAgent(
        agent=agent,
        checkpoint_dir="./checkpoints",
        checkpoint_interval=1,  # Checkpoint every step
        auto_resume=False
    )

    session_id = "demo-5"

    print("\n📝 Creating 20 checkpoints (one per step)...")
    for i in range(1, 21):
        message = Message(role="user", content=f"Message {i}")
        await durable.process(message, session_id=session_id)

    checkpoints = await durable.list_checkpoints(session_id)
    print(f"✅ Created {len(checkpoints)} checkpoints")

    # Prune to keep only last 5
    print("\n🗑️  Pruning old checkpoints (keeping last 5)...")
    deleted = await durable.manager.prune_old_checkpoints(session_id, keep_last=5)

    remaining = await durable.list_checkpoints(session_id)
    print(f"✅ Deleted {deleted} checkpoints")
    print(f"📦 Remaining: {len(remaining)} checkpoints")
    print(f"   Steps covered: {remaining[-1].step_number} to {remaining[0].step_number}")


async def example_6_custom_state_tracking():
    """Example 6: Custom state tracking with durable agent."""
    print("\n" + "="*70)
    print("Example 6: Custom State Tracking")
    print("="*70)

    class CustomDurableAgent(DurableAgent):
        """DurableAgent with custom state tracking."""

        def _update_state(self, session_id: str, input_message: Message,
                         output_message: Message) -> None:
            """Track custom metrics in state."""
            state = self._session_state[session_id]

            # Track word counts
            input_words = len(input_message.content.split())
            output_words = len(output_message.content.split())

            state["total_input_words"] = state.get("total_input_words", 0) + input_words
            state["total_output_words"] = state.get("total_output_words", 0) + output_words
            state["message_count"] = state.get("message_count", 0) + 1

            # Track timestamps
            state["last_updated"] = datetime.now().isoformat()

    agent = CounterAgent("custom-agent")
    durable = CustomDurableAgent(
        agent=agent,
        checkpoint_dir="./checkpoints",
        checkpoint_interval=3,
        auto_resume=False
    )

    session_id = "demo-6"

    print("\n📝 Processing messages with custom state tracking...")
    messages = [
        "Hello",
        "How are you doing today?",
        "This is a longer message with more words",
        "Short",
        "Final message"
    ]

    for i, content in enumerate(messages, 1):
        message = Message(role="user", content=content)
        await durable.process(message, session_id=session_id)
        print(f"  Step {i}: Processed '{content}'")

    # Show custom state
    state = await durable.get_state(session_id)
    print(f"\n📊 Custom State Tracking:")
    print(f"   Total messages: {state['message_count']}")
    print(f"   Input words: {state['total_input_words']}")
    print(f"   Output words: {state['total_output_words']}")
    print(f"   Last updated: {state['last_updated']}")


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("🚀 DURABLE AGENT EXAMPLES - Checkpointing for 30-Hour Agents")
    print("="*70)

    try:
        await example_1_basic_checkpointing()
        await example_2_resume_after_crash()
        await example_3_persistence_across_restarts()
        await example_4_time_travel_debugging()
        await example_5_checkpoint_pruning()
        await example_6_custom_state_tracking()

        print("\n" + "="*70)
        print("✅ All Examples Completed Successfully!")
        print("="*70)
        print("\n💡 Key Takeaways:")
        print("   • Automatic checkpointing preserves state every N steps")
        print("   • Resume from checkpoints after crashes or restarts")
        print("   • Time-travel debugging with checkpoint replay")
        print("   • Prune old checkpoints to manage storage")
        print("   • Custom state tracking for application-specific needs")
        print("   • Perfect for 30-hour autonomous agent runs")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
