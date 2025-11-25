# Agent Patterns: A Comprehensive Guide

**Building Intelligent Systems with Agenkit**

*Version 0.1 - Foundation Release*

---

## Preface

This guide explores agent patterns through the lens of building production systems. We survey the landscape of agent frameworks in 2025, distill core patterns, and show how to implement them using Agenkit's minimal interface.

**What You'll Learn:**
- What agents are (and aren't)
- The distinction between agents, tasks, and tools
- Seven core agent patterns with implementations
- Production considerations for real deployments
- How Agenkit compares to other frameworks

**Who This Is For:**
- Software engineers building AI systems
- Architects designing multi-agent systems
- AI practitioners seeking production patterns
- Anyone wanting to understand the agent landscape

**How to Use This Guide:**
- **Linear reading**: Start at Chapter 1, progress through
- **Pattern reference**: Jump to specific patterns (Chapters 5-11)
- **Framework comparison**: See Chapter 3 for landscape analysis
- **Production focus**: Chapters 12-15 for deployment

This is a living document that will grow into a comprehensive book. The foundation chapters are complete. Pattern chapters are outlined with implementations planned.

---

## Table of Contents

### Part I: Foundations
- [Chapter 1: What is an Agent?](#chapter-1-what-is-an-agent)
- [Chapter 2: Agent vs Task vs Tool](#chapter-2-agent-vs-task-vs-tool)
- [Chapter 3: Framework Landscape](#chapter-3-framework-landscape) *(outline)*
- [Chapter 4: The Agenkit Philosophy](#chapter-4-the-agenkit-philosophy) *(outline)*

### Part II: Patterns
- [Chapter 5: Single Agent Pattern](#chapter-5-single-agent-pattern) *(outline)*
- [Chapter 6: Sequential Pattern](#chapter-6-sequential-pattern) *(outline)*
- [Chapter 7: Parallel Pattern](#chapter-7-parallel-pattern) *(outline)*
- [Chapter 8: Supervisor Pattern](#chapter-8-supervisor-pattern) *(outline)*
- [Chapter 9: Router Pattern](#chapter-9-router-pattern) *(outline)*
- [Chapter 10: Peer Collaboration Pattern](#chapter-10-peer-collaboration-pattern) *(outline)*
- [Chapter 11: Human-in-the-Loop Pattern](#chapter-11-human-in-the-loop-pattern) *(outline)*
- [Chapter 12: Reflection Pattern](#chapter-12-reflection-pattern) **✅ NEW in v0.12.0**
- [Chapter 13: Agents-as-Tools Pattern](#chapter-13-agents-as-tools-pattern) **✅ NEW in v0.12.0**
- [Chapter 14: Memory Hierarchy Pattern](#chapter-14-memory-hierarchy-pattern) **✅ NEW in v0.12.0**

### Part III: Production *(planned)*
- Chapter 15: State Management
- Chapter 16: Error Handling & Resilience
- Chapter 17: Deployment Patterns
- Chapter 18: Observability & Debugging

### Part IV: Advanced Topics *(planned)*
- Chapter 19: Multi-Agent Systems
- Chapter 20: Agent Learning & Adaptation
- Chapter 21: Future Directions

---

# Part I: Foundations

---

# Chapter 1: What is an Agent?

## 1.1 Defining Agency

The term "agent" has been used in AI for decades, but the rise of large language models has fundamentally changed what we mean by "agentic" systems. Let's start with the traditional definition, then explore the modern perspective.

### Traditional Definition

In classical AI (Russell & Norvig, *Artificial Intelligence: A Modern Approach*), an **agent** is:

> "Anything that can be viewed as perceiving its environment through sensors and acting upon that environment through actuators."

This definition includes everything from thermostats to autonomous vehicles. More specifically, Wooldridge defines a **rational agent** as one that:

1. **Acts autonomously** - operates without human intervention
2. **Perceives its environment** - gathers information about its context
3. **Persists over time** - continues to operate across multiple interactions
4. **Adapts to change** - modifies behavior based on new information
5. **Creates and pursues goals** - works toward specific objectives

These characteristics are useful but don't capture what makes modern LLM-based agents distinctive.

### Modern Perspective: LLM Output Controls Workflow

Hugging Face's smolagents framework offers a more practical modern definition:

> **"Agents are programs where LLM outputs control the workflow."**

This definition captures what's fundamentally different about LLM-based agents: the language model's output isn't just the final answer—it determines what the program does next. The LLM decides:

- Which tool to call
- What arguments to pass
- When to iterate vs when to finish
- How to react to observations

This is the key insight: **agency emerges when an LLM controls program execution**.

### Agency as a Spectrum

Agency isn't binary. It exists on a spectrum:

```
Low Agency                                                    High Agency
|-----------------------------------------------------------------------|
Simple      LLM with     Tool            Multi-step      Autonomous
wrapper     output       calling         reasoning       continuous
            parsing      agent           with memory     operation

Example:    Example:     Example:        Example:        Example:
"Classify   "Extract     "Search web,    "Research       "Monitor inbox,
this text"  structured   read results,   topic,          triage emails,
            data from    summarize"      compare         draft replies,
            response"                    sources,        learn from
                                        write report"    feedback"
```

**Key characteristics by position on spectrum:**

- **Low Agency** (0-20%):
  - Single LLM call
  - Deterministic output processing
  - No iteration or tool use
  - Human controls all decisions

- **Moderate Agency** (20-60%):
  - Multiple LLM calls
  - Tool calling based on output
  - Some iteration (fixed max steps)
  - Human defines workflow

- **High Agency** (60-90%):
  - Multi-step reasoning
  - LLM controls iteration
  - Memory and context management
  - Dynamic tool selection
  - Human oversight at key points

- **Full Autonomy** (90-100%):
  - Continuous operation
  - Self-directed goals
  - Learning and adaptation
  - Minimal human intervention

Most production systems today operate in the 40-80% range—significant agency, but with guardrails and human oversight.

### The PEAS Framework

To understand an agent's capabilities, consider the PEAS framework:

- **Performance**: How do we measure success?
- **Environment**: What context does it operate in?
- **Actuators**: What actions can it take?
- **Sensors**: What information can it perceive?

**Example: Customer Support Agent**

| Component | Description |
|-----------|-------------|
| **Performance** | Customer satisfaction, resolution time, accuracy |
| **Environment** | Support tickets, knowledge base, CRM system |
| **Actuators** | Search docs, create tickets, update CRM, send emails |
| **Sensors** | Read ticket content, query database, check user history |

This framework helps clarify what an agent can and cannot do.

## 1.2 The Agent Landscape (2025)

The agent ecosystem has exploded. Let's understand the current state.

### Market Growth

According to Deloitte's 2025 predictions:
- **25% of enterprises** using generative AI will deploy AI agents in 2025
- This grows to **50% by 2027**
- Primary use cases: customer service, code generation, data analysis

Production agents are no longer experimental—they're becoming standard.

### Production Examples

**Claude Code** (Anthropic):
- Autonomous coding assistant
- Reads files, writes code, runs tests
- Uses planning tool + sub-agents + file system
- Agency: ~70% (high oversight, but autonomous within tasks)

**Deep Research** (various implementations):
- Multi-step research with web search
- Gathers sources, compares information, synthesizes findings
- Uses planner-executor pattern
- Agency: ~60% (structured workflow, autonomous research)

**Manus** (workflow automation):
- Connects multiple systems
- Orchestrates data flows
- Adapts to API changes
- Agency: ~50% (predefined workflows, adaptive execution)

These systems show the maturity of agentic AI in 2025: they're solving real problems, handling complexity, and operating with meaningful autonomy.

### Framework Explosion

The number of agent frameworks has grown significantly:

| Framework | Focus | Agency Level | Best For |
|-----------|-------|-------------|----------|
| **Smolagents** | Code generation | Medium | Simple, code-first agents |
| **LangGraph** | State machines | High | Complex, stateful workflows |
| **CrewAI** | Role-based teams | High | Multi-agent collaboration |
| **LangChain** | Modular chains | Medium-High | Enterprise integration |
| **Haystack** | Pipeline/RAG | Medium | Search and QA systems |
| **AWS Bedrock** | Managed service | High | Enterprise, AWS-native |
| **Agenkit** | Minimal interface | Flexible | Cross-language, transport-agnostic |

We'll explore these frameworks in depth in Chapter 3.

## 1.3 Core Characteristics

What makes a system an agent vs just an LLM wrapper? Five key characteristics:

### 1. Autonomy: Self-Directed Behavior

The agent makes decisions without constant human input.

**Not Autonomous:**
```python
# Human controls everything
def process_request(query: str) -> str:
    prompt = f"Answer this: {query}"
    response = llm.generate(prompt)
    return response  # Done
```

**Autonomous:**
```python
# Agent controls its own process
async def process_request(query: str) -> str:
    plan = await planner.create_plan(query)

    for step in plan:
        if step.type == "search":
            results = await search_tool(step.query)
            context = await synthesizer.process(results)
        elif step.type == "analyze":
            analysis = await analyzer.analyze(context)
        # Agent decides what to do, when to stop

    return await writer.synthesize_response(context, analysis)
```

The agent determines the workflow—how many steps, which tools, when to finish.

### 2. Reactivity: Environment Awareness

The agent perceives and responds to its environment.

**Example: Adaptive Customer Support**
```python
class CustomerSupportAgent:
    async def handle_query(self, query: str, context: dict) -> str:
        # Perceive environment
        sentiment = await self.analyze_sentiment(query)
        user_history = context.get("history", [])

        # Adapt behavior based on perception
        if sentiment == "frustrated" and len(user_history) > 3:
            # Escalate to human
            return await self.escalate_to_human(query, context)
        elif sentiment == "curious":
            # Provide detailed explanation
            return await self.detailed_response(query)
        else:
            # Standard response
            return await self.standard_response(query)
```

The agent's behavior changes based on what it perceives.

### 3. Proactivity: Goal-Directed Behavior

The agent pursues objectives, not just reacting to inputs.

**Example: Research Agent with Sub-Goals**
```python
class ResearchAgent:
    async def research_topic(self, topic: str) -> Report:
        # Set main goal
        goal = Goal(f"Comprehensive report on {topic}")

        # Break into sub-goals (proactive planning)
        sub_goals = await self.create_sub_goals(goal)
        # -> [find_sources, verify_credibility, extract_key_points,
        #     compare_perspectives, synthesize_findings]

        # Pursue each sub-goal
        results = {}
        for sub_goal in sub_goals:
            results[sub_goal.name] = await self.pursue(sub_goal)

        # Synthesize toward main goal
        return await self.synthesize_report(goal, results)
```

The agent doesn't just answer questions—it sets and pursues goals.

### 4. Social Ability: Multi-Agent Interaction

The agent can communicate and collaborate with other agents.

**Example: Specialist Agents Collaborating**
```python
class CollaborativeAgents:
    async def solve_problem(self, problem: str) -> Solution:
        # Research agent gathers information
        research = await self.researcher.investigate(problem)

        # Analyst agent evaluates options
        analysis = await self.analyst.analyze(research)

        # Planner agent creates strategy
        plan = await self.planner.create_plan(analysis)

        # Executor agent implements (with feedback to planner)
        while not plan.complete:
            result = await self.executor.execute_step(plan.current_step)
            feedback = await self.evaluator.assess(result)

            if not feedback.acceptable:
                # Planner adapts based on feedback
                plan = await self.planner.replan(plan, feedback)

        return plan.result
```

Agents communicate, negotiate, and coordinate.

### 5. Learning: Adaptation Over Time

The agent improves through experience (though this is still emerging in 2025).

**Example: Tool Selection Learning**
```python
class LearningAgent:
    def __init__(self):
        self.tool_performance = {}  # Track tool effectiveness

    async def handle_query(self, query: str) -> str:
        # Select tool based on learned performance
        tool = self.select_best_tool(query, self.tool_performance)

        result = await tool.execute(query)

        # Learn from outcome
        success = await self.evaluate_result(result)
        self.tool_performance[tool.name] = {
            "success_rate": self.update_rate(tool.name, success),
            "avg_latency": self.update_latency(tool.name, result.latency)
        }

        return result
```

The agent gets better at tool selection over time.

## 1.4 What Agents Are Not

It's equally important to understand what agents **aren't**:

### Not Simple LLM Wrappers

```python
# This is NOT an agent
def ask_llm(question: str) -> str:
    return llm.generate(question)
```

**Why not?** No autonomy, no tool use, no iteration. Just input → output.

### Not Static Pipelines

```python
# This is NOT an agent (it's a pipeline)
async def process_document(doc: str) -> Summary:
    extracted = extract_text(doc)
    classified = classify(extracted)
    summarized = summarize(classified)
    return summarized
```

**Why not?** The flow is predetermined. No dynamic decision-making.

### Not Traditional APIs

```python
# This is NOT an agent (it's an API)
def search(query: str, filters: dict) -> Results:
    return database.query(query, filters)
```

**Why not?** Deterministic, no LLM, no reasoning.

### Not Deterministic Functions

Even with some complexity, if behavior is fully deterministic, it's not an agent:

```python
# Still NOT an agent
def route_request(request: Request) -> Response:
    if request.type == "A":
        return handle_a(request)
    elif request.type == "B":
        return handle_b(request)
    else:
        return handle_default(request)
```

**Why not?** No LLM controls workflow. Behavior is predefined.

### The Key Distinction

**Agents have LLM-driven control flow.** Everything else is automation, orchestration, or tooling—all useful, but not agentic.

## 1.5 The Agenkit Perspective

Agenkit takes a **minimal interface** approach to agents. Where other frameworks add abstractions, Agenkit strips them away.

### Core Interface

```python
class Agent:
    async def call(
        self,
        messages: list[Message],
        **kwargs
    ) -> Message:
        """That's it. One method."""
```

This minimal interface has profound implications:

**1. Maximum Flexibility**
You can implement any agent pattern—single, sequential, parallel, supervisor—using the same interface.

**2. Easy Composition**
```python
# Wrap agents in middleware
agent = MyAgent()
agent = RetryDecorator(agent, max_attempts=3)
agent = CachingDecorator(agent, max_size=1000)
agent = TracingMiddleware(agent, "my-agent")
```

**3. Transport Agnostic**
```python
# Same agent, different transports
from agenkit.adapter.http import HTTPAgent
from agenkit.adapter.grpc import GRPCAgent
from agenkit.adapter.websocket import WebSocketAgent

# HTTP server
HTTPAgent(my_agent, addr="0.0.0.0:8080")

# gRPC server (same agent!)
GRPCAgent(my_agent, addr="0.0.0.0:50051")

# WebSocket server (same agent!)
WebSocketAgent(my_agent, addr="0.0.0.0:8080")
```

**4. Cross-Language by Default**
```python
# Python agent
class PythonAgent:
    async def call(self, messages):
        # ... Python implementation
```

```go
// Go client (calls Python agent over HTTP)
agent := remote.NewAgent("http://localhost:8080")
response, _ := agent.Call(ctx, messages)
```

The Go code doesn't know or care that the agent is implemented in Python.

### Why Minimal Matters

Other frameworks add abstractions for:
- State management
- Tool schemas
- Workflow graphs
- Role definitions
- Memory systems

Agenkit says: **you can build all of these on top of `call(messages) -> message`**.

**Benefits:**
- **Easier to learn**: One interface to understand
- **Easier to debug**: Less framework magic
- **More flexible**: No framework constraints
- **More composable**: Middleware + transport + cross-language

**Tradeoffs:**
- More initial code to write
- You make the architectural decisions
- Less "batteries included"

Agenkit is for teams that want **control** over **convenience**.

### Positioning in the Landscape

Where does Agenkit fit?

```
High Abstraction (lots of framework)
↑
│ LangChain (many abstractions)
│ CrewAI (roles, teams)
│ Haystack (pipelines, components)
│ LangGraph (graphs, nodes, edges)
│
│ Agenkit (minimal interface) ← You are here
│
│ Smolagents (code generation)
│ Raw LLM APIs
↓
Low Abstraction (minimal framework)
```

Agenkit sits just above raw LLM APIs, providing:
- Transport abstraction (HTTP/gRPC/WS)
- Middleware composition (retry, cache, trace)
- Cross-language communication
- Message format standardization

But it doesn't prescribe:
- How to manage state
- How to structure workflows
- What tools to use
- How to coordinate agents

**You decide.** Agenkit provides the foundation.

---

## Summary: Chapter 1

**Key Takeaways:**

1. **Agents** are programs where LLM outputs control the workflow
2. **Agency exists on a spectrum** from low (single LLM call) to high (autonomous operation)
3. **Five core characteristics**: autonomy, reactivity, proactivity, social ability, learning
4. **Agents are not**: simple wrappers, static pipelines, traditional APIs, or deterministic functions
5. **Agenkit's minimal interface** provides maximum flexibility and control

**Next:** In Chapter 2, we'll distinguish agents from tasks and tools—three related but distinct primitives for building AI systems.

---

# Chapter 2: Agent vs Task vs Tool

## Introduction

The terms "agent," "task," and "tool" are often used interchangeably, but they represent distinct concepts with different use cases. Understanding when to use each is crucial for building maintainable systems.

**The Three Primitives:**
- **Agent**: Stateful, conversational, autonomous
- **Task**: One-shot, ephemeral, with cleanup
- **Tool**: Deterministic function, no LLM

Let's explore each in depth.

## 2.1 The Agent Primitive

### Definition

An **agent** is a stateful, conversational entity that maintains context across multiple interactions.

**Characteristics:**
- **Persistent**: Exists across multiple calls
- **Stateful**: Remembers previous interactions
- **Conversational**: Handles multi-turn dialogue
- **Autonomous**: Makes its own decisions
- **Complex**: Can perform multi-step reasoning

### When to Use Agents

Use agents when you need:

1. **Multi-turn conversations**
   ```
   User: "What's the weather in SF?"
   Agent: "It's 68°F and sunny in San Francisco."
   User: "How about tomorrow?"
   Agent: "Tomorrow will be 71°F with partly cloudy skies."
   ↑ Agent remembers we're talking about SF
   ```

2. **Persistent state across sessions**
   ```python
   # Session 1
   agent.call([Message(user, "My name is Alice")])

   # Session 2 (later)
   agent.call([Message(user, "What's my name?")])
   # -> "Your name is Alice" (remembered from session 1)
   ```

3. **Complex, multi-step workflows**
   ```
   Task: "Research competitors and write a report"
   Agent steps:
   1. Search for competitors
   2. Visit each website
   3. Extract key information
   4. Compare features
   5. Analyze strengths/weaknesses
   6. Write structured report
   ↑ Multiple steps, dynamic decision-making
   ```

4. **Adaptive behavior based on context**
   ```python
   if user.sentiment == "frustrated":
       return empathetic_response()
   elif user.tier == "enterprise":
       return detailed_technical_response()
   else:
       return standard_response()
   ```

### Agent Implementation Pattern

```python
class ConversationalAgent:
    """
    Stateful agent with memory and tools.
    """

    def __init__(self, llm, tools, memory_store):
        self.llm = llm
        self.tools = tools
        self.memory = memory_store

    async def call(
        self,
        messages: list[Message],
        session_id: str,
        **kwargs
    ) -> Message:
        # Load conversation history
        history = await self.memory.load(session_id)

        # Combine history with new messages
        full_context = history + messages

        # Generate response (may use tools)
        response = await self.llm.complete(full_context)

        # Check if agent wants to use a tool
        if response.wants_tool_call:
            tool_result = await self.execute_tool(response.tool_call)
            response = await self.llm.complete(
                full_context + [response, tool_result]
            )

        # Save updated history
        await self.memory.save(
            session_id,
            history + messages + [response]
        )

        return response
```

**Key points:**
- Maintains state via `memory` store
- Handles tool execution
- Multi-turn conversation support
- Session-based isolation

### Agent Lifecycle

```
[Create] → [Multiple Calls] → [Persist State] → [Later Calls] → [Eventually Cleanup]
   ↓           ↓                    ↓                 ↓                    ↓
 agent =    call()              save state        call()              dispose()
 Agent()    call()                                call()
           call()
```

Agents are **long-lived**. They exist across many interactions.

## 2.2 The Task Primitive

### Definition

A **task** is a one-shot execution of an agent with automatic cleanup.

**Characteristics:**
- **Ephemeral**: Exists only for one execution
- **Stateless**: No memory between calls
- **Bounded**: Has timeout and retry limits
- **Clean**: Automatic resource cleanup
- **Simple**: Single input → single output

### When to Use Tasks

Use tasks when you need:

1. **One-shot queries with no follow-up**
   ```python
   async with Task(agent, timeout=10.0) as task:
       result = await task.execute([
           Message(role="user", content="Summarize this article")
       ])
   # Task cleaned up automatically
   ```

2. **Resource-bounded execution**
   ```python
   # Enforce timeout
   async with Task(agent, timeout=30.0) as task:
       result = await task.execute(messages)
   # Times out after 30s, no hanging
   ```

3. **Retry with backoff**
   ```python
   async with Task(agent, retries=3) as task:
       result = await task.execute(messages)
   # Auto-retries on transient failures
   ```

4. **Stateless operations**
   ```python
   # Each execution is independent
   task1 = await Task(agent).execute([Message(...)])
   task2 = await Task(agent).execute([Message(...)])
   # task2 doesn't know about task1
   ```

### Task Implementation Pattern

```python
class Task:
    """
    One-shot agent execution with cleanup.

    Implements context manager for automatic resource management.
    """

    def __init__(
        self,
        agent: Agent,
        timeout: float | None = None,
        retries: int = 0,
        **kwargs
    ):
        self.agent = agent
        self.timeout = timeout
        self.retries = retries
        self.completed = False
        self.result = None

    async def execute(
        self,
        messages: list[Message],
        **kwargs
    ) -> Message:
        """Execute agent once, with retry and timeout."""
        if self.completed:
            raise RuntimeError(
                "Task already completed. Create a new Task."
            )

        attempts = self.retries + 1

        for attempt in range(attempts):
            try:
                if self.timeout:
                    result = await asyncio.wait_for(
                        self.agent.call(messages, **kwargs),
                        timeout=self.timeout
                    )
                else:
                    result = await self.agent.call(messages, **kwargs)

                self.completed = True
                self.result = result
                return result

            except asyncio.TimeoutError:
                self.completed = True
                await self.cleanup()
                raise

            except Exception as e:
                if attempt == attempts - 1:
                    # Last attempt failed
                    self.completed = True
                    await self.cleanup()
                    raise

                # Retry with exponential backoff
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)

    async def cleanup(self):
        """Clean up resources."""
        # Close connections, release locks, etc.
        if hasattr(self.agent, 'cleanup'):
            await self.agent.cleanup()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
```

**Key points:**
- Single execution only (`completed` flag)
- Automatic timeout enforcement
- Retry with exponential backoff
- Context manager for cleanup
- No state between executions

### Task Lifecycle

```
[Create] → [Execute Once] → [Cleanup] → [Done]
   ↓            ↓              ↓
Task()      execute()      cleanup()
           (with retries)  (automatic)
```

Tasks are **short-lived**. They exist for a single execution.

## 2.3 The Tool Primitive

### Definition

A **tool** is a deterministic function that an agent can call to perform specific operations.

**Characteristics:**
- **Deterministic**: Same input → same output
- **No LLM**: Pure computation or API calls
- **Focused**: Does one thing well
- **Composable**: Can be combined
- **Fast**: No LLM latency

### When to Use Tools

Use tools when you need:

1. **Deterministic operations**
   ```python
   @tool
   def calculator(expression: str) -> float:
       """Calculate mathematical expressions."""
       return eval(expression)  # (with safety checks)
   ```

2. **External API calls**
   ```python
   @tool
   async def search_web(query: str, max_results: int = 10) -> list[Result]:
       """Search the web for information."""
       return await web_api.search(query, limit=max_results)
   ```

3. **Database queries**
   ```python
   @tool
   async def lookup_user(user_id: str) -> User:
       """Get user information from database."""
       return await db.query("SELECT * FROM users WHERE id = ?", user_id)
   ```

4. **File operations**
   ```python
   @tool
   async def read_file(path: str) -> str:
       """Read file contents."""
       async with aiofiles.open(path, 'r') as f:
           return await f.read()
   ```

### Tool Implementation Pattern

```python
from typing import Callable, Any
from dataclasses import dataclass

@dataclass
class ToolDefinition:
    """Metadata about a tool."""
    name: str
    description: str
    parameters: dict  # JSON schema
    function: Callable

def tool(func: Callable) -> ToolDefinition:
    """
    Decorator to register a function as a tool.

    Example:
        @tool
        def calculator(expression: str) -> float:
            '''Calculate mathematical expressions.'''
            return eval(expression)
    """
    return ToolDefinition(
        name=func.__name__,
        description=func.__doc__ or "",
        parameters=extract_params(func),
        function=func
    )

class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self.tools: dict[str, ToolDefinition] = {}

    def register(self, tool_def: ToolDefinition):
        """Add a tool to the registry."""
        self.tools[tool_def.name] = tool_def

    async def execute(
        self,
        tool_name: str,
        **kwargs: Any
    ) -> Any:
        """Execute a tool by name."""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool = self.tools[tool_name]

        # Validate parameters
        self.validate_params(tool, kwargs)

        # Execute
        if asyncio.iscoroutinefunction(tool.function):
            return await tool.function(**kwargs)
        else:
            return tool.function(**kwargs)

    def get_schemas(self) -> list[dict]:
        """Get tool schemas for LLM."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self.tools.values()
        ]
```

**Key points:**
- Simple decorator pattern
- Registry for discovery
- Schema generation for LLMs
- Sync and async support
- Parameter validation

### Tool Lifecycle

```
[Define] → [Register] → [Agent Calls] → [Execute] → [Return Result]
   ↓          ↓             ↓              ↓              ↓
@tool()   registry.   agent decides   validate      return
         register()    to use tool     params        value
```

Tools are **stateless functions**. Each call is independent.

## 2.4 When to Use Each: Decision Tree

```
START: I need to build something with an LLM

Q: Does it need to remember past conversations?
├─ YES → Use AGENT
│         └─ Multi-turn dialogue, persistent state
│
└─ NO → Q: Is it a single input/output operation?
         ├─ YES → Q: Does it need cleanup or retry logic?
         │        ├─ YES → Use TASK
         │        │        └─ One-shot with timeout, retry, cleanup
         │        │
         │        └─ NO → Q: Is it deterministic (no LLM needed)?
         │                 ├─ YES → Use TOOL
         │                 │        └─ Pure function, API call, computation
         │                 │
         │                 └─ NO → Use simple agent.call()
         │
         └─ NO → Complex workflow
                 └─ Use AGENT with multiple calls
```

### Examples by Category

| Scenario | Use | Why |
|----------|-----|-----|
| Customer support chat | **Agent** | Multi-turn, remembers context |
| "Summarize this article" | **Task** | One-shot, cleanup after |
| Calculate 2+2 | **Tool** | Deterministic, no LLM |
| Research and write report | **Agent** | Multi-step, autonomous |
| Translate text | **Task** | One input, one output, bounded |
| Search database | **Tool** | API call, no reasoning |
| Analyze code quality | **Agent** | Multiple files, complex analysis |
| Retry failed API call | **Task** | One-shot with retry |
| Convert currency | **Tool** | Simple calculation |

## 2.5 Composition Rules

How do these primitives combine?

### Valid Compositions

✅ **Agent uses Tools**
```python
class AgentWithTools:
    def __init__(self, llm, tools: ToolRegistry):
        self.llm = llm
        self.tools = tools

    async def call(self, messages):
        # Agent can call tools
        response = await self.llm.complete(messages)
        if response.wants_tool_call:
            result = await self.tools.execute(
                response.tool_name,
                **response.tool_args
            )
            # Continue with tool result
```

✅ **Task wraps Agent**
```python
async with Task(my_agent, timeout=30.0) as task:
    result = await task.execute(messages)
```

✅ **Agent coordinates multiple Agents**
```python
class SupervisorAgent:
    def __init__(self, specialists: dict[str, Agent]):
        self.specialists = specialists

    async def call(self, messages):
        # Delegate to specialist agents
        specialist = self.choose_specialist(messages)
        return await specialist.call(messages)
```

✅ **Tool calls external API or service (can be an Agent)**
```python
@tool
async def call_research_agent(query: str) -> str:
    """Call specialized research agent."""
    agent = RemoteAgent("http://research-agent:8080")
    response = await agent.call([Message(role="user", content=query)])
    return response.content
```

### Invalid Compositions

❌ **Tool should not contain Agent logic**
```python
# WRONG - tool should be deterministic
@tool
async def smart_search(query: str) -> str:
    llm = LLM()
    enhanced_query = await llm.enhance(query)  # NO!
    return await search(enhanced_query)
```
**Why wrong?** Tools should be deterministic. If you need LLM reasoning, make it an Agent.

❌ **Agent wrapping Task** (makes no sense)
```python
# WRONG - unnecessary indirection
class WeirdAgent:
    async def call(self, messages):
        async with Task(another_agent) as task:
            return await task.execute(messages)
        # Just call another_agent directly!
```
**Why wrong?** Task is for adding timeout/retry/cleanup. If you need those, use Task. If not, call agent directly.

❌ **Task with persistent state**
```python
# WRONG - tasks should be stateless
class StatefulTask(Task):
    def __init__(self):
        self.history = []  # NO!

    async def execute(self, messages):
        self.history.append(messages)  # Tasks shouldn't remember
```
**Why wrong?** Use an Agent for stateful behavior. Tasks are ephemeral.

### Correct Architecture

```
┌──────────────────────────────────────┐
│ Application Layer                    │
├──────────────────────────────────────┤
│  User Request                         │
│       ↓                               │
│  [Supervisor Agent] ←─────┐          │
│       ↓                     │          │
│  ┌─────────────┬──────────┬─────┐   │
│  │             │          │      │   │
│  [Specialist  [Specialist [Tool ]│   │
│   Agent A]     Agent B]   Registry│  │
│       ↓             ↓          ↓   │  │
│  [uses Tools]  [uses Tools]  [Tools]│
│                                      │
└──────────────────────────────────────┘

Composition:
- Supervisor Agent coordinates specialist agents
- Specialist Agents use Tools for deterministic ops
- Tools are stateless functions
- Each component has clear responsibility
```

---

## 2.6 Practical Examples

Let's see complete examples of each primitive.

### Example 1: Customer Support Agent

**Requirements:**
- Remember customer conversation
- Look up order information
- Handle multi-turn dialogue

**Solution: Agent + Tools**

```python
# Define tools
@tool
async def lookup_order(order_id: str) -> dict:
    """Get order details from database."""
    return await db.orders.find_one({"id": order_id})

@tool
async def track_shipment(tracking_number: str) -> dict:
    """Get shipment tracking information."""
    return await shipping_api.track(tracking_number)

# Register tools
tools = ToolRegistry()
tools.register(lookup_order)
tools.register(track_shipment)

# Create agent
class CustomerSupportAgent:
    def __init__(self, llm, tools, memory_store):
        self.llm = llm
        self.tools = tools
        self.memory = memory_store

    async def call(self, messages, session_id):
        # Load history
        history = await self.memory.load(session_id)
        context = history + messages

        # Provide tool schemas to LLM
        tool_schemas = self.tools.get_schemas()

        # Generate response
        response = await self.llm.complete(
            context,
            tools=tool_schemas
        )

        # Handle tool calls
        while response.tool_calls:
            for tool_call in response.tool_calls:
                result = await self.tools.execute(
                    tool_call.name,
                    **tool_call.arguments
                )
                context.append(Message(
                    role="tool",
                    content=str(result),
                    name=tool_call.name
                ))

            # Get next response
            response = await self.llm.complete(
                context,
                tools=tool_schemas
            )

        # Save conversation
        await self.memory.save(
            session_id,
            history + messages + [response]
        )

        return response

# Usage
agent = CustomerSupportAgent(llm, tools, memory_store)

# Turn 1
response1 = await agent.call(
    [Message(role="user", content="Where is my order #12345?")],
    session_id="user-789"
)
# Agent calls lookup_order tool, responds with order status

# Turn 2 (same session)
response2 = await agent.call(
    [Message(role="user", content="When will it arrive?")],
    session_id="user-789"
)
# Agent remembers we're talking about order #12345
```

**Why Agent?** Multi-turn conversation, needs to remember context.

**Why Tools?** Order lookup and tracking are deterministic operations.

### Example 2: Document Summarization

**Requirements:**
- Summarize single document
- No follow-up questions
- Should timeout if too long

**Solution: Task**

```python
class SummarizationAgent:
    async def call(self, messages):
        # Simple summarization
        return await self.llm.complete(messages)

# Usage with Task for timeout and cleanup
agent = SummarizationAgent(llm)

async with Task(agent, timeout=30.0) as task:
    summary = await task.execute([
        Message(
            role="user",
            content=f"Summarize this: {document_text}"
        )
    ])

print(summary.content)
# Task automatically cleaned up
```

**Why Task?** One-shot operation, needs timeout, no state.

### Example 3: Data Processing Pipeline

**Requirements:**
- Extract → Transform → Load
- Each step is deterministic
- No LLM needed

**Solution: Tools**

```python
@tool
def extract_data(file_path: str) -> dict:
    """Extract data from CSV file."""
    import csv
    with open(file_path) as f:
        return list(csv.DictReader(f))

@tool
def transform_data(data: dict, rules: dict) -> dict:
    """Apply transformation rules to data."""
    # Apply rules (deterministic)
    return apply_transformations(data, rules)

@tool
async def load_data(data: dict, target: str) -> bool:
    """Load data to target database."""
    await db.bulk_insert(target, data)
    return True

# Usage (no agent needed!)
data = extract_data("input.csv")
transformed = transform_data(data, rules)
loaded = await load_data(transformed, "target_table")
```

**Why Tools?** All operations are deterministic, no reasoning needed.

---

## 2.7 Common Mistakes

### Mistake 1: Using Agent When Task Would Suffice

❌ **Wrong:**
```python
class TranslationAgent:
    def __init__(self):
        self.history = []  # Unnecessary!

    async def call(self, messages):
        self.history.append(messages)
        return await llm.translate(messages[-1].content)

agent = TranslationAgent()
# Keeping state for no reason
```

✅ **Correct:**
```python
class TranslationAgent:
    async def call(self, messages):
        return await llm.translate(messages[-1].content)

# Use Task for one-shot
async with Task(TranslationAgent(), timeout=10.0) as task:
    result = await task.execute([Message(...)])
```

### Mistake 2: Using Tool With Non-Deterministic Logic

❌ **Wrong:**
```python
@tool
async def smart_response(query: str) -> str:
    """Generate smart response."""
    # Tool contains LLM logic!
    return await llm.generate(f"Respond to: {query}")
```

✅ **Correct:**
```python
# Make it an Agent
class ResponseAgent:
    async def call(self, messages):
        return await llm.complete(messages)
```

### Mistake 3: Not Using Task When You Need Timeout

❌ **Wrong:**
```python
# No timeout protection
result = await potentially_slow_agent.call(messages)
# Could hang forever!
```

✅ **Correct:**
```python
async with Task(potentially_slow_agent, timeout=30.0) as task:
    result = await task.execute(messages)
# Times out after 30 seconds
```

---

## Summary: Chapter 2

**Key Takeaways:**

1. **Three distinct primitives:**
   - **Agent**: Stateful, multi-turn, autonomous
   - **Task**: One-shot, ephemeral, with cleanup
   - **Tool**: Deterministic, no LLM

2. **Decision tree:**
   - Needs conversation history? → Agent
   - One-shot with timeout/retry? → Task
   - Deterministic operation? → Tool

3. **Valid compositions:**
   - Agent uses Tools ✅
   - Task wraps Agent ✅
   - Agent coordinates Agents ✅
   - Tool as Agent wrapper ✅ (for remote agents)

4. **Common mistakes:**
   - Using Agent when Task suffices
   - Putting LLM logic in Tools
   - Not using Task when timeout needed

**Next:** In Chapter 3, we'll survey the framework landscape and understand how different frameworks approach these primitives.

---

# Chapter 3: Framework Landscape

## Introduction

*(This chapter is outlined. Full content to be written.)*

The agent framework ecosystem has exploded in 2025. Understanding the landscape helps you choose the right tool for your needs—and understand where Agenkit fits.

### Topics to Cover:

**3.1 Framework Comparison**
- Smolagents: Code-first, minimal
- AWS Bedrock: Managed, enterprise
- LangGraph: Graph-based state machines
- CrewAI: Role-based teams
- LangChain: Modular chains
- Haystack: Pipeline, RAG-first
- Agenkit: Minimal interface

**3.2 Mental Models**
- How each framework thinks about agents
- Core abstractions and patterns
- Learning curves and complexity

**3.3 When to Use Each**
- Decision matrix by use case
- Integration requirements
- Team constraints

**3.4 Interoperability**
- Using frameworks together
- Agenkit as transport layer

**3.5 Lessons from the Landscape**
- Trends toward less abstraction
- Importance of visibility
- State management patterns

---

# Chapter 4: The Agenkit Philosophy

## Introduction

*(This chapter is outlined. Full content to be written.)*

Why does Agenkit take a minimal approach? What are the benefits and tradeoffs?

### Topics to Cover:

**4.1 Design Principles**
- Minimal: Fewest concepts
- Explicit: No magic
- Composable: Build complex from simple
- Cross-language: Python ↔ Go
- Observable: Full tracing

**4.2 The Core Interface**
```python
class Agent:
    async def call(messages, **kwargs) -> Message: ...
```

**4.3 Why Minimal Matters**
- Easier reasoning
- Simpler debugging
- Lower learning curve
- More flexibility

**4.4 Transport Abstraction**
- HTTP, gRPC, WebSocket
- Location transparency
- Cross-language by default

**4.5 Middleware Composition**
- Retry, cache, circuit breaker
- Observability
- Stack like functions

**4.6 Comparison with Maximal Frameworks**
- When you need more abstractions
- When minimal is better

---

# Part II: Patterns

---

# Chapter 5: Single Agent Pattern

## Overview

*(This chapter is outlined. Full content to be written.)*

The simplest useful agent: one agent, one task.

### Topics to Cover:

**5.1 When to Use**
- Simple, focused tasks
- No coordination needed
- Direct user interaction

**5.2 Architecture**
```
User → Agent → LLM → Tools → Response
```

**5.3 Implementation Patterns**
- Basic agent with tools
- Conversational agent
- Specialist agent

**5.4 Code-First Agents** (Smolagents pattern)
- Generate Python code
- Execute in sandbox
- Leverage LLM code training

**5.5 ReAct Pattern** (LangChain)
- Reasoning + Acting
- Thought → Action → Observation loop

**5.6 State Management**
- Message history
- External memory
- Session management

**Case Study:** Customer support agent

---

# Chapter 6: Sequential Pattern

## Overview

*(This chapter is outlined. Full content to be written.)*

Pipeline of agents executing in order.

### Topics to Cover:

**6.1 When to Use**
- Multi-stage processing
- Clear dependencies
- Quality control

**6.2 Architecture**
```
Agent1 → Agent2 → Agent3 → Result
```

**6.3 Implementation**
```python
class SequentialAgent:
    async def call(self, messages):
        result = messages
        for agent in self.agents:
            result = await agent.call(result)
        return result
```

**6.4 Pipeline Patterns**
- Linear pipeline
- Branches
- Feedback loops
- Validation stages

**Case Study:** Document processing (extract → classify → summarize)

---

# Chapter 7: Parallel Pattern

## Overview

*(This chapter is outlined. Full content to be written.)*

Concurrent agent execution for speed and ensemble methods.

### Topics to Cover:

**7.1 When to Use**
- Independent subtasks
- Low latency needs
- Ensemble methods

**7.2 Architecture**
```
[Agent1, Agent2, Agent3] → Aggregator → Result
```

**7.3 Aggregation Strategies**
- Voting
- Merging
- Best-of-N
- Consensus

**7.4 Scatter-Gather** (LangGraph pattern)
- Split input
- Process parallel
- Gather and merge

**Case Study:** Multi-model analysis (GPT-4 + Claude + Gemini)

---

# Chapter 8: Supervisor Pattern

## Overview

*(This chapter is outlined. Full content to be written.)*

Hierarchical coordination with central supervisor.

### Topics to Cover:

**8.1 When to Use**
- Complex task decomposition
- Specialized sub-agents
- Dynamic delegation

**8.2 Architecture**
```
Supervisor → [Specialist1, Specialist2, Specialist3]
```

**8.3 Supervisor Variants**
- Static routing
- Dynamic routing (LLM decides)
- With fallback (Bedrock pattern)
- Hierarchical (multi-level)

**8.4 Planner-Executor** (LangChain)
- Planner: Strategy
- Executors: Tactical
- Feedback loop

**Case Study:** Software development agent

---

# Chapter 9: Router Pattern

## Overview

*(This chapter is outlined. Full content to be written.)*

Conditional selection of specialized agents.

### Topics to Cover:

**9.1 When to Use**
- Multiple execution paths
- Specialized by domain
- Efficiency optimization

**9.2 Routing Strategies**
- LLM-based classification
- Rule-based
- Hybrid
- Similarity-based

**9.3 Supervisor vs Router**
- Router: Single selection
- Supervisor: Multiple coordination

**Case Study:** Customer service router

---

# Chapter 10: Peer Collaboration Pattern

## Overview

*(This chapter is outlined. Full content to be written.)*

Agents working together iteratively.

### Topics to Cover:

**10.1 When to Use**
- Iterative refinement
- Multiple perspectives
- Debate and consensus

**10.2 Collaboration Patterns**
- Debate
- Refine
- Consensus
- Swarm (Haystack)

**10.3 Peer-to-Peer** (LangGraph)
- No central coordinator
- Emergent intelligence

**Case Study:** Code review system

---

# Chapter 11: Human-in-the-Loop Pattern

## Overview

*(This chapter is outlined. Full content to be written.)*

Agents with human oversight for high-stakes decisions.

### Topics to Cover:

**11.1 When to Use**
- High-stakes decisions
- Regulatory requirements
- Trust building

**11.2 Approval Patterns**
- Pre-execution
- Post-execution
- Confidence-based
- Random sampling

**11.3 Feedback Loops**
- Learning from corrections
- Confidence calibration

**11.4 Self-Reflection** (Haystack)
- Output validators
- Quality control

**Case Study:** Financial trading agent

---

# Chapter 12: Reflection Pattern

## Overview

The Reflection pattern enables agents to improve their outputs through iterative self-critique and refinement. An agent generates an initial output, a critic evaluates it, and the generator refines based on feedback—repeating until quality thresholds are met.

**✅ Implemented in Agenkit v0.12.0**

### 12.1 When to Use

Use reflection when you need:

- **Quality improvement through iteration**: Code generation, content creation, analysis
- **Self-critique and error detection**: Catching mistakes automatically
- **Incremental refinement**: Multi-draft writing, optimization problems
- **Quality threshold enforcement**: Ensuring output meets standards

**Don't use when:**
- Single-pass quality is sufficient
- Iteration doesn't improve results
- Cost/latency constraints are tight

### 12.2 Architecture

```
User Query
    ↓
[Generator Agent] → Initial Output
    ↓
[Critic Agent] → Quality Score + Feedback
    ↓
[Generator Agent] → Refined Output
    ↓
(Repeat until quality threshold, minimal improvement, or max iterations)
    ↓
Final Output
```

### 12.3 Implementation

```python
from agenkit.patterns import ReflectionAgent

# Create generator and critic agents
generator = CodeGeneratorAgent()
critic = CodeReviewAgent()

# Create reflection agent
agent = ReflectionAgent(
    generator=generator,
    critic=critic,
    max_iterations=5,
    quality_threshold=0.9,       # Stop when quality >= 0.9
    improvement_threshold=0.05,  # Stop if improvement < 5%
)

# Execute with automatic refinement
result = await agent.process(
    Message(role="user", content="Write a function to calculate Fibonacci numbers")
)

# Access metadata
print(f"Iterations: {result.metadata['reflection_iterations']}")
print(f"Final quality: {result.metadata['final_quality_score']}")
print(f"Stop reason: {result.metadata['stop_reason']}")
```

### 12.4 Stopping Conditions

The reflection loop terminates when:

1. **Quality threshold met**: Score >= `quality_threshold`
2. **Minimal improvement**: Improvement < `improvement_threshold`
3. **Max iterations reached**: Iteration count >= `max_iterations`
4. **Perfect score**: Score == 1.0

### 12.5 Critique Formats

**Structured JSON** (default):
```python
{
  "score": 0.85,
  "feedback": "Good progress. Add error handling for negative inputs."
}
```

**Free-form text**:
```
The code looks good overall (8.5/10). Consider adding:
- Error handling for negative inputs
- Documentation with examples
```

Set `critique_format=CritiqueFormat.FREEFORM` for text-based critiques.

### 12.6 Production Considerations

**Cost Management:**
- Each iteration = 2 LLM calls (generate + critique)
- Set reasonable `max_iterations` (3-5 typical)
- Use cheaper models for critique when possible

**Quality Calibration:**
- Test your critic's scoring on known examples
- Adjust thresholds based on your domain
- Monitor improvement rates

**History Tracking:**
- Set `verbose=True` to include full iteration history
- Use `agent.get_history()` for debugging
- Track quality improvements over time

### 12.7 Advanced Patterns

**Multi-Critic Ensemble:**
```python
critics = [
    CodeQualityagent(),
    SecurityCriticAgent(),
    PerformanceCriticAgent()
]

# Aggregate scores
total_score = sum(c.score for c in critics) / len(critics)
```

**Domain-Specific Refinement:**
```python
class SpecializedReflectionAgent(ReflectionAgent):
    async def _build_refinement_prompt(self, ...):
        # Custom refinement instructions
        return f"Refine for {self.domain}: {feedback}"
```

**See Also:**
- `examples/patterns/06_reflection_agent.py` - Complete demos
- `tests/patterns/test_reflection.py` - 22 tests covering all scenarios

---

# Chapter 13: Agents-as-Tools Pattern

## Overview

The Agents-as-Tools pattern (also called Hierarchical Agents) enables agents to call other agents as tools, creating multi-level agent hierarchies where specialized agents can be invoked by supervisor agents.

**✅ Implemented in Agenkit v0.12.0**

### 13.1 When to Use

Use agents-as-tools when you need:

- **Domain specialization**: Different agents for code, data, research, etc.
- **Hierarchical organization**: Supervisor → specialists
- **Agent reuse**: Same specialist across multiple supervisors
- **Seamless integration**: Works with existing ReAct pattern
- **Clear separation**: Each agent has focused responsibility

**Don't use when:**
- Simple tool calls suffice (use regular tools)
- No need for agent-level reasoning in specialists
- Flat architecture is simpler

### 13.2 Architecture

```
User Query
    ↓
[Supervisor Agent] (decides which specialist)
    ↓
┌────────────┬────────────┬────────────┐
│            │            │            │
[Code       [Data       [Research    [Other
 Specialist] Specialist] Specialist]  Specialists]
    │            │            │
    └────────────┴────────────┘
               ↓
          Final Response
```

### 13.3 Implementation

```python
from agenkit.patterns import agent_as_tool, ReActAgent, ToolRegistry

# Create specialist agents
code_agent = AnthropicAgent(
    system_prompt="You are an expert programmer..."
)
data_agent = AnthropicAgent(
    system_prompt="You are an expert data analyst..."
)

# Wrap specialists as tools
code_tool = agent_as_tool(
    agent=code_agent,
    name="code_specialist",
    description="Expert in programming. Use for code-related questions."
)

data_tool = agent_as_tool(
    agent=data_agent,
    name="data_specialist",
    description="Expert in data analysis. Use for data questions."
)

# Register with supervisor
registry = ToolRegistry()
registry.register(code_tool)
registry.register(data_tool)

# Create supervisor that routes to specialists
supervisor = ReActAgent(
    llm_client=llm,
    tool_registry=registry,
    max_iterations=5
)

# Supervisor automatically delegates
result = await supervisor.process(
    Message(role="user", content="Write a function to analyze sales data")
)
# Supervisor calls data_specialist tool (which wraps data_agent)
```

### 13.4 Output Formats

**String (default):**
```python
tool = agent_as_tool(agent, "name", "desc", output_format="str")
result = await tool.execute(query="Task")
# result is a string
```

**Dictionary:**
```python
tool = agent_as_tool(agent, "name", "desc",
                    output_format="dict",
                    include_metadata=True)
result = await tool.execute(query="Task")
# result = {"content": "...", "metadata": {...}}
```

**Message:**
```python
tool = agent_as_tool(agent, "name", "desc", output_format="message")
result = await tool.execute(query="Task")
# result is a Message object
```

### 13.5 Multi-Level Hierarchies

```python
# Level 3: Specialists
python_agent = CodeSpecialistAgent(language="python")
rust_agent = CodeSpecialistAgent(language="rust")

# Level 2: Domain managers
python_tool = agent_as_tool(python_agent, "python_expert", "Python specialist")
rust_tool = agent_as_tool(rust_agent, "rust_expert", "Rust specialist")

code_registry = ToolRegistry()
code_registry.register(python_tool)
code_registry.register(rust_tool)

code_manager = ReActAgent(llm, code_registry)

# Level 1: Top supervisor
code_manager_tool = agent_as_tool(code_manager, "code_manager", "Manages all coding tasks")

supervisor_registry = ToolRegistry()
supervisor_registry.register(code_manager_tool)
supervisor_registry.register(data_tool)  # Other specialists

supervisor = ReActAgent(llm, supervisor_registry)
```

### 13.6 Direct Invocation

Agents wrapped as tools can also be called directly:

```python
# Create specialist tool
specialist_tool = agent_as_tool(
    agent=specialist_agent,
    name="specialist",
    description="Domain expert",
    input_key="task"  # Custom parameter name
)

# Call directly (bypass supervisor)
result = await specialist_tool.execute(task="Analyze this data")
```

### 13.7 Production Considerations

**Performance:**
- Each delegation = extra LLM call for routing
- Consider direct routing for simple cases
- Use cheaper models for routing decisions

**Error Handling:**
- Specialist failures propagate to supervisor
- Add retry/fallback at supervisor level
- Log delegation decisions for debugging

**Cost Optimization:**
- Use smaller models for specialists when possible
- Cache specialist results
- Limit delegation depth

**See Also:**
- `examples/patterns/07_hierarchical_agents.py` - Complete demos
- `tests/patterns/test_agents_as_tools.py` - 20 tests with ReAct integration

---

# Chapter 14: Memory Hierarchy Pattern

## Overview

The Memory Hierarchy pattern provides a multi-tier memory system for agents, automatically managing memory across working (in-context), short-term (session), and long-term (persistent) storage tiers.

**✅ Implemented in Agenkit v0.12.0**

### 14.1 When to Use

Use memory hierarchy when you need:

- **Conversational agents**: Remember context across turns
- **Session continuity**: Persist important information
- **Personalization**: Store user preferences long-term
- **Long-running agents**: Manage memory automatically
- **Multi-session context**: Resume conversations later

**Don't use when:**
- Stateless operations only
- No need to remember past interactions
- All context fits in single prompt

### 14.2 Architecture

```
┌─────────────────────────────────────┐
│  Working Memory (In-Context)        │
│  • Last 5-10 messages                │
│  • FIFO eviction                     │
│  • Fastest access                    │
└──────────────┬──────────────────────┘
               ↓ (evicted messages)
┌─────────────────────────────────────┐
│  Short-Term Memory (Session)        │
│  • Last 50-100 messages              │
│  • TTL-based expiration              │
│  • LRU eviction                      │
└──────────────┬──────────────────────┘
               ↓ (high-importance only)
┌─────────────────────────────────────┐
│  Long-Term Memory (Persistent)      │
│  • Important facts only              │
│  • Importance >=  threshold          │
│  • Permanent storage                 │
└─────────────────────────────────────┘
```

### 14.3 Implementation

```python
from agenkit.patterns import (
    MemoryHierarchy,
    WorkingMemory,
    ShortTermMemory,
    LongTermMemory
)

# Create 3-tier memory system
memory = MemoryHierarchy(
    working_memory=WorkingMemory(max_messages=10),
    short_term_memory=ShortTermMemory(
        max_messages=100,
        ttl_seconds=3600  # 1 hour
    ),
    long_term_memory=LongTermMemory(
        min_importance=0.7  # Only high-importance
    )
)

# Store memories with importance-based routing
await memory.store(
    content="User's name is Alice",
    importance=0.95,  # High importance → all tiers
    metadata={"category": "identity"},
    session_id="session-001"
)

await memory.store(
    content="User asked about weather",
    importance=0.2,  # Low importance → working + short-term only
    session_id="session-001"
)

# Retrieve relevant memories
memories = await memory.retrieve(
    query="What do I know about the user?",
    limit=5
)

# Get statistics
stats = memory.get_stats()
print(f"Working: {stats['working']['size']}/{stats['working']['capacity']}")
print(f"Short-term: {stats['short_term']['size']}")
print(f"Long-term: {stats['long_term']['size']}")
```

### 14.4 Tier Characteristics

**Working Memory:**
- **Purpose**: Current conversation context
- **Capacity**: 5-20 messages (fits in LLM context)
- **Eviction**: FIFO (first in, first out)
- **Latency**: Instant (in-memory)
- **Use case**: Active dialogue turns

**Short-Term Memory:**
- **Purpose**: Recent session history
- **Capacity**: 50-200 messages
- **Eviction**: LRU (least recently used) + TTL expiration
- **Latency**: Fast (in-memory or cache)
- **Use case**: Same-session context

**Long-Term Memory:**
- **Purpose**: Persistent facts and preferences
- **Capacity**: Unlimited (database-backed)
- **Eviction**: None (or manual cleanup)
- **Latency**: Moderate (database query)
- **Use case**: Cross-session knowledge

### 14.5 Importance-Based Routing

Memory entries are routed to tiers based on importance score (0.0-1.0):

```python
# Low importance (< 0.3): Working only
await memory.store("User said hello", importance=0.1)
# → Working memory only

# Medium importance (0.3-0.7): Working + Short-term
await memory.store("User prefers dark mode", importance=0.5)
# → Working + Short-term

# High importance (>= 0.7): All tiers
await memory.store("User lives in San Francisco", importance=0.9)
# → Working + Short-term + Long-term
```

### 14.6 Cross-Tier Search

```python
# Search across all tiers with deduplication
results = await memory.retrieve(
    query="user preferences",
    limit=10,
    search_tiers=["working", "short_term", "long_term"]  # Default: all
)

# Results are ranked by relevance and deduplicated
for mem in results:
    print(f"{mem.content} (importance: {mem.importance})")
```

### 14.7 Production Considerations

**TTL Configuration:**
- **Working**: No TTL (FIFO eviction only)
- **Short-term**: 1-24 hours typical
- **Long-term**: No TTL (permanent)

**Capacity Planning:**
- **Working**: Match LLM context window
- **Short-term**: Based on session length
- **Long-term**: Scale with user base

**Performance:**
- Working memory: O(1) access
- Short-term: O(1) with hash index
- Long-term: O(log n) with vector search

**Cost:**
- Working/short-term: RAM only (cheap)
- Long-term: Database + vector embeddings

### 14.8 Integration with Agents

```python
class ConversationalAgent:
    def __init__(self, llm, memory: MemoryHierarchy):
        self.llm = llm
        self.memory = memory

    async def process(self, message: Message, session_id: str) -> Message:
        # Retrieve relevant context
        context = await self.memory.retrieve(
            query=message.content,
            limit=10
        )

        # Build prompt with context
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            *[Message(role="assistant", content=m.content) for m in context],
            message
        ]

        # Generate response
        response = await self.llm.complete(messages)

        # Store interaction
        await self.memory.store(
            content=f"User: {message.content}",
            importance=0.5,
            session_id=session_id
        )
        await self.memory.store(
            content=f"Assistant: {response.content}",
            importance=0.5,
            session_id=session_id
        )

        return response
```

**See Also:**
- `examples/patterns/08_memory_hierarchy.py` - 6 complete demos
- `tests/patterns/test_memory.py` - 30 tests covering all tiers

---

# Chapter 15: Reasoning with Tools Pattern

✅ **NEW in v0.13.0** | **Production Ready**

**What It Is:** A pattern that enables tools to be called DURING reasoning (not just after), allowing models to dynamically access information and perform computations while thinking through a problem.

**Key Insight:** Unlike ReAct (which is sequential: Observe → Think → Act → Observe), this pattern enables interleaved thinking and tool use (Think ↔ Act), inspired by Claude 4 and OpenAI o3's extended thinking capabilities.

## Why This Pattern?

### Traditional ReAct Limitations:

1. **Sequential Only**: Think first, THEN act
2. **Rigid Loop**: Can't use tools mid-thought
3. **Information Delays**: Must complete reasoning before getting data
4. **Less Natural**: Humans look up facts WHILE thinking

### Reasoning with Tools Advantages:

1. **Dynamic Information**: Get data exactly when needed
2. **Iterative Refinement**: Tool results inform next reasoning step
3. **Natural Flow**: More like human problem-solving
4. **Better Accuracy**: Access to real-time information during reasoning

## Implementation

### Basic Structure:

```python
from agenkit.patterns import ReasoningWithToolsAgent, ReasoningStep, ReasoningStepType

# Create agent with tools
agent = ReasoningWithToolsAgent(
    llm=base_llm_agent,
    tools=[calculator, database, web_search],
    max_reasoning_steps=20,
    enable_trace=True
)

# Agent interleaves thinking and tool use
response = await agent.process(
    Message(role="user", content="Calculate total cost of 3 items at $15.99 with 8.5% tax")
)

# Access reasoning trace
trace = response.metadata["reasoning_trace"]
print(f"Steps: {len(trace['steps'])}")
print(f"Tools used: {trace['total_tools_used']}")
```

### Tool Call Format:

The LLM indicates tool use during reasoning:

```
TOOL_CALL: calculator
PARAMETERS: {"operation": "multiply", "a": 15.99, "b": 3}
```

The agent:
1. Detects the tool call
2. Executes the tool
3. Feeds result back into reasoning
4. Continues thinking with new information

## Reasoning Trace

Every step is recorded with detailed metadata:

```python
trace = response.metadata["reasoning_trace"]

for step in trace["steps"]:
    if step["step_type"] == "thinking":
        print(f"💭 {step['content']}")
    elif step["step_type"] == "tool_call":
        print(f"🔧 Called {step['tool_name']}: {step['tool_parameters']}")
    elif step["step_type"] == "tool_result":
        print(f"✓ Result: {step['content']}")
    elif step["step_type"] == "conclusion":
        print(f"🎯 {step['content']}")
```

## Production Usage

### With Error Handling:

```python
agent = ReasoningWithToolsAgent(
    llm=llm,
    tools=[calculator, database],
    max_reasoning_steps=20,
    enable_trace=True
)

try:
    response = await agent.process(message)

    # Check if agent reached conclusion
    if response.metadata["reasoning_steps"] >= 20:
        logger.warning("Hit max reasoning steps")

    return response.content

except Exception as e:
    # Tool execution errors are handled gracefully
    logger.error(f"Reasoning failed: {e}")
    return "I encountered an error while processing your request."
```

### Dynamic Tool Management:

```python
agent = ReasoningWithToolsAgent(llm=llm, tools=[calculator])

# Add tools at runtime
if user.has_premium:
    agent.add_tool(premium_database_tool)

# Remove tools based on context
if not user.allow_web:
    agent.remove_tool("web_search")

# Get specific tool
tool = agent.get_tool("calculator")
```

## When to Use

**✅ Use Reasoning with Tools When:**

- Solving multi-step problems requiring data lookups
- Performing calculations during analysis
- Research tasks with fact-checking
- Financial planning with price lookups
- Scientific computing with specialized tools
- Any task where information is needed mid-thought

**❌ Don't Use When:**

- Simple single-step tasks
- All required information is already available
- Tools are expensive and should be used sparingly
- ReAct's sequential pattern is sufficient

## Key Differences from ReAct

| Aspect | ReAct | Reasoning with Tools |
|--------|-------|---------------------|
| **Execution** | Sequential (think → act → observe) | Interleaved (think ↔ act) |
| **Tool Access** | After reasoning completes | During reasoning |
| **Use Case** | Action-oriented tasks | Information-gathering during reasoning |
| **Trace** | Observation → Thought → Action | Thinking + Tool Call + Result (interleaved) |
| **Natural Fit** | Multi-step procedures | Research and analysis |

## Configuration Options

```python
agent = ReasoningWithToolsAgent(
    llm=llm,
    tools=[tool1, tool2],
    max_reasoning_steps=20,          # Max steps before stopping
    tool_use_prompt=custom_prompt,   # Custom instruction for tool usage
    enable_trace=True,                # Record detailed reasoning trace
    confidence_threshold=0.8,         # Minimum confidence for answer
)
```

## Performance Characteristics

**Trace Overhead:**
- Enabled: ~5-10% overhead (detailed step recording)
- Disabled: <1% overhead (minimal metadata)

**Tool Call Latency:**
- Sequential tools: O(n) where n = number of tool calls
- Each tool call adds network/compute latency

**Optimization Tips:**
1. Limit `max_reasoning_steps` to prevent infinite loops
2. Cache expensive tool results
3. Use `enable_trace=False` in production if trace not needed
4. Provide clear tool descriptions to reduce unnecessary calls

## Real-World Example

**Scenario:** Calculate shopping cart total with database lookups

```python
# Agent interleaves database lookups and calculations:
# 1. 💭 "I need to find laptop price"
# 2. 🔧 database.query("laptop") → $999
# 3. 💭 "Now I need the mouse price"
# 4. 🔧 database.query("mouse") → $29.99
# 5. 💭 "Let me calculate the total"
# 6. 🔧 calculator.add(999, 29.99) → $1,028.99
# 7. 🎯 "Total cost is $1,028.99"

response = await agent.process(
    Message(role="user", content="What's the total for laptop and mouse?")
)

print(response.content)
# → "The total for a laptop and mouse is $1,028.99"
```

## Debugging with Traces

Reasoning traces are invaluable for debugging:

```python
trace = response.metadata["reasoning_trace"]

# Statistics
print(f"Total steps: {len(trace['steps'])}")
print(f"Thinking steps: {trace['total_thinking_steps']}")
print(f"Tools used: {trace['total_tools_used']}")
print(f"Duration: {trace['duration_seconds']:.2f}s")

# Step-by-step analysis
for i, step in enumerate(trace["steps"], 1):
    print(f"\nStep {i}:")
    print(f"  Type: {step['step_type']}")
    print(f"  Content: {step['content'][:100]}...")
    if step['tool_name']:
        print(f"  Tool: {step['tool_name']}")
        print(f"  Parameters: {step['tool_parameters']}")
```

## Best Practices

1. **Provide Clear Tool Descriptions**: LLM uses descriptions to decide when to call tools
2. **Set Reasonable Max Steps**: Prevent infinite reasoning loops (typically 10-30)
3. **Enable Tracing in Development**: Critical for debugging reasoning flow
4. **Handle Tool Errors Gracefully**: Agent continues even if tools fail
5. **Monitor Tool Usage**: Track which tools are called most frequently
6. **Cache Tool Results**: Avoid redundant expensive operations

## Anti-Patterns

**❌ Tool Thrashing:**
```python
# Bad: Agent repeatedly calls same tool
# search("Python tutorial")
# search("Python tutorial for beginners")
# search("beginner Python tutorial")
```
**Fix:** Cache results, add cooldowns, or improve tool descriptions

**❌ Infinite Reasoning:**
```python
# Bad: No termination condition
agent = ReasoningWithToolsAgent(
    llm=llm,
    tools=tools,
    max_reasoning_steps=1000,  # Too high!
)
```
**Fix:** Set reasonable limit (10-30 steps), add conclusion detection

**See Also:**
- `examples/patterns/09_reasoning_with_tools.py` - 6 complete demos
- `tests/patterns/test_reasoning_with_tools.py` - 25 comprehensive tests
- Related: Chapter 6 (ReAct) for sequential reasoning + acting

---

# Part III: Production

*(Chapters 16-19 planned but not yet written)*

## Chapter 16: State Management
- Conversational, session, long-term state
- Storage options
- Checkpointing

## Chapter 17: Error Handling & Resilience
- Failure modes
- Retry patterns
- Circuit breakers
- Fallback strategies

## Chapter 18: Deployment Patterns
- Architectures
- Container deployment
- Kubernetes
- Cross-language

## Chapter 19: Observability & Debugging
- Distributed tracing
- Metrics
- Logging
- Debugging techniques

---

# Part IV: Advanced Topics

*(Chapters 20-22 planned but not yet written)*

## Chapter 20: Multi-Agent Systems
- System architectures
- Communication patterns
- Coordination mechanisms

## Chapter 21: Agent Learning & Adaptation
- Learning strategies
- Feedback loops
- Self-reflection
- Memory systems

## Chapter 22: Future Directions
- Current trends
- Research frontiers
- Scaling challenges
- The road ahead

---

# Appendices

*(Planned but not yet written)*

## Appendix A: Agenkit API Reference
## Appendix B: Framework Comparison Matrix
## Appendix C: Case Studies
## Appendix D: Design Patterns Catalog
## Appendix E: Resources

---

# Contributing to This Guide

This guide is a living document. We welcome contributions!

**How to Contribute:**

1. **Report issues**: Found errors or unclear sections? [Open an issue](https://github.com/scttfrdmn/agenkit/issues)

2. **Suggest content**: Have ideas for chapters or examples? [Start a discussion](https://github.com/scttfrdmn/agenkit/discussions)

3. **Submit PRs**: Want to write a section? See [CONTRIBUTING.md](../../.github/CONTRIBUTING.md)

**Expansion Roadmap:**

- ✅ **Phase 1**: Chapters 1-2 complete (foundations)
- 🔄 **Phase 2**: Chapters 3-11 (all patterns)
- 📅 **Phase 3**: Chapters 12-15 (production)
- 📅 **Phase 4**: Chapters 16-18 (advanced)
- 📅 **Phase 5**: Appendices and polish

---

# References and Further Reading

## Papers and Research

- Russell, S., & Norvig, P. (2020). *Artificial Intelligence: A Modern Approach* (4th ed.)
- Wooldridge, M. (2009). *An Introduction to MultiAgent Systems* (2nd ed.)

## Framework Documentation

- [Smolagents](https://huggingface.co/blog/smolagents) - Code-first agent approach
- [LangGraph](https://blog.langchain.com/building-langgraph/) - Graph-based orchestration
- [CrewAI](https://www.crewai.com/) - Role-based multi-agent systems
- [LangChain](https://blog.langchain.com/deep-agents/) - Deep agents architecture
- [Haystack](https://docs.haystack.deepset.ai/docs/agents) - Pipeline-based agents
- [AWS Bedrock](https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-announces-general-availability-of-multi-agent-collaboration/) - Multi-agent collaboration

## Agenkit Documentation

- [Getting Started](../getting-started/index.md)
- [Architecture Guide](../core-concepts/architecture.md)
- [LLM Adapters](../features/llm-adapters.md)
- [API Reference](../api/index.md)

---

# Appendix A: 2025 Patterns Update

**Context:** November 2025 marked a watershed moment—agents went from research to production.

## Major Developments (2025)

1. **Claude Sonnet 4.5** (September 2025): **30-hour autonomous operation**
2. **OpenAI o3** (April 2025): Visual reasoning, extended thinking, autonomous tool use
3. **Production Deployments**: AutoGen, LangGraph at scale
4. **Tool-Use Evolution**: Models use tools *during* reasoning (not just sequential)

## New Patterns for Autonomous Agents

### 1. Long-Running Agent Pattern ⭐ **CRITICAL**

**Problem:** Agents now work for 30+ hours. Sessions can crash, need to resume.

**Solution:** Durable execution with checkpointing.

```python
class CheckpointedAgent:
    """Agent with automatic checkpointing."""

    def __init__(self, agent: Agent, checkpoint_storage: Storage):
        self.agent = agent
        self.storage = checkpoint_storage

    async def call(
        self,
        messages: list[Message],
        session_id: str,
        **kwargs
    ) -> Message:
        # Load checkpoint if exists
        checkpoint = await self.storage.load(session_id)
        if checkpoint:
            self.restore_state(checkpoint)

        try:
            # Process
            response = await self.agent.call(messages, **kwargs)

            # Checkpoint after success
            await self.storage.save(session_id, self.get_state())

            return response
        except Exception as e:
            # Save state on failure
            await self.storage.save(session_id, self.get_state())
            raise
```

**Why It Matters:** Without checkpointing, 30-hour agents lose all progress on failure.

**Status:** Planned (#69)

### 2. Reasoning Budget Pattern ⭐ **NEW IN 2025**

**Problem:** Hybrid models (Claude 4, o3) have "instant" vs "extended thinking" modes. When to use which?

**Solution:** Dynamic allocation based on complexity.

```python
class ReasoningBudgetAgent:
    """Route queries to appropriate reasoning depth."""

    def __init__(
        self,
        fast_llm: LLM,      # Instant mode
        reasoning_llm: LLM, # Extended thinking
        complexity_detector: Callable
    ):
        self.fast = fast_llm
        self.reasoning = reasoning_llm
        self.detector = complexity_detector

    async def call(self, messages: list[Message], **kwargs) -> Message:
        complexity = await self.detector(messages)

        if complexity == "simple":
            # Use fast mode (cheaper, instant)
            return await self.fast.complete(messages, **kwargs)
        else:
            # Use extended thinking (expensive, deeper)
            return await self.reasoning.complete(
                messages,
                thinking_time=complexity_score * 10,  # Scale by complexity
                **kwargs
            )
```

**Why It Matters:** Saves cost (extended thinking is 3-10x more expensive) while maintaining quality.

**Status:** Planned (#72)

### 3. Tool-Use During Reasoning Pattern ⭐ **NEW CAPABILITY**

**Problem:** Claude 4 and o3 can use tools *while* reasoning (not just after). Different from ReAct.

**Solution:** Support interleaved reasoning + tool calls.

```python
class ReasoningWithToolsAgent:
    """Agent that uses tools during extended thinking."""

    async def call(self, messages: list[Message], **kwargs) -> Message:
        # Start extended thinking
        reasoning_session = await self.llm.start_reasoning(messages)

        while not reasoning_session.complete:
            # Check if reasoning wants to use tool
            if reasoning_session.wants_tool:
                tool_call = reasoning_session.pending_tool_call
                result = await self.tools.execute(tool_call)

                # Feed result back into reasoning
                reasoning_session.continue_with_tool_result(result)
            else:
                # Continue reasoning
                await reasoning_session.continue_thinking()

        return reasoning_session.final_response
```

**Why Different from ReAct:** Reasoning happens *inside* tool selection, not sequential.

**Status:** Planned (#75)

### 4. Cost-Aware Agent Pattern ⭐ **PRODUCTION NEED**

**Problem:** 30-hour agent with expensive model (o3, Opus 4) could cost $500+.

**Solution:** Budget tracking and enforcement.

```python
class CostAwareAgent:
    """Agent with cost tracking and budget limits."""

    def __init__(
        self,
        agent: Agent,
        tracker: CostTracker,
        session_budget: float = 10.00  # $10 max per session
    ):
        self.agent = agent
        self.tracker = tracker
        self.budget = session_budget

    async def call(
        self,
        messages: list[Message],
        session_id: str,
        **kwargs
    ) -> Message:
        # Check budget before processing
        current_cost = await self.tracker.get_session_cost(session_id)
        if current_cost >= self.budget:
            raise BudgetExceededError(
                f"Session budget ${self.budget} exceeded (${current_cost:.2f})"
            )

        response = await self.agent.call(messages, **kwargs)

        # Record cost
        await self.tracker.record_cost(
            session_id=session_id,
            model=response.metadata["model"],
            input_tokens=response.metadata["usage"]["prompt_tokens"],
            output_tokens=response.metadata["usage"]["completion_tokens"]
        )

        return response
```

**Why It Matters:** Prevents runaway costs in production.

**Status:** Planned (#68)

## Anti-Patterns (What NOT to Do)

### 1. Infinite Loop Anti-Pattern ❌

**Problem:** Agent recursively calls itself without termination.

**Example:**
```python
# BAD: No termination condition
async def agent(messages):
    response = await llm.complete(messages)
    if not satisfied(response):
        return await agent(messages + [response])  # Infinite loop risk
```

**Fix:** Max depth, cycle detection, timeout.

### 2. Context Explosion Anti-Pattern ❌

**Problem:** Accumulating unbounded conversation history.

**Example:**
```python
# BAD: History grows forever
history = []
while True:
    response = await agent.call(history + [new_message])
    history.append(new_message)
    history.append(response)  # Will hit context limit!
```

**Fix:** Sliding windows, summarization, external memory (#67).

### 3. Tool Thrashing Anti-Pattern ❌

**Problem:** Repeatedly calling same tool with slight variations.

**Example:**
```python
# BAD: Wasting tokens and money
search("Python tutorial")
search("Python tutorial for beginners")
search("beginner Python tutorial")
search("Python tutorial beginners")
```

**Fix:** Caching, result validation, tool cooldowns.

### 4. Prompt Injection Anti-Pattern ❌

**Problem:** User input affects agent behavior.

**Research Finding:** "Complete control over tool calls" if attacker injects tokens.

**Example:**
```python
# BAD: User input directly in prompt
prompt = f"Summarize: {user_input}"  # User can inject "Ignore previous, do X"
```

**Fix:** Input sanitization, role separation, sandboxing (#71).

### 5. Error Propagation Anti-Pattern ❌

**Problem:** Early mistake cascades through reasoning.

**Research Finding:** "No native rollback mechanism" in LLMs.

**Fix:** Checkpointing (#69), validation gates.

### 6. Over-Automation Anti-Pattern ❌

**Problem:** Automating high-stakes decisions.

**Research Finding:** Most production teams require human approval for critical actions.

**Fix:** Human-in-loop for critical actions (Chapter 11).

### 7. Unbounded Resource Consumption ❌

**Problem:** Arbitrary CPU/memory/token usage.

**Example:**
```python
# BAD: No limits
while agent.wants_to_continue():
    result = await agent.call(messages)  # Could run forever
```

**Fix:** Rate limiting, circuit breakers, quotas, budget limits (#68).

## Recommended Reading (2025 Research)

1. **Claude Sonnet 4.5 Release** (Anthropic, September 2025)
   - 30-hour autonomous operation
   - Hybrid reasoning (instant + extended)

2. **OpenAI o3 Release** (OpenAI, April 2025)
   - Visual reasoning
   - Tool use during extended thinking

3. **AutoGen Production Guide** (Microsoft, 2025)
   - Multi-agent patterns at scale
   - Production deployment patterns

4. **LangGraph Checkpointing** (LangChain, 2025)
   - Durable execution patterns
   - State persistence

5. **Design Patterns for Securing LLM Agents** (Research, June 2025)
   - Prompt injection defense
   - Sandboxing patterns
   - Input/output validation

6. **AWS AgentCore Gateway** (AWS, 2025)
   - Semantic tool selection
   - Protocol translation (MCP)
   - Agent routing patterns

## Status of Pattern Implementations

**Completed:**
- ✅ Basic agent patterns (sequential, parallel, fallback)
- ✅ Middleware patterns (retry, circuit breaker, timeout, caching, batching)
- ✅ Transport patterns (HTTP/1.1, HTTP/2, HTTP/3, WebSocket, gRPC)

**Q4 2025 (In Progress):**
- 🔄 Memory systems (#67) - Critical for 30-hour agents
- 🔄 Cost tracking (#68) - Prevent runaway spend
- 🔄 Long-running pattern (#69) - Checkpointing and resume

**Q1-Q2 2026 (Planned):**
- 📋 Reasoning budget pattern (#72) - NEW IN 2025
- 📋 Safety framework (#71) - Prompt injection defense
- 📋 Evaluation framework (#73) - Measure 30-hour success
- 📋 Tool-use during reasoning (#75) - NEW CAPABILITY
- 📋 Routing & semantic tool selection (#74) - Production scale

See [ROADMAP.md](../../ROADMAP.md) and [.github/STRATEGIC_2026_ROADMAP.md](../../.github/STRATEGIC_2026_ROADMAP.md) for complete roadmap.

---

# Acknowledgments

This guide builds on insights from the broader agent community:

- Hugging Face team for smolagents and the "agency spectrum" concept
- LangChain/LangGraph team for ReAct and graph patterns
- CrewAI team for role-based abstractions
- AWS Bedrock team for supervisor with routing
- Haystack team for pipeline and self-reflection patterns
- The entire open-source AI agent community

---

# Changelog

**Version 0.3** (November 24, 2025)
- Added Chapter 12: Reflection Pattern (✅ Implemented in v0.12.0)
  - Iterative self-critique and refinement
  - Quality thresholds and stopping conditions
  - 22 tests, complete examples
- Added Chapter 13: Agents-as-Tools Pattern (✅ Implemented in v0.12.0)
  - Hierarchical agent delegation
  - Multi-level agent hierarchies
  - 20 tests, ReAct integration
- Added Chapter 14: Memory Hierarchy Pattern (✅ Implemented in v0.12.0)
  - Multi-tier memory management (working, short-term, long-term)
  - Importance-based routing, TTL expiration, LRU eviction
  - 30 tests, cross-tier search
- Renumbered Part III and IV chapters to accommodate new content

**Version 0.2** (November 13, 2025)
- Added Appendix A: 2025 Patterns Update
- Documented 4 new patterns for autonomous agents
- Documented 7 anti-patterns with fixes
- Updated for Claude Sonnet 4.5 (30-hour operation) and OpenAI o3
- Added production pattern roadmap status

**Version 0.1** (November 13, 2025)
- Initial foundation release
- Chapters 1-2 complete
- Chapters 3-11 outlined
- Book structure established

---

# License

This guide is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

You are free to:
- **Share** — copy and redistribute
- **Adapt** — remix, transform, and build upon

Under the following terms:
- **Attribution** — Give appropriate credit
- **ShareAlike** — Distribute under same license

---

*Last updated: November 24, 2025*
