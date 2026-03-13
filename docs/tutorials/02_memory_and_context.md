# Tutorial 2: Memory and Conversation Context

Stateless agents answer one question at a time. Real assistants remember what was said
three turns ago, recall the user's name, and pick up where they left off after a restart.
This tutorial shows you how to add memory to an agent in Python and Go.

---

## What you are building

A customer-support agent that:

1. Stores every conversation turn in `EphemeralMemory` (in-memory, no persistence).
2. Limits the context window with a `SlidingWindowStrategy` so long sessions do not
   overflow the model's token budget.
3. Persists conversation state to disk with `LocalCheckpointStorage` so the session
   survives a process restart.

---

## Core concepts

| Concept | Description |
|---|---|
| `EphemeralMemory` | In-process store. Fast, no I/O. Lost on restart. |
| `SlidingWindowStrategy` | Keeps the most-recent N messages for context. |
| `LocalCheckpointStorage` | Writes session state as JSON files under a directory. |
| `session_id` | Opaque string that identifies one conversation thread. |

---

## Python

### Step 1 — Basic multi-turn conversation

The simplest approach: manually track history as a list and pass it on every call.

```python
import asyncio
from agenkit import Agent, Message


class ChatAgent(Agent):
    """Stateful agent that remembers conversation history."""

    def __init__(self, system_prompt: str = "") -> None:
        self._history: list[Message] = []
        self._system_prompt = system_prompt

    @property
    def name(self) -> str:
        return "chat_agent"

    async def process(self, message: Message) -> Message:
        # Append the incoming user turn
        self._history.append(message)

        # Build context: system prompt + last 10 turns
        context_window = self._history[-10:]
        context = "\n".join(
            f"{m.role}: {m.content}" for m in context_window
        )
        if self._system_prompt:
            context = f"System: {self._system_prompt}\n{context}"

        # In production this is where you call your LLM.
        # Here we echo the context length as a stand-in.
        reply_text = (
            f"I see {len(context_window)} message(s) in context. "
            f"You said: {message.content}"
        )
        reply = Message(role="agent", content=reply_text)
        self._history.append(reply)
        return reply

    def clear_history(self) -> None:
        """Reset conversation — useful at session boundaries."""
        self._history.clear()


async def main() -> None:
    agent = ChatAgent(system_prompt="You are a helpful support agent.")

    turns = [
        "Hi, my order hasn't arrived yet.",
        "My order number is 98765.",
        "It was supposed to arrive yesterday.",
    ]

    for user_text in turns:
        msg = Message(role="user", content=user_text)
        response = await agent.process(msg)
        print(f"User : {user_text}")
        print(f"Agent: {response.content}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
```

**Expected output (abbreviated):**

```
User : Hi, my order hasn't arrived yet.
Agent: I see 1 message(s) in context. You said: Hi, my order hasn't arrived yet.

User : My order number is 98765.
Agent: I see 3 message(s) in context. You said: My order number is 98765.
```

---

### Step 2 — Using `EphemeralMemory` and `SlidingWindowStrategy`

For production agents you want storage decoupled from the agent so multiple agent
instances (or test code) can share the same session data.

```python
import asyncio
from agenkit import Agent, Message
from agenkit.memory import EphemeralMemory, SlidingWindowStrategy


class MemoryBackedAgent(Agent):
    """Agent that delegates history storage to EphemeralMemory."""

    def __init__(self, max_history: int = 20) -> None:
        self._memory = EphemeralMemory(max_size=max_history)
        self._strategy = SlidingWindowStrategy(window_size=10)

    @property
    def name(self) -> str:
        return "memory_agent"

    async def process(self, message: Message) -> Message:
        session_id = str(message.metadata.get("session_id", "default"))

        # Persist the incoming message
        await self._memory.store(session_id, message)

        # Retrieve context using the sliding-window strategy
        context_msgs = await self._strategy.select(
            self._memory, session_id, context_limit=10
        )
        context = "\n".join(f"{m.role}: {m.content}" for m in context_msgs)

        # (Replace this with an actual LLM call in production.)
        reply_text = (
            f"Context has {len(context_msgs)} message(s). "
            f"You said: {message.content}"
        )
        reply = Message(
            role="agent",
            content=reply_text,
            metadata={"session_id": session_id},
        )

        # Persist the reply too
        await self._memory.store(session_id, reply)
        return reply

    async def clear_session(self, session_id: str) -> None:
        """Drop all memory for a session."""
        await self._memory.clear(session_id)


async def main() -> None:
    agent = MemoryBackedAgent(max_history=50)
    session = "support-session-001"

    questions = [
        "What is your return policy?",
        "Can I return a digital download?",
        "How long does a refund take?",
    ]

    for text in questions:
        msg = Message(
            role="user",
            content=text,
            metadata={"session_id": session},
        )
        response = await agent.process(msg)
        print(f"User : {text}")
        print(f"Agent: {response.content}")
        print()

    # Clear just this session when done
    await agent.clear_session(session)
    print("Session cleared.")


if __name__ == "__main__":
    asyncio.run(main())
```

