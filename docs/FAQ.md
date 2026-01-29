# Frequently Asked Questions (FAQ)

**Quick answers to common questions about Agenkit**

---

## General Questions

### What is Agenkit?

Agenkit is a cross-language toolkit for building production-ready AI agent systems. It provides:
- **18 core patterns** for agent orchestration (documented in the [Agent Patterns Book](../../agent-patterns-book))
- **6 language implementations** with 100% feature parity (Python, Go, TypeScript, Rust, C++, Zig)
- **Production middleware** (retry, circuit breaker, timeout, rate limiting)
- **Full observability** (OpenTelemetry, distributed tracing)

### Is Agenkit a framework or a toolkit?

**Toolkit.** Agenkit provides composable building blocks you can use à la carte. You're not locked into a specific architecture or opinionated workflow. Start with just the core `Agent` interface and add middleware as needed.

### How is Agenkit different from LangChain/AutoGPT/CrewAI?

| Feature | Agenkit | LangChain | AutoGPT | CrewAI |
|---------|---------|-----------|---------|--------|
| **Philosophy** | Toolkit (composable) | Framework (opinionated) | Framework (autonomous) | Framework (multi-agent) |
| **Languages** | 6 (100% parity) | Python, TypeScript | Python | Python |
| **Core Interface** | 1 method (process) | Complex chains | Complex | Complex |
| **Production Ready** | ✅ Yes | ⚠️ Partial | ❌ No | ⚠️ Partial |
| **Observability** | ✅ Full (OpenTelemetry) | ⚠️ Limited | ❌ None | ⚠️ Limited |
| **Learning Curve** | Low (1 hour) | High (days) | High (days) | Medium (hours) |

**Use Agenkit if:** You need production reliability, cross-language support, or want to build on simple primitives.

**Use LangChain if:** You want pre-built chains and don't need multi-language support.

### What are the 18 core patterns?

See the **[Agent Patterns Book](../../agent-patterns-book)** for comprehensive coverage. Quick reference:

**Core Patterns**: Task, Conversational, ReAct, Planning, Reflection, ReasoningWithTools, AgentsAsTools, Memory

**Composition Patterns**: Sequential, Parallel, Router, Fallback, Orchestration, Supervisor, Collaborative, HumanInLoop, MultiAgent, Autonomous

---

## Language Choice

### Which language should I use?

**Start with Python:**
- Fastest prototyping
- Rich ML/AI ecosystem
- Most documentation/examples

**Move to Go for production:**
- 18x faster than Python
- Better for distributed systems
- Production-grade error handling

**Use TypeScript for:**
- Full-stack applications
- Browser-based agents
- Node.js backend

**Use Rust/C++/Zig for:**
- Maximum performance
- Systems programming
- Embedded systems

### Can I mix languages in one project?

**Yes!** Agenkit is designed for polyglot systems:

```
┌─────────────┐     HTTP      ┌─────────────┐
│   Python    │ ◄────────────► │     Go      │
│   Agent     │                │   Agent     │
│  (Prototype)│                │ (Production)│
└─────────────┘                └─────────────┘
```

All languages use the same `Message` format and can communicate via HTTP/gRPC/WebSocket.

### Is feature parity really 100%?

Yes. All 6 languages have:
- ✅ All 18 patterns
- ✅ All 6 LLM adapters (OpenAI, Anthropic, Ollama, Bedrock, Gemini, LiteLLM)
- ✅ All middleware (retry, circuit breaker, timeout, rate limiting)
- ✅ Full observability (OpenTelemetry, distributed tracing)

