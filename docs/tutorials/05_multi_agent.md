# Tutorial 5: Multi-Agent Composition Patterns

Single agents are powerful, but many real tasks benefit from multiple agents working
together. Agenkit ships three composition patterns:

| Pattern | Class | Use when |
|---|---|---|
| **Sequential** | `SequentialAgent` | Tasks have ordered stages; each stage transforms the previous output |
| **Parallel** | `ParallelAgent` | Independent sub-tasks that can run simultaneously |
| **Fallback** | `FallbackAgent` | Primary agent may fail; you need a backup |

All three implement the `Agent` interface, so they compose with each other and with
middleware decorators from Tutorial 3.

---

## Pattern 1: SequentialAgent

Output of agent N becomes the input to agent N+1.

**When to use:**
- ETL-style pipelines (validate → enrich → format)
- Multi-step reasoning (plan → research → write → review)
- Content moderation (detect language → translate → check policy)

### Python

```python
import asyncio
from agenkit import Agent, Message, SequentialAgent


class ValidatorAgent(Agent):
    """Rejects inputs that are too short."""

    @property
    def name(self) -> str:
        return "validator"

    async def process(self, message: Message) -> Message:
        text = str(message.content)
        if len(text.split()) < 3:
            return Message(
                role="agent",
                content="ERROR: input must be at least 3 words",
                metadata={"valid": False},
            )
        return Message(role="agent", content=text, metadata={"valid": True})


class EnricherAgent(Agent):
    """Appends word count and character count."""

    @property
    def name(self) -> str:
        return "enricher"

    async def process(self, message: Message) -> Message:
        if not message.metadata.get("valid", True):
            return message  # pass errors through unchanged

        text = str(message.content)
        words = len(text.split())
        chars = len(text)
        enriched = f"{text} [words={words}, chars={chars}]"
        return Message(
            role="agent",
            content=enriched,
            metadata={**message.metadata, "enriched": True},
        )


class FormatterAgent(Agent):
    """Formats the final result for display."""

    @property
    def name(self) -> str:
        return "formatter"

    async def process(self, message: Message) -> Message:
        text = str(message.content)
        if text.startswith("ERROR:"):
            return message
        return Message(
            role="agent",
            content=f"RESULT: {text.upper()}",
            metadata={**message.metadata, "formatted": True},
        )


async def main() -> None:
    pipeline = SequentialAgent(
        name="text_pipeline",
        agents=[ValidatorAgent(), EnricherAgent(), FormatterAgent()],
    )

    inputs = [
        "Hello world this is a test",  # valid
        "Hi",                           # too short
    ]

    for text in inputs:
        msg = Message(role="user", content=text)
        response = await pipeline.process(msg)
        print(f"Input : {text!r}")
        print(f"Output: {response.content!r}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
```

**Expected output:**

```
Input : 'Hello world this is a test'
Output: 'RESULT: HELLO WORLD THIS IS A TEST [WORDS=6, CHARS=26]'

Input : 'Hi'
Output: 'ERROR: input must be at least 3 words'
```

### Go

