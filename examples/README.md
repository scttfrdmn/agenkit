# Agenkit Examples

Comprehensive collection of **280 examples** across **6 languages** (including WASM!) demonstrating all Agenkit features, patterns, and integrations.

## 🎯 Start Here

**New to Agenkit?** Follow this path:
1. [01_basic_agent.py](01_basic_agent.py) - Your first agent
2. [02_sequential_pattern.py](02_sequential_pattern.py) - Composing agents
3. [03_parallel_pattern.py](03_parallel_pattern.py) - Parallel execution
4. [05_tool_usage.py](05_tool_usage.py) - Adding tools
5. [06_pattern_composition.py](06_pattern_composition.py) - Complex patterns

**Want structured learning?** Check out our [Tutorials](../tutorials/) with Jupyter and Marimo notebooks!

---

## 📊 Quick Stats

| Language | Examples | Status |
|----------|----------|--------|
| **Python** | 151 | ✅ Complete |
| **Rust** | 35 | ✅ Complete (+ WASM!) |
| **C++** | 42 | ✅ Complete |
| **Zig** | 37 | ✅ Complete |
| **Go** | 7 | ⚠️ Growing |
| **TypeScript** | 8 | ⚠️ Growing |
| **Total** | **280** | |

---

## 📂 Examples by Category

### 🧠 Core Patterns (11 examples)

The 11 foundational agent patterns from the Agenkit library.

**Location**: [`patterns/`](patterns/)

| Pattern | Description | Python | Go | TS |
|---------|-------------|--------|----|----|
| **ReAct** | Reasoning + Acting loop | ✅ | ✅ | ✅ |
| **Reflection** | Self-critique and improvement | ✅ | ✅ | ✅ |
| **Agents-as-Tools** | Agents calling other agents | ✅ | ✅ | ✅ |
| **Orchestration** | Coordinate multiple agents | ✅ | ✅ | ✅ |
| **Conversational** | Stateful conversations | ✅ | ✅ | ✅ |
| **Task** | Goal-oriented execution | ✅ | ✅ | ✅ |
| **Multiagent** | Parallel agent collaboration | ✅ | ✅ | ✅ |
| **Planning** | Multi-step planning | ✅ | - | - |
| **Autonomous** | Self-directed agents | ✅ | - | - |
| **Memory Hierarchy** | Tiered memory system | ✅ | - | - |
| **Reasoning with Tools** | Tool-augmented reasoning | ✅ | - | - |

**Key Files**:
- `patterns/react-pattern.py` - Reason, Act, Observe loop
- `patterns/reflection-pattern.py` - Self-improvement cycle
- `patterns/orchestration-pattern.py` - Multi-agent coordination
- `patterns/multiagent-pattern.py` - Parallel collaboration

---

### 🎨 Advanced Reasoning Techniques (6 examples)

Cutting-edge reasoning methods for complex problem-solving.

**Location**: [`techniques/reasoning/`](techniques/reasoning/)

| Technique | Description | File |
|-----------|-------------|------|
| **Chain-of-Thought (CoT)** | Step-by-step reasoning | `cot_example.py` |
| **Tree-of-Thought (ToT)** | Multi-path exploration | `tot_example.py` |
| **Self-Consistency (SC)** | Voting for reliability | `sc_example.py` |
| **Graph-of-Thought (GoT)** | Graph-based reasoning | `got_example.py` |
| **Least-to-Most (LTM)** | Decomposition strategy | `ltm_example.py` |
| **Plan-and-Solve** | Planning before execution | `plan_and_solve_example.py` |

**Use Cases**:
- Complex problem decomposition
- Multi-step reasoning
- Uncertainty handling
- Strategic planning

**Learn More**: [Tutorial 03: Advanced Reasoning](../tutorials/03-advanced-reasoning.ipynb)

---

### 🛡️ Production Middleware (8 examples)

Production-ready middleware for reliability, performance, and observability.

**Location**: [`middleware/`](middleware/)

