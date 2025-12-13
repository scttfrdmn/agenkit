# Agenkit Techniques Library - Design Document

**Created**: 2025-11-30
**Target Version**: v0.41.0+
**Status**: Design Phase

---

## Executive Summary

Agenkit has **complete pattern coverage** (18+ patterns implemented). This proposal adds a new `techniques/` area to house:

1. **Reasoning Techniques** (CoT, ToT, Self-Consistency, etc.) - Advanced reasoning methods
2. **Protocols** (MCP, A2A) - Industry standards for agent interoperability
3. **Compositions** - Trivial implementations showing "patterns that aren't really patterns"
4. **Frameworks** - Already covered in Milestone #29 (Framework Interoperability)

## Motivation

Recent books and frameworks on agentic systems cover a wide range of concepts, which can be categorized into:

- **Behavioral Patterns**: Reusable solutions to recurring agent coordination problems → **Agenkit has comprehensive coverage ✅**
- **Protocols**: Industry standards for interoperability (MCP, A2A) → **Gap: Should add for ecosystem compatibility**
- **Infrastructure**: Cross-cutting concerns (resilience, observability) → **Agenkit has complete middleware ✅**
- **Reasoning Techniques**: Advanced prompting and reasoning methods → **Gap: Valuable for o3/Opus 4 era**
- **Compositions**: Simple combinations of existing patterns → **Gap: Valuable as recipes/examples**

### What is a "Pattern"?

For clarity, Agenkit defines patterns as:
1. **Reusable solution** to a recurring coordination/orchestration problem
2. **Clear structure** with defined roles, interactions, and lifecycle
3. **Non-trivial** - requires more than just combining existing primitives
4. **General purpose** - applicable across domains

**Examples**:
- ✅ Pattern: Reflection (iterative critique loop with stopping conditions, history tracking)
- ✅ Pattern: Planning (plan generation, step execution, monitoring, replanning)
- ❌ Not a pattern: RAG (just Sequential + Retrieval tool - too simple)
- ❌ Not a pattern: Prioritization (just priority queue - too basic)

### Gap Analysis

**What Agenkit Has:**
- ✅ Patterns: 18+ comprehensive patterns (Sequential, Parallel, Router, ReAct, Planning, Reflection, Memory, Autonomous, Supervisor, Collaborative, Human-in-Loop, Fallback, Consensus, etc.)
- ✅ Infrastructure: Complete production middleware (Circuit Breaker, Retry, Rate Limiting, Timeout, Caching, Observability)

**Valuable Additions:**
- ❌ Reasoning Techniques: CoT, ToT, Self-Consistency, GoT - Critical for modern reasoning models (o3, Opus 4)
- ❌ Protocols: MCP (Anthropic standard), A2A (cross-platform) - Important for ecosystem interoperability
- ❌ Composition Examples: Simple recipes showing how to combine patterns (educational value)

---

## Architecture

```
agenkit/
├── patterns/          # Behavioral patterns (18+ patterns) ✅ COMPLETE
│   ├── orchestration.py
│   ├── react.py
│   ├── reflection.py
│   ├── memory.py
│   └── ... (18 total patterns)
│
├── middleware/        # Infrastructure ✅ COMPLETE
│   ├── retry.py
│   ├── circuit_breaker.py
│   ├── rate_limiter.py
│   └── ... (observability, etc.)
│
└── techniques/        # NEW - Reasoning, protocols, compositions
    │
    ├── reasoning/     # Advanced reasoning techniques
    │   ├── __init__.py
    │   ├── chain_of_thought.py         # CoT prompting
    │   ├── tree_of_thought.py          # ToT search with backtracking
    │   ├── self_consistency.py         # Multiple samples + voting
    │   ├── graph_of_thought.py         # Graph-based reasoning
    │   ├── least_to_most.py            # Break down to subproblems
    │   └── plan_and_solve.py           # Planning-first approach
    │
    ├── protocols/     # Industry standards
    │   ├── __init__.py
    │   ├── mcp/       # Model Context Protocol (Anthropic)
    │   │   ├── __init__.py
    │   │   ├── server.py
    │   │   ├── client.py
    │   │   ├── resources.py
    │   │   └── transports.py
    │   └── a2a/       # Agent-to-Agent Protocol
    │       ├── __init__.py
    │       ├── protocol.py
    │       ├── transport.py
    │       └── discovery.py
    │
    ├── compositions/  # Simple recipes combining patterns
    │   ├── __init__.py
    │   ├── README.md              # "Simple compositions vs full patterns"
    │   ├── simple_human_approval.py  # Minimal approval tool (10 lines)
    │   ├── rag.py                    # Retrieval + Sequential (15 lines)
    │   ├── prioritization.py         # Task scoring + queue (20 lines)
    │   ├── goal_monitoring.py        # Planning + callbacks (25 lines)
    │   ├── exploration.py            # ReAct + search strategy (30 lines)
    │   └── learning_feedback.py      # Reflection + Memory (35 lines)
    │
    └── frameworks/    # Framework-style implementations
        └── (Milestone #29 - Framework Interoperability covers this)
```

