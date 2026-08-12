# AG-UI Standard State Management

> **🔄 Shared State**: These examples demonstrate bidirectional state synchronization between agents and frontends using JSON Patch (RFC 6902) via AG-UI StateDelta events.

## Overview

AG-UI Standard provides formal state management through:
- **StateManager**: Manages agent state with snapshot and delta tracking
- **StateDelta Events**: Efficient incremental updates using JSON Patch
- **StateSnapshot Events**: Complete state for initialization
- **Bidirectional Sync**: Agent ↔ Frontend state synchronization

---

## Quick Start

```bash
# Run basic counter example
python example_basic.py

# Run todo list example
python example_todo_list.py

# Run frontend sync example
python example_frontend_sync.py
```

---

## Core Concepts

### StateManager

Manages agent state and generates JSON Patch operations:

```python
from agenkit.protocols.agui import StateManager

# Initialize with state
manager = StateManager(initial_state={"count": 0, "items": []})

# Update state
manager.update("/count", 5)
manager.update("/items/0", "apple")

# Get delta event (JSON Patch)
delta_event = manager.get_delta_event()
# Returns: {"type": "state_delta", "delta": [{"op": "replace", "path": "/count", "value": 5}, ...]}

# Get full snapshot
snapshot_event = manager.get_snapshot_event()
# Returns: {"type": "state_snapshot", "snapshot": {"count": 5, "items": ["apple"]}}
```

### JSON Patch Operations

StateManager generates RFC 6902 compliant JSON Patch operations:

| Operation | Description | Example |
|-----------|-------------|---------|
| `add` | Add new value | `{"op": "add", "path": "/items/0", "value": "apple"}` |
| `remove` | Remove value | `{"op": "remove", "path": "/items/0"}` |
| `replace` | Replace value | `{"op": "replace", "path": "/count", "value": 5}` |

### AGUIAdapter Integration

The adapter automatically emits state events:

```python
from agenkit.protocols.agui import AGUIAdapter, StateManager

state_manager = StateManager(initial_state={"count": 0})

adapter = AGUIAdapter(
    agent,
    state_manager=state_manager,
    emit_state_snapshots=True,  # Emit initial snapshot
)

async for event in adapter.stream_events(message, thread_id):
    if event.type == "state_snapshot":
        # Initial state
        frontend_state = event.snapshot

    elif event.type == "state_delta":
        # Incremental update
        apply_patch(frontend_state, event.delta)
```

---

## Examples

### 1. Basic Counter (`example_basic.py`)

**Demonstrates:**
- Simple state updates (increment/decrement/reset)
- StateDelta event generation
- State tracking across messages

**Key Features:**
- Counter state: `{"count": 0, "last_action": null}`
- Commands: increment, decrement, reset, status
- Automatic delta emission after each action

**Run:**
```bash
python example_basic.py
```

**Expected Output:**
```
Test 1: Increment
------------------------------------------------------------
Event: state_snapshot
  Initial state: {'count': 0, 'last_action': None}
Event: text_message_start
Event: text_message_content
  Text: ✅ Incremented! Coun
Event: text_message_content
  Text: t is now: 1
Event: text_message_end
Event: state_delta
  State delta: [{'op': 'replace', 'path': '/count', 'value': 1}]
Event: run_finished
```

### 2. Todo List (`example_todo_list.py`)

**Demonstrates:**
- Nested state structures
- Array operations
- Multiple concurrent state updates
- Complex state queries

**Key Features:**
- Todo state: `{"todos": [], "total_count": 0, "stats": {...}}`
- Commands: add, complete, delete, list, stats
- Nested updates: `/todos/0/completed`, `/stats/pending`

**Run:**
```bash
python example_todo_list.py
```

**State Structure:**
```json
{
  "todos": [
    {
      "id": 1,
      "title": "Write documentation",
      "completed": true,
      "created_at": "2026-01-27T12:00:00",
      "completed_at": "2026-01-27T12:05:00"
    }
  ],
  "total_count": 1,
  "stats": {
    "total": 1,
    "completed": 1,
    "pending": 0
  }
}
```

### 3. Frontend Synchronization (`example_frontend_sync.py`)