| Middleware | Purpose | File |
|------------|---------|------|
| **Retry** | Exponential backoff | `retry_example.py` |
| **Circuit Breaker** | Fail-fast pattern | `circuit_breaker_example.py` |
| **Timeout** | Request deadlines | `timeout_example.py` |
| **Caching** | LRU cache with TTL | `caching_example.py` |
| **Metrics** | Prometheus metrics | `metrics_example.py` |
| **Rate Limiter** | Token bucket | `rate_limiter_example.py` |
| **Batching** | Request batching | `batching_example.py` |
| **Per-User Rate Limiter** | User-specific limits | `per_user_rate_limiter_example.py` |

**Key Features**:
- Stack multiple middleware
- Zero-configuration defaults
- Production-tested patterns
- Full observability

**Learn More**: [Tutorial 02: Production Patterns](../tutorials/02-production-patterns.ipynb)

---

### 🔧 Composition Patterns (4 examples)

Compose agents into complex workflows.

**Location**: [`composition/`](composition/)

- **Sequential**: Pipeline processing (`sequential_example.py`)
- **Parallel**: Concurrent execution (`parallel_example.py`)
- **Fallback**: Graceful degradation (`fallback_example.py`)
- **Conditional**: Dynamic routing (`conditional_example.py`)

**Advanced Compositions**: [`patterns/composition/`](patterns/composition/)
- `sequential-parallel.py` - Hybrid workflows
- `router-supervisor.py` - Routing + supervision

---

### 🌐 Transport Layer (2 examples)

Network protocols for distributed agents.

**Location**: [`transport/`](transport/)

- **gRPC**: High-performance RPC (`grpc_example.py`)
- **WebSocket**: Real-time bidirectional (`websocket_example.py`)

**Cross-Language**:
- [`e2e/cross-language-system/`](e2e/cross-language-system/) - Python ↔ Go ↔ TypeScript

---

### 🔌 LLM Adapters (9 examples)

Connect to any LLM provider.

**Locations**:
- Basic: [`adapters/`](adapters/)
- Integration: [`llm/`](llm/)

| Adapter | Provider | Files |
|---------|----------|-------|
| **OpenAI** | GPT-4, GPT-3.5 | `openai-basic.py`, `openai_example.py` |
| **Anthropic** | Claude 3.5 | `anthropic-basic.py`, `anthropic_example.py` |
| **Ollama** | Local models | `ollama-basic.py` |
| **LiteLLM** | 100+ providers | `litellm_providers.py` |
| **Remote** | HTTP API | `01_basic_remote_agent.py` |

**Advanced Features**:
- **Streaming**: `streaming_example.py`, `03_streaming.py`
- **Provider Swapping**: `swapping_providers.py`
- **Agent + LLM**: `agent_with_llm.py`

**Pattern Integration**:
- [`patterns/llm-integration/patterns-with-openai.py`](patterns/llm-integration/patterns-with-openai.py)
- [`patterns/llm-integration/patterns-with-anthropic.py`](patterns/llm-integration/patterns-with-anthropic.py)

---

### 🧰 Tools (3 examples)

Extend agents with external capabilities.

**Location**: [`tools/`](tools/)

- **Database**: SQL operations (`database_example.py`)
- **Search**: Web search integration (`search_example.py`)
- **OS Tools**: File system, shell commands (`os_tools_example.py`)

**Example**: [05_tool_usage.py](05_tool_usage.py)

---

### 🔐 Safety & Permissions (4 examples)

Secure agents with validation and permissions.

**Location**: [`safety/`](safety/)

1. **Input Validation**: Sanitize user input (`01_input_validation.py`)
2. **Output Validation**: Filter agent responses (`02_output_validation.py`)
3. **Permissions**: Fine-grained access control (`03_permissions.py`)
4. **Complete Stack**: Production security setup (`04_complete_safety_stack.py`)

**Features**:
- Content filtering
- PII detection
- Prompt injection defense
- Rate limiting
- Audit logging

---

