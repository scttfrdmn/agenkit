# Composition Techniques

## What are Compositions?

Compositions are **simple combinations of existing patterns and primitives**. They solve specific use cases but don't qualify as "patterns" because they're too simple or too specific.

**Key Insight**: Many frameworks and books present simple compositions as "design patterns" or "innovative features." This creates confusion about what actually constitutes a pattern. Agenkit distinguishes between:

- **Patterns** (`agenkit/patterns/`): Non-trivial, reusable coordination solutions
- **Compositions** (`agenkit/techniques/compositions/`): Simple wiring of existing primitives

Both are valuable! Compositions are perfect for prototyping and simple use cases. Patterns are for production systems requiring robustness, configuration, and error handling.

---

## Pattern vs Composition: The Distinction

### What makes something a PATTERN?

1. **Reusable solution** to a recurring coordination problem
2. **Clear structure** with defined roles, interactions, and lifecycle
3. **Non-trivial** - requires more than just combining primitives
4. **Configurable** - multiple valid implementation strategies
5. **General purpose** - applicable across many domains
6. **Production-grade** - error handling, monitoring, recovery

### What makes something a COMPOSITION?

1. **Combines existing patterns/primitives** in a straightforward way
2. **Minimal logic** - mostly just wiring components together
3. **Specific use case** - solves one particular problem
4. **Few lines** - typically 10-50 lines of code
5. **Prototype-quality** - works but lacks production features

---

## Examples: Pattern vs Composition

### ✅ PATTERN: HumanInLoopAgent

**Why it's a pattern:**
- **Complex**: Confidence thresholds, async approval, structured requests/responses
- **Configurable**: Multiple approval functions, timeout strategies, retry logic
- **Production-grade**: Error handling, audit trails, approval history
- **General purpose**: Works for any approval scenario

**Location**: `agenkit/patterns/human_in_loop.py` (~300 LOC)

**Features**:
```python
HumanInLoopAgent(
    agent=base_agent,
    approval_fn=custom_approval,      # Configurable
    confidence_threshold=0.7,          # When to ask
    timeout=60,                        # Response timeout
    max_retries=3,                     # Retry on failure
    audit_trail=True                   # Track all approvals
)
```

### ❌ COMPOSITION: Simple Human Approval

**Why it's NOT a pattern:**
- **Too simple**: Just `input()` + `if` statement
- **No configuration**: Hard-coded behavior
- **No error handling**: Fails on invalid input
- **Specific**: Only works for basic prototypes

**Location**: `agenkit/techniques/compositions/simple_human_approval.py` (~10 lines)

**Code**:
```python
class SimpleApprovalTool(Tool):
    async def execute(self, action: str) -> dict:
        response = input(f"Approve {action}? (y/n): ")
        return {"approved": response == 'y'}
```

**Both are valuable!** Use the composition for quick prototypes, the pattern for production.

---

### ✅ PATTERN: ReflectionAgent

**Why it's a pattern:**
- **Complex**: Generator-critic loop, stopping conditions, history tracking
- **Configurable**: Quality thresholds, max iterations, critique formats
- **Production-grade**: Convergence detection, multiple strategies, metrics
- **General purpose**: Works for any iterative refinement task

**Location**: `agenkit/patterns/reflection.py` (~400 LOC)

**Features**:
```python
ReflectionAgent(
    generator=base_agent,
    critic=critique_agent,
    max_iterations=5,
    quality_threshold=0.8,
    improvement_threshold=0.05,
    critique_format="structured"
)
```

### ❌ COMPOSITION: Actor-Critic Variation

**Why it's NOT a separate pattern:**
- **Nearly identical** to ReflectionAgent
- **Same mechanism**: Proposal → Evaluation → Refinement loop
- **Just terminology**: "Actor/Critic" vs "Generator/Critic"
- **No unique value**: Use ReflectionAgent instead

**Location**: `agenkit/techniques/compositions/actor_critic_variation.py` (~40 lines)

**Insight**: Books call this "actor-critic" borrowing from RL, but in LLM context it's just reflection with different names. This composition exists to show the equivalence.

---

## The Framework Marketing Problem

Many AI agent frameworks market simple compositions as "innovative features" or "design patterns":

| Framework Claims | Agenkit Reality |
|------------------|-----------------|
| "Advanced RAG with citations" | Sequential + Retrieval + metadata (25 lines) |
| "Context optimization engine" | Summarizer wrapper + token counting (30 lines) |
| "Actor-critic architecture" | Reflection pattern with RL terminology |
| "Human-in-the-loop workflow" | Input function + conditional (10 lines for simple, full pattern for production) |
| "Goal-driven autonomous agents" | While loop + progress function (25 lines) |

**Agenkit's philosophy**: We show you how simple these are. If you need the simple version, use our compositions. If you need production quality, use our patterns.

---

## Available Compositions

### 1. Simple Human Approval
**Lines**: ~30 LOC (code + docs)
**Use case**: Quick prototypes needing basic approval
**Upgrade to**: `HumanInLoopAgent` pattern for production

Minimal tool that asks for yes/no approval via input.

### 2. RAG (Retrieval-Augmented Generation)
**Lines**: ~40 LOC (code + docs)
**Use case**: Basic question-answering with context
**Upgrade to**: Full RAG pattern with caching, reranking

Just Sequential + RetrievalAgent + AnswerAgent.

### 3. RAG with Citations
**Lines**: ~50 LOC (code + docs)
**Source**: Rothman "Context Engineering" Ch. 7
**Use case**: When source attribution is critical (legal, medical, research)

Adds citation tracking and source metadata to basic RAG.

### 4. Context Optimization
**Lines**: ~60 LOC (code + docs)
**Source**: Rothman "Context Engineering" Ch. 6
**Use case**: Token reduction for cost optimization

