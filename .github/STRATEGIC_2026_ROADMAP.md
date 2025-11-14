# Agenkit 2026 Strategic Roadmap

**Context:** November 2025 - The Year Agents Went to Production

## State of the Field (November 2025)

### Major Shifts in 2025

1. **Reasoning Models Are Now Standard**
   - Claude 4/Sonnet 4.5: Hybrid reasoning, **30-hour autonomous operation**
   - OpenAI o3/o3-mini/o4-mini: Visual reasoning, autonomous tool use
   - Models now reason deeply before acting (extended thinking mode)

2. **Production Adoption Breakthrough**
   - 2025 = "agents went from research to production"
   - AutoGen emerged as most production-ready
   - LangGraph dominates for stateful workflows
   - Multi-agent collaboration is mainstream

3. **New Capabilities Unlocked**
   - Agents work autonomously for 30+ hours (Claude Sonnet 4.5)
   - Tool use during extended reasoning (not just sequential)
   - Parallel speculative execution ("firing off multiple searches")
   - Context-aware resource management (tracks token usage)

### Strategic Position for Agenkit

**Old Mission (2024):** "Minimal interface for agent communication"

**New Mission (2026):** "Minimal, composable interfaces for **production-scale autonomous agents**"

**Why the shift:**
- Agents actually work now (30 hours autonomous!)
- Models reason deeply (o3, Claude 4 hybrid thinking)
- Production is happening (not just research)
- New challenges: Cost, safety, memory, durability, evaluation

## 2026 Strategic Roadmap

### Q4 2025 (Nov-Dec) - Foundation Layer

**Focus:** Core infrastructure for autonomous agents

#### Memory Systems ✅ CRITICAL
- [ ] Memory interface (ABC)
- [ ] In-memory implementation
- [ ] Redis implementation
- [ ] Integration with endless project
- [ ] Sliding window strategy
- [ ] Summarization strategy
- [ ] Importance weighting

**Why Now:** 30-hour agents need persistent memory beyond context windows.

**Issue:** #67

#### Cost Tracking Middleware ✅ PRODUCTION NEED
- [ ] Cost tracker (per session, per agent)
- [ ] Budget limiter (stop at threshold)
- [ ] Model cost optimizer (cheap for simple, expensive for hard)
- [ ] Dashboard/reporting

**Why Now:** Reasoning models expensive (o3: $5/1M, Claude Opus 4: $15/1M). 30-hour runs could cost hundreds.

**Issue:** #68

#### Long-Running Agent Pattern ✅ CRITICAL
- [ ] Checkpointing interface
- [ ] State persistence
- [ ] Resume from checkpoint
- [ ] Durable execution (like LangGraph)
- [ ] Time-travel debugging

**Why Now:** Claude Sonnet 4.5 works for 30 hours autonomously. Need durability.

**Issue:** #69

---

### Q1 2026 (Jan-Mar) - Language Expansion

**Focus:** TypeScript port + Safety layer

#### TypeScript/JavaScript Port ✅ HIGH PRIORITY
- [ ] Core interfaces (Agent, Message, Tool)
- [ ] HTTP/WebSocket/gRPC transports
- [ ] Middleware system
- [ ] LLM adapters (OpenAI, Anthropic)
- [ ] Examples and documentation
- [ ] npm package

**Why First:** Massive web developer market, Node.js ecosystem, browser agents.

**Market Research (Nov 2025):** LangChain.js mature but heavy. Opportunity for minimal alternative.

**Issue:** #70

#### Agent Safety Framework ✅ PRODUCTION REQUIREMENT
- [ ] Input validation (prompt injection defense)
- [ ] Output validation (schema, content filtering)
- [ ] Action constraints (sandboxing, permission system)
- [ ] Anomaly detection
- [ ] Safety violations logging

**Why Now:** Autonomous agents need guardrails. Research shows "prompt injection = complete control."

**Issue:** #71

#### Reasoning Budget Pattern ✅ NEW IN 2025
- [ ] Dynamic allocation (instant vs extended thinking)
- [ ] Complexity detection
- [ ] Model router (o3 for hard, Sonnet for medium, Haiku for simple)
- [ ] Cost-quality tradeoff

**Why Now:** Hybrid models (Claude 4, o3) have dual modes. Need orchestration.

**Issue:** #72

---

### Q2 2026 (Apr-Jun) - Advanced Patterns

**Focus:** New agent patterns from 2025 research

#### Evaluation Framework ✅ CRITICAL GAP
- [ ] Success/failure metrics
- [ ] Session replay
- [ ] Regression detection
- [ ] A/B testing for agents
- [ ] Benchmark suite

