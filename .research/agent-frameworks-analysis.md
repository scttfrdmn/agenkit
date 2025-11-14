# Agent Framework Landscape Analysis
*Research Date: November 13, 2025*

## Executive Summary

This document analyzes leading agent frameworks and contribution models to inform Agenkit's Agent Patterns Guide (#61) and community structure.

---

## Agent Framework Patterns

### 1. Hugging Face Smolagents 🔥

**Philosophy**: "Agents are programs where LLM outputs control the workflow"

**Key Innovations**:
- **Code-First Actions**: Agents generate executable Python code instead of JSON
  - Research shows superior composability and object management
  - Leverages LLM training on programming languages
  - Better for complex, nested operations
- **Minimal Abstractions**: ~thousands of lines of code
- **Agency as Spectrum**: Not binary—ranges from simple output processing to multi-step autonomous systems
- **Hub Integration**: Share and load tools/agents from Hugging Face Hub

**Architecture**:
```
Multi-step loop:
1. Maintain memory log of original task
2. Iterate: generate next action → execute → record observations
3. Continue until LLM determines completion
```

**Tool Pattern**:
```python
@tool
def my_tool(input: str) -> str:
    """Clear docstring describing the tool."""
    return result
```

**Why It's Interesting**:
- Challenges JSON tool calling orthodoxy
- Embraces code generation as primary interface
- Extremely simple mental model
- Leverages existing LLM strengths (code)

---

### 2. AWS Bedrock Multi-Agent (GA March 2025)

**Philosophy**: Specialized agents coordinated by supervisor

**Key Patterns**:

1. **Supervisor Mode**
   - Central supervisor agent orchestrates multiple specialist sub-agents
   - Breaks down complex tasks
   - Assigns tasks to domain specialists
   - Parallel execution with coordination

2. **Supervisor with Routing Mode**
   - Optimized for mixed complexity
   - Simple queries → direct routing to specialist
   - Complex queries → supervisor mode with full orchestration
   - Automatic mode switching

**Key Features (GA)**:
- **Inline Agents**: Dynamically adjust roles/behaviors at runtime
- **Payload Referencing**: Reference linked data instead of embedding (efficiency)
- **IaC Support**: CloudFormation and CDK for agent networks as code

**Integration**:
- Works with LangGraph and CrewAI
- Enterprise-grade with AWS infrastructure

**Why It's Interesting**:
- Production-ready, managed service
- Adaptive routing intelligence
- Runtime reconfiguration (inline agents)
- Enterprise adoption path

---

### 3. LangGraph (LangChain)

**Philosophy**: Agents as state machines with explicit control flow

**Core Concept**: Structured agents = graphs of states and nodes
- State (usually message history) flows through nodes
- Nodes = functions or LLM calls
- Edges = conditional logic

**Multi-Agent Patterns**:

1. **Supervisor Architecture**
   - One orchestrator agent + multiple sub-agents
   - LLM-based reasoning for delegation
   - Collects sub-agent outputs
   - Decides next action or final output

2. **Pipeline (Sequential)**
   - Document extraction → classification → summarization
   - Dependable but limited scaling
   - Clear linear flow

3. **Hub-and-Spoke**
   - Central coordinator dispatches tasks
   - Radial communication pattern

4. **Scatter-Gather (Parallel)**
   - Break work into sections
   - Multiple agents process simultaneously
   - Merge results
   - Better scaling than sequential

5. **Fan-Out / Fan-In**
   - Single node triggers multiple downstream nodes
   - Multiple nodes converge on single target
   - Complex coordination with clarity

**Production Features**:
- Parallelization
- Streaming
- Checkpointing (durability)
- Human-in-the-loop
- Tracing
- Task queue
- State persistence across nodes
- Dynamic decision-making (retry, revisit)

**Design Philosophy**: "Little to no abstraction"—focus on control and durability

**Adoption**: LinkedIn, Uber, Klarna (production)

**Why It's Interesting**:
- Most flexible control flow
- Explicit state management
- Production-proven at scale
- Graph mental model fits complex workflows

---

### 4. CrewAI

**Philosophy**: Role-based collaborative agents

**Core Architecture**:
- **Agent**: LLM-powered unit with name, role, goal
- **Task**: Specific job requiring completion

**Dual System (2025)**:

1. **Crews**: Autonomous agent groups
   - Collaborate on loosely defined tasks
   - High-level orchestration
   - Agent intelligence drives coordination

2. **Flows**: Structured workflows
   - Event-driven
   - Granular control
   - Precise task execution

**Design Patterns**:

1. **Coordinator-Worker**
   - Main planner breaks tasks into subtasks
   - Specialized agents execute
   - Structured orchestration

2. **Collaborative Peer Group**
   - Agents share outputs iteratively
   - Refine each other's results
   - Emergent intelligence

3. **Hybrid Planner-Executor**
   - Planning + execution + feedback loops
   - Adaptability built-in

