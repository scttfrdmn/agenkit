# Multi-LLM Cost Optimizer

Intelligent LLM routing system that optimizes costs while maintaining quality by routing requests to appropriate models based on complexity.

## Overview

Demonstrates **cost-optimized LLM routing** with automatic complexity classification, intelligent model selection, and fallback strategies.

**Key Features:**
- **Complexity Classification**: Automatically classifies requests (simple/medium/complex/critical)
- **Smart Routing**: Routes to optimal model based on complexity and cost
- **Cost Tracking**: Monitors spending and calculates savings
- **Fallback Support**: Automatic fallback to alternative models on failure
- **Budget Management**: Optional budget limits

## Quick Start

```bash
cd examples/e2e/llm-optimizer

# Run demo
python3 main.py

# Interactive mode
python3 main.py interactive
```

## How It Works

1. **Classify**: Analyze request complexity
2. **Route**: Select optimal model (balancing cost vs quality)
3. **Execute**: Call selected LLM with fallback support
4. **Track**: Record costs and metrics

## Model Configuration

| Model | Cost/1K tokens | Quality | Use Case |
|-------|---------------|---------|----------|
| gpt-4 | $0.030 | 9.5/10 | Critical requests |
| claude-2 | $0.010 | 9.0/10 | Complex requests |
| gpt-3.5-turbo | $0.002 | 7.5/10 | Standard requests |
| llama-2-70b | $0.001 | 6.5/10 | Simple requests |

## Routing Logic

- **Simple** (< 50 tokens, basic queries) → llama-2-70b ($0.001/1K)
- **Medium** (50-200 tokens, standard) → gpt-3.5-turbo ($0.002/1K)
- **Complex** (> 200 tokens, analysis) → claude-2 ($0.010/1K)
- **Critical** (medical, legal, financial) → gpt-4 ($0.030/1K)

## Example Output

```
======================================================================
REQUEST: What is Python?
======================================================================
Complexity: simple (confidence: 0.85)
Reasoning: Short prompt (3 tokens) or simple keywords
Primary Model: llama-2-70b
Estimated Cost: $0.000003
✓ Success with llama-2-70b (800ms, $0.000003)

======================================================================
COST OPTIMIZATION SUMMARY
======================================================================
Total Requests: 5
Total Cost: $0.000156
Avg Cost/Request: $0.000031
Success Rate: 100.0%

Cost Analysis:
  If all requests used gpt-4: $0.001500
  Actual cost with routing: $0.000156
  💰 Savings: $0.001344 (89.6% reduction)
```

## Programmatic Usage

```python
from llm_optimizer import ComplexityClassifier, CostTracker, LLMRouter

# Initialize
classifier = ComplexityClassifier()
cost_tracker = CostTracker()
router = LLMRouter(classifier, cost_tracker, budget_limit=10.0)

# Execute with automatic routing
response = await router.execute("Explain quantum computing")

# Get statistics
stats = cost_tracker.get_stats()
print(f"Total cost: ${stats['total_cost']:.6f}")
print(f"Requests: {stats['total_requests']}")
```

## Components

### ComplexityClassifier
Classifies request complexity using heuristics:
- Token count
- Keyword analysis
- Context length
- Domain detection (medical, legal, etc.)

### LLMRouter
Routes requests to optimal model:
- Considers complexity classification
- Checks budget constraints
- Selects best cost/quality balance
- Handles fallbacks automatically

### CostTracker
Tracks usage and costs:
- Per-request metrics
- Model-level aggregation
- Cost savings calculation
- Success rate monitoring

## Production Enhancements

**Current (Demo):**
- Heuristic classification
- Mock LLM calls
- Fixed model configs

**Production:**
- ML-based complexity classifier
- Real API integrations (OpenAI, Anthropic, etc.)
- Dynamic pricing from APIs
- Caching layer
- Rate limiting
- Load balancing

## Extending

### Add Custom Models

```python
from llm_optimizer import LLMModel, MODELS

MODELS["custom-model"] = LLMModel(
    name="custom-model",
    cost_per_1k_tokens=0.005,
    max_tokens=8192,
    quality_score=8.0,
    latency_ms=1000,
    provider="custom",
)
```

### Custom Routing Logic

```python
class CustomRouter(LLMRouter):
    def route(self, prompt, context=None):
        # Your custom routing logic
        if "urgent" in prompt.lower():
            return RoutingDecision(
                primary_model="gpt-4",
                fallback_models=["claude-2"],
                reasoning="Urgent request",
                estimated_cost=0.03,
            )
        return super().route(prompt, context)
```

## Cost Savings

Typical savings: **70-90%** compared to always using premium models

Example scenarios:
- 100 simple queries: Save $2.90 (llama-2 vs gpt-4)
- 100 medium queries: Save $2.80 (gpt-3.5 vs gpt-4)
- Mixed workload: Save 80%+ on average

---

**Built with AgentKit** - Production-grade multi-agent framework for Python
