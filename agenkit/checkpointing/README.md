# Checkpointing & Durable Execution

> **Status**: Production Ready
> **Python**: ✅ | **Go**: 🚧 Planned Q1 2026

## Overview

The Agenkit Checkpointing System enables durable execution for long-running autonomous agents (30+ hours), providing state persistence, crash recovery, and time-travel debugging capabilities.

## Why Checkpointing?

**Problem**: Claude Sonnet 4.5 can run autonomously for 30+ hours, but:
- Crashes lose all progress
- No way to resume from failure
- Debugging 30-hour runs is impossible
- State must survive restarts

**Solution**: Automatic checkpointing with resume capability.

## Quick Start

```python
from agenkit.checkpointing import DurableAgent

# Make any agent durable
durable = DurableAgent(
    agent=my_agent,
    checkpoint_dir="./checkpoints",
    checkpoint_interval=10  # Checkpoint every 10 steps
)

# Use normally (auto-checkpoints in background)
response = await durable.process(message, session_id="session-1")

# Resume after crash
state = await durable.resume("session-1")
print(f"Resumed at step {state['step']}")
```

## Components

### 1. Checkpoint
Immutable snapshot of agent state:
```python
@dataclass
class Checkpoint:
    checkpoint_id: str       # Unique ID
    session_id: str          # Session identifier
    step: int                # Step number
    timestamp: datetime      # When created
    state: dict              # Agent state
    metadata: dict           # Additional info
    previous_id: Optional[str]  # Previous checkpoint (for time-travel)
```

### 2. CheckpointStorage
Abstract storage interface with multiple backends:

**InMemoryCheckpointStorage**: Testing and prototyping
```python
storage = InMemoryCheckpointStorage()
```

**FileCheckpointStorage**: Production (JSON files)
```python
storage = FileCheckpointStorage(checkpoint_dir="./checkpoints")
```

**Custom**: Implement `CheckpointStorage` interface for Redis, S3, Postgres, etc.

### 3. CheckpointManager
High-level checkpoint management:
```python
manager = CheckpointManager(
    storage=storage,
    max_checkpoints_per_session=100,
    auto_prune=True
)

# Create checkpoint
checkpoint = await manager.create_checkpoint(
    session_id="session-1",
    state={"step": 42, "data": "..."},
    metadata={"agent": "research-agent"}
)

# Restore state
state = await manager.restore_state("session-1")
state = await manager.restore_state("session-1", step=10)  # Time-travel

# List checkpoints
checkpoints = await manager.list_checkpoints("session-1")

# Prune old checkpoints
await manager.prune_old_checkpoints("session-1", keep=10)
```

### 4. DurableAgent
Agent wrapper with automatic checkpointing:
```python
durable = DurableAgent(
    agent=base_agent,
    checkpoint_dir="./checkpoints",
    checkpoint_interval=10,      # Checkpoint every N steps
    auto_resume=True,            # Auto-resume on restart
    max_checkpoints=100          # Keep last N checkpoints
)

# Use like normal agent
response = await durable.process(message, session_id="session-1")

# Resume after crash
state = await durable.resume("session-1")

# Get checkpoint stats
stats = await durable.get_session_stats("session-1")
# {"current_step": 42, "message_count": 84, "checkpoints": 5}
```

## Features

### Automatic Checkpointing
```python
durable = DurableAgent(
    agent=agent,
    checkpoint_dir="./checkpoints",
    checkpoint_interval=10  # Every 10 steps
)

# Checkpoints created automatically
for i in range(100):
    await durable.process(message, session_id="session-1")
# Creates checkpoints at steps: 10, 20, 30, ..., 100
```

### Crash Recovery
```python
# Before crash
durable = DurableAgent(agent, checkpoint_dir="./checkpoints")
for i in range(50):
    await durable.process(message, session_id="session-1")
# CRASH at step 37

# After restart
durable = DurableAgent(agent, checkpoint_dir="./checkpoints")
state = await durable.resume("session-1")
# Resumes from step 30 (last checkpoint)
```

### Time-Travel Debugging
```python
# Go back to any checkpoint
state_now = await manager.restore_state("session-1")  # Latest
state_past = await manager.restore_state("session-1", step=10)  # Step 10

# Compare states
print(f"Now: {state_now}")
print(f"Then: {state_past}")

# Replay from checkpoint
durable = DurableAgent(agent, checkpoint_dir="./checkpoints")
await durable.resume("session-1", from_step=10)
# Replays from step 10 forward
```