**Why Now:** How do you know 30-hour agent succeeded? Need measurement.

**Issue:** #73

#### Routing & Semantic Tool Selection ✅ SCALING NEED
- [ ] Semantic tool selection (inspired by AgentCore Gateway)
- [ ] Load balancer (route to least-loaded agent)
- [ ] Enhanced circuit breaker
- [ ] Gateway building blocks (not full gateway)

**Why Now:** Production systems have hundreds of tools. Need intelligent routing.

**Issue:** #74

#### Tool-Use During Reasoning Pattern ✅ NEW CAPABILITY
- [ ] Interleaved reasoning + tool calls
- [ ] Different from ReAct (reasoning inside tool selection)
- [ ] Support for Claude 4 / o3 style
- [ ] Examples and patterns

**Why Now:** Claude 4: "Use tools during extended thinking." New capability to support.

**Issue:** #75

#### Implement Core Agent Patterns ✅
- [ ] Complete issues #64, #65, #66 (already created)
- [ ] ReAct pattern (industry standard)
- [ ] Tree-of-Thoughts (with efficiency constraints)
- [ ] Iterative refinement
- [ ] Critic-actor
- [ ] End-to-end examples (3 applications)

**Issues:** #64, #65, #66 (already created)

---

### Q3 2026 (Jul-Sep) - Performance Tier

**Focus:** Rust port + Advanced features

#### Rust Port ✅ PERFORMANCE DIFFERENTIATION
- [ ] Core interfaces
- [ ] Tokio-based async (4.5k req/sec proven)
- [ ] HTTP/WebSocket/gRPC transports
- [ ] LLM adapters
- [ ] Cargo package
- [ ] Performance benchmarks

**Why Now:** Edge computing, embedded agents, performance-critical systems.

**Why After TypeScript:** Smaller market but high differentiation.

**Issue:** #76

#### Advanced Memory Strategies ✅
- [ ] Temporal knowledge graphs (like Zep)
- [ ] Multi-type memory (episodic, semantic, procedural)
- [ ] Memory consolidation
- [ ] Forgetting strategies
- [ ] Cross-session memory

**Why Now:** Building on Q4 foundation, needed for complex agents.

**Issue:** #77

#### Production Reference Architectures ✅
- [ ] Multi-agent system (10+ agents)
- [ ] High-availability setup
- [ ] Cost-optimized deployment
- [ ] Security-hardened configuration
- [ ] Scaling patterns (1K+ RPS)

**Why Now:** Production users need blueprints.

**Issue:** #78

---

## New Agent Patterns (Based on 2025 Research)

### Critical Patterns to Add

1. **Long-Running Agent Pattern**
   - 30-hour autonomous operation
   - Checkpointing, resume, state persistence
   - Status: Q4 2025

2. **Reasoning Budget Pattern**
   - Dynamic allocation (instant vs extended)
   - Model routing based on complexity
   - Status: Q1 2026

3. **Tool-Use During Reasoning**
   - Interleaved reasoning + tool calls
   - Different from ReAct
   - Status: Q2 2026

4. **Parallel Speculative Execution**
   - Anticipatory parallelism
   - Rollback on wrong speculation
   - Status: Q2 2026

5. **Context-Aware Resource Management**
   - Self-monitoring (token usage, cost)
   - Prevents premature abandonment
   - Status: Q4 2025 (via cost tracking)

