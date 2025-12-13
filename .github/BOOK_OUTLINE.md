# Agent Patterns: A Comprehensive Guide
## "Gang of Four" Style Pattern Catalog for AI Agents

**Working Title**: *Agent Patterns: Building Production AI Systems with Composable Patterns*

**Authors**: Scott Friedman (lead), Contributors TBD

**Publisher Target**: O'Reilly Media, Manning Publications, or self-published via Pragmatic Bookshelf

**Status**: Research and outline phase (November 2025)

**Current Assets**:
- Foundation chapters started: `docs-site/guides/agent-patterns.md` (2,609 lines)
- Pattern analysis complete: `.github/AGENT_PATTERNS_ANALYSIS.md`
- Framework analysis complete: `.github/FRAMEWORK_ANALYSIS.md`
- 11 patterns implemented across 6 languages in Agenkit project

---

## Book Concept

### Inspiration: Gang of Four

The seminal *Design Patterns: Elements of Reusable Object-Oriented Software* (1994) by Gamma, Helm, Johnson, and Vlissides established the vocabulary for object-oriented design. This book aims to do the same for AI agent systems.

**Key principles from GoF we'll adopt**:
1. **Pattern Catalog Structure**: Name, Intent, Motivation, Applicability, Structure, Participants, Collaborations, Consequences, Implementation, Sample Code, Known Uses, Related Patterns
2. **Classification Taxonomy**: Group patterns by purpose (creational, structural, behavioral → coordination, composition, cognitive)
3. **Language-Agnostic**: Patterns transcend implementation details
4. **Production-Focused**: Real systems, not academic toys
5. **Relationships**: Show how patterns relate and compose

### What Makes This Different

**Existing agent books/resources**:
- Framework-specific tutorials (LangGraph, AutoGen docs)
- Academic papers (research-focused, not production)
- Blog posts (fragmented, inconsistent terminology)
- Vendor documentation (platform lock-in)

**This book**:
- **Framework-agnostic**: Patterns work across LangGraph, AutoGen, CrewAI, Strands, smolagents, Agenkit
- **Research-backed**: Cites 2025 papers (LatentMAS, Multi-Agent Collaboration Survey, ACL voting/consensus studies)
- **Production-proven**: Patterns from Anthropic, AWS, Microsoft, OpenAI production systems
- **Complete taxonomy**: 11 fundamental + meta-patterns + framework mapping
- **Cross-language**: Python, Go, TypeScript, C++, Rust, Zig implementations
- **Composable**: Shows how patterns combine (meta-patterns)

---

## Target Audience

### Primary Readers

1. **Senior Software Engineers** building AI features into production systems
2. **Engineering Managers/Architects** designing multi-agent architectures
3. **AI/ML Engineers** transitioning from notebooks to production
4. **CTO/Tech Leads** evaluating agent frameworks and patterns

### Prerequisites

- Working knowledge of LLMs and API usage (OpenAI, Anthropic, etc.)
- Software engineering background (async/await, APIs, state management)
- Experience with Python or similar languages
- NOT required: Deep ML knowledge, agent framework experience

### What Readers Will Learn

By the end of this book, readers will:
1. Understand the **11 fundamental agent patterns** and when to use each
2. Know how to **compose patterns** to solve complex problems (meta-patterns)
3. Map patterns to **any framework** (LangGraph, AutoGen, CrewAI, custom)
4. Build **production-grade** agent systems with reliability and observability
5. Avoid common pitfalls (handoff failures, context loss, infinite loops)
6. Evaluate framework trade-offs (graph vs conversation vs role vs code-first)

---

## Book Structure

### Part I: Foundations (Chapters 1-4)

**Goal**: Establish common vocabulary and mental models

#### Chapter 1: The Agent Landscape (2025)
- What is an agent? (classical vs modern definitions)
- The watershed moment: 30-hour autonomous operation
- Production reality: AutoGen, LangGraph at scale
- Key challenges: memory, cost, durability, safety
- LLM output controls workflow (Hugging Face definition)

**Status**: ✅ Draft exists in `docs-site/guides/agent-patterns.md`

#### Chapter 2: Agents vs Tasks vs Tools
- Core abstractions: Message, Agent, Tool
- Agent: Stateful computation with decision-making
- Task: One-shot execution with explicit lifecycle
- Tool: Deterministic function without agency
- Why the distinction matters (composability, testing, reliability)

