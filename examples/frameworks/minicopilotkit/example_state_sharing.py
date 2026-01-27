"""Shared state example with MiniCopilotKit.

This example demonstrates:
- State hooks (like useCopilotReadable/useCopilotAction)
- Bidirectional state sync (agent ↔ frontend)
- Real-time state updates
- Multiple state hooks

Compare with CopilotKit:
- CopilotKit: useCopilotReadable/useCopilotAction React hooks
- MiniCopilotKit: StateHook with AG-UI StateManager
- Both: Bidirectional sync, real-time updates, typed state
"""

import asyncio

from agenkit import Agent, Message

from minicopilotkit import CopilotAgent, StateHook, create_copilot_agent


class CounterAgent(Agent):
    """Agent that maintains counter state."""

    def __init__(self, counter_hook: StateHook):
        self.counter_hook = counter_hook

    @property
    def name(self) -> str:
        return "CounterAgent"

    async def process(self, message: Message) -> Message:
        """Process message and update counter."""
        content = message.content.lower()
        current = self.counter_hook.get()

        if "increment" in content or "++" in content:
            new_value = current + 1
            self.counter_hook.update(new_value)
            response = f"✅ Incremented! Counter: {new_value}"

        elif "decrement" in content or "--" in content:
            new_value = current - 1
            self.counter_hook.update(new_value)
            response = f"⬇️ Decremented! Counter: {new_value}"

        elif "reset" in content:
            self.counter_hook.update(0)
            response = f"🔄 Reset! Counter: 0"

        elif "status" in content or "current" in content:
            response = f"📊 Current counter: {current}"

        else:
            response = (
                f"Counter Agent Commands:\n"
                f"  • increment / ++ - Add 1\n"
                f"  • decrement / -- - Subtract 1\n"
                f"  • reset - Reset to 0\n"
                f"  • status - Show current value\n\n"
                f"Current counter: {current}"
            )

        return Message(role="assistant", content=response)


class TodoAgent(Agent):
    """Agent that maintains todo list state."""

    def __init__(self, todos_hook: StateHook):
        self.todos_hook = todos_hook

    @property
    def name(self) -> str:
        return "TodoAgent"

    async def process(self, message: Message) -> Message:
        """Process message and update todos."""
        content = message.content.lower()
        todos = self.todos_hook.get() or []

        if content.startswith("add "):
            todo = message.content[4:].strip()
            todos.append({"id": len(todos) + 1, "text": todo, "done": False})
            self.todos_hook.update(todos)
            response = f"✅ Added: {todo}\n\nTotal todos: {len(todos)}"

        elif content.startswith("complete "):
            try:
                todo_id = int(message.content[9:].strip())
                for todo in todos:
                    if todo["id"] == todo_id:
                        todo["done"] = True
                        self.todos_hook.update(todos)
                        response = f"✨ Completed: {todo['text']}"
                        break
                else:
                    response = f"❌ Todo #{todo_id} not found"
            except ValueError:
                response = "❌ Invalid ID"

        elif "list" in content or "show" in content:
            if not todos:
                response = "📋 No todos yet. Add one with: add <task>"
            else:
                lines = ["📋 Your Todos:\n"]
                for todo in todos:
                    status = "✅" if todo["done"] else "⬜"
                    lines.append(f"{status} #{todo['id']}: {todo['text']}")
                response = "\n".join(lines)

        else:
            response = (
                "Todo Agent Commands:\n"
                "  • add <task> - Add new todo\n"
                "  • complete <id> - Mark as done\n"
                "  • list - Show all todos\n\n"
                f"Current todos: {len(todos)}"
            )

        return Message(role="assistant", content=response)


# ============================================
# Demos
# ============================================


async def demo_counter_state():
    """Demonstrate counter state hook."""
    print("=" * 60)
    print("Counter State Hook Demo")
    print("=" * 60)
    print()

    # Create state hook
    counter_hook = StateHook("counter", initial_value=0)

    # Create agent with hook
    agent = CounterAgent(counter_hook)
    copilot = CopilotAgent(agent, hooks=[counter_hook])

    # Commands
    commands = ["increment", "increment", "status", "decrement", "reset"]

    for cmd in commands:
        print(f"User: {cmd}")

        message = Message(role="user", content=cmd)
        async for event in copilot.stream_chat(message, "counter-demo"):
            if event.type == "state_delta":
                print(f"  🔄 State updated: {event.delta}")
            elif event.type == "text_message_content":
                print(f"  {event.delta}", end="", flush=True)

        print("\n")

    # Show final state
    print(f"Final counter value: {counter_hook.get()}")


