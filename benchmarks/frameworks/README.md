# Framework Performance Benchmarks

Measures orchestration overhead of mini-frameworks vs Agenkit primitives (Issue #479).

## Benchmark Scenarios

| File | Compares | Iterations |
|------|----------|-----------|
| `bench_simple_chain.py` | `LLMChain.run` vs direct `LLM.complete` vs `Agent.process` | 100 |
| `bench_sequential.py` | `SequentialChain` vs `SequentialAgent` (3 agents) | 100 |
| `bench_parallel.py` | `Crew(parallel)` vs `ParallelAgent` (3 agents) | 100 |
| `bench_conversational.py` | `ConversationChain` vs `ConversationalAgent` (10 turns) | 50 |
| `bench_router.py` | `RouterChain` vs `RouterAgent` | 100 |

All benchmarks use `MockLLM` with zero latency to measure pure framework overhead.

## Running

```bash
# Run all benchmarks
cd /path/to/agenkit
uv run python benchmarks/frameworks/run_all.py

# Run individual benchmark
uv run python benchmarks/frameworks/bench_simple_chain.py
```

## Output

Results are saved as JSON to `results/results_{timestamp}.json`.

Example output:
```
Suite                Scenario                          mean_ms   p50_ms   p95_ms     iter/s
--------------------------------------------------------------------------------
simple_chain         LLMChain.run                       0.0123   0.0118   0.0189    81300.5
simple_chain         direct_llm_complete                0.0089   0.0085   0.0142   112359.5
...
```

## Interpretation

The overhead shown is pure Python async dispatch overhead from the framework
abstraction layers. Real-world numbers will be dominated by LLM API latency (100-3000ms),
making this overhead negligible in production.