**Status**: ✅ Draft exists

#### Chapter 3: Framework Landscape Analysis
- Major frameworks: LangGraph, AutoGen, CrewAI, Strands, smolagents, OpenAI SDK
- Orchestration philosophies: Graph, Conversation, Role, Code-First, Model-Driven
- Universal primitives: Routines, Handoffs, Tools, Context
- Comparative analysis (when to use which)
- Framework mapping to fundamental patterns

**Status**: 🔄 Source material complete (`.github/FRAMEWORK_ANALYSIS.md`)

#### Chapter 4: Pattern Taxonomy
- Pattern classification: Coordination, Composition, Cognitive
- Fundamental vs composite (meta-patterns)
- Dimensional analysis (Actors, Types, Structures, Strategies, Coordination)
- Reading the pattern catalog (structure explanation)
- How patterns relate and compose

**Status**: 🔄 Source material complete (`.github/AGENT_PATTERNS_ANALYSIS.md`)

---

### Part II: Fundamental Patterns (Chapters 5-15)

**Goal**: Deep dive into 11 core coordination mechanisms

**Pattern Structure** (following GoF format):
1. **Name and Classification**
2. **Intent**: One-line summary
3. **Also Known As**: Alternative names in literature/frameworks
4. **Motivation**: Real-world problem this solves
5. **Applicability**: When to use (and when not to)
6. **Structure**: Visual diagram + components
7. **Participants**: Agents, messages, state
8. **Collaborations**: How participants interact
9. **Consequences**: Benefits and trade-offs
10. **Implementation**: Key considerations, variants
11. **Sample Code**: Python + one other language (Go/TypeScript)
12. **Known Uses**: Production systems using this pattern
13. **Related Patterns**: How this composes with others

---

#### Chapter 5: Reflection Pattern 🔄

**Intent**: Enable iterative self-improvement through generator-critic loops

**Classification**: Cognitive pattern (enhances quality through iteration)

**Structure**:
- Generator agent produces initial output
- Critic agent evaluates and provides feedback
- Generator refines based on critique
- Repeat until convergence or max iterations

**Known Uses**:
- Code review systems (generator writes, critic reviews)
- Document editing (draft → critique → revise)
- Research validation (hypothesis → peer review → refinement)

**Variants**:
- Multi-critic reflection (parallel critics)
- Staged reflection (different critics for different aspects)
- Self-reflection (same agent as generator and critic)

**Related Patterns**:
- Debate (multiple generators + critics)
- Agents-as-Tools (critic can be specialized agent)

**Status**: ✅ Implemented in Agenkit, chapter outline exists

---

#### Chapter 6: Agents-as-Tools Pattern 🔄

**Intent**: Hierarchical delegation where agents invoke other agents as specialized tools

**Classification**: Composition pattern (structural organization)

**Structure**:
- Orchestrator agent with decision-making capability
- Specialist agents registered as tools
- Tool invocation through standard interface
- Results returned to orchestrator for synthesis

**Known Uses**:
- Strands' agents-as-tools pattern
- Microsoft's AutoGen agent delegation
- Anthropic's research system (lead agent + subagents)

**Variants**:
- Dynamic agent selection (orchestrator chooses specialists)
- Static tool roster (predefined specialist set)
- Recursive delegation (specialists can have sub-specialists)

**Related Patterns**:
- Orchestration (sequential/parallel composition)
- Planning (orchestrator as planner)
- Multiagent (coordination protocol)

**Status**: ✅ Implemented in Agenkit, chapter outline exists

---

#### Chapter 7: Orchestration Pattern 🔄

**Intent**: Compose multiple agents with explicit control flow (sequential, parallel, conditional)

**Classification**: Composition pattern (structural organization)

**Structure**:
- Sequential: Agent A → Agent B → Agent C (pipeline)
- Parallel: Agents A, B, C execute simultaneously, results aggregated
- Conditional: Route to agent based on runtime conditions

**Known Uses**:
- LangGraph's graph-based workflows
- Processing pipelines (data ingestion → analysis → reporting)
- Parallel research (multiple agents explore different angles)

**Variants**:
- Graph orchestration (LangGraph FSM style)
- Workflow orchestration (Strands stateful workflows)
- Dynamic orchestration (runtime topology changes)