See [Status](../README.md#status) in README for test counts per language.

---

## Getting Started

### How long does it take to learn Agenkit?

**Timeline:**
- 15-30 min: First agent working
- 1-2 hours: Understand core patterns
- 1 day: Production-ready system

**Learning path:**
1. [Getting Started Guide](getting-started/) for your language (30 min)
2. [Agent Patterns Book](../../agent-patterns-book) - 18 patterns (2-3 hours)
3. [Advanced Architectures](ADVANCED_ARCHITECTURES.md) - Compositions (1 hour)
4. [Examples](../examples/) - Learn by doing (1 hour)

### Do I need to know all 6 languages?

**No.** Pick one language and stick with it. The cross-language support is for teams or migration, not individuals.

Most users:
- Learn **one** language deeply
- Reference other languages when needed

### What if I'm new to AI agents?

Perfect! Agenkit is designed for learning. Start here:

1. **Read:** [What is an Agent?](../../agent-patterns-book/chapters/01-what-is-an-agent.md) (15 min)
2. **Build:** Follow your language's [Getting Started Guide](getting-started/) (30 min)
3. **Learn patterns:** [Agent Patterns Book](../../agent-patterns-book) - Start with Task, ReAct, Sequential (1 hour)

---

## Patterns

### When should I use each pattern?

Quick decision tree:

**Need to process one item?** → Task Pattern  
**Need a conversation?** → Conversational Pattern  
**Need tools/reasoning?** → ReAct Pattern  
**Need known workflow?** → Planning Pattern  
**Need quality improvement?** → Reflection Pattern  
**Need to run steps in order?** → Sequential Pattern  
**Need to run tasks concurrently?** → Parallel Pattern  
**Need to route to specialists?** → Router Pattern  
**Need failure handling?** → Fallback Pattern  
**Need team coordination?** → Supervisor Pattern

See [Agent Patterns Book](../../agent-patterns-book/PATTERN_REFERENCE_GUIDE.md) for complete decision guide.

### Should I use ReAct or Planning?

**Use ReAct when:**
- Tool selection not obvious
- Need adaptation based on discoveries
- Transparency important (debugging)

**Use Planning when:**
- Workflow predictable
- Cost matters (5-10× cheaper)
- Steps known upfront

**Comparison:**
| Aspect | ReAct | Planning |
|--------|-------|----------|
| Cost | $0.45 | $0.04 |
| Latency | 45s | 10s |
| Adaptability | High | Low |
| Transparency | High | Medium |

### Can I combine patterns?

**Yes!** See [Advanced Architectures](ADVANCED_ARCHITECTURES.md) for 8 common compositions:

- ReAct + Fallback = Reliable research agent
- Planning + Sequential = Adaptive ETL pipeline
- Supervisor + Parallel Workers = Coordinated research team
- Router + Specialists = Smart customer support

**Rule of thumb:** Start with one pattern, add complexity only when needed.

### What's the difference between a pattern and middleware?

**Patterns** = How agents orchestrate work (ReAct, Sequential, etc.)  
**Middleware** = Cross-cutting concerns (retry, timeout, rate limiting)

```python
# Pattern: How agents work together
agent = SequentialAgent([ResearchAgent(), SummarizerAgent()])

# Middleware: How agents handle failures
agent = RetryDecorator(agent, max_attempts=3)
agent = TimeoutDecorator(agent, timeout_ms=30000)
```

You can combine both!

---

## Production

### Is Agenkit production-ready?

**Yes.** v0.50.0 includes:
- ✅ 2,100+ tests (100% passing)
- ✅ Full observability (OpenTelemetry)
- ✅ Production middleware (retry, circuit breaker, timeout, rate limiting)
- ✅ Deployment manifests (Docker + Kubernetes)
- ✅ Security hardening (non-root containers, RBAC, audit logging)

Many teams use Agenkit in production today.

### How do I deploy Agenkit agents?

**Option 1: Docker (simplest)**
```bash
docker-compose up
```

**Option 2: Kubernetes (scalable)**
```bash
kubectl apply -f deploy/kubernetes/
```

**Option 3: Serverless (AWS Lambda, etc.)**
```python
from agenkit.patterns import Task

async def lambda_handler(event, context):
    async with Task(agent, timeout_ms=30000) as task:
        result = await task.call(message)
    return result
```

See [Deployment Guide](../deploy/README.md).

### How do I monitor agents in production?

**Built-in observability:**

```python
from agenkit.observability import configure_observability

configure_observability(
    service_name="my-agent",
    exporter_type="jaeger",
    jaeger_endpoint="http://localhost:14268/api/traces"
)

# Every agent.process() call automatically traced
```

**View traces:** http://localhost:16686 (Jaeger UI)

Includes:
- Request/response tracing
- LLM call timing
- Error tracking
- W3C Trace Context propagation

### How do I handle secrets (API keys)?

**Never hardcode secrets.** Use environment variables:

```python
import os

llm = OpenAILLM(
    api_key=os.getenv("OPENAI_API_KEY"),  # ✅ From environment
    model="gpt-4-turbo"
)
```

**In Kubernetes:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: llm-secrets
stringData:
  OPENAI_API_KEY: sk-...
```

**In Docker:**
```bash
docker run --env-file .env agenkit
```

---

## Performance

### How fast is Agenkit?

**Transport overhead:** <1% of total time in realistic LLM workloads

**Language performance (HTTP transport):**
- Python: 1.02ms per request (baseline)
- Go: 0.055ms per request (18.5× faster)
- Rust: 0.051ms per request (20× faster)
- C++: 0.041ms per request (25× faster)
- Zig: 0.046ms per request (22× faster)

**Real bottleneck:** LLM API calls (500ms - 5s), not Agenkit overhead.

### Should I optimize my agents?

**Profile first:**

```python
import time

start = time.time()
result = await agent.process(message)
print(f"Total time: {time.time() - start:.2f}s")

# If >90% is LLM time, don't optimize Agenkit
# If significant middleware overhead, optimize composition
```

**Common optimizations:**
1. Use Parallel pattern for independent tasks
2. Reduce retry attempts (3 is usually enough)
3. Use Planning instead of ReAct when possible (5-10× cheaper)
4. Switch to Go/Rust for high-throughput services

### Can Agenkit handle 1000s of requests/second?

**Yes,** especially with Go/Rust/C++/Zig:

- **Horizontal scaling:** Deploy multiple pods in Kubernetes
- **Rate limiting:** Built-in token bucket rate limiter
- **Circuit breaker:** Prevent cascading failures
- **Caching:** LRU cache with TTL for repeated requests

**Bottleneck:** Usually the LLM provider's rate limits, not Agenkit.

---

## Costs

### How much does Agenkit cost?

**Agenkit itself:** Free and open source (Apache 2.0 license)

**Costs you'll pay:**
- **LLM API calls:** $0.01 - $0.10 per 1K tokens (varies by provider/model)
- **Infrastructure:** Cloud hosting costs (if deploying remotely)

**Cost optimization tips:**
1. Use Planning pattern instead of ReAct (5-10× cheaper)
2. Cache repeated requests
3. Use cheaper models for simple tasks
4. Set max_tokens limits

### Which pattern is most cost-effective?

**From cheapest to most expensive:**

1. **Tool** - Free (no LLM calls)
2. **Task/Planning** - 1-2 LLM calls
3. **Sequential** - N LLM calls (N = stages)
4. **Reflection** - 3-5 LLM calls (iterative refinement)
5. **ReAct** - 6+ LLM calls (2 per step)

**Example costs** (GPT-4 Turbo at $0.01/1K input tokens):
- Task: $0.05
- Planning: $0.04
- ReAct (3 steps): $0.45
- Reflection (3 iterations): $0.15

See [Pattern Book](../../agent-patterns-book/PATTERN_REFERENCE_GUIDE.md#cost--latency-reference) for detailed comparison.

---

## Migration

### Can I migrate from LangChain to Agenkit?

**Yes.** Common migration paths:

**LangChain Chain → Agenkit Sequential:**
```python
# LangChain
chain = LLMChain(...) | TransformChain(...) | OutputChain(...)

# Agenkit
agent = SequentialAgent([
    ProcessorAgent(llm),
    TransformAgent(llm),
    OutputAgent(llm)
])
```

**LangChain Agent → Agenkit ReAct:**
```python
# LangChain
agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)

