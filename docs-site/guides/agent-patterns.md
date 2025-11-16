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

### Part III: Production *(planned)*
- Chapter 12: State Management
- Chapter 13: Error Handling & Resilience
- Chapter 14: Deployment Patterns
- Chapter 15: Observability & Debugging

### Part IV: Advanced Topics *(planned)*
- Chapter 16: Multi-Agent Systems
- Chapter 17: Agent Learning & Adaptation
- Chapter 18: Future Directions

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

# Part III: Production

*(Chapters 12-15 planned but not yet written)*

## Chapter 12: State Management
- Conversational, session, long-term state
- Storage options
- Checkpointing

## Chapter 13: Error Handling & Resilience
- Failure modes
- Retry patterns
- Circuit breakers
- Fallback strategies

## Chapter 14: Deployment Patterns
- Architectures
- Container deployment
- Kubernetes
- Cross-language

## Chapter 15: Observability & Debugging
- Distributed tracing
- Metrics
- Logging
- Debugging techniques

---

# Part IV: Advanced Topics

*(Chapters 16-18 planned but not yet written)*

## Chapter 16: Multi-Agent Systems
- System architectures
- Communication patterns
- Coordination mechanisms

## Chapter 17: Agent Learning & Adaptation
- Learning strategies
- Feedback loops
- Self-reflection
- Memory systems

## Chapter 18: Future Directions
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

*Last updated: November 13, 2025*