**Related Patterns**:
- Planning (decomposes into orchestration steps)
- Agents-as-Tools (orchestrates specialist invocations)

**Status**: ✅ Implemented in Agenkit, needs chapter write-up

---

#### Chapter 8: ReAct Pattern 🔄

**Intent**: Interleave reasoning (thinking) and action (tool use) in iterative cycles

**Classification**: Cognitive pattern (decision-making process)

**Structure**:
- Think: Agent reasons about what to do next
- Act: Agent invokes tool or takes action
- Observe: Agent processes result
- Repeat until task complete

**Known Uses**:
- Original ReAct paper (Yao et al., 2022)
- Most agent frameworks' default mode
- Web browsing agents, research agents

**Variants**:
- Code-first ReAct (smolagents - generates Python code)
- JSON tool calling ReAct (OpenAI function calling)
- Reasoning during tool use (tools available during thinking)

**Related Patterns**:
- Reasoning with Tools (advanced variant)
- Autonomous (extended ReAct with goal management)

**Status**: ✅ Implemented in Agenkit, needs chapter write-up

---

#### Chapter 9: Conversational Pattern 🔄

**Intent**: Stateful multi-turn dialogue management with context preservation

**Classification**: Coordination pattern (interaction protocol)

**Structure**:
- Message history tracking
- Context window management
- Turn-taking protocol
- State persistence across turns

**Known Uses**:
- ChatGPT-style interfaces
- Customer support bots
- Interactive debugging assistants

**Variants**:
- Single-agent conversation (user ↔ agent)
- Multi-agent conversation (AutoGen group chat)
- Hierarchical conversation (routing to specialists)

**Related Patterns**:
- Memory Hierarchy (persistent conversation memory)
- Multiagent (multi-party conversations)

**Status**: ✅ Implemented in Agenkit, needs chapter write-up

---

#### Chapter 10: Task Pattern 🔄

**Intent**: One-shot execution with explicit lifecycle (create → execute → complete)

**Classification**: Coordination pattern (execution model)

**Structure**:
- Task creation with goals and constraints
- Single execution pass
- Success/failure determination
- Resource cleanup

**Known Uses**:
- Batch processing jobs
- One-time data transformations
- Scheduled automation tasks

**Variants**:
- Task with retries (fault tolerance)
- Task with timeout (resource limits)
- Task with checkpointing (long-running resilience)

**Related Patterns**:
- Autonomous (extends task with goal pursuit)
- Planning (decomposes into subtasks)

**Status**: ✅ Implemented in Agenkit, needs chapter write-up

---

#### Chapter 11: Multiagent Pattern 🔄

**Intent**: Coordinate multiple agents working together (cooperation, competition, coopetition)

**Classification**: Coordination pattern (multi-party interaction)

**Structure**:
- Agent registration and discovery
- Coordination protocol (sequential, parallel, peer-to-peer)
- Result aggregation
- Decision-making mechanisms

**Known Uses**:
- Research teams (multiple agents explore problem)
- Competitive scenarios (agents with opposing goals)
- Democratic decision-making (voting, consensus)

**Variants**:
- Sequential multiagent (ordered execution)
- Parallel multiagent (simultaneous execution)
- Voting (democratic decision-making)
- Consensus (iterative agreement)
- Debate (structured argumentation)
- Coopetition (mixed cooperation/competition)

**Related Patterns**:
- Voting (multiagent variant)
- Debate (multiagent variant)
- Consensus (multiagent variant)
- Orchestration (coordination mechanism)

**Status**: ⚠️ Basic implementation in Agenkit, needs expansion (voting, debate, consensus)

---

#### Chapter 12: Planning Pattern 🔄

**Intent**: Hierarchical task decomposition with dynamic replanning

**Classification**: Cognitive pattern (problem-solving strategy)

**Structure**:
- Goal specification
- Task decomposition (break into subtasks)
- Execution ordering
- Progress monitoring
- Replanning on failure

**Known Uses**:
- Project management agents
- Research planning systems
- Complex workflow automation

**Variants**:
- Hierarchical Task Network (HTN) planning
- Forward planning (goal → steps)
- Backward planning (steps → goal)
- Adaptive replanning (adjust on failure)

**Related Patterns**:
- Task (individual units of planning)
- Orchestration (executes planned steps)
- Autonomous (combines planning with execution)

**Status**: ✅ Implemented in Agenkit, needs chapter write-up

---