# Agenkit
agent = ReActAgent(llm, tools, max_iterations=5)
```

### Can I migrate from Python to Go?

**Yes.** Agenkit maintains API consistency:

**Python:**
```python
class MyAgent(Agent):
    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content=f"Processed: {message.content}")
```

**Go:**
```go
type MyAgent struct{}

func (a *MyAgent) Process(ctx context.Context, msg *Message) (*Message, error) {
    return &Message{
        Role:    "assistant",
        Content: fmt.Sprintf("Processed: %s", msg.Content),
    }, nil
}
```

See [Migration Guides](MIGRATION_INDEX.md) for detailed examples.

---

## Testing

### How do I test my agents?

**Unit tests:**
```python
import pytest

@pytest.mark.asyncio
async def test_agent():
    agent = MyAgent()
    message = Message(role="user", content="test")
    
    result = await agent.process(message)
    
    assert result.role == "assistant"
    assert "test" in result.content
```

**Integration tests with mocks:**
```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_agent_with_llm():
    # Mock LLM
    llm = AsyncMock()
    llm.complete.return_value = Message(role="assistant", content="mocked")
    
    agent = MyAgent(llm)
    result = await agent.process(message)
    
    assert result.content == "mocked"
    llm.complete.assert_called_once()
```

### Should I test with real LLMs?

**For unit tests:** No, use mocks (faster, deterministic, free)

**For integration tests:** Yes, use real LLMs occasionally:
- Test end-to-end flows
- Validate prompt engineering
- Catch API changes

**Best practice:** 90% mocked tests, 10% real LLM tests.

---

## Support

### Where can I get help?

1. **Documentation:**
   - [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues
   - [Getting Started Guides](getting-started/) - Language-specific
   - [Agent Patterns Book](../../agent-patterns-book) - Pattern details

2. **Community:**
   - GitHub Issues: https://github.com/yourusername/agenkit/issues
   - Discussions: https://github.com/yourusername/agenkit/discussions

3. **Contributing:**
   - See [Contributing Guide](../.github/CONTRIBUTING.md)
   - Good first issues: https://github.com/yourusername/agenkit/labels/good%20first%20issue

### How can I contribute?

We welcome contributions!

**Ways to contribute:**
- Report bugs or request features (GitHub Issues)
- Improve documentation
- Add examples
- Fix bugs
- Add new patterns or middleware

See [Contributing Guide](../.github/CONTRIBUTING.md) for details.

### Is there commercial support?

Agenkit is open source (Apache 2.0). Commercial support may be available in the future. For now:
- Community support via GitHub Discussions
- Bug reports via GitHub Issues
- Professional services from contributors (contact maintainers)

---

## Roadmap

### What's coming in v1.0?

**Target:** Q1 2026

**Focus areas:**
- Cross-language equivalence tests
- Performance benchmarks
- API stability guarantees
- More examples and tutorials

See [ROADMAP.md](../ROADMAP.md) for details.

### Can I use Agenkit in production before v1.0?

**Yes!** Many teams use v0.50.0 in production today. The API is stable and breaking changes are rare (and clearly documented when they happen).

Pre-1.0 versions are production-ready but may have occasional breaking changes as we refine the API.

---

**Version**: v0.50.0  
**Last Updated**: January 28, 2026

**Have more questions?** Ask in [GitHub Discussions](https://github.com/yourusername/agenkit/discussions)
