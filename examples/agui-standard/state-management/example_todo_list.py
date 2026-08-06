"""Todo list example with complex state management.

This example demonstrates:
- Nested state structures
- Array operations with JSON Patch
- Multiple concurrent state updates
- Complex state queries
"""

import asyncio
from datetime import datetime
from typing import Any

from agenkit import Agent, Message
from agenkit.protocols.agui import AGUIAdapter, StateManager


class TodoAgent(Agent):
    """Todo list agent with state management."""

    def __init__(self, state_manager: StateManager):
        self._state_manager = state_manager
        self._todos: list[dict[str, Any]] = []
        self._next_id = 1

    @property
    def name(self) -> str:
        return "TodoAgent"

    async def process(self, message: Message) -> Message:
        """Process todo commands."""
        content = message.content.lower()

        if content.startswith("add "):
            title = message.content[4:].strip()
            return self._add_todo(title)

        elif content.startswith("complete "):
            try:
                todo_id = int(message.content[9:].strip())
                return self._complete_todo(todo_id)
            except ValueError:
                return Message(role="assistant", content="❌ Invalid ID. Use: complete <id>")

        elif content.startswith("delete "):
            try:
                todo_id = int(message.content[7:].strip())
                return self._delete_todo(todo_id)
            except ValueError:
                return Message(role="assistant", content="❌ Invalid ID. Use: delete <id>")

        elif "list" in content or "show" in content:
            return self._list_todos()

        elif "stats" in content or "statistics" in content:
            return self._show_stats()

        else:
            return Message(
                role="assistant",
                content=(
                    "📝 Todo List Commands:\n"
                    "  • add <task> - Add a new todo\n"
                    "  • complete <id> - Mark todo as done\n"
                    "  • delete <id> - Remove a todo\n"
                    "  • list - Show all todos\n"
                    "  • stats - Show statistics"
                ),
            )

    def _add_todo(self, title: str) -> Message:
        """Add a new todo."""
        todo = {
            "id": self._next_id,
            "title": title,
            "completed": False,
            "created_at": datetime.now().isoformat(),
        }

        self._todos.append(todo)
        self._next_id += 1

        # Update state with new todo and stats
        self._state_manager.update(f"/todos/{len(self._todos) - 1}", todo)
        self._state_manager.update("/total_count", len(self._todos))
        self._update_stats()

        return Message(
            role="assistant",
            content=f"✅ Added todo #{todo['id']}: {title}",
        )

    def _complete_todo(self, todo_id: int) -> Message:
        """Mark todo as completed."""
        for i, todo in enumerate(self._todos):
            if todo["id"] == todo_id:
                todo["completed"] = True
                todo["completed_at"] = datetime.now().isoformat()

                # Update state
                self._state_manager.update(f"/todos/{i}/completed", True)
                self._state_manager.update(f"/todos/{i}/completed_at", todo["completed_at"])
                self._update_stats()

                return Message(
                    role="assistant",
                    content=f"✨ Completed todo #{todo_id}: {todo['title']}",
                )

        return Message(role="assistant", content=f"❌ Todo #{todo_id} not found")

    def _delete_todo(self, todo_id: int) -> Message:
        """Delete a todo."""
        for i, todo in enumerate(self._todos):
            if todo["id"] == todo_id:
                title = todo["title"]
                del self._todos[i]

                # Remove from state and update count
                self._state_manager.remove(f"/todos/{i}")
                self._state_manager.update("/total_count", len(self._todos))
                self._update_stats()

                return Message(role="assistant", content=f"🗑️ Deleted todo #{todo_id}: {title}")

        return Message(role="assistant", content=f"❌ Todo #{todo_id} not found")

    def _list_todos(self) -> Message:
        """List all todos."""
        if not self._todos:
            return Message(role="assistant", content="📋 No todos yet. Add one!")

        lines = ["📋 **Your Todos:**\n"]
        for todo in self._todos:
            status = "✅" if todo["completed"] else "⬜"
            lines.append(f"{status} #{todo['id']}: {todo['title']}")

        return Message(role="assistant", content="\n".join(lines))

    def _show_stats(self) -> Message:
        """Show todo statistics."""
        total = len(self._todos)
        completed = sum(1 for t in self._todos if t["completed"])
        pending = total - completed

        return Message(
            role="assistant",
            content=(
                f"📊 **Statistics:**\n"
                f"  • Total: {total}\n"
                f"  • Completed: {completed}\n"
                f"  • Pending: {pending}\n"
                f"  • Completion Rate: {(completed / total * 100) if total > 0 else 0:.1f}%"
            ),
        )

    def _update_stats(self):
        """Update statistics in state."""
        total = len(self._todos)
        completed = sum(1 for t in self._todos if t["completed"])
        pending = total - completed

        self._state_manager.update("/stats/total", total)
        self._state_manager.update("/stats/completed", completed)
        self._state_manager.update("/stats/pending", pending)


async def main():
    """Run todo list example."""
    print("=" * 60)
    print("Todo List State Management Example")
    print("=" * 60)
    print()

    # Create state manager with initial state
    state_manager = StateManager(
        initial_state={
            "todos": [],
            "total_count": 0,
            "stats": {"total": 0, "completed": 0, "pending": 0},
        }
    )

    # Create agent and adapter
    agent = TodoAgent(state_manager)
    adapter = AGUIAdapter(
        agent,
        chunk_size=30,
        state_manager=state_manager,
        emit_state_snapshots=True,
    )

    # Scenario: Build a todo list with state tracking
    commands = [
        "add Write documentation",
        "add Implement tests",
        "add Review code",
        "complete 1",
        "add Deploy to production",
        "complete 2",
        "list",
        "stats",
    ]

    for cmd in commands:
        print(f"\n> {cmd}")
        print("-" * 60)

        deltas = []

        async for event in adapter.stream_events(
            message=Message(role="user", content=cmd),
            thread_id="todo-demo",
        ):
            if event.type == "state_delta":
                deltas.extend(event.delta)

            elif event.type == "text_message_content":
                print(event.delta, end="", flush=True)

        print("\n")

        # Show state changes
        if deltas:
            print("State changes:")
            for op in deltas:
                if op["op"] == "add" or op["op"] == "replace":
                    print(f"  {op['op']}: {op['path']} = {op.get('value')}")
                elif op["op"] == "remove":
                    print(f"  {op['op']}: {op['path']}")

    # Show final state
    print("\n\nFinal State:")
    print("=" * 60)
    final_state = state_manager.get_state()
    print(f"Todos: {len(final_state['todos'])}")
    print(f"Stats: {final_state['stats']}")


if __name__ == "__main__":
    asyncio.run(main())
