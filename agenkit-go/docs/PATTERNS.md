# Agenkit Go Agent Patterns Guide

A comprehensive guide to the 11 agent patterns in Agenkit-Go.

## Table of Contents

- [Overview](#overview)
- [Pattern Comparison](#pattern-comparison)
- [Composition Patterns](#composition-patterns)
  - [Sequential](#sequential)
  - [Parallel](#parallel)
- [Enhancement Patterns](#enhancement-patterns)
  - [Reflection](#reflection)
  - [ReAct](#react)
  - [Planning](#planning)
- [Specialized Patterns](#specialized-patterns)
  - [Task](#task)
  - [Conversational](#conversational)
  - [AgentsAsTools](#agentsastools)
- [Advanced Patterns](#advanced-patterns)
  - [Autonomous](#autonomous)
  - [Multiagent](#multiagent)
  - [MemoryHierarchy](#memoryhierarchy)
- [Pattern Selection Guide](#pattern-selection-guide)
- [Composing Patterns](#composing-patterns)

---

## Overview

Agent patterns are reusable architectural templates that solve common problems in AI agent design. Agenkit provides 11 production-ready patterns you can use immediately or combine for complex workflows.

### Why Patterns Matter

1. **Proven Solutions** - Patterns encode best practices from production systems
2. **Composability** - Patterns compose naturally because they all implement `agenkit.Agent`
3. **Performance** - Go's goroutines make parallel patterns genuinely concurrent
4. **Idiomatic** - Each pattern follows Go conventions: context propagation, error returns, interface composition

### Pattern Categories

- **Composition** (Sequential, Parallel) - Combine multiple agents
- **Enhancement** (Reflection, ReAct, Planning) - Improve agent quality
- **Specialized** (Task, Conversational, AgentsAsTools) - Domain-specific patterns
- **Advanced** (Autonomous, Multiagent, MemoryHierarchy) - Complex behaviors

---

## Pattern Comparison

| Pattern | Complexity | Use Case | Performance | Best For |
|---------|-----------|----------|-------------|----------|
| Sequential | Low | Data pipelines | Fast | Multi-stage processing |
| Parallel | Medium | Independent tasks | Very Fast (goroutines) | Concurrent operations |
| Reflection | Medium | Quality improvement | Slow (iterative) | Self-correction |
| ReAct | Medium | Reasoning + tools | Medium | Decision-making |
| Planning | High | Complex tasks | Slow (planning overhead) | Multi-step workflows |
| Task | Low | Job execution | Fast | Single-purpose agents |
| Conversational | Medium | Dialogue | Fast | Chatbots |
| AgentsAsTools | High | Orchestration | Medium | Tool delegation |
| Autonomous | Very High | Goal pursuit | Slow (iterative) | Self-directed agents |
| Multiagent | Very High | Collaboration | Medium | Multi-agent systems |
| MemoryHierarchy | High | Context management | Medium | Long-running agents |

---

## Composition Patterns

### Sequential

**Purpose:** Process messages through multiple agents in order. The output of each agent becomes the input to the next.

**When to Use:**
- Data transformation pipelines
- Multi-stage validation (validate → sanitize → enrich)
- Step-by-step processing where order matters
- When output of agent N must feed into agent N+1

**ASCII Diagram:**

```
Input → Agent1 → Agent2 → Agent3 → Output
```

**Implementation:**

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// ValidationAgent ensures input meets requirements.
type ValidationAgent struct{}

func (a *ValidationAgent) Name() string { return "validator" }
func (a *ValidationAgent) Capabilities() []string { return []string{"validation"} }
func (a *ValidationAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *ValidationAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    if msg.Content == "" {
        return nil, fmt.Errorf("validation failed: empty content")
    }
    return msg, nil // pass through on success
}

// ProcessingAgent transforms the content.
type ProcessingAgent struct{}

func (a *ProcessingAgent) Name() string { return "processor" }
func (a *ProcessingAgent) Capabilities() []string { return []string{"processing"} }
func (a *ProcessingAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *ProcessingAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    processed := "PROCESSED: " + msg.ContentString()
    return agenkit.NewMessage("assistant", processed), nil
}

// FormattingAgent formats the final output.
type FormattingAgent struct{}

func (a *FormattingAgent) Name() string { return "formatter" }
func (a *FormattingAgent) Capabilities() []string { return []string{"formatting"} }
func (a *FormattingAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *FormattingAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    formatted := fmt.Sprintf("[%s]", msg.Content)
    return agenkit.NewMessage("assistant", formatted), nil
}

func main() {
    ctx := context.Background()

    // Build pipeline: validate → process → format
    pipeline := patterns.NewSequentialAgent([]agenkit.Agent{
        &ValidationAgent{},
        &ProcessingAgent{},
        &FormattingAgent{},
    })

    msg := agenkit.NewMessage("user", "hello world")
    result, err := pipeline.Process(ctx, msg)
    if err != nil {
        log.Fatalf("pipeline failed: %v", err)
    }

    fmt.Println(result.Content)
    // Output: [PROCESSED: hello world]
}
```

**Trade-offs:**

| Pros | Cons |
|------|------|
| Simple mental model | Sequential only - no parallelism |
| Clear data flow | Failure stops the pipeline |
| Easy to debug | Latency adds up across stages |
| Composable with other patterns | |

---

### Parallel

**Purpose:** Execute multiple agents concurrently using goroutines and aggregate their results.

**When to Use:**
- Independent analyses of the same input
- Fan-out processing (analyze from multiple perspectives)
- Gathering data from multiple sources simultaneously
- When tasks have no dependencies on each other

**ASCII Diagram:**

```
         ┌→ Agent1 ─────┐
         │              │
Input ───┼→ Agent2 ─────┼→ Aggregator → Output
         │              │
         └→ Agent3 ─────┘
```

**Implementation:**

```go
package main

import (
    "context"
    "fmt"
    "log"
    "strings"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

type SentimentAgent struct{}

func (a *SentimentAgent) Name() string { return "sentiment" }
func (a *SentimentAgent) Capabilities() []string { return []string{"sentiment-analysis"} }
func (a *SentimentAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *SentimentAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    // Real implementation would use an LLM
    return agenkit.NewMessage("assistant", "sentiment: positive"), nil
}

type TopicAgent struct{}

func (a *TopicAgent) Name() string { return "topic" }
func (a *TopicAgent) Capabilities() []string { return []string{"topic-classification"} }
func (a *TopicAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *TopicAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    return agenkit.NewMessage("assistant", "topic: technology"), nil
}

type SummaryAgent struct{}

func (a *SummaryAgent) Name() string { return "summary" }
func (a *SummaryAgent) Capabilities() []string { return []string{"summarization"} }
func (a *SummaryAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *SummaryAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    summary := fmt.Sprintf("summary: %s...", msg.Content[:min(20, len(msg.Content))])
    return agenkit.NewMessage("assistant", summary), nil
}

func min(a, b int) int {
    if a < b {
        return a
    }
    return b
}

// Custom aggregator combines all responses.
func combineResponses(responses []*agenkit.Message) (*agenkit.Message, error) {
    parts := make([]string, 0, len(responses))
    for _, r := range responses {
        parts = append(parts, r.Content)
    }
    combined := strings.Join(parts, " | ")
    return agenkit.NewMessage("assistant", combined), nil
}

func main() {
    ctx := context.Background()

    // All three agents run concurrently
    parallel := patterns.NewParallelAgent([]agenkit.Agent{
        &SentimentAgent{},
        &TopicAgent{},
        &SummaryAgent{},
    }, combineResponses) // custom aggregator

    msg := agenkit.NewMessage("user", "Go 1.22 was released with exciting new features")
    result, err := parallel.Process(ctx, msg)
    if err != nil {
        log.Fatalf("parallel processing failed: %v", err)
    }

    fmt.Println(result.Content)
    // Output: sentiment: positive | topic: technology | summary: Go 1.22 was releas...
}
```

**Goroutine Safety:**

Each agent in a `ParallelAgent` runs in its own goroutine. Your agents must be safe for concurrent use. Stateless agents are safe by default; stateful agents need synchronization:

```go
import "sync"

type CountingAgent struct {
    mu    sync.Mutex
    count int
}

func (a *CountingAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    a.mu.Lock()
    a.count++
    c := a.count
    a.mu.Unlock()
    return agenkit.NewMessage("assistant", fmt.Sprintf("count: %d", c)), nil
}
```

**Trade-offs:**

| Pros | Cons |
|------|------|
| True parallelism with goroutines | All agents must be goroutine-safe |
| Reduced total latency | Aggregation logic required |
| Independent failures don't block others | Memory usage scales with agents |
| Natural Go idiom | Order of results is non-deterministic |

---

## Enhancement Patterns

### Reflection

**Purpose:** Iteratively improve output through a draft-critique-refine loop.

**When to Use:**
- Quality-critical outputs (reports, code, plans)
- Self-correction of initial drafts
- When the first attempt is unlikely to be optimal
- Situations where explicit criteria for "good" exist

**ASCII Diagram:**

```
         ┌─────────────────────────────┐
         │                             │
Input → Draft → Critique → Meets criteria? ─Yes→ Output
                              │No
                              └→ Revise → Draft (again)
```

**Implementation:**

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

func main() {
    ctx := context.Background()

    // myLLM implements agenkit.Agent
    reflective := patterns.NewReflectionAgent(&patterns.ReflectionConfig{
        BaseAgent:      myLLM,
        MaxIterations:  3,
        CritiquePrompt: "Review this response. List any improvements needed. If it is satisfactory, say APPROVED.",
    })

    msg := agenkit.NewMessage("user", "Explain context.Context in Go")
    result, err := reflective.Process(ctx, msg)
    if err != nil {
        log.Fatalf("reflection failed: %v", err)
    }

    fmt.Println(result.Content)
    fmt.Printf("Iterations: %v\n", result.Metadata["iterations"])
}
```

**Trade-offs:**

| Pros | Cons |
|------|------|
| Significantly improves output quality | Multiple LLM calls increase cost and latency |
| Explicit improvement criteria | Risk of oscillation without convergence |
| Works with any LLM | Needs thoughtful critique prompt |
| Self-contained improvement | Not suitable for real-time applications |

---

### ReAct

**Purpose:** Interleave reasoning (Thought) with action (Tool call) and observation (Tool result) in a loop.

**When to Use:**
- Tasks requiring external information
- Multi-step problem solving with tools
- Situations where reasoning must precede action
- When you want explainable decision-making

**ASCII Diagram:**

```
Input → Thought → Action → Observation → Thought → ... → Final Answer
```

**Implementation:**

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// WeatherTool retrieves current weather data.
type WeatherTool struct{}

func (t *WeatherTool) Name() string { return "get_weather" }

func (t *WeatherTool) Description() string {
    return "Get the current weather for a city"
}

func (t *WeatherTool) Parameters() map[string]interface{} {
    return map[string]interface{}{
        "city": map[string]interface{}{
            "type":        "string",
            "description": "The city name",
        },
    }
}

func (t *WeatherTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
    city, ok := params["city"].(string)
    if !ok {
        return nil, fmt.Errorf("missing required parameter: city")
    }
    // Real implementation would call a weather API
    return agenkit.NewToolResult(fmt.Sprintf("Weather in %s: 22°C, sunny", city)), nil
}

// CalculatorTool evaluates math expressions.
type CalculatorTool struct{}

func (t *CalculatorTool) Name() string { return "calculator" }

func (t *CalculatorTool) Description() string {
    return "Evaluate a mathematical expression"
}

func (t *CalculatorTool) Parameters() map[string]interface{} {
    return map[string]interface{}{
        "expression": map[string]interface{}{
            "type":        "string",
            "description": "The math expression to evaluate",
        },
    }
}

func (t *CalculatorTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
    expr, ok := params["expression"].(string)
    if !ok {
        return nil, fmt.Errorf("missing required parameter: expression")
    }
    // Real implementation would evaluate the expression
    return agenkit.NewToolResult(fmt.Sprintf("Result of %s = 42", expr)), nil
}

func main() {
    ctx := context.Background()

    react := patterns.NewReActAgent(&patterns.ReActConfig{
        LLM: myLLM,
        Tools: []agenkit.Tool{
            &WeatherTool{},
            &CalculatorTool{},
        },
        MaxIterations: 5,
    })

    msg := agenkit.NewMessage("user", "What's the weather in Tokyo and Berlin?")
    result, err := react.Process(ctx, msg)
    if err != nil {
        log.Fatalf("react agent failed: %v", err)
    }

    fmt.Println(result.Content)
    steps := result.Metadata["steps"].([]string)
    fmt.Printf("Completed in %d steps\n", len(steps))
}
```

**Trade-offs:**

| Pros | Cons |
|------|------|
| Handles complex multi-step tasks | More LLM calls than simple patterns |
| Explainable reasoning chain | Loop can run many iterations |
| Flexible tool composition | Tool execution errors can cascade |
| Natural for tool-using agents | Requires well-designed tool interfaces |

---

### Planning

**Purpose:** Decompose a complex goal into a plan of subtasks, then execute them.

**When to Use:**
- Complex goals requiring multiple coordinated steps
- When the sequence of actions must be determined upfront
- Tasks with dependencies between steps
- Long-horizon reasoning

**ASCII Diagram:**

```
Input → Planner → [Step1, Step2, Step3] → Execute(Step1) → Execute(Step2) → Execute(Step3) → Output
```

**Implementation:**

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

func main() {
    ctx := context.Background()

    planner := patterns.NewPlanningAgent(&patterns.PlanningConfig{
        Planner:  plannerLLM,  // Responsible for task decomposition
        Executor: executorLLM, // Responsible for executing each step
        MaxSteps: 10,
    })

    msg := agenkit.NewMessage("user", "Write a blog post about Go generics with code examples")
    result, err := planner.Process(ctx, msg)
    if err != nil {
        log.Fatalf("planning agent failed: %v", err)
    }

    fmt.Println(result.Content)
    plan := result.Metadata["plan"].([]string)
    fmt.Printf("Executed plan:\n")
    for i, step := range plan {
        fmt.Printf("  %d. %s\n", i+1, step)
    }
}
```

**Trade-offs:**

| Pros | Cons |
|------|------|
| Handles arbitrarily complex tasks | High latency (plan then execute) |
| Clear task decomposition | Planning can be incorrect |
| Good for long-horizon goals | Hard to adapt plan mid-execution |
| Separates strategy from execution | Requires capable planning LLM |

---

## Specialized Patterns

### Task

**Purpose:** A single-purpose agent that wraps a specific function. Useful for creating tool-like agents.

**When to Use:**
- Wrapping a specific function as an agent
- Single-responsibility agents
- Integrating external services
- Creating testable, composable building blocks

**Implementation:**

```go
package main

import (
    "context"
    "fmt"
    "strings"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

func main() {
    ctx := context.Background()

    // Wrap a function as an agent
    upperCaseAgent := patterns.NewTaskAgent(&patterns.TaskConfig{
        Name:        "uppercase",
        Description: "Converts text to uppercase",
        Handler: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
            return agenkit.NewMessage("assistant", strings.ToUpper(msg.ContentString())), nil
        },
    })

    wordCountAgent := patterns.NewTaskAgent(&patterns.TaskConfig{
        Name:        "word-counter",
        Description: "Counts words in text",
        Handler: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
            words := strings.Fields(msg.ContentString())
            return agenkit.NewMessage("assistant", fmt.Sprintf("%d words", len(words))), nil
        },
    })

    msg := agenkit.NewMessage("user", "hello world from Go")
    upper, _ := upperCaseAgent.Process(ctx, msg)
    count, _ := wordCountAgent.Process(ctx, msg)

    fmt.Println(upper.Content) // HELLO WORLD FROM GO
    fmt.Println(count.Content) // 4 words
}
```

---

### Conversational

**Purpose:** Maintain multi-turn dialogue by keeping conversation history.

**When to Use:**
- Chatbots and interactive assistants
- Context-dependent conversations (where follow-up questions reference prior answers)
- Scenarios requiring dialogue state management
- Any interaction that spans multiple exchanges

**Implementation:**

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
    "github.com/scttfrdmn/agenkit/agenkit-go/adapter"
)

func main() {
    ctx := context.Background()

    llm, err := adapter.NewAnthropicAdapter(
        os.Getenv("ANTHROPIC_API_KEY"),
        adapter.WithModel("claude-3-5-sonnet-20241022"),
    )
    if err != nil {
        log.Fatalf("failed to create LLM: %v", err)
    }

    conv := patterns.NewConversationalAgent(&patterns.ConversationalConfig{
        LLM:          llm,
        SystemPrompt: "You are a Go programming expert. Be concise.",
        MaxHistory:   20,
    })

    exchanges := []string{
        "What is a goroutine?",
        "How is it different from a thread?",
        "Can you show me an example?",
    }

    for _, question := range exchanges {
        msg := agenkit.NewMessage("user", question)
        response, err := conv.Process(ctx, msg)
        if err != nil {
            log.Fatalf("conversation error: %v", err)
        }
        fmt.Printf("User: %s\n", question)
        fmt.Printf("Agent: %s\n\n", response.Content)
    }
    // The agent maintains context across all three exchanges.
}
```

**History Management:**

`MaxHistory` controls how many messages are kept in the active context. Older messages are dropped when the limit is exceeded. For longer memory, combine with `MemoryHierarchyAgent`.

---

### AgentsAsTools

**Purpose:** An orchestrating agent that can delegate to specialized sub-agents as if they were tools.

**When to Use:**
- Routing tasks to specialized agents
- Building agent hierarchies
- Capability composition without hard-coding dependencies
- Multi-domain assistants

**ASCII Diagram:**

```
                      ┌→ CalculatorAgent
User → Orchestrator ──┼→ SearchAgent
                      └→ CodeAgent
```

**Implementation:**

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

func main() {
    ctx := context.Background()

    orchestrator := patterns.NewAgentsAsToolsAgent(&patterns.AgentsAsToolsConfig{
        Orchestrator: myLLM, // Decides which sub-agent to call
        SubAgents: map[string]agenkit.Agent{
            "calculator": &CalculatorAgent{},
            "search":     &SearchAgent{},
            "code":       &CodeReviewAgent{},
        },
    })

    msg := agenkit.NewMessage("user", "Calculate 15 * 24 and search for the Go 1.22 release notes")
    result, err := orchestrator.Process(ctx, msg)
    if err != nil {
        log.Fatalf("orchestration failed: %v", err)
    }

    fmt.Println(result.Content)
}
```

---

## Advanced Patterns

### Autonomous

**Purpose:** A self-directed agent that pursues a goal across many steps without per-step human instruction.

**When to Use:**
- Long-running autonomous tasks
- Open-ended goals
- Tasks requiring adaptive decision-making
- Research, writing, or coding workflows

**ASCII Diagram:**

```
Goal → Plan → Act → Observe → Goal achieved? → Output
                 ↑                  │No
                 └──────────────────┘
```

**Implementation:**

```go
package main

import (
    "context"
    "fmt"
    "log"
    "strings"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

func main() {
    ctx := context.Background()

    auto := patterns.NewAutonomousAgent(&patterns.AutonomousConfig{
        BaseAgent: myLLM,
        Goal:      "Research Go 1.22 and write a summary of the top 3 new features",
        MaxSteps:  15,
        StopCriteria: func(resp *agenkit.Message) bool {
            // Stop when agent signals completion
            return strings.Contains(resp.ContentString(), "TASK_COMPLETE")
        },
    })

    result, err := auto.Process(ctx, agenkit.NewMessage("user", "begin"))
    if err != nil {
        log.Fatalf("autonomous agent failed: %v", err)
    }

    fmt.Printf("Result:\n%s\n", result.Content)
    fmt.Printf("Steps taken: %v\n", result.Metadata["steps_taken"])
}
```

**Safety Considerations:**

- Always set `MaxSteps` to prevent runaway loops
- Define clear `StopCriteria`
- Use `context.WithTimeout` to bound wall-clock time
- Audit logs are highly recommended for autonomous agents

---

### Multiagent

**Purpose:** Coordinate multiple specialized agents to collaborate on a task.

**When to Use:**
- Tasks requiring multiple domains of expertise
- Situations where agents critique each other's work
- Distributed problem solving
- Simulations requiring multiple perspectives

**ASCII Diagram:**

```
                  ┌→ ResearchAgent ─┐
User → Coordinator┼→ WriterAgent    ├→ Synthesis → Output
                  └→ EditorAgent   ─┘
```

**Implementation:**

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

func main() {
    ctx := context.Background()

    system := patterns.NewMultiagentSystem(&patterns.MultiagentConfig{
        Coordinator: coordinatorLLM, // Decides which agent to invoke
        Agents: map[string]agenkit.Agent{
            "researcher": &ResearchAgent{},
            "writer":     &WritingAgent{},
            "editor":     &EditingAgent{},
        },
        MaxRounds: 5,
    })

    msg := agenkit.NewMessage("user", "Write a technical blog post about Go's new range-over-integers feature")
    result, err := system.Process(ctx, msg)
    if err != nil {
        log.Fatalf("multiagent system failed: %v", err)
    }

    fmt.Println(result.Content)
    rounds := result.Metadata["rounds"].(int)
    fmt.Printf("Completed in %d coordination rounds\n", rounds)
}
```

---

### MemoryHierarchy

**Purpose:** Manage memory across three tiers: working (immediate context), short-term (recent interactions), and long-term (persistent storage).

**When to Use:**
- Long-running conversational agents
- Agents that need to remember facts across sessions
- Optimizing context window usage
- Personalized agent experiences

**ASCII Diagram:**

```
Working Memory (5 msgs)
     ↕
Short-Term Memory (50 msgs)
     ↕
Long-Term Memory (persistent DB)
```

**Implementation:**

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

func main() {
    ctx := context.Background()

    memAgent := patterns.NewMemoryHierarchyAgent(&patterns.MemoryConfig{
        BaseAgent:     myLLM,
        WorkingSize:   5,   // Active context window
        ShortTermSize: 50,  // Recent history buffer
        LongTermStore: "./agent_memory.db",
    })

    // Process many messages over time
    messages := []string{
        "My name is Alice",
        "I prefer Go over Python",
        "I work on distributed systems",
        // ... many more messages later ...
        "What is my name?",       // Agent should recall "Alice"
        "What language do I prefer?", // Agent should recall "Go"
    }

    for _, content := range messages {
        msg := agenkit.NewMessage("user", content)
        response, err := memAgent.Process(ctx, msg)
        if err != nil {
            log.Fatalf("memory agent failed: %v", err)
        }
        if content[0] == 'W' { // Print only questions
            fmt.Printf("Q: %s\nA: %s\n\n", content, response.Content)
        }
    }
}
```

**Memory Tiers Explained:**

| Tier | Size | Persistence | Speed | Purpose |
|------|------|-------------|-------|---------|
| Working | Small (5-10 msgs) | In-memory | Fastest | Current conversation context |
| Short-term | Medium (50-100 msgs) | In-memory | Fast | Recent interaction history |
| Long-term | Unlimited | Disk/DB | Slower | Persistent facts and preferences |

---

## Pattern Selection Guide

Use this guide to choose the right pattern:

```
Is the task a single well-defined function?
    → Yes: Task pattern
    → No: Continue...

Does the task require maintaining conversation history?
    → Yes: Conversational or MemoryHierarchy pattern
    → No: Continue...

Does the task require external tools or APIs?
    → Yes: ReAct pattern
    → No: Continue...

Does the task require multiple independent analyses?
    → Yes: Parallel pattern
    → No: Continue...

Does the task require a sequence of transformations?
    → Yes: Sequential pattern
    → No: Continue...

Does the task benefit from self-critique and refinement?
    → Yes: Reflection pattern
    → No: Continue...

Does the task require upfront planning?
    → Yes: Planning pattern
    → No: Continue...

Does the task require delegation to specialized agents?
    → Yes: AgentsAsTools pattern
    → No: Continue...

Does the task require multiple collaborating agents?
    → Yes: Multiagent pattern
    → No: Continue...

Is the task open-ended and goal-directed?
    → Yes: Autonomous pattern
```

---

## Composing Patterns

Because all patterns implement `agenkit.Agent`, they compose freely. Here are common compositions:

### Research Pipeline

```go
// Sequential wraps parallel: gather multiple sources, then synthesize
pipeline := patterns.NewSequentialAgent([]agenkit.Agent{
    // Step 1: gather from multiple sources in parallel
    patterns.NewParallelAgent([]agenkit.Agent{
        &WebSearchAgent{},
        &DatabaseAgent{},
        &DocumentAgent{},
    }, nil),
    // Step 2: synthesize results
    &SynthesisAgent{},
    // Step 3: format output
    &FormattingAgent{},
})
```

### Reliable LLM Pipeline

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/middleware"

// Wrap an LLM-based pattern with resilience middleware
base := patterns.NewReflectionAgent(&patterns.ReflectionConfig{
    BaseAgent:     myLLM,
    MaxIterations: 3,
})

// Add reliability
reliable := agenkit.Agent(base)
reliable = middleware.NewRetryMiddleware(reliable, &middleware.RetryConfig{
    MaxRetries:   3,
    InitialDelay: 500 * time.Millisecond,
})
reliable = middleware.NewTimeoutMiddleware(reliable, &middleware.TimeoutConfig{
    Timeout: 30 * time.Second,
})
```

### Conversational Agent with Long Memory

```go
// Conversational with memory hierarchy for persistence
memAgent := patterns.NewMemoryHierarchyAgent(&patterns.MemoryConfig{
    BaseAgent:     myLLM,
    WorkingSize:   10,
    ShortTermSize: 100,
    LongTermStore: "./memory.db",
})

conv := patterns.NewConversationalAgent(&patterns.ConversationalConfig{
    LLM:        memAgent, // Memory-enhanced LLM
    MaxHistory: 20,
})
```

### Autonomous Agent with Observability

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/observability"

auto := patterns.NewAutonomousAgent(&patterns.AutonomousConfig{
    BaseAgent: myLLM,
    Goal:      "Complete the task",
    MaxSteps:  20,
})

// Add tracing
tracer := otel.Tracer("my-service")
traced := observability.NewTracingMiddleware(auto, tracer)

// Add metrics
collector := observability.NewMetricsCollector("agenkit")
observed := collector.Middleware(traced)

result, err := observed.Process(ctx, message)
```

---

## Testing Patterns

All patterns implement `agenkit.Agent` and can be tested uniformly:

```go
package patterns_test

import (
    "context"
    "testing"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// mockAgent is a simple test double.
type mockAgent struct {
    response string
}

func (m *mockAgent) Name() string { return "mock" }
func (m *mockAgent) Capabilities() []string { return nil }
func (m *mockAgent) Introspect() *agenkit.IntrospectionResult { return nil }
func (m *mockAgent) Process(_ context.Context, _ *agenkit.Message) (*agenkit.Message, error) {
    return agenkit.NewMessage("assistant", m.response), nil
}

func TestSequentialPassesOutput(t *testing.T) {
    ctx := context.Background()

    pipeline := patterns.NewSequentialAgent([]agenkit.Agent{
        &mockAgent{response: "step-1"},
        &mockAgent{response: "step-2"},
    })

    result, err := pipeline.Process(ctx, agenkit.NewMessage("user", "input"))
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    // Last agent's response should be the output
    if result.Content != "step-2" {
        t.Errorf("expected %q, got %q", "step-2", result.Content)
    }
}

func TestParallelRunsConcurrently(t *testing.T) {
    ctx := context.Background()

    parallel := patterns.NewParallelAgent([]agenkit.Agent{
        &mockAgent{response: "a"},
        &mockAgent{response: "b"},
        &mockAgent{response: "c"},
    }, nil)

    result, err := parallel.Process(ctx, agenkit.NewMessage("user", "input"))
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
    if result == nil {
        t.Error("expected non-nil result")
    }
}
```

---

## See Also

- [API Reference](API.md) - Complete type and function signatures
- [Getting Started](GETTING_STARTED.md) - Installation and first agent
- [Observability](OBSERVABILITY.md) - Adding tracing and metrics
- [Testing Framework](TESTING_FRAMEWORK.md) - Testing patterns and mock agents
- [Migration Guide](MIGRATION.md) - Porting from other languages