```go
package main

import (
    "context"
    "fmt"
    "strings"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/composition"
)

type ValidatorAgent struct{}

func (v *ValidatorAgent) Name() string { return "validator" }
func (v *ValidatorAgent) Capabilities() []string { return nil }
func (v *ValidatorAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(v)
}
func (v *ValidatorAgent) Process(
    _ context.Context, msg *agenkit.Message,
) (*agenkit.Message, error) {
    if len(strings.Fields(msg.Content)) < 3 {
        r := agenkit.NewMessage("agent", "ERROR: input must be at least 3 words")
        r.Metadata["valid"] = false
        return r, nil
    }
    r := agenkit.NewMessage("agent", msg.Content)
    r.Metadata["valid"] = true
    return r, nil
}

type EnricherAgent struct{}

func (e *EnricherAgent) Name() string { return "enricher" }
func (e *EnricherAgent) Capabilities() []string { return nil }
func (e *EnricherAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(e)
}
func (e *EnricherAgent) Process(
    _ context.Context, msg *agenkit.Message,
) (*agenkit.Message, error) {
    if valid, _ := msg.Metadata["valid"].(bool); !valid {
        return msg, nil
    }
    words := strings.Fields(msg.Content)
    enriched := fmt.Sprintf(
        "%s [words=%d, chars=%d]",
        msg.Content, len(words), len(msg.Content),
    )
    r := agenkit.NewMessage("agent", enriched)
    r.Metadata["enriched"] = true
    return r, nil
}

type FormatterAgent struct{}

func (f *FormatterAgent) Name() string { return "formatter" }
func (f *FormatterAgent) Capabilities() []string { return nil }
func (f *FormatterAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(f)
}
func (f *FormatterAgent) Process(
    _ context.Context, msg *agenkit.Message,
) (*agenkit.Message, error) {
    if strings.HasPrefix(msg.Content, "ERROR:") {
        return msg, nil
    }
    r := agenkit.NewMessage("agent", "RESULT: "+strings.ToUpper(msg.Content))
    return r, nil
}

func main() {
    ctx := context.Background()

    pipeline, err := composition.NewSequentialAgent(
        "text_pipeline",
        &ValidatorAgent{},
        &EnricherAgent{},
        &FormatterAgent{},
    )
    if err != nil {
        panic(err)
    }

    inputs := []string{
        "Hello world this is a test",
        "Hi",
    }

    for _, text := range inputs {
        msg := agenkit.NewMessage("user", text)
        response, err := pipeline.Process(ctx, msg)
        if err != nil {
            fmt.Printf("pipeline error: %v\n", err)
            continue
        }
        fmt.Printf("Input : %q\n", text)
        fmt.Printf("Output: %q\n\n", response.Content)
    }
}
```

---

## Pattern 2: ParallelAgent

All agents receive the same input simultaneously. Responses are combined into a single
message with each agent's output labeled `[agent-name]: ...`.

**When to use:**
- Fan-out aggregation (query multiple search APIs, combine results)
- Ensemble scoring (run several classifiers, take the majority vote)
- A/B testing (call two model versions, compare outputs)
- Latency reduction (independent sub-tasks that would otherwise run in sequence)

### Python

```python
import asyncio
from agenkit import Agent, Message, ParallelAgent


class SentimentAgent(Agent):
    """Classifies text sentiment (mock)."""

    @property
    def name(self) -> str:
        return "sentiment"

    async def process(self, message: Message) -> Message:
        text = str(message.content).lower()
        score = "positive" if any(w in text for w in ("good", "great", "love")) else "neutral"
        return Message(role="agent", content=f"Sentiment: {score}")


class KeywordAgent(Agent):
    """Extracts simple keywords (mock)."""

    @property
    def name(self) -> str:
        return "keywords"

    async def process(self, message: Message) -> Message:
        text = str(message.content)
        # Keep words longer than 4 characters as "keywords"
        keywords = [w for w in text.split() if len(w) > 4]
        return Message(role="agent", content=f"Keywords: {', '.join(keywords)}")


class SummaryAgent(Agent):
    """Produces a one-sentence summary (mock)."""

    @property
    def name(self) -> str:
        return "summary"

    async def process(self, message: Message) -> Message:
        text = str(message.content)
        first_sentence = text.split(".")[0].strip()
        return Message(role="agent", content=f"Summary: {first_sentence}")


async def main() -> None:
    # All three agents run concurrently
    ensemble = ParallelAgent(
        name="text_analysis",
        agents=[SentimentAgent(), KeywordAgent(), SummaryAgent()],
    )

    msg = Message(
        role="user",
        content=(
            "The product quality is great and I love the fast shipping. "
            "Will definitely order again."
        ),
    )

    response = await ensemble.process(msg)
    print("Combined analysis:")
    print(response.content)


if __name__ == "__main__":
    asyncio.run(main())
```

**Expected output:**

```
Combined analysis:
[sentiment]: Sentiment: positive
[keywords]: Keywords: product, quality, great, shipping, definitely, order, again
[summary]: Summary: The product quality is great and I love the fast shipping
```

### Go