#### Chapter 13: Autonomous Pattern 🔄

**Intent**: Self-directed goal pursuit with minimal human intervention

**Classification**: Coordination pattern (execution model)

**Structure**:
- Long-running execution
- Self-determined next actions
- Goal tracking and adaptation
- Termination conditions

**Known Uses**:
- Personal assistant agents (30-hour sessions)
- Continuous monitoring systems
- Self-organizing workflows

**Variants**:
- Bounded autonomy (time/resource limits)
- Supervised autonomy (human-in-the-loop checkpoints)
- Fully autonomous (no human intervention)

**Related Patterns**:
- Planning (goal decomposition)
- ReAct (reasoning-action cycles)
- Memory Hierarchy (state persistence)

**Status**: ✅ Implemented in Agenkit, needs chapter write-up

---

#### Chapter 14: Memory Hierarchy Pattern 🔄

**Intent**: Three-tier memory system (working, episodic, semantic) for context management

**Classification**: Cognitive pattern (state management)

**Structure**:
- Working memory: Current conversation context (limited size)
- Episodic memory: Historical interactions (retrievable by time/relevance)
- Semantic memory: General knowledge and facts (long-term storage)

**Known Uses**:
- Long-running personal assistants
- Customer support with history
- Research agents building knowledge bases

**Variants**:
- Vector-based retrieval (embedding search)
- Time-based retrieval (recent interactions)
- Relevance-based retrieval (similarity search)

**Related Patterns**:
- Conversational (uses working memory)
- Autonomous (requires persistent memory)
- Reasoning with Tools (semantic memory as tool)

**Status**: ✅ Implemented in Agenkit, chapter outline exists

---

#### Chapter 15: Reasoning with Tools Pattern 🔄

**Intent**: Tools available during reasoning, not just after (interleaved thinking and tool use)

**Classification**: Cognitive pattern (enhanced reasoning)

**Structure**:
- Agent can query tools while thinking
- Tools inform reasoning process
- Iterative refinement of thought with tool results
- More efficient than think → act → think

**Known Uses**:
- Claude's extended thinking with web search
- Research agents that query databases mid-thought
- Code generation with API documentation lookup

**Variants**:
- Synchronous tool access (block until tool returns)
- Asynchronous tool access (continue reasoning while tool executes)
- Speculative tool use (query multiple tools in parallel)

**Related Patterns**:
- ReAct (basic reasoning + action)
- Agents-as-Tools (tools can be agents)

**Status**: ✅ Implemented in Agenkit, needs chapter write-up

---

### Part III: Meta-Patterns (Chapters 16-22)

**Goal**: Show how fundamental patterns compose to solve complex problems

**Format**: Less formal than Part II, more case-study driven

---

#### Chapter 16: Voting Pattern 🆕

**Intent**: Democratic decision-making through multiple independent agent evaluations

**Composition**: **Multiagent** + **Orchestration** (parallel)

**Structure**:
- Multiple agents process same input independently
- Each agent submits vote/response
- Aggregation via decision protocol (majority, plurality, ranked-choice, weighted)
- Final decision based on aggregate

**Research Evidence**: 13.2% improvement in reasoning tasks (ACL 2025)

**Known Uses**:
- Ensemble methods for robustness
- Quality control (multiple reviewers)
- Adversarial filtering (majority vote removes outliers)

**Decision Protocols**:
1. Majority voting (>50% agreement)
2. Plurality (most votes wins)
3. Ranked-choice voting (preference ordering)
4. Weighted voting (by confidence scores)
5. Unanimity (all must agree)

**Related Patterns**:
- Consensus (iterative vs one-shot)
- Debate (interaction vs independence)
- Multiagent (coordination mechanism)

**Status**: 🆕 Identified in research, needs implementation

---

#### Chapter 17: Consensus Pattern 🆕

**Intent**: Iterative agreement through discussion and refinement

**Composition**: **Multiagent** + **Reflection** + **Conversational**

**Structure**:
- Agents propose initial responses
- Agents review each other's responses
- Iterative refinement based on feedback
- Convergence detection (similarity threshold)
- Fallback to voting if no convergence

**Research Evidence**: 2.8% improvement in knowledge tasks (ACL 2025)

**Known Uses**:
- Fact verification (multiple sources must agree)
- Document drafting (iterative group editing)
- Research synthesis (combining perspectives)

