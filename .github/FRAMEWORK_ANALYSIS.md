# Agent Framework Analysis: Primitives, Patterns, and Architecture

**Date**: November 30, 2025
**Purpose**: Analyze major agent frameworks to identify primitives, patterns, and architectural innovations relevant to Agenkit
**Context**: Evaluate AWS Strands, Hugging Face smolagents, OpenAI Swarm/Agents SDK, and others for novel patterns or meta-patterns

---

## Executive Summary

After analyzing major production frameworks, we've identified:

**🔑 Common Primitives**: All frameworks converge on 3-4 core primitives (routines, handoffs, tools, context)

**📐 Architectural Innovation**: Frameworks differ primarily in **orchestration philosophy** (graph-based, conversation-based, role-based, code-first) rather than fundamental coordination patterns

**✅ Agenkit Position**: Agenkit's patterns map well to framework primitives - no fundamental gaps, but opportunities for enhanced ergonomics and meta-pattern documentation

**🎯 Key Finding**: "Handoffs" are the universal primitive across all frameworks - Agenkit's Agents-as-Tools + Orchestration cover this, but should be made more explicit

---

## Framework Landscape (2025)

### Production Frameworks Analyzed

| Framework | Maintainer | Philosophy | Launch/Status |
|-----------|-----------|------------|--------------|
| **Strands** | AWS | Model-driven, 4 primitives | v1.0 (2025), Production |
| **smolagents** | Hugging Face | Code-first, minimal | 2025, 3.9K stars/week |
| **Swarm** → **Agents SDK** | OpenAI | Handoffs + Routines | Experimental → Production |
| **LangGraph** | LangChain | Graph-based FSM | Production, mature |
| **AutoGen** | Microsoft | Conversation-based | Production, research-grade |
| **CrewAI** | Independent | Role-based orchestration | Production, popular |

---

## Universal Primitives (Cross-Framework Analysis)

### 1. **Routines** (Instructions/Prompts)

**What**: Predefined instructions that define agent behavior, role, and goals

**Implementations**:
- **Strands**: System prompts with role definitions
- **OpenAI Swarm/SDK**: `instructions` parameter in agent definition
- **LangGraph**: Node-level prompts
- **CrewAI**: Agent role definitions ("Planner", "Researcher", "Writer")
- **AutoGen**: System messages in conversation

**Agenkit Equivalent**:
- Built into Agent interface (agents define their own behavior)
- Message role system (system, user, assistant)

**Gap**: No first-class "routine" abstraction - users must implement in agent subclasses

**Recommendation**: Consider adding `AgentRoutine` or `AgentRole` abstraction for common patterns

---

### 2. **Handoffs** (Delegation/Transfer)

**What**: Transferring control/context from one agent to another

**Implementations**:
- **Strands**: Agent-to-Agent (A2A) protocol primitive
- **OpenAI Swarm**: Handoff tools that return new agent to continue conversation
- **LangGraph**: Graph edges with conditional routing
- **Google ADK**: Coordinator routing to sub-agents
- **All frameworks**: Treat handoffs as specialized tools