**Demonstrates:**
- Bidirectional state sync (agent ↔ frontend)
- Applying patches from frontend
- Real-world chat application state
- Conflict resolution patterns

**Key Features:**
- Conversation metadata: message count, timestamps
- User preferences: theme, notifications
- Frontend-initiated state changes
- State acknowledgment flow

**Run:**
```bash
python example_frontend_sync.py
```

**Bidirectional Flow:**
```
Frontend → Agent:
  [{"op": "replace", "path": "/user/preferences/theme", "value": "dark"}]

Agent → Frontend:
  [{"op": "replace", "path": "/conversation/message_count", "value": 5}]
```

---

## State Management Patterns

### Pattern 1: Simple Key-Value State

Best for: Counters, flags, simple settings

```python
state_manager = StateManager({"count": 0, "enabled": True})

# Update
state_manager.update("/count", 5)
state_manager.update("/enabled", False)

# Remove
state_manager.remove("/temp_data")
```

### Pattern 2: Nested Structures

Best for: User profiles, complex settings

```python
state_manager = StateManager(
    {"user": {"profile": {"name": "Alice", "age": 30}, "settings": {"theme": "dark"}}}
)

# Update nested
state_manager.update("/user/profile/name", "Bob")
state_manager.update("/user/settings/theme", "light")
```

### Pattern 3: Array Operations

Best for: Lists, collections, histories

```python
state_manager = StateManager({"items": []})

# Add to array (use index)
state_manager.update("/items/0", "apple")
state_manager.update("/items/1", "banana")

# Remove from array
state_manager.remove("/items/0")
```

### Pattern 4: Bidirectional Sync

Best for: Real-time collaboration, user preferences

```python
# Agent updates state
agent.state_manager.update("/preferences/theme", "dark")

# Frontend sends changes
frontend_patch = [{"op": "replace", "path": "/preferences/language", "value": "es"}]
agent.state_manager.apply_patch(frontend_patch)

# Both sides stay synchronized
```

---

## Frontend Integration

### JavaScript/TypeScript

Apply JSON Patch on the frontend:

```typescript
interface AppState {
  count: number;
  items: string[];
}

let state: AppState = { count: 0, items: [] };

// Apply patch from AG-UI StateDelta event
function applyPatch(state: AppState, operations: any[]): AppState {
  const newState = { ...state };

  for (const op of operations) {
    const { op: operation, path, value } = op;
    const keys = path.slice(1).split('/');

    if (operation === 'replace' || operation === 'add') {
      let current: any = newState;
      for (let i = 0; i < keys.length - 1; i++) {
        current = current[keys[i]];
      }
      current[keys[keys.length - 1]] = value;
    } else if (operation === 'remove') {
      let current: any = newState;
      for (let i = 0; i < keys.length - 1; i++) {
        current = current[keys[i]];
      }
      delete current[keys[keys.length - 1]];
    }
  }

  return newState;
}

// Listen for state events
eventSource.addEventListener('state_delta', (event) => {
  const data = JSON.parse(event.data);
  state = applyPatch(state, data.delta);
  updateUI(state);
});
```

### Using fast-json-patch Library

For production, use a JSON Patch library:

```typescript
import { applyPatch } from 'fast-json-patch';

let state = { count: 0 };

eventSource.addEventListener('state_delta', (event) => {
  const { delta } = JSON.parse(event.data);
  state = applyPatch(state, delta).newDocument;
  updateUI(state);
});
```

---

## Testing State Management

### Unit Tests

```python
import pytest
from agenkit.protocols.agui import StateManager


def test_state_updates():
    manager = StateManager({"count": 0})

    manager.update("/count", 5)
    delta = manager.get_delta_event()

    assert delta is not None
    assert len(delta.delta) == 1
    assert delta.delta[0]["op"] == "replace"
    assert delta.delta[0]["path"] == "/count"
    assert delta.delta[0]["value"] == 5


def test_no_change_no_delta():
    manager = StateManager({"count": 5})

    manager.update("/count", 5)  # Same value
    delta = manager.get_delta_event()

    assert delta is None  # No change
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_state_in_streaming():
    state_manager = StateManager({"count": 0})
    agent = CounterAgent(state_manager)
    adapter = AGUIAdapter(agent, state_manager=state_manager)

    events = []
    async for event in adapter.stream_events(
        Message(role="user", content="increment"), thread_id="test"
    ):
        events.append(event)

    # Verify StateDelta was emitted
    state_deltas = [e for e in events if e.type == "state_delta"]
    assert len(state_deltas) == 1
    assert state_deltas[0].delta[0]["value"] == 1
```

