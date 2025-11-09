# agenkit-frameworks

**Every framework, one toolkit.**

Reimplementations of major agent frameworks on agenkit. Not because the originals are bad, but to show that 90% of every framework is the same primitives—and those primitives should be standardized.

---

## What This Is

Educational reimplementations of popular agent frameworks, built on agenkit primitives. Each implementation:

- **Modular components** - Use the whole framework or just one piece
- **Independently useful** - Each component works standalone
- **Captures the core patterns** that users actually use
- **Shows what's fundamental** vs what's abstraction
- **Provides migration paths** for moving to agenkit
- **Mix-and-match friendly** - Combine components from different frameworks
- **Is intentionally readable** (not feature-complete)

**Key architectural principle:** These are **component libraries**, not monolithic frameworks. Take what you need, leave the rest.

## The Implementations

### LangChain Classic (~500 lines, 6 components)

**Component-based architecture** - Use the whole thing or just the pieces you want:

```python
# Option 1: Use the whole framework
from langchain_classic import (
    PromptTemplate,
    LLMChain,
    ConversationMemory,
    ReActAgent,
    RetrievalQA
)

# Option 2: Import just what you need
from langchain_classic.agents import ReActAgent       # Just the ReAct agent (200 lines)
from langchain_classic.prompts import PromptTemplate  # Just prompt templates (50 lines)

# Option 3: Mix with other frameworks
from langchain_classic.agents import ReActAgent
from haystack_classic.retrieval import Retriever
from crewai_classic.crew import Crew

# Each component is independently useful
```

**Components (500 lines total):**

| Component | Lines | What it does | Use independently |
|-----------|-------|-------------|-------------------|
| **prompts.py** | ~50 | Template formatting | ✅ Yes - just need string formatting |
| **memory.py** | ~50 | Conversation history | ✅ Yes - just need message storage |
| **chains.py** | ~100 | Sequential processing | ✅ Yes - basic agent chaining |
| **agents.py** | ~200 | ReAct reasoning | ✅ Yes - tool-using agent |
| **retrieval.py** | ~100 | Basic RAG | ✅ Yes - retrieve + generate |
| **parsers.py** | ~50 | Output parsing | ✅ Yes - parse JSON/lists from text |

**Example: Use just the ReAct agent**
```python
from langchain_classic.agents import ReActAgent
from agent_toolkit.patterns import SequentialPattern

# Use LangChain's ReAct agent with toolkit patterns
agent = ReActAgent(llm=my_llm, tools=[search, calculator])

# Combine with other agents
pipeline = SequentialPattern([
    agent,                    # LangChain ReAct
    your_custom_agent,        # Your code
    haystack_reranker         # Haystack component
])
```

