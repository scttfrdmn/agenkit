# Pattern Examples

Comprehensive examples showcasing the 7 reusable pattern classes introduced in v0.33.0.

## Overview

This directory contains 46 pattern examples across all 5 languages (Python, Go, TypeScript, C++, Rust):

- **35 usage examples** (7 patterns × 5 languages)
- **2 composition examples** (combining multiple patterns)
- **2 LLM integration examples** (patterns with real LLM providers)

**Total: 5,211 lines of code**

## Directory Structure

```
patterns/
├── usage/              # Pattern usage examples (Python: full, others: templates)
│   ├── sequential-usage.py
│   ├── parallel-usage.py
│   ├── router-usage.py
│   ├── supervisor-usage.py
│   ├── collaborative-usage.py
│   ├── human-in-loop-usage.py
│   └── fallback-usage.py
├── composition/        # Pattern composition examples (Python)
│   ├── sequential-parallel.py
│   └── router-supervisor.py
└── llm-integration/    # LLM provider integration (Python)
    ├── patterns-with-openai.py
    └── patterns-with-anthropic.py
```

## The 7 Pattern Classes

### 1. Sequential Pattern (`sequential-usage.py`)
**Pipeline-style agent composition**

```python
from agenkit.patterns import SequentialAgent

pipeline = SequentialAgent([
    ExtractorAgent(),
    ModeratorAgent(),
    EnricherAgent(),
])
```

**Use cases:**
- Multi-stage data transformation
- Document processing workflows
- Step-by-step refinement

### 2. Parallel Pattern (`parallel-usage.py`)
**Concurrent execution with result aggregation**

```python
from agenkit.patterns import ParallelAgent, default_aggregators

analyzer = ParallelAgent(
    agents=[SentimentAnalyzer(), TopicClassifier(), EntityExtractor()],
    aggregator=default_aggregators["concatenate"],
)
```

**Use cases:**
- Ensemble methods and voting
- Multi-perspective analysis
- Independent parallel tasks
- Fault-tolerant processing

### 3. Router Pattern (`router-usage.py`)
**Conditional agent selection based on classification**

```python
from agenkit.patterns import RouterAgent, SimpleClassifier

router = RouterAgent(
    classifier=SupportClassifier(),
    routes={
        "technical": TechnicalAgent(),
        "billing": BillingAgent(),
        "general": GeneralAgent(),
    },
)
```

**Use cases:**
- Intent-based routing
- Specialized agent dispatch
- Dynamic workflow selection

### 4. Supervisor Pattern (`supervisor-usage.py`)
**Hierarchical coordination with task decomposition**

```python
from agenkit.patterns import SupervisorAgent, SimplePlanner

supervisor = SupervisorAgent(
    planner=CustomPlanner(),
    workers=[ResearchAgent(), AnalysisAgent(), WriterAgent()],
)
```

**Use cases:**
- Complex task decomposition
- Multi-step workflows
- Dynamic planning

### 5. Collaborative Pattern (`collaborative-usage.py`)
**Peer-to-peer collaboration with iterative refinement**

```python
from agenkit.patterns import CollaborativeAgent, CollaborativeConfig

collaborators = CollaborativeAgent(
    agents=[DraftAgent(), ReviewerAgent(), EditorAgent()],
    config=CollaborativeConfig(max_rounds=3, min_consensus=0.8),
)
```

**Use cases:**
- Peer review and feedback
- Consensus building
- Iterative refinement

### 6. Human-in-Loop Pattern (`human-in-loop-usage.py`)
**Human approval gates for high-stakes decisions**

```python
from agenkit.patterns import HumanInLoopAgent, HumanInLoopConfig

agent = HumanInLoopAgent(
    agent=TransactionAgent(),
    approval_func=custom_approval_func,
    config=HumanInLoopConfig(require_approval=True),
)
```

**Use cases:**
- Financial transaction approval
- Content moderation decisions
- Critical system changes

### 7. Fallback Pattern (`fallback-usage.py`)
**Sequential retry with automatic failover**

```python
from agenkit.patterns import FallbackAgent

fallback = FallbackAgent([
    PrimaryServiceAgent(),
    SecondaryServiceAgent(),
    FallbackServiceAgent(),
])
```

**Use cases:**
- Resilient service calls
- Multi-provider fallback
- Error recovery

## Running the Examples

### Python (Full Implementations)

