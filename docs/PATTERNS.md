# Agenkit Agent Patterns Guide

A comprehensive guide to the 18 agent patterns in Agenkit Python.

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
- [Reliability Patterns](#reliability-patterns)
  - [Fallback](#fallback)
  - [Supervisor](#supervisor)
  - [Human in Loop](#human-in-loop)
  - [Router](#router)
  - [Orchestration](#orchestration)
  - [Reasoning with Tools](#reasoning-with-tools)
  - [Collaborative](#collaborative)
- [Pattern Selection Guide](#pattern-selection-guide)
- [Composing Patterns](#composing-patterns)
- [Performance Considerations](#performance-considerations)

---

## Overview

Agent patterns are reusable architectural templates that solve common problems in AI agent design. Agenkit provides 18 production-ready patterns that you can use immediately or combine for complex workflows.

### Why Patterns Matter

1. **Proven Solutions** - Patterns encode best practices from production systems
2. **Composability** - Patterns work together seamlessly
3. **Flexibility** - Easy to customize and extend
4. **Maintainability** - Clear separation of concerns
5. **Testability** - Well-defined interfaces for testing

### Pattern Categories

- **Composition** (Sequential, Parallel) - Combine multiple agents
- **Enhancement** (Reflection, ReAct, Planning) - Improve agent quality
- **Specialized** (Task, Conversational, Agents as Tools) - Domain-specific patterns
- **Advanced** (Autonomous, Multiagent, Memory Hierarchy) - Complex behaviors
- **Reliability** (Fallback, Supervisor, Human in Loop, Router, Orchestration, Reasoning with Tools, Collaborative) - Error recovery, oversight, and complex coordination

### Core Concepts

All patterns share common building blocks:
- **Message** - Unit of communication with role, content, metadata
- **Agent** - Interface with `process()` method
- **Tools** - Functions agents can call
- **Memory** - Conversation history and state

---

## Pattern Comparison

| Pattern | Complexity | Use Case | Latency | Best For |
|---------|-----------|----------|---------|----------|
| Sequential | Low | Data pipelines | Fast | Multi-stage processing |
| Parallel | Medium | Independent tasks | Very Fast | Concurrent operations |
| Reflection | Medium | Quality improvement | Slow (iterative) | Self-correction |
| ReAct | Medium | Reasoning + Tools | Medium | Decision-making |
| Planning | High | Complex tasks | Slow (planning) | Multi-step workflows |
| Task | Low | Job execution | Fast | Single-purpose agents |
| Conversational | Medium | Dialogue | Fast | Chatbots, assistants |
| Agents as Tools | High | Orchestration | Medium | Tool delegation |
| Autonomous | Very High | Goal pursuit | Slow (iterative) | Self-directed agents |
| Multiagent | Very High | Collaboration | Medium | Multi-agent systems |
| Memory Hierarchy | High | Context management | Medium | Long-running agents |
| **Fallback** | **Low** | **Error recovery** | **Fast (on success)** | **High availability** |
| **Supervisor** | **Medium** | **Quality control** | **Medium** | **Oversight workflows** |
| **Human in Loop** | **Medium** | **Safety-critical** | **Slow (human wait)** | **Compliance, safety** |
| **Router** | **Low** | **Message routing** | **Fast** | **Specialist selection** |
| **Orchestration** | **Very High** | **Complex workflows** | **Variable** | **Business automation** |
| **Reasoning with Tools** | **High** | **Enhanced reasoning** | **Slow (multiple paths)** | **Explainable AI** |
| **Collaborative** | **High** | **Team coordination** | **Medium** | **Shared problem-solving** |

### Pros and Cons

| Pattern | Pros | Cons |
|---------|------|------|
| Sequential | Simple, predictable, fast | No parallelism, linear only |
| Parallel | High throughput, concurrent | More complex, harder to debug |
| Reflection | Self-improving, high quality | Slow, multiple LLM calls |
| ReAct | Flexible, tool-aware | Can loop indefinitely |
| Planning | Structured, handles complexity | Upfront planning cost |
| Task | Focused, efficient | Limited scope |
| Conversational | Natural interaction | Stateful, memory management |
| Agents as Tools | Modular, reusable | Coordination overhead |
| Autonomous | Goal-oriented, adaptive | Unpredictable, expensive |
| Multiagent | Distributed, scalable | Complex coordination |
| Memory Hierarchy | Efficient retrieval | Setup complexity |
| **Fallback** | **High availability, automatic failover** | **Higher latency on failures** |
| **Supervisor** | **Quality assurance, error correction** | **Extra overhead, potential bottleneck** |
| **Human in Loop** | **Safety, compliance, user control** | **Slow, doesn't scale** |
| **Router** | **Intelligent selection, specialist optimization** | **Routing overhead, potential misrouting** |
| **Orchestration** | **Handles complex workflows, flexible** | **High complexity, difficult to debug** |
| **Reasoning with Tools** | **Explicit reasoning, better accuracy** | **Slow, expensive, many LLM calls** |
| **Collaborative** | **Multiple perspectives, team synergy** | **Coordination complexity, slower** |

---

## Composition Patterns

### Sequential

**Purpose:** Process messages through multiple agents in order.

**When to Use:**
- Data transformation pipelines
- Multi-stage validation
- Step-by-step processing
- When output of agent N feeds into agent N+1

**Pattern:**
```
Input → Agent1 → Agent2 → Agent3 → Output
```

**Implementation:**

```python
from agenkit.patterns import SequentialAgent
from agenkit import Message

# Create sequential agent
sequential = SequentialAgent(
    agents=[
        validator_agent,   # Step 1: Validate input
        processor_agent,   # Step 2: Process data
        formatter_agent    # Step 3: Format output
    ],
    name="data-pipeline"
)

# Process message through pipeline
input_msg = Message.with_text("user", "Process this data")
result = await sequential.process(input_msg)
print(result.text)  # Formatted output after all stages
```

**Detailed Example - Document Processing:**

```python
from agenkit.patterns import SequentialAgent
from agenkit import Agent, Message

class ExtractorAgent(Agent):
    """Extract key information from documents."""

    async def process(self, message: Message) -> Message:
        doc = message.text
        # Extract entities, dates, etc.
        extracted = f"Extracted: entities={doc.count(' ')}, chars={len(doc)}"
        return Message.with_text("assistant", extracted)

class SummarizerAgent(Agent):
    """Summarize extracted information."""

    async def process(self, message: Message) -> Message:
        data = message.text
        # Summarize the extracted data
        summary = f"Summary: {data[:50]}..."
        return Message.with_text("assistant", summary)

class ValidatorAgent(Agent):
    """Validate the final output."""

    async def process(self, message: Message) -> Message:
        summary = message.text
        # Validate completeness
        if len(summary) > 10:
            return Message.with_text("assistant", f"✓ Valid: {summary}")
        return Message.with_text("assistant", "✗ Invalid summary")

# Build pipeline
doc_pipeline = SequentialAgent(
    agents=[
        ExtractorAgent(name="extractor"),
        SummarizerAgent(name="summarizer"),
        ValidatorAgent(name="validator")
    ],
    name="document-pipeline"
)

# Process document
doc = Message.with_text("user", "Annual Report 2024: Revenue increased 15%...")
result = await doc_pipeline.process(doc)
print(result.text)  # ✓ Valid: Summary: Extracted: entities=5...
```

**Pros:**
- ✅ Simple and predictable
- ✅ Easy to debug (one agent at a time)
- ✅ Fast (no overhead)
- ✅ Clear data flow

**Cons:**
- ❌ No parallelism (sequential only)
- ❌ Single point of failure (one agent fails, all fail)
- ❌ Linear scaling only

**Best Practices:**
1. Keep each agent focused on one task
2. Use descriptive names for agents
3. Add logging between stages
4. Handle errors gracefully
5. Consider timeout for each stage

---

### Parallel

**Purpose:** Execute multiple agents concurrently and aggregate results.

**When to Use:**
- Independent tasks that can run simultaneously
- Gathering multiple perspectives
- A/B testing different approaches
- Reducing latency with concurrent execution

**Pattern:**
```
       ┌→ Agent1 →┐
Input ─┼→ Agent2 →┼→ Aggregator → Output
       └→ Agent3 →┘
```

**Implementation:**

```python
from agenkit.patterns import ParallelAgent
from agenkit import Message

# Create parallel agent
parallel = ParallelAgent(
    agents=[
        sentiment_agent,  # Analyze sentiment
        entity_agent,     # Extract entities
        topic_agent       # Identify topics
    ],
    name="multi-analyzer",
    aggregation="concat"  # or "vote", "first", "custom"
)

# Process with all agents concurrently
input_msg = Message.with_text("user", "Apple announced new iPhone today")
result = await parallel.process(input_msg)

# Result contains aggregated output from all agents
print(result.text)
# "Sentiment: Positive\nEntities: Apple, iPhone\nTopics: Technology, Products"
```

**Detailed Example - Multi-Perspective Analysis:**

```python
from agenkit.patterns import ParallelAgent
from agenkit import Agent, Message
import asyncio

class TechnicalAnalyst(Agent):
    """Analyze from technical perspective."""

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(0.5)  # Simulate LLM call
        return Message.with_text(
            "assistant",
            "Technical: System architecture is scalable and maintainable."
        )

class BusinessAnalyst(Agent):
    """Analyze from business perspective."""

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(0.5)  # Simulate LLM call
        return Message.with_text(
            "assistant",
            "Business: ROI is positive, market opportunity is large."
        )

class RiskAnalyst(Agent):
    """Analyze from risk perspective."""

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(0.5)  # Simulate LLM call
        return Message.with_text(
            "assistant",
            "Risk: Low technical risk, medium market risk."
        )

# Create parallel analysis
multi_analyst = ParallelAgent(
    agents=[
        TechnicalAnalyst(name="technical"),
        BusinessAnalyst(name="business"),
        RiskAnalyst(name="risk")
    ],
    name="multi-perspective",
    aggregation="concat"
)

# Analyze proposal
proposal = Message.with_text("user", "Should we build a new mobile app?")

import time
start = time.time()
result = await multi_analyst.process(proposal)
elapsed = time.time() - start

print(f"Analysis completed in {elapsed:.2f}s")
print(result.text)
# All three analyses in ~0.5s (parallel) vs ~1.5s (sequential)
```

**Custom Aggregation:**

```python
from agenkit.patterns import ParallelAgent

def voting_aggregator(results: list[Message]) -> Message:
    """Aggregate by majority vote."""
    votes = {}
    for msg in results:
        answer = msg.text.lower()
        votes[answer] = votes.get(answer, 0) + 1

    winner = max(votes, key=votes.get)
    return Message.with_text(
        "assistant",
        f"Decision: {winner} ({votes[winner]}/{len(results)} votes)"
    )

parallel = ParallelAgent(
    agents=[judge1, judge2, judge3],
    aggregation=voting_aggregator
)
```

**Pros:**
- ✅ High throughput (concurrent execution)
- ✅ Reduced latency (N agents in parallel)
- ✅ Multiple perspectives
- ✅ Fault tolerance (some agents can fail)

**Cons:**
- ❌ Higher complexity
- ❌ More resource intensive
- ❌ Harder to debug
- ❌ Aggregation overhead

**Best Practices:**
1. Ensure agents are truly independent
2. Set appropriate timeouts
3. Handle partial failures gracefully
4. Choose aggregation strategy carefully
5. Monitor resource usage

---

## Enhancement Patterns

### Reflection

**Purpose:** Agent reviews and improves its own output iteratively.

**When to Use:**
- Quality matters more than speed
- Self-correction is valuable
- Iterative refinement needed
- Learning from mistakes

**Pattern:**
```
Input → Generate → Reflect → Improve → Output
          ↑____________↓
         (iterate until satisfied)
```

**Implementation:**

```python
from agenkit.patterns import ReflectionAgent
from agenkit import Message

# Create reflection agent
reflector = ReflectionAgent(
    agent=writer_agent,
    critic=critic_agent,  # Reviews and suggests improvements
    max_iterations=3,
    improvement_threshold=0.8  # Stop if score > 0.8
)

# Generate with self-improvement
prompt = Message.with_text("user", "Write a product description")
result = await reflector.process(prompt)

# Result went through multiple refinement cycles
print(result.text)  # High-quality, refined output
print(result.metadata["iterations"])  # Number of refinement cycles
```

**Detailed Example - Essay Writing:**

```python
from agenkit.patterns import ReflectionAgent
from agenkit import Agent, Message

class EssayWriter(Agent):
    """Write essays."""

    async def process(self, message: Message) -> Message:
        topic = message.text
        # Generate essay (simulated)
        essay = f"Essay on {topic}: This is a draft essay that could be improved..."
        return Message.with_text("assistant", essay)

class EssayCritic(Agent):
    """Critique and score essays."""

    async def process(self, message: Message) -> Message:
        essay = message.text

        # Analyze essay
        has_intro = "Essay on" in essay
        has_conclusion = "conclusion" in essay.lower()
        word_count = len(essay.split())

        # Calculate score
        score = 0.0
        if has_intro:
            score += 0.3
        if has_conclusion:
            score += 0.3
        if word_count > 50:
            score += 0.4

        feedback = []
        if not has_intro:
            feedback.append("Add a clear introduction")
        if not has_conclusion:
            feedback.append("Add a strong conclusion")
        if word_count < 50:
            feedback.append("Expand with more details")

        critique = {
            "score": score,
            "feedback": feedback
        }

        response = Message.with_text("assistant", str(critique))
        response.metadata["reflection_score"] = score
        return response

# Create reflection writer
essay_agent = ReflectionAgent(
    agent=EssayWriter(name="writer"),
    critic=EssayCritic(name="critic"),
    max_iterations=5,
    improvement_threshold=0.9
)

# Write essay with self-improvement
topic = Message.with_text("user", "The importance of AI in education")
result = await essay_agent.process(topic)

print(f"Final essay (after {result.metadata['iterations']} iterations):")
print(result.text)
print(f"Final score: {result.metadata.get('reflection_score', 'N/A')}")
```

**Pros:**
- ✅ High-quality output
- ✅ Self-correcting
- ✅ Learns from mistakes
- ✅ Measurable improvement

**Cons:**
- ❌ Slow (multiple LLM calls)
- ❌ Expensive (tokens)
- ❌ Can get stuck in loops
- ❌ No guarantee of convergence

**Best Practices:**
1. Set reasonable max_iterations (3-5)
2. Define clear improvement criteria
3. Use early stopping (threshold)
4. Log each iteration for debugging
5. Consider cost vs quality tradeoff

---

### ReAct

**Purpose:** Reasoning and Acting - agent thinks through problems step-by-step and uses tools.

**When to Use:**
- Tools/APIs need to be called
- Complex reasoning required
- Multi-step problem solving
- Dynamic decision making

**Pattern:**
```
Thought → Action → Observation → Thought → ... → Answer
```

**Implementation:**

```python
from agenkit.patterns import ReActAgent
from agenkit import Tool, Message

# Define tools
def search_web(query: str) -> str:
    """Search the web for information."""
    return f"Search results for: {query}"

def calculate(expression: str) -> float:
    """Evaluate mathematical expressions."""
    return eval(expression)

# Create ReAct agent
react = ReActAgent(
    llm=my_llm,
    tools=[
        Tool(name="search", func=search_web, description="Search the web"),
        Tool(name="calculate", func=calculate, description="Do math")
    ],
    max_iterations=5,
    verbose=True  # Show reasoning steps
)

# Solve problem with reasoning
question = Message.with_text("user", "What is 15% of the GDP of France?")
result = await react.process(question)

# Agent will:
# 1. Think: "I need to find France's GDP"
# 2. Act: search("France GDP 2024")
# 3. Observe: "GDP is $2.8 trillion"
# 4. Think: "Now calculate 15% of $2.8 trillion"
# 5. Act: calculate("2.8 * 0.15")
# 6. Observe: "0.42"
# 7. Answer: "15% of France's GDP is $420 billion"

print(result.text)
```

**Detailed Example - Research Assistant:**

```python
from agenkit.patterns import ReActAgent
from agenkit import Tool, Message
import json

# Define research tools
def search_papers(query: str) -> str:
    """Search academic papers."""
    # Simulated paper search
    papers = {
        "transformers": ["Attention Is All You Need (2017)"],
        "rl": ["Deep Reinforcement Learning (2015)"]
    }
    results = []
    for key, papers_list in papers.items():
        if key in query.lower():
            results.extend(papers_list)
    return json.dumps(results) if results else "No papers found"

def read_paper(title: str) -> str:
    """Get abstract of a paper."""
    abstracts = {
        "Attention Is All You Need (2017)":
            "Introduces the Transformer architecture using self-attention mechanisms."
    }
    return abstracts.get(title, "Paper not found")

def summarize(text: str) -> str:
    """Summarize text."""
    return f"Summary: {text[:100]}..."

# Create research assistant
researcher = ReActAgent(
    llm=my_llm,
    tools=[
        Tool(name="search_papers", func=search_papers,
             description="Search for academic papers"),
        Tool(name="read_paper", func=read_paper,
             description="Read paper abstract"),
        Tool(name="summarize", func=summarize,
             description="Summarize text")
    ],
    max_iterations=10,
    verbose=True
)

# Research question
question = Message.with_text(
    "user",
    "What are the key innovations in the Transformer architecture?"
)

result = await researcher.process(question)
print(result.text)

# Reasoning trace (verbose=True):
# Thought: I need to find papers about Transformers
# Action: search_papers("transformers architecture")
# Observation: ["Attention Is All You Need (2017)"]
# Thought: Let me read this seminal paper
# Action: read_paper("Attention Is All You Need (2017)")
# Observation: "Introduces the Transformer architecture using self-attention..."
# Thought: I can summarize the key innovation
# Action: summarize("Introduces the Transformer architecture using self-attention mechanisms.")
# Observation: "Summary: Introduces the Transformer architecture..."
# Thought: I have enough information to answer
# Answer: The key innovation in the Transformer architecture is...
```

**Pros:**
- ✅ Flexible and adaptable
- ✅ Tool-aware reasoning
- ✅ Transparent decision making
- ✅ Handles complex tasks

**Cons:**
- ❌ Can loop indefinitely
- ❌ Token-intensive (reasoning + actions)
- ❌ Requires good prompt engineering
- ❌ Tool calls can fail

**Best Practices:**
1. Define clear tool descriptions
2. Set max_iterations to prevent loops
3. Use verbose mode for debugging
4. Validate tool outputs
5. Handle tool errors gracefully

---

### Planning

**Purpose:** Agent creates a plan before execution, then follows the plan step-by-step.

**When to Use:**
- Complex multi-step workflows
- Deterministic execution needed
- Decompose large tasks
- Track progress explicitly

**Pattern:**
```
Input → Plan → Step 1 → Step 2 → Step 3 → Output
        ↓
    [Task, Task, Task]
```

**Implementation:**

```python
from agenkit.patterns import PlanningAgent
from agenkit import Message, Tool

# Create planning agent
planner = PlanningAgent(
    llm=my_llm,
    tools=[file_tool, search_tool, calculate_tool],
    max_steps=10
)

# Task with implicit planning
task = Message.with_text(
    "user",
    "Research competitors, analyze pricing, create comparison report"
)

result = await planner.process(task)

# Agent will:
# 1. Create plan: [Search competitors, Get pricing, Compare, Write report]
# 2. Execute each step sequentially
# 3. Track progress
# 4. Return final result

print(result.text)  # Complete comparison report
print(result.metadata["plan"])  # The generated plan
print(result.metadata["steps_completed"])  # Progress tracking
```

**Detailed Example - Travel Itinerary:**

```python
from agenkit.patterns import PlanningAgent
from agenkit import Tool, Message

# Define travel tools
def search_flights(origin: str, destination: str) -> str:
    """Search for flights."""
    return f"Flights from {origin} to {destination}: $500-800"

def search_hotels(city: str, nights: int) -> str:
    """Search for hotels."""
    return f"Hotels in {city} for {nights} nights: $100-200/night"

def search_activities(city: str) -> str:
    """Find activities in city."""
    activities = {
        "Paris": ["Eiffel Tower", "Louvre Museum", "Notre-Dame"],
        "Tokyo": ["Tokyo Tower", "Senso-ji Temple", "Shibuya Crossing"]
    }
    return ", ".join(activities.get(city, ["General sightseeing"]))

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
trip_request = Message.with_text(
    "user",
    "Plan a 5-day trip to Paris from New York in June"
)

result = await travel_planner.process(trip_request)

print("=== Travel Plan ===")
print(result.text)
print("\n=== Execution Steps ===")
for step in result.metadata.get("execution_steps", []):
    print(f"{step['number']}. {step['action']} → {step['result'][:50]}...")

# Output:
# === Travel Plan ===
# Day 1: Flight from New York to Paris ($650)
# Day 1-5: Hotel in Paris ($150/night, total $750)
# Day 2: Visit Eiffel Tower
# Day 3: Explore Louvre Museum
# Day 4: See Notre-Dame
# Day 5: Return flight
#
# === Execution Steps ===
# 1. search_flights → Flights from New York to Paris: $500-800...
# 2. search_hotels → Hotels in Paris for 5 nights: $100-200/night...
# 3. search_activities → Eiffel Tower, Louvre Museum, Notre-Dame...
```

**Pros:**
- ✅ Structured approach
- ✅ Progress tracking
- ✅ Handles complexity
- ✅ Clear execution path

**Cons:**
- ❌ Upfront planning cost
- ❌ Less flexible (locked into plan)
- ❌ Plan may be suboptimal
- ❌ Doesn't adapt to changes

**Best Practices:**
1. Provide clear initial instructions
2. Set appropriate max_steps
3. Log plan and execution
4. Handle step failures gracefully
5. Consider re-planning if needed

---

## Specialized Patterns

### Task

**Purpose:** Single-purpose agent optimized for specific tasks.

**When to Use:**
- Focused, well-defined task
- No need for conversation history
- Stateless operation
- Maximum performance

**Pattern:**
```
Task Input → Process → Task Output
```

**Implementation:**

```python
from agenkit.patterns import TaskAgent
from agenkit import Message

# Create task agent
summarizer = TaskAgent(
    system_prompt="You are an expert summarizer. Create concise summaries.",
    llm=my_llm,
    name="summarizer"
)

# Execute task
doc = Message.with_text("user", "Long document text...")
summary = await summarizer.process(doc)

print(summary.text)  # Concise summary
```

**Detailed Example - Data Validator:**

```python
from agenkit.patterns import TaskAgent
from agenkit import Message
import json

# Create validation task agent
validator = TaskAgent(
    system_prompt="""You are a data validator. Check if JSON data is valid.
    Return: {"valid": true/false, "errors": [...]}""",
    llm=my_llm,
    name="json-validator"
)

# Validate data
data = Message.with_text("user", json.dumps({
    "name": "John",
    "email": "invalid-email",  # Invalid
    "age": -5  # Invalid
}))

result = await validator.process(data)
validation = json.loads(result.text)

if not validation["valid"]:
    print("Validation errors:")
    for error in validation["errors"]:
        print(f"  - {error}")
```

**Pros:**
- ✅ Fast and efficient
- ✅ Predictable behavior
- ✅ Easy to test
- ✅ Low overhead

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
5. Use for focused tasks

---

### Conversational

**Purpose:** Multi-turn dialogue with memory of conversation history.

**When to Use:**
- Chatbots and assistants
- Multi-turn interactions
- Context from previous messages matters
- Natural conversation flow

**Pattern:**
```
User → Agent → User → Agent → ...
        ↓                ↓
    [Memory: Message History]
```

**Implementation:**

```python
from agenkit.patterns import ConversationalAgent
from agenkit import Message

# Create conversational agent
assistant = ConversationalAgent(
    system_prompt="You are a helpful assistant.",
    llm=my_llm,
    max_history=10,  # Keep last 10 messages
    name="assistant"
)

# Multi-turn conversation
msg1 = Message.with_text("user", "My name is Alice")
resp1 = await assistant.process(msg1)
print(resp1.text)  # "Nice to meet you, Alice!"

msg2 = Message.with_text("user", "What's my name?")
resp2 = await assistant.process(msg2)
print(resp2.text)  # "Your name is Alice" (remembers context)

# Clear history when needed
assistant.clear_history()
```

**Detailed Example - Customer Support Bot:**

```python
from agenkit.patterns import ConversationalAgent
from agenkit import Message

# Create support bot
support_bot = ConversationalAgent(
    system_prompt="""You are a friendly customer support agent.
    Help customers with orders, returns, and general questions.
    Be empathetic and solution-oriented.""",
    llm=my_llm,
    max_history=20,
    name="support-bot"
)

# Simulate customer conversation
async def chat(user_input: str):
    msg = Message.with_text("user", user_input)
    response = await support_bot.process(msg)
    print(f"User: {user_input}")
    print(f"Bot: {response.text}\n")

# Multi-turn support conversation
await chat("Hi, I have a problem with my order")
# Bot: Hello! I'm sorry to hear that. What's your order number?

await chat("Order #12345")
# Bot: Thank you. Let me look up order #12345. What seems to be the issue?

await chat("It hasn't arrived yet")
# Bot: I understand your concern about order #12345 not arriving...

await chat("When will it arrive?")
# Bot: Based on the tracking for order #12345, it should arrive by Friday...

# Check conversation history
print(f"Messages in history: {len(support_bot.history)}")
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
resp = await agent_a.process(Message.with_text("user", "Hi!"))

# User B conversation (independent)
agent_b = manager.get_or_create("user-b")
resp = await agent_b.process(Message.with_text("user", "Hello!"))

# Clear user A session
manager.clear_session("user-a")
```

**Pros:**
- ✅ Natural conversation
- ✅ Context awareness
- ✅ Multi-turn support
- ✅ Stateful interaction

**Cons:**
- ❌ Memory management complexity
- ❌ Token usage grows with history
- ❌ Need session management
- ❌ History can confuse agent

**Best Practices:**
1. Set appropriate max_history
2. Clear history periodically
3. Use session IDs for multi-user
4. Summarize old conversations
5. Monitor token usage

---

### Agents as Tools

**Purpose:** Wrap agents as tools that other agents can use.

**When to Use:**
- Agent orchestration
- Specialized sub-agents
- Modular architecture
- Dynamic agent selection

**Pattern:**
```
Main Agent
    ├→ Specialist Agent 1 (as tool)
    ├→ Specialist Agent 2 (as tool)
    └→ Specialist Agent 3 (as tool)
```

**Implementation:**

```python
from agenkit.patterns import AgentAsToolWrapper, ReActAgent
from agenkit import Agent, Message, Tool

# Create specialist agents
summarizer = SummarizerAgent(name="summarizer")
translator = TranslatorAgent(name="translator")
analyzer = AnalyzerAgent(name="analyzer")

# Wrap agents as tools
tools = [
    AgentAsToolWrapper(summarizer).to_tool(),
    AgentAsToolWrapper(translator).to_tool(),
    AgentAsToolWrapper(analyzer).to_tool()
]

# Create orchestrator
orchestrator = ReActAgent(
    llm=my_llm,
    tools=tools,
    name="orchestrator"
)

# Orchestrator decides which specialist to use
request = Message.with_text(
    "user",
    "Analyze this French document and summarize it in English"
)

result = await orchestrator.process(request)

# Orchestrator will:
# 1. Detect it's French → call translator tool
# 2. Get English text → call analyzer tool
# 3. Get analysis → call summarizer tool
# 4. Return final summary

print(result.text)
```

**Detailed Example - Multi-Domain Assistant:**

```python
from agenkit.patterns import AgentAsToolWrapper, ReActAgent
from agenkit import Agent, Message

class WeatherAgent(Agent):
    """Specialist for weather queries."""

    async def process(self, message: Message) -> Message:
        city = message.text
        # Fetch weather data (simulated)
        weather = f"Weather in {city}: Sunny, 72°F"
        return Message.with_text("assistant", weather)

class StockAgent(Agent):
    """Specialist for stock queries."""

    async def process(self, message: Message) -> Message:
        symbol = message.text
        # Fetch stock price (simulated)
        price = f"Stock {symbol}: $150.25 (+2.5%)"
        return Message.with_text("assistant", price)

class NewsAgent(Agent):
    """Specialist for news queries."""

    async def process(self, message: Message) -> Message:
        topic = message.text
        # Fetch news (simulated)
        news = f"Latest on {topic}: Breaking developments today..."
        return Message.with_text("assistant", news)

# Create specialist agents
weather_specialist = WeatherAgent(name="weather")
stock_specialist = StockAgent(name="stocks")
news_specialist = NewsAgent(name="news")

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

# Create main assistant
assistant = ReActAgent(
    llm=my_llm,
    tools=tools,
    name="multi-domain-assistant"
)

# User queries
queries = [
    "What's the weather in Seattle?",
    "What's the price of AAPL?",
    "What's happening with AI?",
    "Give me the weather in Tokyo and the price of TSLA"
]

for query in queries:
    print(f"\nUser: {query}")
    result = await assistant.process(Message.with_text("user", query))
    print(f"Assistant: {result.text}")

# Assistant intelligently routes to specialist agents
```

**Pros:**
- ✅ Modular architecture
- ✅ Specialist agents
- ✅ Easy to extend
- ✅ Clear separation of concerns

**Cons:**
- ❌ Coordination overhead
- ❌ More complex debugging
- ❌ Potential for miscommunication
- ❌ Orchestrator can make wrong choices

**Best Practices:**
1. Clear tool descriptions
2. Well-defined interfaces
3. Handle tool failures
4. Log tool calls
5. Use for true specialists

---

## Advanced Patterns

### Autonomous

**Purpose:** Self-directed agent that pursues goals independently.

**When to Use:**
- Open-ended tasks
- Goal-driven behavior
- Agent needs autonomy
- Long-running processes

**Pattern:**
```
Goal → [Assess → Plan → Act → Evaluate]* → Goal Achieved
         ↑______________________________↓
              (loop until goal met)
```

**Implementation:**

```python
from agenkit.patterns import AutonomousAgent
from agenkit import Message, Tool

# Create autonomous agent
autonomous = AutonomousAgent(
    llm=my_llm,
    tools=[search_tool, file_tool, code_tool],
    max_iterations=20,
    goal_check_interval=5
)

# Set goal (agent figures out how to achieve it)
goal = Message.with_text(
    "user",
    "Research market trends, analyze data, and create investment strategy"
)

result = await autonomous.process(goal)

# Agent will autonomously:
# 1. Break down goal
# 2. Search for market data
# 3. Analyze findings
# 4. Create strategy
# 5. Self-evaluate
# 6. Iterate until satisfied

print(result.text)
print(f"Took {result.metadata['iterations']} iterations")
```

**Pros:**
- ✅ Self-directed
- ✅ Goal-oriented
- ✅ Handles open-ended tasks
- ✅ Adaptive

**Cons:**
- ❌ Unpredictable behavior
- ❌ Expensive (many iterations)
- ❌ Hard to control
- ❌ May not converge

**Best Practices:**
1. Clear goal definition
2. Set max_iterations
3. Monitor closely
4. Use in controlled environments
5. Have human oversight

---

### Multiagent

**Purpose:** Multiple agents collaborate to solve problems together.

**When to Use:**
- Complex problems requiring specialization
- Distributed problem solving
- Debate and consensus needed
- Parallel expertise

**Pattern:**
```
Problem → Agent1 ⟺ Agent2 ⟺ Agent3 → Solution
            ↓         ↓         ↓
        [Collaboration/Debate/Voting]
```

**Implementation:**

```python
from agenkit.patterns import MultiagentSystem
from agenkit import Message

# Create multiagent system
system = MultiagentSystem(
    agents=[expert1, expert2, expert3],
    coordination="debate",  # or "vote", "consensus"
    rounds=3
)

# Problem requiring multiple perspectives
problem = Message.with_text("user", "Should we invest in this startup?")
decision = await system.process(problem)

print(decision.text)
```

**Pros:**
- ✅ Multiple perspectives
- ✅ Distributed expertise
- ✅ Robust decisions
- ✅ Scalable

**Cons:**
- ❌ Coordination complexity
- ❌ Communication overhead
- ❌ Expensive
- ❌ May not reach consensus

**Best Practices:**
1. Clear roles for each agent
2. Define coordination protocol
3. Set termination criteria
4. Monitor agent interactions
5. Handle disagreements

---

### Memory Hierarchy

**Purpose:** Efficient memory management with short-term and long-term storage.

**When to Use:**
- Long-running agents
- Large conversation histories
- Efficient context retrieval
- Knowledge persistence

**Pattern:**
```
Short-term Memory (recent messages)
Long-term Memory (summarized/indexed history)
External Memory (vector store, database)
```

**Implementation:**

```python
from agenkit.patterns import MemoryHierarchyAgent
from agenkit import Message

# Create agent with memory hierarchy
agent = MemoryHierarchyAgent(
    llm=my_llm,
    short_term_size=10,
    long_term_size=100,
    summarization_interval=20
)

# Agent automatically manages memory
for i in range(100):
    msg = Message.with_text("user", f"Message {i}")
    response = await agent.process(msg)

# Recent messages in short-term, old ones summarized in long-term
```

**Pros:**
- ✅ Efficient memory usage
- ✅ Scales to long conversations
- ✅ Fast retrieval
- ✅ Preserves important context

**Cons:**
- ❌ Setup complexity
- ❌ Summarization may lose details
- ❌ Retrieval may be imperfect
- ❌ Storage overhead

**Best Practices:**
1. Tune memory sizes
2. Good summarization strategy
3. Use vector stores for retrieval
4. Monitor memory usage
5. Periodic cleanup

---

## Pattern Selection Guide

### Decision Tree

```
Start
 │
 ├─ Need multiple agents?
 │   ├─ Yes, sequential → Sequential
 │   ├─ Yes, parallel → Parallel
 │   └─ Yes, collaborate → Multiagent
 │
 ├─ Need tools/reasoning?
 │   ├─ Yes, step-by-step → ReAct
 │   ├─ Yes, planned → Planning
 │   └─ No → continue
 │
 ├─ Need quality improvement?
 │   ├─ Yes → Reflection
 │   └─ No → continue
 │
 ├─ Need conversation?
 │   ├─ Yes → Conversational
 │   └─ No → Task
 │
 ├─ Need autonomy?
 │   └─ Yes → Autonomous
 │
 └─ Need memory management?
     └─ Yes → Memory Hierarchy
```

### By Use Case

| Use Case | Recommended Pattern |
|----------|-------------------|
| Data pipeline | Sequential |
| Analysis from multiple angles | Parallel |
| Self-improving content | Reflection |
| Research with tools | ReAct |
| Complex project | Planning |
| Single-purpose task | Task |
| Chatbot | Conversational |
| Agent orchestration | Agents as Tools |
| Open-ended goals | Autonomous |
| Expert collaboration | Multiagent |
| Long conversations | Memory Hierarchy |

---

## Composing Patterns

Patterns can be combined for sophisticated behaviors:

### Example: Sequential + Reflection

```python
from agenkit.patterns import SequentialAgent, ReflectionAgent

# Create refined pipeline
refiner = ReflectionAgent(agent=writer, critic=critic)
pipeline = SequentialAgent(agents=[extractor, refiner, formatter])

# Extract → Refine → Format
result = await pipeline.process(doc)
```

### Example: Parallel + Conversational

```python
from agenkit.patterns import ParallelAgent, ConversationalAgent

# Multiple conversational assistants in parallel
assistants = [
    ConversationalAgent(llm=llm1, name="assistant-1"),
    ConversationalAgent(llm=llm2, name="assistant-2"),
    ConversationalAgent(llm=llm3, name="assistant-3")
]

multi_assistant = ParallelAgent(agents=assistants, aggregation="vote")

# Get consensus from multiple assistants
result = await multi_assistant.process(query)
```

### Example: ReAct + Agents as Tools

```python
from agenkit.patterns import ReActAgent, AgentAsToolWrapper

# Specialists as tools for ReAct orchestrator
tools = [
    AgentAsToolWrapper(summarizer).to_tool(),
    AgentAsToolWrapper(translator).to_tool(),
    search_tool,  # Regular tool
    calculator_tool  # Regular tool
]

orchestrator = ReActAgent(llm=llm, tools=tools)

# Orchestrator uses both specialist agents and regular tools
```

---

## Performance Considerations

### Latency

| Pattern | Latency | Optimization |
|---------|---------|-------------|
| Sequential | N * agent_time | Reduce agents, optimize each |
| Parallel | max(agent_times) | Balance agent complexity |
| Reflection | K * agent_time | Reduce iterations |
| ReAct | M * (think + tool) | Reduce max_iterations |
| Planning | plan + N * step | Cache plans |
| Others | 1 * agent_time | Standard optimizations |

### Cost

| Pattern | Cost Factor | Optimization |
|---------|-------------|-------------|
| Reflection | 3-5x | Lower iterations |
| ReAct | 2-4x | Reduce thinking steps |
| Planning | 2-3x | Simpler plans |
| Autonomous | 5-10x | Strict limits |
| Multiagent | N * agent_cost | Fewer agents |
| Others | 1x | N/A |

### When to Cache

- **Sequential**: Cache individual agent outputs
- **Parallel**: Cache per-agent results
- **Reflection**: Cache intermediate drafts
- **ReAct**: Cache tool results
- **Planning**: Cache generated plans
- **Conversational**: Cache conversation summaries

---

## Reliability Patterns

### Fallback

**Purpose:** Sequential retry across multiple agents with automatic failover.

**When to Use:**
- High availability systems
- Multi-provider LLM setups (try different providers)
- Graceful degradation (advanced → simple models)
- Error recovery with fallback strategies
- Retry with alternative approaches

**Pattern:**
```
Primary Agent (try first)
     ↓ (if fails)
Fallback 1
     ↓ (if fails)
Fallback 2
     ↓ (if fails)
...
```

**Implementation:**

```python
from agenkit.patterns import FallbackAgent
from agenkit import Message

# Create fallback chain
fallback = FallbackAgent(
    agents=[
        primary_agent,      # Try this first
        backup_agent,       # Fallback if primary fails
        simple_agent        # Last resort
    ]
)

# Automatically tries agents until one succeeds
result = await fallback.process(message)

# Metadata shows which agent succeeded
print(result.metadata["fallback_success_agent"])  # "backup_agent"
print(result.metadata["fallback_attempts"])  # 2
```

**Detailed Example - Multi-Provider LLM:**

```python
from agenkit.patterns import FallbackAgent
from agenkit.adapters import OpenAIAgent, AnthropicAgent, OllamaAgent
from agenkit import Message

# Create agents for different providers
openai_agent = OpenAIAgent(model="gpt-4")
anthropic_agent = AnthropicAgent(model="claude-3-5-sonnet-20241022")
ollama_agent = OllamaAgent(model="llama3.3")  # Local fallback

# Fallback chain: expensive → mid-tier → free local
multi_provider = FallbackAgent(
    agents=[openai_agent, anthropic_agent, ollama_agent]
)

# Try all providers until one succeeds
question = Message.with_text("user", "Explain quantum computing")
result = await multi_provider.process(question)

# Check which provider succeeded
if result.metadata["fallback_attempts"] == 1:
    print("✓ OpenAI succeeded immediately")
elif result.metadata["fallback_attempts"] == 2:
    print("⚠ OpenAI failed, Anthropic succeeded")
else:
    print("⚠⚠ Cloud providers failed, using local Ollama")
```

**With Custom Recovery:**

```python
from agenkit.patterns import WithRecovery

# Add recovery logic to any agent
agent_with_recovery = WithRecovery(
    agent=primary_agent,
    recovery=lambda ctx, msg, err: Message.with_text(
        "assistant",
        "Service temporarily unavailable. Please try again."
    )
)

# Always returns a response, even if agent fails
result = await agent_with_recovery.process(message)
```

**Pros:**
- ✅ High availability and fault tolerance
- ✅ Automatic failover (no manual intervention)
- ✅ Early termination on first success (fast path)
- ✅ Error collection for debugging
- ✅ Simple to reason about (sequential)

**Cons:**
- ❌ Higher latency on failures (tries each agent sequentially)
- ❌ Increased cost if all agents fail
- ❌ No parallelism (could be added with timeout-based fallback)
- ❌ Requires multiple agents/providers

**Best Practices:**
1. Order agents by preference (fastest/cheapest first)
2. Include error details in metadata for monitoring
3. Set appropriate timeouts per agent
4. Use recovery functions for graceful degradation
5. Monitor fallback rates to detect systemic issues

---

### Supervisor

**Purpose:** Oversee and coordinate execution of worker agents with monitoring, approval, and error handling.

**When to Use:**
- Quality control needed
- Workers need oversight
- Task delegation and coordination
- Error detection and correction
- Approval workflows

**Pattern:**
```
Supervisor (coordinator)
     ├→ Worker 1 → Report back
     ├→ Worker 2 → Report back
     └→ Worker 3 → Report back
Supervisor reviews, approves, or requests revisions
```

**Implementation:**

```python
from agenkit.patterns import SupervisorAgent
from agenkit import Message

# Create supervisor with workers
supervisor = SupervisorAgent(
    supervisor=coordinator_agent,
    workers=[worker1, worker2, worker3],
    require_approval=True  # Supervisor approves all outputs
)

# Supervisor delegates, monitors, and coordinates
task = Message.with_text("user", "Complete project analysis")
result = await supervisor.process(task)

# Metadata shows delegation details
print(result.metadata["supervisor_delegations"])  # Which workers were used
print(result.metadata["supervisor_revisions"])  # How many revisions requested
```

**Detailed Example - Quality Control:**

```python
from agenkit.patterns import SupervisorAgent
from agenkit import Agent, Message

class QualityController(Agent):
    """Supervisor that reviews worker output for quality."""

    async def process(self, message: Message) -> Message:
        # Analyze worker output
        content = message.text

        issues = []
        if len(content) < 100:
            issues.append("Response too short")
        if not any(word in content.lower() for word in ["because", "therefore", "due to"]):
            issues.append("Lacks reasoning")

        if issues:
            # Request revision
            feedback = "Revise with improvements:\n" + "\n".join(f"- {i}" for i in issues)
            response = Message.with_text("supervisor", feedback)
            response.metadata["approval"] = False
            response.metadata["revision_requested"] = True
            return response

        # Approve
        response = Message.with_text("supervisor", "Approved")
        response.metadata["approval"] = True
        return response

# Create supervised workflow
supervisor = SupervisorAgent(
    supervisor=QualityController(name="qa"),
    workers=[analyst_agent, writer_agent],
    require_approval=True
)

# Workers produce output, supervisor reviews and requests revisions if needed
result = await supervisor.process(task)
```

**Pros:**
- ✅ Quality assurance built in
- ✅ Centralized coordination
- ✅ Error detection and correction
- ✅ Can request revisions
- ✅ Clear hierarchy

**Cons:**
- ❌ Extra overhead (supervisor reviews)
- ❌ Potential bottleneck
- ❌ More complex coordination
- ❌ Supervisor must be reliable

**Best Practices:**
1. Supervisor should have higher capability than workers
2. Define clear approval criteria
3. Limit revision cycles to prevent loops
4. Log all delegation and approval decisions
5. Use for critical/high-stakes tasks

---

### Human in Loop

**Purpose:** Include human approval or feedback at critical decision points during agent execution.

**When to Use:**
- Safety-critical applications
- High-stakes decisions
- Regulatory compliance
- User preferences matter
- Verification needed before actions

**Pattern:**
```
Agent proposes action
     ↓
Request human approval
     ↓
Human reviews and decides
     ↓ (approved)          ↓ (rejected)
Execute action       Revise and retry
```

**Implementation:**

```python
from agenkit.patterns import HumanInLoopAgent
from agenkit import Message

def approval_callback(action: str, context: dict) -> bool:
    """Human reviews and approves/rejects proposed action."""
    print(f"Agent proposes: {action}")
    print(f"Context: {context}")
    response = input("Approve? (y/n): ")
    return response.lower() == 'y'

# Create agent with human approval gates
agent = HumanInLoopAgent(
    agent=autonomous_agent,
    approval_callback=approval_callback,
    require_approval_for=["tool_calls", "final_answer"]
)

# Agent will pause for human approval before critical actions
result = await agent.process(task)
```

**Detailed Example - Financial Transactions:**

```python
from agenkit.patterns import HumanInLoopAgent
from agenkit import Agent, Message, Tool

class FinancialAgent(Agent):
    """Agent that can execute financial transactions."""

    def __init__(self):
        self.tools = [
            Tool(name="transfer_money", func=self.transfer,
                 description="Transfer money between accounts"),
            Tool(name="pay_bill", func=self.pay_bill,
                 description="Pay a bill")
        ]

    async def transfer(self, from_account: str, to_account: str, amount: float):
        return f"Transferred ${amount} from {from_account} to {to_account}"

    async def pay_bill(self, biller: str, amount: float):
        return f"Paid ${amount} to {biller}"

def financial_approval(action: str, context: dict) -> tuple[bool, str]:
    """
    Human reviews financial actions.
    Returns: (approved: bool, feedback: str)
    """
    print(f"\n{'='*60}")
    print(f"APPROVAL REQUIRED: {action}")
    print(f"Details: {context}")
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
task = Message.with_text("user", "Pay my electricity bill of $150")
result = await safe_financial_agent.process(task)
```

**Pros:**
- ✅ Human oversight for safety
- ✅ Catch errors before execution
- ✅ Regulatory compliance
- ✅ User control and transparency
- ✅ Can modify agent proposals

**Cons:**
- ❌ Slow (human in the loop)
- ❌ Doesn't scale to high volume
- ❌ Human availability required
- ❌ Approval fatigue possible

**Best Practices:**
1. Only require approval for critical actions
2. Provide clear context for approval decisions
3. Allow modifications, not just approve/reject
4. Log all approval decisions for audit trail
5. Set timeouts for approval requests
6. Consider async approval workflows

---

### Router

**Purpose:** Route messages to appropriate specialist agents based on content, metadata, or classification.

**When to Use:**
- Multiple specialists available
- Need intelligent routing
- Domain-specific agents
- Load balancing across agents
- Conditional execution paths

**Pattern:**
```
Router (classifier)
     ├→ [weather query] → Weather Agent
     ├→ [stock query] → Stock Agent
     ├→ [news query] → News Agent
     └→ [other] → General Agent (default)
```

**Implementation:**

```python
from agenkit.patterns import RouterAgent
from agenkit import Message

# Create router with specialists
router = RouterAgent(
    routes={
        "weather": weather_agent,
        "stocks": stock_agent,
        "news": news_agent
    },
    default_agent=general_agent,
    routing_strategy="keyword"  # or "llm", "metadata", "custom"
)

# Router automatically selects appropriate specialist
question = Message.with_text("user", "What's the weather in Seattle?")
result = await router.process(question)  # Routed to weather_agent
```

**Detailed Example - Customer Support Router:**

```python
from agenkit.patterns import RouterAgent
from agenkit import Agent, Message

# Define specialist agents
class BillingAgent(Agent):
    async def process(self, message: Message) -> Message:
        return Message.with_text("assistant", "Billing: Let me help with your account...")

class TechnicalAgent(Agent):
    async def process(self, message: Message) -> Message:
        return Message.with_text("assistant", "Technical: Let me troubleshoot...")

class SalesAgent(Agent):
    async def process(self, message: Message) -> Message:
        return Message.with_text("assistant", "Sales: I can help you find the right product...")

# LLM-based routing for complex classification
def llm_routing_strategy(message: Message, routes: dict) -> str:
    """Use LLM to classify message and select route."""
    # In practice, this would call an LLM
    content = message.text.lower()

    if any(word in content for word in ["bill", "payment", "charge", "invoice"]):
        return "billing"
    elif any(word in content for word in ["broken", "error", "not working", "problem"]):
        return "technical"
    elif any(word in content for word in ["buy", "purchase", "price", "upgrade"]):
        return "sales"
    else:
        return None  # Use default

# Create customer support router
support_router = RouterAgent(
    routes={
        "billing": BillingAgent(name="billing"),
        "technical": TechnicalAgent(name="technical"),
        "sales": SalesAgent(name="sales")
    },
    default_agent=GeneralAgent(name="general"),
    routing_strategy=llm_routing_strategy
)

# Route customer inquiries
inquiries = [
    "My credit card was charged twice",
    "The app keeps crashing",
    "I want to upgrade to pro plan",
    "What are your business hours?"
]

for inquiry in inquiries:
    msg = Message.with_text("user", inquiry)
    result = await support_router.process(msg)
    routed_to = result.metadata.get("routed_to", "unknown")
    print(f"'{inquiry}' → {routed_to}")
```

**Metadata-based Routing:**

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
msg = Message.with_text("user", "Important question")
msg.metadata["priority"] = "urgent"
result = await router.process(msg)  # Routed to priority_agent
```

**Pros:**
- ✅ Intelligent agent selection
- ✅ Specialist optimization
- ✅ Load balancing possible
- ✅ Flexible routing strategies
- ✅ Easy to add new specialists

**Cons:**
- ❌ Routing overhead (classification)
- ❌ Potential misrouting
- ❌ Requires good routing logic
- ❌ Single point of routing failure

**Best Practices:**
1. Use clear, non-overlapping route criteria
2. Always provide a default agent
3. Log routing decisions for debugging
4. Monitor routing accuracy
5. Use LLM-based routing for complex cases
6. Combine with fallback for reliability

---

### Orchestration

**Purpose:** Coordinate multiple agents with complex workflows, conditional routing, and sophisticated aggregation.

**When to Use:**
- Complex multi-agent workflows
- Conditional execution paths
- Sequential + parallel combinations
- State machines
- Business process automation

**Pattern:**
```
Orchestrator (workflow engine)
     ├→ Stage 1: [Agent A || Agent B] → Aggregate
     ├→ Decision: Route based on Stage 1 output
     ├→ Stage 2a: Agent C → Agent D (if condition X)
     ├→ Stage 2b: Agent E (if condition Y)
     └→ Final: Combine all results
```

**Implementation:**

```python
from agenkit.patterns import OrchestrationAgent
from agenkit import Message, WorkflowDefinition

# Define complex workflow
workflow = WorkflowDefinition(
    stages=[
        {
            "name": "analysis",
            "agents": [sentiment_agent, entity_agent],
            "execution": "parallel",
            "aggregation": "merge"
        },
        {
            "name": "processing",
            "agents": [processor_agent],
            "condition": "analysis.sentiment == 'positive'",
            "execution": "sequential"
        },
        {
            "name": "output",
            "agents": [formatter_agent],
            "inputs": ["analysis", "processing"]
        }
    ]
)

# Create orchestrator
orchestrator = OrchestrationAgent(
    agents={
        "sentiment": sentiment_agent,
        "entity": entity_agent,
        "processor": processor_agent,
        "formatter": formatter_agent
    },
    workflow=workflow
)

# Execute complex workflow
result = await orchestrator.process(message)
```

**Detailed Example - Content Moderation Pipeline:**

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
            "execution": "sequential"
        },
        # Stage 4: Final decision
        {
            "name": "decision",
            "agents": ["decision_maker"],
            "inputs": ["screening", "deep_analysis", "human_review"],
            "aggregation": "consensus"
        }
    ]
})

# Create orchestration system
content_moderator = OrchestrationAgent(
    agents={
        "spam_detector": SpamDetectorAgent(),
        "toxicity_detector": ToxicityDetectorAgent(),
        "pii_detector": PIIDetectorAgent(),
        "context_analyzer": ContextAnalyzer(),
        "human_review_queue": HumanReviewQueue(),
        "decision_maker": DecisionMaker()
    },
    workflow=moderation_workflow
)

# Process content through workflow
content = Message.with_text("user", "User-generated content here...")
decision = await content_moderator.process(content)

# Result includes full workflow execution details
print(decision.metadata["workflow_stages_executed"])
print(decision.metadata["workflow_decisions"])
```

**Pros:**
- ✅ Handles complex workflows
- ✅ Flexible execution (sequential, parallel, conditional)
- ✅ State machine support
- ✅ Reusable workflow definitions
- ✅ Sophisticated coordination

**Cons:**
- ❌ High complexity
- ❌ Difficult to debug
- ❌ Workflow definition overhead
- ❌ Potential performance bottlenecks

**Best Practices:**
1. Define workflows declaratively (YAML/JSON)
2. Keep stages focused and independent
3. Use meaningful stage names
4. Log all workflow decisions
5. Test workflows thoroughly
6. Monitor workflow execution metrics

---

### Reasoning with Tools

**Purpose:** Enhanced reasoning pattern combining structured thinking (Chain of Thought, Tree of Thought) with tool usage.

**When to Use:**
- Complex reasoning required
- Multiple reasoning paths
- Tool usage with justification
- Explainable AI needed
- Self-consistency checking

**Pattern:**
```
Problem → Reasoning Strategy (CoT/ToT/Self-Consistency)
              ↓
         Thought branches + tool identification
              ↓
         Execute tools with reasoning context
              ↓
         Synthesize results with reasoning
              ↓
         Final answer with explanation
```

**Implementation:**

```python
from agenkit.patterns import ReasoningWithTools
from agenkit import Message, Tool

# Create enhanced reasoning agent
reasoning_agent = ReasoningWithTools(
    llm=my_llm,
    tools=[search_tool, calculator_tool, code_tool],
    reasoning_strategy="chain-of-thought",  # or "tree-of-thought", "self-consistency"
    max_iterations=10
)

# Agent provides explicit reasoning with tool usage
problem = Message.with_text(
    "user",
    "A train travels from A to B at 60mph. It's 180 miles. " +
    "But there's a 30-minute stop halfway. What time does it arrive if it leaves at 2pm?"
)

result = await reasoning_agent.process(problem)

# Result includes reasoning trace
print("Reasoning steps:")
for step in result.metadata["reasoning_trace"]:
    print(f"  {step['thought']}")
    if step.get("tool_call"):
        print(f"    → Tool: {step['tool_call']}")
        print(f"    → Result: {step['tool_result']}")
```

**Detailed Example - Tree of Thought with Tools:**

```python
from agenkit.patterns import ReasoningWithTools
from agenkit import Tool

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

# Complex problem with multiple solution paths
problem = Message.with_text(
    "user",
    "What's the most cost-effective way to travel from Paris to Tokyo, " +
    "considering time, comfort, and budget?"
)

result = await tot_agent.process(problem)

# Result shows explored reasoning branches
print("Explored reasoning paths:")
for i, branch in enumerate(result.metadata["reasoning_branches"]):
    print(f"\nPath {i+1}: {branch['approach']}")
    print(f"  Tools used: {branch['tools_used']}")
    print(f"  Conclusion: {branch['conclusion']}")
    print(f"  Score: {branch['score']}")

print(f"\nBest path: {result.metadata['best_branch']}")
print(f"Final answer: {result.text}")
```

**Self-Consistency Reasoning:**

```python
# Self-consistency: generate multiple reasoning paths and vote
consistency_agent = ReasoningWithTools(
    llm=my_llm,
    tools=[calculator_tool],
    reasoning_strategy="self-consistency",
    num_samples=5  # Generate 5 independent reasoning paths
)

# Agent generates multiple solutions and picks most consistent
math_problem = Message.with_text(
    "user",
    "If x + 2y = 10 and 2x + y = 8, what is x + y?"
)

result = await consistency_agent.process(math_problem)

# Shows all reasoning paths and consensus
print(f"Generated {len(result.metadata['reasoning_samples'])} solutions:")
for sample in result.metadata['reasoning_samples']:
    print(f"  Answer: {sample['answer']}, Reasoning: {sample['steps']}")
print(f"\nConsensus answer: {result.text}")
```

**Pros:**
- ✅ Explicit reasoning (explainable AI)
- ✅ Better accuracy (multiple paths)
- ✅ Tool usage justified
- ✅ Self-verification
- ✅ Handles complex problems

**Cons:**
- ❌ Slow (multiple reasoning paths)
- ❌ Expensive (many LLM calls)
- ❌ Can generate contradictions
- ❌ Requires strong reasoning LLM

**Best Practices:**
1. Use Chain of Thought for straightforward problems
2. Use Tree of Thought for multi-path exploration
3. Use Self-Consistency for verification
4. Log all reasoning traces for debugging
5. Limit branches/samples to control cost
6. Combine with reflection for refinement

---

### Collaborative

**Purpose:** Multiple agents work together on shared tasks with bidirectional communication and shared workspace.

**When to Use:**
- Team-based problem solving
- Shared knowledge building
- Iterative refinement by multiple agents
- Consensus building
- Distributed expertise

**Pattern:**
```
Shared Workspace
     ↕
Agent 1 ⟷ Agent 2 ⟷ Agent 3
     ↕         ↕         ↕
[Bidirectional communication]
     ↓
Collaborative Result
```

**Implementation:**

```python
from agenkit.patterns import CollaborativeAgent
from agenkit import Message

# Create collaborative team
team = CollaborativeAgent(
    agents=[researcher, analyst, writer],
    collaboration_strategy="shared-workspace",
    max_rounds=5
)

# Agents collaborate on shared task
task = Message.with_text("user", "Research and write comprehensive market analysis")
result = await team.process(task)

# Result shows collaboration dynamics
print(result.metadata["collaboration_rounds"])
print(result.metadata["agent_contributions"])
```

**Detailed Example - Collaborative Writing:**

```python
from agenkit.patterns import CollaborativeAgent
from agenkit import Agent, Message

class OutlineAgent(Agent):
    """Creates document outline."""
    async def process(self, message: Message) -> Message:
        topic = message.text
        outline = f"Outline for {topic}:\n1. Introduction\n2. Body\n3. Conclusion"
        return Message.with_text("assistant", outline)

class ResearchAgent(Agent):
    """Researches content for each section."""
    async def process(self, message: Message) -> Message:
        outline = message.text
        research = f"Research findings:\n- Key fact 1\n- Key fact 2\n- Key fact 3"
        return Message.with_text("assistant", research)

class WriterAgent(Agent):
    """Writes full content based on outline and research."""
    async def process(self, message: Message) -> Message:
        content = message.text
        article = f"Full article:\n{content}\n[Expanded with details]"
        return Message.with_text("assistant", article)

class EditorAgent(Agent):
    """Reviews and refines the writing."""
    async def process(self, message: Message) -> Message:
        draft = message.text
        edited = f"Edited version:\n{draft}\n[Improved clarity and flow]"
        return Message.with_text("assistant", edited)

# Create collaborative writing team
writing_team = CollaborativeAgent(
    agents=[
        OutlineAgent(name="outliner"),
        ResearchAgent(name="researcher"),
        WriterAgent(name="writer"),
        EditorAgent(name="editor")
    ],
    collaboration_strategy="sequential-refinement",
    shared_context=True  # All agents see previous contributions
)

# Team collaborates on article
topic = Message.with_text("user", "The Impact of AI on Healthcare")
article = await writing_team.process(topic)

# Each agent contributes in sequence, building on previous work
print("Collaboration trace:")
for contribution in article.metadata["agent_contributions"]:
    print(f"{contribution['agent']}: {contribution['summary']}")
```

**Pros:**
- ✅ Leverages multiple perspectives
- ✅ Iterative improvement
- ✅ Shared knowledge
- ✅ Consensus building
- ✅ Team synergy

**Cons:**
- ❌ Coordination complexity
- ❌ Communication overhead
- ❌ Potential conflicts
- ❌ Slower than single-agent

**Best Practices:**
1. Define clear collaboration protocols
2. Use shared workspace for context
3. Limit collaboration rounds
4. Ensure agents have complementary skills
5. Monitor communication patterns
6. Use for complex, multifaceted tasks

---

## Summary

Choose patterns based on your needs:

1. **Simple tasks** → Task
2. **Multi-stage processing** → Sequential
3. **Speed matters** → Parallel
4. **Quality matters** → Reflection
5. **Need tools** → ReAct
6. **Complex projects** → Planning
7. **Chatbots** → Conversational
8. **Orchestration** → Agents as Tools
9. **Open-ended goals** → Autonomous
10. **Collaboration** → Multiagent
11. **Long conversations** → Memory Hierarchy
12. **High availability** → Fallback
13. **Quality control** → Supervisor
14. **Safety-critical** → Human in Loop
15. **Message routing** → Router
16. **Complex workflows** → Orchestration
17. **Enhanced reasoning** → Reasoning with Tools
18. **Team coordination** → Collaborative

Combine patterns for sophisticated agent systems! 🚀
