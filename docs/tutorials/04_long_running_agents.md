# Tutorial 4: Long-Running Agents and Checkpointing

An agent that runs a 30-hour autonomous research task needs to survive:

- **Process restarts** — the host machine reboots or the container is evicted.
- **Infrastructure failures** — the network drops or the storage backend is momentarily
  unavailable.
- **Intentional pauses** — the operator stops the job and resumes it later.

`DurableAgent` handles all three cases by automatically checkpointing session state
at a configurable interval and restoring it on the next startup.

---

## How checkpointing works

```
Process message N
        │
        ├─ Append message to session history
        ├─ Call inner agent.process()
        ├─ Append response to session history
        ├─ Update session state
        └─ If step % interval == 0: save Checkpoint JSON
                                         │
                                    checkpoint_id
                                    session_id
                                    step_number
                                    state dict
                                    message history

On restart (auto_resume=True):
        └─ Before first process(): load latest Checkpoint → restore state
```

Each checkpoint is a self-contained JSON snapshot. You can list checkpoints, restore
to a specific point in time, and diff states for debugging.

---

## Python

### Step 1 — Basic durable agent

```python
import asyncio
from agenkit import Agent, Message
from agenkit.checkpointing import DurableAgent, LocalCheckpointStorage


class ResearchAgent(Agent):
    """Simulates a long-running research task."""

    @property
    def name(self) -> str:
        return "research_agent"

    async def process(self, message: Message) -> Message:
        # In production, this calls an LLM, runs web searches, etc.
        step = message.metadata.get("step", "?")
        return Message(
            role="agent",
            content=f"Research result for step {step}: {message.content[:50]}",
        )


async def run_research_session(session_id: str, start_step: int) -> None:
    """Run or resume a research session."""
    inner = ResearchAgent()

    # LocalCheckpointStorage writes one JSON file per checkpoint under ./checkpoints/
    durable = DurableAgent(
        agent=inner,
        checkpoint_dir="./checkpoints",
        checkpoint_interval=10,   # save every 10 steps
        auto_resume=True,         # load latest checkpoint on first call
    )

    print(f"Starting session '{session_id}' from step {start_step}")

    for step in range(start_step, start_step + 5):
        msg = Message(
            role="user",
            content=f"Analyze topic: distributed systems at scale",
            metadata={"step": step, "session_id": session_id},
        )
        response = await durable.process(msg, session_id=session_id)
        print(f"  Step {step}: {response.content}")

    # Force a checkpoint before exit
    ckpt_id = await durable.checkpoint(session_id, metadata={"reason": "scheduled"})
    print(f"\nCheckpoint saved: {ckpt_id}")

    stats = await durable.get_session_stats(session_id)
    print(f"Session stats: steps={stats['current_step']}, "
          f"messages={stats['message_count']}, "
          f"checkpoints={stats.get('checkpoint_count', 0)}")


async def restore_and_resume(session_id: str) -> None:
    """Show how a new process restores from the latest checkpoint."""
    inner = ResearchAgent()

    # Create a brand-new DurableAgent — simulates a process restart
    durable = DurableAgent(
        agent=inner,
        checkpoint_dir="./checkpoints",
        checkpoint_interval=10,
        auto_resume=True,   # this is the key: loads latest checkpoint automatically
    )

    print(f"\nResuming session '{session_id}' after simulated restart...")

    # List checkpoints to understand what is available
    checkpoints = await durable.list_checkpoints(session_id)
    print(f"Found {len(checkpoints)} checkpoint(s)")
    if checkpoints:
        latest = checkpoints[0]
        print(f"Latest checkpoint: step={latest.step_number}, id={latest.checkpoint_id[:12]}...")

    # The first process() call triggers auto-resume
    msg = Message(
        role="user",
        content="Continue analysis from where we left off",
        metadata={"session_id": session_id},
    )
    response = await durable.process(msg, session_id=session_id)
    print(f"Resumed response: {response.content}")


async def main() -> None:
    session = "research-session-2026"

    # First "run" of the process
    await run_research_session(session, start_step=1)

    # Simulate a restart and resume
    await restore_and_resume(session)


if __name__ == "__main__":
    asyncio.run(main())
```