### Checkpoint History
```python
# Get all checkpoints for session
checkpoints = await manager.list_checkpoints("session-1")

for cp in checkpoints:
    print(f"Step {cp.step}: {cp.checkpoint_id} at {cp.timestamp}")
    print(f"  State: {cp.state}")
    print(f"  Previous: {cp.previous_id}")
```

### Pruning Old Checkpoints
```python
# Automatic pruning
durable = DurableAgent(
    agent=agent,
    checkpoint_dir="./checkpoints",
    max_checkpoints=10  # Keep only last 10
)

# Manual pruning
await manager.prune_old_checkpoints("session-1", keep=5)

# Delete all checkpoints for session
await manager.delete_session("session-1")
```

## Real-World Scenarios

### Scenario 1: 30-Hour Research Agent

```python
from agenkit.checkpointing import DurableAgent
from agenkit.memory import RedisMemory
from agenkit.budget import CostTracker, BudgetLimiter

# Create durable research agent
memory = RedisMemory(redis_url="redis://localhost:6379")
tracker = CostTracker()

agent = ResearchAgent(memory=memory)
agent = BudgetLimiter(tracker, session_budget=100.00)(agent)
agent = DurableAgent(
    agent,
    checkpoint_dir="./research_checkpoints",
    checkpoint_interval=50,  # Every 50 research steps
    max_checkpoints=100
)

# Run for 30 hours
session_id = "research-2025-11-14"
for i in range(1000):
    try:
        response = await agent.process(
            Message(role="user", content=f"Research task {i}"),
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"Crash at step {i}: {e}")
        # Resume from last checkpoint
        await agent.resume(session_id)
        continue
```

### Scenario 2: Multi-Agent Coordination

```python
# Each agent has independent checkpoints
agents = {
    "researcher": DurableAgent(researcher, checkpoint_dir="./checkpoints/researcher"),
    "writer": DurableAgent(writer, checkpoint_dir="./checkpoints/writer"),
    "reviewer": DurableAgent(reviewer, checkpoint_dir="./checkpoints/reviewer")
}

session_id = "project-123"

# All agents checkpoint independently
for step in range(100):
    research = await agents["researcher"].process(msg, session_id=session_id)
    draft = await agents["writer"].process(research, session_id=session_id)
    review = await agents["reviewer"].process(draft, session_id=session_id)

# Resume all agents from their checkpoints
for name, agent in agents.items():
    state = await agent.resume(session_id)
    print(f"{name} resumed at step {state['step']}")
```

### Scenario 3: A/B Testing with Time-Travel

```python
# Run experiment to step 50
durable = DurableAgent(agent, checkpoint_dir="./exp_checkpoints")
for i in range(50):
    await durable.process(message, session_id="experiment-A")

# Fork from step 30 for comparison
state_30 = await manager.restore_state("experiment-A", step=30)

# Try alternative approach from step 30
durable_fork = DurableAgent(agent, checkpoint_dir="./exp_checkpoints_fork")
await durable_fork.load_state(state_30, session_id="experiment-B")

for i in range(30, 50):
    await durable_fork.process(message_alt, session_id="experiment-B")

# Compare outcomes
stats_a = await durable.get_session_stats("experiment-A")
stats_b = await durable_fork.get_session_stats("experiment-B")
```

## Storage Backends

### File Storage (Default)
```python
storage = FileCheckpointStorage(checkpoint_dir="./checkpoints")
# Creates: ./checkpoints/session-1/checkpoint-00001.json
```

**Pros**:
- Simple, no dependencies
- Human-readable (JSON)
- Works everywhere

**Cons**:
- Not suitable for very high frequency (>100/sec)
- No atomic operations across sessions

### In-Memory (Testing)
```python
storage = InMemoryCheckpointStorage()
```

**Pros**:
- Fastest
- No I/O

**Cons**:
- Lost on restart
- Memory limited

