# Agenkit v0.9.0 - First Public Release 🎉

**Release Date:** November 15, 2025  
**Status:** Production Ready, API Stabilizing  
**Website:** [https://agenkit.dev](https://agenkit.dev)  
**GitHub:** [https://github.com/scttfrdmn/agenkit](https://github.com/scttfrdmn/agenkit)

## 🌟 What is Agenkit?

**Agenkit is infrastructure, not a framework.**

Think of it like Express.js for Node or Flask for Python - it provides the foundational building blocks for building agent systems, but **you** decide what to build on top of it.

### The Problem We Solve

Building production AI agent systems is hard:
- LLMs fail unpredictably - you need circuit breakers, retries, and timeouts
- Prototypes work locally but break in production
- Understanding failures requires distributed tracing
- Python is great for prototyping, but you need Go/Rust for performance
- Every agent framework has its own incompatible abstractions

### The Agenkit Solution

Write your agents once in Python. Deploy them in Go for 18x better performance. Same interface, zero rewrites.

```python
# Day 1: Simple prototype
from agenkit import Agent, Message

class MyAgent(Agent):
    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Processed: {message.content}")

# Day 30: Production ready
from agenkit.middleware import RetryMiddleware, CircuitBreakerMiddleware

production_agent = RetryMiddleware(
    CircuitBreakerMiddleware(MyAgent())
)

# Day 90: Distributed system
from agenkit.adapters import HTTPServer
HTTPServer(production_agent, port=8080).start()
```

## ✅ Release Highlights

### Why 0.9.0 Instead of 1.0.0?

We're releasing as **0.9.0** because while the implementation is production-ready, we believe in the power of real-world feedback. This version number signals:

- ✅ **Ready for production use** - All features tested and validated
- 🔄 **API still evolving** - We may adjust based on your feedback
- 🎯 **Path to 1.0.0** - After 3-6 months of real-world usage, we'll commit to API stability

**In short:** Use it in production, but expect some API refinements based on community feedback before we lock in 1.0.0.

### Security: Zero Vulnerabilities
- ✅ **Python Dependencies:** Passed pip-audit - no known vulnerabilities
- ✅ **Go Dependencies:** Passed govulncheck - no vulnerabilities found
- ✅ **Secrets Scan:** Clean - no API keys or credentials in codebase
- ✅ **Container Security:** Non-root containers, dropped capabilities, read-only filesystems

### Testing: 867 Tests Passing
- ✅ **100% Individual Test Pass Rate** - All functionality verified working
- ✅ **76 Cross-Language Integration Tests** - Python ↔ Go compatibility validated
- ✅ **53 Chaos Engineering Tests** - Network failures, crashes, partial failures
- ✅ **37 Property-Based Tests** - Invariant validation with Hypothesis

### Production Infrastructure Ready
- ✅ **Development Status:** Beta (API Stabilizing)
- ✅ **Version:** All files updated to 0.9.0
- ✅ **Documentation:** Professional, clear positioning and architecture
- ✅ **Official Website:** Launched at agenkit.dev

## 📍 What This Means for You

### If you're evaluating Agenkit:
- ✅ All core features are complete and tested
- ✅ Production deployment infrastructure is ready
- 🔄 API may change based on feedback (we'll document all changes)

### If you're building with Agenkit:
- ✅ Safe to use in production (867 tests validate everything works)
- 🔄 Pin to 0.9.x in your dependencies for stability
- 📣 Your feedback shapes 1.0.0 - please share your experience!

### Path to 1.0.0:
1. **Now (0.9.0)** - First public release, seeking feedback
2. **Next 3-6 months** - Iterate based on real-world usage (0.10, 0.11, etc.)
3. **Future (1.0.0)** - API stability guarantee after validation

## 🚀 Key Features

### Minimal, Stable Interface

```python
class Agent:
    name: str                          # Unique identifier
    async def process(msg) -> Message  # Process messages
```

**That's it.** Everything else is optional.

### Production Middleware (Add What You Need)

```python
# Start simple
agent = MyAgent()

# Add retry logic
agent = RetryMiddleware(agent, max_attempts=3)

# Add circuit breaker
agent = CircuitBreakerMiddleware(agent)

# Stack as many as you need
```

### Cross-Language Support

- **Write once in Python, run anywhere**
- **Go implementation:** 18.5x faster than Python (0.055ms vs 1.02ms)
- **Same interface, same behavior**

## 📊 Performance

**Transport Overhead:** <1% of total time in realistic LLM workloads

**Language Performance:**
- Go HTTP: 18.5x faster than Python (0.055ms vs 1.02ms)
- Middleware overhead: <0.01% of request time

See [benchmarks/BASELINES.md](benchmarks/BASELINES.md) for details.

## 📚 Getting Started

```bash
# Install
pip install agenkit

# Create your first agent
python examples/01_basic_agent.py
```

Visit **[agenkit.dev](https://agenkit.dev)** for complete documentation!

---

**Agenkit v0.9.0** - Infrastructure for AI Agents | Released November 15, 2025  
**Next:** Share your feedback to help shape 1.0.0!