### 🔒 Authentication (1 example)

Secure agent communications.

**Location**: [`auth/`](auth/)

- **Bearer Token**: HTTP authentication (`bearer_token_example.py`)

---

### 🧭 Routing (2 examples)

Intelligent request routing.

**Location**: [`routing/`](routing/)

- **Semantic Tool Selection**: Embedding-based routing (`semantic_tool_selection_example.py`)
- **Load Balancer**: Distribute requests (`load_balancer_example.py`)

---

### 💾 Memory (1 example)

Stateful agents with memory.

**Location**: [`memory/`](memory/)

- **Conversational Agent**: Context-aware conversations (`conversational_agent.py`)

**See also**: [`patterns/memory-hierarchy-pattern.py`](patterns/memory-hierarchy-pattern.py)

---

### 💰 Budget & Cost Tracking (2 examples)

Monitor and control LLM costs.

**Location**: [`budget/`](budget/)

- **Cost Tracking**: Monitor spending (`cost_tracking_demo.py`)
- **Extended Thinking**: Token budget management (`extended_thinking_demo.py`)

---

### 💾 Checkpointing (1 example)

Durable agents with state persistence.

**Location**: [`checkpointing/`](checkpointing/)

- **Durable Agent**: Save/restore agent state (`durable_agent_demo.py`)

---

### 📊 Observability (1 example)

Monitor agents with OpenTelemetry.

**Location**: [`observability/`](observability/)

- **Full Stack**: Tracing + Metrics + Logging (`observability_example.py`)

**Features**:
- Distributed tracing
- Prometheus metrics
- Structured logging
- Grafana dashboards

**Learn More**: [Tutorial 04: Deployment](../tutorials/04-deployment/)

---

### 🧪 Evaluation & Testing (3 examples)

Test, optimize, and compare agents.

**Location**: [`evaluation/`](evaluation/)

- **Evaluation Demo**: Quality metrics (`evaluation_demo.py`)
- **A/B Testing**: Compare agent versions (`ab_testing_demo.py`)
- **Optimization**: Hyperparameter tuning (`optimization_demo.py`)

**Learn More**: [Tutorial 05: Testing Patterns](../tutorials/05-testing-patterns.md)

---

### 🎭 Pattern Usage Examples (7 examples)

Real-world pattern usage.

**Location**: [`patterns/usage/`](patterns/usage/)

- `sequential-usage.py` - Sequential pipelines
- `parallel-usage.py` - Parallel execution
- `fallback-usage.py` - Error handling
- `router-usage.py` - Dynamic routing
- `supervisor-usage.py` - Supervised agents
- `collaborative-usage.py` - Agent collaboration
- `human-in-loop-usage.py` - Human feedback

---

### 🚀 Complete Applications (5 E2E examples)

Production-ready applications demonstrating full system architecture.

**Location**: [`e2e/`](e2e/)

#### 1. Code Review System
**Directory**: [`e2e/code-review/`](e2e/code-review/)

Multi-agent code review with specialized reviewers.

**Agents**:
- `correctness_agent.py` - Logic validation
- `performance_agent.py` - Performance analysis
- `security_agent.py` - Security scanning
- `style_agent.py` - Style checking
- `synthesis_agent.py` - Report generation

**Orchestration**: `review_orchestrator.py`

**Total**: 7 files

---

#### 2. Customer Support System
**Directory**: [`e2e/customer-support/`](e2e/customer-support/)

RAG-based support with escalation.

**Agents**:
- `classifier.py` - Intent classification
- `qa_agent.py` - Q&A with knowledge base
- `escalation_agent.py` - Human handoff
- `synthesis_agent.py` - Response generation

**Knowledge Base**: `vector_store.py`

**Total**: 7 files

---

#### 3. Research Assistant
**Directory**: [`e2e/research-assistant/`](e2e/research-assistant/)

Multi-source research with memory.

**Agents**: `research_agent.py`
**Memory**: `memory_store.py` (hierarchical memory)
**Tools**: `tool_registry.py` (search, summarize, analyze)