---

## Phase 1: Reasoning Techniques (8 weeks)

**Target Version**: v0.41.0
**Priority**: HIGH
**Why**: o3, Opus 4 use extended reasoning - users need these techniques

### Techniques to Implement

#### 1. Chain-of-Thought (CoT)
```python
from agenkit.techniques.reasoning import ChainOfThought

agent = ChainOfThought(
    llm=llm,
    prompt_template="Let's think step by step:\n{query}"
)

response = await agent.process(
    Message(content="What is 15 * 24?")
)
# Uses step-by-step reasoning
```

**Implementation**: ~150 LOC
- Structured prompting for step-by-step reasoning
- Parse reasoning steps from output
- Configurable prompt templates

#### 2. Tree-of-Thought (ToT)
```python
from agenkit.techniques.reasoning import TreeOfThought

agent = TreeOfThought(
    llm=llm,
    branching_factor=3,      # Explore 3 paths per step
    depth=4,                 # Max depth 4
    evaluator=score_path     # Score each reasoning path
)

response = await agent.process(
    Message(content="Solve this creative writing problem...")
)
# Explores multiple reasoning paths, backtracks if needed
```

**Implementation**: ~300 LOC
- Tree search with branching
- Path evaluation and pruning
- Backtracking when paths fail
- Best path selection

#### 3. Self-Consistency
```python
from agenkit.techniques.reasoning import SelfConsistency

agent = SelfConsistency(
    agent=base_agent,
    num_samples=5,           # Sample 5 times
    voting_strategy="majority"  # Or "weighted", "confidence"
)

response = await agent.process(
    Message(content="What is the capital of France?")
)
# Samples multiple times, returns consensus answer
```

**Implementation**: ~200 LOC
- Multiple sampling
- Voting strategies (majority, weighted, confidence-based)
- Consistency metrics

#### 4. Graph-of-Thought (GoT)
```python
from agenkit.techniques.reasoning import GraphOfThought

agent = GraphOfThought(
    llm=llm,
    max_nodes=20,
    max_edges=40
)

response = await agent.process(
    Message(content="Analyze this complex multi-hop reasoning problem...")
)
# Builds reasoning graph, explores connections
```

**Implementation**: ~350 LOC
- Graph construction (nodes = thoughts, edges = connections)
- Graph traversal strategies
- Cycle detection
- Path aggregation

#### 5. Least-to-Most Prompting
```python
from agenkit.techniques.reasoning import LeastToMost

agent = LeastToMost(
    llm=llm,
    decomposer=decompose_problem,
    max_depth=5
)

response = await agent.process(
    Message(content="Solve this complex math problem...")
)
# Breaks down problem into subproblems, solves sequentially
```

**Implementation**: ~200 LOC
- Problem decomposition
- Sequential subproblem solving
- Solution composition

#### 6. Plan-and-Solve
```python
from agenkit.techniques.reasoning import PlanAndSolve

agent = PlanAndSolve(
    llm=llm,
    planner=create_plan,
    solver=execute_steps
)

response = await agent.process(
    Message(content="Complex reasoning task...")
)
# Creates detailed plan first, then executes
```

**Implementation**: ~200 LOC
- Planning phase (structured plan generation)
- Execution phase (step-by-step execution)
- Plan validation

### Deliverables
- [ ] 6 reasoning technique implementations (~1,400 LOC)
- [ ] Comprehensive tests (90%+ coverage, ~1,000 LOC)
- [ ] Examples for each technique (~600 LOC)
- [ ] Documentation guide: `docs/techniques/REASONING_TECHNIQUES.md`
- [ ] API reference