**Expected output:**

```
Starting session 'research-session-2026' from step 1
  Step 1: Research result for step 1: Analyze topic: distributed systems at scale
  Step 2: Research result for step 2: Analyze topic: distributed systems at scale
  Step 3: Research result for step 3: Analyze topic: distributed systems at scale
  Step 4: Research result for step 4: Analyze topic: distributed systems at scale
  Step 5: Research result for step 5: Analyze topic: distributed systems at scale

Checkpoint saved: ckpt-<uuid>
Session stats: steps=5, messages=10, checkpoints=1

Resuming session 'research-session-2026' after simulated restart...
Found 1 checkpoint(s)
Latest checkpoint: step=5, id=ckpt-<uuid-prefix>...
Resumed response: Research result for step ...
```

---

### Step 2 — Restore to a specific checkpoint

Sometimes you want to roll back to a particular point in time, not just the latest:

```python
import asyncio
from agenkit import Agent, Message
from agenkit.checkpointing import DurableAgent


async def time_travel_demo() -> None:
    inner = SimpleAgent()   # any Agent implementation

    durable = DurableAgent(
        agent=inner,
        checkpoint_dir="./checkpoints",
        checkpoint_interval=1,  # checkpoint after every step for this demo
    )

    session = "debug-session"
    checkpoint_ids: list[str] = []

    # Create a few checkpoints
    for i in range(1, 4):
        msg = Message(role="user", content=f"Step {i} input")
        await durable.process(msg, session_id=session)
        ckpt_id = await durable.checkpoint(session)
        checkpoint_ids.append(ckpt_id)
        print(f"Step {i}: checkpoint {ckpt_id[:12]}...")

    # Roll back to checkpoint from step 1
    state = await durable.resume(session, checkpoint_id=checkpoint_ids[0])
    print(f"\nRolled back to step-1 state: {state}")

    # Continue from the rolled-back state
    msg = Message(role="user", content="Continue from step 1")
    response = await durable.process(msg, session_id=session)
    print(f"Response after rollback: {response.content}")
```

---

### Step 3 — Storage backends

#### In-memory (testing only)

```python
from agenkit.checkpointing import DurableAgent, MemoryCheckpointStorage

# MemoryCheckpointStorage is the default when checkpoint_dir is None
durable = DurableAgent(agent=inner)  # no checkpoint_dir = in-memory
```

#### Local disk (single-machine production)

```python
from agenkit.checkpointing import DurableAgent

durable = DurableAgent(
    agent=inner,
    checkpoint_dir="./checkpoints",
    checkpoint_interval=10,
)
```

Directory layout created on disk:

```
./checkpoints/
  {session_id}/
    ckpt-<uuid1>.json
    ckpt-<uuid2>.json
    ...
```

Each JSON file is fully self-contained and human-readable — you can inspect or copy
them with standard shell tools.

---

## Go

### Basic durable agent with local storage

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/checkpointing"
)

// ResearchAgent simulates a long-running research task.
type ResearchAgent struct{}

func (a *ResearchAgent) Name() string { return "research_agent" }
func (a *ResearchAgent) Capabilities() []string { return nil }
func (a *ResearchAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *ResearchAgent) Process(
    _ context.Context, msg *agenkit.Message,
) (*agenkit.Message, error) {
    step, _ := msg.Metadata["step"].(int)
    content := msg.Content
    if len(content) > 50 {
        content = content[:50]
    }
    reply := fmt.Sprintf("Research result for step %d: %s", step, content)
    return agenkit.NewMessage("agent", reply), nil
}

