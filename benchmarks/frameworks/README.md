# Framework Performance Benchmarks

Measures orchestration overhead of mini-frameworks vs Agenkit primitives (Issue #479).
Uses `MockLLM` with zero latency to isolate pure framework dispatch cost.

## Benchmark Scenarios

| File | Compares | Iterations |
|------|----------|-----------|
| `bench_simple_chain.py` | `LLMChain.run` vs direct `LLM.complete` vs `Agent.process` | 100 |
| `bench_sequential.py` | `SequentialChain` vs `SequentialAgent` (3 agents) | 100 |
| `bench_parallel.py` | `Crew(parallel)` vs `ParallelAgent` (3 agents) | 100 |
| `bench_conversational.py` | `ConversationChain` vs `ConversationalAgent` (10 turns) | 50 |
| `bench_router.py` | `RouterChain` vs `RouterAgent` | 100 |

## Running

```bash
# Run all benchmarks
uv run python benchmarks/frameworks/run_all.py

# Run individual benchmark
uv run python benchmarks/frameworks/bench_simple_chain.py

# Visualize results (ASCII charts)
uv run python benchmarks/frameworks/visualize.py

# Generate HTML report
uv run python benchmarks/frameworks/visualize.py --html
```

## Measured Results (2026-03-16)

```
Suite                Scenario                          mean_ms   p50_ms   p95_ms     iter/s
────────────────────────────────────────────────────────────────────────────────
simple_chain         LLMChain.run                       0.0016   0.0016   0.0017   624,364
simple_chain         direct_llm_complete                0.0007   0.0007   0.0008  1,387,415
simple_chain         agent_process                      0.0008   0.0008   0.0009  1,236,550

sequential           SequentialChain (3 agents)         0.0033   0.0032   0.0034   306,045
sequential           SequentialAgent (3 agents)         0.0032   0.0032   0.0033   314,762

parallel             Crew parallel (3 agents)           0.0780   0.0713   0.1542    12,813
parallel             ParallelAgent (3 agents)           0.0835   0.0694   0.1478    11,979

conversational       ConversationChain (10 turns)       0.0206   0.0204   0.0216    48,654
conversational       ConversationalAgent (10 turns)     0.0250   0.0231   0.0272    40,032

router               RouterChain                        0.0018   0.0017   0.0021   557,086
router               RouterAgent                        0.0021   0.0021   0.0022   473,122
```

Full results in [`RESULTS.md`](RESULTS.md) and [`results/results_20260316_142839.json`](results/results_20260316_142839.json).

## Interpretation

**All overhead is sub-millisecond.** Real LLM API latency (100–3000ms) completely
dominates production performance. Framework orchestration represents < 0.1% of
end-to-end latency in every scenario.

| Pattern | Mini-framework overhead vs primitives |
|---|---|
| Simple chain | 2.3x (0.0009ms absolute) |
| Sequential pipeline | 1.03x (within noise) |
| Parallel execution | 1.07x (within noise) |
| Conversational (10 turns) | 1.21x (0.004ms absolute) |
| Router | 1.17x (0.0003ms absolute) |

**Conclusion:** Choose between mini-frameworks and agenkit primitives based on API
familiarity and migration path — **not performance**.