### Timeline
- Week 1-2: CoT, Self-Consistency, Plan-and-Solve
- Week 3-4: Least-to-Most, basic tests
- Week 5-6: ToT, GoT (more complex)
- Week 7-8: Testing, documentation, examples

---

## Phase 2: Protocol Implementations (6 weeks)

**Target Version**: v0.42.0
**Priority**: HIGH
**Why**: Emerging industry standards (MCP from Anthropic, A2A for multi-agent)

### 2.1: Model Context Protocol (MCP)

**What**: Anthropic's standard for tool/resource integration
**Spec**: https://modelcontextprotocol.io/

```python
from agenkit.techniques.protocols.mcp import MCPServer, MCPResource

# Create MCP server
server = MCPServer(name="my-agent-server")

# Register resources
@server.resource("user://profile")
async def get_user_profile(user_id: str) -> dict:
    return {"name": "John", "email": "john@example.com"}

# Register tools
@server.tool("search")
async def search_tool(query: str) -> dict:
    return {"results": [...]}

# Start server
await server.start()

# Client usage
from agenkit.techniques.protocols.mcp import MCPClient

client = MCPClient(server_url="http://localhost:3000")
profile = await client.get_resource("user://profile", user_id="123")
result = await client.call_tool("search", query="agentic AI")
```

**Implementation**: ~800 LOC
- MCP server (HTTP/SSE/stdio transports)
- MCP client
- Resource registration and discovery
- Tool registration and invocation
- Message protocol implementation
- Integration with Agenkit agents

**Deliverables**:
- [ ] MCP server implementation
- [ ] MCP client implementation
- [ ] Transport layer (HTTP, SSE, stdio)
- [ ] Examples (Claude integration)
- [ ] Tests (~500 LOC)
- [ ] Documentation

### 2.2: Agent-to-Agent (A2A) Protocol

**What**: Cross-platform agent communication standard
**Supported by**: Google Vertex AI, AWS Bedrock

```python
from agenkit.techniques.protocols.a2a import A2AAgent, A2AMessage

# Create A2A-compatible agent
agent = A2AAgent(
    agent_id="analyzer-001",
    capabilities=["text-analysis", "sentiment"],
    transport="grpc"
)

# Send message to another agent
message = A2AMessage(
    from_agent="analyzer-001",
    to_agent="summarizer-001",
    content={"text": "Analyze this..."}
)
response = await agent.send(message)

# Register with discovery service
await agent.register_discovery(
    service_url="https://agent-registry.example.com"
)

# Find agents by capability
agents = await agent.discover(capability="summarization")
```

**Implementation**: ~600 LOC
- A2A protocol implementation
- Message format (JSON-RPC style)
- Transport layer (HTTP, gRPC, WebSocket)
- Agent discovery service
- Capability registration
- Integration examples (Vertex AI, Bedrock)

**Deliverables**:
- [ ] A2A protocol implementation
- [ ] Discovery service client
- [ ] Transport implementations
- [ ] Examples (Vertex AI, Bedrock integration)
- [ ] Tests (~400 LOC)
- [ ] Documentation

### Timeline
- Week 1-3: MCP implementation (server, client, transports)
- Week 4-6: A2A implementation (protocol, discovery, examples)

---

## Phase 3: Compositions (4 weeks)

**Target Version**: v0.43.0
**Priority**: MEDIUM
**Why**: Educational - shows what ISN'T a pattern, provides recipes

### Compositions to Implement

Each composition shows:
1. Why it's NOT a pattern (too simple, just composition)
2. How to build it (10-40 lines)
3. When to use it
4. Common variations

#### 1. Simple Human Approval (~10 lines)

**Note**: Agenkit has a full `HumanInLoopAgent` pattern (v0.32.0) with:
- Confidence-based approval triggers
- Configurable approval functions
- Structured approval requests/responses
- Async approval workflows

But for simple cases, you can use a 10-line tool:

```python
# techniques/compositions/simple_human_approval.py

class SimpleApprovalTool(Tool):
    """Minimal approval tool for simple use cases."""
    async def execute(self, action: str) -> dict:
        response = input(f"Approve {action}? (y/n): ")
        return {"approved": response == 'y'}

# Use with any agent:
agent = ReActAgent(tools=[SimpleApprovalTool(), ...])
```

