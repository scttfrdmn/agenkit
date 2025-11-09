# agenkit Architecture Principles

**Core design decisions that make agenkit different.**

---

## Implementation Philosophy

**Production quality from day one.** This is not an experiment or prototype—it's infrastructure.

### Code Quality Standards

**Idiomatic, professional code:**
- Python: Type hints (mypy strict), async/await, proper exception handling
- Go: Idiomatic patterns, structured concurrency, comprehensive error handling
- Rust: Zero-cost abstractions, proper error propagation (Result<T, E>), no unsafe unless necessary

**Comprehensive testing:**
- Unit tests (every component, every edge case)
- Integration tests (cross-component interactions)
- Property-based tests (invariants hold under all inputs)
- Benchmarks (performance regression detection)

**Production readiness:**
- Proper error handling (no silent failures, informative errors)
- Input validation (fail fast on invalid input)
- Security by default (no SQL injection, XSS, command injection patterns)
- Observable (logging, metrics, tracing hooks)

**Documentation:**
- API docs (every public interface)
- Architecture docs (design decisions, trade-offs)
- Examples (real-world use cases)
- Migration guides (from existing frameworks)

### Why This Matters

**Trust is prerequisite for adoption:**
- Frameworks won't build on toy code
- Production systems need production quality
- Reference implementations must be reference quality
- 40-year professionals can spot shortcuts

**Quality compounds:**
- Good code → Easy to understand → Easy to extend → More adoption
- Bad code → Hard to understand → Hard to extend → Abandonware

### The Bar

Code quality that would pass review at:
- High-performance systems teams (low-level efficiency)
- Infrastructure teams (reliability, observability)
- Security teams (no vulnerabilities, safe defaults)
- Open source projects (readable, maintainable, documented)

**Not "good enough for demo"—good enough for production.**

---

## 1. Component-Based, Not Monolithic

### Framework Reimplementations Are Component Libraries

❌ **Don't do this:**
```python
# Monolithic - all or nothing
from langchain_classic import LangChainFramework
framework = LangChainFramework(...)  # Get everything
```

✅ **Do this:**
```python
# Modular - take what you need
from langchain_classic.agents import ReActAgent        # Just this (200 lines)
from langchain_classic.prompts import PromptTemplate  # Just this (50 lines)
from haystack_classic.retrieval import Reranker       # Mix frameworks

# Build your own combination
```

### Why This Matters

**For users:**
- Use just what you need (no bloat)
- Mix components from different frameworks
- Build custom frameworks from components

**For frameworks:**
- Your components can be reused individually
- Users aren't locked into "all or nothing"
- Natural path to gradual adoption

### Implementation

Each framework reimplementation is structured as independent components:

```
langchain-classic/
├── prompts.py        # Independent - 50 lines
├── memory.py         # Independent - 50 lines
├── chains.py         # Independent - 100 lines
├── agents.py         # Independent - 200 lines
├── retrieval.py      # Independent - 100 lines
└── parsers.py        # Independent - 50 lines

# Each file is self-contained and usable alone
```

**Key principle:** Every component is independently useful.

---

## 2. Reference Implementations, Not Mandates

### Protocol Adapters Are Suggestions

❌ **Don't do this:**
```python
# Forced to use our implementation
from agenkit.protocols.mcp import MCPAdapter  # Only option
```

✅ **Do this:**
```python
# Choose: ours, forked, or custom
from agenkit_mcp_py import MCPAdapter      # Use ours
from agenkit_mcp_go import MCPAdapter      # Use high-performance version
from my_custom_mcp import MCPAdapter       # Use your custom implementation

# All implement the same interface
```

### Why This Matters

**Reduces NIH (Not Invented Here) syndrome:**
- "We can't use agenkit because the MCP adapter doesn't X"
- Response: "Write your own adapter that does X. Same interface."

**Enables optimization:**
- Python reference: Easy to understand, modify, prototype
- Go/Rust: High performance when needed
- Custom: Optimized for your specific workload

**No vendor lock-in:**
- Don't like our adapter? Replace it.
- Interface is standard, implementation is yours.

### What agenkit Provides

```
Protocol Adapter Specification:
├── Interface definition      # Required contract
├── Reference implementations # Python, Go, Rust
├── Test suite               # Verify compliance
└── Documentation            # How to build your own
```

**Key principle:** Adapters are implementations, not specifications.

---

## 3. Three Layers of Extensibility

### The Stack

```
┌─────────────────────────────────────────────┐
│  Your Innovation Layer                      │
│  - Custom protocol adapters                 │
│  - Custom framework components              │
│  - Novel framework combinations             │
│  → YOU own this, YOU optimize this          │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Reference Implementation Layer             │
│  - agenkit protocol adapters (Py, Go, Rust) │
│  - Framework components (LangChain, etc.)   │
│  - Impossible frameworks (Composer, etc.)   │
│  → WE provide these, YOU can fork/replace   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Core Interface Layer (STABLE)              │
│  - Agent, Tool, Message interfaces          │
│  - Pattern interfaces                       │
│  - Observability interfaces                 │
│  → STANDARD contract, rarely changes        │
└─────────────────────────────────────────────┘
```

### Layer 1: Core Interfaces (Standard, Stable)

**What it is:**
- Agent, Tool, Message, Pattern interfaces
- The contract that everything builds on
- Changes rarely (semantic versioning)

**Your commitment:**
- Implement these interfaces
- Your code works with all agenkit-compatible components

