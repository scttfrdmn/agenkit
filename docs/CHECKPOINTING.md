# Agenkit Checkpointing Guide

Comprehensive guide to durable agent execution with automatic state persistence across all languages.

## Table of Contents

- [Overview](#overview)
- [Core Concepts](#core-concepts)
- [Architecture](#architecture)
- [Storage Backends](#storage-backends)
- [Quick Start](#quick-start)
- [Usage Patterns](#usage-patterns)
- [API Reference](#api-reference)
- [Language-Specific Examples](#language-specific-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Performance Considerations](#performance-considerations)

---

## Overview

Checkpointing enables long-running agents to persist their state at key points, allowing them to:
- **Resume** after crashes or restarts
- **Replay** from specific execution points
- **Debug** with time-travel capabilities
- **Audit** execution history for compliance
- **Optimize** by skipping completed work

### Why Checkpointing Matters

1. **Reliability** - Agents survive crashes and network failures
2. **Cost Efficiency** - Don't re-run expensive LLM calls after failures
3. **Auditability** - Complete execution history for compliance
4. **Debugging** - Inspect and replay from any checkpoint
5. **Scalability** - Migrate long-running agents between servers

### Available in All Languages

- ✅ **Python** - Production-ready, SQLite + file storage
- ✅ **Go** - High-performance, concurrent-safe
- ✅ **TypeScript** - Node.js and Deno support
- ✅ **Rust** - Zero-cost abstractions, async/await
- ✅ **C++** - Modern C++17, header-only option
- ✅ **Zig** - Systems-level, manual memory management
- ✅ **C#** - `System.Text.Json` file storage, async/await (see [note below](#csharp-java-scala-checkpointing-baseline))
- ✅ **Java** - `Jackson` file storage + in-memory cache, `CompletableFuture` (see [note below](#csharp-java-scala-checkpointing-baseline))
- ✅ **Scala** - In-memory only, `Future`/`ExecutionContext` (see [note below](#csharp-java-scala-checkpointing-baseline))

---

## Core Concepts

### Checkpoint

A checkpoint captures complete agent state at a point in time:

```python
Checkpoint {
    checkpoint_id: str          # Unique identifier (UUID)
    session_id: str             # Session this checkpoint belongs to
    agent_name: str             # Agent that created it
    timestamp: int              # Unix timestamp (milliseconds)
    step_number: int            # Sequential step in session
    state: dict                 # Agent state (JSON-serializable)
    messages: list[Message]     # Conversation history
    metadata: dict              # Optional custom metadata
    parent_checkpoint_id: str?  # Previous checkpoint (for chains)
}
```

### Storage Backend

Abstraction for persisting checkpoints:

```python
class CheckpointStorage:
    def save(checkpoint: Checkpoint) -> None
    def load(checkpoint_id: str) -> Checkpoint?
    def list_checkpoints(session_id: str, limit: int) -> list[Checkpoint]
    def get_latest(session_id: str) -> Checkpoint?
    def delete(checkpoint_id: str) -> bool
    def delete_session(session_id: str) -> int
```

Implementations:
- **InMemoryStorage** - Fast, volatile (testing/dev)
- **FileStorage** - Persistent JSON files (production)
- **SQLiteStorage** - Structured queries (Python only)
- **RedisStorage** - Distributed, high-performance (Python/Go)

### Checkpoint Manager

High-level API for checkpoint operations:

```python
CheckpointManager {
    storage: CheckpointStorage
    auto_checkpoint_interval: int  # Checkpoint every N steps (0 = manual)
}
```

Features:
- Automatic checkpoint creation based on interval
- Session-based organization
- Checkpoint chain reconstruction (parent links)
- Retention policies and pruning
- Statistics and analytics

### Durable Agent

Decorator/wrapper that adds checkpointing to any agent:

```python
DurableAgent {
    agent: Agent                      # Wrapped agent
    manager: CheckpointManager        # Checkpoint manager
    auto_resume: bool                 # Resume from latest on start
}
```

Capabilities:
- Transparent checkpointing (no agent changes needed)
- Automatic state restoration on failure
- Progress resumption from last checkpoint
- Manual checkpoint control when needed

---

## Architecture

### Checkpoint Lifecycle

```
┌─────────────┐
│ Agent Start │
└──────┬──────┘
       │
       ▼
┌──────────────────┐     Yes    ┌──────────────────┐
│ Auto-resume?     │─────────────▶│ Load Latest CP   │
└──────┬───────────┘              └────────┬─────────┘
       │ No                                 │
       ▼                                    │
┌──────────────────┐◀───────────────────────┘
│ Process Message  │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐     Yes    ┌──────────────────┐
│ Should CP?       │─────────────▶│ Create CP        │
└──────┬───────────┘              └────────┬─────────┘
       │ No                                 │
       ▼                                    │
┌──────────────────┐◀───────────────────────┘
│ Return Result    │
└──────────────────┘
```

### Storage Architecture

```
┌───────────────────────────────────────┐
│         Checkpoint Manager             │
│  - CRUD operations                     │
│  - Auto-checkpoint logic               │
│  - Session management                  │
└─────────────┬─────────────────────────┘
              │ CheckpointStorage interface
              ▼
┌─────────────────────────────────────────────────┐
│              Storage Backends                    │
├──────────────┬──────────────┬───────────────────┤
│ InMemory     │ FileStorage  │ SQLiteStorage     │
│ - HashMap    │ - JSON files │ - SQL queries     │
│ - Fast       │ - Persistent │ - Structured      │
└──────────────┴──────────────┴───────────────────┘
```

### Threading Model

**Python**: Thread-safe with `threading.Lock`
**Go**: Goroutine-safe with `sync.Mutex`
**TypeScript**: Event loop, no locking needed
**Rust**: `Arc<Mutex<>>` for thread safety
**C++**: `std::mutex` for concurrent access
**Zig**: `std.Thread.Mutex` manual management
**C#**: No explicit locking — `CheckpointManager` (`agenkit-cs/src/Agenkit/Checkpointing/CheckpointManager.cs`) does a plain `File.WriteAllTextAsync`/`File.ReadAllTextAsync` per call; concurrent writers to the same checkpoint name can race
**Java**: `ConcurrentHashMap` for the in-memory cache (`agenkit-java/src/main/java/io/agenkit/checkpointing/CheckpointManager.java`); the JSON file write via Jackson is unsynchronized
**Scala**: `java.util.concurrent.ConcurrentHashMap` (`agenkit-scala/src/main/scala/io/agenkit/checkpointing/CheckpointManager.scala`) — in-memory only, no file I/O to race on

---

## Storage Backends

### InMemoryStorage

**Use for:**
- Development and testing
- Short-lived sessions
- Maximum performance

**Pros:**
- Zero I/O latency
- Simple setup
- Thread-safe

**Cons:**
- Lost on restart
- Memory usage grows with checkpoints
- Not suitable for production

**Example:**

```python
# Python
from agenkit import InMemoryStorage, CheckpointManager

storage = InMemoryStorage()
manager = CheckpointManager(storage, auto_checkpoint_interval=10)
```

```go
// Go
storage := checkpointing.NewInMemoryStorage()
manager := checkpointing.NewCheckpointManager(storage, 10)
```

```typescript
// TypeScript
const storage = new InMemoryStorage();
const manager = new CheckpointManager(storage, 10);
```

```zig
// Zig
var storage = InMemoryStorage.init(allocator);
defer storage.deinit();
var manager = CheckpointManager.init(allocator, storage.storage(), 10);
defer manager.deinit();
```

### FileStorage

**Use for:**
- Production deployments
- Single-node applications
- Human-readable checkpoints

**Pros:**
- Persists across restarts
- JSON format (human-readable)
- No database dependencies
- Easy to backup/migrate

**Cons:**
- Slower than in-memory
- File system I/O limits
- Manual cleanup needed

**Directory Structure:**

```
checkpoint_dir/
├── session-1/
│   ├── checkpoint-uuid-1.json
│   ├── checkpoint-uuid-2.json
│   └── checkpoint-uuid-3.json
├── session-2/
│   └── checkpoint-uuid-4.json
└── session-3/
    └── checkpoint-uuid-5.json
```

**Example:**

```python
# Python
from agenkit import FileStorage

storage = FileStorage("./checkpoints")
# Creates ./checkpoints/{session_id}/{checkpoint_id}.json
```

```go
// Go
storage, err := checkpointing.NewFileStorage("./checkpoints")
if err != nil {
    log.Fatal(err)
}
defer storage.Close()
```

```zig
// Zig
var storage = try FileStorage.init(allocator, "./checkpoints");
defer storage.deinit();
```

### SQLiteStorage (Python Only)

**Use for:**
- Structured queries
- Analytics on checkpoints
- Complex retention policies

**Pros:**
- SQL queries
- Atomic transactions
- Efficient indexing
- Built into Python

**Cons:**
- Database overhead
- Locking contention
- Not distributed

**Example:**

```python
from agenkit import SQLiteStorage

storage = SQLiteStorage("checkpoints.db")
# Creates SQLite database with indexed tables
```

### RedisStorage (Python/Go)

**Use for:**
- Distributed systems
- High-throughput applications
- Multi-node deployments

**Pros:**
- Distributed
- High performance
- Built-in TTL/expiry
- Pub/sub capabilities

**Cons:**
- External dependency
- Network latency
- Configuration complexity

**Example:**

```python
# Python
from agenkit import RedisStorage

storage = RedisStorage(
    host="localhost",
    port=6379,
    db=0,
    ttl=86400  # 24 hours
)
```

```go
// Go
storage, err := checkpointing.NewRedisStorage(
    "localhost:6379",
    0,  // db
    24 * time.Hour,  // ttl
)
```

---

## Quick Start

### 1. Basic Checkpointing (Python)

```python
from agenkit import Agent, EchoAgent, DurableAgent, InMemoryStorage

# Create base agent
agent = EchoAgent()

# Wrap with checkpointing
storage = InMemoryStorage()
durable = DurableAgent(
    agent=agent,
    storage=storage,
    auto_checkpoint_interval=5,  # Checkpoint every 5 steps
    auto_resume=True              # Resume from latest on start
)

# Use normally - checkpointing happens automatically
response = durable.process_with_session(
    Message.with_text("user", "Hello!"),
    session_id="my-session"
)
```

### 2. Manual Checkpointing (Go)

```go
package main

import (
    "agenkit-go/checkpointing"
    "agenkit-go/message"
)

func main() {
    // Create storage
    storage := checkpointing.NewInMemoryStorage()
    manager := checkpointing.NewCheckpointManager(storage, 0) // 0 = manual

    // Create checkpoint manually
    state := map[string]interface{}{
        "counter": 5,
        "status": "processing",
    }

    messages := []message.Message{
        message.WithText("user", "Hello"),
    }

    checkpointID, err := manager.CreateCheckpoint(
        "session-1",
        "my-agent",
        1, // step number
        state,
        messages,
        nil, // metadata
        nil, // parent checkpoint
    )
    if err != nil {
        panic(err)
    }

    // Later: restore from checkpoint
    checkpoint, err := manager.GetLatest("session-1")
    if err != nil {
        panic(err)
    }

    restoredState := checkpoint.State
    // Continue processing...
}
```

### 3. File Persistence (TypeScript)

```typescript
import { DurableAgent, FileStorage, Message } from 'agenkit';

// Create file-backed storage
const storage = new FileStorage('./checkpoints');
const durable = new DurableAgent(
  myAgent,
  storage,
  3,    // checkpoint every 3 steps
  true  // auto-resume
);

// Checkpoints persist across restarts
const response = await durable.processWithSession(
  Message.withText('user', 'Resume my task'),
  'persistent-session'
);

// Survives process restart!
```

### 4. Checkpoint History (Zig)

```zig
const agenkit = @import("agenkit");

// Get checkpoint history
const history = try manager.getCheckpointHistory(checkpoint_id, 10);
defer {
    for (history) |cp| {
        cp.deinit();
        allocator.destroy(cp);
    }
    allocator.free(history);
}

// Iterate through checkpoint chain
for (history, 0..) |checkpoint, i| {
    std.debug.print("Step {d}: {s}\n", .{
        i,
        checkpoint.checkpoint_id,
    });
}
```

---

## Usage Patterns

### Pattern 1: Automatic Checkpointing

**When:** Background processing, batch jobs, long workflows
**How:** Set `auto_checkpoint_interval` to checkpoint every N steps

```python
# Python
durable = DurableAgent(
    agent=agent,
    storage=FileStorage("./checkpoints"),
    auto_checkpoint_interval=10,  # Every 10 steps
    auto_resume=True
)

# Automatically checkpoints after every 10 messages
for i in range(100):
    response = durable.process_with_session(
        Message.with_text("user", f"Task {i}"),
        session_id="batch-job"
    )
```

**Benefits:**
- No manual checkpoint calls
- Consistent checkpoint frequency
- Minimal code changes

### Pattern 2: Manual Checkpointing

**When:** Critical operations, transaction boundaries, custom logic
**How:** Checkpoint explicitly at important points

```python
# Python
durable = DurableAgent(
    agent=agent,
    storage=storage,
    auto_checkpoint_interval=0,  # Manual only
)

# Checkpoint before expensive operation
checkpoint_id = durable.checkpoint("session-1")

try:
    result = expensive_operation()
    # Checkpoint after success
    checkpoint_id = durable.checkpoint("session-1", metadata={
        "status": "success",
        "result_size": len(result)
    })
except Exception as e:
    # Can rollback to previous checkpoint
    durable.resume_from_checkpoint("session-1", checkpoint_id)
```

**Benefits:**
- Fine-grained control
- Checkpoint at transaction boundaries
- Custom metadata for each checkpoint

### Pattern 3: Resumption on Failure

**When:** Unreliable networks, cloud functions, intermittent failures
**How:** Enable `auto_resume` and catch exceptions

```python
# Python
def process_with_retry(durable, message, session_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            return durable.process_with_session(message, session_id)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            # Automatically resumes from last checkpoint on next call
            print(f"Attempt {attempt + 1} failed, retrying...")

# Usage
durable = DurableAgent(agent, storage, auto_resume=True)
response = process_with_retry(durable, message, "session-1")
```

**Benefits:**
- Automatic recovery
- No lost work
- Transparent to caller

### Pattern 4: Time-Travel Debugging

**When:** Debugging complex workflows, reproducing issues
**How:** Load specific checkpoint and replay

```python
# Python
# List all checkpoints for session
checkpoints = manager.list_checkpoints("debug-session", limit=0)

# Find problematic checkpoint
problem_checkpoint = next(
    cp for cp in checkpoints
    if cp.metadata.get("error") is not None
)

# Load state from before error
state = manager.restore_state(problem_checkpoint)

# Replay from that point with modified inputs
agent.state = state
response = agent.process(modified_message)
```

**Benefits:**
- Reproduce issues reliably
- Test fixes without full replay
- Inspect state at any point

### Pattern 5: Checkpoint Pruning

**When:** Long-running sessions, storage limits
**How:** Implement retention policies

```python
# Python
# Keep only last 10 checkpoints per session
def prune_old_checkpoints(manager, session_id, keep_last=10):
    deleted = manager.prune_old_checkpoints(session_id, keep_last)
    print(f"Deleted {deleted} old checkpoints")

# Run periodically
import schedule
schedule.every().day.at("02:00").do(
    lambda: prune_old_checkpoints(manager, "long-session")
)
```

**Benefits:**
- Control storage usage
- Keep recent checkpoints
- Configurable retention

### Pattern 6: Distributed Checkpointing

**When:** Multi-node deployments, load balancing
**How:** Use shared storage backend (Redis, S3)

```python
# Python
# Node 1
storage = RedisStorage(host="redis.example.com")
durable = DurableAgent(agent, storage, auto_resume=True)
response = durable.process_with_session(msg, "shared-session")

# Node 2 (different machine)
storage = RedisStorage(host="redis.example.com")
durable = DurableAgent(agent, storage, auto_resume=True)
# Automatically resumes from checkpoint created by Node 1
response = durable.process_with_session(msg, "shared-session")
```

**Benefits:**
- Agent migration between nodes
- Load balancing
- High availability

---

## API Reference

### CheckpointManager

**Python:**
```python
class CheckpointManager:
    def __init__(
        self,
        storage: CheckpointStorage,
        auto_checkpoint_interval: int = 0
    )

    def create_checkpoint(
        self,
        session_id: str,
        agent_name: str,
        step_number: int,
        state: dict,
        messages: list[Message],
        metadata: dict | None = None,
        parent_checkpoint_id: str | None = None
    ) -> str

    def load_checkpoint(self, checkpoint_id: str) -> Checkpoint | None
    def get_latest(self, session_id: str) -> Checkpoint | None
    def list_checkpoints(self, session_id: str, limit: int = 0) -> list[Checkpoint]
    def delete_checkpoint(self, checkpoint_id: str) -> bool
    def delete_session(self, session_id: str) -> int
    def prune_old_checkpoints(self, session_id: str, keep_last: int) -> int
    def get_session_stats(self, session_id: str) -> dict
    def should_checkpoint(self, session_id: str, step_number: int) -> bool
```

**Go:**
```go
type CheckpointManager struct {}

func NewCheckpointManager(
    storage CheckpointStorage,
    autoCheckpointInterval int,
) *CheckpointManager

func (m *CheckpointManager) CreateCheckpoint(
    sessionID string,
    agentName string,
    stepNumber int,
    state map[string]interface{},
    messages []message.Message,
    metadata map[string]interface{},
    parentCheckpointID *string,
) (string, error)

func (m *CheckpointManager) LoadCheckpoint(checkpointID string) (*Checkpoint, error)
func (m *CheckpointManager) GetLatest(sessionID string) (*Checkpoint, error)
func (m *CheckpointManager) ListCheckpoints(sessionID string, limit int) ([]*Checkpoint, error)
func (m *CheckpointManager) DeleteCheckpoint(checkpointID string) (bool, error)
func (m *CheckpointManager) DeleteSession(sessionID string) (int, error)
func (m *CheckpointManager) PruneOldCheckpoints(sessionID string, keepLast int) (int, error)
func (m *CheckpointManager) GetSessionStats(sessionID string) (map[string]interface{}, error)
func (m *CheckpointManager) ShouldCheckpoint(sessionID string, stepNumber int) bool
```

**TypeScript:**
```typescript
class CheckpointManager {
  constructor(
    storage: CheckpointStorage,
    autoCheckpointInterval: number = 0
  );

  createCheckpoint(
    sessionId: string,
    agentName: string,
    stepNumber: number,
    state: Record<string, any>,
    messages: Message[],
    metadata?: Record<string, any>,
    parentCheckpointId?: string
  ): Promise<string>;

  loadCheckpoint(checkpointId: string): Promise<Checkpoint | null>;
  getLatest(sessionId: string): Promise<Checkpoint | null>;
  listCheckpoints(sessionId: string, limit?: number): Promise<Checkpoint[]>;
  deleteCheckpoint(checkpointId: string): Promise<boolean>;
  deleteSession(sessionId: string): Promise<number>;
  pruneOldCheckpoints(sessionId: string, keepLast: number): Promise<number>;
  getSessionStats(sessionId: string): Promise<Record<string, any>>;
  shouldCheckpoint(sessionId: string, stepNumber: number): boolean;
}
```

**Zig:**
```zig
pub const CheckpointManager = struct {
    allocator: Allocator,
    storage: CheckpointStorage,
    auto_checkpoint_interval: usize,

    pub fn init(
        allocator: Allocator,
        storage: CheckpointStorage,
        auto_checkpoint_interval: usize,
    ) CheckpointManager;

    pub fn deinit(self: *CheckpointManager) void;

    pub fn createCheckpoint(
        self: *CheckpointManager,
        session_id: []const u8,
        agent_name: []const u8,
        step_number: usize,
        state: std.json.Value,
        messages: []const Message,
        metadata: ?std.json.Value,
        parent_checkpoint_id: ?[]const u8,
    ) ![]const u8;

    pub fn loadCheckpoint(self: *CheckpointManager, checkpoint_id: []const u8) !?*Checkpoint;
    pub fn getLatest(self: *CheckpointManager, session_id: []const u8) !?*Checkpoint;
    pub fn listCheckpoints(self: *CheckpointManager, session_id: []const u8, limit: usize) ![]const *Checkpoint;
    pub fn deleteCheckpoint(self: *CheckpointManager, checkpoint_id: []const u8) !bool;
    pub fn deleteSession(self: *CheckpointManager, session_id: []const u8) !usize;
    pub fn pruneOldCheckpoints(self: *CheckpointManager, session_id: []const u8, keep_last: usize) !usize;
    pub fn getSessionStats(self: *CheckpointManager, session_id: []const u8) !std.json.Value;
    pub fn shouldCheckpoint(self: *CheckpointManager, session_id: []const u8, step_number: usize) bool;
};
```

### DurableAgent

**Python:**
```python
class DurableAgent:
    def __init__(
        self,
        agent: Agent,
        storage: CheckpointStorage,
        auto_checkpoint_interval: int = 0,
        auto_resume: bool = False
    )

    def process_with_session(
        self,
        message: Message,
        session_id: str
    ) -> Message

    def checkpoint(
        self,
        session_id: str,
        metadata: dict | None = None
    ) -> str

    def resume_from_checkpoint(
        self,
        session_id: str,
        checkpoint_id: str | None = None
    ) -> dict | None

    def reset_session(self, session_id: str) -> None
    def get_state(self, session_id: str) -> dict | None
    def list_checkpoints(self, session_id: str, limit: int = 0) -> list[Checkpoint]
    def delete_checkpoints(self, session_id: str) -> int
    def get_session_stats(self, session_id: str) -> dict
```

**Go:**
```go
type DurableAgent struct {}

func NewDurableAgent(
    agent agents.Agent,
    storage CheckpointStorage,
    autoCheckpointInterval int,
    autoResume bool,
) (*DurableAgent, error)

func (d *DurableAgent) ProcessWithSession(
    msg message.Message,
    sessionID string,
) (message.Message, error)

func (d *DurableAgent) Checkpoint(
    sessionID string,
    metadata map[string]interface{},
) (string, error)

func (d *DurableAgent) ResumeFromCheckpoint(
    sessionID string,
    checkpointID *string,
) (map[string]interface{}, error)

func (d *DurableAgent) ResetSession(sessionID string)
func (d *DurableAgent) GetState(sessionID string) (map[string]interface{}, bool)
func (d *DurableAgent) ListCheckpoints(sessionID string, limit int) ([]*Checkpoint, error)
func (d *DurableAgent) DeleteCheckpoints(sessionID string) (int, error)
func (d *DurableAgent) GetSessionStats(sessionID string) (map[string]interface{}, error)
```

**Zig:**
```zig
pub const DurableAgent = struct {
    allocator: Allocator,
    agent: *Agent,
    manager: CheckpointManager,
    auto_resume: bool,

    pub fn init(
        allocator: Allocator,
        agent: *Agent,
        storage: CheckpointStorage,
        auto_checkpoint_interval: usize,
        auto_resume: bool,
    ) !DurableAgent;

    pub fn deinit(self: *DurableAgent) void;

    pub fn processWithSession(
        self: *DurableAgent,
        message: Message,
        session_id: []const u8,
    ) !Message;

    pub fn checkpoint(
        self: *DurableAgent,
        session_id: []const u8,
        metadata: ?std.json.Value,
    ) ![]const u8;

    pub fn resumeFromCheckpoint(
        self: *DurableAgent,
        session_id: []const u8,
        checkpoint_id: ?[]const u8,
    ) !?std.json.Value;

    pub fn resetSession(self: *DurableAgent, session_id: []const u8) void;
    pub fn getState(self: *DurableAgent, session_id: []const u8) ?std.json.Value;
    pub fn listCheckpoints(self: *DurableAgent, session_id: []const u8, limit: usize) ![]const *Checkpoint;
    pub fn deleteCheckpoints(self: *DurableAgent, session_id: []const u8) !usize;
    pub fn getSessionStats(self: *DurableAgent, session_id: []const u8) !std.json.Value;
};
```

### C#/Java/Scala Checkpointing Baseline

C#, Java, and Scala implement checkpointing, but with a much smaller surface than the
`CheckpointManager`/`CheckpointStorage`/`DurableAgent` contract described above — they
predate a `Checkpoint` type with `session_id`, `step_number`, `parent_checkpoint_id`, or
any pluggable `CheckpointStorage` backend. None of the three has `list_checkpoints`,
`get_latest`, `prune_old_checkpoints`, `get_session_stats`, or `should_checkpoint`.

**C#** (`agenkit-cs/src/Agenkit/Checkpointing/CheckpointManager.cs`):
```csharp
public class CheckpointManager
{
    public CheckpointManager(string directory = "checkpoints");
    public Task SaveAsync(string name, object state, CancellationToken ct = default);
    public Task<T?> LoadAsync<T>(string name, CancellationToken ct = default);
    public bool Exists(string name);
    public void Delete(string name);
    public IReadOnlyList<string> ListCheckpoints();
}
```
Checkpoints are keyed by an arbitrary `name` (not a session/step pair) and persisted as
one JSON file per name — `System.Text.Json`, no in-memory cache.
`DurableAgent(IAgent inner, CheckpointManager manager, string? checkpointName = null)`
(`agenkit-cs/src/Agenkit/Checkpointing/DurableAgent.cs`) checkpoints **after every single
message** — there is no `auto_checkpoint_interval`, so the canonical "checkpoint every N
steps" default doesn't apply; N is implicitly `1`.

**Java** (`agenkit-java/src/main/java/io/agenkit/checkpointing/CheckpointManager.java`):
```java
public final class CheckpointManager {
    public CheckpointManager(Path checkpointDir);
    public CheckpointManager();  // defaults to {java.io.tmpdir}/agenkit-checkpoints
    public void save(String agentId, Object state);
    public Optional<Object> load(String agentId);
    public void delete(String agentId);
    public boolean exists(String agentId);
}
```
Keyed by `agentId`, backed by both a `ConcurrentHashMap` (read-through cache) and a
Jackson-serialized JSON file. `DurableAgent(Agent inner, CheckpointManager
checkpointManager)` (`agenkit-java/src/main/java/io/agenkit/checkpointing/DurableAgent.java`)
also checkpoints after every message (accumulating an `interactionLog`, not a `state`
dict) — no configurable interval, same as C#.

**Scala** (`agenkit-scala/src/main/scala/io/agenkit/checkpointing/CheckpointManager.scala`):
```scala
case class Checkpoint(
  id: String,
  agentName: String,
  messages: List[Message],
  metadata: Map[String, Any],
  createdAt: Instant = Instant.now()
)

class CheckpointManager:
  def save(checkpoint: Checkpoint): Unit
  def load(id: String): Option[Checkpoint]
  def list(agentName: String): List[Checkpoint]
  def delete(id: String): Boolean
  def count: Int
```
Scala is the only one of the three with a real `Checkpoint` case class (closer in shape
to the canonical one) and the only one with a configurable interval: `DurableAgent(inner:
Agent, checkpointManager: CheckpointManager, checkpointInterval: Int = 10)`
(`agenkit-scala/src/main/scala/io/agenkit/checkpointing/DurableAgent.scala`) — **default
`10`**, matching the canonical "every 10 steps" default used in the Quick Start examples
above. Storage is in-memory only (`ConcurrentHashMap`); there is no file or database
backend, so `count` and `list(agentName)` are the closest analogs to
`get_session_stats`/`list_checkpoints`, and both lose all data on restart.

| | C# | Java | Scala |
|---|---|---|---|
| Checkpoint key | `name` (string) | `agentId` (string) | `id` (string, UUID in `DurableAgent`) |
| Storage backend | File (JSON) | File (JSON) + in-memory cache | In-memory only |
| `auto_checkpoint_interval` default | not implemented (every message) | not implemented (every message) | `10` |
| Checkpoint chain / `parent_checkpoint_id` | not implemented | not implemented | not implemented |
| Retention / pruning | not implemented | not implemented | not implemented |
| Thread safety | none (file I/O unsynchronized) | `ConcurrentHashMap` (cache only) | `ConcurrentHashMap` |

---

## Language-Specific Examples

### Python Example

```python
from agenkit import (
    Agent, Message, DurableAgent,
    FileStorage, CheckpointManager
)

# Create custom agent
class MyAgent(Agent):
    def process(self, message: Message) -> Message:
        # Your logic here
        return Message.with_text("assistant", "Response")

# Setup checkpointing
storage = FileStorage("./checkpoints")
agent = MyAgent()
durable = DurableAgent(
    agent=agent,
    storage=storage,
    auto_checkpoint_interval=5,
    auto_resume=True
)

# Use with automatic checkpointing
session_id = "user-123"
for i in range(20):
    msg = Message.with_text("user", f"Message {i}")
    response = durable.process_with_session(msg, session_id)
    print(f"Step {i}: {response.content}")

# Get statistics
stats = durable.get_session_stats(session_id)
print(f"Total checkpoints: {stats['total_checkpoints']}")
print(f"Latest step: {stats['latest_step']}")
```

### Go Example

```go
package main

import (
    "fmt"
    "log"

    "agenkit-go/agents"
    "agenkit-go/checkpointing"
    "agenkit-go/message"
)

func main() {
    // Create agent
    agent := agents.NewEchoAgent()

    // Setup checkpointing
    storage, err := checkpointing.NewFileStorage("./checkpoints")
    if err != nil {
        log.Fatal(err)
    }
    defer storage.Close()

    durable, err := checkpointing.NewDurableAgent(
        agent,
        storage,
        5,    // checkpoint every 5 steps
        true, // auto-resume
    )
    if err != nil {
        log.Fatal(err)
    }

    // Use with automatic checkpointing
    sessionID := "user-123"
    for i := 0; i < 20; i++ {
        msg := message.WithText("user", fmt.Sprintf("Message %d", i))
        response, err := durable.ProcessWithSession(msg, sessionID)
        if err != nil {
            log.Printf("Error at step %d: %v", i, err)
            continue
        }
        fmt.Printf("Step %d: %s\n", i, response.Content())
    }

    // Get statistics
    stats, err := durable.GetSessionStats(sessionID)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Total checkpoints: %v\n", stats["total_checkpoints"])
}
```

### TypeScript Example

```typescript
import {
  Agent, Message, DurableAgent,
  FileStorage, CheckpointManager
} from 'agenkit';

// Create custom agent
class MyAgent implements Agent {
  async process(message: Message): Promise<Message> {
    // Your logic here
    return Message.withText('assistant', 'Response');
  }
}

// Setup checkpointing
const storage = new FileStorage('./checkpoints');
const agent = new MyAgent();
const durable = new DurableAgent(
  agent,
  storage,
  5,    // checkpoint every 5 steps
  true  // auto-resume
);

// Use with automatic checkpointing
const sessionId = 'user-123';
for (let i = 0; i < 20; i++) {
  const msg = Message.withText('user', `Message ${i}`);
  const response = await durable.processWithSession(msg, sessionId);
  console.log(`Step ${i}: ${response.content}`);
}

// Get statistics
const stats = await durable.getSessionStats(sessionId);
console.log(`Total checkpoints: ${stats.total_checkpoints}`);
console.log(`Latest step: ${stats.latest_step}`);
```

### Rust Example

```rust
use agenkit::{
    Agent, Message, DurableAgent,
    FileStorage, CheckpointManager,
};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Create agent
    let agent = MyAgent::new();

    // Setup checkpointing
    let storage = FileStorage::new("./checkpoints")?;
    let durable = DurableAgent::new(
        Box::new(agent),
        Box::new(storage),
        5,    // checkpoint every 5 steps
        true, // auto-resume
    )?;

    // Use with automatic checkpointing
    let session_id = "user-123";
    for i in 0..20 {
        let msg = Message::with_text("user", format!("Message {}", i));
        let response = durable.process_with_session(msg, session_id).await?;
        println!("Step {}: {}", i, response.content());
    }

    // Get statistics
    let stats = durable.get_session_stats(session_id).await?;
    println!("Total checkpoints: {}", stats["total_checkpoints"]);

    Ok(())
}
```

### C++ Example

```cpp
#include <agenkit/checkpointing.hpp>
#include <iostream>

int main() {
    // Create agent
    auto agent = std::make_unique<MyAgent>();

    // Setup checkpointing
    auto storage = agenkit::FileStorage::create("./checkpoints");
    auto durable = agenkit::DurableAgent(
        std::move(agent),
        std::move(storage),
        5,    // checkpoint every 5 steps
        true  // auto-resume
    );

    // Use with automatic checkpointing
    std::string session_id = "user-123";
    for (int i = 0; i < 20; i++) {
        auto msg = agenkit::Message::with_text(
            "user",
            "Message " + std::to_string(i)
        );
        auto response = durable.process_with_session(msg, session_id);
        std::cout << "Step " << i << ": " << response.content() << "\n";
    }

    // Get statistics
    auto stats = durable.get_session_stats(session_id);
    std::cout << "Total checkpoints: "
              << stats["total_checkpoints"] << "\n";

    return 0;
}
```

### Zig Example

```zig
const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Create agent
    var agent = try MyAgent.init(allocator);
    defer agent.deinit();

    // Setup checkpointing
    var storage = try agenkit.FileStorage.init(allocator, "./checkpoints");
    defer storage.deinit();

    var durable = try agenkit.DurableAgent.init(
        allocator,
        agent.agent(),
        storage.storage(),
        5,    // checkpoint every 5 steps
        true, // auto-resume
    );
    defer durable.deinit();

    // Use with automatic checkpointing
    const session_id = "user-123";
    var i: usize = 0;
    while (i < 20) : (i += 1) {
        const text = try std.fmt.allocPrint(allocator, "Message {d}", .{i});
        defer allocator.free(text);

        var msg = try agenkit.Message.withText(allocator, .user, text);
        defer msg.deinit();

        const result = try durable.processWithSession(msg, session_id);
        var response = try result.unwrap();
        defer response.deinit();

        std.debug.print("Step {d}: {s}\n", .{i, try response.contentAsText()});
    }

    // Get statistics
    var stats = try durable.getSessionStats(session_id);
    defer stats.object.deinit();

    if (stats.object.get("total_checkpoints")) |total| {
        std.debug.print("Total checkpoints: {d}\n", .{total.integer});
    }
}
```

---

## Best Practices

### 1. Choose Appropriate Checkpoint Frequency

**Too frequent:**
- Higher I/O overhead
- More storage usage
- Slower execution

**Too infrequent:**
- More work lost on failure
- Longer recovery time
- Less granular replay

**Recommendations:**
- **Fast operations (< 100ms)**: Every 50-100 steps
- **Medium operations (100ms-1s)**: Every 10-20 steps
- **Expensive operations (> 1s)**: Every 1-5 steps
- **Critical transactions**: Manual checkpoint before/after

```python
# Python - adaptive checkpointing
class AdaptiveDurableAgent:
    def determine_interval(self, avg_step_time_ms):
        if avg_step_time_ms < 100:
            return 50
        elif avg_step_time_ms < 1000:
            return 10
        else:
            return 5
```

### 2. Include Meaningful Metadata

Metadata helps with debugging, analytics, and retention policies:

```python
# Python
checkpoint_id = durable.checkpoint(
    session_id,
    metadata={
        "operation": "payment_processing",
        "amount": 99.99,
        "currency": "USD",
        "status": "completed",
        "duration_ms": 1523,
        "retry_count": 0,
        "tags": ["critical", "production"],
    }
)
```

### 3. Implement Retention Policies

Don't let checkpoints grow unbounded:

```python
# Python
# Strategy 1: Keep last N checkpoints
manager.prune_old_checkpoints(session_id, keep_last=10)

# Strategy 2: Time-based retention
def prune_by_age(manager, session_id, max_age_days=7):
    cutoff = time.time() - (max_age_days * 86400 * 1000)
    checkpoints = manager.list_checkpoints(session_id, limit=0)

    for cp in checkpoints:
        if cp.timestamp < cutoff:
            manager.delete_checkpoint(cp.checkpoint_id)

# Strategy 3: Keep important checkpoints
def prune_with_exceptions(manager, session_id, keep_last=5):
    checkpoints = manager.list_checkpoints(session_id, limit=0)

    # Always keep checkpoints marked as important
    important = [cp for cp in checkpoints
                 if cp.metadata.get("important")]
    recent = checkpoints[:keep_last]

    to_keep = set([cp.checkpoint_id for cp in important + recent])

    for cp in checkpoints:
        if cp.checkpoint_id not in to_keep:
            manager.delete_checkpoint(cp.checkpoint_id)
```

### 4. Handle Storage Failures Gracefully

Storage operations can fail - handle them properly:

```python
# Python
def safe_checkpoint(durable, session_id):
    try:
        return durable.checkpoint(session_id)
    except IOError as e:
        # Storage failure - log but continue
        logger.error(f"Checkpoint failed: {e}")
        return None
    except Exception as e:
        # Unexpected error - re-raise
        logger.exception(f"Unexpected checkpoint error: {e}")
        raise

# Use with fallback
checkpoint_id = safe_checkpoint(durable, session_id)
if checkpoint_id:
    logger.info(f"Checkpointed: {checkpoint_id}")
else:
    logger.warning("Checkpoint skipped due to storage error")
```

### 5. Test Resumption Logic

Always test that your agent can resume correctly:

```python
# Python - test resumption
def test_agent_resumption():
    storage = InMemoryStorage()
    agent = MyAgent()
    durable = DurableAgent(agent, storage, auto_checkpoint_interval=1)

    # Process some messages
    for i in range(5):
        msg = Message.with_text("user", f"Message {i}")
        durable.process_with_session(msg, "test-session")

    # Simulate failure and restart
    state_before = durable.get_state("test-session")
    durable.reset_session("test-session")

    # Should resume from checkpoint
    restored = durable.resume_from_checkpoint("test-session")
    assert restored == state_before

    # Continue processing
    msg = Message.with_text("user", "After resume")
    response = durable.process_with_session(msg, "test-session")
    assert response is not None
```

### 6. Use Appropriate Storage for Environment

**Development:**
```python
storage = InMemoryStorage()  # Fast, no persistence needed
```

**Single-Node Production:**
```python
storage = FileStorage("./checkpoints")  # Persistent, simple
```

**Multi-Node Production:**
```python
storage = RedisStorage(host="redis.cluster")  # Distributed
```

**Compliance/Audit:**
```python
storage = SQLiteStorage("audit.db")  # Queryable, structured
```

### 7. Monitor Checkpoint Performance

Track checkpoint metrics in production:

```python
# Python
import time
from dataclasses import dataclass

@dataclass
class CheckpointMetrics:
    checkpoint_duration_ms: float
    checkpoint_size_bytes: int
    storage_latency_ms: float

def monitored_checkpoint(durable, session_id):
    start = time.time()

    checkpoint_id = durable.checkpoint(session_id)

    duration = (time.time() - start) * 1000

    # Log metrics
    logger.info(
        "checkpoint_created",
        checkpoint_id=checkpoint_id,
        duration_ms=duration,
        session_id=session_id,
    )

    return checkpoint_id
```

### 8. Secure Sensitive Data

Checkpoints may contain sensitive information:

```python
# Python
# Option 1: Encrypt checkpoint data
from cryptography.fernet import Fernet

class EncryptedFileStorage:
    def __init__(self, base_dir, encryption_key):
        self.storage = FileStorage(base_dir)
        self.cipher = Fernet(encryption_key)

    def save(self, checkpoint):
        # Encrypt before saving
        checkpoint_json = checkpoint.to_json()
        encrypted = self.cipher.encrypt(checkpoint_json.encode())
        # Save encrypted data

    def load(self, checkpoint_id):
        # Load and decrypt
        encrypted = self.storage.load_raw(checkpoint_id)
        decrypted = self.cipher.decrypt(encrypted)
        return Checkpoint.from_json(decrypted)

# Option 2: Redact sensitive fields
def sanitize_checkpoint(checkpoint):
    """Remove sensitive data from checkpoint before saving."""
    state = checkpoint.state.copy()

    # Redact sensitive fields
    sensitive_keys = ["password", "api_key", "token", "ssn"]
    for key in sensitive_keys:
        if key in state:
            state[key] = "[REDACTED]"

    checkpoint.state = state
    return checkpoint
```

---

## Troubleshooting

### Issue: Checkpoint Not Found After Restart

**Symptom:** `get_latest()` returns `None` after process restart

**Causes:**
1. Using `InMemoryStorage` (not persistent)
2. Wrong checkpoint directory
3. Session ID mismatch

**Solutions:**

```python
# Python
# 1. Use persistent storage
storage = FileStorage("./checkpoints")  # Not InMemoryStorage

# 2. Verify checkpoint directory exists
import os
assert os.path.exists("./checkpoints")

# 3. List all sessions to verify
storage_impl = storage._storage  # Access underlying storage
sessions = os.listdir("./checkpoints")
print(f"Available sessions: {sessions}")
```

### Issue: High Memory Usage

**Symptom:** Memory grows unbounded with many checkpoints

**Causes:**
1. No retention policy
2. Large state objects in checkpoints
3. Holding checkpoint references

**Solutions:**

```python
# Python
# 1. Implement pruning
manager.prune_old_checkpoints(session_id, keep_last=10)

# 2. Minimize state size
def get_minimal_state(agent):
    """Only include essential state."""
    return {
        "counter": agent.counter,
        "last_id": agent.last_id,
        # Don't include: full conversation history, cached data
    }

# 3. Release checkpoint references
checkpoints = manager.list_checkpoints(session_id)
process_checkpoints(checkpoints)
del checkpoints  # Free memory
```

### Issue: Slow Checkpoint Performance

**Symptom:** Checkpointing takes too long, slowing down agent

**Causes:**
1. Large state or message history
2. Slow storage backend
3. Too frequent checkpointing

**Solutions:**

```python
# Python
# 1. Reduce state size
def optimize_state(state):
    # Compress large objects
    if len(state.get("history", [])) > 100:
        state["history"] = state["history"][-50:]  # Keep only recent
    return state

# 2. Use faster storage
storage = InMemoryStorage()  # For development
# Or use Redis with connection pooling

# 3. Adjust checkpoint frequency
durable = DurableAgent(
    agent,
    storage,
    auto_checkpoint_interval=20,  # Less frequent
)

# 4. Checkpoint asynchronously (Python asyncio)
async def async_checkpoint(durable, session_id):
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        durable.checkpoint,
        session_id
    )
```

### Issue: Checkpoint Corruption

**Symptom:** Cannot load checkpoint, JSON parse errors

**Causes:**
1. Process killed during write
2. Disk full
3. Concurrent writes

**Solutions:**

```python
# Python
# 1. Use atomic writes
import tempfile
import os

class AtomicFileStorage:
    def save(self, checkpoint):
        # Write to temp file first
        temp_path = f"{checkpoint_path}.tmp"
        with open(temp_path, 'w') as f:
            f.write(checkpoint.to_json())
            f.flush()
            os.fsync(f.fileno())  # Force to disk

        # Atomic rename
        os.rename(temp_path, checkpoint_path)

# 2. Verify after write
def verified_save(storage, checkpoint):
    storage.save(checkpoint)

    # Verify by loading
    loaded = storage.load(checkpoint.checkpoint_id)
    if not loaded:
        raise IOError("Checkpoint verification failed")

# 3. Add checksums
import hashlib

def add_checksum(checkpoint_json):
    checksum = hashlib.sha256(checkpoint_json.encode()).hexdigest()
    return {
        "data": checkpoint_json,
        "checksum": checksum,
    }

def verify_checksum(data):
    expected = data["checksum"]
    actual = hashlib.sha256(data["data"].encode()).hexdigest()
    if expected != actual:
        raise ValueError("Checkpoint checksum mismatch")
    return data["data"]
```

### Issue: Cannot Resume - State Mismatch

**Symptom:** Agent behaves incorrectly after resumption

**Causes:**
1. Incomplete state capture
2. Non-serializable state
3. Code version mismatch

**Solutions:**

```python
# Python
# 1. Capture complete state
class StatefulAgent(Agent):
    def get_checkpoint_state(self):
        """Override to ensure complete state."""
        return {
            "counter": self.counter,
            "status": self.status,
            "internal_state": self.internal_state,
            "version": "1.0",  # Track code version
        }

    def restore_checkpoint_state(self, state):
        """Override to restore complete state."""
        if state.get("version") != "1.0":
            raise ValueError("Incompatible checkpoint version")

        self.counter = state["counter"]
        self.status = state["status"]
        self.internal_state = state["internal_state"]

# 2. Handle version migration
def migrate_checkpoint(checkpoint, from_version, to_version):
    if from_version == "1.0" and to_version == "2.0":
        # Migrate state schema
        checkpoint.state["new_field"] = default_value
    return checkpoint

# 3. Validate state after restore
def validate_restored_state(agent, state):
    required_fields = ["counter", "status"]
    for field in required_fields:
        if field not in state:
            raise ValueError(f"Missing required field: {field}")
```

### Issue: Distributed Checkpoint Race Conditions

**Symptom:** Multiple nodes create conflicting checkpoints

**Causes:**
1. No coordination between nodes
2. Concurrent checkpoint creation
3. Stale checkpoint reads

**Solutions:**

```python
# Python with Redis
# 1. Use distributed locks
from redis import Redis
from redis.lock import Lock

def atomic_checkpoint(durable, session_id, redis_client):
    lock_key = f"checkpoint_lock:{session_id}"
    lock = Lock(redis_client, lock_key, timeout=5)

    if lock.acquire(blocking=True, blocking_timeout=10):
        try:
            return durable.checkpoint(session_id)
        finally:
            lock.release()
    else:
        raise TimeoutError("Could not acquire checkpoint lock")

# 2. Use optimistic locking with versioning
def checkpoint_with_version(manager, session_id, expected_version):
    latest = manager.get_latest(session_id)
    if latest and latest.metadata.get("version") != expected_version:
        raise ValueError("Checkpoint version conflict")

    checkpoint_id = manager.create_checkpoint(
        session_id,
        # ... checkpoint data ...
        metadata={"version": expected_version + 1}
    )
    return checkpoint_id

# 3. Use consensus protocol (advanced)
# Implement Raft or Paxos for distributed checkpointing
```

---

## Performance Considerations

### Checkpoint Size Optimization

**Minimize state size:**

```python
# Bad - includes unnecessary data
state = {
    "full_conversation": all_messages,      # 10,000+ messages
    "cached_embeddings": embeddings_cache,  # 100MB
    "debug_info": debug_logs,               # Large
}

# Good - only essential state
state = {
    "last_message_id": last_id,             # Small
    "user_preferences": user_prefs,         # Small
    "session_metadata": metadata,           # Small
}
```

**Use compression for large states:**

```python
# Python
import gzip
import json

def compress_checkpoint(checkpoint):
    json_str = checkpoint.to_json()
    compressed = gzip.compress(json_str.encode())
    return compressed

def decompress_checkpoint(compressed):
    json_str = gzip.decompress(compressed).decode()
    return Checkpoint.from_json(json_str)
```

### Storage Performance

**Benchmark different storage backends:**

| Storage | Write (ms) | Read (ms) | Disk Space | Concurrency |
|---------|-----------|----------|------------|-------------|
| InMemory | 0.01 | 0.01 | RAM only | Thread-safe |
| FileStorage | 5-10 | 2-5 | JSON files | Single-node |
| SQLite | 10-20 | 5-10 | Database | Single-node |
| Redis | 1-2 | 1-2 | RAM/Disk | Distributed |
| S3 | 50-100 | 20-50 | Cloud | Distributed |

**Choose based on requirements:**
- **Development**: InMemory (fastest)
- **Single-node prod**: FileStorage (simple, persistent)
- **Multi-node prod**: Redis (distributed, fast)
- **Compliance**: SQLite (queryable, structured)
- **Archival**: S3 (cheap, durable)

### Checkpoint Frequency vs Overhead

```python
# Python - measure checkpoint overhead
import time

def benchmark_checkpointing(agent, iterations=100):
    # Without checkpointing
    start = time.time()
    for i in range(iterations):
        agent.process(Message.with_text("user", f"Test {i}"))
    baseline = time.time() - start

    # With checkpointing every N steps
    for interval in [1, 5, 10, 20, 50]:
        durable = DurableAgent(agent, storage, interval)

        start = time.time()
        for i in range(iterations):
            durable.process_with_session(
                Message.with_text("user", f"Test {i}"),
                "bench-session"
            )
        elapsed = time.time() - start

        overhead = ((elapsed - baseline) / baseline) * 100
        print(f"Interval {interval}: {overhead:.1f}% overhead")

# Typical results:
# Interval 1:  25-40% overhead (checkpoint every step)
# Interval 5:  5-10% overhead
# Interval 10: 2-5% overhead
# Interval 20: 1-3% overhead
# Interval 50: <1% overhead
```

**Recommendations:**
- Aim for < 5% overhead in production
- Use intervals of 10-20 for most workloads
- Adjust based on step duration (longer steps = more frequent checkpoints tolerable)

### Batching and Async Checkpointing

```python
# Python - async checkpointing to reduce latency
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncDurableAgent:
    def __init__(self, agent, storage, interval):
        self.agent = agent
        self.storage = storage
        self.interval = interval
        self.executor = ThreadPoolExecutor(max_workers=2)

    async def process_with_session(self, message, session_id):
        # Process message
        response = self.agent.process(message)

        # Checkpoint asynchronously (non-blocking)
        if self.should_checkpoint(session_id):
            asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.checkpoint,
                session_id
            )
            # Don't wait for checkpoint to complete

        return response
```

---

## Conclusion

Checkpointing is essential for production-grade agent systems. Key takeaways:

1. **Start simple** - Use InMemoryStorage for development, FileStorage for production
2. **Tune checkpoint frequency** - Balance reliability with performance (10-20 steps typical)
3. **Implement retention** - Don't let checkpoints grow unbounded
4. **Test resumption** - Always verify agents can recover correctly
5. **Monitor performance** - Track checkpoint latency and storage usage
6. **Handle failures** - Storage operations can fail, handle gracefully
7. **Secure sensitive data** - Encrypt or redact sensitive information

### Next Steps

- Explore [Agent Patterns](./PATTERNS.md) for advanced agent architectures
- Read [Safety & Security](./SAFETY.md) for production hardening
- See [Performance Guide](./PERFORMANCE.md) for optimization techniques
- Check [Migration Guide](./MIGRATION.md) for framework-specific porting

### Getting Help

- **Examples**: See `examples/checkpointing/` in each language directory
- **API Docs**: Full API reference at [agenkit.dev/api](https://agenkit.dev/api)
- **Issues**: Report bugs at [github.com/scttfrdmn/agenkit/issues](https://github.com/scttfrdmn/agenkit/issues)
- **Discussions**: Ask questions at [github.com/scttfrdmn/agenkit/discussions](https://github.com/scttfrdmn/agenkit/discussions)

---

**Last Updated:** August 2026
**Applies to:** Agenkit v0.44.0+ (C#/Java/Scala baseline notes added in v0.89.0+, #879)
**Languages:** Python, Go, TypeScript, Rust, C++, Zig, C#, Java, Scala