---

### Step 3 — Persisting context to disk

Swap `EphemeralMemory` for `LocalCheckpointStorage` when you need sessions that
survive process restarts.

```python
import asyncio
from agenkit import Agent, Message
from agenkit.checkpointing import DurableAgent, LocalCheckpointStorage


class SimpleAgent(Agent):
    @property
    def name(self) -> str:
        return "simple_agent"

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=f"Acknowledged: {message.content}",
        )


async def demonstrate_persistence() -> None:
    inner_agent = SimpleAgent()

    # LocalCheckpointStorage writes JSON files under ./checkpoints/
    durable = DurableAgent(
        agent=inner_agent,
        checkpoint_dir="./checkpoints",
        checkpoint_interval=5,   # auto-checkpoint every 5 steps
        auto_resume=True,        # resume latest checkpoint on first call
    )

    session = "user-42"

    # First run: process a few messages
    for i in range(1, 4):
        msg = Message(role="user", content=f"Message {i}")
        response = await durable.process(msg, session_id=session)
        print(f"Step {i}: {response.content}")

    # Manually save a checkpoint
    ckpt_id = await durable.checkpoint(session)
    print(f"\nCheckpoint saved: {ckpt_id}")

    # Simulate a restart: create a new DurableAgent over the same directory
    durable2 = DurableAgent(
        agent=inner_agent,
        checkpoint_dir="./checkpoints",
        checkpoint_interval=5,
        auto_resume=True,
    )

    # auto_resume=True means the first process() call loads the latest checkpoint
    msg = Message(role="user", content="Are you still there after the restart?")
    response = await durable2.process(msg, session_id=session)
    print(f"\nAfter restart: {response.content}")

    stats = await durable2.get_session_stats(session)
    print(f"Session stats: {stats}")


if __name__ == "__main__":
    asyncio.run(demonstrate_persistence())
```

---

## Go

### Multi-turn conversation with `EphemeralMemory`

```go
package main

import (
    "context"
    "fmt"
    "strings"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/memory"
)

// SupportAgent holds conversation state in EphemeralMemory.
type SupportAgent struct {
    mem      *memory.EphemeralMemory
    strategy *memory.SlidingWindowStrategy
}

func NewSupportAgent() *SupportAgent {
    return &SupportAgent{
        mem:      memory.NewEphemeralMemory(200),
        strategy: memory.NewSlidingWindowStrategy(10),
    }
}

func (a *SupportAgent) Name() string { return "support_agent" }

func (a *SupportAgent) Capabilities() []string { return []string{"support", "memory"} }

func (a *SupportAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}

func (a *SupportAgent) Process(
    ctx context.Context,
    message *agenkit.Message,
) (*agenkit.Message, error) {
    sessionID, _ := message.Metadata["session_id"].(string)
    if sessionID == "" {
        sessionID = "default"
    }

    // Store incoming message
    if err := a.mem.Store(ctx, sessionID, *message, nil); err != nil {
        return nil, fmt.Errorf("memory store: %w", err)
    }

    // Retrieve context window
    limit := 10
    history, err := a.mem.Retrieve(ctx, sessionID, memory.RetrieveOptions{Limit: &limit})
    if err != nil {
        return nil, fmt.Errorf("memory retrieve: %w", err)
    }

    // Build context string (replace with real LLM call in production)
    var sb strings.Builder
    for _, m := range history {
        sb.WriteString(fmt.Sprintf("%s: %s\n", m.Role, m.Content))
    }

    replyText := fmt.Sprintf(
        "Context has %d message(s). You said: %s",
        len(history),
        message.Content,
    )

    reply := agenkit.NewMessage("agent", replyText)
    reply.Metadata["session_id"] = sessionID

    // Store the reply too
    if err := a.mem.Store(ctx, sessionID, *reply, nil); err != nil {
        return nil, fmt.Errorf("memory store reply: %w", err)
    }

    return reply, nil
}

func main() {
    ctx := context.Background()
    agent := NewSupportAgent()
    session := "support-session-001"

    questions := []string{
        "What is your return policy?",
        "Can I return a digital download?",
        "How long does a refund take?",
    }

    for _, q := range questions {
        msg := agenkit.NewMessage("user", q)
        msg.Metadata["session_id"] = session

        response, err := agent.Process(ctx, msg)
        if err != nil {
            panic(err)
        }

        fmt.Printf("User : %s\n", q)
        fmt.Printf("Agent: %s\n\n", response.Content)
    }
}
```

