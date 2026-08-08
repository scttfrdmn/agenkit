# Agenkit Python

**Production-ready AI agent toolkit for Python 3.10+**

The Python implementation of Agenkit provides the reference implementation with the most complete feature set and best developer experience.

[![PyPI version](https://img.shields.io/pypi/v/agenkit)](https://pypi.org/project/agenkit/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](../../tests/)
[![Documentation](https://img.shields.io/badge/docs-agenkit.dev-blue)](https://agenkit.dev)

## Installation

```bash
pip install agenkit
```

### Optional Dependencies

```bash
# With LLM adapters
pip install agenkit[anthropic,openai]

# With observability
pip install agenkit[observability]

# Full installation
pip install agenkit[all]
```

## Quick Start

### Basic Agent

```python
from agenkit import Agent, Message

class EchoAgent(Agent):
    @property
    def name(self) -> str:
        return "echo-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["echo", "simple"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content=f"Echo: {message.content}"
        )

    def introspect(self) -> IntrospectionResult:
        return default_introspection_result(self)

# Use it
agent = EchoAgent()
response = await agent.process(Message(role="user", content="Hello!"))
print(response.content)  # "Echo: Hello!"
```

### Production-Ready Agent with Resilience

```python
from agenkit import Agent, Message
from agenkit.middleware import (
    RetryMiddleware,
    CircuitBreakerMiddleware,
    TimeoutMiddleware
)

# Create agent
agent = MyAgent()

# Add resilience
agent = RetryMiddleware(agent, max_retries=3, backoff_factor=2.0)
agent = CircuitBreakerMiddleware(agent, failure_threshold=5, recovery_timeout=60.0)
agent = TimeoutMiddleware(agent, timeout=30.0)

# Now it's production-ready with automatic retries, circuit breaking, and timeouts
response = await agent.process(message)
```

### Agent Patterns

#### Sequential Pipeline

```python
from agenkit.patterns import SequentialAgent

# Data flows: Agent1 → Agent2 → Agent3
pipeline = SequentialAgent([
    DataExtractionAgent(),
    AnalysisAgent(),
    ReportGenerationAgent()
])

result = await pipeline.process(message)
```

#### Parallel Execution

```python
from agenkit.patterns import ParallelAgent

# Execute multiple agents concurrently
parallel = ParallelAgent([
    SentimentAnalysisAgent(),
    EntityExtractionAgent(),
    TopicClassificationAgent()
])

result = await parallel.process(message)
# Results are automatically aggregated
```

#### Conversational Agent

```python
from agenkit.patterns import ConversationalAgent
from agenkit.adapters import AnthropicAdapter

# Maintains conversation history
agent = ConversationalAgent(
    llm=AnthropicAdapter(api_key="..."),
    system_prompt="You are a helpful assistant.",
    max_history=10
)

response1 = await agent.process(Message(content="What's the capital of France?"))
response2 = await agent.process(Message(content="What's its population?"))
# Agent remembers context from previous messages
```

#### ReAct (Reasoning + Acting)

```python
from agenkit.patterns import ReActAgent, Tool

class CalculatorTool(Tool):
    def name(self) -> str:
        return "calculator"

    def description(self) -> str:
        return "Evaluates mathematical expressions"

    async def execute(self, params: dict) -> ToolResult:
        expr = params["expression"]
        result = eval(expr)  # In production, use a safe evaluator
        return ToolResult(success=True, data=result)

# ReAct agent with tools
agent = ReActAgent(
    llm=my_llm,
    tools=[CalculatorTool(), WebSearchTool()],
    max_iterations=5
)

result = await agent.process(Message(content="What is 15% of 200?"))
```

### Reasoning Techniques

#### Chain-of-Thought (CoT)

```python
from agenkit.techniques.reasoning import ChainOfThought

# Step-by-step reasoning
cot = ChainOfThought(
    llm=my_llm,
    prompt_template="Let's solve this step by step:\n{query}",
    max_steps=5
)

result = await cot.process(Message(content="What is 15 * 24?"))
print(result.metadata["reasoning_steps"])
# ["1. Multiply 15 by 20: 300", "2. Multiply 15 by 4: 60", "3. Add: 360"]
```

#### Tree-of-Thought (ToT)

```python
from agenkit.techniques.reasoning import TreeOfThought, SearchStrategy

# Multi-path exploration with backtracking
tot = TreeOfThought(
    agent=my_agent,
    branching_factor=3,
    max_depth=4,
    strategy=SearchStrategy.BEST_FIRST,
    evaluator=lambda text: quality_score(text)
)

result = await tot.process(message)
print(result.metadata["reasoning_path"])  # Best path through tree
print(result.metadata["best_score"])       # 0.95
```

#### Self-Consistency

```python
from agenkit.techniques.reasoning import SelfConsistency

# Generate multiple reasoning paths and vote
sc = SelfConsistency(
    agent=my_cot_agent,
    num_samples=7,
    voting_strategy="majority"
)

result = await sc.process(message)
print(result.metadata["consistency_score"])  # 0.85
print(result.metadata["answer_counts"])      # {"42": 5, "40": 2}
```

### Observability

```python
from agenkit.observability import TracingMiddleware
from opentelemetry import trace

# Enable distributed tracing
tracer = trace.get_tracer(__name__)
agent = TracingMiddleware(agent, tracer=tracer)

# Now all agent calls are traced
with tracer.start_as_current_span("process_request"):
    result = await agent.process(message)
```

### Evaluation

```python
from agenkit.evaluation import BenchmarkRunner, Recorder

# Record agent sessions for regression testing
recorder = Recorder("./sessions")
agent = recorder.wrap(agent)

# Run benchmarks
runner = BenchmarkRunner()
results = await runner.run_benchmark(
    agent=agent,
    test_cases=my_test_cases
)

print(f"Success rate: {results.success_rate}")
print(f"Avg latency: {results.avg_latency_ms}ms")
```

## Package Structure

```
agenkit/
├── __init__.py              # Core exports
├── interfaces.py            # Agent, Message, Tool interfaces
├── introspection.py         # Agent introspection utilities
├── composition/             # Sequential, Parallel, Conditional
├── patterns/                # 32 agent patterns
│   ├── sequential.py        # Pipeline execution
│   ├── parallel.py          # Concurrent execution
│   ├── router.py            # Conditional routing
│   ├── conversational.py    # History management
│   ├── react.py             # Reasoning + Acting
│   ├── reflection.py        # Self-critique loop
│   ├── planning.py          # Task decomposition
│   ├── autonomous.py        # Goal-driven agents
│   ├── memory.py            # Memory hierarchy
│   └── ... [23 more patterns]
├── techniques/              # Reasoning techniques
│   └── reasoning/
│       ├── chain_of_thought.py     # CoT prompting
│       ├── tree_of_thought.py      # ToT search
│       ├── self_consistency.py     # Voting strategy
│       ├── graph_of_thought.py     # Graph reasoning
│       └── ... [more techniques]
├── middleware/              # Production middleware
│   ├── retry.py             # Automatic retries
│   ├── circuit_breaker.py   # Circuit breaker pattern
│   ├── timeout.py           # Timeout handling
│   ├── rate_limiter.py      # Rate limiting
│   ├── caching.py           # Response caching
│   └── batching.py          # Request batching
├── adapters/                # LLM adapters
│   ├── anthropic.py         # Claude API
│   ├── openai.py            # OpenAI API
│   ├── bedrock.py           # AWS Bedrock
│   └── gemini.py            # Google Gemini
├── transport/               # Communication protocols
│   ├── http.py              # HTTP/REST
│   ├── grpc.py              # gRPC
│   └── websocket.py         # WebSocket
├── observability/           # Tracing and metrics
│   ├── tracing.py           # OpenTelemetry integration
│   └── metrics.py           # Metrics collection
├── evaluation/              # Testing and optimization
│   ├── recorder.py          # Session recording
│   ├── benchmarks.py        # Performance benchmarks
│   └── optimizer.py         # Hyperparameter optimization
└── budget/                  # Token and cost management
    └── limiter.py           # Budget limiting
```

## API Reference

See [docs/API.md](../../docs/API.md) for complete API documentation.

## Examples

Comprehensive examples are available in [examples/](../../examples/):

- **Basics**: Simple agents, composition patterns
- **Patterns**: All 32 agent patterns with real-world use cases
- **Techniques**: CoT, ToT, Self-Consistency, and more
- **Integrations**: LLM adapters, observability, deployment
- **Production**: Resilience, scaling, monitoring

## Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_patterns.py

# Run with coverage
pytest --cov=agenkit
```

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run linting
ruff check agenkit/
black agenkit/

# Run type checking
mypy agenkit/
```

## Migration from Other Frameworks

See [docs/MIGRATION.md](../../docs/MIGRATION.md) for migration guides from:
- LangChain
- LlamaIndex
- Haystack
- Semantic Kernel

## Performance

Python is the reference implementation optimized for developer experience. For production workloads requiring maximum performance:

- **Go**: 18x faster, see [../agenkit-go/](../agenkit-go/)
- **Rust**: 22x faster, see [../agenkit-rust/](../agenkit-rust/)
- **C++**: 25x faster, see [../agenkit-cpp/](../agenkit-cpp/)

All implementations maintain 100% behavioral parity - write in Python, deploy in any language.

## Cross-Language Compatibility

Agenkit agents can communicate across languages using HTTP or gRPC:

```python
# Python agent calling Go agent
from agenkit.transport import HTTPClient

go_agent = HTTPClient("http://localhost:8080")
result = await go_agent.process(message)
```

See [docs/PATTERNS.md](../../docs/PATTERNS.md#cross-language) for details.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - See [LICENSE](../../LICENSE) for details.

## Links

- **Documentation**: https://agenkit.dev
- **GitHub**: https://github.com/scttfrdmn/agenkit
- **PyPI**: https://pypi.org/project/agenkit/
- **Discord**: https://discord.gg/agenkit
- **Twitter**: @agenkit

## Support

- **Issues**: https://github.com/scttfrdmn/agenkit/issues
- **Discussions**: https://github.com/scttfrdmn/agenkit/discussions
- **Email**: support@agenkit.dev
