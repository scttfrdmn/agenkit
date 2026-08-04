# Reasoning Techniques

Advanced reasoning techniques that enhance agent capabilities through structured prompting and multi-step reasoning strategies.

## Overview

Reasoning techniques are composable enhancements that can be applied to any LLM or agent to improve their problem-solving capabilities. They work by structuring the prompting and processing of queries to encourage more thoughtful, step-by-step reasoning.

## Available Techniques

### Chain-of-Thought (CoT)

**Status:** ✅ Available
**Module:** `agenkit.techniques.reasoning.ChainOfThought`
**Paper:** [Wei et al., 2022](https://arxiv.org/abs/2201.11903)

Chain-of-Thought reasoning encourages LLMs to break down complex problems into explicit reasoning steps, leading to more accurate and explainable results.

#### When to Use CoT

✅ **Good for:**
- Mathematical reasoning and calculations
- Logical deduction problems
- Multi-step tasks requiring explanation
- Complex problem-solving where intermediate steps matter
- Situations requiring transparency and explainability

❌ **Not ideal for:**
- Simple factual questions
- Tasks where reasoning steps aren't needed
- Real-time applications with strict latency requirements
- Creative writing or open-ended generation

#### Basic Usage

```python
from agenkit import Message
from agenkit.techniques.reasoning import ChainOfThought

# Create CoT agent with your LLM
cot = ChainOfThought(llm=my_llm)

# Process a query
response = await cot.process(Message(
    role="user",
    content="What is 15 * 24?"
))

# Access reasoning steps
print(f"Steps: {response.metadata['num_steps']}")
for step in response.metadata['reasoning_steps']:
    print(f"- {step}")
```

#### Configuration Options

```python
ChainOfThought(
    llm,                    # Required: Your LLM client
    prompt_template="...",  # Custom prompt template (default: "Let's think step by step:\n{query}")
    parse_steps=True,       # Extract reasoning steps (default: True)
    step_delimiter="\n",    # Delimiter for parsing (default: newline)
    max_steps=None,         # Limit number of steps (default: unlimited)
)
```

#### Prompt Templates

The prompt template must include a `{query}` placeholder. The default template uses the famous "Let's think step by step" phrase from the original paper.

**Default template:**
```python
"Let's think step by step:\n{query}"
```

**Custom examples:**
```python
# More formal
"Analyze this problem carefully and solve it step by step:\n{query}"

# For code
"Break down this coding problem into steps:\n{query}\n\nShow your reasoning:"

# For math
"Solve this math problem step by step:\n{query}\n\nWork:"
```

#### Step Parsing

CoT automatically detects and parses reasoning steps in multiple formats:

1. **Numbered steps** (1. 2. 3. or 1) 2) 3))
   ```
   1. First, multiply 15 by 20 to get 300
   2. Then, multiply 15 by 4 to get 60
   3. Add 300 + 60 = 360
   ```

2. **Bullet points** (-, *, •)
   ```
   - First step is to analyze
   - Second step is to break down
   - Third step is to solve
   ```

3. **Delimiter-based** (fallback for plain text)
   ```
   First thought
   Second thought
   Third thought
   ```

Disable parsing with `parse_steps=False` to just apply CoT prompting without extraction.

#### Response Metadata

When `parse_steps=True`, responses include:

```python
{
    "technique": "chain_of_thought",      # Technique identifier
    "reasoning_steps": [...],             # List of extracted steps
    "num_steps": 3,                       # Number of steps found
}
```

#### Examples

See `examples/techniques/reasoning/cot_example.py` for comprehensive examples including:
- Basic usage with default settings
- Custom prompt templates
- Step limiting with `max_steps`
- Disabling step parsing
- Integration with real LLMs (OpenAI, Anthropic, etc.)

#### Performance Characteristics

- **Latency:** Adds ~10-30% to LLM call time (depends on problem complexity)
- **Token Cost:** Increases by ~20-100 tokens per query (prompt template overhead)
- **Accuracy:** Improves accuracy on reasoning tasks by 10-30% (varies by task)
- **Memory:** Minimal overhead (<1MB for typical usage)

#### Integration Patterns

**With Agent composition:**
```python
from agenkit.patterns import ReflectionAgent

# CoT + Reflection for enhanced reasoning
base_llm = MyLLM()
cot = ChainOfThought(llm=base_llm)
reflective_cot = ReflectionAgent(agent=cot)
```

**With tools:**
```python
from agenkit.patterns import ReactAgent

# CoT reasoning with tool use
cot = ChainOfThought(llm=my_llm)
react = ReactAgent(agent=cot, tools=[calculator, search])
```

**With caching:**
```python
from functools import lru_cache

class CachedCoT(ChainOfThought):
    @lru_cache(maxsize=128)
    async def process(self, message):
        return await super().process(message)
```

### Tree-of-Thought (ToT)