**Convergence Criteria**:
- Similarity threshold (embeddings within ε)
- Change rate (proposals stable across iterations)
- Explicit agreement (agents signal consensus)
- Iteration limit (fallback after N rounds)

**Related Patterns**:
- Voting (one-shot vs iterative)
- Debate (structured argument vs open discussion)
- Reflection (multi-agent reflection)

**Status**: ⚠️ Basic implementation exists, needs enhancement

---

#### Chapter 18: Debate Pattern 🆕

**Intent**: Structured argumentation with rounds, critiques, and synthesis

**Composition**: **Reflection** + **Multiagent** + **Conversational** + **Orchestration**

**Structure**:
- Multiple rounds of structured exchange
- Speaking order (sequential turn-taking)
- Argument tracking (claims and evidence)
- Critique and rebuttal
- Judge agent or convergence detection for final decision

**Research Evidence**: Mathematically proven to amplify correctness vs ensembles

**Known Uses**:
- AutoGen's debate capabilities (LLM-to-LLM conversations)
- Code review (author presents, reviewers debate)
- Research validation (hypothesis defense)

**Debate Formats**:
1. Oxford debate (proposition, opposition, rebuttals)
2. Fishbowl (inner circle debates, outer circle observes)
3. Round-robin (each agent responds to all others)
4. Moderated (orchestrator controls speaking order)

**Related Patterns**:
- Voting (decision mechanism after debate)
- Consensus (unstructured vs structured discussion)
- Reflection (multi-party critique)

**Status**: 🆕 Identified in research, needs implementation

---

#### Chapter 19: Coopetition Pattern 🆕

**Intent**: Agents simultaneously cooperate (shared goals) and compete (individual optimization)

**Composition**: **Multiagent** + **Autonomous** + **Planning**

**Structure**:
- Shared objective (cooperation)
- Individual metrics (competition)
- Resource constraints (competitive pressure)
- Information sharing protocols
- Nash equilibrium or Pareto optimality