**What's not included:**
- 500+ integration adapters (that's ecosystem value)
- Complex chain types (framework-specific)
- Legacy APIs (backward compatibility burden)

**The point:** The core that everyone uses is simple (500 lines, 6 components). The value is in the ecosystem and opinions, not the abstractions.

---

### CrewAI Classic (~300 lines)

```python
from crewai_classic import Crew, Agent, Task

# Role-based agent teams
# Built on agenkit
# 300 lines vs 20,000
```

**What's included:**
- Agent roles (metadata + capabilities)
- Task definitions (structured messages)
- Crew orchestration (sequential/hierarchical patterns)
- Result aggregation

**What's not included:**
- Custom task types
- Complex delegation strategies
- Framework-specific tooling

**The point:** Roles are metadata. Tasks are messages. Crews are patterns. The value is in the team metaphor.

---

### AutoGen Classic (~400 lines)

```python
from autogen_classic import ConversableAgent, GroupChat

# Conversation-driven agents
# Built on agenkit
# 400 lines vs 25,000
```

**What's included:**
- Conversable agents (message exchange)
- Group chat (multi-agent conversations)
- Termination conditions
- Human-in-the-loop

**What's not included:**
- Advanced code execution
- Complex negotiation
- Framework-specific features

**The point:** Conversations are message exchanges. Groups are routing. The value is in the conversation model.

---

### Haystack Classic (~600 lines)

```python
from haystack_classic import Pipeline, Component

# Pipeline-based RAG
# Built on agenkit
# 600 lines vs 30,000
```

**What's included:**
- Pipeline orchestration (sequential/conditional)
- Component abstraction (agents as components)
- Basic RAG patterns (retrieve + generate)
- Document processing

**What's not included:**
- 50+ vector DB integrations
- Advanced retrieval strategies
- Production features

**The point:** Pipelines are patterns. Components are agents. The value is in the RAG expertise and integrations.

---

## Why We Did This

This is strategic provocation—but not for provocation's sake. It's the most effective way to demonstrate the need for shared primitives.

### The Strategy

**Instead of saying:** "Frameworks should share primitives"
**We show:** "We rebuilt your framework in 500 lines on shared primitives"

**Instead of claiming:** "Most framework code is duplicated effort"
**We prove:** "Here's LangChain: 500 lines of core, 49,500 lines of other stuff"

**Instead of arguing:** "The ecosystem is fragmented"
**We demonstrate:** "Here's four frameworks interoperating because they share primitives"

### What This Achieves

**1. Proof**
- Can agenkit support framework-level abstractions? Yes, we rebuilt them.
- Is the layer right? If major frameworks fit on it, yes.

**2. Education**
- What do frameworks actually do? Read the 500-line version.
- What's fundamental vs framework-specific? Now it's obvious.
- How do different frameworks approach the same problems? Compare implementations.

**3. Migration Paths**
- Moving from Framework X to agenkit? Start with Framework X Classic.
- See exactly how patterns map to primitives.
- Migrate gradually, component by component.

**4. Constructive Pressure**
- Framework authors: "What are those other 49,500 lines doing?"
- Honest answer: "Integrations, ecosystem, convenience, production features"
- Follow-up: "That's valuable! Focus on that instead of reinventing primitives"

**5. Conversation Shift**
- From: "Which framework should I use?" (divisive)
- To: "Why are we all reinventing primitives?" (unifying)

### The Respect Implicit in This

Reimplementing something requires deep understanding. We're showing:
- We studied your framework thoroughly
- We understand the patterns you identified
- We respect the problems you solved
- We're proposing where to standardize and where to differentiate

This isn't "your framework is bad"—it's "you solved real problems, now let's solve them together."

---

## What Each Implementation Shows

| Framework | Core Pattern | Lines | What's Fundamental | What's Added Value |
|-----------|--------------|-------|-------------------|-------------------|
| LangChain | Chains | ~500 | Sequential processing, tool calling | Ecosystem, integrations, convenience |
| CrewAI | Teams | ~300 | Agent coordination, role-based patterns | Team metaphor, task templates |
| AutoGen | Conversations | ~400 | Message exchange, multi-agent chat | Conversation model, negotiation |
| Haystack | Pipelines | ~600 | DAG orchestration, components | RAG expertise, vector DB integrations |

**The pattern:** They're all doing agent coordination with different metaphors. The primitives are the same.

---

## Beyond Reimplementation: The Impossible Frameworks

Even more powerful than showing "we can do what you do" is showing **"we can do what you CAN'T do."**

These frameworks are **impossible** without shared primitives:

### 1. Composer Framework (~200 lines)

**What it does:** Combines the best component from each framework into one system.

```python
from agenkit_composer import FrameworkComposer

composer = FrameworkComposer({
    "retrieval": "haystack",      # Best RAG
    "reasoning": "langchain",     # Best ReAct
    "coordination": "crewai",     # Best teams
    "conversations": "autogen"    # Best chat
})

result = await composer.execute("Research quantum computing")
```

**Why impossible without agenkit:** Frameworks don't interoperate. You can't pick Haystack's retrieval, LangChain's reasoning, and CrewAI's coordination. But you should be able to.

**The message:** "Best-of-breed is better than any single framework."

### 2. Framework A/B Tester (~150 lines)

**What it does:** Scientific comparison of frameworks on your workload.

```python
from agenkit_abtest import FrameworkABTest

ab_test = FrameworkABTest(
    frameworks=["langchain-classic", "haystack-classic"],
    metric="response_quality",
    sample_size=100
)

results = await ab_test.run("Compare RAG performance")
print(f"Winner: {results.winner}")
```

**Why impossible without agenkit:** Frameworks have different APIs, different data formats. Can't run identical experiments.

**The message:** "Choose frameworks based on data, not marketing."

### 3. Framework Migration Tool (~300 lines)

**What it does:** Gradual, risk-free migration between frameworks.

```python
from agenkit_migrate import GradualMigration

migration = GradualMigration(
    source="langchain-classic",
    target="haystack-classic"
)

# Start with 90% LangChain, 10% Haystack
system = migration.at_ratio(0.9, 0.1)

# Measure, then shift gradually
if metrics.target_better:
    migration.shift_to_target(0.05)  # Now 85/15
```

**Why impossible without agenkit:** Can't run two frameworks side-by-side. Migration is all-or-nothing, high-risk.

**The message:** "Eliminate vendor lock-in. Migrate gradually with data."

### 4. Multi-Perspective Agent (~250 lines)

**What it does:** Ensemble reasoning across different framework approaches.

```python
from agenkit_perspectives import MultiPerspectiveAgent

perspectives = MultiPerspectiveAgent({
    "langchain": LangChainReActAgent(...),
    "crewai": CrewAITeamAgent(...),
    "autogen": AutoGenConversationAgent(...),
})

results = await perspectives.analyze("Should we build this?")
synthesis = await perspectives.synthesize(results)
```

**Why impossible without agenkit:** Different frameworks = different interfaces. Can't run in parallel and synthesize.

**The message:** "Better decisions through diverse reasoning approaches."

---

## Interoperability Examples

**Concrete demonstrations** of value that single frameworks can't provide:

### Example 1: Best-of-Breed Research System

```python
from langchain_classic import RetrievalQA
from haystack_classic import Reranker
from crewai_classic import SynthesisAgent
from agent_toolkit.patterns import SequentialPattern

# Use each framework's strength
system = SequentialPattern([
    RetrievalQA(llm, retriever),      # LangChain prompts
    Reranker(model="cross-encoder"),  # Haystack reranking
    SynthesisAgent(role="analyst")    # CrewAI coordination
])

result = await system.execute("Research climate tech")
```

**Why this matters:** Each framework does one thing excellently. Why choose when you can combine?

### Example 2: Cross-Framework Debate

```python
from langchain_classic import ReActAgent
from autogen_classic import ConversableAgent
from agent_toolkit.patterns import DebatePattern

# Different reasoning styles debate
debate = DebatePattern(
    agents=[
        ReActAgent(tools=[...]),      # Tool-focused
        ConversableAgent(role="critic") # Conversation-focused
    ],
    rounds=3
)

result = await debate.discuss("Should we build this feature?")
```

**Why this matters:** Diversity of reasoning → better outcomes. Like ensemble ML models.

### Example 3: Complexity-Based Routing

```python
from langchain_classic import LLMChain
from haystack_classic import Pipeline
from crewai_classic import Crew

# Route by task complexity
router = ComplexityRouter({
    "simple": LLMChain(llm, prompt),          # Fast, cheap
    "medium": Pipeline([retrieve, generate]),  # Balanced
    "complex": Crew(agents=[...])             # Full power
})

# Right tool for the job
result = await router.handle(task)
```

**Why this matters:** Granularity is a feature. Don't use a sledgehammer for a thumbtack.

---

## The Strategic Narrative

### Stage 1: "We can do what you do"
Reimplementations prove agenkit supports framework abstractions.
**Component-based** - Use whole frameworks or individual pieces.

### Stage 2: "We can do what you CAN'T do"
Impossible frameworks show the power of interoperability.
**Novel capabilities** - Best-of-breed composition, A/B testing, risk-free migration, ensemble reasoning.

### Stage 3: "Together we can do more"
Invite frameworks to adopt agenkit as foundation.
**Extensible by design** - We provide reference implementations, you can always do better.

**The shift:** From competitive to collaborative. From "replace" to "enhance."

---

## Extensibility: Protocol Adapters & Components

### Protocol Adapters: Reference Implementations

**Philosophy:** We provide reference implementations. Use them, fork them, or write your own.

**What agenkit provides:**
```
Protocol Adapter Specification:
├── Interface definition      # What any adapter must implement
├── Reference implementations # Python, Go, Rust examples
├── Test suite               # Verify your adapter is compliant
└── Documentation            # How to build your own
```

**You can:**
- ✅ Use our MCP adapter as-is
- ✅ Fork our adapter and optimize for your workload
- ✅ Write your own from scratch (implement the interface)
- ✅ Mix and match (our MCP, your custom A2A)

**Example: Custom protocol adapter**
```python
from agenkit.protocols import ProtocolAdapter

class MyCustomMCPAdapter(ProtocolAdapter):
    """Your custom implementation"""

    def __init__(self, endpoint: str, **custom_opts):
        # Your custom initialization
        # Maybe connection pooling, custom auth, etc.
        pass

    async def send(self, message: Message) -> Message:
        # Your optimized send logic
        pass

    async def receive(self) -> Message:
        # Your optimized receive logic
        pass

# Works with all toolkit patterns
from agent_toolkit.patterns import SequentialPattern
pipeline = SequentialPattern([agent1, agent2], adapter=MyCustomMCPAdapter(...))
```

**The key:** Adapters are **implementations**, not specifications. We provide good defaults. You can always do better for your use case.

### Framework Components: Mix and Match

**Philosophy:** Components are independently useful. Pick what you want.

**Example: Custom framework from components**
```python
# Take the best pieces from each framework
from langchain_classic.agents import ReActAgent       # LangChain reasoning
from haystack_classic.retrieval import Reranker       # Haystack reranking
from crewai_classic.crew import TaskCoordinator       # CrewAI coordination
from your_custom_components import YourSpecialSauce   # Your innovation

# Build your own framework from these components
class MyCustomFramework:
    def __init__(self, config):
        self.agent = ReActAgent(...)           # Best reasoning
        self.reranker = Reranker(...)          # Best reranking
        self.coordinator = TaskCoordinator(...) # Best coordination
        self.special = YourSpecialSauce(...)   # Your differentiator

    async def execute(self, task):
        # Your orchestration logic
        pass

# This is the power of shared primitives
```

---

## Installation

```bash
# Core toolkit (required)
pip install agenkit

# Install framework reimplementations
pip install langchain-classic
pip install crewai-classic
pip install autogen-classic
pip install haystack-classic

# Or all at once
pip install agenkit-frameworks
```

## Usage

### As Drop-In Replacements

```python
# Replace this:
# from langchain import LLMChain

# With this:
from langchain_classic import LLMChain

# Same API, but built on agenkit
# So it works with other agenkit-based frameworks
```

### For Interoperability

```python
from langchain_classic import RetrievalQA
from haystack_classic import Pipeline
from crewai_classic import Agent
from agent_toolkit.patterns import ParallelPattern

# Mix different "frameworks"
# All speak agenkit underneath
system = ParallelPattern([
    RetrievalQA(llm, retriever),      # LangChain pattern
    Pipeline([component1, component2]), # Haystack pattern
    Agent(role="analyst", goal="...")  # CrewAI pattern
])

# This is IMPOSSIBLE with the real frameworks
# With agenkit: It just works
```

### For Learning

```python
# Want to understand how ReAct agents work?
# Read the source:

from langchain_classic.agents import ReActAgent

# It's 100 lines of readable code
# Not 5000 lines of abstractions
```

---

## Repository Structure

```
agenkit-frameworks/
├── langchain-classic/
│   ├── langchain_classic/
│   │   ├── __init__.py
│   │   ├── prompts.py        # PromptTemplate (~50 lines)
│   │   ├── chains.py          # LLMChain (~100 lines)
│   │   ├── memory.py          # ConversationMemory (~50 lines)
│   │   ├── agents.py          # ReActAgent (~200 lines)
│   │   └── retrieval.py       # RetrievalQA (~100 lines)
│   ├── examples/
│   │   ├── basic_chain.py
│   │   ├── react_agent.py
│   │   └── rag_system.py
│   ├── tests/
│   ├── README.md              # "LangChain in 500 lines"
│   └── MIGRATION.md           # How to migrate from LangChain
│
├── crewai-classic/
│   ├── crewai_classic/
│   │   ├── __init__.py
│   │   ├── agent.py           # Agent (~100 lines)
│   │   ├── task.py            # Task (~50 lines)
│   │   └── crew.py            # Crew (~150 lines)
│   ├── examples/
│   ├── tests/
│   ├── README.md              # "CrewAI in 300 lines"
│   └── MIGRATION.md
│
├── autogen-classic/
│   ├── autogen_classic/
│   │   ├── __init__.py
│   │   ├── agent.py           # ConversableAgent (~150 lines)
│   │   ├── groupchat.py       # GroupChat (~150 lines)
│   │   └── termination.py     # Termination (~100 lines)
│   ├── examples/
│   ├── tests/
│   ├── README.md              # "AutoGen in 400 lines"
│   └── MIGRATION.md
│
├── haystack-classic/
│   ├── haystack_classic/
│   │   ├── __init__.py
│   │   ├── pipeline.py        # Pipeline (~200 lines)
│   │   ├── component.py       # Component (~100 lines)
│   │   ├── retrieval.py       # Retrieval components (~200 lines)
│   │   └── generation.py      # Generation components (~100 lines)
│   ├── examples/
│   ├── tests/
│   ├── README.md              # "Haystack in 600 lines"
│   └── MIGRATION.md
│
├── agenkit-composer/          # NEW: Impossible without shared primitives
│   ├── agenkit_composer/
│   │   ├── __init__.py
│   │   ├── composer.py        # FrameworkComposer (~200 lines)
│   │   └── strategies.py      # Best-of-breed strategies (~100 lines)
│   ├── examples/
│   │   ├── best_of_breed.py   # Use best from each framework
│   │   └── custom_composition.py
│   ├── tests/
│   └── README.md              # "The Impossible Framework"
│
├── agenkit-abtest/            # NEW: Scientific framework comparison
│   ├── agenkit_abtest/
│   │   ├── __init__.py
│   │   ├── tester.py          # FrameworkABTest (~150 lines)
│   │   └── metrics.py         # Comparison metrics (~50 lines)
│   ├── examples/
│   │   ├── compare_rag.py     # Compare RAG approaches
│   │   └── benchmark_suite.py
│   ├── tests/
│   └── README.md              # "Data-Driven Framework Choice"
│
├── agenkit-migrate/           # NEW: Risk-free migration
│   ├── agenkit_migrate/
│   │   ├── __init__.py
│   │   ├── migration.py       # GradualMigration (~300 lines)
│   │   └── monitoring.py      # Migration metrics (~100 lines)
│   ├── examples/
│   │   ├── gradual_migration.py
│   │   └── canary_deployment.py
│   ├── tests/
│   └── README.md              # "Zero-Risk Framework Migration"
│
├── agenkit-perspectives/      # NEW: Ensemble reasoning
│   ├── agenkit_perspectives/
│   │   ├── __init__.py
│   │   ├── multi_perspective.py  # MultiPerspectiveAgent (~250 lines)
│   │   └── synthesis.py          # Synthesize across perspectives (~100 lines)
│   ├── examples/
│   │   ├── agent_debate.py
│   │   └── ensemble_reasoning.py
│   ├── tests/
│   └── README.md              # "Better Decisions Through Diversity"
│
├── examples/                   # Cross-cutting examples
│   ├── best_of_breed_research.py      # Example 1
│   ├── cross_framework_debate.py      # Example 2
│   ├── complexity_routing.py          # Example 3
│   └── production_system.py           # Full production example
│
└── README.md                   # This file
```

---

## FAQ

### "Isn't this just mocking the original frameworks?"

No. This is strategic provocation to drive industry progress.

**The parallel:** When SQLite was reimplemented in Rust (rsqlite), was that mocking SQLite? No—it was showing the value of memory safety. The original was still valuable, but the provocation started important conversations.

**Our case:** We're not saying frameworks are bad. We're showing that 90% of every framework is the same primitives—and that's the part that should be standardized.

**The respect:** Reimplementing requires deep understanding. We studied these frameworks enough to distill their essence. That's not mockery—that's scholarship.

**The purpose:** Move the industry from fragmentation to interoperability. The provocation is the marketing strategy that makes this conversation impossible to ignore.

### "Why are features X, Y, Z missing?"

Because they're framework-specific, not fundamental. The point is to show the core that everyone uses, which is surprisingly small.

### "Can I use these in production?"

These are educational. For production:
- Use the real frameworks (with their ecosystems and support)
- Or build your own framework on agenkit
- Or use these as starting points and extend them

### "Will you keep these up-to-date with the originals?"

No. These are point-in-time reimplementations showing core patterns. They're not feature-for-feature replacements.

### "Can I contribute?"

Yes! Improvements to readability, examples, and migration guides welcome. But we won't add every framework feature—that defeats the purpose.

### "What about Framework X?"

If you want to see your favorite framework reimplemented on agenkit, submit a PR! The pattern is clear.

---

## The Real Message

**Every framework reinvents:**
- Agent abstraction
- Tool abstraction
- Message formats
- Coordination patterns
- Protocol adapters

**Every framework adds value through:**
- Domain expertise
- Ecosystem integrations
- Convenience features
- Production tooling
- Community support

**The problem:** They spend 60% of effort on the first list, 40% on the second.

**The solution:** Share the first list (agenkit), compete on the second.

**These reimplementations prove:** The first list is standardizable. It's ~500-600 lines per framework. The value is in the second list.

---

## Related Projects

- **agenkit**: The foundation layer ([github.com/agenkit/agenkit](https://github.com/agenkit/agenkit))
- **agenkit-protocols**: Protocol adapters (MCP, A2A, HTTP, gRPC)
- **agenkit-benchmarks**: Performance comparisons vs frameworks

---

## License

BSD-3-Clause. Use it, fork it, build on it.

These are educational reimplementations. Original frameworks retain their respective licenses and trademarks.

---

## Acknowledgments

Built to show respect for the original frameworks by demonstrating what they got right: the patterns. And to suggest what the ecosystem needs: shared primitives.

**LangChain, CrewAI, AutoGen, Haystack** - you solved real problems. Now let's solve them together.

---

**Every framework, one toolkit. That's agenkit.**
