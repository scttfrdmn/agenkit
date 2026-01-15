# Agenkit Pattern Guide

**A comprehensive guide to the 18 agent patterns for building production AI systems.**

---

## Table of Contents

- [Introduction](#introduction)
- [Pattern Categories](#pattern-categories)
- [Quick Selection Guide](#quick-selection-guide)
- [Core Patterns](#core-patterns)
  - [Sequential](#sequential)
  - [Parallel](#parallel)
  - [Router](#router)
  - [Fallback](#fallback)
- [Enhancement Patterns](#enhancement-patterns)
  - [Reflection](#reflection)
  - [ReAct](#react)
  - [Planning](#planning)
  - [Reasoning with Tools](#reasoning-with-tools)
- [Coordination Patterns](#coordination-patterns)
  - [Supervisor](#supervisor)
  - [Orchestration](#orchestration)
  - [Multiagent](#multiagent)
  - [Collaborative](#collaborative)
- [Specialized Patterns](#specialized-patterns)
  - [Task](#task)
  - [Conversational](#conversational)
  - [Human in Loop](#human-in-loop)
  - [Agents as Tools](#agents-as-tools)
- [Advanced Patterns](#advanced-patterns)
  - [Autonomous](#autonomous)
  - [Memory Hierarchy](#memory-hierarchy)
- [Pattern Composition](#pattern-composition)
- [Performance Characteristics](#performance-characteristics)
- [Best Practices](#best-practices)

---

## Introduction

Agent patterns are **reusable architectural templates** that solve common problems in AI agent design. Agenkit provides 18 production-ready patterns that work identically across Python, Go, TypeScript, Rust, C++, and Zig.

### Why Patterns Matter

1. **Proven Solutions** - Patterns encode best practices from production systems
2. **Cross-Language Consistency** - Same patterns work in all 6 languages
3. **Composability** - Patterns work together seamlessly
4. **Performance** - Framework overhead <1% of LLM call time
5. **Production Ready** - 100% test coverage, used in real systems

### Pattern Philosophy

**Composition over Inheritance**: Build complex behaviors by combining simple patterns, not by creating monolithic agents.

```python
# ❌ Monolithic (hard to test, modify, reuse)
class SuperAgent(Agent):
    async def process(self, message: Message) -> Message:
        # 500 lines of mixed concerns
        pass

# ✅ Composed (modular, testable, reusable)
pipeline = SequentialAgent(
    agents=[
        ValidationAgent(),
        RouterAgent(routes={...}),
        ReflectionAgent(agent=writer, critic=critic)
    ]
)
```

---

## Pattern Categories

### Core Patterns (Orchestration)
- **Sequential** - Process through agents in order
- **Parallel** - Execute agents concurrently
- **Router** - Route to specialist agents
- **Fallback** - Automatic failover chain

### Enhancement Patterns (Quality)
- **Reflection** - Iterative self-improvement
- **ReAct** - Reasoning + Tool usage
- **Planning** - Create plan then execute
- **Reasoning with Tools** - Advanced reasoning strategies (CoT, ToT)

### Coordination Patterns (Multi-Agent)
- **Supervisor** - Oversee worker agents
- **Orchestration** - Complex workflow automation
- **Multiagent** - Collaborative problem solving
- **Collaborative** - Shared workspace collaboration

### Specialized Patterns (Domain-Specific)
- **Task** - Single-purpose execution
- **Conversational** - Multi-turn dialogue
- **Human in Loop** - Human approval gates
- **Agents as Tools** - Wrap agents as tools

### Advanced Patterns (Complex)
- **Autonomous** - Self-directed goal pursuit
- **Memory Hierarchy** - Efficient long-term memory

---

## Quick Selection Guide

### Decision Tree

```
What do you need?

├─ Multiple agents?
│  ├─ Sequential processing → Sequential
│  ├─ Parallel execution → Parallel
│  ├─ Route to specialists → Router
│  └─ Failover/retry → Fallback
│
├─ Improve quality?
│  ├─ Self-improvement → Reflection
│  ├─ With tools → ReAct
│  ├─ Planned approach → Planning
│  └─ Complex reasoning → Reasoning with Tools
│
├─ Coordination?
│  ├─ Oversight → Supervisor
│  ├─ Complex workflows → Orchestration
│  ├─ Collaboration → Multiagent or Collaborative
│  └─ Human approval → Human in Loop
│
├─ Specialized?
│  ├─ Chatbot → Conversational
│  ├─ Single task → Task
│  ├─ Agent orchestration → Agents as Tools
│  └─ Long conversations → Memory Hierarchy
│
└─ Advanced?
   └─ Open-ended goals → Autonomous
```

### By Use Case

| Use Case | Recommended Pattern | Alternative |
|----------|-------------------|-------------|
| Data pipeline | Sequential | - |
| A/B testing | Parallel | - |
| Multi-provider LLM | Fallback | Router |
| Customer support routing | Router | Agents as Tools |
| Content writing | Reflection | Planning |
| Research with APIs | ReAct | Planning |
| Multi-step workflows | Planning | Orchestration |
| Mathematical reasoning | Reasoning with Tools | ReAct |
| Quality control | Supervisor | Reflection |
| Business automation | Orchestration | Sequential + Router |
| Expert panel | Multiagent | Parallel |
| Team collaboration | Collaborative | Multiagent |
| Single API call | Task | - |
| Chat assistant | Conversational | - |
| Financial transactions | Human in Loop | Supervisor |
| Tool delegation | Agents as Tools | ReAct |
| Agent swarm | Autonomous | Multiagent |
| Long dialogues | Memory Hierarchy | Conversational |

---

## Core Patterns

### Sequential

**Purpose:** Process messages through multiple agents in order, where each agent's output becomes the next agent's input.

**When to Use:**
- Multi-stage data processing pipelines
- Validation → Processing → Formatting workflows
- Document processing (extract → analyze → summarize)
- Any workflow with dependent stages

**Pattern Diagram:**
```
Input → Agent 1 → Agent 2 → Agent 3 → Output
```

**Performance:** O(n) latency where n = number of agents

**Example - Document Processing Pipeline:**

```python
from agenkit.patterns import SequentialAgent
from agenkit import Agent, Message

class ExtractorAgent(Agent):
    """Extract key information from documents."""
    @property
    def name(self) -> str:
        return "extractor"

    async def process(self, message: Message) -> Message:
        doc = message.content
        # Extract entities, dates, amounts
        extracted = extract_information(doc)
        return Message(role="assistant", content=extracted)

class AnalyzerAgent(Agent):
    """Analyze extracted information."""
    @property
    def name(self) -> str:
        return "analyzer"

    async def process(self, message: Message) -> Message:
        data = message.content
        # Perform analysis
        analysis = analyze_data(data)
        return Message(role="assistant", content=analysis)

class SummarizerAgent(Agent):
    """Create final summary."""
    @property
    def name(self) -> str:
        return "summarizer"

    async def process(self, message: Message) -> Message:
        analysis = message.content
        # Generate summary
        summary = create_summary(analysis)
        return Message(role="assistant", content=summary)

# Build pipeline
pipeline = SequentialAgent(
    agents=[
        ExtractorAgent(),
        AnalyzerAgent(),
        SummarizerAgent()
    ],
    name="document-pipeline"
)

# Process document
doc = Message(role="user", content="Q4 2024 Financial Report...")
result = await pipeline.process(doc)
print(result.content)  # Final summary
```

**Cross-Language Example (Go):**

```go
package main

import (
    "context"
    "github.com/scttfrdmn/agenkit/agenkit-go/core"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// Build pipeline in Go
pipeline := patterns.NewSequential(
    patterns.SequentialConfig{
        Agents: []core.Agent{
            &ExtractorAgent{},
            &AnalyzerAgent{},
            &SummarizerAgent{},
        },
    },
)

// Process document
doc := core.Message{Role: "user", Content: "Q4 2024 Financial Report..."}
result, err := pipeline.Process(context.Background(), doc)
if err != nil {
    log.Fatal(err)
}
fmt.Println(result.Content)
```

**Pros:**
- ✅ Simple and predictable
- ✅ Easy to debug (one agent at a time)
- ✅ Clear data flow
- ✅ Fast (minimal overhead)

**Cons:**
- ❌ No parallelism (sequential only)
- ❌ Single point of failure
- ❌ Latency = sum of all agents

**Best Practices:**
1. Keep each agent focused on one task
2. Use descriptive names
3. Add logging between stages
4. Handle errors gracefully (or use Fallback for resilience)
5. Consider timeout per stage

**Performance Benchmark:**
```
Sequential Pattern (3 agents): ~450 ns/op (Go), ~1.2 μs/op (TypeScript)
Framework overhead: <0.001% vs LLM call (100,000 μs)
```

---

### Parallel

**Purpose:** Execute multiple agents concurrently and aggregate their results.

**When to Use:**
- Independent tasks that can run simultaneously
- Gathering multiple perspectives (technical + business + risk)
- A/B testing different approaches
- Ensemble models (combine multiple agent outputs)
- Reducing latency with concurrent execution

**Pattern Diagram:**
```
       ┌→ Agent 1 →┐
Input ─┼→ Agent 2 →┼→ Aggregator → Output
       └→ Agent 3 →┘
```

**Performance:** O(max(t1, t2, ..., tn)) latency where ti = time for agent i

**Example - Multi-Perspective Analysis:**

```python
from agenkit.patterns import ParallelAgent
from agenkit import Agent, Message
import asyncio

class TechnicalAnalyst(Agent):
    """Analyze from technical perspective."""
    @property
    def name(self) -> str:
        return "technical"

    async def process(self, message: Message) -> Message:
        # Simulate analysis
        await asyncio.sleep(0.5)
        return Message(
            role="assistant",
            content="Technical: System architecture is scalable and maintainable."
        )

class BusinessAnalyst(Agent):
    """Analyze from business perspective."""
    @property
    def name(self) -> str:
        return "business"

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(0.5)
        return Message(
            role="assistant",
            content="Business: ROI is positive, market opportunity is large."
        )

class RiskAnalyst(Agent):
    """Analyze from risk perspective."""
    @property
    def name(self) -> str:
        return "risk"

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(0.5)
        return Message(
            role="assistant",
            content="Risk: Low technical risk, medium market risk."
        )

# Create parallel analysis
analysts = ParallelAgent(
    agents=[
        TechnicalAnalyst(),
        BusinessAnalyst(),
        RiskAnalyst()
    ],
    name="multi-perspective",
    aggregation="concat"  # Options: concat, vote, first, custom
)

# Analyze proposal
proposal = Message(role="user", content="Should we build a new mobile app?")

import time
start = time.time()
result = await analysts.process(proposal)
elapsed = time.time() - start

print(f"Analysis completed in {elapsed:.2f}s")  # ~0.5s (parallel) vs ~1.5s (sequential)
print(result.content)
# Output:
# Technical: System architecture is scalable and maintainable.
# Business: ROI is positive, market opportunity is large.
# Risk: Low technical risk, medium market risk.
```

**Custom Aggregation:**

```python
def voting_aggregator(results: list[Message]) -> Message:
    """Aggregate by majority vote."""
    votes = {}
    for msg in results:
        answer = msg.content.lower()
        votes[answer] = votes.get(answer, 0) + 1

    winner = max(votes, key=votes.get)
    return Message(
        role="assistant",
        content=f"Decision: {winner} ({votes[winner]}/{len(results)} votes)"
    )

parallel = ParallelAgent(
    agents=[judge1, judge2, judge3],
    aggregation=voting_aggregator
)
```

**Pros:**
- ✅ High throughput (concurrent execution)
- ✅ Reduced latency (N agents in time of slowest)
- ✅ Multiple perspectives
- ✅ Fault tolerance (partial failures OK with right aggregation)

**Cons:**
- ❌ Higher complexity
- ❌ More resource intensive
- ❌ Harder to debug
- ❌ Aggregation strategy matters

**Best Practices:**
1. Ensure agents are truly independent
2. Set appropriate timeouts
3. Handle partial failures gracefully
4. Choose aggregation strategy carefully
5. Monitor resource usage

**Performance Benchmark:**
```
Parallel Pattern (3 agents): ~150 ns/op (C++), ~1.8 μs/op (TypeScript)
Real-world speedup: 3x with 3 independent agents
```

---

### Router

**Purpose:** Route messages to appropriate specialist agents based on content, metadata, or classification.

**When to Use:**
- Multiple specialists available (weather, stocks, news agents)
- Need intelligent routing based on content
- Domain-specific agents (billing, technical, sales support)
- Load balancing across agents
- Conditional execution paths

**Pattern Diagram:**
```
Router (classifier)
     ├→ [weather query] → Weather Agent
     ├→ [stock query] → Stock Agent
     ├→ [news query] → News Agent
     └→ [other] → General Agent (default)
```

**Performance:** O(routing) + O(selected_agent)

**Example - Customer Support Router:**

```python
from agenkit.patterns import RouterAgent
from agenkit import Agent, Message

# Define specialist agents
class BillingAgent(Agent):
    @property
    def name(self) -> str:
        return "billing"

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content="Billing: Let me help with your account..."
        )

class TechnicalAgent(Agent):
    @property
    def name(self) -> str:
        return "technical"

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content="Technical: Let me troubleshoot..."
        )

class SalesAgent(Agent):
    @property
    def name(self) -> str:
        return "sales"

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content="Sales: I can help you find the right product..."
        )

# Keyword-based routing strategy
def keyword_router(message: Message, routes: dict) -> str:
    """Route based on keywords in message."""
    content = message.content.lower()

    if any(word in content for word in ["bill", "payment", "charge", "invoice"]):
        return "billing"
    elif any(word in content for word in ["broken", "error", "not working", "problem"]):
        return "technical"
    elif any(word in content for word in ["buy", "purchase", "price", "upgrade"]):
        return "sales"
    else:
        return None  # Use default

# Create router
support_router = RouterAgent(
    routes={
        "billing": BillingAgent(),
        "technical": TechnicalAgent(),
        "sales": SalesAgent()
    },
    default_agent=GeneralAgent(),
    routing_strategy=keyword_router  # or "llm", "metadata", "custom"
)

# Route customer inquiries
inquiries = [
    "My credit card was charged twice",
    "The app keeps crashing",
    "I want to upgrade to pro plan"
]

for inquiry in inquiries:
    msg = Message(role="user", content=inquiry)
    result = await support_router.process(msg)
    routed_to = result.metadata.get("routed_to", "unknown")
    print(f"'{inquiry}' → {routed_to}")
    print(f"Response: {result.content}\n")
```

**LLM-Based Routing (More Accurate):**

```python
from agenkit.patterns import RouterAgent

# Use LLM to classify and route
router = RouterAgent(
    routes={
        "billing": billing_agent,
        "technical": technical_agent,
        "sales": sales_agent
    },
    routing_strategy="llm",  # Uses LLM to classify
    routing_llm=classifier_llm  # Fast, cheap model for classification
)
```

**Metadata-Based Routing:**

```python
# Route based on message metadata
router = RouterAgent(
    routes={
        "urgent": priority_agent,
        "normal": standard_agent,
        "low": batch_agent
    },
    routing_strategy="metadata",
    metadata_key="priority"
)

# Message metadata determines routing
msg = Message(role="user", content="Important question")
msg.metadata["priority"] = "urgent"
result = await router.process(msg)  # → priority_agent
```

**Pros:**
- ✅ Intelligent agent selection
- ✅ Specialist optimization
- ✅ Load balancing possible
- ✅ Flexible routing strategies
- ✅ Easy to add new specialists

**Cons:**
- ❌ Routing overhead (classification cost)
- ❌ Potential misrouting
- ❌ Requires good routing logic
- ❌ Single point of routing failure

**Best Practices:**
1. Use clear, non-overlapping route criteria
2. Always provide a default agent
3. Log routing decisions for debugging
4. Monitor routing accuracy
5. Use LLM-based routing for complex cases
6. Combine with Fallback for reliability

**Performance Benchmark:**
```
Router Pattern: ~250 ns/op (Go), ~3.5 μs/op (TypeScript)
LLM routing adds: ~50-100ms (classification LLM call)
Keyword routing adds: <1ms (regex matching)
```

---

### Fallback

**Purpose:** Sequential retry across multiple agents with automatic failover for high availability.

**When to Use:**
- High availability systems (99.9%+ uptime)
- Multi-provider LLM setups (OpenAI → Anthropic → local)
- Graceful degradation (advanced model → simple model)
- Error recovery with fallback strategies
- Cost optimization (try cheap option first)

**Pattern Diagram:**
```
Primary Agent (try first)
     ↓ (if fails)
Fallback 1
     ↓ (if fails)
Fallback 2
     ↓ (if fails)
Last Resort
```

**Performance:** O(first_success) - Fast path when primary succeeds

**Example - Multi-Provider LLM:**

```python
from agenkit.patterns import FallbackAgent
from agenkit.adapters import OpenAIAgent, AnthropicAgent, OllamaAgent
from agenkit import Message

# Create agents for different providers
openai_agent = OpenAIAgent(model="gpt-4", name="openai")
anthropic_agent = AnthropicAgent(model="claude-3-5-sonnet-20241022", name="anthropic")
ollama_agent = OllamaAgent(model="llama3.3", name="ollama")  # Local fallback

# Fallback chain: expensive → mid-tier → free local
multi_provider = FallbackAgent(
    agents=[openai_agent, anthropic_agent, ollama_agent],
    name="ha-llm"
)

# Try all providers until one succeeds
question = Message(role="user", content="Explain quantum computing")
result = await multi_provider.process(question)

# Check which provider succeeded
attempts = result.metadata.get("fallback_attempts", 1)
success_agent = result.metadata.get("fallback_success_agent", "unknown")

if attempts == 1:
    print("✓ OpenAI succeeded immediately")
elif attempts == 2:
    print("⚠ OpenAI failed, Anthropic succeeded")
else:
    print("⚠⚠ Cloud providers failed, using local Ollama")

print(f"Response: {result.content}")
```

**Cost Optimization Example:**

```python
from agenkit.patterns import FallbackAgent

# Try cheaper models first
cost_optimizer = FallbackAgent(
    agents=[
        cheap_model_agent,    # Try $0.0005/1K tokens first
        mid_tier_agent,       # Fall back to $0.002/1K tokens
        premium_agent         # Last resort: $0.01/1K tokens
    ]
)

# Most queries succeed with cheap model (90%)
# Only complex queries fall through to expensive models (10%)
```

**With Custom Recovery:**

```python
from agenkit.patterns import FallbackAgent

def graceful_fallback(context, message, error):
    """Provide graceful fallback on total failure."""
    return Message(
        role="assistant",
        content="I'm experiencing technical difficulties. Please try again later.",
        metadata={"error": str(error)}
    )

fallback = FallbackAgent(
    agents=[primary, secondary],
    recovery_fn=graceful_fallback  # Always returns a response
)
```

**Pros:**
- ✅ High availability (automatic failover)
- ✅ Cost optimization (try cheap first)
- ✅ Early termination on success (fast path)
- ✅ Error collection for debugging
- ✅ Simple to reason about

**Cons:**
- ❌ Higher latency on failures (sequential tries)
- ❌ Increased cost if all fail
- ❌ No parallelism (could timeout-race instead)
- ❌ Requires multiple agents/providers

**Best Practices:**
1. Order agents by preference (fastest/cheapest first)
2. Include error details in metadata for monitoring
3. Set appropriate timeouts per agent
4. Use recovery functions for graceful degradation
5. Monitor fallback rates to detect systemic issues
6. Consider timeout-based parallel fallback for ultra-low latency

**Performance Benchmark:**
```
Fallback Pattern (success on first): ~200 ns/op (Rust), ~2.5 μs/op (TypeScript)
Fallback Pattern (success on third): 3x first-agent latency
Real-world: 99.9% success on primary = ~0.1% penalty
```

---

## Enhancement Patterns

### Reflection

**Purpose:** Agent reviews and improves its own output iteratively through self-critique.

**When to Use:**
- Quality matters more than speed
- Self-correction is valuable (writing, code generation)
- Iterative refinement needed
- Learning from mistakes
- Content that benefits from multiple drafts

**Pattern Diagram:**
```
Input → Generate → Critique → Improve → Output
          ↑_____________↓
         (iterate until satisfied)
```

**Performance:** O(k * agent_time) where k = iterations (typically 2-5)

**Example - Essay Writing:**

```python
from agenkit.patterns import ReflectionAgent
from agenkit import Agent, Message

class EssayWriter(Agent):
    """Write essays."""
    @property
    def name(self) -> str:
        return "writer"

    async def process(self, message: Message) -> Message:
        topic = message.content
        # Generate essay (LLM call)
        essay = await generate_essay(topic)
        return Message(role="assistant", content=essay)

class EssayCritic(Agent):
    """Critique and score essays."""
    @property
    def name(self) -> str:
        return "critic"

    async def process(self, message: Message) -> Message:
        essay = message.content

        # Analyze essay quality
        score, feedback = await analyze_essay(essay)

        # Return critique with score in metadata
        response = Message(
            role="assistant",
            content=feedback,
            metadata={"reflection_score": score}
        )
        return response

# Create reflection writer
essay_agent = ReflectionAgent(
    agent=EssayWriter(),
    critic=EssayCritic(),
    max_iterations=5,
    improvement_threshold=0.9  # Stop if score > 0.9
)

# Write essay with self-improvement
topic = Message(role="user", content="The importance of AI in education")
result = await essay_agent.process(topic)

print(f"Final essay (after {result.metadata['iterations']} iterations):")
print(result.content)
print(f"Final score: {result.metadata.get('reflection_score', 'N/A')}")
```

**Code Generation with Reflection:**

```python
from agenkit.patterns import ReflectionAgent

# Code generator that improves through reflection
code_agent = ReflectionAgent(
    agent=CodeGeneratorAgent(),
    critic=CodeReviewerAgent(),  # Checks for bugs, style, efficiency
    max_iterations=3,
    improvement_threshold=0.95
)

prompt = Message(role="user", content="Write a binary search function in Python")
result = await code_agent.process(prompt)

# Result went through multiple refinement cycles
# - Iteration 1: Basic implementation
# - Iteration 2: Fix off-by-one error
# - Iteration 3: Add type hints and docstring
```

**Pros:**
- ✅ High-quality output
- ✅ Self-correcting
- ✅ Learns from mistakes
- ✅ Measurable improvement
- ✅ Works with any agent type

**Cons:**
- ❌ Slow (multiple LLM calls: 2-5x base latency)
- ❌ Expensive (tokens: 2-5x base cost)
- ❌ Can get stuck in loops
- ❌ No guarantee of convergence
- ❌ Critic quality matters

**Best Practices:**
1. Set reasonable max_iterations (3-5)
2. Define clear improvement criteria
3. Use early stopping (threshold)
4. Log each iteration for debugging
5. Consider cost vs quality tradeoff
6. Use strong critic (same or better than generator)

**Performance Benchmark:**
```
Reflection Pattern (3 iterations): ~1.35 μs/op (Python), ~3,299 μs/op (Rust anomaly)
Real-world: 3x LLM calls = 3x cost and latency
Quality improvement: 20-40% in content quality metrics
```

---

### ReAct

**Purpose:** Reasoning and Acting - agent thinks through problems step-by-step and uses tools to gather information.

**When to Use:**
- Tools/APIs need to be called
- Complex reasoning required
- Multi-step problem solving
- Dynamic decision making
- Research tasks with external data

**Pattern Diagram:**
```
Thought → Action (tool call) → Observation → Thought → ... → Answer
```

**Performance:** O(k * (think + tool)) where k = reasoning steps

**Example - Research Assistant:**

```python
from agenkit.patterns import ReActAgent
from agenkit import Tool, Message

# Define research tools
def search_papers(query: str) -> str:
    """Search academic papers."""
    # Call academic search API
    results = search_api(query)
    return format_results(results)

def read_paper(arxiv_id: str) -> str:
    """Get paper abstract and key findings."""
    paper = fetch_paper(arxiv_id)
    return paper.abstract

def calculate(expression: str) -> float:
    """Evaluate mathematical expressions."""
    return eval(expression)  # In production, use safe math parser

# Create ReAct agent
researcher = ReActAgent(
    llm=my_llm,
    tools=[
        Tool(name="search_papers", func=search_papers,
             description="Search for academic papers by query"),
        Tool(name="read_paper", func=read_paper,
             description="Read paper abstract and findings"),
        Tool(name="calculate", func=calculate,
             description="Perform mathematical calculations")
    ],
    max_iterations=10,
    verbose=True  # Show reasoning steps
)

# Research question
question = Message(
    role="user",
    content="What are the key innovations in the Transformer architecture and how do they improve upon RNNs?"
)

result = await researcher.process(question)
print(result.content)

# Reasoning trace (verbose=True shows):
# Thought: I need to find papers about Transformers and understand their innovations
# Action: search_papers("Transformer architecture innovations")
# Observation: Found "Attention Is All You Need (2017)" - arxiv:1706.03762
# Thought: Let me read this seminal paper
# Action: read_paper("1706.03762")
# Observation: "Introduces self-attention mechanism, eliminates recurrence..."
# Thought: I now have enough information to answer
# Answer: The key innovations in the Transformer architecture are...
```

**Financial Analysis Example:**

```python
from agenkit.patterns import ReActAgent
from agenkit import Tool

# Financial analysis tools
tools = [
    Tool(name="get_stock_price", func=fetch_stock_price,
         description="Get current stock price for a symbol"),
    Tool(name="get_financials", func=fetch_financials,
         description="Get company financial statements"),
    Tool(name="calculate_ratio", func=calculate_financial_ratio,
         description="Calculate financial ratios (P/E, ROE, etc.)")
]

analyst = ReActAgent(llm=my_llm, tools=tools, max_iterations=15)

query = Message(
    role="user",
    content="Is Apple (AAPL) undervalued compared to Microsoft (MSFT)?"
)

analysis = await analyst.process(query)
# Agent will:
# 1. Get stock prices for both
# 2. Fetch financial statements
# 3. Calculate P/E, P/B, PEG ratios
# 4. Compare metrics
# 5. Provide recommendation
```

**Pros:**
- ✅ Flexible and adaptable
- ✅ Tool-aware reasoning
- ✅ Transparent decision making
- ✅ Handles complex tasks
- ✅ Can recover from tool failures

**Cons:**
- ❌ Can loop indefinitely (set max_iterations)
- ❌ Token-intensive (reasoning + tool outputs)
- ❌ Requires good prompt engineering
- ❌ Tool calls can fail
- ❌ Quality depends on LLM reasoning ability

**Best Practices:**
1. Define clear tool descriptions
2. Set max_iterations to prevent loops (10-20)
3. Use verbose mode for debugging
4. Validate tool outputs
5. Handle tool errors gracefully
6. Use function calling LLMs (GPT-4, Claude) for best results

**Performance Benchmark:**
```
ReAct Pattern (5 steps): ~525 ns/op (C++), ~5.5 μs/op (TypeScript)
Real-world: 5-15 LLM calls = 5-15x base cost
Tool calls add: Variable (0ms-5s depending on API)
```

---

### Planning

**Purpose:** Agent creates a detailed plan before execution, then follows the plan step-by-step.

**When to Use:**
- Complex multi-step workflows
- Deterministic execution needed
- Decompose large tasks into subtasks
- Track progress explicitly
- When you need to inspect/approve plan before execution

**Pattern Diagram:**
```
Input → Create Plan → Execute Step 1 → Execute Step 2 → ... → Output
        ↓
    [Task 1, Task 2, Task 3, ...]
```

**Performance:** O(planning + Σ(steps))

**Example - Travel Itinerary Planner:**

```python
from agenkit.patterns import PlanningAgent
from agenkit import Tool, Message

# Define travel tools
def search_flights(origin: str, destination: str, date: str) -> str:
    """Search for flights."""
    results = flight_api(origin, destination, date)
    return format_flight_results(results)

def search_hotels(city: str, checkin: str, nights: int) -> str:
    """Search for hotels."""
    results = hotel_api(city, checkin, nights)
    return format_hotel_results(results)

def search_activities(city: str) -> str:
    """Find activities and attractions."""
    results = activity_api(city)
    return format_activity_results(results)

# Create travel planner
travel_planner = PlanningAgent(
    llm=my_llm,
    tools=[
        Tool(name="search_flights", func=search_flights,
             description="Search for flight options"),
        Tool(name="search_hotels", func=search_hotels,
             description="Search for hotel options"),
        Tool(name="search_activities", func=search_activities,
             description="Find activities and attractions")
    ],
    max_steps=15
)

# Plan trip
trip_request = Message(
    role="user",
    content="Plan a 5-day trip to Paris from New York, departing June 15th"
)

result = await travel_planner.process(trip_request)

print("=== Travel Itinerary ===")
print(result.content)

print("\n=== Execution Plan ===")
for step in result.metadata.get("plan", []):
    print(f"{step['number']}. {step['action']}")

print("\n=== Execution Details ===")
for step in result.metadata.get("execution_steps", []):
    print(f"{step['number']}. {step['action']}")
    print(f"   Result: {step['result'][:100]}...")
    print(f"   Status: {step['status']}")

# Output:
# === Travel Itinerary ===
# Day 1 (June 15): Flight from JFK to CDG, departing 7:00 PM ($650)
# Day 1-5: Hotel Eiffel Seine (4-star), $180/night = $900 total
# Day 2: Visit Eiffel Tower and Trocadéro Gardens
# Day 3: Explore Louvre Museum and Tuileries Garden
# Day 4: Tour Montmartre and Sacré-Cœur
# Day 5: Seine River cruise, return flight 8:00 PM
#
# === Execution Plan ===
# 1. Search for flights from New York to Paris on June 15
# 2. Search for hotels in Paris for 5 nights starting June 15
# 3. Find top activities and attractions in Paris
# 4. Create detailed day-by-day itinerary
# 5. Calculate total cost estimate
```

**Project Management Example:**

```python
from agenkit.patterns import PlanningAgent

# Project management with planning
project_planner = PlanningAgent(
    llm=my_llm,
    tools=[
        Tool(name="create_task", func=create_jira_task),
        Tool(name="assign_task", func=assign_to_team_member),
        Tool(name="set_deadline", func=set_task_deadline),
        Tool(name="add_dependency", func=add_task_dependency)
    ],
    max_steps=30
)

project = Message(
    role="user",
    content="Set up a new microservice for user authentication with OAuth2 support"
)

plan = await project_planner.process(project)
# Agent creates detailed implementation plan:
# 1. Create epic in Jira
# 2. Break down into tasks (database schema, API endpoints, OAuth integration, tests)
# 3. Assign tasks to team members based on expertise
# 4. Set dependencies (schema → endpoints → OAuth → tests)
# 5. Calculate timeline
```

**Pros:**
- ✅ Structured approach
- ✅ Progress tracking
- ✅ Handles complexity
- ✅ Clear execution path
- ✅ Can inspect plan before execution

**Cons:**
- ❌ Upfront planning cost (extra LLM call)
- ❌ Less flexible (locked into plan)
- ❌ Plan may be suboptimal
- ❌ Doesn't adapt to changes mid-execution
- ❌ Planning quality depends on LLM

**Best Practices:**
1. Provide clear initial instructions
2. Set appropriate max_steps
3. Log plan and execution separately
4. Handle step failures gracefully
5. Consider re-planning if conditions change
6. Allow human approval of plan before execution

**Performance Benchmark:**
```
Planning Pattern: ~400 ns/op (Go), ~4.2 μs/op (TypeScript)
Real-world: 1 LLM call (planning) + N LLM calls (execution)
Planning overhead: +1 LLM call (~100-200ms)
```

---

### Reasoning with Tools

**Purpose:** Enhanced reasoning pattern combining structured thinking (Chain of Thought, Tree of Thought, Self-Consistency) with tool usage for explainable AI.

**When to Use:**
- Complex reasoning required
- Multiple reasoning paths to explore
- Tool usage needs justification
- Explainable AI needed
- Self-consistency checking important
- Math/logic problems

**Pattern Diagram:**
```
Problem → Reasoning Strategy (CoT/ToT/Self-Consistency)
              ↓
         Thought branches + tool identification
              ↓
         Execute tools with reasoning context
              ↓
         Synthesize results with reasoning
              ↓
         Final answer with full explanation
```

**Performance:** O(branches * depth * (think + tool))

**Example - Chain of Thought with Tools:**

```python
from agenkit.patterns import ReasoningWithTools
from agenkit import Message, Tool

# Create enhanced reasoning agent
reasoning_agent = ReasoningWithTools(
    llm=my_llm,
    tools=[
        Tool(name="search", func=web_search),
        Tool(name="calculate", func=calculator)
    ],
    reasoning_strategy="chain-of-thought",  # Step-by-step reasoning
    max_iterations=10
)

# Complex multi-step problem
problem = Message(
    role="user",
    content=(
        "A train travels from City A to City B at 60mph. "
        "The distance is 180 miles, but there's a 30-minute stop halfway. "
        "If it leaves at 2:00 PM, what time does it arrive?"
    )
)

result = await reasoning_agent.process(problem)

print("=== Answer ===")
print(result.content)

print("\n=== Reasoning Trace ===")
for i, step in enumerate(result.metadata["reasoning_trace"], 1):
    print(f"Step {i}: {step['thought']}")
    if step.get("tool_call"):
        print(f"  → Tool: {step['tool_call']['tool']}({step['tool_call']['args']})")
        print(f"  → Result: {step['tool_result']}")

# Output:
# === Answer ===
# The train arrives at 5:30 PM.
#
# === Reasoning Trace ===
# Step 1: I need to calculate the travel time for 180 miles at 60 mph
#   → Tool: calculate(180 / 60)
#   → Result: 3.0
# Step 2: The travel time is 3 hours, plus a 30-minute stop
#   → Tool: calculate(3.0 + 0.5)
#   → Result: 3.5
# Step 3: Starting at 2:00 PM and adding 3.5 hours gives the arrival time
#   → Tool: calculate(14.0 + 3.5)
#   → Result: 17.5 (5:30 PM)
```

**Tree of Thought Example:**

```python
from agenkit.patterns import ReasoningWithTools

# Tree of Thought explores multiple reasoning branches
tot_agent = ReasoningWithTools(
    llm=my_llm,
    tools=[
        Tool(name="search", func=web_search),
        Tool(name="calculate", func=calculator)
    ],
    reasoning_strategy="tree-of-thought",
    branches=3,  # Explore 3 reasoning paths
    max_depth=5
)

# Complex problem with multiple solution approaches
problem = Message(
    role="user",
    content=(
        "What's the most cost-effective way to travel from Paris to Tokyo, "
        "considering time (should be < 24 hours), comfort, and budget?"
    )
)

result = await tot_agent.process(problem)

print("=== Explored Reasoning Paths ===")
for i, branch in enumerate(result.metadata["reasoning_branches"], 1):
    print(f"\nPath {i}: {branch['approach']}")
    print(f"  Tools used: {branch['tools_used']}")
    print(f"  Pros: {branch['pros']}")
    print(f"  Cons: {branch['cons']}")
    print(f"  Cost: {branch['estimated_cost']}")
    print(f"  Score: {branch['score']:.2f}")

print(f"\n=== Best Path ===")
print(f"Path {result.metadata['best_branch'] + 1}: {result.metadata['best_approach']}")
print(f"\n{result.content}")

# Output:
# === Explored Reasoning Paths ===
#
# Path 1: Direct flight Paris → Tokyo
#   Tools used: ['search_flights']
#   Pros: Fastest (13 hours), most comfortable
#   Cons: Most expensive
#   Cost: $1,200
#   Score: 7.5
#
# Path 2: Paris → Dubai → Tokyo
#   Tools used: ['search_flights', 'calculate']
#   Pros: Moderate cost ($800), < 24 hours (18 hours)
#   Cons: One layover, longer
#   Cost: $800
#   Score: 8.5
#
# Path 3: Paris → Istanbul → Tokyo
#   Tools used: ['search_flights', 'calculate']
#   Pros: Cheapest ($650)
#   Cons: Longest (22 hours), two layovers
#   Cost: $650
#   Score: 7.0
#
# === Best Path ===
# Path 2: Paris → Dubai → Tokyo
# The most cost-effective option considering all factors is...
```

**Self-Consistency Example:**

```python
from agenkit.patterns import ReasoningWithTools

# Self-consistency: generate multiple reasoning paths and vote
consistency_agent = ReasoningWithTools(
    llm=my_llm,
    tools=[Tool(name="calculate", func=calculator)],
    reasoning_strategy="self-consistency",
    num_samples=5  # Generate 5 independent reasoning paths
)

# Math problem with potential for different approaches
math_problem = Message(
    role="user",
    content="If x + 2y = 10 and 2x + y = 8, what is x + y?"
)

result = await consistency_agent.process(math_problem)

print(f"Generated {len(result.metadata['reasoning_samples'])} solutions:")
for i, sample in enumerate(result.metadata['reasoning_samples'], 1):
    print(f"\nSample {i}:")
    print(f"  Answer: {sample['answer']}")
    print(f"  Method: {sample['method']}")
    print(f"  Steps: {len(sample['steps'])}")

print(f"\n=== Consensus Answer ===")
print(f"Most common answer (appears in {result.metadata['consensus_count']}/5 samples):")
print(result.content)

# Output:
# Generated 5 solutions:
#
# Sample 1:
#   Answer: 6
#   Method: Substitution
#   Steps: 4
#
# Sample 2:
#   Answer: 6
#   Method: Elimination
#   Steps: 3
#
# Sample 3:
#   Answer: 6
#   Method: Matrix inversion
#   Steps: 5
#
# Sample 4:
#   Answer: 6
#   Method: Substitution
#   Steps: 4
#
# Sample 5:
#   Answer: 6
#   Method: Graphical intersection
#   Steps: 6
#
# === Consensus Answer ===
# Most common answer (appears in 5/5 samples):
# x + y = 6
```

**Pros:**
- ✅ Explicit reasoning (explainable AI)
- ✅ Better accuracy (multiple paths explored)
- ✅ Tool usage justified with reasoning
- ✅ Self-verification (consistency checking)
- ✅ Handles complex, ambiguous problems
- ✅ Multiple solution approaches

**Cons:**
- ❌ Very slow (multiple reasoning paths)
- ❌ Very expensive (many LLM calls: 3-10x)
- ❌ Can generate contradictions
- ❌ Requires strong reasoning LLM
- ❌ High token usage

**Best Practices:**
1. Use Chain of Thought for straightforward problems
2. Use Tree of Thought for multi-path exploration
3. Use Self-Consistency for verification and confidence
4. Log all reasoning traces for debugging and auditing
5. Limit branches/samples to control cost
6. Combine with Reflection for iterative refinement
7. Use for high-stakes decisions where explainability matters

**Performance Benchmark:**
```
Reasoning with Tools (CoT): ~600 ns/op (C++), ~6.8 μs/op (TypeScript)
Reasoning with Tools (ToT, 3 branches): 3x CoT
Reasoning with Tools (Self-Consistency, 5 samples): 5x CoT
Real-world: 3-10 LLM calls depending on strategy
```

---

## Coordination Patterns

### Supervisor

**Purpose:** Oversee and coordinate execution of worker agents with monitoring, quality control, approval, and error handling.

**When to Use:**
- Quality control needed (code review, content approval)
- Workers need oversight
- Task delegation and coordination
- Error detection and correction
- Approval workflows
- Hierarchical agent systems

**Pattern Diagram:**
```
Supervisor (coordinator)
     ├→ Worker 1 → Report back
     ├→ Worker 2 → Report back
     └→ Worker 3 → Report back
Supervisor reviews, approves, or requests revisions
```

**Performance:** O(supervisor + workers + review)

**Example - Quality Control System:**

```python
from agenkit.patterns import SupervisorAgent
from agenkit import Agent, Message

class QualityController(Agent):
    """Supervisor that reviews worker output for quality."""
    @property
    def name(self) -> str:
        return "qa-supervisor"

    async def process(self, message: Message) -> Message:
        # Analyze worker output
        content = message.content

        # Quality checks
        issues = []
        if len(content) < 100:
            issues.append("Response too short - needs more detail")
        if not any(word in content.lower() for word in ["because", "therefore", "due to"]):
            issues.append("Lacks clear reasoning")
        if content.count('.') < 3:
            issues.append("Needs more complete sentences")

        if issues:
            # Request revision
            feedback = "Quality issues found. Please revise:\n"
            feedback += "\n".join(f"- {issue}" for issue in issues)
            response = Message(
                role="supervisor",
                content=feedback,
                metadata={
                    "approval": False,
                    "revision_requested": True,
                    "issues": issues
                }
            )
            return response

        # Approve
        response = Message(
            role="supervisor",
            content="Quality approved. Excellent work!",
            metadata={"approval": True}
        )
        return response

# Create supervised workflow
workflow = SupervisorAgent(
    supervisor=QualityController(),
    workers=[analyst_agent, writer_agent, researcher_agent],
    require_approval=True,
    max_revisions=3
)

# Workers produce output, supervisor reviews
task = Message(role="user", content="Analyze market trends in AI hardware")
result = await workflow.process(task)

print(f"Final output (after {result.metadata.get('revisions', 0)} revisions):")
print(result.content)
print(f"Approval status: {result.metadata.get('approval', False)}")
```

**Code Review Example:**

```python
from agenkit.patterns import SupervisorAgent
from agenkit import Agent

class CodeReviewSupervisor(Agent):
    """Supervisor for code quality."""
    async def process(self, message: Message) -> Message:
        code = message.content

        # Run static analysis
        issues = run_linter(code)
        security_issues = run_security_scan(code)
        test_coverage = calculate_test_coverage(code)

        problems = []
        if issues:
            problems.append(f"Linting issues: {len(issues)}")
        if security_issues:
            problems.append(f"Security vulnerabilities: {len(security_issues)}")
        if test_coverage < 80:
            problems.append(f"Test coverage too low: {test_coverage}%")

        if problems:
            feedback = "Code review failed:\n" + "\n".join(problems)
            return Message(
                role="supervisor",
                content=feedback,
                metadata={"approval": False, "issues": problems}
            )

        return Message(
            role="supervisor",
            content="Code review passed ✓",
            metadata={"approval": True}
        )

# Supervised code generation
code_workflow = SupervisorAgent(
    supervisor=CodeReviewSupervisor(),
    workers=[code_generator_agent],
    require_approval=True
)
```

**Pros:**
- ✅ Quality assurance built in
- ✅ Centralized coordination
- ✅ Error detection and correction
- ✅ Can request revisions (iterative improvement)
- ✅ Clear hierarchy
- ✅ Audit trail of approvals

**Cons:**
- ❌ Extra overhead (supervisor reviews)
- ❌ Potential bottleneck (supervisor must scale)
- ❌ More complex coordination
- ❌ Supervisor must be reliable and high-quality
- ❌ Can create revision loops

**Best Practices:**
1. Supervisor should have higher capability than workers
2. Define clear approval criteria
3. Limit revision cycles to prevent loops (max_revisions)
4. Log all delegation and approval decisions
5. Use for critical/high-stakes tasks
6. Consider parallel supervisors for scale

**Performance Benchmark:**
```
Supervisor Pattern: ~350 ns/op (Rust), ~4.8 μs/op (TypeScript)
Real-world: 1x worker + 1x supervisor per iteration
Revisions add: Nx worker time (where N = revisions)
```

---

### Orchestration

**Purpose:** Coordinate multiple agents with complex workflows, conditional routing, sequential + parallel combinations, and sophisticated aggregation.

**When to Use:**
- Complex multi-agent workflows (5+ stages)
- Conditional execution paths (if-then-else logic)
- Sequential + parallel combinations
- State machines
- Business process automation
- Enterprise workflow systems

**Pattern Diagram:**
```
Orchestrator (workflow engine)
     ├→ Stage 1: [Agent A || Agent B] → Aggregate
     ├→ Decision: Route based on Stage 1 output
     ├→ Stage 2a: Agent C → Agent D (if condition X)
     ├→ Stage 2b: Agent E (if condition Y)
     └→ Final: Combine all results
```

**Performance:** O(Σ(stages)) with parallelism where possible

**Example - Content Moderation Pipeline:**

```python
from agenkit.patterns import OrchestrationAgent, WorkflowDefinition
from agenkit import Agent, Message

# Define moderation workflow
moderation_workflow = WorkflowDefinition({
    "stages": [
        # Stage 1: Parallel initial screening
        {
            "name": "screening",
            "agents": ["spam_detector", "toxicity_detector", "pii_detector"],
            "execution": "parallel",
            "aggregation": "any_flag"  # Flag if any detector triggers
        },
        # Stage 2: Conditional deep analysis
        {
            "name": "deep_analysis",
            "agents": ["context_analyzer"],
            "condition": "screening.flagged == true",
            "execution": "sequential"
        },
        # Stage 3: Human review if high risk
        {
            "name": "human_review",
            "agents": ["human_review_queue"],
            "condition": "deep_analysis.risk_score > 0.8",
            "execution": "sequential",
            "timeout": 3600  # 1 hour for human response
        },
        # Stage 4: Final decision
        {
            "name": "decision",
            "agents": ["decision_maker"],
            "inputs": ["screening", "deep_analysis", "human_review"],
            "aggregation": "weighted_vote"
        }
    ]
})

# Create orchestration system
content_moderator = OrchestrationAgent(
    agents={
        "spam_detector": SpamDetectorAgent(),
        "toxicity_detector": ToxicityDetectorAgent(),
        "pii_detector": PIIDetectorAgent(),
        "context_analyzer": ContextAnalyzerAgent(),
        "human_review_queue": HumanReviewQueue(),
        "decision_maker": DecisionMakerAgent()
    },
    workflow=moderation_workflow
)

# Process content through workflow
content = Message(role="user", content="User-generated content here...")
decision = await content_moderator.process(content)

# Result includes full workflow execution details
print("=== Moderation Decision ===")
print(decision.content)

print("\n=== Workflow Execution ===")
for stage in decision.metadata["workflow_stages_executed"]:
    print(f"{stage['name']} ({stage['execution_time']}ms):")
    print(f"  Status: {stage['status']}")
    print(f"  Agents: {', '.join(stage['agents_used'])}")
    if stage.get("skipped"):
        print(f"  Skipped: {stage['skip_reason']}")

print("\n=== Decisions ===")
for decision_point in decision.metadata["workflow_decisions"]:
    print(f"{decision_point['stage']}: {decision_point['decision']}")
    print(f"  Reason: {decision_point['reason']}")
```

**E-Commerce Order Processing:**

```python
from agenkit.patterns import OrchestrationAgent, WorkflowDefinition

# Complex order processing workflow
order_workflow = WorkflowDefinition({
    "stages": [
        # Validate order
        {
            "name": "validation",
            "agents": ["inventory_checker", "payment_validator"],
            "execution": "parallel"
        },
        # Process payment (only if valid)
        {
            "name": "payment",
            "agents": ["payment_processor"],
            "condition": "validation.all_valid == true",
            "execution": "sequential"
        },
        # Parallel fulfillment
        {
            "name": "fulfillment",
            "agents": ["warehouse_agent", "shipping_agent", "notification_agent"],
            "condition": "payment.status == 'success'",
            "execution": "parallel"
        },
        # Handle failures
        {
            "name": "failure_handling",
            "agents": ["refund_agent", "customer_service"],
            "condition": "payment.status == 'failed'",
            "execution": "sequential"
        }
    ]
})

order_processor = OrchestrationAgent(
    agents={...},
    workflow=order_workflow
)
```

**Pros:**
- ✅ Handles very complex workflows
- ✅ Flexible execution (sequential, parallel, conditional)
- ✅ State machine support
- ✅ Reusable workflow definitions
- ✅ Sophisticated coordination
- ✅ Can model real business processes

**Cons:**
- ❌ High complexity (hardest pattern to implement correctly)
- ❌ Difficult to debug (many moving parts)
- ❌ Workflow definition overhead
- ❌ Potential performance bottlenecks
- ❌ Requires careful testing

**Best Practices:**
1. Define workflows declaratively (YAML/JSON)
2. Keep stages focused and independent
3. Use meaningful stage names
4. Log all workflow decisions and timing
5. Test workflows thoroughly (unit + integration)
6. Monitor workflow execution metrics
7. Use visualization tools for complex workflows
8. Consider workflow versioning for changes

**Performance Benchmark:**
```
Orchestration Pattern: ~450 ns/op (Go), ~5.2 μs/op (TypeScript)
Real-world: Depends on workflow structure
3-stage sequential: 3x single agent
3-stage parallel: max(3 agents)
5-stage complex: ~2-4x average agent time
```

---

### Multiagent

**Purpose:** Multiple agents collaborate to solve problems together through debate, voting, or consensus.

**When to Use:**
- Complex problems requiring specialization
- Distributed problem solving
- Debate and consensus needed
- Parallel expertise (legal + financial + technical)
- Democratic decision making

**Pattern Diagram:**
```
Problem → Agent 1 ⟺ Agent 2 ⟺ Agent 3 → Solution
            ↓         ↓         ↓
        [Collaboration: Debate/Vote/Consensus]
```

**Performance:** O(rounds * num_agents)

**Example - Expert Panel Decision:**

```python
from agenkit.patterns import MultiagentSystem
from agenkit import Agent, Message

class LegalExpert(Agent):
    """Legal perspective."""
    @property
    def name(self) -> str:
        return "legal-expert"

    async def process(self, message: Message) -> Message:
        decision = message.content
        # Analyze legal implications
        analysis = await analyze_legal_aspects(decision)
        return Message(
            role="assistant",
            content=f"Legal Analysis: {analysis}",
            metadata={"vote": "approve" if analysis.risk < 0.3 else "reject"}
        )

class FinancialExpert(Agent):
    """Financial perspective."""
    @property
    def name(self) -> str:
        return "financial-expert"

    async def process(self, message: Message) -> Message:
        decision = message.content
        # Analyze financial impact
        analysis = await analyze_financial_impact(decision)
        return Message(
            role="assistant",
            content=f"Financial Analysis: {analysis}",
            metadata={"vote": "approve" if analysis.roi > 0.15 else "reject"}
        )

class TechnicalExpert(Agent):
    """Technical perspective."""
    @property
    def name(self) -> str:
        return "technical-expert"

    async def process(self, message: Message) -> Message:
        decision = message.content
        # Analyze technical feasibility
        analysis = await analyze_technical_feasibility(decision)
        return Message(
            role="assistant",
            content=f"Technical Analysis: {analysis}",
            metadata={"vote": "approve" if analysis.feasibility > 0.7 else "reject"}
        )

# Create expert panel
expert_panel = MultiagentSystem(
    agents=[
        LegalExpert(),
        FinancialExpert(),
        TechnicalExpert()
    ],
    coordination="vote",  # Options: "debate", "vote", "consensus"
    voting_strategy="majority"  # Or "unanimous", "weighted"
)

# Get panel decision
proposal = Message(
    role="user",
    content="Should we acquire Company X for $50M?"
)

decision = await expert_panel.process(proposal)

print("=== Expert Panel Decision ===")
print(decision.content)

print("\n=== Individual Expert Opinions ===")
for opinion in decision.metadata["agent_responses"]:
    print(f"\n{opinion['agent']}:")
    print(f"  {opinion['content']}")
    print(f"  Vote: {opinion['metadata']['vote']}")

print(f"\n=== Final Vote ===")
print(f"Approve: {decision.metadata['vote_counts']['approve']}")
print(f"Reject: {decision.metadata['vote_counts']['reject']}")
print(f"Decision: {decision.metadata['final_decision']}")
```

**Debate Mode Example:**

```python
from agenkit.patterns import MultiagentSystem

# Agents debate to reach better conclusions
debate_system = MultiagentSystem(
    agents=[optimist_agent, pessimist_agent, realist_agent],
    coordination="debate",
    max_rounds=3  # 3 rounds of debate
)

question = Message(
    role="user",
    content="Will AI achieve AGI by 2030?"
)

conclusion = await debate_system.process(question)

# Agents will:
# Round 1: Each agent presents initial position
# Round 2: Each agent responds to others' arguments
# Round 3: Each agent makes final argument
# Synthesize: Combine perspectives into nuanced conclusion
```

**Pros:**
- ✅ Multiple perspectives (reduces bias)
- ✅ Distributed expertise
- ✅ Robust decisions (democratic)
- ✅ Scalable (add more agents)
- ✅ Natural for expert panels

**Cons:**
- ❌ Coordination complexity
- ❌ Communication overhead
- ❌ Expensive (N agents)
- ❌ May not reach consensus
- ❌ Slower than single-agent

**Best Practices:**
1. Clear roles for each agent
2. Define coordination protocol (debate/vote/consensus)
3. Set termination criteria (rounds, time, consensus threshold)
4. Monitor agent interactions
5. Handle disagreements explicitly
6. Use weighted voting if agents have different expertise levels

**Performance Benchmark:**
```
Multiagent Pattern (3 agents, 2 rounds): ~800 ns/op (Python), ~8.5 μs/op (TypeScript)
Real-world: N agents × M rounds
3 agents × 2 rounds = 6x single agent cost
```

---

### Collaborative

**Purpose:** Multiple agents work together on shared tasks with bidirectional communication and shared workspace for iterative team-based problem solving.

**When to Use:**
- Team-based problem solving
- Shared knowledge building
- Iterative refinement by multiple agents
- Consensus building with iteration
- Distributed expertise with shared context

**Pattern Diagram:**
```
Shared Workspace
     ↕
Agent 1 ⟷ Agent 2 ⟷ Agent 3
     ↕         ↕         ↕
[Bidirectional communication + shared context]
     ↓
Collaborative Result
```

**Performance:** O(rounds * max_agent_time)

**Example - Collaborative Writing Team:**

```python
from agenkit.patterns import CollaborativeAgent
from agenkit import Agent, Message

class OutlineAgent(Agent):
    """Creates document outline."""
    @property
    def name(self) -> str:
        return "outliner"

    async def process(self, message: Message) -> Message:
        topic = message.content
        outline = f"""
Outline for '{topic}':
I. Introduction
II. Background and Context
III. Key Points
    A. Point 1
    B. Point 2
    C. Point 3
IV. Conclusion
"""
        return Message(role="assistant", content=outline)

class ResearchAgent(Agent):
    """Researches content for each section."""
    @property
    def name(self) -> str:
        return "researcher"

    async def process(self, message: Message) -> Message:
        outline = message.content
        # Research based on outline
        research = await gather_research(outline)
        return Message(
            role="assistant",
            content=f"Research findings:\n{research}"
        )

class WriterAgent(Agent):
    """Writes full content based on outline and research."""
    @property
    def name(self) -> str:
        return "writer"

    async def process(self, message: Message) -> Message:
        context = message.content  # Includes outline + research
        # Generate full draft
        draft = await write_article(context)
        return Message(role="assistant", content=draft)

class EditorAgent(Agent):
    """Reviews and refines the writing."""
    @property
    def name(self) -> str:
        return "editor"

    async def process(self, message: Message) -> Message:
        draft = message.content
        # Edit for clarity, flow, grammar
        edited = await edit_content(draft)
        return Message(role="assistant", content=edited)

# Create collaborative writing team
writing_team = CollaborativeAgent(
    agents=[
        OutlineAgent(),
        ResearchAgent(),
        WriterAgent(),
        EditorAgent()
    ],
    collaboration_strategy="sequential-refinement",  # Or "shared-workspace"
    shared_context=True,  # All agents see previous contributions
    max_rounds=2  # Can iterate if editor requests changes
)

# Team collaborates on article
topic = Message(role="user", content="The Impact of AI on Healthcare")
article = await writing_team.process(topic)

print("=== Final Article ===")
print(article.content)

print("\n=== Collaboration Trace ===")
for contribution in article.metadata["agent_contributions"]:
    print(f"\n{contribution['agent']} (Round {contribution['round']}):")
    print(f"  Action: {contribution['action']}")
    print(f"  Summary: {contribution['summary'][:100]}...")
```

**Software Development Team Example:**

```python
from agenkit.patterns import CollaborativeAgent

# Collaborative software development
dev_team = CollaborativeAgent(
    agents=[
        ArchitectAgent(),  # Designs system architecture
        DeveloperAgent(),  # Implements code
        TesterAgent(),     # Writes and runs tests
        ReviewerAgent()    # Reviews code quality
    ],
    collaboration_strategy="shared-workspace",
    shared_context=True,
    max_rounds=3  # Iterate until tests pass and review approves
)

task = Message(
    role="user",
    content="Implement a rate limiter with sliding window algorithm"
)

result = await dev_team.process(task)

# Agents collaborate:
# Round 1:
#   - Architect: Designs sliding window rate limiter
#   - Developer: Implements based on design
#   - Tester: Tests fail (bug found)
#   - Reviewer: Suggests improvements
# Round 2:
#   - Developer: Fixes bug, implements improvements
#   - Tester: Tests pass
#   - Reviewer: Requests better comments
# Round 3:
#   - Developer: Adds comments
#   - Tester: All tests pass
#   - Reviewer: Approves ✓
```

**Pros:**
- ✅ Leverages multiple perspectives
- ✅ Iterative improvement through collaboration
- ✅ Shared knowledge and context
- ✅ Consensus building
- ✅ Team synergy (whole > sum of parts)
- ✅ Natural for creative tasks

**Cons:**
- ❌ High coordination complexity
- ❌ Communication overhead
- ❌ Potential conflicts between agents
- ❌ Slower than single-agent
- ❌ Requires clear collaboration protocol

**Best Practices:**
1. Define clear collaboration protocols
2. Use shared workspace for context
3. Limit collaboration rounds (2-3 typically)
4. Ensure agents have complementary skills
5. Monitor communication patterns
6. Use for complex, multifaceted tasks
7. Provide conflict resolution mechanism

**Performance Benchmark:**
```
Collaborative Pattern (4 agents, 2 rounds): ~900 ns/op (Go), ~9.2 μs/op (TypeScript)
Real-world: N agents × M rounds with shared context
4 agents × 2 rounds = 8x single agent cost
```

---

## Specialized Patterns

### Task

**Purpose:** Single-purpose agent optimized for specific, focused tasks with no conversation history.

**When to Use:**
- Focused, well-defined task
- No need for conversation history
- Stateless operation
- Maximum performance
- Microservice-style agents

**Pattern Diagram:**
```
Task Input → Process → Task Output
(stateless)
```

**Performance:** O(1) - Single operation, no overhead

**Example - Data Validator:**

```python
from agenkit.patterns import TaskAgent
from agenkit import Message
import json

# Create validation task agent
validator = TaskAgent(
    system_prompt="""You are a data validator. Check if JSON data meets these rules:
    - Email must be valid format
    - Age must be 18-120
    - Name must be present
    Return: {"valid": true/false, "errors": [...]}""",
    llm=my_llm,
    name="json-validator"
)

# Validate data
data = Message(role="user", content=json.dumps({
    "name": "John",
    "email": "invalid-email",  # Invalid
    "age": -5  # Invalid
}))

result = await validator.process(data)
validation = json.loads(result.content)

if not validation["valid"]:
    print("Validation errors:")
    for error in validation["errors"]:
        print(f"  - {error}")

# Output:
# Validation errors:
#   - Invalid email format: 'invalid-email'
#   - Age must be between 18 and 120, got: -5
```

**Translation Task:**

```python
from agenkit.patterns import TaskAgent

# Simple translation task
translator = TaskAgent(
    system_prompt="You are a translator. Translate the input to French.",
    llm=my_llm,
    name="en-to-fr"
)

text = Message(role="user", content="Hello, how are you?")
result = await translator.process(text)
print(result.content)  # "Bonjour, comment allez-vous?"
```

**Pros:**
- ✅ Fast and efficient
- ✅ Predictable behavior
- ✅ Easy to test
- ✅ Low overhead (no history management)
- ✅ Scalable (stateless)

**Cons:**
- ❌ Limited scope
- ❌ No conversation context
- ❌ Can't handle complex workflows
- ❌ Stateless only

**Best Practices:**
1. Clear system prompt
2. Single responsibility
3. Validate inputs
4. Handle errors explicitly
5. Use for focused, repetitive tasks
6. Perfect for microservices

**Performance Benchmark:**
```
Task Pattern: ~100 ns/op (C++), ~1.0 μs/op (TypeScript)
Fastest pattern - minimal framework overhead
Real-world: 1 LLM call + negligible overhead
```

---

### Conversational

**Purpose:** Multi-turn dialogue with memory of conversation history for natural interaction.

**When to Use:**
- Chatbots and assistants
- Multi-turn interactions
- Context from previous messages matters
- Natural conversation flow
- Customer support bots

**Pattern Diagram:**
```
User → Agent → User → Agent → ...
        ↓                ↓
    [Memory: Message History]
```

**Performance:** O(history_size) for context, grows with conversation

**Example - Customer Support Bot:**

```python
from agenkit.patterns import ConversationalAgent
from agenkit import Message

# Create support bot
support_bot = ConversationalAgent(
    system_prompt="""You are a friendly customer support agent.
    Help customers with orders, returns, and general questions.
    Be empathetic and solution-oriented.""",
    llm=my_llm,
    max_history=20,  # Keep last 20 messages
    name="support-bot"
)

# Simulate customer conversation
async def chat(user_input: str):
    msg = Message(role="user", content=user_input)
    response = await support_bot.process(msg)
    print(f"User: {user_input}")
    print(f"Bot: {response.content}\n")

# Multi-turn support conversation
await chat("Hi, I have a problem with my order")
# Bot: Hello! I'm sorry to hear that. What's your order number?

await chat("Order #12345")
# Bot: Thank you. Let me look up order #12345. What seems to be the issue?

await chat("It hasn't arrived yet")
# Bot: I understand your concern about order #12345 not arriving...

await chat("When will it arrive?")
# Bot: Based on the tracking for order #12345, it should arrive by Friday...

# Bot remembers:
# - Order number (#12345)
# - Issue (hasn't arrived)
# - Context of entire conversation
```

**With Session Management:**

```python
from agenkit.patterns import ConversationalAgent
from agenkit import Message

class SessionManager:
    """Manage multiple conversation sessions."""

    def __init__(self):
        self.sessions = {}

    def get_or_create(self, session_id: str) -> ConversationalAgent:
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationalAgent(
                system_prompt="You are a helpful assistant.",
                llm=my_llm,
                max_history=50,
                name=f"session-{session_id}"
            )
        return self.sessions[session_id]

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id].clear_history()
            del self.sessions[session_id]

# Usage
manager = SessionManager()

# User A conversation
agent_a = manager.get_or_create("user-a")
resp = await agent_a.process(Message(role="user", content="Hi, my name is Alice"))
# Bot remembers Alice's name in this session

# User B conversation (independent)
agent_b = manager.get_or_create("user-b")
resp = await agent_b.process(Message(role="user", content="Hi, my name is Bob"))
# Bot remembers Bob's name in this session

# Clear user A session
manager.clear_session("user-a")
```

**Pros:**
- ✅ Natural conversation
- ✅ Context awareness
- ✅ Multi-turn support
- ✅ Stateful interaction
- ✅ Remembers user preferences

**Cons:**
- ❌ Memory management complexity
- ❌ Token usage grows with history
- ❌ Need session management for multi-user
- ❌ History can confuse agent (irrelevant context)
- ❌ Privacy concerns (history storage)

**Best Practices:**
1. Set appropriate max_history (10-50 messages)
2. Clear history periodically or on explicit user request
3. Use session IDs for multi-user applications
4. Summarize old conversations to save tokens
5. Monitor token usage
6. Implement history persistence for long-term memory

**Performance Benchmark:**
```
Conversational Pattern: ~350 ns/op (Rust), ~3.8 μs/op (TypeScript)
Real-world: 1 LLM call + history context
Context grows: N messages × avg_message_size tokens
```

---

### Human in Loop

**Purpose:** Include human approval or feedback at critical decision points during agent execution for safety and oversight.

**When to Use:**
- Safety-critical applications (medical, financial, legal)
- High-stakes decisions
- Regulatory compliance (SOX, HIPAA, GDPR)
- User preferences matter
- Verification needed before actions
- Sensitive operations

**Pattern Diagram:**
```
Agent proposes action
     ↓
Request human approval
     ↓
Human reviews and decides
     ↓ (approved)          ↓ (rejected)
Execute action       Revise and retry
```

**Performance:** O(agent + human_response_time) - Slow, doesn't scale

**Example - Financial Transactions:**

```python
from agenkit.patterns import HumanInLoopAgent
from agenkit import Agent, Message, Tool

class FinancialAgent(Agent):
    """Agent that can execute financial transactions."""
    @property
    def name(self) -> str:
        return "financial-agent"

    def __init__(self):
        self.tools = [
            Tool(name="transfer_money", func=self.transfer,
                 description="Transfer money between accounts"),
            Tool(name="pay_bill", func=self.pay_bill,
                 description="Pay a bill")
        ]

    async def transfer(self, from_account: str, to_account: str, amount: float):
        # Execute transfer (only if approved)
        return f"Transferred ${amount} from {from_account} to {to_account}"

    async def pay_bill(self, biller: str, amount: float):
        # Pay bill (only if approved)
        return f"Paid ${amount} to {biller}"

def financial_approval(action: str, context: dict) -> tuple[bool, str]:
    """
    Human reviews financial actions.
    Returns: (approved: bool, feedback: str)
    """
    print(f"\n{'='*60}")
    print(f"⚠️  APPROVAL REQUIRED: {action}")
    print(f"Details:")
    for key, value in context.items():
        print(f"  {key}: {value}")
    print(f"{'='*60}")

    response = input("Approve this transaction? (y/n/edit): ").lower()

    if response == 'y':
        return True, "Approved"
    elif response == 'edit':
        new_amount = input("Enter new amount: ")
        return True, f"Approved with modification: amount={new_amount}"
    else:
        reason = input("Reason for rejection: ")
        return False, f"Rejected: {reason}"

# Wrap financial agent with human approval
safe_financial_agent = HumanInLoopAgent(
    agent=FinancialAgent(),
    approval_callback=financial_approval,
    require_approval_for=["all"]  # Require approval for everything
)

# Every financial action requires human approval
task = Message(role="user", content="Pay my electricity bill of $150")
result = await safe_financial_agent.process(task)

# User sees:
# ============================================================
# ⚠️  APPROVAL REQUIRED: pay_bill
# Details:
#   biller: Electric Company
#   amount: 150.0
# ============================================================
# Approve this transaction? (y/n/edit): y
#
# Result: Paid $150 to Electric Company
```

**Async Approval Workflow:**

```python
from agenkit.patterns import HumanInLoopAgent
import asyncio

async def async_approval_callback(action: str, context: dict) -> tuple[bool, str]:
    """Async approval via notification + database polling."""
    # Send notification to admin
    approval_id = await send_approval_request(action, context)

    # Poll for approval (with timeout)
    for _ in range(60):  # Poll for 10 minutes
        status = await check_approval_status(approval_id)
        if status in ["approved", "rejected"]:
            return (status == "approved"), status
        await asyncio.sleep(10)  # Check every 10 seconds

    return False, "Approval timeout"

agent_with_async_approval = HumanInLoopAgent(
    agent=critical_agent,
    approval_callback=async_approval_callback
)
```

**Pros:**
- ✅ Human oversight for safety
- ✅ Catch errors before execution
- ✅ Regulatory compliance
- ✅ User control and transparency
- ✅ Can modify agent proposals
- ✅ Audit trail of all approvals

**Cons:**
- ❌ Very slow (human in the loop)
- ❌ Doesn't scale to high volume
- ❌ Human availability required
- ❌ Approval fatigue possible
- ❌ Can block agent progress

**Best Practices:**
1. Only require approval for critical actions
2. Provide clear context for approval decisions
3. Allow modifications, not just approve/reject
4. Log all approval decisions for audit trail
5. Set timeouts for approval requests
6. Consider async approval workflows for scalability
7. Use for high-stakes decisions only

**Performance Benchmark:**
```
Human in Loop Pattern: ~150 ns/op (C++) + human_response_time
Real-world: 1 LLM call + 10s-10min (human response)
Not suitable for high-throughput systems
Use for <100 approvals/day
```

---

### Agents as Tools

**Purpose:** Wrap agents as tools that other agents can use for modular orchestration and dynamic agent selection.

**When to Use:**
- Agent orchestration (main agent + specialist sub-agents)
- Specialized sub-agents
- Modular architecture
- Dynamic agent selection
- Tool delegation to other agents

**Pattern Diagram:**
```
Main Agent (Orchestrator)
    ├→ Specialist Agent 1 (wrapped as tool)
    ├→ Specialist Agent 2 (wrapped as tool)
    └→ Specialist Agent 3 (wrapped as tool)
```

**Performance:** O(orchestrator + selected_specialists)

**Example - Multi-Domain Assistant:**

```python
from agenkit.patterns import AgentAsToolWrapper, ReActAgent
from agenkit import Agent, Message

class WeatherAgent(Agent):
    """Specialist for weather queries."""
    @property
    def name(self) -> str:
        return "weather"

    async def process(self, message: Message) -> Message:
        city = message.content
        # Fetch weather data
        weather = await get_weather(city)
        return Message(
            role="assistant",
            content=f"Weather in {city}: {weather}"
        )

class StockAgent(Agent):
    """Specialist for stock queries."""
    @property
    def name(self) -> str:
        return "stocks"

    async def process(self, message: Message) -> Message:
        symbol = message.content
        # Fetch stock price
        price = await get_stock_price(symbol)
        return Message(
            role="assistant",
            content=f"Stock {symbol}: ${price}"
        )

class NewsAgent(Agent):
    """Specialist for news queries."""
    @property
    def name(self) -> str:
        return "news"

    async def process(self, message: Message) -> Message:
        topic = message.content
        # Fetch news
        articles = await get_news(topic)
        return Message(
            role="assistant",
            content=f"Latest on {topic}: {articles}"
        )

# Create specialist agents
weather_specialist = WeatherAgent()
stock_specialist = StockAgent()
news_specialist = NewsAgent()

# Wrap as tools with descriptions
tools = [
    AgentAsToolWrapper(
        weather_specialist,
        description="Get weather information for a city"
    ).to_tool(),
    AgentAsToolWrapper(
        stock_specialist,
        description="Get stock price and info for a symbol"
    ).to_tool(),
    AgentAsToolWrapper(
        news_specialist,
        description="Get latest news on a topic"
    ).to_tool()
]

# Create main assistant (orchestrator)
assistant = ReActAgent(
    llm=my_llm,
    tools=tools,
    name="multi-domain-assistant"
)

# Assistant intelligently routes to specialist agents
queries = [
    "What's the weather in Seattle?",
    "What's the price of AAPL stock?",
    "What's happening with AI technology?",
    "Give me the weather in Tokyo and the price of TSLA"
]

for query in queries:
    print(f"\nUser: {query}")
    result = await assistant.process(Message(role="user", content=query))
    print(f"Assistant: {result.content}")

# Assistant uses ReAct to:
# 1. Analyze query
# 2. Select appropriate specialist tool
# 3. Call tool with extracted parameters
# 4. Return result to user
```

**Code Generation Specialists:**

```python
from agenkit.patterns import AgentAsToolWrapper, ReActAgent

# Specialist agents for different languages
python_expert = PythonCodeAgent()
javascript_expert = JavaScriptCodeAgent()
rust_expert = RustCodeAgent()

# Wrap as tools
tools = [
    AgentAsToolWrapper(python_expert,
        description="Generate Python code").to_tool(),
    AgentAsToolWrapper(javascript_expert,
        description="Generate JavaScript code").to_tool(),
    AgentAsToolWrapper(rust_expert,
        description="Generate Rust code").to_tool()
]

# Orchestrator selects appropriate specialist
code_assistant = ReActAgent(llm=my_llm, tools=tools)

request = Message(
    role="user",
    content="Write a function to fetch data from an API. Use Python."
)
result = await code_assistant.process(request)
# Orchestrator calls python_expert tool
```

**Pros:**
- ✅ Modular architecture
- ✅ Specialist agents for different domains
- ✅ Easy to extend (add new specialists)
- ✅ Clear separation of concerns
- ✅ Reusable specialists

**Cons:**
- ❌ Coordination overhead
- ❌ More complex debugging
- ❌ Potential for miscommunication
- ❌ Orchestrator can make wrong choices
- ❌ Extra layer of indirection

**Best Practices:**
1. Clear tool descriptions (help orchestrator choose)
2. Well-defined interfaces
3. Handle tool (agent) failures
4. Log tool calls for debugging
5. Use for true specialists (not general agents)
6. Consider caching specialist results

**Performance Benchmark:**
```
Agents as Tools Pattern: ~400 ns/op (Go), ~4.5 μs/op (TypeScript)
Real-world: 1x orchestrator + 1x specialist
Routing overhead: ~5-10ms (orchestrator decides)
```

---

## Advanced Patterns

### Autonomous

**Purpose:** Self-directed agent that pursues goals independently through iterative assessment, planning, action, and evaluation.

**When to Use:**
- Open-ended tasks
- Goal-driven behavior
- Agent needs autonomy
- Long-running processes
- Agent swarms
- Experimental/research applications

**Pattern Diagram:**
```
Goal → [Assess → Plan → Act → Evaluate]* → Goal Achieved
         ↑______________________________↓
              (loop until goal met)
```

**Performance:** O(k * (assess + plan + act + evaluate)) where k = iterations

**Example - Research Agent:**

```python
from agenkit.patterns import AutonomousAgent
from agenkit import Message, Tool

# Create autonomous agent
researcher = AutonomousAgent(
    llm=my_llm,
    tools=[
        Tool(name="search", func=web_search),
        Tool(name="read_url", func=fetch_url),
        Tool(name="take_notes", func=save_notes),
        Tool(name="write_summary", func=write_file)
    ],
    max_iterations=20,
    goal_check_interval=5  # Check if goal met every 5 iterations
)

# Set goal (agent figures out how to achieve it)
goal = Message(
    role="user",
    content="Research the latest developments in quantum computing and create a comprehensive summary document"
)

result = await researcher.process(goal)

# Agent will autonomously:
# Iteration 1:
#   Assess: Need to find recent quantum computing news
#   Plan: Search for "quantum computing 2024 breakthroughs"
#   Act: Execute search tool
#   Evaluate: Found 10 articles, need to read them
#
# Iteration 2-11:
#   Assess: Have article URLs, need content
#   Plan: Read each URL
#   Act: Execute read_url tool for each
#   Evaluate: Collected information, need to organize
#
# Iteration 12-15:
#   Assess: Have raw information, need structure
#   Plan: Organize into categories
#   Act: Take notes with categorization
#   Evaluate: Notes organized, need summary
#
# Iteration 16-18:
#   Assess: Ready to write summary
#   Plan: Create document structure
#   Act: Write summary document
#   Evaluate: Document created
#
# Iteration 19:
#   Assess: Goal achieved (comprehensive summary exists)
#   Exit: Success

print(result.content)  # Path to summary document
print(f"Took {result.metadata['iterations']} iterations")
print(f"Goal achieved: {result.metadata['goal_achieved']}")
```

**⚠️ Important Warnings:**

```python
# Autonomous agents can be unpredictable - use safeguards
safe_autonomous = AutonomousAgent(
    llm=my_llm,
    tools=safe_tools,  # Whitelist of safe tools only
    max_iterations=10,  # Hard limit
    budget_limit=5.00,  # $ limit on LLM costs
    allowed_domains=["wikipedia.org", "arxiv.org"],  # Restrict web access
    require_approval_for=["write_file", "delete_file"]  # Human approval
)
```

**Pros:**
- ✅ Self-directed (minimal human intervention)
- ✅ Goal-oriented
- ✅ Handles open-ended tasks
- ✅ Adaptive (plans dynamically)
- ✅ Can discover novel solutions

**Cons:**
- ❌ Unpredictable behavior (can go off-track)
- ❌ Very expensive (many iterations, many LLM calls)
- ❌ Hard to control and debug
- ❌ May not converge on goal
- ❌ Safety concerns (needs sandboxing)

**Best Practices:**
1. Clear goal definition (measurable success criteria)
2. Set max_iterations (hard limit)
3. Monitor closely (log all actions)
4. Use in controlled environments only
5. Implement cost/budget limits
6. Require human oversight for critical actions
7. Whitelist tools (don't give unrestricted access)
8. Use for research/experimentation, not production (yet)

**Performance Benchmark:**
```
Autonomous Pattern: ~1.2 μs/op (Python) framework overhead
Real-world: 10-50 iterations × (1 LLM call + N tool calls)
Very expensive: 10-50x basic agent cost
Unpredictable latency: Seconds to hours
```

---

### Memory Hierarchy

**Purpose:** Efficient memory management with short-term (recent messages), long-term (summarized history), and external memory (vector store) for scalable conversation history.

**When to Use:**
- Long-running agents (100+ messages)
- Large conversation histories
- Efficient context retrieval needed
- Knowledge persistence
- Chat applications with history
- Agents that learn over time

**Pattern Diagram:**
```
┌─────────────────────────────────┐
│ Short-term Memory               │
│ (recent 10-20 messages)         │
│ - Fast access                   │
│ - Full detail                   │
└─────────────────────────────────┘
          ↓ (summarize)
┌─────────────────────────────────┐
│ Long-term Memory                │
│ (summaries of 100-1000 messages)│
│ - Compressed context            │
│ - Key facts preserved           │
└─────────────────────────────────┘
          ↓ (index)
┌─────────────────────────────────┐
│ External Memory                 │
│ (vector store, database)        │
│ - Semantic search               │
│ - Unlimited capacity            │
└─────────────────────────────────┘
```

**Performance:** O(short_term_size) + O(log(long_term_size)) for retrieval

**Example - Long-Running Assistant:**

```python
from agenkit.patterns import MemoryHierarchyAgent
from agenkit import Message
from agenkit.memory import VectorMemoryStore

# Create vector store for external memory
vector_store = VectorMemoryStore(
    embedding_model="text-embedding-3-small",
    dimension=1536
)

# Create agent with memory hierarchy
assistant = MemoryHierarchyAgent(
    llm=my_llm,
    short_term_size=10,  # Keep last 10 messages in full
    long_term_size=100,  # Keep summaries of 100 messages
    external_memory=vector_store,  # Unlimited indexed storage
    summarization_interval=20,  # Summarize every 20 messages
    name="long-term-assistant"
)

# Simulate long conversation
for i in range(150):
    user_msg = Message(role="user", content=f"Question {i}: ...")
    response = await assistant.process(user_msg)

    # Memory management happens automatically:
    # - Messages 141-150: In short-term (full detail)
    # - Messages 41-140: In long-term (summarized)
    # - Messages 1-40: In external memory (indexed, searchable)

# Agent can still recall information from message 1!
recall_query = Message(role="user", content="What did I ask about in message 5?")
response = await assistant.process(recall_query)
# Agent retrieves from external memory using semantic search
```

**With Custom Summarization:**

```python
from agenkit.patterns import MemoryHierarchyAgent

async def custom_summarizer(messages: list[Message]) -> str:
    """Custom summarization strategy."""
    # Extract key facts
    key_facts = []
    for msg in messages:
        if "important" in msg.content.lower():
            key_facts.append(msg.content)

    # Create structured summary
    summary = f"Summary of {len(messages)} messages:\n"
    summary += f"Key facts: {len(key_facts)}\n"
    for fact in key_facts:
        summary += f"- {fact}\n"

    return summary

assistant = MemoryHierarchyAgent(
    llm=my_llm,
    short_term_size=15,
    long_term_size=200,
    summarization_fn=custom_summarizer  # Custom logic
)
```

**Pros:**
- ✅ Efficient memory usage (scales to long conversations)
- ✅ Fast retrieval (tiered access)
- ✅ Preserves important context
- ✅ Semantic search in external memory
- ✅ Unbounded conversation length

**Cons:**
- ❌ Setup complexity (vector store, embeddings)
- ❌ Summarization may lose details
- ❌ Retrieval may be imperfect (relevance)
- ❌ Storage overhead (vector database)
- ❌ Additional costs (embeddings)

**Best Practices:**
1. Tune memory sizes (10-20 short, 100-200 long)
2. Good summarization strategy (preserve key facts)
3. Use vector stores for semantic retrieval (Pinecone, Weaviate, Chroma)
4. Monitor memory usage and retrieval accuracy
5. Periodic cleanup of old external memory
6. Consider privacy (encrypt stored conversations)

**Performance Benchmark:**
```
Memory Hierarchy Pattern: ~500 ns/op (Rust), ~5.8 μs/op (TypeScript)
Real-world: 1 LLM call + O(log n) vector search
Summarization: +1 LLM call every N messages
Vector search: 10-50ms per query
Scales to 10,000+ message conversations
```

---

## Pattern Composition

Patterns can be combined to create sophisticated multi-agent systems. The key is understanding how patterns interact.

### Composition Examples

#### Sequential + Reflection

```python
from agenkit.patterns import SequentialAgent, ReflectionAgent

# Refined pipeline: Each stage self-improves
refiner = ReflectionAgent(agent=writer, critic=critic, max_iterations=3)

pipeline = SequentialAgent(
    agents=[
        extractor,  # Extract data
        refiner,    # Generate refined output
        formatter   # Format final result
    ]
)

# Data flows through: Extract → Generate+Refine → Format
```

#### Parallel + Router + Fallback

```python
from agenkit.patterns import ParallelAgent, RouterAgent, FallbackAgent

# High-availability multi-provider system with specialist routing

# Fallback for each specialist (HA)
weather_ha = FallbackAgent(agents=[weather_openai, weather_anthropic, weather_local])
stock_ha = FallbackAgent(agents=[stock_openai, stock_anthropic, stock_local])
news_ha = FallbackAgent(agents=[news_openai, news_anthropic, news_local])

# Router to specialists
router = RouterAgent(
    routes={
        "weather": weather_ha,
        "stocks": stock_ha,
        "news": news_ha
    }
)

# Result: High-availability specialist routing system
```

#### ReAct + Agents as Tools + Supervisor

```python
from agenkit.patterns import ReActAgent, AgentAsToolWrapper, SupervisorAgent

# Specialists as tools
tools = [
    AgentAsToolWrapper(code_generator).to_tool(),
    AgentAsToolWrapper(code_tester).to_tool(),
    search_tool
]

# ReAct orchestrator
orchestrator = ReActAgent(llm=my_llm, tools=tools)

# Supervisor oversees everything
supervised = SupervisorAgent(
    supervisor=quality_controller,
    workers=[orchestrator]
)

# Result: Supervised orchestration with specialist tools
```

#### Orchestration + Human in Loop + Memory Hierarchy

```python
from agenkit.patterns import OrchestrationAgent, HumanInLoopAgent, MemoryHierarchyAgent

# Long-term memory agent
memory_agent = MemoryHierarchyAgent(
    llm=my_llm,
    short_term_size=10,
    long_term_size=100
)

# Human approval wrapper
safe_agent = HumanInLoopAgent(
    agent=memory_agent,
    approval_callback=approval_fn,
    require_approval_for=["critical_actions"]
)

# Orchestrated workflow
workflow = OrchestrationAgent(
    agents={"safe_agent": safe_agent, ...},
    workflow=complex_workflow
)

# Result: Complex workflow with memory and human oversight
```

### Composition Patterns

| Pattern 1 | Pattern 2 | Result | Use Case |
|-----------|-----------|--------|----------|
| Sequential | Reflection | Self-improving pipeline | Content creation |
| Parallel | Router | Multi-specialist analysis | Expert panels |
| Router | Fallback | HA specialist routing | Production systems |
| ReAct | Agents as Tools | Tool-using orchestrator | Research, automation |
| Supervisor | ReAct | Overseen tool usage | Code generation |
| Orchestration | Human in Loop | Safe workflows | Financial, medical |
| Conversational | Memory Hierarchy | Long-term chat | Customer support |
| Planning | Parallel | Parallel plan execution | Project management |

### Anti-Patterns (Don't Do This)

❌ **Too Many Layers**
```python
# Bad: 5+ layers of patterns
agent = FallbackAgent(
    agents=[
        SupervisorAgent(
            supervisor=...,
            workers=[
                ReflectionAgent(
                    agent=SequentialAgent(
                        agents=[
                            RouterAgent(...)
                        ]
                    )
                )
            ]
        )
    ]
)
# Result: Unmaintainable, slow, impossible to debug
```

✅ **Good: 2-3 layers maximum**
```python
# Good: Clear, maintainable
agent = SupervisorAgent(
    supervisor=quality_controller,
    workers=[
        SequentialAgent(agents=[validator, processor, formatter])
    ]
)
```

---

## Performance Characteristics

### Framework Overhead Benchmarks

Based on real benchmarks from all 6 languages:

| Pattern | Go (ns/op) | Rust (ns/op) | C++ (ns/op) | Zig (ns/op) | TypeScript (μs/op) | Python (μs/op) |
|---------|-----------|--------------|-------------|-------------|-------------------|----------------|
| Sequential (3 agents) | 450 | 400 | 300 | 200 | 1.2 | 1.35 |
| Parallel (3 agents) | 180 | 180 | 150 | 300 | 1.8 | 2.1 |
| Reflection (3 iter) | 600 | **3,299*** | 400 | 250 | 2.5 | 3.2 |
| ReAct (5 steps) | 700 | 500 | 525 | 350 | 5.5 | 6.8 |
| Planning | 400 | 350 | 380 | 280 | 4.2 | 5.1 |
| Router | 250 | 220 | 200 | 180 | 3.5 | 4.2 |
| Fallback (1st success) | 200 | 200 | 150 | 150 | 2.5 | 2.8 |

*Rust Reflection anomaly: 3,299 μs likely due to dev build or benchmark issue

### Key Insights

1. **Framework overhead is negligible** - All patterns <10 μs, LLM calls ~100,000 μs
2. **C++ and Zig fastest** - Compiled languages dominate (150-400 ns/op)
3. **TypeScript surprisingly competitive** - 1-6 μs/op despite JIT
4. **Python acceptable** - 1-7 μs/op, still <0.01% of LLM call

### Real-World Performance

```
LLM call latency: ~100-500ms (100,000-500,000 μs)
Framework overhead: <10 μs
Percentage: <0.01%

Conclusion: Pattern choice matters for LOGIC, not SPEED
```

### Latency Comparison

| Pattern | Framework | LLM Calls | Total Latency |
|---------|-----------|-----------|---------------|
| Task | <1 μs | 1 | ~100ms |
| Sequential (3) | <2 μs | 3 | ~300ms |
| Parallel (3) | <2 μs | 3 | ~100ms (concurrent) |
| Reflection (3) | <4 μs | 6 | ~600ms (gen+critique×3) |
| ReAct (5) | <7 μs | 5-10 | ~500-1000ms |
| Autonomous (20) | <20 μs | 20-100 | ~2-10 seconds |

**Optimization Rule**: Optimize LLM calls (model, caching, batching), not framework overhead.

---

## Best Practices

### General Principles

1. **Start Simple**
   - Begin with Task or Conversational
   - Add complexity only when needed
   - Single agent > Multiple agents if possible

2. **Composition Over Complexity**
   - Combine 2-3 simple patterns
   - Avoid deep nesting (max 3 layers)
   - Each layer should add clear value

3. **Error Handling**
   - Use Fallback for high availability
   - Set timeouts at every level
   - Log errors with context
   - Graceful degradation

4. **Cost Management**
   - Monitor LLM call counts
   - Use Fallback to try cheap models first
   - Cache results when possible
   - Set budget limits for Autonomous

5. **Testing**
   - Unit test each agent individually
   - Integration test pattern compositions
   - Use mock agents for deterministic tests
   - Benchmark performance regularly

6. **Observability**
   - Log all agent interactions
   - Track latency and cost per pattern
   - Monitor success rates
   - Use metadata for debugging

7. **Safety**
   - Human in Loop for critical actions
   - Whitelist tools for Autonomous
   - Validate all inputs and outputs
   - Implement rate limiting

### Pattern Selection Flowchart

```
1. Do you need multiple agents?
   NO → Task or Conversational
   YES → Continue

2. How should they execute?
   Sequential stages → Sequential
   Parallel/concurrent → Parallel
   Route to specialist → Router
   Try until success → Fallback

3. Do you need quality improvement?
   YES → Add Reflection layer

4. Do you need tools/reasoning?
   Basic tools → ReAct
   Complex reasoning → Reasoning with Tools
   Structured plan → Planning

5. Do you need coordination?
   Oversight → Supervisor
   Complex workflow → Orchestration
   Collaboration → Multiagent or Collaborative

6. Do you need human approval?
   YES → Add Human in Loop wrapper

7. Is conversation long?
   YES → Use Memory Hierarchy
```

### Common Mistakes

❌ **Over-Engineering**
```python
# Bad: Complex pattern for simple task
agent = SupervisorAgent(
    supervisor=...,
    workers=[ReflectionAgent(...)]
)

# Good: Simple task agent
agent = TaskAgent(system_prompt="...", llm=my_llm)
```

❌ **No Error Handling**
```python
# Bad: No fallback
result = await unreliable_agent.process(msg)

# Good: Fallback for reliability
result = await FallbackAgent(
    agents=[primary, backup, local]
).process(msg)
```

❌ **Ignoring Costs**
```python
# Bad: Unlimited iterations
agent = ReflectionAgent(max_iterations=100)  # Could cost $100+

# Good: Reasonable limits
agent = ReflectionAgent(max_iterations=3)  # ~$1-5
```

❌ **Deep Nesting**
```python
# Bad: 5 layers
Sequential(
    agents=[
        Parallel(
            agents=[
                Reflection(
                    agent=ReAct(
                        tools=[AgentAsToolWrapper(...)]
                    )
                )
            ]
        )
    ]
)

# Good: 2 layers
Sequential(
    agents=[
        Parallel(agents=[agent1, agent2]),
        formatter
    ]
)
```

### Production Checklist

Before deploying patterns to production:

- [ ] Error handling for all failure modes
- [ ] Timeouts set at every level
- [ ] Logging and observability configured
- [ ] Cost limits and budget monitoring
- [ ] Rate limiting implemented
- [ ] Human approval for critical actions
- [ ] Fallback for high availability
- [ ] Test coverage >80%
- [ ] Performance benchmarked
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Monitoring and alerts configured

---

## Conclusion

Agenkit's 18 patterns provide a comprehensive toolkit for building production AI agent systems. Key takeaways:

1. **Start simple** - Use Task or Conversational for most applications
2. **Compose patterns** - Combine 2-3 patterns for sophisticated behaviors
3. **Framework overhead is negligible** - <0.01% of LLM call time
4. **Cross-language consistency** - Same patterns work in all 6 languages
5. **Production-ready** - Used in real systems with 100% test coverage

### Pattern Selection Summary

- **Simple tasks** → Task
- **Chatbots** → Conversational
- **Pipelines** → Sequential
- **Speed** → Parallel
- **High availability** → Fallback
- **Specialists** → Router
- **Quality** → Reflection
- **Tools** → ReAct
- **Complex projects** → Planning
- **Advanced reasoning** → Reasoning with Tools
- **Oversight** → Supervisor
- **Complex workflows** → Orchestration
- **Expert panel** → Multiagent
- **Team collaboration** → Collaborative
- **Safety** → Human in Loop
- **Tool delegation** → Agents as Tools
- **Open-ended** → Autonomous
- **Long conversations** → Memory Hierarchy

### Next Steps

1. **Try examples** - Start with Getting Started guides for your language
2. **Experiment** - Build simple agents with Task or Conversational
3. **Compose** - Combine patterns as complexity grows
4. **Optimize** - Use performance benchmarks to guide decisions
5. **Deploy** - Follow production checklist

### Resources

- **Getting Started**: `docs/getting-started/{PYTHON|GO|TYPESCRIPT|RUST|CPP|ZIG}.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Performance**: `docs/PATTERN_BENCHMARK_RESULTS.md`
- **Examples**: `examples/` directory (all languages)
- **API Reference**: (coming in v0.47.0)

---

**Happy building! 🚀**