**Architecture Advantage**:
- Built from scratch (not LangChain-dependent)
- Lightning-fast
- High-level simplicity + low-level control

**Adoption**: 30.5K GitHub stars, 1M monthly downloads

**Why It's Interesting**:
- Role-based abstraction is intuitive
- Dual Crews/Flows system balances autonomy and control
- Fastest-growing framework (2025)
- Simple mental model for teams

---

### 5. LangChain

**Philosophy**: Modular, chainable components for LLM applications

**Core Architecture** (2025):
- Layered system: planning, execution, communication, evaluation
- Agents as modular functions with memory, toolset, autonomy
- **Recommendation**: Use LangGraph for new implementations

**Key Agent Patterns**:

1. **ReAct Pattern** (Reasoning and Acting)
   - Foundation of modern LangChain agents
   - Chain-of-thought reasoning + action taking through tools
   - Autonomous complex problem solving

2. **Planner-Executor Model**
   - **Planner Agent**: Strategic brain, breaks goals into subtasks
   - **Executor Agents**: Carry out specific subtasks
   - Clear separation of concerns

3. **Deep Agents Architecture**
   - Planning tool
   - Sub-agents for delegation
   - File system access
   - Detailed prompting
   - Powers applications like "Deep Research", "Manus", "Claude Code"

**LangGraph Orchestration Patterns**:
- **Supervisor**: Routes tasks to specialized workers
- **Peer-to-Peer**: Agents share info, collaborate autonomously
- **Pipeline**: Sequential execution, each processes previous output

**Enterprise Integration**:
- Built-in connectors for CRM/ERP, databases, cloud APIs
- Enterprise plugins: Snowflake, Databricks, SAP, Salesforce, ServiceNow
- Production-grade for autonomous agent deployments

**Evolution**:
- Originally: Simple chains of LLM calls
- 2025: Full multi-agent orchestration framework
- Split into LangChain (library) and LangGraph (orchestration)

**Why It's Interesting**:
- Most mature ecosystem (longest history)
- Enterprise integration depth
- ReAct pattern widely adopted
- Split into library vs orchestration shows evolution

---

### 6. Haystack

**Philosophy**: Pipeline-based, modular RAG-first framework

**Core Architecture**:
- Components + Pipelines
- Branching and looping for complex workflows
- Originally RAG-focused, now full agentic AI

**Key Architectural Patterns**:

1. **Tool-Driven Agent Architecture**
   - Tools as individual modules for specific tasks
   - Three creation methods:
     - `Tool` class
     - `ComponentTool` class
     - `@tool` decorator
   - Modular, composable

2. **Pipeline-Based Workflows**
   - Routers enable dynamic decision-making
   - Conditional routing with fallbacks
   - Example: web search fallback when LLM lacks context

3. **Agentic RAG Systems**
   - More intelligent than traditional RAG
   - Context-aware routing
   - Key pattern for 2025 applications

4. **Self-Reflecting Agents**
   - Pipelines can loop using output validators
   - Quality control built-in
   - Iterative refinement

5. **Multi-Agent Swarms**
   - Tool calling for agent control exchange
   - Routines and handoffs
   - Dynamic agent coordination

**Framework Characteristics**:
- Full visibility: inspect, debug, optimize
- Modular: clear component boundaries
- RAG heritage: excellent for retrieval-augmented generation
- MCP tools integration

**Use Cases**:
- Agentic pipelines with function calling
- Advanced RAG with retrieval strategies
- Question answering systems
- Conversational agent chatbots

**Why It's Interesting**:
- RAG-native architecture (unique strength)
- Pipeline mental model different from graphs
- Self-reflection pattern built-in
- Validator-based quality control

---

## Comparative Analysis

| Framework | Mental Model | Complexity | Control | Best For |
|-----------|-------------|------------|---------|----------|
| **Smolagents** | Code generation | Minimal | Medium | Simple agents, code-first workflows |
| **Bedrock** | Supervisor + routing | Low | High | Enterprise, managed service |
| **LangGraph** | State machine graph | High | Very High | Complex workflows, production scale |
| **CrewAI** | Role-based teams | Medium | High | Team-oriented tasks, business logic |
| **LangChain** | Modular chains | Medium | High | Enterprise integration, mature ecosystem |
| **Haystack** | Pipeline + RAG | Medium | High | RAG-first, question answering, search |
| **Agenkit** | Minimal interface | Minimal | Very High | Cross-language, transport-agnostic |

---

## Key Insights for Agenkit