### Persisting context with `LocalStorage`

```go
package main

import (
    "context"
    "fmt"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/checkpointing"
)

type EchoAgent struct{}

func (e *EchoAgent) Name() string { return "echo" }
func (e *EchoAgent) Capabilities() []string { return nil }
func (e *EchoAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(e)
}
func (e *EchoAgent) Process(
    _ context.Context, msg *agenkit.Message,
) (*agenkit.Message, error) {
    return agenkit.NewMessage("agent", "Acknowledged: "+msg.Content), nil
}

func main() {
    ctx := context.Background()
    inner := &EchoAgent{}

    storage := checkpointing.NewLocalStorage("./checkpoints")
    durable := checkpointing.NewDurableAgent(
        inner,
        storage,
        5,    // checkpoint every 5 steps
        true, // auto-resume on first Process call
        "",   // use agent.Name()
    )

    session := "user-42"

    // First run
    for i := 1; i <= 3; i++ {
        msg := agenkit.NewMessage("user", fmt.Sprintf("Message %d", i))
        response, err := durable.Process(ctx, msg, session)
        if err != nil {
            panic(err)
        }
        fmt.Printf("Step %d: %s\n", i, response.Content)
    }

    // Manual checkpoint
    ckptID, err := durable.Checkpoint(ctx, session, nil)
    if err != nil {
        panic(err)
    }
    fmt.Printf("\nCheckpoint saved: %s\n", ckptID)

    // Simulate restart with a fresh DurableAgent over the same directory
    storage2 := checkpointing.NewLocalStorage("./checkpoints")
    durable2 := checkpointing.NewDurableAgent(inner, storage2, 5, true, "")

    msg := agenkit.NewMessage("user", "Still there after restart?")
    response, err := durable2.Process(ctx, msg, session)
    if err != nil {
        panic(err)
    }
    fmt.Printf("\nAfter restart: %s\n", response.Content)
}
```

---

## Choosing a storage backend

| Backend | Class | When to use |
|---|---|---|
| In-process | `EphemeralMemory` / `MemoryStorage` | Testing, ephemeral sessions |
| Local disk | `LocalCheckpointStorage` / `LocalStorage` | Single-machine production |
| Amazon S3 | `S3Storage` (Go) | Multi-region, serverless |
| NFS mount | `NFSStorage` (Go) | On-prem clusters |

---

## Key takeaways

- `EphemeralMemory.store()` / `retrieve()` decouples history management from agent logic.
- `SlidingWindowStrategy` prevents context overflow without losing recent turns.
- `DurableAgent` wraps any `Agent` and adds automatic checkpointing — your agent code
  does not change at all.
- Set `auto_resume=True` (Python) / `autoResume: true` (Go) so a restarted agent
  picks up the session automatically.

---

## Next Steps

Continue to **[Tutorial 3: Production Patterns](./03_production_patterns.md)** to
learn how to harden your agent with retry logic, a circuit breaker, and observability.