```go
package main

import (
    "context"
    "fmt"
    "strings"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/composition"
)

type SentimentAgent struct{}

func (a *SentimentAgent) Name() string { return "sentiment" }
func (a *SentimentAgent) Capabilities() []string { return []string{"analysis"} }
func (a *SentimentAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *SentimentAgent) Process(
    _ context.Context, msg *agenkit.Message,
) (*agenkit.Message, error) {
    lower := strings.ToLower(msg.Content)
    score := "neutral"
    for _, word := range []string{"good", "great", "love"} {
        if strings.Contains(lower, word) {
            score = "positive"
            break
        }
    }
    return agenkit.NewMessage("agent", "Sentiment: "+score), nil
}

type KeywordAgent struct{}

func (a *KeywordAgent) Name() string { return "keywords" }
func (a *KeywordAgent) Capabilities() []string { return []string{"analysis"} }
func (a *KeywordAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *KeywordAgent) Process(
    _ context.Context, msg *agenkit.Message,
) (*agenkit.Message, error) {
    var keywords []string
    for _, w := range strings.Fields(msg.Content) {
        if len(w) > 4 {
            keywords = append(keywords, w)
        }
    }
    return agenkit.NewMessage("agent", "Keywords: "+strings.Join(keywords, ", ")), nil
}

func main() {
    ctx := context.Background()

    ensemble, err := composition.NewParallelAgent(
        "text_analysis",
        &SentimentAgent{},
        &KeywordAgent{},
    )
    if err != nil {
        panic(err)
    }

    msg := agenkit.NewMessage("user",
        "The product quality is great and I love the fast shipping.")

    response, err := ensemble.Process(ctx, msg)
    if err != nil {
        panic(err)
    }

    fmt.Println("Combined analysis:")
    fmt.Println(response.Content)
}
```

---

## Pattern 3: FallbackAgent

Tries agents in order. Returns the first successful response. If all agents fail,
raises an exception listing every failure.

**When to use:**
- Primary model is expensive; fall back to a cheaper model on error
- Multi-cloud redundancy (try AWS, fall back to GCP)
- Graceful degradation (try full answer, fall back to cached result)

### Python

```python
import asyncio
from agenkit import Agent, Message, FallbackAgent


class PrimaryLLMAgent(Agent):
    """Expensive primary model — may be rate-limited."""

    def __init__(self, healthy: bool = True) -> None:
        self._healthy = healthy

    @property
    def name(self) -> str:
        return "primary_llm"

    async def process(self, message: Message) -> Message:
        if not self._healthy:
            raise RuntimeError("rate limit exceeded")
        return Message(
            role="agent",
            content=f"[Primary] High-quality answer to: {message.content}",
        )


class BackupLLMAgent(Agent):
    """Cheaper backup model — always available."""

    @property
    def name(self) -> str:
        return "backup_llm"

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=f"[Backup] Basic answer to: {message.content}",
        )


class CacheAgent(Agent):
    """Returns a cached response — never fails."""

    @property
    def name(self) -> str:
        return "cache"

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content="[Cache] Sorry, I don't have a fresh answer. Please try again later.",
        )


async def demonstrate_fallback(primary_healthy: bool) -> None:
    router = FallbackAgent(
        name="resilient_agent",
        agents=[
            PrimaryLLMAgent(healthy=primary_healthy),
            BackupLLMAgent(),
            CacheAgent(),
        ],
    )

    msg = Message(role="user", content="What is the boiling point of water?")
    response = await router.process(msg)
    used = response.metadata.get("fallback_agent_used", "primary")
    attempt = response.metadata.get("fallback_attempt", 1)
    print(f"Primary healthy={primary_healthy}")
    print(f"  Used agent  : {used} (attempt {attempt})")
    print(f"  Response    : {response.content}")
    print()


async def main() -> None:
    # Case 1: primary is healthy — uses it directly
    await demonstrate_fallback(primary_healthy=True)

    # Case 2: primary is down — falls back to backup
    await demonstrate_fallback(primary_healthy=False)


if __name__ == "__main__":
    asyncio.run(main())
```

**Expected output:**

```
Primary healthy=True
  Used agent  : primary_llm (attempt 1)
  Response    : [Primary] High-quality answer to: What is the boiling point of water?

Primary healthy=False
  Used agent  : backup_llm (attempt 2)
  Response    : [Backup] Basic answer to: What is the boiling point of water?
```

### Go