async def demo_todo_state():
    """Demonstrate todo list state hook."""
    print("\n\n" + "=" * 60)
    print("Todo List State Hook Demo")
    print("=" * 60)
    print()

    # Create state hook
    todos_hook = StateHook("todos", initial_value=[])

    # Create agent with hook
    agent = TodoAgent(todos_hook)
    copilot = CopilotAgent(agent, hooks=[todos_hook])

    # Commands
    commands = [
        "add Write documentation",
        "add Implement tests",
        "add Review code",
        "complete 1",
        "list",
    ]

    for cmd in commands:
        print(f"User: {cmd}")

        message = Message(role="user", content=cmd)
        async for event in copilot.stream_chat(message, "todo-demo"):
            if event.type == "state_delta":
                print(f"  🔄 State updated")
            elif event.type == "text_message_content":
                print(f"  {event.delta}", end="", flush=True)

        print("\n")

    # Show final state
    todos = todos_hook.get()
    print(f"Final todos: {len(todos)} items")
    for todo in todos:
        status = "✅" if todo["done"] else "⬜"
        print(f"  {status} {todo['text']}")


async def demo_multiple_hooks():
    """Demonstrate multiple state hooks."""
    print("\n\n" + "=" * 60)
    print("Multiple State Hooks Demo")
    print("=" * 60)
    print()

    # Create agent with multiple hooks using helper
    agent = CounterAgent(StateHook("counter", 0))
    copilot = create_copilot_agent(
        agent,
        initial_state={
            "counter": 0,
            "todos": [],
            "settings": {"theme": "light", "notifications": True},
        },
    )

    print("State hooks created:")
    for name, hook in copilot.hooks.items():
        print(f"  • {name}: {hook.get()}")

    print("\nUpdating counter hook:")
    counter_hook = copilot.get_hook("counter")
    if counter_hook:
        counter_hook.update(42)
        print(f"  Counter updated to: {counter_hook.get()}")

    print("\nUpdating settings hook:")
    settings_hook = copilot.get_hook("settings")
    if settings_hook:
        settings = settings_hook.get()
        settings["theme"] = "dark"
        settings_hook.update(settings)
        print(f"  Settings updated to: {settings_hook.get()}")


async def demo_frontend_sync():
    """Demonstrate bidirectional frontend sync."""
    print("\n\n" + "=" * 60)
    print("Frontend Sync Demo")
    print("=" * 60)
    print()

    counter_hook = StateHook("counter", initial_value=5)
    agent = CounterAgent(counter_hook)
    copilot = CopilotAgent(agent, hooks=[counter_hook])

    print(f"Initial counter: {counter_hook.get()}")
    print()

    # Agent updates (backend → frontend)
    print("1. Agent Update (backend → frontend):")
    message = Message(role="user", content="increment")
    async for event in copilot.stream_chat(message, "sync-demo"):
        if event.type == "state_delta":
            print(f"   StateDelta event: {event.delta}")
            print(f"   Frontend would apply this patch")

    print()

    # Simulate frontend update (frontend → backend)
    print("2. Frontend Update (frontend → backend):")
    print("   Frontend sends: {op: 'replace', path: '/hooks/counter', value: 100}")
    counter_hook.update(100)  # Simulate applying frontend patch
    print(f"   Backend state updated to: {counter_hook.get()}")

    print()

    # Verify sync
    print("3. Verify Sync:")
    message = Message(role="user", content="status")
    async for event in copilot.stream_chat(message, "sync-demo"):
        if event.type == "text_message_content":
            print(f"   {event.delta}", end="", flush=True)

    print("\n")


async def main():
    """Run all state sharing demos."""
    print("🔄 MiniCopilotKit - Shared State\n")

    await demo_counter_state()
    await demo_todo_state()
    await demo_multiple_hooks()
    await demo_frontend_sync()

    print("\n\n" + "=" * 60)
    print("Key Concepts:")
    print("=" * 60)
    print("""
1. **StateHook Class**:
   - Similar to useCopilotReadable/useCopilotAction
   - Bidirectional state sync
   - JSON Patch for efficient updates

2. **Hook Methods**:
   - get(): Read current value
   - update(value): Update state (agent → frontend)
   - get_delta_event(): Get StateDelta for transmission

3. **State Synchronization**:
   Agent → Frontend:
   - Agent calls hook.update()
   - StateDelta event emitted
   - Frontend applies JSON Patch

   Frontend → Agent:
   - Frontend sends StateDelta
   - Backend applies patch
   - Agent reads updated state

4. **Comparison**:
   CopilotKit:
   ```jsx
   const [count, setCount] = useCopilotReadable({
     key: "counter",
     value: 0
   });

   useCopilotAction({
     name: "increment",
     handler: () => setCount(count + 1)
   });
   ```

   MiniCopilotKit:
   ```python
   counter_hook = StateHook("counter", initial_value=0)
   counter_hook.update(counter_hook.get() + 1)
   ```

   Both: Bidirectional sync with AG-UI StateManager!

5. **Use Cases**:
   - Collaborative editing
   - Real-time dashboards
   - Shared whiteboards
   - Multi-user applications
   - Agent-frontend state consistency
""")


if __name__ == "__main__":
    asyncio.run(main())