**When to use**:
- **Simple tool** (this): Quick prototypes, single approval point
- **Full pattern** (HumanInLoopAgent): Production systems, confidence-based triggers, complex workflows

#### 2. RAG (~15 lines)
```python
# techniques/compositions/rag.py

rag_agent = SequentialAgent([
    RetrievalTool(vector_store),  # Step 1: Retrieve
    AnswerAgent(llm)               # Step 2: Generate
])
# RAG is just Sequential + Retrieval Tool
```

#### 3. Prioritization (~20 lines)
```python
# techniques/compositions/prioritization.py

class PrioritizedTaskAgent(Agent):
    def __init__(self, worker: Agent, priority_fn: Callable):
        self.worker = worker
        self.priority_fn = priority_fn
        self.queue = []  # Heap

    async def add_task(self, task: Message):
        priority = self.priority_fn(task)
        heapq.heappush(self.queue, (-priority, task))

    async def process_next(self):
        _, task = heapq.heappop(self.queue)
        return await self.worker.process(task)
```

#### 4. Goal Monitoring (~25 lines)
```python
# techniques/compositions/goal_monitoring.py

class GoalMonitoringAgent(Agent):
    def __init__(self, planner: PlanningAgent, goal_fn: Callable):
        self.planner = planner
        self.goal_fn = goal_fn

    async def process(self, message: Message):
        plan = await self.planner.create_plan(message)

        for step in plan.steps:
            result = await self.planner.execute_step(step)

            # Monitor goal progress
            progress = self.goal_fn(result)
            if progress >= 1.0:
                return result  # Goal achieved

        return result
```

#### 5. Exploration Strategy (~30 lines)
```python
# techniques/compositions/exploration.py

class ExplorationAgent(Agent):
    def __init__(self, base_agent: ReActAgent, strategy: str = "ucb"):
        self.base_agent = base_agent
        self.strategy = strategy
        self.action_stats = {}  # Track action rewards

    async def process(self, message: Message):
        # UCB exploration-exploitation tradeoff
        action = self._select_action()
        result = await self.base_agent.process_with_action(message, action)
        self._update_stats(action, result.reward)
        return result
```

#### 6. Learning from Feedback (~35 lines)
```python
# techniques/compositions/learning_feedback.py

class LearningAgent(Agent):
    def __init__(self, agent: Agent, memory: MemoryHierarchy):
        self.agent = agent
        self.memory = memory

    async def process(self, message: Message):
        # Retrieve similar past interactions
        similar = await self.memory.retrieve(message.content)

        # Add to context
        augmented_message = self._augment_with_history(message, similar)

        # Process
        result = await self.agent.process(augmented_message)

        # Store for future learning
        await self.memory.store(
            content=f"Q: {message.content}\nA: {result.content}",
            importance=result.metadata.get("quality", 0.5)
        )

        return result
```

### Deliverables
- [ ] 6 composition implementations (~150 LOC total)
- [ ] README explaining "Why these aren't patterns"
- [ ] Tests for each (~300 LOC)
- [ ] Documentation with use cases

### Timeline
- Week 1: Human-in-Loop, RAG, Prioritization
- Week 2: Goal Monitoring, Exploration
- Week 3: Learning from Feedback
- Week 4: Testing, documentation

---

## Phase 4: Integration with Milestone #29 (Ongoing)

**Milestone #29**: Framework Interoperability (due Oct 2025)
**Status**: 12 open issues covering LangChain, Haystack, CrewAI, AutoGen, Vertex AI, Bedrock

The `techniques/frameworks/` directory structure aligns with existing Milestone #29 work:
- Issue #189: LangChain Pattern Examples
- Issue #190: LlamaIndex Pattern Examples
- Issue #191: Haystack Pattern Examples
- Issue #192: CrewAI Pattern Examples
- Issue #193: AutoGen Pattern Examples
- Issue #195: Vertex AI Agent Builder Integration
- Issue #196: AWS Bedrock AgentCore Integration

**No new work needed** - just ensure `techniques/frameworks/` directory houses these implementations.

---

## Milestones and Issues