**Total**: 6 files

---

#### 4. LLM Optimizer
**Directory**: [`e2e/llm-optimizer/`](e2e/llm-optimizer/)

Automatic prompt and model optimization.

**Features**:
- Classification task optimization
- Model selection (GPT-4, Claude, etc.)
- Prompt tuning
- A/B testing

**Total**: 3 files

---

#### 5. Cross-Language System
**Directory**: [`e2e/cross-language-system/`](e2e/cross-language-system/)

Python orchestrator coordinating Go and TypeScript agents.

**Architecture**:
- Python: `orchestrator.py` (coordination)
- Go: gRPC services
- TypeScript: WebSocket services

**Total**: 3 files (Python)

---

### 🌍 Multi-Language Examples

#### Rust Examples (35 files) ✨
**Location**: [agenkit-rust/examples/](../agenkit-rust/examples/)

**Full pattern coverage** with evaluation framework:
- All 11 core patterns (ReAct, Reflection, Orchestration, etc.)
- 7 pattern usage examples
- 8 evaluation examples (A/B testing, Bayesian optimization, etc.)
- LLM adapters (OpenAI, Anthropic, Ollama, LiteLLM, Gemini, Bedrock)
- HTTP transport
- **WASM support!** `wasm_browser_agent.html` - Run agents in the browser

**Why Rust?**
- Memory safety without garbage collection
- Zero-cost abstractions
- Excellent performance
- Native WASM compilation for browser deployment

---

#### C++ Examples (42 files)
**Location**: [agenkit-cpp/examples/](../agenkit-cpp/examples/)

**Full pattern coverage** organized by category:
- All 11 core patterns
- Multiple adapters (OpenAI, Anthropic, etc.)
- Evaluation framework
- Integration examples
- Production-ready error handling

**Why C++?**
- Maximum performance for latency-sensitive applications
- Systems programming capabilities
- Existing C++ codebase integration
- Fine-grained memory control

---

#### Zig Examples (37 files)
**Location**: [agenkit-zig/examples/](../agenkit-zig/examples/)

**Modern systems programming** with full pattern coverage:
- All 11 core patterns
- Evaluation framework
- Observability integration
- LLM adapters
- Integration examples

**Why Zig?**
- Modern, simple syntax
- C interoperability
- Compile-time execution
- Memory safety with manual control

---

#### Go Examples (7 files)
**Location**: [`go/`](go/)

**Reasoning techniques**:
- Chain-of-Thought (CoT)
- Tree-of-Thought (ToT)
- Self-Consistency (SC)
- Graph-of-Thought (GoT)

**Full implementation**: [agenkit-go/examples/](../agenkit-go/examples/)

**Why Go?**
- Simple concurrency with goroutines
- Fast compilation
- Excellent for microservices
- Native gRPC support

---

#### TypeScript Examples (8 files)
**Location**: [`typescript/`](typescript/)

**Reasoning techniques + browser integrations**:

**Browser Examples**: [`browser/`](browser/)
- React: [`browser/react-example/`](browser/react-example/)
- Vue: [`browser/vue-example/`](browser/vue-example/)
- Svelte: [`browser/svelte-example/`](browser/svelte-example/)
- Astro: [`browser/astro-example/`](browser/astro-example/)

**Full implementation**: [agenkit-ts/examples/](../agenkit-ts/examples/)

**Why TypeScript?**
- Full-stack (Node.js + browser)
- Type safety for JavaScript
- Rich ecosystem
- Web framework integration

---

## 🗺️ Learning Paths

### Path 1: Beginner (1-2 hours)
Perfect for first-time users.

1. **Basic Agent** → `01_basic_agent.py`
2. **Sequential Pattern** → `02_sequential_pattern.py`
3. **Parallel Pattern** → `03_parallel_pattern.py`
4. **Tool Usage** → `05_tool_usage.py`
5. **LLM Integration** → `llm/openai_example.py`

