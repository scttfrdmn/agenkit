# MiniCopilotKit - CopilotKit Patterns on Agenkit

> **🎯 Framework Reimagination**: This example demonstrates how to implement CopilotKit-like patterns using Agenkit's AG-UI Standard protocol, showing that CopilotKit's features are built on the same primitives that Agenkit provides.

## Overview

**MiniCopilotKit** is NOT an integration with CopilotKit. Instead, it's a framework example showing how CopilotKit's key patterns can be reimplemented using Agenkit's core abstractions.

**Key Insight**: CopilotKit and Agenkit both build on AG-UI Standard. MiniCopilotKit demonstrates that you can achieve CopilotKit-like functionality using Agenkit's primitives directly.

---

## Quick Start

```bash
# Run streaming chat example
python example_chat_ui.py

# Run tool visualization example
python example_tools_ui.py

# Run state sharing example
python example_state_sharing.py
```

---

## Core Concepts

### What is CopilotKit?

[CopilotKit](https://copilotkit.ai/) is an open-source React framework for building AI copilots. It provides:
- `<CopilotChat>` - Streaming chat UI component
- `useCopilotReadable` / `useCopilotAction` - State management hooks
- Tool visualization - Automatic UI for tool calls
- HITL approvals - Confirmation dialogs

**Under the hood**: CopilotKit uses the AG-UI Standard protocol for agent communication.

### What is MiniCopilotKit?

MiniCopilotKit reimplements CopilotKit's core patterns using **pure Agenkit primitives**:
- `ChatUI` - Streaming chat (like `<CopilotChat>`)
- `StateHook` - Shared state (like `useCopilotReadable`/`useCopilotAction`)
- `ToolCard` - Tool visualization (like CopilotKit's tool cards)
- `ApprovalDialog` - HITL confirmations (like `useConfirmation`)

**The Point**: Shows that CopilotKit's features are accessible through Agenkit's AG-UI Standard.

---

## Architecture Comparison

### CopilotKit Architecture

```
┌─────────────────────────────────────────┐
│           React Frontend                │
│  ┌────────────────────────────────────┐ │
│  │ <CopilotChat>                      │ │
│  │ useCopilotReadable                 │ │
│  │ useCopilotAction                   │ │
│  └────────────────────────────────────┘ │
└──────────────┬──────────────────────────┘
               │ AG-UI Standard (SSE/WS)
┌──────────────┴──────────────────────────┐
│       CopilotKit Runtime Server         │
│  (Your agent integrated via adapter)    │
└─────────────────────────────────────────┘
```

### MiniCopilotKit Architecture

```
┌─────────────────────────────────────────┐
│        Python/React Frontend            │
│  ┌────────────────────────────────────┐ │
│  │ ChatUI                             │ │
│  │ StateHook                          │ │
│  │ ToolCard                           │ │
│  └────────────────────────────────────┘ │
└──────────────┬──────────────────────────┘
               │ AG-UI Standard Events
┌──────────────┴──────────────────────────┐
│          Agenkit Agent                   │
│  ┌────────────────────────────────────┐ │
│  │ AGUIAdapter                        │ │
│  │ StateManager                       │ │
│  │ ToolCallTracker                    │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Same Protocol**: Both use AG-UI Standard events for communication!

---

## Feature Comparison

| Feature | CopilotKit | MiniCopilotKit | AG-UI Event |
|---------|------------|----------------|-------------|
| **Streaming Chat** | `<CopilotChat>` | `ChatUI` | `text_message_content` |
| **State Hooks** | `useCopilotReadable` | `StateHook` | `state_delta` |
| **Actions** | `useCopilotAction` | `StateHook.update()` | `state_delta` |
| **Tool UI** | Auto tool cards | `ToolCard` | `tool_call_*` events |
| **Progress** | Built-in bars | `ToolCard.progress` | `tool_call_progress` |
| **Approvals** | `useConfirmation` | `ApprovalDialog` | Custom events |

**Key Takeaway**: Same underlying protocol, different API styles.

---

## Examples

### 1. Streaming Chat (`example_chat_ui.py`)

**Demonstrates**: Basic chat interface with streaming responses

**CopilotKit Version**:
```jsx
import { CopilotChat } from "@copilotkit/react-ui";

function App() {
  return (
    <CopilotChat
      runtimeUrl="/api/copilotkit"
      labels={{
        title: "Assistant",
        initial: "How can I help?"
      }}
    />
  );
}
```

**MiniCopilotKit Version**:
```python
from minicopilotkit import ChatUI, CopilotAgent

agent = AssistantAgent()
copilot = CopilotAgent(agent)
ui = ChatUI(copilot)

response = await ui.send_message("Hello!")
print(ui.display_chat())
```

**What it Shows**:
- Streaming text chunks (`text_message_content` events)
- Message history management
- Real-time UI updates
- Same streaming protocol, different interfaces

---

### 2. Tool Visualization (`example_tools_ui.py`)

**Demonstrates**: Tool call tracking with progress bars

**CopilotKit Version**:
```jsx
// Automatic tool card rendering
// CopilotKit shows tools in UI automatically
```

**MiniCopilotKit Version**:
```python
from minicopilotkit import CopilotAgent, ToolCard

copilot = CopilotAgent(agent, tools=[SearchTool(), CalculatorTool()])

async for event in copilot.stream_chat(message):
    if event.type == "tool_call_start":
        print(f"🔧 Tool: {event.tool_call_name}")
    elif event.type == "tool_call_progress":
        print(f"Progress: {event.progress * 100:.0f}%")
    elif event.type == "tool_call_result":
        print(f"✅ Result: {event.content}")

# Get tool cards for UI rendering
cards = copilot.get_active_tools()
```

**What it Shows**:
- Tool execution tracking
- Progress updates (`tool_call_progress` events)
- Results display
- State: pending → executing → completed

**Tool Card Data Structure**:
```python
{
    "tool_name": "search",
    "tool_call_id": "tool-abc123",
    "status": "executing",
    "progress": 0.6,
    "args": {"query": "AI agents"},
    "result": None,
}
```

---

### 3. State Sharing (`example_state_sharing.py`)

**Demonstrates**: Bidirectional state synchronization

**CopilotKit Version**:
```jsx
import { useCopilotReadable, useCopilotAction } from "@copilotkit/react-core";

function Counter() {
  const [count, setCount] = useCopilotReadable({
    key: "counter",
    value: 0
  });

  useCopilotAction({
    name: "increment",
    handler: () => setCount(count + 1)
  });

  return <div>Count: {count}</div>;
}
```

**MiniCopilotKit Version**:
```python
from minicopilotkit import StateHook, CopilotAgent

counter_hook = StateHook("counter", initial_value=0)


class CounterAgent(Agent):
    def __init__(self, counter_hook):
        self.counter_hook = counter_hook

    async def process(self, message):
        if "increment" in message.content:
            current = self.counter_hook.get()
            self.counter_hook.update(current + 1)
        return Message(role="assistant", content="Incremented!")


copilot = CopilotAgent(agent, hooks=[counter_hook])
```

**What it Shows**:
- Agent → Frontend: `hook.update()` emits `state_delta`
- Frontend → Agent: Frontend sends `state_delta`, agent applies
- JSON Patch for efficient updates
- Real-time state synchronization

**State Flow**:
```
Agent Updates:
1. hook.update(new_value)
2. StateManager generates JSON Patch
3. StateDelta event emitted
4. Frontend applies patch

Frontend Updates:
1. User modifies state
2. Frontend sends StateDelta event
3. Agent applies patch
4. Agent reads updated state via hook.get()
```

---

## Implementation Details

### CopilotAgent Class

Wraps any Agenkit agent with CopilotKit-style features:

```python
class CopilotAgent:
    def __init__(self, base_agent, tools=None, hooks=None):
        self.base_agent = base_agent
        self.tools = tools or []
        self.hooks = {hook.name: hook for hook in (hooks or [])}

        # Create state manager for hooks
        hook_states = {hook.name: hook.initial_value for hook in (hooks or [])}
        self.state_manager = StateManager(initial_state={"hooks": hook_states})

        # Create AG-UI adapter
        self.adapter = AGUIAdapter(
            base_agent, state_manager=self.state_manager, emit_state_snapshots=True
        )
```

**Key Components**:
- `AGUIAdapter` - Converts agent responses to AG-UI events
- `StateManager` - Manages state with JSON Patch
- `ToolCallTracker` - Tracks tool execution
- `active_tools` - Dictionary of active ToolCards

### StateHook Class

Bidirectional state management:

```python
@dataclass
class StateHook:
    name: str
    initial_value: Any
    _state_manager: Optional[StateManager] = None

    def get(self) -> Any:
        """Get current value."""
        state = self._state_manager.get_state()
        return state.get("hooks", {}).get(self.name)

    def update(self, value: Any) -> None:
        """Update value (generates StateDelta)."""
        self._state_manager.update(f"/hooks/{self.name}", value)

    def get_delta_event(self):
        """Get StateDelta event for frontend."""
        return self._state_manager.get_delta_event()
```

**Behind the Scenes**:
- Uses AG-UI `StateManager` for state tracking
- Generates JSON Patch operations (RFC 6902)
- Emits `StateDelta` events automatically

### ToolCard Class

Tool execution visualization:

```python
@dataclass
class ToolCard:
    tool_name: str
    tool_call_id: str
    status: str = "pending"  # pending, executing, completed, failed
    progress: float = 0.0  # 0.0 to 1.0
    args: Optional[dict] = None
    result: Optional[Any] = None

    def to_dict(self) -> dict:
        """Convert to dict for frontend rendering."""
        return {
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "status": self.status,
            "progress": self.progress,
            "args": self.args,
            "result": self.result,
        }
```

**Updated by Events**:
- `tool_call_start` → Create card, status = "executing"
- `tool_call_progress` → Update progress field
- `tool_call_result` → Set result, status = "completed"

---

## Frontend Integration

### React Example

```jsx
import { useState, useEffect } from 'react';

function MiniCopilotKitUI() {
  const [messages, setMessages] = useState([]);
  const [state, setState] = useState({});
  const [toolCards, setToolCards] = useState({});

  useEffect(() => {
    const eventSource = new EventSource('/agui');

    // Text streaming
    eventSource.addEventListener('text_message_content', (e) => {
      const data = JSON.parse(e.data);
      // Append to current message
    });

    // State updates
    eventSource.addEventListener('state_delta', (e) => {
      const { delta } = JSON.parse(e.data);
      setState(prev => applyPatch(prev, delta));
    });

    // Tool visualization
    eventSource.addEventListener('tool_call_start', (e) => {
      const { tool_call_id, tool_call_name } = JSON.parse(e.data);
      setToolCards(prev => ({
        ...prev,
        [tool_call_id]: { name: tool_call_name, status: 'executing', progress: 0 }
      }));
    });

    eventSource.addEventListener('tool_call_progress', (e) => {
      const { tool_call_id, progress } = JSON.parse(e.data);
      setToolCards(prev => ({
        ...prev,
        [tool_call_id]: { ...prev[tool_call_id], progress }
      }));
    });

    return () => eventSource.close();
  }, []);

  return (
    <div>
      <ChatMessages messages={messages} />
      <ToolCards cards={Object.values(toolCards)} />
      <StateDisplay state={state} />
    </div>
  );
}
```

---

## Key Differences

### What MiniCopilotKit Does NOT Include

1. **No React Components** - Pure Python/AG-UI, not React-specific
2. **No Runtime Server** - Direct agent integration, no separate server
3. **No Built-in UI** - Provides data structures, not rendered components
4. **No LangChain/LangGraph** - Pure Agenkit agents

### What MiniCopilotKit DOES Include

1. **Same Protocol** - AG-UI Standard events
2. **Same Patterns** - Streaming, state, tools, approvals
3. **Same Capabilities** - All CopilotKit features achievable
4. **Simpler Stack** - Fewer layers, direct primitives

---

## When to Use What

### Use CopilotKit When:
- Building React applications
- Want pre-built UI components
- Need production-ready React copilot
- Prefer declarative React APIs

### Use MiniCopilotKit Patterns When:
- Building non-React applications (Python, CLI, desktop)
- Want direct control over agent behavior
- Building custom frameworks on Agenkit
- Learning how copilot frameworks work

### Use Direct Agenkit When:
- Building custom agent patterns
- Need maximum flexibility
- Don't need copilot-specific features
- Integrating with existing systems

---

## Extending MiniCopilotKit

### Adding Custom Hooks

```python
# Create custom hook
class ThemeHook(StateHook):
    def set_theme(self, theme: str):
        """Set theme with validation."""
        if theme in ["light", "dark", "auto"]:
            self.update(theme)
        else:
            raise ValueError(f"Invalid theme: {theme}")


# Use in agent
theme_hook = ThemeHook("theme", initial_value="light")
copilot = CopilotAgent(agent, hooks=[theme_hook])
```

### Adding Custom Tool Cards

```python
# Create custom tool card
class DatabaseToolCard(ToolCard):
    def __init__(self, *args, query: str = None, rows_affected: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.query = query
        self.rows_affected = rows_affected

    def to_dict(self):
        data = super().to_dict()
        data.update({"query": self.query, "rows_affected": self.rows_affected})
        return data
```

---

## Performance Considerations

### State Updates

- **CopilotKit**: React re-renders on state changes
- **MiniCopilotKit**: JSON Patch for minimal updates
- **Both**: Efficient incremental synchronization

### Tool Visualization

- **CopilotKit**: Automatic React component rendering
- **MiniCopilotKit**: Data structures for manual rendering
- **Both**: Real-time progress tracking

### Streaming

- **CopilotKit**: SSE with React state updates
- **MiniCopilotKit**: AG-UI events with custom handling
- **Both**: Same underlying event stream

---

## FAQ

**Q: Is this a replacement for CopilotKit?**
A: No. MiniCopilotKit demonstrates patterns, not a production framework.

**Q: Can I use CopilotKit with Agenkit?**
A: Yes! Agenkit's `AGUIAdapter` is compatible with CopilotKit. This example just shows you don't *need* CopilotKit to achieve similar functionality.

**Q: Why build this?**
A: To demonstrate that CopilotKit's features are accessible through Agenkit's core primitives, showing Agenkit as a toolkit rather than requiring specific frameworks.

**Q: Should I use this in production?**
A: Use CopilotKit for production React apps. Use these patterns as inspiration for custom implementations.

**Q: What about LangChain/LangGraph?**
A: MiniCopilotKit uses pure Agenkit agents. For LangChain, see the MiniLangChain example.

---

## Resources

### Documentation
- **AG-UI Standard**: Complete protocol specification
- **Agenkit State Management**: `examples/agui-standard/state-management/`
- **Tool Streaming**: `examples/agui-standard/tool-streaming/`

### Related Examples
- **MiniPydantic**: `examples/frameworks/minipydantic/`
- **Custom Frontends**: `examples/integrations/custom-frontends/`
- **CopilotKit (official)**: https://copilotkit.ai/

---

## Next Steps

1. **Run Examples**: Try all three examples to see patterns in action
2. **Build Custom Agent**: Create agent with hooks and tools
3. **Frontend Integration**: Connect to React/Vue/Svelte frontend
4. **Extend Patterns**: Add custom hooks and tool cards
5. **Compare with CopilotKit**: See how patterns translate

---

**Built with ❤️ using Agenkit primitives**

*Demonstrating that framework features emerge from composable primitives.*