### 1. Agency is a Spectrum
- Not binary (is/isn't an agent)
- Ranges from output processing to full autonomy
- Agenkit should acknowledge this spectrum

### 2. Multiple Valid Patterns
- **Code-first** (Smolagents): Let LLM write Python
- **Supervisor** (Bedrock, LangGraph): Central coordinator
- **Role-based** (CrewAI): Define by function
- **Graph-based** (LangGraph): Explicit state machines
- **Minimal** (Agenkit): Transport + Message interface

### 3. Control vs Abstraction Tradeoff
- Smolagents: Minimal abstraction
- LangGraph: "Little to no abstraction"
- Agenkit: Minimal interface, maximum control
- Trend: Less abstraction, more explicit control

### 4. State Management is Critical
- LangGraph's explicit state persistence
- CrewAI's context sharing
- Agenkit's Message-based state

### 5. Production Needs
- Checkpointing/durability (LangGraph)
- Human-in-the-loop (LangGraph, CrewAI)
- Runtime reconfiguration (Bedrock inline agents)
- Observability (Agenkit's strength)

---

## Recommendations for Agent Patterns Guide

### Structure Proposal

1. **Philosophy: What is an Agent?**
   - Agency as spectrum (borrowing from Smolagents)
   - LLM output controls workflow
   - Distinction from tools and tasks

2. **The Agenkit Approach**
   - Minimal interface: `Agent.call(messages) -> Message`
   - Transport-agnostic
   - Cross-language by default
   - Composable via middleware and patterns

3. **Pattern Catalog** (inspired by all frameworks)
   - **Single Agent**: Simplest case
   - **Sequential** (Pipeline): Task → Task → Task
   - **Parallel** (Scatter-Gather): Concurrent processing
   - **Supervisor**: Central coordinator + specialists
   - **Peer Collaboration**: Iterative refinement
   - **Router**: Conditional delegation
   - **Human-in-Loop**: Pause for approval

4. **When to Use What**
   - Decision tree based on:
     - Task complexity
     - Need for coordination
     - Latency requirements
     - Failure handling
     - State management needs

5. **Agent vs Task vs Tool**
   - **Agent**: Stateful, conversational, autonomous
   - **Task**: One-shot, ephemeral, cleanup
   - **Tool**: Deterministic function, no LLM

6. **Implementation Examples**
   - Code-first pattern (Smolagents inspiration)
   - Graph-based pattern (LangGraph inspiration)
   - Role-based pattern (CrewAI inspiration)
   - Supervisor pattern (Bedrock/LangGraph)
   - All using Agenkit's minimal interface

7. **Production Considerations**
   - State persistence
   - Error handling
   - Observability (Agenkit's strength)
   - Deployment patterns

8. **Case Studies**
   - Real-world examples
   - Why pattern X was chosen
   - Lessons learned

---

## GitHub gh CLI Contribution Model

**Structure**:
```
CONTRIBUTING.md
├── Introduction (welcoming)
├── Please do: (encouraged)
├── Please do not: (discouraged)
├── Building the project
├── Submitting a pull request
├── Design guidelines
└── Resources
```

**Key Elements**:

1. **Clear Expectations**
   - Explicit "do" and "do not" lists
   - No ambiguity about what's accepted

2. **Issue Labels System**
   - `help wanted`: Community contributions welcome
   - `good first issue`: Beginner-friendly
   - `core`: Reserved for maintainers (DO NOT PR)

3. **Acceptance Criteria Required**
   - No PRs without clear AC in issue
   - Mention `@cli/code-reviewers` for clarification

4. **Tone**
   - Welcoming: "Hi! Thanks for your interest..."
   - Professional but friendly
   - Structured and clear

5. **Scope Management**
   - No expanding PR scope beyond issue
   - One issue = one PR
   - Prevents scope creep

**Recommendations for Agenkit**:
- Adopt similar structure
- Create label system (help-wanted, good-first-issue, core)
- Require acceptance criteria before PRs
- Welcoming but clear tone
- Add sections for:
  - Cross-language contributions (Python + Go)
  - Testing requirements (both languages)
  - Documentation expectations

---

## Next Steps

### For Agent Patterns Guide (#61):
1. Create comprehensive guide using insights from all frameworks
2. Position Agenkit's minimal approach in context
3. Show how to implement patterns from other frameworks using Agenkit
4. Include decision trees and when-to-use guidance

### For Community/Contributing:
1. Create `CONTRIBUTING.md` following gh CLI model
2. Set up issue label system
3. Create issue templates with acceptance criteria
4. Write Code of Conduct
5. Create PR template

---

## References

- [Smolagents Blog Post](https://huggingface.co/blog/smolagents)
- [AWS Bedrock Multi-Agent (GA)](https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-announces-general-availability-of-multi-agent-collaboration/)
- [LangGraph Architecture](https://blog.langchain.com/building-langgraph/)
- [CrewAI Framework](https://www.crewai.com/)
- [LangChain Multi-Agent AI 2025](https://blogs.infoservices.com/artificial-intelligence/langchain-multi-agent-ai-framework-2025/)
- [LangChain Deep Agents](https://blog.langchain.com/deep-agents/)
- [Haystack AI Documentation](https://docs.haystack.deepset.ai/docs/agents)
- [Haystack Agents Tutorial](https://www.datacamp.com/tutorial/haystack-ai-tutorial)
- [GitHub gh CLI Contributing](https://github.com/cli/cli/blob/trunk/.github/CONTRIBUTING.md)

---

*End of Analysis*
