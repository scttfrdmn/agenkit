# Experimental: Recursive Long-Context Handling (RLM)

**Status**: ⚠️ EXPERIMENTAL - Research validation stage

Based on ["Recursive Language Models"](https://arxiv.org/abs/2512.24601) (Zhang, Kraska, Khattab - MIT CSAIL, Dec 2025)

## Overview

This experimental technique composes Agenkit's existing patterns to handle arbitrarily long contexts (10M+ tokens) by treating prompts as external environment variables rather than direct model input.

**Core Idea**: Load long context into a Python REPL as a variable, allow the agent to programmatically examine/decompose it, and recursively call sub-agents on filtered snippets.

## Pattern Composition

RLM combines these existing Agenkit patterns:

1. **`ReasoningWithToolsAgent`** - Code execution in REPL environment
2. **`AgentTool`** - Recursive sub-agent delegation
3. **`ReActAgent`** - Iterative observe → reason → act loop
4. **`MemoryHierarchy`** - External context management

**Novel aspect**: Specific composition strategy + system prompts, not new primitives.

## When to Use

✅ **Good for**:
- Inputs beyond model context limits (>500K tokens)
- Information-dense tasks requiring processing most/all of input
- Multi-hop reasoning over large document collections
- Tasks where summarization loses critical details

❌ **Not good for**:
- Short inputs that fit in model context (<100K tokens)
- Simple retrieval tasks (use RAG/BM25 instead)
- Cost-sensitive applications (high variance)
- Real-time latency requirements

## Performance Characteristics

**From paper results**:

| Task | Base Model | RLM | Improvement |
|------|-----------|-----|-------------|
| BrowseComp+ (1K docs, 6-11M tokens) | 0% | 91% | +91pp |
| OOLONG-Pairs (32K tokens) | 0.04% | 58% | +58pp |
| CodeQA (900K tokens) | 24% | 62% | +38pp |

**Cost profile**:
- Median: Comparable to base model
- 95th percentile: 3-10x higher (due to long trajectories)
- Scales log-linearly with input size

## Maturity & Limitations

### ✅ Validated
- Peer-reviewed research (MIT CSAIL)
- Works across GPT-5 and Qwen3-Coder
- Handles inputs 100x beyond context limits

### ⚠️ Caveats
- **Models not trained for this** - Current LLMs make suboptimal decisions (e.g., Qwen3 makes 1000s of unnecessary sub-calls)
- **Brittle prompts** - Requires model-specific tuning (see `prompts/`)
- **High cost variance** - Some trajectories explore inefficiently
- **Async needed** - Sequential sub-calls are slow (paper uses blocking)
- **No training data** - Performance will improve as models train on this pattern

## Examples

### Basic RLM
Minimal working example showing core mechanics:
```bash
python basic_rlm.py
```

### Document QA
Multi-hop reasoning over large document collections:
```bash
python document_qa.py
```

### Data Aggregation
Semantic transformations over structured data:
```bash
python data_aggregation.py
```

## Budget Protection (Critical!)

**RLM has high cost variance** - 95th percentile costs 3-10x higher than median due to long trajectories. Always use budget protection:

```python
from basic_rlm import RecursiveREPLAgent
from agenkit.adapters.llm import OpenAIAgent
from agenkit.budget import CostTracker

# Create cost tracker
tracker = CostTracker()

# Initialize agents
root_agent = OpenAIAgent(model="gpt-5")
sub_agent = OpenAIAgent(model="gpt-5-mini")

# Create RLM with budget limit
rlm = RecursiveREPLAgent(
    agent=root_agent,
    sub_agent=sub_agent,
    max_iterations=20,
    session_budget=5.00,  # Stop if exceeds $5
    cost_tracker=tracker,
)

# Process long context (will raise BudgetExceededError if over limit)
result = await rlm.process(message)

# Check final cost
session_cost = await tracker.get_session_cost("session-id")
print(f"Total cost: ${session_cost:.4f}")
```

**Recommended budgets**:
- Development/testing: $1-2
- Research experiments: $5-10
- Production (rare): $10-20 with alerts

See `agenkit/budget/README.md` for full budget management features.

## Implementation Notes

### REPL Environment
- Uses Python's `exec()` with sandboxed namespace
- Context loaded as string variable
- Provides `llm_query(prompt)` for recursive calls
- Agent iterates until `FINAL(answer)` or `FINAL_VAR(var)`

### System Prompts
Two variants provided (based on paper Appendix D):

- **`prompts/gpt5_system.txt`** - For GPT-5/Claude/Opus models
- **`prompts/qwen_system.txt`** - Adds warning about excessive sub-calls

Key prompt elements:
1. Context metadata (size, chunk structure)
2. REPL environment description
3. Recursive call strategy examples
4. Final answer format specification

### Recursion Depth
Paper uses **max_depth=1** (sub-calls are base LMs, not recursive).

Deeper recursion theoretically possible but:
- Not evaluated in paper
- Increases complexity/cost
- Models already struggle with depth=1

## Research Trajectory

### Current (Dec 2025)
- ✅ Proven technique for long-context scaling
- ⚠️ Models not optimized for this pattern

### Near Future (2026)
- Models may be trained on RLM trajectories
- Better cost predictability as models improve
- Standard prompts may emerge

### Long Term
- Could become standard inference pattern
- May inform model training objectives
- Potential graduation to core Agenkit patterns

## Promotion Criteria

This technique will be considered for `agenkit/patterns/` if:

1. ✅ Widely adopted in production (6+ months validation)
2. ✅ Models improve decision-making (training or fine-tuning)
3. ✅ Cost variance becomes predictable (<2x median)
4. ✅ Standard prompts work across models
5. ✅ Community consensus on best practices

## References

- **Paper**: Zhang et al., "Recursive Language Models", arXiv:2512.24601, Dec 2025
- **Code**: [Paper repository](https://github.com/mit-oasys/recursive-llm) (when available)
- **Related**: Context Folding (Sun et al., 2025), AgentFold (Ye et al., 2025)

## Contributing

This is experimental research validation. Contributions welcome:

- ✅ New examples demonstrating use cases
- ✅ Performance profiling and optimization
- ✅ Prompt improvements for specific models
- ✅ Cost reduction strategies
- ❌ Core API changes (keep experimental isolated)

**Questions?** Open an issue tagged `experimental/rlm`

---

**Disclaimer**: This is a research technique, not production-ready infrastructure. **Always use budget limits** to prevent runaway costs. Performance and cost characteristics may change as underlying models evolve.