**Key Quote** ([Skywork AI](https://skywork.ai/blog/ai-agent-orchestration-best-practices-handoffs/)):
> "Reliability lives and dies in the handoffs. Most 'agent failures' are actually orchestration and context-transfer issues."

**Agenkit Equivalent**:
- **Agents-as-Tools** pattern (agents call other agents as tools)
- **Orchestration** pattern (sequential/parallel delegation)
- **Multiagent** pattern (coordination among agents)

**Gap**: Handoffs not explicitly modeled as first-class primitive with:
- Context preservation guarantees
- Versioned handoff schemas
- Explicit return/resume mechanisms

**Recommendation**: Add `Handoff` primitive or enhance Agents-as-Tools with explicit handoff semantics

---

### 3. **Tools** (Functions/Actions)

**What**: External functions/APIs that agents can invoke

**Implementations**:
- **Strands**: Python tools, MCP servers, LangChain tools
- **smolagents**: Generates Python code to call tools
- **All frameworks**: Function calling via OpenAI-style tool schemas

**Agenkit Equivalent**:
- Agents have tools as part of their capabilities
- **Reasoning with Tools** pattern for advanced usage

**Status**: ✅ Well covered

---

### 4. **Context/State Management**

**What**: Managing conversation history, state, and memory across interactions

**Implementations**:
- **LangGraph**: State as first-class graph data structure
- **Strands**: Session management, conversation memory
- **AutoGen**: Conversation history in messages
- **CrewAI**: Task context and agent memory

**Agenkit Equivalent**:
- **Message** type carries context
- **Conversational** pattern for multi-turn state
- **Memory Hierarchy** pattern for working/episodic/semantic memory

**Status**: ✅ Well covered

---

## Orchestration Philosophies (Framework Differentiation)

Frameworks differ not in *what patterns* they support, but in *how they structure orchestration*:

### 1. **Graph-Based** (LangGraph)

**Philosophy**: Agent workflows as finite state machines (FSM) with nodes and edges

**Key Features**:
- Explicit state transitions
- Conditional routing between agents
- Cyclic workflows (loops)
- Stateful computations

**Use Cases**: Complex, deterministic workflows with clear dependencies

**Agenkit Equivalent**: **Orchestration** pattern (sequential/parallel) + **Planning** pattern

**Gap**: No explicit graph/FSM abstraction - users implement via orchestration composition

---

### 2. **Conversation-Based** (AutoGen)

**Philosophy**: Workflows as multi-turn conversations between agents

**Key Features**:
- LLM-to-LLM dialogue
- Natural language coordination
- Emergent behavior from conversation
- Research-grade flexibility

**Use Cases**: Exploratory, flexible collaboration where coordination protocol is learned

**Agenkit Equivalent**: **Conversational** + **Multiagent** patterns

**Status**: ✅ Covered

---

### 3. **Role-Based** (CrewAI)

**Philosophy**: Agents as specialized "crew members" with defined organizational roles

**Key Features**:
- Explicit role hierarchy (Planner, Researcher, Writer, QA)
- Task delegation based on role expertise
- Organizational metaphor (teams, crews)

**Use Cases**: Clear division of labor, team-like collaboration

**Agenkit Equivalent**: **Multiagent** + **Agents-as-Tools** + **Planning**

**Gap**: No explicit "role" abstraction - agents define their own capabilities but no role taxonomy

**Recommendation**: Document role-based meta-pattern using existing primitives

---

### 4. **Code-First** (smolagents)

**Philosophy**: Agents generate and execute Python code for actions (not JSON tool calls)

**Key Features**:
- Natural composability (function nesting, loops, conditionals)
- Minimal abstractions (~1000 LOC)
- Sandboxed execution (Blaxel, E2B, Modal, Docker, Pyodide)
- Tool calls as code generation

**Use Cases**: Transparent, debuggable agent behavior; smaller models on HuggingFace

**Agenkit Equivalent**: **ReAct** pattern (reasoning + action) + **Reasoning with Tools**

**Innovation**: Code generation instead of JSON tool calling

**Gap**: Agenkit doesn't mandate code-first approach - agents can implement either style

**Recommendation**: Document code-first pattern as alternative to JSON tool calling in ReAct pattern

---

### 5. **Model-Driven** (Strands)

**Philosophy**: Leverage LLM reasoning for planning/orchestration (don't hardcode flows)

**Key Features**:
- 4 primitives (A2A, agents-as-tools, swarms, graphs, workflows)
- Model reasons about coordination
- Dynamic adaptation based on LLM decisions
- AWS production integrations

**Use Cases**: Enterprise deployments needing observability, governance, security

**Agenkit Equivalent**: All patterns allow model-driven coordination - not prescriptive

**Status**: ✅ Covered by pattern flexibility

---

## Strands-Specific Patterns

[AWS Strands](https://aws.amazon.com/blogs/machine-learning/multi-agent-collaboration-patterns-with-strands-agents-and-amazon-nova/) exposes 4 collaboration patterns:

### 1. **Agents-as-Tools**

**Description**: Hierarchical delegation where orchestrator dynamically consults domain experts

**Agenkit Equivalent**: ✅ **Agents-as-Tools** pattern (exact match)

---

### 2. **Swarms Agents**

**Description**: Autonomous collaboration with self-organizing teams of agents

**Fundamental Composition**:
- Multiagent (multiple agents)
- Autonomous (self-directed)
- Decentralized coordination

**Agenkit Equivalent**: **Autonomous** + **Multiagent** patterns

**Note**: Similar to Swarm meta-pattern analyzed in AGENT_PATTERNS_ANALYSIS.md

**Status**: ✅ Composable from existing patterns

---

### 3. **Agent Graphs**

**Description**: Structured workflows with deterministic execution paths

**Fundamental Composition**:
- Orchestration (control flow)
- Planning (task decomposition)
- Explicit state transitions

**Agenkit Equivalent**: **Orchestration** + **Planning** patterns

**Gap**: No explicit graph/FSM abstraction like LangGraph

**Recommendation**: Document graph-based orchestration as meta-pattern

---

### 4. **Agent Workflows**

**Description**: Stateful workflows with pause/resume across sessions

**Key Feature**: "Persist beyond a single session"

**Fundamental Composition**:
- Orchestration (sequential/conditional)
- Memory Hierarchy (persistent state)
- Planning (progress tracking)

**Agenkit Equivalent**: **Orchestration** + **Memory Hierarchy** + **Conversational**

**Gap**: No built-in checkpoint/resume primitives

**Recommendation**: Add checkpoint/resume pattern (critical for long-running workflows)

---

## OpenAI Swarm → Agents SDK

[OpenAI Swarm](https://github.com/openai/swarm) → [Agents SDK](https://blog.agen.cy/p/openai-agents-sdk-a-comprehensive)

**Status**: Swarm deprecated, superseded by Agents SDK (production-ready)

### Core Abstractions

1. **Routines**: Instructions + tools defining agent behavior
2. **Handoffs**: Transfer control to another agent

**Philosophy**: "Lightweight, scalable patterns for many independent tasks"

### Key Pattern: Handoff-Centric Architecture

**Handoff Mechanism**:
- Agents operate independently
- Connect only through handoff functions
- Full context transfer on handoff
- Responses come from handoff target

**Agenkit Equivalent**: **Agents-as-Tools** + **Orchestration**

**Gap**: Handoffs not modeled as explicit primitive with return semantics

---

## smolagents Innovation: Code-First Agents

[Hugging Face smolagents](https://huggingface.co/docs/smolagents/en/index)

### Core Innovation

**CodeAgent** (primary agent type):
- Generates Python code (not JSON tool calls)
- Executes code in sandboxes
- Natural composability: loops, conditionals, function calls

**Quote** ([smolagents docs](https://smolagents.org/)):
> "Agents write actions in code... enabling natural composability (function nesting, loops, conditionals)"

### Why This Matters

**Traditional approach**:
```json
{"tool": "calculator", "args": {"operation": "add", "x": 5, "y": 3}}
```

**Code-first approach**:
```python
result = calculator.add(5, 3)
if result > 7:
    search("large numbers")
```

**Benefits**:
- Transparent logic (readable Python)
- Natural control flow (if/else, loops)
- Easier debugging
- Composable functions

### Agenkit Implications

**Current State**: Agenkit is agnostic - agents can implement either style

**Recommendation**:
1. Document code-first as alternative implementation style in **ReAct** pattern
2. Add security guidance for code execution (sandboxing)
3. Show examples of both JSON tool calling and code generation

---

## Framework Comparison Matrix

| Feature/Pattern | Strands | smolagents | OpenAI SDK | LangGraph | AutoGen | CrewAI | Agenkit |
|----------------|---------|------------|------------|-----------|---------|--------|---------|
| **Handoffs** | ✅ A2A | ✅ Implicit | ✅ Explicit | ✅ Edges | ✅ Conv | ✅ Task | ⚠️ Via Agents-as-Tools |
| **Routines** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Roles | ⚠️ Per-agent |
| **Code-First** | ❌ | ✅ Primary | ❌ | ❌ | ❌ | ❌ | ⚠️ Optional |
| **Graph/FSM** | ✅ Workflows | ❌ | ❌ | ✅ Primary | ❌ | ❌ | ⚠️ Via composition |
| **Pause/Resume** | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Swarm/Emergence** | ✅ | ❌ | ✅ Concept | ❌ | ❌ | ❌ | ⚠️ Via composition |
| **Voting** | ❌ | ❌ | ❌ | ⚠️ Custom | ❌ | ❌ | ❌ |
| **Debate** | ❌ | ❌ | ❌ | ⚠️ Custom | ✅ LLM-LLM | ❌ | ❌ |
| **Consensus** | ❌ | ❌ | ❌ | ⚠️ Custom | ⚠️ Implicit | ❌ | ⚠️ Basic |
| **Memory Hierarchy** | ❌ | ❌ | ❌ | ⚠️ State | ❌ | ⚠️ Task | ✅ |
| **Observability** | ✅ AWS | ⚠️ Basic | ✅ | ⚠️ LangSmith | ⚠️ | ⚠️ | ✅ OpenTelemetry |

**Legend**:
- ✅ First-class primitive or strong support
- ⚠️ Possible via composition or custom implementation
- ❌ Not supported or no documentation

---

## Key Insights from Framework Analysis

### 1. **Handoffs are Universal**

Every framework models agent-to-agent delegation as a core primitive:
- **Strands**: A2A protocol
- **OpenAI**: Handoff tools
- **LangGraph**: Graph edges
- **Google ADK**: Coordinator routing
- **AutoGen**: Conversation turns

**Agenkit**: Handoffs exist through Agents-as-Tools but aren't explicitly named

**Recommendation**: Make "Handoffs" explicit in Agenkit vocabulary

---

### 2. **Orchestration Philosophy ≠ Fundamental Patterns**

Frameworks differ in *how they express* orchestration (graph, conversation, roles, code), not *what coordination mechanisms* they support.

**All frameworks use the same fundamental patterns** we identified:
- Reflection (implicit in most frameworks)
- Agents-as-Tools (hierarchical delegation)
- Orchestration (sequential/parallel/conditional)
- ReAct (reasoning + action)
- Multiagent (coordination)

**Implication**: Agenkit doesn't need to pick one philosophy - support all via pattern flexibility

---

### 3. **Production Frameworks Prioritize Ergonomics**

Research frameworks (AutoGen) focus on flexibility and LLM-to-LLM experiments.

Production frameworks focus on:
- **Developer ergonomics**: Simple APIs, minimal code
- **Observability**: Logging, tracing, debugging
- **Safety**: Sandboxing, guardrails, timeouts
- **Governance**: Permission systems, audit trails
- **Reliability**: Error handling, retry logic, context preservation

**Agenkit Strength**: Already has production-grade observability (OpenTelemetry), middleware (retry, circuit breaker), and safety patterns

---

### 4. **Code-First is an Implementation Detail**

smolagents' code-first approach is an **implementation strategy** for the **ReAct pattern**, not a new fundamental pattern.

**Choice**:
- Code generation (smolagents)
- JSON tool calling (most frameworks)

Both implement the same pattern: "Agent reasons about what to do, then does it"

**Recommendation**: Document both styles in ReAct pattern

---

### 5. **Missing in Most Frameworks: Voting/Debate/Consensus**

Despite research (ACL 2025) showing 10-13% performance gains from voting and debate:
- Most frameworks don't provide voting primitives
- Debate is only in AutoGen (LLM-to-LLM conversations)
- Consensus is rarely formalized

**Opportunity**: Agenkit can differentiate by providing first-class voting, debate, and consensus in expanded Multiagent pattern

---

## Gaps in Agenkit (Framework Perspective)

### 1. **Explicit Handoff Primitive** 🔥 HIGH PRIORITY

**What**: First-class abstraction for agent-to-agent delegation with context preservation

**Why**: Universal across all frameworks, critical for reliability

**Current**: Achievable via Agents-as-Tools + Orchestration, but not explicit

**Recommendation**: Add `Handoff` class or enhance Agents-as-Tools with handoff semantics

**Design**:
```python
class Handoff:
    target_agent: Agent
    context: Message | dict
    return_to_sender: bool = False  # Resume original agent after handoff
    preserve_history: bool = True
```

---

### 2. **Checkpoint/Resume for Long-Running Workflows** 🔥 HIGH PRIORITY

**What**: Save agent state mid-execution, resume later (critical for 30-hour autonomous agents)

**Why**: Strands, LangGraph, OpenAI SDK all support this; crucial for production

**Current**: Not supported

**Recommendation**: Add checkpoint/resume pattern

**Design**:
```python
class CheckpointableOrchestrator(Orchestrator):
    def checkpoint(self) -> str:  # Returns checkpoint ID
    def resume(checkpoint_id: str) -> Orchestrator:
```

---

### 3. **Routine/Role Abstraction** 🎯 MEDIUM PRIORITY

**What**: First-class abstraction for agent instructions/roles

**Why**: Common across frameworks (Swarm routines, CrewAI roles)

**Current**: Implicit in agent implementation

**Recommendation**: Add optional `AgentRoutine` or `AgentRole` helper class

**Design**:
```python
class AgentRoutine:
    name: str
    instructions: str
    tools: list[Tool]

class RoleBasedAgent(Agent):
    def __init__(self, routine: AgentRoutine):
        ...
```

---

### 4. **Graph/FSM Orchestration** 🎯 MEDIUM PRIORITY

**What**: Explicit graph-based workflows like LangGraph

**Why**: Popular paradigm, clear visual representation

**Current**: Achievable via Orchestration + Planning composition

**Recommendation**: Document graph-based meta-pattern, consider adding `GraphOrchestrator` helper

**Not Urgent**: Composable from existing patterns

---

### 5. **Code-First ReAct Style** 🔵 LOW PRIORITY

**What**: Agents generate Python code (like smolagents) instead of JSON tool calls

**Why**: Transparent, debuggable, composable

**Current**: Not prescribed - agents can implement either way

**Recommendation**: Document code-first as alternative ReAct implementation with security guidance

---

## Recommendations

### Immediate (v0.39.0-v0.40.0)

1. **Make Handoffs Explicit**
   - Add `Handoff` class or expand Agents-as-Tools documentation
   - Show handoff patterns clearly in examples
   - Add context preservation guarantees

2. **Expand Multiagent Pattern**
   - Add `VotingAgent` (addresses gap vs all frameworks)
   - Enhance `ConsensusAgent` with convergence detection
   - Add `DebateAgent` (AutoGen's strength)
   - Document role-based orchestration

3. **Document Meta-Patterns**
   - Graph-based orchestration (LangGraph style)
   - Role-based teams (CrewAI style)
   - Code-first ReAct (smolagents style)
   - Conversation-based coordination (AutoGen style)

### Short-Term (v0.40.0-v0.41.0)

4. **Add Checkpoint/Resume Pattern**
   - Critical for long-running agents (30-hour sessions)
   - Strands, LangGraph, OpenAI SDK all have this
   - Production requirement

5. **Optional: Add AgentRoutine/Role Helper**
   - Ergonomic abstraction for common pattern
   - Not required (composable from existing primitives)
   - Nice-to-have for developer experience

### Long-Term (v0.42.0+)

6. **Consider GraphOrchestrator Helper**
   - LangGraph-style FSM orchestration
   - Visual workflow representation
   - Not urgent - composable from existing patterns

---

## Competitive Positioning

### Agenkit's Unique Strengths

1. **Cross-Language Parity**: 6 languages (Python, Go, TypeScript, C++, Rust, Zig)
   - No other framework has this
   - Production deployment flexibility

2. **Production-Grade Observability**: OpenTelemetry integration
   - Better than most frameworks
   - Enterprise-ready

3. **Comprehensive Patterns**: 11 fundamental patterns
   - More complete than any single framework
   - Research-backed (Memory Hierarchy, Reasoning with Tools)

4. **Minimal, Composable**: Like smolagents philosophy but with full pattern coverage

### Where Frameworks Lead

1. **Developer Ergonomics**:
   - CrewAI (role-based simplicity)
   - smolagents (code-first transparency)
   - Strands (AWS integrations)

2. **Specific Paradigms**:
   - LangGraph (graph/FSM)
   - AutoGen (LLM-to-LLM debate)

3. **Platform Lock-in Benefits**:
   - Strands (AWS)
   - Microsoft (AutoGen + Azure)
   - OpenAI (Agents SDK + API)

### Differentiation Strategy

**Don't compete on paradigm** (graph vs conversation vs role vs code) - support all through pattern flexibility

**Compete on**:
1. **Multi-language production deployments**
2. **Complete pattern coverage** (especially voting/debate/consensus gaps in other frameworks)
3. **Production-grade middleware** (observability, resilience, safety)
4. **Research-backed patterns** (Memory Hierarchy, Reasoning with Tools)

---

## Action Items

### For Issue #149 (Zig Critical Patterns)

When implementing Multiagent pattern in Zig:
- Include VotingAgent with multiple protocols
- Enhanced ConsensusAgent with convergence
- Document handoff semantics clearly
- Consider DebateAgent (can defer to #150)

### For Issue #222 (Advanced Examples)

Create examples showing:
1. **Code Review System**: Demonstrates debate + voting (addresses framework gap)
2. **Multi-Stage Research**: Demonstrates checkpoint/resume pattern (Strands-style workflow)
3. **Role-Based Team**: Demonstrates CrewAI-style role orchestration

Each example should:
- Show which fundamental patterns compose it
- Reference equivalent framework approaches (LangGraph, CrewAI, Strands)
- Document when to use vs alternatives

### For Documentation

1. **Create `docs/FRAMEWORK_COMPARISON.md`**
   - Map Agenkit patterns to framework features
   - Help users migrate from other frameworks
   - Show how to implement framework-specific paradigms in Agenkit

2. **Enhance `docs/META_PATTERNS.md`**
   - Add handoff pattern
   - Add checkpoint/resume pattern
   - Add role-based orchestration
   - Add graph-based orchestration
   - Add code-first ReAct

3. **Create migration guides**:
   - From LangGraph → Agenkit
   - From CrewAI → Agenkit
   - From AutoGen → Agenkit
   - From Strands → Agenkit

---

## Conclusion

**Key Findings**:

1. ✅ **Agenkit's fundamental patterns are complete** - frameworks don't expose new fundamental coordination mechanisms

2. 🔑 **Handoffs are the universal primitive** - should be made explicit in Agenkit

3. 📐 **Orchestration philosophy varies** - graph vs conversation vs role vs code - but all use same fundamental patterns

4. ⚠️ **Gaps in production features**: Checkpoint/resume (critical for long-running workflows)

5. 🎯 **Opportunity**: Voting/Debate/Consensus are missing in most frameworks - Agenkit can lead here

6. 💡 **Frameworks prioritize ergonomics** - developer experience matters as much as completeness

**Strategic Recommendation**:

Focus on:
1. Making handoffs explicit (universal across all frameworks)
2. Adding checkpoint/resume (production requirement)
3. Expanding Multiagent with voting/debate/consensus (differentiation)
4. Documenting meta-patterns showing how to achieve framework-specific paradigms

Agenkit's strength is **complete pattern coverage + cross-language support + production-grade observability**. Don't try to be LangGraph (graphs) or CrewAI (roles) or smolagents (code-first) - be the foundation that enables all paradigms.

---

**Sources**:
- [AWS Strands Multi-Agent Patterns](https://aws.amazon.com/blogs/machine-learning/multi-agent-collaboration-patterns-with-strands-agents-and-amazon-nova/)
- [Strands Agents 1.0 Announcement](https://aws.amazon.com/blogs/opensource/introducing-strands-agents-1-0-production-ready-multi-agent-orchestration-made-simple/)
- [Strands Documentation](https://strandsagents.com/latest/)
- [Hugging Face smolagents](https://smolagents.org/)
- [smolagents GitHub](https://github.com/huggingface/smolagents)
- [OpenAI Swarm (deprecated)](https://github.com/openai/swarm)
- [OpenAI Agents SDK Guide](https://blog.agen.cy/p/openai-agents-sdk-a-comprehensive)
- [Framework Comparison - Langfuse](https://langfuse.com/blog/2025-03-19-ai-agent-comparison)
- [AI Agent Frameworks 2025 - Turing](https://www.turing.com/resources/ai-agent-frameworks)
- [LangGraph vs CrewAI vs AutoGen](https://langwatch.ai/blog/best-ai-agent-frameworks-in-2025-comparing-langgraph-dspy-crewai-agno-and-more)
- [Agent Handoffs: LangGraph vs OpenAI vs Google ADK](https://blog.arcade.dev/agent-handoffs-langgraph-openai-google)
- [Azure AI Agent Design Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [Best Practices for Agent Orchestration](https://skywork.ai/blog/ai-agent-orchestration-best-practices-handoffs/)

**Last Updated**: November 30, 2025
**Next Review**: Q1 2026 (monitor framework releases and new patterns)
