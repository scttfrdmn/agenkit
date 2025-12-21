# Advanced Reasoning Techniques

Cutting-edge reasoning methods for complex problem-solving.

## Overview

Agenkit supports **6 advanced reasoning techniques** that enhance agent capabilities for complex tasks:

| Technique | Description | When to Use |
|-----------|-------------|-------------|
| **[Chain-of-Thought (CoT)](cot.md)** | Step-by-step reasoning | Multi-step problems |
| **[Tree-of-Thought (ToT)](tot.md)** | Multi-path exploration | Multiple solution paths |
| **[Self-Consistency (SC)](sc.md)** | Voting for reliability | Uncertain answers |
| **[Graph-of-Thought (GoT)](got.md)** | Graph-based reasoning | Connected concepts |
| **[Least-to-Most (LTM)](ltm.md)** | Decomposition strategy | Complex → simple |
| **[Plan-and-Solve](plan-and-solve.md)** | Planning before execution | Strategic tasks |

---

## Quick Comparison

### Chain-of-Thought (CoT)
**What**: Break down problem into reasoning steps
**Best for**: Math, logic, multi-step reasoning
**Cost**: Low (single LLM call)
**Quality**: Good for clear problems

### Tree-of-Thought (ToT)
**What**: Explore multiple reasoning paths in parallel
**Best for**: Creative tasks, multiple solutions
**Cost**: High (many LLM calls)
**Quality**: Excellent for complex problems

### Self-Consistency (SC)
**What**: Generate multiple answers and vote
**Best for**: Tasks with uncertainty
**Cost**: Medium (N parallel calls)
**Quality**: Very reliable

### Graph-of-Thought (GoT)
**What**: Reason over connected concepts
**Best for**: Knowledge graphs, relationships
**Cost**: Medium (iterative exploration)
**Quality**: Good for interconnected problems

### Least-to-Most (LTM)
**What**: Solve simpler sub-problems first
**Best for**: Complex decomposable problems
**Cost**: Medium (sequential sub-problems)
**Quality**: Good for hierarchical tasks

### Plan-and-Solve
**What**: Plan steps before executing
**Best for**: Strategic, multi-phase tasks
**Cost**: Medium (plan + execute)
**Quality**: Good for structured problems

---

## When to Use Which?

### Problem Type Decision Tree

```
Is the problem straightforward?
├─ YES → Use Chain-of-Thought (CoT)
└─ NO  → Does it have multiple valid solutions?
    ├─ YES → Use Tree-of-Thought (ToT)
    └─ NO  → Is accuracy critical?
        ├─ YES → Use Self-Consistency (SC)
        └─ NO  → Can it be decomposed?
            ├─ YES → Use Least-to-Most (LTM)
            └─ NO  → Use Plan-and-Solve
```

---

## Examples

### Example: Math Problem

**Chain-of-Thought**:
```
Problem: If John has 5 apples and buys 3 more, how many does he have?
Reasoning:
1. John starts with 5 apples
2. He buys 3 more apples
3. Total = 5 + 3 = 8 apples
Answer: 8
```

**Tree-of-Thought** (exploring multiple approaches):
```
Branch 1: Direct addition (5 + 3)
Branch 2: Count sequentially (5, 6, 7, 8)
Branch 3: Use subtraction from a known total
Evaluate branches → Choose best path
```

**Self-Consistency** (voting):
```
Sample 1: 8 apples
Sample 2: 8 apples
Sample 3: 8 apples
Vote: 8 (unanimous) → High confidence
```

---

## Performance Characteristics

| Technique | Speed | Quality | Cost | Complexity |
|-----------|-------|---------|------|------------|
| CoT | ⚡⚡⚡ | ⭐⭐⭐ | 💰 | Simple |
| ToT | ⚡ | ⭐⭐⭐⭐⭐ | 💰💰💰 | Complex |
| SC | ⚡⚡ | ⭐⭐⭐⭐ | 💰💰 | Medium |
| GoT | ⚡⚡ | ⭐⭐⭐⭐ | 💰💰 | Medium |
| LTM | ⚡⚡ | ⭐⭐⭐ | 💰💰 | Medium |
| Plan-and-Solve | ⚡⚡ | ⭐⭐⭐⭐ | 💰💰 | Medium |

---

## Combining Techniques

You can combine techniques for maximum power:

**Example: ToT + SC**
- Use ToT to explore multiple reasoning paths
- Use SC to vote on the best path
- Result: High quality with confidence measure

**Example: CoT + LTM**
- Use LTM to break down the problem
- Use CoT for each sub-problem
- Result: Systematic approach to complexity

---

## Code Examples

See working examples in:
- Python: [examples/techniques/reasoning/](../../examples/techniques/reasoning/)
- Go: [agenkit-go/examples/techniques/](../../agenkit-go/examples/techniques/)
- TypeScript: [agenkit-ts/examples/techniques/](../../agenkit-ts/examples/techniques/)
- All languages: 280+ examples total

---

## Tutorial

Learn reasoning techniques step-by-step:
- [Tutorial 03: Advanced Reasoning](../tutorials/index.md#03-advanced-reasoning)

Includes interactive Marimo notebook with:
- Parameter tuning sliders
- Real-time technique comparison
- Cost vs. quality trade-offs

---

## API Reference

See [API documentation](../api/python.md) for implementation details.

---

## Related

- [ReAct Pattern](../patterns/react.md) - Combines reasoning with actions
- [Reasoning with Tools Pattern](../patterns/reasoning-with-tools.md) - Tool-augmented reasoning
- [Evaluation](../features/evaluation.md) - Testing reasoning quality

---

For detailed reasoning technique documentation, see [examples/techniques/reasoning/](../../examples/techniques/reasoning/) in the repository.
