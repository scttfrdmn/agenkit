# Agenkit Rust Agent Patterns Guide

A comprehensive guide to all 11 agent patterns in Agenkit-Rust, with Rust async/await examples.

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
  - [Agents as Tools](#agents-as-tools)
- [Advanced Patterns](#advanced-patterns)
  - [Autonomous](#autonomous)
  - [Multiagent](#multiagent)
  - [Memory Hierarchy](#memory-hierarchy)
- [Pattern Selection Guide](#pattern-selection-guide)
- [Composing Patterns](#composing-patterns)

---

## Overview

Agent patterns are reusable architectural templates that solve common problems in AI agent design. Agenkit-Rust provides 11 production-ready patterns that compose naturally with Rust's ownership model and async/await.

### Why Patterns Matter

1. **Proven Solutions** — Patterns encode best practices from production systems
2. **Composability** — Patterns work together; combine them for complex workflows
3. **Type Safety** — Rust's type system catches composition errors at compile time
4. **Performance** — Built on Tokio for high-performance concurrent execution
5. **Maintainability** — Clear separation of concerns in each pattern

### Pattern Categories

- **Composition** (Sequential, Parallel) — Combine multiple agents
- **Enhancement** (Reflection, ReAct, Planning) — Improve agent quality through iteration
- **Specialized** (Task, Conversational, Agents as Tools) — Domain-specific patterns
- **Advanced** (Autonomous, Multiagent, Memory Hierarchy) — Complex coordinated behaviors

---

## Pattern Comparison

| Pattern | Complexity | Use Case | Tokio Feature Used | Best For |
|---------|-----------|----------|-------------------|----------|
| Sequential | Low | Data pipelines | Sequential `.await` | Multi-stage processing |
| Parallel | Medium | Independent tasks | `tokio::join!` / `join_all` | Concurrent operations |
| Reflection | Medium | Quality improvement | Iterative `.await` | Self-correction loops |
| ReAct | Medium | Reasoning with tools | Sequential `.await` | Decision-making with actions |
| Planning | High | Complex tasks | Sequential `.await` | Multi-step workflows |
| Task | Low | Job execution | Single `.await` | One-shot purpose agents |
| Conversational | Medium | Dialogue | Stateful async | Chatbots, assistants |
| Agents as Tools | High | Orchestration | Tool dispatch | Hierarchical delegation |
| Autonomous | Very High | Goal pursuit | Loop with `.await` | Self-directed agents |
| Multiagent | Very High | Collaboration | `join_all` + consensus | Multi-agent coordination |
| Memory Hierarchy | High | Context management | Async store/retrieve | Long-running agents |

---

## Composition Patterns

### Sequential

**Purpose:** Process messages through multiple agents in order, passing each output as the next input.

**When to Use:**
- Data transformation pipelines (extract → transform → format)
- Multi-stage validation workflows
- Step-by-step reasoning where each stage depends on the previous
- When output of agent N must feed agent N+1

**Pattern Diagram:**
```
Input → Agent[0] → Agent[1] → Agent[2] → Output
          ↓           ↓           ↓
       (result)   (result)   (final output)
```

**Implementation:**

```rust
use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::SequentialPattern;
use async_trait::async_trait;

// Define pipeline stages as individual agents
struct ExtractAgent;
struct AnalyzeAgent;
struct FormatAgent;

#[async_trait]
impl Agent for ExtractAgent {
    fn name(&self) -> &str { "extractor" }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let text = message.content_as_str().unwrap_or("");
        let extracted = format!("KEY_FACTS: {}", &text[..text.len().min(100)]);
        Ok(Message::assistant(&extracted))
    }
}

#[async_trait]
impl Agent for AnalyzeAgent {
    fn name(&self) -> &str { "analyzer" }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let input = message.content_as_str().unwrap_or("");
        let analyzed = format!("ANALYSIS: {} → implications: positive", input);
        Ok(Message::assistant(&analyzed))
    }
}

#[async_trait]
impl Agent for FormatAgent {
    fn name(&self) -> &str { "formatter" }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let input = message.content_as_str().unwrap_or("");
        let formatted = format!("## Report\n\n{}", input);
        Ok(Message::assistant(&formatted))
    }
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    // Compose into a pipeline
    let pipeline = SequentialPattern::new(vec![
        Box::new(ExtractAgent),
        Box::new(AnalyzeAgent),
        Box::new(FormatAgent),
    ])?;

    let message = Message::user("The new Rust edition introduces significant improvements to async patterns.");
    let result = pipeline.process(message).await?;

    println!("{}", result.content_as_str().unwrap_or(""));
    Ok(())
}
```

**Trade-offs:**
- Pro: Simple to reason about; clear data flow
- Pro: Easy to add/remove/reorder stages
- Con: Latency accumulates (stages are sequential)
- Con: One failing stage aborts the entire pipeline

**Error handling in pipelines:**

```rust
use agenkit::middleware::RetryDecorator;
use std::time::Duration;

// Wrap individual stages with retry to make the pipeline resilient
let pipeline = SequentialPattern::new(vec![
    Box::new(RetryDecorator::new(ExtractAgent, 3, Duration::from_millis(100))),
    Box::new(RetryDecorator::new(AnalyzeAgent, 3, Duration::from_millis(100))),
    Box::new(FormatAgent),
])?;
```

---

### Parallel

**Purpose:** Send the same message to multiple agents concurrently and aggregate their responses.

**When to Use:**
- Independent operations with no data dependencies between them
- Gathering multiple perspectives on the same input
- Fan-out/fan-in data processing
- Reducing total latency when stages don't depend on each other

**Pattern Diagram:**
```
                 ┌─── Agent[0] ───┐
                 │                │
Input Message ───┤─── Agent[1] ───┼─── Aggregator ─── Output
                 │                │
                 └─── Agent[2] ───┘
     (all start simultaneously)
```

**Implementation:**

```rust
use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::ParallelPattern;
use async_trait::async_trait;
use tokio;

// Agents that can run in parallel (no dependencies between them)
struct PerspectiveAgent { viewpoint: String }

impl PerspectiveAgent {
    fn new(viewpoint: &str) -> Self {
        Self { viewpoint: viewpoint.to_string() }
    }
}

#[async_trait]
impl Agent for PerspectiveAgent {
    fn name(&self) -> &str { &self.viewpoint }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let text = message.content_as_str().unwrap_or("");
        let analysis = format!("[{}]: {}", self.viewpoint, text);
        Ok(Message::assistant(&analysis))
    }
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let parallel = ParallelPattern::new(vec![
        Box::new(PerspectiveAgent::new("technical")),
        Box::new(PerspectiveAgent::new("business")),
        Box::new(PerspectiveAgent::new("user-experience")),
    ])?;

    let message = Message::user("Should we adopt microservices architecture?");
    let result = parallel.process(message).await?;
    // result contains all three perspectives combined

    println!("{}", result.content_as_str().unwrap_or(""));
    Ok(())
}
```

**Manual Parallel Execution with `tokio::join!`:**

For a fixed number of agents known at compile time:

```rust
use tokio;

async fn parallel_fixed() -> Result<(), AgentError> {
    let agent_a = TechnicalAgent::new();
    let agent_b = BusinessAgent::new();
    let agent_c = UxAgent::new();
    let message = Message::user("Evaluate this proposal");

    // All three run concurrently
    let (result_a, result_b, result_c) = tokio::join!(
        agent_a.process(message.clone()),
        agent_b.process(message.clone()),
        agent_c.process(message.clone()),
    );

    let (a, b, c) = (result_a?, result_b?, result_c?);
    println!("Technical: {}", a.content_as_str().unwrap_or(""));
    println!("Business: {}", b.content_as_str().unwrap_or(""));
    println!("UX: {}", c.content_as_str().unwrap_or(""));

    Ok(())
}
```

**Dynamic Parallel Execution with `join_all`:**

For a variable number of agents determined at runtime:

```rust
use futures::future::join_all;

async fn parallel_dynamic(
    agents: &[Box<dyn Agent>],
    message: Message,
) -> Vec<Result<Message, AgentError>> {
    let futures: Vec<_> = agents
        .iter()
        .map(|agent| agent.process(message.clone()))
        .collect();

    join_all(futures).await
}
```

**Trade-offs:**
- Pro: Dramatically reduces latency (parallel vs sequential)
- Pro: Failure of one agent doesn't block others
- Con: All agents receive identical input (can't depend on each other)
- Con: Aggregation logic may be complex

---

## Enhancement Patterns

### Reflection

**Purpose:** Iterative self-improvement through draft-critique-refine loop.

**When to Use:**
- Quality is more important than speed
- Output requires self-correction (writing, code, reasoning)
- When a single attempt rarely produces optimal results
- Creative tasks that benefit from iteration

**Pattern Diagram:**
```
Input
  │
  ▼
Generator ──→ Draft
                │
                ▼
             Critic ──→ Critique + Score
                │
                ▼
           Score >= threshold?
           YES → Return Draft
           NO  → Generator (with critique) → New Draft
                    (repeat up to max_iterations)
```

**Implementation:**

```rust
use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::{ReflectionAgent, ReflectionConfig, CritiqueFormat};
use async_trait::async_trait;

struct WritingAgent;
struct CritiqueAgent;

#[async_trait]
impl Agent for WritingAgent {
    fn name(&self) -> &str { "writer" }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let input = message.content_as_str().unwrap_or("");

        // In production this would call an LLM
        let draft = format!("Draft response to: {}", input);
        Ok(Message::assistant(&draft))
    }
}

#[async_trait]
impl Agent for CritiqueAgent {
    fn name(&self) -> &str { "critic" }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let draft = message.content_as_str().unwrap_or("");

        // Structured critique format for precise scoring
        let critique = format!(
            "SCORE: 7/10\nSTRENGTHS: Clear structure\nWEAKNESSES: Lacks specific examples\nSUGGESTIONS: Add concrete examples from {} to improve clarity",
            draft
        );
        Ok(Message::assistant(&critique))
    }
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let config = ReflectionConfig {
        generator: Box::new(WritingAgent),
        critic: Box::new(CritiqueAgent),
        max_iterations: 3,
        quality_threshold: 0.85,        // Stop if score >= 8.5/10
        improvement_threshold: 0.05,    // Stop if improvement < 5%
        critique_format: CritiqueFormat::Structured,
        verbose: true,                  // Log each iteration
    };

    let agent = ReflectionAgent::new(config)?;

    let message = Message::user("Write a technical explanation of Rust's borrow checker");
    let refined = agent.process(message).await?;

    println!("Refined output:\n{}", refined.content_as_str().unwrap_or(""));
    Ok(())
}
```

**Trade-offs:**
- Pro: Significant quality improvement over single-pass
- Pro: Self-correcting — catches and fixes its own errors
- Con: Slower (multiple LLM calls per request)
- Con: Cost increases linearly with iterations
- Con: May converge on local optimum rather than global best

---

### ReAct

**Purpose:** Reasoning + Acting with explicit thought-action-observation cycle.

**When to Use:**
- Tasks requiring external information (search, databases, APIs)
- Multi-step reasoning where each step depends on tool results
- When the agent needs to make decisions based on real-world state
- Debugging-friendly tasks (the thought chain is visible)

**Pattern Diagram:**
```
Input
  │
  ▼
[Thought]: What do I need to do?
  │
  ▼
[Action]: Call tool X with params Y
  │
  ▼
[Observation]: Tool returned Z
  │
  ▼
[Thought]: Given Z, I should...
  │
  ▼
[Action]: Call tool A or give Final Answer
  │
(repeat until answer or max_iterations)
```

**Implementation:**

```rust
use agenkit::core::{Agent, AgentError, Message, Tool, ToolResult};
use agenkit::patterns::ReActAgent;
use async_trait::async_trait;
use std::collections::HashMap;
use serde_json::json;

// Define tools the agent can use
struct SearchTool;
struct CalculatorTool;

#[async_trait]
impl Tool for SearchTool {
    fn name(&self) -> &str { "search" }

    fn description(&self) -> &str {
        "Search for factual information. Use for current events, statistics, and facts."
    }

    fn parameters(&self) -> HashMap<String, serde_json::Value> {
        let mut params = HashMap::new();
        params.insert("query".to_string(), json!({
            "type": "string",
            "description": "The search query"
        }));
        params
    }

    async fn execute(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        let query = params.get("query")
            .and_then(|v| v.as_str())
            .ok_or_else(|| AgentError::InvalidParameters("query required".to_string()))?;

        // Simulate search results
        let result = format!("Search results for '{}': [result1, result2, result3]", query);
        Ok(ToolResult { success: true, result, metadata: HashMap::new() })
    }
}

#[async_trait]
impl Tool for CalculatorTool {
    fn name(&self) -> &str { "calculator" }

    fn description(&self) -> &str {
        "Perform arithmetic calculations. Use for any math operations."
    }

    fn parameters(&self) -> HashMap<String, serde_json::Value> {
        let mut params = HashMap::new();
        params.insert("expression".to_string(), json!({
            "type": "string",
            "description": "Mathematical expression to evaluate"
        }));
        params
    }

    async fn execute(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        let expr = params.get("expression")
            .and_then(|v| v.as_str())
            .ok_or_else(|| AgentError::InvalidParameters("expression required".to_string()))?;

        // In production: use a safe expression evaluator
        let result = format!("Result of {}: 42", expr);
        Ok(ToolResult { success: true, result, metadata: HashMap::new() })
    }
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    // LLM that drives the reasoning
    let llm = Box::new(MyLLMAgent::new());

    let tools: Vec<Box<dyn Tool>> = vec![
        Box::new(SearchTool),
        Box::new(CalculatorTool),
    ];

    let agent = ReActAgent::new(llm, tools)
        .with_max_iterations(10)
        .with_system_prompt(
            "You are a helpful assistant with access to search and calculator tools. \
             Think step by step and use tools when needed."
        );

    let message = Message::user("What is 15% of France's GDP in USD?");
    let response = agent.process(message).await?;

    println!("Answer: {}", response.content_as_str().unwrap_or(""));
    Ok(())
}
```

**Trade-offs:**
- Pro: Grounds reasoning in real-world data via tools
- Pro: Transparent reasoning chain (debuggable)
- Con: Tool calls add latency
- Con: May use tools unnecessarily (increases cost)
- Con: Can get stuck in reasoning loops without max_iterations

---

### Planning

**Purpose:** Decompose complex tasks into explicit steps, then execute each step.

**When to Use:**
- Tasks too complex for a single agent in one pass
- When the approach needs to be determined before execution
- Long-horizon goals requiring multiple phases
- When you want to inspect/modify the plan before execution

**Pattern Diagram:**
```
Input
  │
  ▼
Planner Agent
  │ Creates plan:
  │  Step 1: Research X
  │  Step 2: Analyze Y
  │  Step 3: Synthesize Z
  │
  ▼
Executor (Step 1) → Result 1
  │
Executor (Step 2, using Result 1) → Result 2
  │
Executor (Step 3, using Results 1+2) → Final Output
```

**Implementation:**

```rust
use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::PlanningAgent;
use async_trait::async_trait;

struct PlannerAgent;
struct ExecutorAgent;

#[async_trait]
impl Agent for PlannerAgent {
    fn name(&self) -> &str { "planner" }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let goal = message.content_as_str().unwrap_or("");

        // In production: call LLM to generate a plan
        let plan = format!(
            "PLAN:\n\
             1. Research: gather facts about {}\n\
             2. Analyze: identify key patterns\n\
             3. Synthesize: write comprehensive response\n\
             4. Validate: check for accuracy",
            goal
        );
        Ok(Message::assistant(&plan))
    }
}

#[async_trait]
impl Agent for ExecutorAgent {
    fn name(&self) -> &str { "executor" }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let step = message.content_as_str().unwrap_or("");

        // Execute one plan step
        let result = format!("Completed: {}", step);
        Ok(Message::assistant(&result))
    }
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let agent = PlanningAgent::new(
        Box::new(PlannerAgent),
        Box::new(ExecutorAgent),
    )
    .with_max_plan_steps(10)
    .with_replan_on_failure(true);

    let message = Message::user("Write a comprehensive guide to Rust async programming");
    let result = agent.process(message).await?;

    println!("{}", result.content_as_str().unwrap_or(""));
    Ok(())
}
```

**Trade-offs:**
- Pro: Handles complex multi-step tasks well
- Pro: Plan is inspectable and potentially modifiable
- Con: Significant overhead for simple tasks
- Con: Plan quality depends on planner agent quality
- Con: Replanning on failure can be slow

---

## Specialized Patterns

### Task

**Purpose:** One-shot task execution with explicit success criteria and lifecycle management.

**When to Use:**
- Well-defined, bounded tasks with clear completion criteria
- Tasks where you want to assert success/failure explicitly
- Background job processing
- When you need to enforce a timeout on task completion

**Pattern Diagram:**
```
Task Config: {
  description: "...",
  success_criteria: [...],
  timeout: Duration
}
  │
  ▼
Start Task → Agent Processing → Check Criteria → Success/Failure
                    │
                (with timeout)
```

**Implementation:**

```rust
use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::{TaskAgent, TaskConfig};
use std::time::Duration;

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let config = TaskConfig {
        description: "Classify the sentiment of the provided text".to_string(),
        success_criteria: vec![
            "Response contains one of: POSITIVE, NEGATIVE, NEUTRAL".to_string(),
            "Response is under 100 characters".to_string(),
        ],
        timeout: Duration::from_secs(30),
        retry_on_failure: true,
    };

    let agent = TaskAgent::new(Box::new(ClassifierAgent::new()), config);

    let message = Message::user("I absolutely love how fast Rust compiles!");
    let result = agent.process(message).await?;

    println!("Classification: {}", result.content_as_str().unwrap_or(""));
    Ok(())
}
```

**Trade-offs:**
- Pro: Clear lifecycle and success/failure semantics
- Pro: Enforces timeout automatically
- Con: Overhead vs raw agent call for simple tasks
- Con: Success criteria checking may require LLM evaluation

---

### Conversational

**Purpose:** Multi-turn dialogue with conversation history management.

**When to Use:**
- Interactive chat applications
- Agents that need to remember context across turns
- Customer service bots
- Coding assistants that maintain project context

**Pattern Diagram:**
```
Turn 1: User message → [system + user] → Agent → Response
Turn 2: User message → [system + user + response + user] → Agent → Response
Turn 3: User message → [system + user + ... + user] → Agent → Response
                         (history up to limit)
```

**Implementation:**

```rust
use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::ConversationalAgent;
use agenkit::memory::{MemoryHierarchy, WorkingMemory, LongTermMemory};

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    // Build agent with history and memory
    let mut agent = ConversationalAgent::new(Box::new(MyLLMAgent::new()))
        .with_history_limit(20)   // Keep last 20 messages
        .with_system_prompt(
            "You are a helpful Rust programming assistant. \
             Remember context between turns."
        )
        .with_memory(MemoryHierarchy::new(
            WorkingMemory::with_capacity(10),
            LongTermMemory::with_path("./conversation_memory.db"),
        ));

    // Simulate a multi-turn conversation
    let turns = vec![
        "I'm building a web server in Rust. What framework should I use?",
        "Tell me more about Axum specifically.",
        "How do I add middleware in Axum?",
    ];

    for user_input in turns {
        let message = Message::user(user_input);
        let response = agent.process(message).await?;

        println!("User: {}", user_input);
        println!("Agent: {}\n", response.content_as_str().unwrap_or(""));
    }

    // The agent remembers previous turns
    println!("History length: {}", agent.history().len());

    Ok(())
}
```

**Ownership note:** `ConversationalAgent` requires `&mut self` for history mutation, which differs from other patterns. Use `Arc<Mutex<ConversationalAgent>>` when sharing across tasks:

```rust
use std::sync::Arc;
use tokio::sync::Mutex;

let agent = Arc::new(Mutex::new(ConversationalAgent::new(llm)));

// In task 1
let agent = Arc::clone(&agent);
tokio::spawn(async move {
    let mut guard = agent.lock().await;
    let response = guard.process(Message::user("Hello")).await?;
    Ok::<_, AgentError>(response)
});
```

**Trade-offs:**
- Pro: Natural, context-aware conversations
- Pro: History management is automatic
- Con: Memory grows unbounded without history limit
- Con: Long histories increase token costs per turn

---

### Agents as Tools

**Purpose:** Wrap specialist agents as tools that a supervisor agent can call by name.

**When to Use:**
- Hierarchical multi-agent systems
- When a coordinator should delegate to specialists
- Building agent-of-agents architectures
- When tool descriptions are more natural than direct agent calls

**Pattern Diagram:**
```
User Request
     │
     ▼
Supervisor Agent
     │ "I need to write code"
     ▼
code_expert Tool ──→ CodeSpecialistAgent.process(...)
     │ "I need to search"
     ▼
search_agent Tool ──→ SearchSpecialistAgent.process(...)
     │
     ▼
Synthesized Response
```

**Implementation:**

```rust
use agenkit::core::{Agent, AgentError, Message, Tool};
use agenkit::patterns::{AgentsAsToolsPattern, agent_as_tool};
use async_trait::async_trait;

struct CodeAgent;
struct MathAgent;
struct SearchAgent;

#[async_trait]
impl Agent for CodeAgent {
    fn name(&self) -> &str { "code-specialist" }
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let query = message.content_as_str().unwrap_or("");
        Ok(Message::assistant(&format!("```rust\n// Code for: {}\nfn main() {{}}\n```", query)))
    }
}

#[async_trait]
impl Agent for MathAgent {
    fn name(&self) -> &str { "math-specialist" }
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let query = message.content_as_str().unwrap_or("");
        Ok(Message::assistant(&format!("Mathematical solution for: {}", query)))
    }
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    // Wrap specialists as tools
    let code_tool = agent_as_tool(
        Box::new(CodeAgent),
        "code_expert",
        "Expert programmer for writing and reviewing code in any language",
    )?;

    let math_tool = agent_as_tool(
        Box::new(MathAgent),
        "math_expert",
        "Expert mathematician for calculations, proofs, and numerical analysis",
    )?;

    // Build the pattern
    let pattern = AgentsAsToolsPattern::new(Box::new(SupervisorAgent::new()))
        .with_specialist(Box::new(CodeAgent), "Expert programmer")
        .with_specialist(Box::new(MathAgent), "Expert mathematician");

    let message = Message::user("Write a Rust function to calculate fibonacci numbers efficiently");
    let response = pattern.process(message).await?;

    println!("{}", response.content_as_str().unwrap_or(""));
    Ok(())
}
```

**Trade-offs:**
- Pro: Clean separation between coordination and execution
- Pro: Specialists are reusable in other contexts
- Con: Tool dispatch overhead
- Con: Supervisor needs to correctly choose which tool to use
- Con: Error handling is more complex (tool errors vs agent errors)

---

## Advanced Patterns

### Autonomous

**Purpose:** Goal-directed agent that iterates until it decides the goal is achieved.

**When to Use:**
- Open-ended tasks without a predetermined number of steps
- Research agents that explore until satisfied
- Code generation agents that iterate until tests pass
- Tasks where the stopping condition depends on content

**Pattern Diagram:**
```
Goal: "Write a Rust web server that handles 10k req/s"
  │
  ▼
┌─────────────────────────────────────────┐
│  Think: What step should I take next?   │
│    │                                    │
│    ▼                                    │
│  Act: Use tool / generate code          │
│    │                                    │
│    ▼                                    │
│  Evaluate: Goal achieved? → YES ──────────→ Return Result
│    NO                                  │
└────────────────────────────────────────┘
  (repeat up to max_iterations)
```

**Implementation:**

```rust
use agenkit::core::{Agent, AgentError, Message, Tool, ToolResult};
use agenkit::patterns::AutonomousAgent;
use async_trait::async_trait;
use std::collections::HashMap;
use serde_json::json;

struct FileWriteTool;
struct RunTestsTool;
struct ReadFileTool;

// (Tool implementations omitted for brevity — see Tool Trait in API.md)

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let tools: Vec<Box<dyn Tool>> = vec![
        Box::new(FileWriteTool),
        Box::new(RunTestsTool),
        Box::new(ReadFileTool),
    ];

    let agent = AutonomousAgent::new(Box::new(MyLLMAgent::new()), tools)
        .with_goal("Write a Rust function that sorts a Vec<i32> in O(n log n) time with tests")
        .with_max_iterations(20)
        .with_completion_signal("GOAL_ACHIEVED");

    let message = Message::user("Start working on the goal.");
    let result = agent.process(message).await?;

    println!("Final result:\n{}", result.content_as_str().unwrap_or(""));
    Ok(())
}
```

**Rust-specific consideration:** The autonomous loop holds no locks across `.await` points. If you need to share state between iterations, use `Arc<Mutex<T>>` inside the agent struct.

**Trade-offs:**
- Pro: Handles genuinely open-ended tasks
- Pro: Can adapt strategy based on intermediate results
- Con: Unpredictable completion time
- Con: Can loop without making progress without safeguards
- Con: Hard to debug; use verbose mode and step limits

---

### Multiagent

**Purpose:** Multiple specialist agents collaborate, potentially reaching consensus.

**When to Use:**
- Complex decisions benefiting from multiple expert opinions
- Tasks requiring specialized knowledge across domains
- When you want peer review of agent outputs
- Simulating panels, committees, or review boards

**Pattern Diagram:**
```
Coordinator Agent
     │
     ├──→ Specialist Agent A (domain: security)
     │         └──→ Opinion A
     ├──→ Specialist Agent B (domain: performance)
     │         └──→ Opinion B
     └──→ Specialist Agent C (domain: maintainability)
               └──→ Opinion C
                    │
                    ▼
           Consensus/Synthesis
                    │
                    ▼
            Final Decision
```

**Implementation:**

```rust
use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::MultiagentOrchestrator;
use async_trait::async_trait;

struct SecurityExpert;
struct PerformanceExpert;
struct MaintainabilityExpert;

#[async_trait]
impl Agent for SecurityExpert {
    fn name(&self) -> &str { "security-expert" }
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let input = message.content_as_str().unwrap_or("");
        Ok(Message::assistant(&format!(
            "SECURITY REVIEW: {} — No obvious vulnerabilities, recommend input validation", input
        )))
    }
}

// (Other experts omitted for brevity)

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let orchestrator = MultiagentOrchestrator::new(Box::new(CoordinatorAgent::new()))
        .with_worker(Box::new(SecurityExpert))
        .with_worker(Box::new(PerformanceExpert))
        .with_worker(Box::new(MaintainabilityExpert))
        .with_consensus_threshold(0.67)  // 2/3 must agree
        .with_max_rounds(3);

    let message = Message::user(
        "Review this Rust code: fn process(data: Vec<u8>) -> String { String::from_utf8_lossy(&data).to_string() }"
    );
    let decision = orchestrator.process(message).await?;

    println!("Consensus decision:\n{}", decision.content_as_str().unwrap_or(""));
    Ok(())
}
```

**Trade-offs:**
- Pro: Higher quality through diverse perspectives
- Pro: Can use `join_all` for concurrent worker execution
- Con: High cost (N LLM calls per round)
- Con: Consensus logic can be complex
- Con: Workers must be independent to avoid coordination overhead

---

### Memory Hierarchy

**Purpose:** Three-tier memory (working, episodic, semantic) for long-running agents that need context beyond a single conversation.

**When to Use:**
- Agents that operate across multiple sessions
- Long-running research or coding agents
- When context exceeds LLM context window limits
- Personalized agents that adapt to individual users

**Pattern Diagram:**
```
New Request
     │
     ▼
Working Memory (fast, recent context)
     │ if not found
     ▼
Episodic Memory (past conversation summaries)
     │ if not found
     ▼
Semantic Memory (long-term knowledge, embeddings)
     │
     ▼
Construct Full Context → Agent → Response
     │
     ▼
Store important info → All memory tiers as appropriate
```

**Implementation:**

```rust
use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::MemoryHierarchyAgent;
use agenkit::memory::{MemoryHierarchy, WorkingMemory, LongTermMemory};

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    // Configure memory tiers
    let memory = MemoryHierarchy::new(
        WorkingMemory::with_capacity(20),          // Last 20 items
        LongTermMemory::with_path("./agent_memory.db"),  // SQLite persistence
    );

    let agent = MemoryHierarchyAgent::new(
        Box::new(MyLLMAgent::new()),
        memory,
    );

    // First session
    let msg1 = Message::user("My name is Alice and I'm working on a Rust web server");
    let _ = agent.process(msg1).await?;

    // Later session (memory persists)
    let msg2 = Message::user("What was I working on last time?");
    let response = agent.process(msg2).await?;

    // Agent remembers "Alice" and "Rust web server" from previous session
    println!("{}", response.content_as_str().unwrap_or(""));

    Ok(())
}
```

**Trade-offs:**
- Pro: Enables very long-horizon agent operation
- Pro: Reduces token costs by summarizing old context
- Con: Memory retrieval adds latency
- Con: Persistent storage requires infrastructure
- Con: Memory can accumulate irrelevant information over time

---

## Pattern Selection Guide

Use this guide to choose the right pattern for your use case:

```
What is your primary need?
│
├─ Combine multiple agents?
│   ├─ Sequential dependencies → Sequential
│   └─ No dependencies → Parallel
│
├─ Improve output quality?
│   ├─ Self-improvement loop → Reflection
│   ├─ Needs external info → ReAct
│   └─ Complex multi-step → Planning
│
├─ Specific domain?
│   ├─ One task, clear criteria → Task
│   ├─ Multi-turn conversation → Conversational
│   └─ Delegate to specialists → Agents as Tools
│
└─ Long-running / complex?
    ├─ Open-ended goal → Autonomous
    ├─ Multiple collaborators → Multiagent
    └─ Long context / multi-session → Memory Hierarchy
```

**Quick Decision Matrix:**

| Need | Pattern |
|------|---------|
| ETL pipeline | Sequential |
| Gather multiple opinions | Parallel |
| Write high-quality content | Reflection |
| Answer questions using tools | ReAct |
| Complete a multi-step project | Planning |
| Execute one bounded task | Task |
| Build a chatbot | Conversational |
| Coordinate expert agents | Agents as Tools |
| Build an autonomous agent | Autonomous |
| Simulate a review panel | Multiagent |
| Long-running personal agent | Memory Hierarchy |

---

## Composing Patterns

Patterns can be nested and combined. Here are common compositions:

### Reflection + Sequential (Quality Pipeline)

```rust
use agenkit::patterns::{ReflectionAgent, ReflectionConfig, SequentialPattern, CritiqueFormat};

// Each stage of the pipeline self-improves
let research_with_reflection = ReflectionAgent::new(ReflectionConfig {
    generator: Box::new(ResearchAgent::new()),
    critic: Box::new(ResearchCriticAgent::new()),
    max_iterations: 2,
    quality_threshold: 0.8,
    improvement_threshold: 0.05,
    critique_format: CritiqueFormat::Structured,
    verbose: false,
})?;

let writing_with_reflection = ReflectionAgent::new(ReflectionConfig {
    generator: Box::new(WritingAgent::new()),
    critic: Box::new(WritingCriticAgent::new()),
    max_iterations: 3,
    quality_threshold: 0.9,
    improvement_threshold: 0.05,
    critique_format: CritiqueFormat::Structured,
    verbose: false,
})?;

// Compose reflective agents sequentially
let pipeline = SequentialPattern::new(vec![
    Box::new(research_with_reflection),
    Box::new(writing_with_reflection),
    Box::new(FormatAgent::new()),
])?;
```

### Parallel + Sequential (Fan-out/Fan-in)

```rust
// Fan out to multiple analysts, then synthesize results sequentially
let analysis = ParallelPattern::new(vec![
    Box::new(TechnicalAnalyst::new()),
    Box::new(BusinessAnalyst::new()),
    Box::new(RiskAnalyst::new()),
])?;

let pipeline = SequentialPattern::new(vec![
    Box::new(analysis),           // Fan out: all analysts work in parallel
    Box::new(SynthesisAgent::new()), // Fan in: synthesize all perspectives
    Box::new(ReportAgent::new()),    // Format the final report
])?;
```

### ReAct + Memory (Long-horizon Research)

```rust
use agenkit::patterns::{ReActAgent, MemoryHierarchyAgent};
use agenkit::memory::{MemoryHierarchy, WorkingMemory, LongTermMemory};

// ReAct agent with persistent memory for multi-session research
let memory = MemoryHierarchy::new(
    WorkingMemory::with_capacity(50),
    LongTermMemory::with_path("./research.db"),
);

let react_agent = ReActAgent::new(
    Box::new(MyLLMAgent::new()),
    vec![
        Box::new(SearchTool::new()),
        Box::new(ReadFileTool::new()),
        Box::new(WriteNoteTool::new()),
    ],
)
.with_max_iterations(20);

let agent = MemoryHierarchyAgent::new(Box::new(react_agent), memory);
```

### Middleware + Any Pattern

Middleware wraps any pattern since patterns implement `Agent`:

```rust
use agenkit::middleware::{RetryDecorator, TimeoutDecorator};
use agenkit::observability::{TracingMiddleware, MetricsMiddleware};
use std::time::Duration;

let pattern = SequentialPattern::new(vec![
    Box::new(AgentA::new()),
    Box::new(AgentB::new()),
])?;

// Add production-grade middleware to the entire pattern
let production_agent = RetryDecorator::new(pattern, 3, Duration::from_millis(100));
let production_agent = TimeoutDecorator::new(production_agent, Duration::from_secs(30));
let production_agent = TracingMiddleware::new(production_agent, Some("my-pipeline"));
let production_agent = MetricsMiddleware::new(production_agent);
```

---

**Version**: v0.75.0
**Last Updated**: March 17, 2026

See [API.md](API.md) for complete type signatures.
See [GETTING_STARTED.md](GETTING_STARTED.md) for setup instructions.