**Status:** ✅ Available
**Module:** `agenkit.techniques.reasoning.TreeOfThought`
**Paper:** [Yao et al., 2023](https://arxiv.org/abs/2305.10601)

Tree-of-Thought explores multiple reasoning paths simultaneously using tree search with branching, evaluation, and backtracking. More sophisticated than CoT for problems requiring exploration of solution space.

#### When to Use ToT

✅ **Good for:**
- Creative problem-solving requiring exploration
- Planning and strategy tasks with multiple approaches
- Problems where single path may lead to dead ends
- Tasks benefiting from considering alternatives
- Complex decision-making with trade-offs

❌ **Not ideal for:**
- Simple factual questions
- Time-critical applications (ToT is slower than CoT)
- Problems with a clear single solution path
- Resource-constrained environments (uses more tokens)

#### Basic Usage

```python
from agenkit import Message
from agenkit.techniques.reasoning import TreeOfThought

# Custom evaluator to score reasoning quality
def score_reasoning(text: str) -> float:
    # Return score 0.0-1.0 (higher = better)
    return min(len(text) / 500, 1.0)

tot = TreeOfThought(
    llm=my_llm,
    branching_factor=3,      # Explore 3 alternatives per step
    max_depth=4,             # Up to 4 reasoning steps
    evaluator=score_reasoning,
    strategy="best-first"    # Search strategy
)

response = await tot.process(Message(
    role="user",
    content="Plan a 3-day trip to Tokyo"
))

# Access tree statistics
stats = response.metadata['reasoning_tree_stats']
print(f"Explored {stats['total_nodes']} reasoning paths")
print(f"Best path score: {response.metadata['best_score']}")
```

#### Configuration Options

```python
TreeOfThought(
    llm,                       # Required: Your LLM client
    branching_factor=3,        # Number of branches per step (default: 3)
    max_depth=5,               # Maximum tree depth (default: 5)
    evaluator=None,            # Scoring function str -> float (default: length-based)
    strategy="best-first",     # Search strategy (default: "best-first")
    prune_threshold=0.3        # Prune paths below this score (default: 0.3)
)
```

#### Search Strategies

ToT supports three search strategies:

**1. Best-First Search (default)**
- Always expands the highest-scoring node
- Most efficient for finding good solutions quickly
- Good balance of exploration and exploitation

```python
tot = TreeOfThought(llm=llm, strategy="best-first")
```

**2. Breadth-First Search (BFS)**
- Explores all nodes at same depth before going deeper
- Guarantees finding shortest path
- Good for systematic exploration

```python
tot = TreeOfThought(llm=llm, strategy="bfs")
```

**3. Depth-First Search (DFS)**
- Explores deep paths before wide ones
- Good for finding any valid solution quickly
- May miss better shallow solutions

```python
tot = TreeOfThought(llm=llm, strategy="dfs")
```

#### Custom Evaluators

Evaluators score reasoning quality (0.0-1.0, higher is better):

```python
def quality_evaluator(text: str) -> float:
    score = 0.0

    # Length component
    score += min(len(text) / 500, 0.4)

    # Structure bonus
    if any(c in text for c in ["1.", "2.", "-"]):
        score += 0.3

    # Quality keywords
    keywords = ["because", "therefore", "approach"]
    keyword_count = sum(1 for kw in keywords if kw in text.lower())
    score += min(keyword_count * 0.1, 0.3)

    return min(score, 1.0)

tot = TreeOfThought(llm=llm, evaluator=quality_evaluator)
```

#### Path Pruning

Prune low-quality paths to save tokens:

```python
tot = TreeOfThought(
    llm=llm,
    prune_threshold=0.5  # Prune paths scoring below 0.5
)
```

Higher thresholds = more aggressive pruning = fewer tokens but may miss solutions.

#### Response Metadata

ToT responses include rich metadata:

```python
{
    "technique": "tree_of_thought",
    "search_strategy": "best-first",
    "reasoning_tree_stats": {
        "total_nodes": 40,
        "max_depth": 3,
        "num_leaves": 27,
        "num_evaluated": 13,
        "num_pruned": 5,
        "avg_score": 0.62,
        "best_score": 0.89
    },
    "reasoning_path": [...],  # List of steps in best path
    "num_steps": 4,
    "best_score": 0.89
}
```

#### Examples

See `examples/techniques/reasoning/tot_example.py` for comprehensive examples including:
- Basic usage with different search strategies
- Custom evaluators
- Path pruning demonstrations
- Comparison with Chain-of-Thought

#### Performance Characteristics

- **Latency:** 5-10x slower than CoT (explores multiple paths)
- **Token Cost:** 3-10x more tokens than CoT (depends on branching_factor × max_depth)
- **Quality:** Higher quality solutions for creative/planning tasks
- **Memory:** Moderate (stores tree structure in memory)

#### CoT vs ToT Comparison

| Aspect | Chain-of-Thought | Tree-of-Thought |
|--------|-----------------|-----------------|
| **Paths** | Single linear path | Multiple branching paths |
| **Speed** | Fast | Slower (explores alternatives) |
| **Tokens** | Low | High (branching_factor × depth) |
| **Use Case** | Straightforward problems | Creative, planning, exploration |
| **Quality** | Good for clear problems | Better for ambiguous problems |

## Planned Techniques

The following reasoning techniques are planned for future releases:

### Graph-of-Thought (GoT)

**Status:** 📋 Planned for v0.42.0
**Issue:** #233

Represents reasoning as a directed graph, allowing for complex dependency relationships between thoughts.

**Key features:**
- Non-linear reasoning with dependencies
- Aggregate multiple reasoning paths
- Handle circular dependencies
- Visualize reasoning graph

### Self-Consistency

**Status:** 📋 Planned for v0.42.0
**Issue:** #234

Generates multiple reasoning paths and selects the most consistent answer through voting.

**Key features:**
- Generate N independent reasoning paths
- Majority voting on final answers
- Configurable sampling strategies
- Confidence scoring

### ReAct (Reason + Act)

**Status:** 📋 Planned for v0.42.0
**Issue:** #235

Interleaves reasoning and action, using tools and observations to guide the reasoning process.

**Key features:**
- Think → Act → Observe loop
- Tool use guided by reasoning
- Observation integration
- Multi-step problem solving

### Reflexion

**Status:** 📋 Planned for v0.42.0
**Issue:** #236

Learns from mistakes by reflecting on failures and adjusting the reasoning strategy.

**Key features:**
- Failure reflection and analysis
- Strategy adjustment based on feedback
- Memory of past attempts
- Iterative improvement

## Best Practices

### Choosing a Technique

1. **Start with Chain-of-Thought** for most reasoning tasks
2. **Use Tree-of-Thought** when multiple solution paths need exploration
3. **Use Self-Consistency** when answer reliability is critical
4. **Use ReAct** when reasoning needs to interact with external tools
5. **Use Reflexion** for iterative improvement on repeated tasks

### Combining Techniques

Techniques can be composed:

```python
# CoT + Self-Consistency
cot = ChainOfThought(llm=llm)
consistent = SelfConsistency(agent=cot, n_samples=5)

# CoT + ReAct
cot = ChainOfThought(llm=llm)
react = ReactAgent(agent=cot, tools=tools)
```

### Prompt Engineering Tips

1. **Be specific:** Clear problem statements get better reasoning
2. **Provide examples:** Few-shot examples improve reasoning quality
3. **Set expectations:** Tell the model what kind of reasoning you want
4. **Iterate:** Test different templates to find what works best
5. **Monitor quality:** Track reasoning step quality over time

### Performance Optimization

1. **Cache results:** Identical queries can reuse reasoning
2. **Limit steps:** Use `max_steps` to cap token usage
3. **Disable parsing:** Skip parsing if you only need the final answer
4. **Batch queries:** Process multiple similar queries together
5. **Stream responses:** Use streaming for long reasoning chains

## Architecture

### Design Principles

1. **Composable:** All techniques implement the `Agent` interface
2. **LLM-agnostic:** Works with any LLM (complete() or process() method)
3. **Metadata-rich:** Reasoning steps and metadata preserved
4. **Type-safe:** Full type hints for IDE support
5. **Tested:** Comprehensive test coverage for all techniques

### Extension Points

Create custom reasoning techniques by subclassing `Agent`:

```python
from agenkit import Agent, Message

class MyReasoningTechnique(Agent):
    @property
    def name(self) -> str:
        return "my_technique"

    async def process(self, message: Message) -> Message:
        # Your reasoning logic here
        return Message(
            role="assistant",
            content=result,
            metadata={"technique": "my_technique"}
        )
```

## References

### Papers

- **Chain-of-Thought:** [Wei et al., 2022](https://arxiv.org/abs/2201.11903)
- **Tree-of-Thought:** [Yao et al., 2023](https://arxiv.org/abs/2305.10601)
- **Graph-of-Thought:** [Besta et al., 2023](https://arxiv.org/abs/2308.09687)
- **Self-Consistency:** [Wang et al., 2022](https://arxiv.org/abs/2203.11171)
- **ReAct:** [Yao et al., 2022](https://arxiv.org/abs/2210.03629)
- **Reflexion:** [Shinn et al., 2023](https://arxiv.org/abs/2303.11366)

### Related Documentation

- [Agent Patterns](../PATTERNS.md) - Core agent patterns
- [API Reference](../API.md) - Complete API documentation
- [Examples](../../examples/techniques/) - Code examples

## Support

- **Issues:** [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
- **Discussions:** [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)
- **Contributing:** See [CONTRIBUTING.md](../../CONTRIBUTING.md)