**Known Uses**:
- Market simulations (firms cooperate on standards, compete on products)
- Multi-agent negotiations (shared deal, individual preferences)
- Game theory scenarios (prisoner's dilemma, stag hunt)

**Related Patterns**:
- Multiagent (coordination mechanism)
- Voting (competitive decision-making)
- Autonomous (self-interested behavior)

**Status**: 🆕 Identified in survey, needs research

---

#### Chapter 20: Swarm Pattern 🆕

**Intent**: Decentralized coordination through local rules and emergent behavior

**Composition**: **Multiagent** + **Autonomous** + Decentralized Orchestration

**Structure**:
- No central coordinator (peer-to-peer)
- Limited local perception (agents see neighbors only)
- Minimal local communication
- Simple rules → complex collective behavior
- Classic tasks: pursuit, synchronization, foraging, flocking, transport

**Research Evidence**: LLMs struggle with swarm constraints (SwarmBench 2025)

**Known Uses**:
- Strands' swarm pattern
- Distributed systems (edge computing)
- Robot swarms (physical coordination)

**Challenges**:
- LLMs designed for rich communication (struggle with minimal info)
- No global state visibility
- Emergent coordination harder than explicit

**Related Patterns**:
- Multiagent (coordination protocol)
- Autonomous (decentralized decision-making)

**Status**: 🔵 Research-stage, not production-ready yet

---

#### Chapter 21: Hierarchical Orchestrator-Worker Pattern 🆕

**Intent**: Lead agent decomposes tasks and coordinates specialized subagents in parallel

**Composition**: **Planning** + **Agents-as-Tools** + **Orchestration** (parallel)

**Structure**:
- Lead agent analyzes problem
- Decomposes into parallel subtasks
- Spawns specialist subagents
- Subagents execute independently
- Lead synthesizes results

**Known Uses**:
- Anthropic's multi-agent research system (THE canonical example)
- Strands' model-driven orchestration
- AWS Q Developer's architecture

**Related Patterns**:
- Planning (task decomposition)
- Agents-as-Tools (specialist delegation)
- Orchestration (parallel execution)

**Status**: ✅ Composable from existing patterns, needs documentation

---

#### Chapter 22: Dynamic Agent Generation (IAAG/DRTAG) 🆕

**Intent**: Automatically spawn agents based on evolving needs (initial or real-time)

**Composition**: **Planning** + **Multiagent** + **Autonomous**

**Structure**:
- IAAG: Initial Automatic Agent Generation (analyze task → spawn agents)
- DRTAG: Dynamic Real-Time Agent Generation (spawn during execution)
- Agent template library
- Capability matching (task requirements → agent skills)
- Resource management (limits on agent creation)

**Known Uses**:
- Research systems that adapt to novel problems
- Customer support (spawn specialists on demand)

**Challenges**:
- Code generation required (create agent implementations)
- Security (generated agents need sandboxing)
- Resource limits (unbounded spawning risk)

**Related Patterns**:
- Planning (determines what agents to spawn)
- Multiagent (manages spawned agents)
- Autonomous (self-organizing system)

**Status**: 🆕 Identified in research, advanced topic

---

### Part IV: Advanced Topics (Chapters 23-27)

**Goal**: Production considerations and future directions

---

#### Chapter 23: Handoffs and Context Preservation 🔥

**Intent**: The universal primitive - reliable agent-to-agent delegation

**Why Critical**: "Reliability lives and dies in the handoffs" (Skywork AI)

**Topics**:
- Handoff as first-class primitive (every framework has this)
- Context preservation guarantees
- Versioned handoff schemas
- Return/resume semantics
- Error handling in handoffs

**Frameworks**:
- Strands: A2A protocol
- OpenAI: Handoff tools with target agent
- LangGraph: Graph edges with state transfer
- Google ADK: Coordinator routing

**Best Practices**:
1. Make handoffs explicit, structured, versioned
2. Use schemas and validators (not free-form prose)
3. Preserve full context or explicitly summarize
4. Support return-to-sender (resume original agent)
5. Handle handoff failures gracefully

**Status**: 🔥 Critical gap identified, needs implementation

---

#### Chapter 24: Checkpoint and Resume for Long-Running Agents 🔥

**Intent**: Persistent state for 30-hour autonomous sessions

**Why Critical**: Production requirement for autonomous agents, supported by Strands/LangGraph/OpenAI SDK

**Topics**:
- Checkpoint serialization (state snapshot)
- Resume from checkpoint (idempotent recovery)
- Incremental checkpointing (streaming state)
- Checkpoint storage (database, S3, Redis)
- Checkpoint expiration and cleanup

**Use Cases**:
- 30-hour research sessions
- Multi-day project workflows
- Crash recovery
- Cost optimization (pause expensive agents)

**Related Patterns**:
- Autonomous (long-running execution)
- Memory Hierarchy (persistent state)
- Planning (resume from partial completion)

**Status**: 🔥 Production requirement, needs implementation

---

#### Chapter 25: Code-First vs JSON Tool Calling

**Intent**: Two implementation styles for ReAct pattern

**Comparison**:

| Aspect | Code-First (smolagents) | JSON Tool Calling (OpenAI) |
|--------|-------------------------|----------------------------|
| **Output** | Python code | JSON schema |
| **Control Flow** | Natural (if/loops) | Explicit tool sequences |
| **Debuggability** | High (read code) | Medium (inspect JSON) |
| **Composability** | Excellent (functions) | Limited (flat calls) |
| **Security** | Requires sandboxing | Safer (no code exec) |
| **Models** | Smaller models OK | Requires function calling support |

**When to Use**:
- Code-First: Transparency, complex logic, smaller models, development/debugging
- JSON: Production safety, API compatibility, structured output

**Security Considerations**:
- Sandboxing: Blaxel, E2B, Modal, Docker, Pyodide
- Resource limits: CPU, memory, network, time
- Code review: Static analysis before execution

**Status**: 🆕 Style guide, needs documentation

---

#### Chapter 26: Observability and Debugging

**Topics**:
- OpenTelemetry integration (traces, metrics, logs)
- Agent execution visualization
- Performance profiling (token usage, latency)
- Error attribution (which agent failed?)
- Cost tracking (per-agent, per-pattern)

**Agenkit Advantage**: First-class OpenTelemetry support

**Status**: ✅ Implemented, needs write-up

---

#### Chapter 27: Future Directions

**Topics**:
1. **LatentMAS**: Latent space collaboration (12th fundamental pattern candidate)
2. **Swarm Intelligence**: When LLMs improve at decentralized coordination
3. **Multi-Modal Agents**: Vision, video, audio integration
4. **Agent Learning**: Agents that improve from experience
5. **Security and Governance**: Prompt injection, jailbreaks, safety
6. **Standardization**: Agent protocols (A2A, MCP, etc.)

**Status**: 🔮 Speculative, research-tracking

---

### Appendices

#### Appendix A: Pattern Quick Reference

One-page summary of each pattern with decision tree

#### Appendix B: Framework Comparison Matrix

Complete comparison table (LangGraph, AutoGen, CrewAI, Strands, smolagents, Agenkit)

#### Appendix C: Implementation Checklist

Production readiness checklist for each pattern

#### Appendix D: Glossary

Unified terminology across frameworks

#### Appendix E: Research Bibliography

Papers, frameworks, and resources

---

## Writing Timeline

### Phase 1: Foundation (Q1 2026) - 3 months

**Goal**: Complete Part I (Chapters 1-4) to publication quality

**Chapters**:
- Chapter 1: The Agent Landscape ✅ Draft exists
- Chapter 2: Agents vs Tasks vs Tools ✅ Draft exists
- Chapter 3: Framework Landscape 🔄 Source material ready
- Chapter 4: Pattern Taxonomy 🔄 Source material ready

**Deliverable**: Self-publish Part I as "preview" or pre-release

---

### Phase 2: Fundamental Patterns (Q2-Q3 2026) - 6 months

**Goal**: Complete Part II (Chapters 5-15) - all 11 fundamental patterns

**Chapters** (in order of current completeness):
1. Reflection ✅ Draft outline exists
2. Agents-as-Tools ✅ Draft outline exists
3. Memory Hierarchy ✅ Draft outline exists
4. ReAct (expand to cover code-first variant)
5. Conversational (expand with multi-agent variant)
6. Orchestration (add graph/FSM style)
7. Planning (expand with replanning variants)
8. Task (expand with retry/timeout/checkpoint)
9. Autonomous (expand with 30-hour session context)
10. Multiagent (expand with voting/consensus/debate)
11. Reasoning with Tools (new chapter, research-backed)

**Deliverable**: Self-publish Parts I-II as "beta" book

---

### Phase 3: Meta-Patterns (Q4 2026) - 3 months

**Goal**: Complete Part III (Chapters 16-22) - 7 composite patterns

**Chapters** (in order of research evidence):
1. Voting (ACL 2025 evidence)
2. Consensus (ACL 2025 evidence)
3. Debate (mathematical proof of amplification)
4. Hierarchical Orchestrator-Worker (Anthropic production)
5. Coopetition (survey identification)
6. Dynamic Agent Generation (research trend)
7. Swarm (future research)

**Deliverable**: Complete "1.0" manuscript (Parts I-III)

---

### Phase 4: Advanced Topics (Q1 2027) - 3 months

**Goal**: Complete Part IV (Chapters 23-27) + Appendices

**Chapters**:
1. Handoffs and Context Preservation (production-critical)
2. Checkpoint and Resume (production-critical)
3. Code-First vs JSON Tool Calling (style guide)
4. Observability and Debugging (production guide)
5. Future Directions (research tracking)

**Appendices** (A-E)

**Deliverable**: Complete manuscript ready for publisher review

---

### Phase 5: Publication (Q2 2027) - 3 months

**Activities**:
- Technical review by experts (Anthropic, AWS, Hugging Face, Microsoft)
- Copy editing and formatting
- Code example testing (all 6 languages)
- Index and cross-references
- Publisher negotiation or self-publication setup

**Deliverable**: Published book (print + digital)

---

## Success Metrics

### Quantitative

- **Page count**: 400-500 pages (similar to GoF's 395 pages)
- **Code examples**: 100+ across 6 languages
- **Patterns documented**: 11 fundamental + 7 meta-patterns = 18 total
- **Citations**: 50+ academic papers and production systems
- **Sales target**: 10,000 copies first year (modest for technical book)

### Qualitative

- **Influence**: Establishes common vocabulary for agent systems
- **Framework adoption**: Patterns referenced in LangGraph, AutoGen, CrewAI docs
- **Production impact**: Companies cite book in architecture decisions
- **Educational**: Used in courses and workshops
- **Community**: Active discussion forum and pattern submissions

---

## Collaboration Model

### Open Source Integration

- **Agenkit project**: Reference implementation for all patterns
- **Pattern implementations**: Open source across 6 languages
- **Community contributions**: Pattern examples and use cases
- **Issue tracking**: GitHub issues for pattern proposals

### Author Contributions

- **Lead author**: Scott Friedman (structure, fundamental patterns, meta-patterns)
- **Contributing authors**: TBD (invite experts for specialized chapters)
  - Anthropic engineer for Hierarchical Orchestrator-Worker
  - AWS Strands team for model-driven orchestration
  - Hugging Face for code-first agents
  - Academic researchers for LatentMAS, SwarmBench

### Review Process

- **Technical reviewers**: Framework maintainers and researchers
- **Production reviewers**: Engineers using patterns in production
- **Academic reviewers**: Researchers in multi-agent systems

---

## Marketing and Distribution

### Target Channels

1. **O'Reilly Media** (traditional tech publisher)
   - Pro: Established distribution, credibility
   - Con: Lower royalties, slower process

2. **Manning Publications** (MEAP early access model)
   - Pro: Iterative feedback, loyal audience
   - Con: Long publication cycle

3. **Pragmatic Bookshelf** (developer-focused)
   - Pro: Developer audience, clean formatting
   - Con: Smaller reach than O'Reilly

4. **Self-Published** (Leanpub, Gumroad)
   - Pro: Full control, higher royalties, fast iteration
   - Con: Marketing burden, less credibility initially

**Recommendation**: Start with Leanpub (iterative releases), negotiate with O'Reilly for print edition

### Launch Strategy

1. **Preview releases**: Part I as free download (marketing funnel)
2. **Beta program**: Early access for contributors and reviewers
3. **Conference talks**: Present patterns at AI conferences
4. **Blog series**: Chapter summaries on Medium, Dev.to
5. **Framework partnerships**: Joint announcements with LangGraph, AutoGen, etc.

---

## Revenue Model

### Book Sales

- **Print**: $49.95 (O'Reilly) or $39.95 (self-published)
- **Digital**: $29.95 (self-published) or included in O'Reilly subscription
- **Bundle**: Book + video course ($99)

**Conservative estimate**: 10,000 copies × $15 royalty = $150,000 first year

### Ancillary Revenue

- **Video course**: Patterns in practice (Udemy, O'Reilly)
- **Workshops**: Corporate training on agent patterns
- **Consulting**: Architecture reviews using pattern framework
- **Agenkit Enterprise**: Commercial support for pattern implementations

---

## Risk Mitigation

### Risk 1: Patterns Become Obsolete

**Mitigation**:
- Focus on fundamental coordination mechanisms (not framework-specific)
- Quarterly updates tracking emerging patterns
- Living digital edition with updates
- Framework-agnostic approach

### Risk 2: Frameworks Dominate

**Mitigation**:
- Show how patterns map to all frameworks (not replacement)
- Position as complement to framework docs
- Collaborate with framework maintainers

### Risk 3: Academic vs Practical Tension

**Mitigation**:
- Ground all patterns in production usage
- Include "Known Uses" section (real systems)
- Balance theory (why) with practice (how)

### Risk 4: Scope Creep

**Mitigation**:
- Fixed pattern count (11 fundamental + 7 meta)
- Clear phase gates (preview → beta → 1.0)
- Defer advanced topics to later editions

---

## Next Steps

### Immediate (November-December 2025)

1. ✅ Create book outline (this document)
2. 🔄 Create GitHub milestones and issues
3. 🔄 Create labels for book work
4. ⏳ Polish Part I chapters to publication quality
5. ⏳ Create pattern template (GoF-style structure)
6. ⏳ Set up Leanpub or similar for early access

### Short-Term (Q1 2026)

1. Complete Chapter 3 (Framework Landscape)
2. Complete Chapter 4 (Pattern Taxonomy)
3. Publish Part I as preview
4. Recruit technical reviewers
5. Begin fundamental pattern chapters

### Medium-Term (Q2-Q3 2026)

1. Complete all 11 fundamental pattern chapters
2. Implement missing pattern variants (voting, debate, consensus)
3. Publish Parts I-II as beta
4. Solicit community feedback

### Long-Term (Q4 2026 - Q2 2027)

1. Complete meta-patterns and advanced topics
2. Technical review and editing
3. Publisher negotiation or self-publication
4. Launch and marketing

---

**Last Updated**: November 30, 2025
**Document Owner**: Scott Friedman
**Status**: Outline and planning phase
**Next Review**: January 2026