---

## Performance Considerations

### Delta vs Snapshot

**Use StateDelta (preferred):**
- ✅ Small incremental changes
- ✅ Frequent updates
- ✅ Network efficiency
- ✅ Minimal frontend rerender

**Use StateSnapshot:**
- Initial load
- After reconnection
- Periodic full sync
- State reset/initialization

### Example: Choosing the Right Event

```python
# Good: Delta for small change
state_manager.update("/count", count + 1)  # ~50 bytes
delta = state_manager.get_delta_event()

# Bad: Snapshot for small change
snapshot = state_manager.get_snapshot_event()  # Could be KB+

# Good: Snapshot for initialization
if is_first_connection:
    yield state_manager.get_snapshot_event()

# Good: Delta for ongoing updates
else:
    delta = state_manager.get_delta_event()
    if delta:
        yield delta
```

---

## Best Practices

### 1. Initialize State Early

```python
# Good: Set initial state upfront
state_manager = StateManager(
    initial_state={"count": 0, "items": [], "settings": {"theme": "light"}}
)

# Bad: Add fields incrementally (creates many operations)
state_manager = StateManager({})
state_manager.update("/count", 0)
state_manager.update("/items", [])
```

### 2. Batch Related Updates

```python
# Good: Update related fields together
state_manager.update("/user/name", "Alice")
state_manager.update("/user/age", 30)
state_manager.update("/user/active", True)
delta = state_manager.get_delta_event()  # Single event with 3 operations

# Bad: Get delta after each update
state_manager.update("/user/name", "Alice")
yield state_manager.get_delta_event()  # 1 operation
state_manager.update("/user/age", 30)
yield state_manager.get_delta_event()  # 1 operation
```

### 3. Use Meaningful Paths

```python
# Good: Clear, semantic paths
"/conversation/message_count"

"/user/preferences/theme"
"/todos/0/completed"

# Bad: Unclear paths
"/c"
"/data/0/1"
"/temp"
```

### 4. Handle State Conflicts

```python
# Good: Check before applying frontend changes
def apply_frontend_changes(self, operations):
    for op in operations:
        # Validate operation
        if self._is_valid_operation(op):
            self.state_manager.apply_patch([op])
        else:
            # Reject invalid change
            yield StateSnapshotEvent(snapshot=self.state_manager.get_state())
```

---

## Troubleshooting

**Issue**: No StateDelta events emitted
**Solution**: Ensure state actually changed (same value = no delta)

**Issue**: Patch application fails on frontend
**Solution**: Verify path exists before replace/remove operations

**Issue**: State out of sync
**Solution**: Send StateSnapshot periodically for reconciliation

**Issue**: Large state causing performance issues
**Solution**: Split into multiple state managers or use nested structures

---

## Resources

### Specifications
- **JSON Patch RFC 6902**: https://tools.ietf.org/html/rfc6902
- **JSON Pointer RFC 6901**: https://tools.ietf.org/html/rfc6901
- **AG-UI Standard**: https://docs.ag-ui.com/

### Libraries
- **Python**: `jsonpatch` (if needed for complex operations)
- **JavaScript**: `fast-json-patch`, `json-patch`
- **TypeScript**: `fast-json-patch` (type-safe)

### Related Examples
- **AG-UI Simple**: `examples/agui_simple/` (simpler protocol without formal state)
- **CopilotKit**: `examples/integrations/copilotkit/` (production example)
- **Custom Frontends**: `examples/integrations/custom-frontends/` (state rendering)

---

## Next Steps

1. **Run Examples**: Start with `example_basic.py` to understand fundamentals
2. **Build Frontend**: Integrate state management into your custom frontend
3. **Test Thoroughly**: Write unit and integration tests for state logic
4. **Monitor Performance**: Track state delta sizes and update frequency
5. **Add Conflict Resolution**: Handle concurrent updates from multiple sources

---

**Built with ❤️ using Agenkit AG-UI Standard**
