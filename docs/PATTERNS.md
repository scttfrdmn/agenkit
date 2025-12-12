# Agenkit Agent Patterns Guide

A comprehensive guide to the 11 agent patterns in Agenkit Python.

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
- [Performance Considerations](#performance-considerations)

---

## Overview

Agent patterns are reusable architectural templates that solve common problems in AI agent design. Agenkit provides 11 production-ready patterns that you can use immediately or combine for complex workflows.

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

Combine patterns for sophisticated agent systems! 🚀