**Next**: [Tutorial 01: Getting Started](../tutorials/01-getting-started.ipynb)

---

### Path 2: Production Engineer (2-3 hours)
For building production systems.

1. **Middleware Stack**:
   - `middleware/retry_example.py`
   - `middleware/circuit_breaker_example.py`
   - `middleware/caching_example.py`
   - `middleware/metrics_example.py`

2. **Safety**:
   - `safety/04_complete_safety_stack.py`

3. **Observability**:
   - `observability/observability_example.py`

4. **E2E Application**:
   - `e2e/customer-support/` (complete system)

**Next**: [Tutorial 02: Production Patterns](../tutorials/02-production-patterns.ipynb)

---

### Path 3: AI Researcher (2-3 hours)
For advanced reasoning and experimentation.

1. **Core Patterns**:
   - `patterns/react-pattern.py`
   - `patterns/reflection-pattern.py`
   - `patterns/orchestration-pattern.py`

2. **Reasoning Techniques**:
   - `techniques/reasoning/cot_example.py`
   - `techniques/reasoning/tot_example.py`
   - `techniques/reasoning/sc_example.py`

3. **Evaluation**:
   - `evaluation/ab_testing_demo.py`
   - `evaluation/optimization_demo.py`

**Next**: [Tutorial 03: Advanced Reasoning](../tutorials/03-advanced-reasoning.ipynb)

---

### Path 4: Full-Stack Developer (3-4 hours)
For multi-language and distributed systems.

1. **Transport Layer**:
   - `transport/grpc_example.py`
   - `transport/websocket_example.py`

2. **Adapters**:
   - `adapters/01_basic_remote_agent.py`
   - `adapters/03_streaming.py`

3. **Cross-Language**:
   - `e2e/cross-language-system/`

4. **Browser Integration**:
   - `browser/react-example/`

**Next**: [Tutorial 04: Deployment](../tutorials/04-deployment/)

---

## 🎯 Examples by Use Case

### Building a Chatbot?
1. `patterns/conversational-pattern.py` - Stateful conversations
2. `memory/conversational_agent.py` - Memory management
3. `llm/streaming_example.py` - Streaming responses
4. `e2e/customer-support/` - Complete support bot

---

### Code Analysis?
1. `patterns/react-pattern.py` - Reasoning about code
2. `patterns/reflection-pattern.py` - Self-improvement
3. `e2e/code-review/` - Multi-agent code review

---

### Research & Analysis?
1. `techniques/reasoning/cot_example.py` - Chain-of-Thought
2. `techniques/reasoning/tot_example.py` - Tree-of-Thought
3. `e2e/research-assistant/` - Full research system

---

### Production Deployment?
1. `middleware/retry_example.py` - Reliability
2. `middleware/circuit_breaker_example.py` - Fail-fast
3. `observability/observability_example.py` - Monitoring
4. `safety/04_complete_safety_stack.py` - Security
5. [Tutorial 04: Deployment](../tutorials/04-deployment/) - Docker + K8s

---

### Browser/WASM Deployment?
1. [Rust WASM Example](../agenkit-rust/examples/wasm_browser_agent.html) - Run agents in browser
2. [`browser/react-example/`](browser/react-example/) - React integration
3. [`browser/vue-example/`](browser/vue-example/) - Vue integration
4. [`browser/svelte-example/`](browser/svelte-example/) - Svelte integration

**Why WASM?**
- Run AI agents directly in the browser (no server required)
- Near-native performance
- Privacy-preserving (data never leaves device)
- Offline-capable applications
- Cross-platform (desktop, mobile, web)

---

## 🚀 Quick Start

### Run an Example

```bash
# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/examples

# Install dependencies
pip install agenkit

# Set API keys (for LLM examples)
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Run basic example
python 01_basic_agent.py

# Run pattern example
python patterns/react-pattern.py

# Run E2E application
cd e2e/customer-support
python main.py
```

### Explore by Category