```go
package main

import (
    "context"
    "errors"
    "fmt"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/composition"
)

type PrimaryLLMAgent struct{ Healthy bool }

func (a *PrimaryLLMAgent) Name() string { return "primary_llm" }
func (a *PrimaryLLMAgent) Capabilities() []string { return nil }
func (a *PrimaryLLMAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *PrimaryLLMAgent) Process(
    _ context.Context, msg *agenkit.Message,
) (*agenkit.Message, error) {
    if !a.Healthy {
        return nil, errors.New("rate limit exceeded")
    }
    return agenkit.NewMessage("agent", "[Primary] Answer to: "+msg.Content), nil
}

type BackupLLMAgent struct{}

func (a *BackupLLMAgent) Name() string { return "backup_llm" }
func (a *BackupLLMAgent) Capabilities() []string { return nil }
func (a *BackupLLMAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *BackupLLMAgent) Process(
    _ context.Context, msg *agenkit.Message,
) (*agenkit.Message, error) {
    return agenkit.NewMessage("agent", "[Backup] Answer to: "+msg.Content), nil
}

func runFallbackDemo(ctx context.Context, primaryHealthy bool) {
    router, err := composition.NewFallbackAgent(
        "resilient_agent",
        &PrimaryLLMAgent{Healthy: primaryHealthy},
        &BackupLLMAgent{},
    )
    if err != nil {
        panic(err)
    }

    msg := agenkit.NewMessage("user", "What is the boiling point of water?")
    response, err := router.Process(ctx, msg)
    if err != nil {
        fmt.Printf("Primary healthy=%v: all agents failed: %v\n", primaryHealthy, err)
        return
    }

    used, _ := response.Metadata["fallback_agent_used"].(string)
    attempt, _ := response.Metadata["fallback_attempt"].(int)
    fmt.Printf("Primary healthy=%v\n", primaryHealthy)
    fmt.Printf("  Used agent: %s (attempt %d)\n", used, attempt)
    fmt.Printf("  Response  : %s\n\n", response.Content)
}

func main() {
    ctx := context.Background()
    runFallbackDemo(ctx, true)   // primary healthy
    runFallbackDemo(ctx, false)  // primary down, uses backup
}
```

---

## Composing patterns

All three patterns implement `Agent`, so they compose freely:

```python
import asyncio
from agenkit import (
    Agent, Message,
    FallbackAgent, ParallelAgent, SequentialAgent,
)


async def composed_pipeline_example() -> None:
    """
    Pipeline: validate input → fan out to two analysis agents → format results.
    The analysis step uses a FallbackAgent so the primary can be swapped out.
    """

    # Step 1: validate
    validator = ValidatorAgent()   # defined earlier in this tutorial

    # Step 2: parallel analysis with a fallback for the keyword extractor
    keyword_with_fallback = FallbackAgent(
        name="keywords_resilient",
        agents=[KeywordAgent(), CacheAgent()],
    )
    analysis = ParallelAgent(
        name="analysis",
        agents=[SentimentAgent(), keyword_with_fallback],
    )

    # Step 3: format
    formatter = FormatterAgent()   # defined in Pattern 1

    # Combine into a sequential pipeline
    pipeline = SequentialAgent(
        name="full_pipeline",
        agents=[validator, analysis, formatter],
    )

    msg = Message(role="user", content="The great new product ships quickly")
    response = await pipeline.process(msg)
    print(f"Pipeline result: {response.content}")


if __name__ == "__main__":
    asyncio.run(composed_pipeline_example())
```

The same nesting works in Go — every composition type satisfies `agenkit.Agent`, so
you can pass any of them to `NewSequentialAgent`, `NewParallelAgent`, or
`NewFallbackAgent`.

---

## Pattern selection guide

```
Does the task have ordered stages where each stage needs the previous result?
  YES → SequentialAgent

Can the sub-tasks run at the same time and be merged afterwards?
  YES → ParallelAgent

Is there a primary agent that may fail, and you need a fallback?
  YES → FallbackAgent

Do you need all three?
  → Compose them. All three are Agents.
```

---

## Congratulations

You have completed the agenkit tutorial series. Here is what you covered:

| Tutorial | Key skill |
|---|---|
| [01 — Getting Started](./01_getting_started.md) | Build a minimal agent in all 6 languages |
| [02 — Memory and Context](./02_memory_and_context.md) | Multi-turn conversations and persistence |
| [03 — Production Patterns](./03_production_patterns.md) | Retry, circuit breaker, metrics, tracing |
| [04 — Long-Running Agents](./04_long_running_agents.md) | Checkpointing for 30-hour sessions |
| [05 — Multi-Agent Patterns](./05_multi_agent.md) | Sequential, parallel, and fallback composition |

**Further reading:**
- `docs/PATTERNS.md` — complete pattern catalogue
- `docs/observability.md` — full OpenTelemetry guide
- `docs/CHECKPOINTING.md` — advanced checkpoint management
- `examples/` — 27+ runnable examples across all languages