Wrapper that summarizes context when it exceeds token limits.

### 5. Prioritization
**Lines**: ~50 LOC (code + docs)
**Source**: Gulli "Agentic Design Patterns"
**Use case**: Task queue with priority ordering

Heap-based task queue with custom priority function.

### 6. Goal Monitoring
**Lines**: ~60 LOC (code + docs)
**Use case**: Stop when goal achieved

Wraps PlanningAgent and checks progress after each step.

### 7. Exploration Strategy
**Lines**: ~70 LOC (code + docs)
**Use case**: Exploration-exploitation tradeoff

UCB (Upper Confidence Bound) for action selection with ReActAgent.

### 8. Learning from Feedback
**Lines**: ~80 LOC (code + docs)
**Use case**: Improve from past interactions

Stores interactions in memory and retrieves similar ones for context.

### 9. Actor-Critic Variation
**Lines**: ~80 LOC (code + docs)
**Source**: Albada "Building Applications with AI Agents"
**Use case**: Educational - shows equivalence to Reflection pattern

Demonstrates that "actor-critic" in LLM context is just reflection.

**Recommendation**: Use `ReflectionAgent` pattern instead!

---

## When to Use Compositions

### ✅ Use Compositions When:

- **Prototyping**: Quick validation of ideas
- **Learning**: Understanding how patterns work
- **Teaching**: Demonstrating composability
- **Simple use cases**: Production system doesn't need full pattern complexity
- **Resource-constrained**: Don't want overhead of full pattern
- **Short-lived**: One-off scripts or temporary solutions

### ⬆️ Upgrade to Full Patterns When:

- **Production deployment**: Need error handling, monitoring, recovery
- **Configuration required**: Different variants for different use cases
- **Scale**: Simple approach hits performance or reliability limits
- **Complexity grows**: Use case requires more sophisticated logic
- **Team development**: Need well-defined interfaces and contracts
- **Long-term maintenance**: Need sustainable, documented architecture

---

## Book Sources

These compositions reference recent books on agentic systems:

1. **Gulli (2025)**: "Agentic Design Patterns"
   - RAG, Prioritization
   - Shows many "patterns" are simple compositions

2. **Alto (2025)**: "AI Agents in Practice"
   - Multi-agent compositions
   - Practical recipes for common scenarios

3. **Rothman (2025)**: "Context Engineering for Multi-Agent Systems"
   - RAG with Citations (Ch. 7)
   - Context Optimization (Ch. 6)
   - High-fidelity context handling

4. **Albada (2025)**: "Building Applications with AI Agents"
   - Actor-Critic variation
   - Shows RL terminology applied to LLMs

**Key Insight**: All these books' "innovations" can be implemented in 10-50 lines using Agenkit's patterns and primitives. This demonstrates:
- Agenkit's composability
- The power of minimal abstractions
- The difference between marketing and engineering

---

## Usage Examples

### Simple Human Approval

```python
from agenkit.techniques.compositions import SimpleApprovalTool

# For prototypes only!
tool = SimpleApprovalTool()
result = await tool.execute("delete database")
if result["approved"]:
    # proceed
```

### RAG

```python
from agenkit.techniques.compositions import SimpleRAG

# Basic RAG in 15 lines
rag = SimpleRAG(
    retriever=vector_store,
    answerer=llm_agent
)

answer = await rag.process(Message(
    role="user",
    content="What is quantum computing?"
))
```

### RAG with Citations

```python
from agenkit.techniques.compositions import CitedRAG

# High-fidelity RAG with source tracking
rag = CitedRAG(
    retriever=vector_store,
    answerer=llm_agent
)

answer = await rag.process(Message(content="Medical question"))

# Access citations
sources = answer.metadata["sources"]
citations = answer.metadata["citations"]  # [1], [2], etc.
```

### Context Optimization

```python
from agenkit.techniques.compositions import ContextOptimizer

# Reduce tokens for cost optimization
optimizer = ContextOptimizer(
    agent=base_agent,
    summarizer=summary_agent,
    max_tokens=4000
)

answer = await optimizer.process(long_context_message)
print(f"Saved {answer.metadata['compression_ratio']}x tokens")
```

---

## Philosophy: Minimal Abstractions, Maximum Power

Agenkit provides:
1. **Primitives**: Agent interface, Message protocol, Tools
2. **Patterns**: Non-trivial coordination solutions (11 patterns)
3. **Techniques**: Reasoning enhancements (6 reasoning techniques)
4. **Compositions**: Simple recipes (9 common combinations)

This layered approach means:
- **You decide the complexity** - use what you need
- **No vendor lock-in** - everything is composable
- **Clear upgrade path** - start simple, add sophistication
- **Educational transparency** - see what's actually complex vs simple

**Other frameworks hide this**: Everything is a "feature" or "pattern," making it hard to understand what's truly complex. Agenkit makes the distinction explicit.

---

## Contributing

When adding new compositions:

1. **Keep it simple** - If it's >100 LOC, it might be a pattern
2. **Document clearly** - Explain why it's NOT a pattern
3. **Show upgrade path** - Link to related patterns if they exist
4. **Cite sources** - Reference books/frameworks if applicable
5. **Provide examples** - Show actual usage
6. **Test it** - Ensure it works as documented

---

## Related Documentation

- **Patterns Library**: `agenkit/patterns/` - Full production patterns
- **Reasoning Techniques**: `agenkit/techniques/reasoning/` - Reasoning enhancements
- **Design Philosophy**: `docs/patterns_library_design.md`
- **Getting Started**: `GETTING_STARTED.md`

---

**Remember**: Compositions are valuable learning tools and great for prototypes. Don't feel bad about using them! But when you're ready for production, our patterns provide the robustness you need.

The key is knowing the difference. 🎯