### Custom (Redis, S3, Postgres)
```python
class RedisCheckpointStorage(CheckpointStorage):
    async def save(self, checkpoint: Checkpoint) -> None:
        await self.redis.set(
            f"checkpoint:{checkpoint.session_id}:{checkpoint.step}",
            checkpoint.to_json()
        )

    async def load(self, session_id: str, step: int) -> Optional[Checkpoint]:
        data = await self.redis.get(f"checkpoint:{session_id}:{step}")
        return Checkpoint.from_json(data) if data else None
```

## Best Practices

### 1. Checkpoint Frequency
```python
# Too frequent: Storage overhead
checkpoint_interval=1  # Every step (expensive)

# Too infrequent: Lost work on crash
checkpoint_interval=1000  # Every 1000 steps (risky)

# Balanced
checkpoint_interval=10-50  # Every 10-50 steps ✅
```

### 2. State Management
```python
# ✅ Good: Include all necessary state
state = {
    "step": 42,
    "conversation_history": messages,
    "tool_results": results,
    "metadata": {...}
}

# ❌ Bad: Missing critical state
state = {"step": 42}  # Where's the conversation?
```

### 3. Checkpoint Pruning
```python
# ✅ Good: Keep reasonable number
max_checkpoints=50-100

# ❌ Bad: Keep everything (storage explosion)
max_checkpoints=None

# ❌ Bad: Keep too few (no recovery options)
max_checkpoints=1
```

### 4. Error Handling
```python
# ✅ Good: Explicit recovery
try:
    response = await durable.process(message, session_id=sid)
except Exception as e:
    logger.error(f"Error: {e}")
    state = await durable.resume(sid)  # Explicit resume
    # Retry or handle error

# ❌ Bad: Silent failures
try:
    response = await durable.process(message, session_id=sid)
except:
    pass  # Lost state!
```

### 5. Session Isolation
```python
# ✅ Good: One session per user/task
session_id = f"user-{user_id}-{task_id}"

# ❌ Bad: Shared session
session_id = "global"  # Everyone's state mixed together
```

## Performance

### Checkpoint Overhead

| Storage | Save (1KB state) | Load | List |
|---------|------------------|------|------|
| InMemory | < 0.1ms | < 0.1ms | < 1ms |
| File | 1-5ms | 1-5ms | 5-10ms |
| Redis | 2-10ms | 2-10ms | 10-20ms |

### Recommendations
- **Development**: InMemory
- **Production (single instance)**: File
- **Production (multi-instance)**: Redis or S3
- **Analytics**: Postgres

## Testing

```bash
# Run tests (18 tests)
uv run pytest tests/checkpointing/ -v

# Run example
python examples/checkpointing/durable_agent_demo.py
```

## API Reference

### DurableAgent

```python
durable = DurableAgent(
    agent: Agent,                    # Base agent to wrap
    checkpoint_dir: str = "./checkpoints",
    checkpoint_interval: int = 10,   # Steps between checkpoints
    auto_resume: bool = True,        # Auto-resume on init
    max_checkpoints: int = 100       # Max checkpoints per session
)

# Methods
await durable.process(message, session_id)      # Normal usage
await durable.resume(session_id, from_step=None) # Resume from checkpoint
await durable.get_session_stats(session_id)     # Get stats
await durable.clear_checkpoints(session_id)     # Delete all checkpoints
```

### CheckpointManager

```python
manager = CheckpointManager(
    storage: CheckpointStorage,
    max_checkpoints_per_session: int = 100,
    auto_prune: bool = True
)

# Methods
await manager.create_checkpoint(session_id, state, metadata)
await manager.restore_state(session_id, step=None)
await manager.list_checkpoints(session_id)
await manager.get_latest(session_id)
await manager.delete_checkpoint(checkpoint_id)
await manager.delete_session(session_id)
await manager.prune_old_checkpoints(session_id, keep=10)
```

## Related

- [Memory Systems](../memory/) - Persistent conversation history
- [Cost Tracking](../budget/) - Budget management for long runs
- [Agent Safety](../safety/) - Security for autonomous agents

## Contributing

Want to add a storage backend? Implement `CheckpointStorage`:

```python
class MyStorage(CheckpointStorage):
    async def save(self, checkpoint: Checkpoint) -> None:
        # Your implementation
        pass

    async def load(self, session_id: str, step: int) -> Optional[Checkpoint]:
        # Your implementation
        pass
```