### Milestone: Techniques Library - Reasoning & Protocols
**Target**: v0.41.0 - v0.43.0 (18 weeks total)
**Due Date**: June 30, 2026

### Issues to Create

#### Reasoning Techniques (v0.41.0)
- [ ] **Issue**: Implement Chain-of-Thought (CoT) reasoning
  - Labels: `enhancement`, `techniques`, `reasoning`
  - Assignee: TBD
  - Estimate: 1 week

- [ ] **Issue**: Implement Tree-of-Thought (ToT) reasoning
  - Labels: `enhancement`, `techniques`, `reasoning`
  - Estimate: 2 weeks

- [ ] **Issue**: Implement Self-Consistency reasoning
  - Labels: `enhancement`, `techniques`, `reasoning`
  - Estimate: 1 week

- [ ] **Issue**: Implement Graph-of-Thought (GoT) reasoning
  - Labels: `enhancement`, `techniques`, `reasoning`
  - Estimate: 2 weeks

- [ ] **Issue**: Implement Least-to-Most Prompting
  - Labels: `enhancement`, `techniques`, `reasoning`
  - Estimate: 1 week

- [ ] **Issue**: Implement Plan-and-Solve reasoning
  - Labels: `enhancement`, `techniques`, `reasoning`
  - Estimate: 1 week

#### Protocol Implementations (v0.42.0)
- [ ] **Issue**: Implement Model Context Protocol (MCP)
  - Labels: `enhancement`, `techniques`, `protocols`
  - Estimate: 3 weeks

- [ ] **Issue**: Implement Agent-to-Agent (A2A) Protocol
  - Labels: `enhancement`, `techniques`, `protocols`
  - Estimate: 3 weeks

#### Compositions (v0.43.0)
- [ ] **Issue**: Implement Composition Techniques (Human-in-Loop, RAG, etc.)
  - Labels: `enhancement`, `techniques`, `compositions`
  - Estimate: 4 weeks

---

## Success Criteria

### Must-Have (v0.41.0 - v0.43.0)
- [ ] 6 reasoning techniques implemented with tests
- [ ] MCP protocol support (server + client)
- [ ] A2A protocol support (protocol + discovery)
- [ ] 6 composition examples with documentation
- [ ] 90%+ test coverage for all new code
- [ ] Comprehensive documentation
- [ ] Examples for each technique/protocol

### Nice-to-Have (Future)
- [ ] Performance benchmarks for reasoning techniques
- [ ] Cross-language implementation (Go, Rust)
- [ ] Additional reasoning techniques (ReAct+, Reflexion)
- [ ] MCP/A2A integration examples with major platforms

---

## Documentation Plan

### New Documentation Files

1. **`docs/techniques/REASONING_TECHNIQUES.md`**
   - Overview of reasoning techniques
   - When to use each technique
   - Comparison matrix (CoT vs ToT vs Self-Consistency)
   - Examples and benchmarks

2. **`docs/techniques/PROTOCOLS.md`**
   - MCP specification and usage
   - A2A protocol and usage
   - Integration examples
   - Platform compatibility

3. **`docs/techniques/COMPOSITIONS.md`**
   - Why these aren't patterns
   - When to use compositions
   - Recipe catalog
   - Extension guide

4. **`techniques/compositions/README.md`**
   - Inline documentation explaining each composition
   - Clear statement: "These are NOT patterns"
   - Links to full patterns in `patterns/`

### Updated Documentation

1. **`README.md`**
   - Add "Techniques" section alongside "Patterns"
   - Highlight reasoning techniques for o3/Opus 4 support
   - Mention MCP/A2A protocol support

2. **`ROADMAP.md`**
   - Add Techniques Library phases
   - Update version targets

---

## Dependencies

### External Libraries
- MCP: `mcp` (if official Python SDK available) or implement from spec
- A2A: Implement from spec (no official Python SDK yet)
- Reasoning: No new dependencies (use existing LLM clients)

### Internal Dependencies
- All techniques leverage existing `patterns/` implementations
- MCP/A2A integrate with existing `Agent` interface
- Compositions showcase existing pattern combinations

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| MCP spec changes | HIGH | Implement against stable spec, version compatibility layer |
| A2A not widely adopted | MEDIUM | Provide value even without wide adoption (cross-platform communication) |
| Reasoning techniques slow | MEDIUM | Provide async implementations, caching, batch processing |
| Composition examples too trivial | LOW | Focus on educational value, provide extensions |