func main() {
    ctx := context.Background()
    inner := &ResearchAgent{}

    // MakeDurableLocal creates LocalStorage and DurableAgent in one call.
    durable, err := checkpointing.MakeDurableLocal(
        inner,
        "./checkpoints", // directory for checkpoint JSON files
        10,              // checkpoint every 10 steps
        "",              // use inner.Name()
    )
    if err != nil {
        log.Fatalf("failed to create durable agent: %v", err)
    }

    session := "research-session-2026"

    fmt.Printf("Starting session '%s'\n", session)

    for step := 1; step <= 5; step++ {
        msg := agenkit.NewMessage("user", "Analyze distributed systems at scale")
        msg.Metadata["step"] = step

        response, err := durable.Process(ctx, msg, session)
        if err != nil {
            log.Fatalf("step %d failed: %v", step, err)
        }
        fmt.Printf("  Step %d: %s\n", step, response.Content)
    }

    // Manual checkpoint before exit
    ckptID, err := durable.Checkpoint(ctx, session, map[string]interface{}{
        "reason": "scheduled",
    })
    if err != nil {
        log.Fatalf("checkpoint failed: %v", err)
    }
    fmt.Printf("\nCheckpoint saved: %s\n", ckptID)

    // Simulate a restart: create a brand-new DurableAgent over the same directory
    fmt.Println("\nSimulating process restart...")

    durable2, err := checkpointing.MakeDurableLocal(inner, "./checkpoints", 10, "")
    if err != nil {
        log.Fatalf("restart failed: %v", err)
    }

    // auto_resume=true (default in MakeDurableLocal) loads the latest checkpoint
    msg := agenkit.NewMessage("user", "Continue from where we left off")
    response, err := durable2.Process(ctx, msg, session)
    if err != nil {
        log.Fatalf("resume failed: %v", err)
    }
    fmt.Printf("After restart: %s\n", response.Content)
}
```

### S3 storage (multi-machine production)

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/checkpointing"
)

func main() {
    ctx := context.Background()
    inner := &ResearchAgent{}  // defined above

    // MakeDurableS3 creates S3Storage and DurableAgent in one call.
    // Credentials come from the standard AWS credential chain
    // (environment variables, ~/.aws/credentials, EC2 instance role, etc.).
    durable, err := checkpointing.MakeDurableS3(
        ctx,
        inner,
        "my-checkpoints-bucket", // S3 bucket name
        "agents/research/",      // key prefix
        "us-west-2",             // AWS region
        "",                      // agent name override (empty = inner.Name())
        10,                      // checkpoint interval
    )
    if err != nil {
        log.Fatalf("failed to create S3 durable agent: %v", err)
    }

    session := "research-session-cloud"
    msg := agenkit.NewMessage("user", "Analyze cloud architectures")
    response, err := durable.Process(ctx, msg, session)
    if err != nil {
        log.Fatalf("process failed: %v", err)
    }
    fmt.Printf("Response: %s\n", response.Content)
}
```

### NFS storage (on-premises clusters)

```go
// MakeDurableNFS creates NFSStorage and DurableAgent.
// The NFS mount must already be mounted at mountPath before calling this.
durable, err := checkpointing.MakeDurableNFS(
    inner,
    "/mnt/nfs/checkpoints", // local mount path
    "nas01.corp.example",   // NFS host (informational, for URI)
    "/exports/checkpoints", // NFS export path (informational, for URI)
    "",                     // agent name override
    10,                     // checkpoint interval
)
```

---

## Choosing a storage backend

| Backend | Go constructor | Python class | Best for |
|---|---|---|---|
| In-memory | `NewMemoryStorage()` | `MemoryCheckpointStorage` | Unit tests |
| Local disk | `NewLocalStorage(dir)` / `MakeDurableLocal(...)` | `LocalCheckpointStorage` / `DurableAgent(checkpoint_dir=...)` | Single-machine production |
| Amazon S3 | `MakeDurableS3(...)` | *(planned)* | Multi-region, serverless |
| NFS | `MakeDurableNFS(...)` | *(planned)* | On-prem clusters, GPU farms |

---

## Checkpoint interval tuning

| Workload | Recommended interval | Rationale |
|---|---|---|
| Interactive chat | 1 | Low overhead; users expect continuity |
| Batch research | 10 | Balances I/O cost vs. lost work on failure |
| GPU training loops | 50–100 | Checkpointing is expensive; steps are fast |
| External API calls | 1 | Each call is expensive; never re-do it |

Rule of thumb: set the interval so that losing a checkpoint costs at most
5 minutes of work at your expected step rate.

---

## Next Steps

Continue to **[Tutorial 5: Multi-Agent Composition Patterns](./05_multi_agent.md)**
to learn how to chain, parallelize, and add fallback behaviour across multiple agents.