### Patterns Already Planned
- ReAct (Issue #64)
- Tree-of-Thoughts (Issue #64)
- Iterative Refinement (Issue #64)
- Multi-agent patterns (Issue #64)

## Anti-Patterns to Document

1. **Infinite Loop Anti-Pattern**
   - Fix: Max depth, cycle detection, timeout

2. **Context Explosion Anti-Pattern**
   - Fix: Sliding windows, summarization, external memory

3. **Tool Thrashing Anti-Pattern**
   - Fix: Caching, validation, cooldowns

4. **Prompt Injection Anti-Pattern**
   - Fix: Input sanitization, role separation, sandboxing

5. **Error Propagation Anti-Pattern**
   - Fix: Checkpointing, validation gates

6. **Over-Automation Anti-Pattern**
   - Fix: Human-in-loop for critical actions

7. **Unbounded Resource Consumption**
   - Fix: Rate limiting, circuit breakers, quotas

**Status:** Add to Agent Patterns Guide (Q1 2026)

## Language Support Strategy

### Current: Python ✅, Go ✅

### Tier 1: TypeScript (Q1 2026)
- **Market:** Massive web developer population
- **Use cases:** Browser agents, Node.js, serverless, full-stack
- **Research:** LangChain.js growing, VoltAgent emerging
- **Decision:** Next language (Q1 2026)

### Tier 2: Rust (Q3 2026)
- **Market:** Growing in infrastructure/systems
- **Use cases:** High-performance, embedded, safety-critical
- **Research:** Tokio excellent (4.5k req/sec benchmarked)
- **Decision:** Performance differentiation

### Future Consideration: Java/C# (Enterprise)
- **Market:** Enterprise systems
- **Use cases:** Spring Boot, .NET ecosystems
- **Timeline:** Post-1.0

## Interesting Capabilities to Reproduce

### High Priority

1. **DSPy-Style Prompt Optimization**
   - Automatic prompt tuning
   - "Programming not prompting"
   - Status: Q2 2026

2. **Structured Output Validation**
   - Type-safe LLM responses
   - Automatic retry on schema failure
   - Status: Q1 2026 (safety framework)

3. **Agent Sandboxing**
   - Safe code execution (containers/VMs)
   - Resource limits
   - Status: Q1 2026 (safety framework)

4. **Durable Execution**
   - LangGraph-style persistence
   - Resume from failures
   - Status: Q4 2025 (checkpointing)

5. **Reasoning Transparency**
   - Instrumentation for reasoning traces
   - Debug why agent made decision
   - Status: Q2 2026 (observability enhancement)

## Agent Gateways

### Analysis: Useful for Production, Not Core

**AWS AgentCore Gateway (2025):**
- Semantic tool selection
- Protocol translation (MCP ↔ API ↔ Lambda)
- Auth/authz
- Observability

**Verdict:** Provide building blocks, not full gateway

**Agenkit Strategy:**
```
agenkit/
  routing/              # NEW (Q2 2026)
    semantic.py         # Semantic tool selection
    load_balancer.py    # Least-loaded routing

  protocols/            # NEW (Q1 2026)
    mcp.py             # Model Context Protocol support
    agent_to_agent.py  # A2A protocol
```

**Issue:** #74 (Q2 2026)

## Integration with Adjacent Projects

### endless Project
- **What:** Effectively infinite context
- **Integration:** Memory interface (Q4 2025)
- **How:** EndlessMemory implementation
- **No code copying:** Interface only

### Vector Databases
- **What:** Semantic memory, RAG
- **Integration:** Memory interface (Q4 2025)
- **How:** Plug-in implementations (Pinecone, Weaviate, etc.)

### Observability Backends
- **What:** Jaeger, Prometheus, Grafana
- **Integration:** Already done ✅
- **Status:** OpenTelemetry in production

## Success Metrics (2026)

### Technical
- [ ] TypeScript port feature parity with Python/Go
- [ ] Memory system handling 30+ hour sessions
- [ ] Cost tracking preventing runaway spend
- [ ] Safety framework catching prompt injections
- [ ] Evaluation framework detecting regressions

### Adoption
- [ ] 1,000+ GitHub stars
- [ ] 100+ production deployments
- [ ] 10+ contributors
- [ ] 3 language ports (Python, Go, TypeScript)

### Community
- [ ] 500+ Discord members
- [ ] 10+ blog posts/tutorials
- [ ] 5+ conference talks
- [ ] 20+ ecosystem integrations

## Risk Mitigation

### Technical Risks
1. **Complexity Creep:** Maintain minimal philosophy
2. **Language Port Quality:** Comprehensive tests, feature parity
3. **Breaking Changes:** Semantic versioning, deprecation warnings

### Market Risks
1. **LangChain Dominance:** Focus on minimal, production-focused alternative
2. **Framework Fatigue:** Differentiate on simplicity and cross-language
3. **Rapid Model Evolution:** Abstract via interfaces

## Next Steps

1. **Immediate (This Week):**
   - [ ] Create GitHub issues for Q4 2025 priorities (#67-69)
   - [ ] Update Agent Patterns Guide with new patterns
   - [ ] Update README positioning

2. **Q4 2025 (Next 6 Weeks):**
   - [ ] Implement memory interface + implementations
   - [ ] Implement cost tracking middleware
   - [ ] Implement long-running agent pattern
   - [ ] Begin TypeScript port planning

3. **Ongoing:**
   - [ ] Monitor LLM landscape (new models, capabilities)
   - [ ] Engage with production users (feedback loop)
   - [ ] Refine roadmap based on learnings

---

**Last Updated:** November 13, 2025
**Next Review:** January 1, 2026
**Owner:** Core maintainers

**Questions?** Open a [discussion](https://github.com/scttfrdmn/agenkit/discussions) or comment on roadmap issues.