```bash
# Patterns
cd patterns && ls *.py

# Reasoning techniques
cd techniques/reasoning && ls

# Middleware
cd middleware && ls

# E2E applications
cd e2e && ls -d */
```

---

## 🔗 Related Resources

### Documentation
- [Main Documentation](https://agenkit.dev)
- [API Reference](https://agenkit.dev/api/)
- [Pattern Library](../docs/patterns/)

### Tutorials
- [Getting Started](../tutorials/01-getting-started.ipynb) - First agent
- [Production Patterns](../tutorials/02-production-patterns.ipynb) - Middleware
- [Advanced Reasoning](../tutorials/03-advanced-reasoning.ipynb) - CoT, ToT, SC
- [Deployment](../tutorials/04-deployment/) - Docker, K8s, CI/CD
- [Testing Patterns](../tutorials/05-testing-patterns.md) - Testing guide

### Migration & Integration
- [LangChain ↔ Agenkit](../docs/integrations/langchain-integration.md)
- [CrewAI ↔ Agenkit](../docs/integrations/crewai-integration.md)
- [AutoGen ↔ Agenkit](../docs/integrations/autogen-integration.md)
- [Framework Integrations](../docs/integrations/)

### More Examples
- **Python**: [agenkit/examples/](../agenkit/examples/)
- **Go**: [agenkit-go/examples/](../agenkit-go/examples/)
- **TypeScript**: [agenkit-ts/examples/](../agenkit-ts/examples/)
- **Rust**: [agenkit-rust/examples/](../agenkit-rust/examples/)
- **C++**: [agenkit-cpp/examples/](../agenkit-cpp/examples/)
- **Zig**: [agenkit-zig/examples/](../agenkit-zig/examples/)

---

## 📊 Example Complexity Matrix

| Category | Beginner | Intermediate | Advanced | Production |
|----------|----------|--------------|----------|------------|
| **Patterns** | ✅ ReAct, Conversational | ✅ Orchestration, Multiagent | ✅ Planning, Autonomous | - |
| **Techniques** | - | ✅ CoT, SC | ✅ ToT, GoT, LTM | - |
| **Middleware** | ✅ Retry, Timeout | ✅ Circuit Breaker, Caching | ✅ Metrics, Rate Limiter | ✅ Complete Stack |
| **Transport** | - | ✅ gRPC, WebSocket | - | ✅ Cross-language |
| **E2E Apps** | - | - | ✅ Code Review, Support | ✅ Research, Optimizer |

---

## 🤝 Contributing

Found a bug or want to add an example?

1. **Report issues**: [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
2. **Discuss ideas**: [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)
3. **Contribute**: [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## 📝 Example Template

Creating your own example? Use this structure:

```python
"""
Brief description of what this example demonstrates.

Features:
- Feature 1
- Feature 2

Usage:
    python example_name.py
"""
from agenkit import Agent, Message

class YourAgent(Agent):
    @property
    def name(self) -> str:
        return "your-agent"

    async def process(self, message: Message) -> Message:
        # Your implementation
        return Message(role="assistant", content="response")

# Example usage
async def main():
    agent = YourAgent()
    response = await agent.process(Message(role="user", content="test"))
    print(response.content)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 🎉 Example Highlights

### Most Popular
1. `patterns/react-pattern.py` - ReAct loop
2. `llm/openai_example.py` - OpenAI integration
3. `middleware/retry_example.py` - Retry middleware

### Most Complex
1. `e2e/code-review/` - 7-file multi-agent system
2. `e2e/customer-support/` - RAG + vectorstore + escalation
3. `e2e/research-assistant/` - Memory hierarchy + tools

### Hidden Gems
1. `evaluation/optimization_demo.py` - Hyperparameter tuning
2. `routing/semantic_tool_selection_example.py` - Embedding routing
3. `budget/extended_thinking_demo.py` - Token budget management

---

**Ready to build?** Start with [01_basic_agent.py](01_basic_agent.py) or dive into [E2E applications](e2e/)!

Made with ❤️ by the Agenkit community
