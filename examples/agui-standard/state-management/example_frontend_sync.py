"""Frontend state synchronization example.

This example demonstrates:
- Bidirectional state sync (agent → frontend, frontend → agent)
- Applying patches from frontend
- State conflict resolution
- Real-world chat application state
"""

import asyncio
from datetime import datetime

from agenkit import Agent, Message
from agenkit.protocols.agui import AGUIAdapter, StateManager


class ChatAgent(Agent):
    """Chat agent with conversation metadata."""

    def __init__(self, state_manager: StateManager):
        self._state_manager = state_manager
        self._message_count = 0
        self._user_preferences = {"theme": "light", "notifications": True}

    @property
    def name(self) -> str:
        return "ChatAgent"

    async def process(self, message: Message) -> Message:
        """Process message and update metadata."""
        self._message_count += 1

        # Update conversation metadata
        self._state_manager.update("/conversation/message_count", self._message_count)
        self._state_manager.update("/conversation/last_message_at", datetime.now().isoformat())

        # Respond to preferences commands
        content = message.content.lower()

        if "theme" in content:
            if "dark" in content:
                self._user_preferences["theme"] = "dark"
                self._state_manager.update("/user/preferences/theme", "dark")
                response = "🌙 Switched to dark theme"
            elif "light" in content:
                self._user_preferences["theme"] = "light"
                self._state_manager.update("/user/preferences/theme", "light")
                response = "☀️ Switched to light theme"
            else:
                response = (
                    f"Current theme: {self._user_preferences['theme']}. "
                    f"Say 'dark theme' or 'light theme' to switch."
                )

        elif "notification" in content:
            if "on" in content or "enable" in content:
                self._user_preferences["notifications"] = True
                self._state_manager.update("/user/preferences/notifications", True)
                response = "🔔 Notifications enabled"
            elif "off" in content or "disable" in content:
                self._user_preferences["notifications"] = False
                self._state_manager.update("/user/preferences/notifications", False)
                response = "🔕 Notifications disabled"
            else:
                status = "enabled" if self._user_preferences["notifications"] else "disabled"
                response = f"Notifications are currently {status}"

        else:
            response = (
                f"Hello! This is message #{self._message_count}.\n\n"
                f"Current settings:\n"
                f"  • Theme: {self._user_preferences['theme']}\n"
                f"  • Notifications: {'on' if self._user_preferences['notifications'] else 'off'}\n\n"
                f"Try: 'dark theme', 'light theme', 'notifications on/off'"
            )

        return Message(role="assistant", content=response)

    def apply_frontend_changes(self, operations: list[dict]):
        """Apply state changes from frontend."""
        print(f"\n📥 Applying {len(operations)} changes from frontend:")
        for op in operations:
            print(f"  {op['op']}: {op['path']} = {op.get('value')}")

            # Apply to state manager
            self._state_manager.apply_patch([op])

            # Sync to local state
            if op["path"] == "/user/preferences/theme":
                self._user_preferences["theme"] = op["value"]
            elif op["path"] == "/user/preferences/notifications":
                self._user_preferences["notifications"] = op["value"]


async def main():
    """Run frontend synchronization example."""
    print("=" * 60)
    print("Frontend State Synchronization Example")
    print("=" * 60)
    print()

    # Create state manager with initial state
    state_manager = StateManager(
        initial_state={
            "conversation": {
                "message_count": 0,
                "last_message_at": None,
                "active": True,
            },
            "user": {"preferences": {"theme": "light", "notifications": True}},
        }
    )

    # Create agent and adapter
    agent = ChatAgent(state_manager)
    adapter = AGUIAdapter(
        agent,
        chunk_size=25,
        state_manager=state_manager,
        emit_state_snapshots=True,
    )

    # Scenario 1: Agent updates state
    print("Scenario 1: Agent Updates State")
    print("-" * 60)

    async for event in adapter.stream_events(
        message=Message(role="user", content="Hello"),
        thread_id="chat-1",
    ):
        if event.type == "state_snapshot":
            print(f"Initial state: {event.snapshot}")

        elif event.type == "state_delta":
            print(f"State delta: {event.delta}")

        elif event.type == "text_message_content":
            print(event.delta, end="", flush=True)

        elif event.type == "run_finished":
            print("\n")

    # Scenario 2: User changes preferences via agent
    print("\nScenario 2: User Changes Preferences")
    print("-" * 60)

    for cmd in ["dark theme", "notifications off"]:
        print(f"\n> {cmd}")

        async for event in adapter.stream_events(
            message=Message(role="user", content=cmd),
            thread_id="chat-1",
        ):
            if event.type == "state_delta":
                print(f"  State changes: {event.delta}")

            elif event.type == "text_message_content":
                print(f"  Response: {event.delta}", end="", flush=True)

        print()

    # Scenario 3: Frontend sends state changes (bidirectional)
    print("\n\nScenario 3: Frontend Sends State Changes")
    print("-" * 60)

    # Simulate frontend sending state changes
    frontend_changes = [
        {"op": "replace", "path": "/user/preferences/theme", "value": "light"},
        {"op": "add", "path": "/user/preferences/language", "value": "en"},
    ]

    agent.apply_frontend_changes(frontend_changes)

    # Agent responds with acknowledgment
    async for event in adapter.stream_events(
        message=Message(role="user", content="Show settings"),
        thread_id="chat-1",
    ):
        if event.type == "state_delta":
            print(f"\nAgent state updates: {event.delta}")

        elif event.type == "text_message_content":
            print(f"{event.delta}", end="", flush=True)

    # Show final state
    print("\n\n\nFinal State:")
    print("=" * 60)
    final_state = state_manager.get_state()
    import json

    print(json.dumps(final_state, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
