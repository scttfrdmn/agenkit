# Framework Benchmark Results

**Platform:** Darwin 25.3.0 · Python 3.12.2 · Apple Silicon
**Date:** 2026-03-16
**Methodology:** MockLLM with zero latency — measures pure framework orchestration overhead
**Iterations:** 100 per scenario (conversational: 50), 10 warmup runs

---

## Results

### 1. Simple Chain — LLMChain.run vs direct LLM call

| Scenario | mean_ms | p50_ms | p95_ms | iter/s |
|---|---|---|---|---|
| `LLMChain.run` | 0.0016 | 0.0016 | 0.0017 | 624,364 |
| `direct_llm_complete` | 0.0007 | 0.0007 | 0.0008 | 1,387,415 |
| `Agent.process` | 0.0008 | 0.0008 | 0.0009 | 1,236,550 |

**Overhead:** LLMChain adds ~0.0009ms (2.3x) over direct LLM call. Both are sub-microsecond.

---

### 2. Sequential Pipeline — SequentialChain vs SequentialAgent (3 agents)

| Scenario | mean_ms | p50_ms | p95_ms | iter/s |
|---|---|---|---|---|
| `SequentialChain (3 agents)` | 0.0033 | 0.0032 | 0.0034 | 306,045 |
| `SequentialAgent (3 agents)` | 0.0032 | 0.0032 | 0.0033 | 314,762 |

**Overhead:** Effectively identical — within statistical noise (1.03x). The MiniChain
wrapper adds no meaningful overhead over the native pattern.

---

### 3. Parallel Execution — Crew(parallel) vs ParallelAgent (3 agents)

| Scenario | mean_ms | p50_ms | p95_ms | iter/s |
|---|---|---|---|---|
| `Crew parallel (3 agents)` | 0.0780 | 0.0713 | 0.1542 | 12,813 |
| `ParallelAgent (3 agents)` | 0.0835 | 0.0694 | 0.1478 | 11,979 |

**Overhead:** Virtually equivalent (within 7%). High p95 variance (~2x mean) is normal
for asyncio task scheduling — not a framework artifact.

---

### 4. Conversational Agent — ConversationChain vs ConversationalAgent (10 turns)

| Scenario | mean_ms | p50_ms | p95_ms | iter/s |
|---|---|---|---|---|
| `ConversationChain (10 turns)` | 0.0206 | 0.0204 | 0.0216 | 48,654 |
| `ConversationalAgent (10 turns)` | 0.0250 | 0.0231 | 0.0272 | 40,032 |

**Overhead:** 10-turn conversation adds 0.0044ms per iteration (1.21x). For a 100ms LLM
this is 0.04% of total latency — negligible.

---

### 5. Router — RouterChain vs RouterAgent

| Scenario | mean_ms | p50_ms | p95_ms | iter/s |
|---|---|---|---|---|
| `RouterChain` | 0.0018 | 0.0017 | 0.0021 | 557,086 |
| `RouterAgent` | 0.0021 | 0.0021 | 0.0022 | 473,122 |

**Overhead:** RouterAgent is 1.17x slower — an absolute difference of 0.0003ms.

---

## Key Findings

### Framework overhead is negligible in production

All orchestration overhead is sub-millisecond. A typical LLM API call takes 100–3000ms.
Framework overhead represents **< 0.1%** of total end-to-end latency in every scenario.

### MiniChain/MiniCrew wrappers are nearly as fast as primitives

The largest overhead observed is 2.3x (LLMChain vs direct LLM call) — an absolute
difference of **0.0009ms**. In the most realistic benchmark (sequential pipeline), overhead
is **1.03x** — statistically indistinguishable.

### Choose based on API familiarity, not performance

The data validates that migration decisions should be driven by:
- **Developer experience** — do your team's mental models fit LangChain-style chains or agenkit primitives?
- **Type safety** — agenkit primitives have stronger typing and less magic
- **Maintenance** — agenkit primitives have no external framework dependency

Performance is **not a differentiator** at the framework orchestration level.

### Go advantage is cross-language, not framework-layer

The "18x Go speedup" claim refers to Go vs Python for CPU-bound workloads with concurrent
agents. At the orchestration level measured here, both Python implementations are equivalent.
See `agenkit-go` benchmarks for cross-language comparison.

---

## Real-World Cost Analysis

At 1M requests/day with 100ms LLM latency:

| Implementation | LLM latency | Orchestration | Total | Overhead % |
|---|---|---|---|---|
| Direct LLM call | 100ms | 0.0007ms | 100.001ms | 0.0007% |
| MiniChain LLMChain | 100ms | 0.0016ms | 100.002ms | 0.0016% |
| SequentialAgent (3 steps) | 300ms | 0.003ms | 300.003ms | 0.001% |
| ParallelAgent (3 parallel) | 100ms | 0.08ms | 100.08ms | 0.08% |

Orchestration overhead is **economically irrelevant**. Cost optimization should focus on
model selection, prompt length, and caching — not framework choice.

---

## Reproduction

```bash
# Run benchmarks
uv run python benchmarks/frameworks/run_all.py

# Visualize results
uv run python benchmarks/frameworks/visualize.py

# Generate HTML report
uv run python benchmarks/frameworks/visualize.py --html
```

Results are saved to `results/results_{timestamp}.json`.