**Our commitment:**
- Keep interfaces minimal
- Version strictly (no surprise breaking changes)
- Provide migration paths for major versions

### Layer 2: Reference Implementations (Provided, Forkable)

**What we provide:**
- Protocol adapters (MCP, A2A, HTTP)
- Framework components (LangChain, CrewAI, AutoGen, Haystack)
- Impossible frameworks (Composer, A/B Test, Migrator, Multi-Perspective)

**Your options:**
- Use as-is (Python reference)
- Use high-performance version (Go/Rust)
- Fork and modify
- Write your own from scratch

**The philosophy:**
> "Here are good implementations. But you can always do better for your use case."

### Layer 3: Your Innovations (Unlimited)

**This is where you differentiate:**
- Custom protocol adapters (optimized for your workload)
- Custom components (your secret sauce)
- Novel frameworks (unique combinations)

**The enabler:**
- Because Layer 1 is standard, your innovations are compatible
- Because Layer 2 is forkable, you can build on proven code
- Because both are extensible, you're never blocked

---

## 4. Composition Over Inheritance

### Mix and Match Components

```python
# Anti-pattern: Inherit from one framework
class MyAgent(LangChainAgent):  # Locked into LangChain
    pass

# Pattern: Compose from multiple frameworks
class MyAgent(Agent):  # Implements agenkit interface
    def __init__(self):
        self.reasoning = LangChainReActAgent(...)  # Best reasoning
        self.retrieval = HaystackRetriever(...)     # Best retrieval
        self.coordination = CrewAICoordinator(...)  # Best coordination

    async def process(self, message: Message) -> Message:
        # Your orchestration logic
        pass
```

### Why This Matters

**Inheritance creates lock-in:**
- Tied to one framework's design decisions
- Can't easily switch or mix

**Composition enables flexibility:**
- Use best component from each framework
- Replace individual pieces without rewriting everything
- Your logic, their components

---

## 5. Escape Hatches Everywhere

### Never Trap Users

Every component provides `.unwrap()`:

```python
# Wrap native object in agenkit interface
langchain_agent = LangChainAgent(...)
agenkit_agent = LangChainAgentWrapper(langchain_agent)

# Use with agenkit patterns
pipeline = SequentialPattern([agenkit_agent, other_agent])

# ESCAPE HATCH: Get native object back
native = agenkit_agent.unwrap()
native.langchain_specific_method()  # Use framework-specific features
```

### Why This Matters

**Trust through transparency:**
- "You're not trapped in agenkit"
- "You can always get your native objects back"
- "Use agenkit because it's useful, not because you're locked in"

**Gradual adoption:**
- Wrap one component at a time
- Use framework-specific features when needed
- Unwrap when agenkit doesn't fit

---

## 6. Impossible Frameworks as Proof

### Show, Don't Tell

❌ **Weak argument:**
> "Frameworks should share primitives because... reasons."

✅ **Strong argument:**
> "Here are 4 frameworks that are IMPOSSIBLE without shared primitives:
> - Composer: Use best from each framework
> - A/B Tester: Scientific comparison
> - Migrator: Risk-free framework migration
> - Multi-Perspective: Ensemble reasoning
>
> These are impossible today. With agenkit, they're inevitable."

### Why This Matters

**Demonstrates unique value:**
- Not just "we can match frameworks"
- But "we enable entirely new categories"

**Creates demand:**
- Developers want these tools
- "Why can't I use Framework Composer with real LangChain?"
- Pressure on frameworks to adopt

**Shows network effects:**
- Value compounds with each compatible framework
- 2 frameworks → 1 combination
- 4 frameworks → 6 combinations
- 10 frameworks → 45 combinations

---

## The Complete Picture

### What agenkit IS

✅ **Standard interfaces** - Agent, Tool, Message, Pattern
✅ **Core patterns** - Sequential, Parallel, Router
✅ **Reference implementations** - Protocol adapters, framework components
✅ **Impossible frameworks** - Composer, A/B Test, Migrator, Multi-Perspective
✅ **Component libraries** - Mix and match pieces
✅ **Extensibility model** - Fork, replace, or write your own
✅ **Escape hatches** - Unwrap to native objects anytime

### What agenkit is NOT

❌ **Another monolithic framework** - It's a component toolkit
❌ **Opinionated** - It's primitives, you add opinions
❌ **Vendor lock-in** - Escape hatches everywhere
❌ **Mandatory implementations** - Reference implementations, not mandates
❌ **Finished product** - Extensibility is the product

---

## Design Principles Summary

1. **Component-based** - Use pieces, not monoliths
2. **Reference implementations** - Suggestions, not mandates
3. **Three-layer extensibility** - Standard interfaces, reference implementations, your innovations
4. **Composition over inheritance** - Mix and match, don't lock in
5. **Escape hatches** - Unwrap to native objects anytime
6. **Impossible frameworks** - Demonstrate unique value through novel capabilities

---

**These principles aren't arbitrary—they're strategic.**

They eliminate objections:
- "I need custom adapters" → Write your own
- "I'm locked in" → Escape hatches everywhere
- "I need just one piece" → Components are independent
- "Why should I care" → Impossible frameworks

They enable adoption:
- New frameworks: Don't reinvent primitives
- Established frameworks: Gradual migration, no rewrite
- Developers: Mix best-of-breed
- Organizations: No vendor lock-in

They create network effects:
- More compatible frameworks → More combinations
- More combinations → More value
- More value → More adoption
- More adoption → De facto standard

---

**This is agenkit. Extensible by design. Compatible by default. Locked-in never.**