---

## References

### Books and Papers
- "Agentic Design Patterns" by Antonio Gulli (2025)
- Chain-of-Thought: https://arxiv.org/abs/2201.11903
- Tree-of-Thought: https://arxiv.org/abs/2305.10601
- Self-Consistency: https://arxiv.org/abs/2203.11171
- Graph-of-Thought: https://arxiv.org/abs/2308.09687

### Specifications
- Model Context Protocol: https://modelcontextprotocol.io/
- Agent-to-Agent Protocol: (Vertex AI and Bedrock documentation)

### Related Work
- Agenkit Milestone #29: Framework Interoperability
- Agenkit ROADMAP.md: Current development phases

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-30 | Claude | Initial design document |

---

## Appendix: Pattern Classification

### Agenkit's Pattern Philosophy

**What makes something a Pattern in Agenkit?**

1. **Behavioral/Structural Pattern**: Has clear roles, interactions, lifecycle
2. **Reusable**: Solves recurring coordination problems
3. **Non-trivial**: Requires more than combining primitives
4. **Configurable**: Multiple valid implementations of same pattern
5. **General purpose**: Works across domains

### Examples of What IS a Pattern

| Pattern | Why it's a Pattern |
|---------|-------------------|
| **Reflection** | Complex: iterative loop, stopping conditions, critique parsing, history tracking |
| **Planning** | Complex: plan generation, validation, execution, monitoring, replanning |
| **Memory Hierarchy** | Complex: three-tier system, promotion/eviction, semantic retrieval |
| **Supervisor** | Complex: task decomposition, delegation, result aggregation, error handling |
| **HumanInLoopAgent** | Complex: confidence thresholds, async approval, structured requests, retry logic |

### Examples of What is NOT a Pattern (but still useful!)

| "Pattern" | Why it's NOT | What it is | Location |
|-----------|--------------|------------|----------|
| **Simple Approval** | Too trivial (input + if statement) | Tool/Function | `compositions/` |
| **RAG** | Just Sequential + Tool | Architecture | `compositions/` |
| **Prioritization** | Just priority queue | Data structure | `compositions/` |
| **Goal Tracking** | Just callbacks | Feature | `compositions/` |

**Note**: HumanInLoopAgent is BOTH:
- **Full Pattern** (`patterns/human_in_loop.py`) - Production-grade with confidence triggers, async, structured
- **Simple Composition** (`compositions/simple_human_approval.py`) - 10-line tool for prototypes

Both are valid! Use what fits your needs.

### Comparison with Common Agentic Concepts

Many books and frameworks discuss similar concepts. Here's how they map to Agenkit:

| Concept | Agenkit Category | Implementation |
|---------|-----------------|----------------|
| Chain-of-Thought | Reasoning Technique | `techniques/reasoning/cot.py` |
| Tree-of-Thought | Reasoning Technique | `techniques/reasoning/tot.py` |
| Self-Consistency | Reasoning Technique | `techniques/reasoning/self_consistency.py` |
| Sequential Chains | Pattern | `patterns/orchestration.py` |
| Parallel Execution | Pattern | `patterns/orchestration.py` |
| ReAct | Pattern | `patterns/react.py` |
| Reflection | Pattern | `patterns/reflection.py` |
| Planning | Pattern | `patterns/planning.py` |
| Memory Systems | Pattern | `patterns/memory.py` |
| Human Oversight (full) | Pattern | `patterns/human_in_loop.py` |
| Human Approval (simple) | Composition | `compositions/simple_human_approval.py` |
| RAG | Composition | `compositions/rag.py` |
| Circuit Breakers | Infrastructure | `middleware/circuit_breaker.py` |
| Rate Limiting | Infrastructure | `middleware/rate_limiter.py` |
| Retries | Infrastructure | `middleware/retry.py` |
| Observability | Infrastructure | `middleware/tracing.py` |
| MCP | Protocol | `techniques/protocols/mcp/` |
| A2A | Protocol | `techniques/protocols/a2a/` |

**Key Insight**: Agenkit provides clear separation:
- **patterns/** = Complex behavioral patterns
- **middleware/** = Cross-cutting infrastructure
- **techniques/** = Reasoning methods, protocols, simple recipes