```bash
# Pattern usage
python examples/patterns/usage/sequential-usage.py
python examples/patterns/usage/parallel-usage.py
python examples/patterns/usage/router-usage.py
python examples/patterns/usage/supervisor-usage.py
python examples/patterns/usage/collaborative-usage.py
python examples/patterns/usage/human-in-loop-usage.py
python examples/patterns/usage/fallback-usage.py

# Composition
python examples/patterns/composition/sequential-parallel.py
python examples/patterns/composition/router-supervisor.py

# LLM integration (requires API keys)
OPENAI_API_KEY=sk-... python examples/patterns/llm-integration/patterns-with-openai.py
ANTHROPIC_API_KEY=sk-... python examples/patterns/llm-integration/patterns-with-anthropic.py
```

### Other Languages (Templates)

See language-specific example directories:
- Go: `agenkit-go/examples/patterns/usage/`
- TypeScript: `agenkit-ts/examples/patterns/usage/`
- C++: `agenkit-cpp/examples/patterns/usage/`
- Rust: `agenkit-rust/examples/pattern-*-usage.rs`

Templates show structure; refer to Python examples for full implementations.

## Pattern Composition

### Sequential + Parallel
**Document analysis pipeline with parallel stages**

```python
# Stage 1: Parallel extraction
extraction = ParallelAgent([TextExtractor(), MetadataExtractor(), StructureExtractor()])

# Stage 2: Sequential processing
pipeline = SequentialAgent([
    extraction,
    NormalizationAgent(),
    ParallelAgent([SentimentAnalyzer(), TopicModeler(), QualityScorer()]),
    ReportGenerator(),
])
```

### Router + Supervisor
**Support system with specialized supervisors**

```python
# Create specialized supervisors
technical_supervisor = SupervisorAgent(planner=TechnicalPlanner(), workers=[...])
billing_supervisor = SupervisorAgent(planner=BillingPlanner(), workers=[...])

# Route to appropriate supervisor
router = RouterAgent(
    classifier=SupportClassifier(),
    routes={
        "technical": technical_supervisor,
        "billing": billing_supervisor,
    },
)
```

## LLM Integration

### With OpenAI

```python
from agenkit.adapters.llm import OpenAILLM
from agenkit.patterns import SequentialAgent

class LLMAgent(Agent):
    def __init__(self, name, system_prompt):
        self.llm = OpenAILLM(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o-mini")
        # ... implementation

pipeline = SequentialAgent([
    LLMAgent("Drafter", "Create a draft..."),
    LLMAgent("Reviewer", "Review and provide feedback..."),
    LLMAgent("Polisher", "Create final version..."),
])
```

### With Anthropic/Claude

```python
from agenkit.adapters.llm import AnthropicLLM
from agenkit.patterns import ParallelAgent

analyzer = ParallelAgent(
    agents=[
        ClaudeAgent("TechnicalAnalyst", "Analyze technical aspects..."),
        ClaudeAgent("BusinessAnalyst", "Analyze business value..."),
        ClaudeAgent("UXAnalyst", "Analyze user experience..."),
    ],
    aggregator=default_aggregators["concatenate"],
)
```

## Key Features Demonstrated

### 1. Realistic Use Cases
- Content moderation pipeline
- Support ticket routing
- Financial approval workflows
- Document analysis
- Research report generation

### 2. Error Handling
- Pipeline error propagation
- Partial failure handling
- Fallback and recovery strategies

### 3. Metadata Flow
- Tracking data through pipelines
- Accumulating context across stages
- Custom metadata for routing decisions

### 4. Advanced Patterns
- Custom aggregation functions
- Dynamic task planning
- Confidence-based approval
- Multi-stage composition

### 5. Production Patterns
- LLM integration
- Ensemble voting
- Resilient service calls
- Human-in-the-loop workflows

## Code Quality

All Python examples:
- ✅ Pass `ruff` linting
- ✅ Follow PEP 8 and type hints
- ✅ Include comprehensive docstrings
- ✅ Demonstrate error handling
- ✅ Use realistic scenarios (not toy examples)

## Learning Path

1. **Start with usage examples**: Understand each pattern individually
2. **Explore composition**: See how patterns combine
3. **Try LLM integration**: Connect patterns to real AI models
4. **Build your own**: Adapt patterns to your use cases

## Contributing

When adding new examples:
1. Follow existing structure and naming conventions
2. Include comprehensive docstrings with use cases
3. Demonstrate multiple scenarios (basic + advanced)
4. Add error handling examples
5. Ensure code passes language-specific linters
6. Update this README

## Related Documentation

- [Pattern Library Documentation](../../docs/patterns/)
- [v0.33.0 Release Notes](../../CHANGELOG.md)
- [API Reference](../../docs/api/)

## Support

For questions or issues:
- GitHub Issues: https://github.com/scttfrdmn/agenkit/issues
- Documentation: https://agenkit.dev/patterns
- Examples Repository: https://github.com/scttfrdmn/agenkit-examples

---

**Version**: v0.34.0
**Last Updated**: 2024-11-29
**Issue**: Closes #206
