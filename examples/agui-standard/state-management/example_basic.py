"""Basic state synchronization example with AG-UI Standard.

This example demonstrates:
- Shared state between agent and frontend
- StateDelta events with JSON Patch
- State updates triggered by agent actions
- Efficient incremental state synchronization
"""

import asyncio

from agenkit import Agent, Message
from agenkit.protocols.agui import AGUIAdapter, StateManager


class CounterAgent(Agent):
    """Simple counter agent that maintains state."""

    def __init__(self, state_manager: StateManager):
        self._state_manager = state_manager
        self._count = 0

    @property
    def name(self) -> str:
        return "CounterAgent"

    async def process(self, message: Message) -> Message:
        """Process message and update state."""
        content = message.content.lower()

        if "increment" in content or "++" in content:
            self._count += 1
            self._state_manager.update("/count", self._count)
            response = f"✅ Incremented! Count is now: {self._count}"

        elif "decrement" in content or "--" in content:
            self._count -= 1
            self._state_manager.update("/count", self._count)
            response = f"⬇️ Decremented! Count is now: {self._count}"

        elif "reset" in content:
            self._count = 0
            self._state_manager.update("/count", self._count)
            response = f"🔄 Reset! Count is now: {self._count}"

        elif "status" in content or "current" in content:
            response = f"📊 Current count: {self._count}"

        else:
            response = (
                f"I'm a counter agent. Commands:\n"
                f"  • 'increment' or '++' - Add 1\n"
                f"  • 'decrement' or '--' - Subtract 1\n"
                f"  • 'reset' - Reset to 0\n"
                f"  • 'status' - Show current count\n\n"
                f"Current count: {self._count}"
            )

        return Message(role="assistant", content=response)


async def main():
    """Run basic state synchronization example."""
    print("=" * 60)
    print("Basic State Synchronization Example")
    print("=" * 60)
    print()

    # Create state manager with initial state
    state_manager = StateManager(initial_state={"count": 0, "last_action": None})

    # Create agent with state manager
    agent = CounterAgent(state_manager)

    # Create adapter with state manager
    adapter = AGUIAdapter(
        agent,
        chunk_size=20,
        state_manager=state_manager,
        emit_state_snapshots=True,  # Emit initial snapshot
    )

    # Test 1: Increment with state delta
    print("Test 1: Increment")
    print("-" * 60)

    async for event in adapter.stream_events(
        message=Message(role="user", content="increment"),
        thread_id="test-1",
    ):
        print(f"Event: {event.type}")

        if event.type == "state_snapshot":
            print(f"  Initial state: {event.snapshot}")

        elif event.type == "state_delta":
            print(f"  State delta: {event.delta}")

        elif event.type == "text_message_content":
            print(f"  Text: {event.delta}", end="", flush=True)

        elif event.type == "run_finished":
            print("\n")

    # Test 2: Multiple operations with state tracking
    print("\nTest 2: Multiple Operations")
    print("-" * 60)

    for action in ["increment", "increment", "decrement", "status"]:
        print(f"\nAction: {action}")

        state_changes = []

        async for event in adapter.stream_events(
            message=Message(role="user", content=action),
            thread_id="test-2",
        ):
            if event.type == "state_delta":
                state_changes.append(event.delta)

            elif event.type == "run_finished":
                if state_changes:
                    print(f"  State changes: {state_changes}")
                else:
                    print("  No state changes")

    # Test 3: Reset with state delta
    print("\n\nTest 3: Reset")
    print("-" * 60)

    async for event in adapter.stream_events(
        message=Message(role="user", content="reset"),
        thread_id="test-3",
    ):
        if event.type == "state_delta":
            print(f"  State delta: {event.delta}")
            for op in event.delta:
                print(f"    Operation: {op['op']} at {op['path']} = {op.get('value')}")

    # Show final state
    print("\n\nFinal State:")
    print("-" * 60)
    final_state = state_manager.get_state()
    print(f"  {final_state}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
