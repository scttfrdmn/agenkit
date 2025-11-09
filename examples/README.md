# agenkit Examples

Practical examples demonstrating agenkit usage.

## Running Examples

```bash
# Make sure you're in the project directory
cd /path/to/agenkit

# Run any example
python examples/01_basic_agent.py
```

## Examples

### [01_basic_agent.py](01_basic_agent.py)
**Basic Agent Creation**

Learn how to create a simple agent that processes messages.

Key concepts:
- Agent interface
- Message creation
- Async processing

```bash
python examples/01_basic_agent.py
```

---

### [02_sequential_pattern.py](02_sequential_pattern.py)
**Sequential Pattern (Pipeline)**

Chain agents in a pipeline where output of one becomes input of next.

Key concepts:
- SequentialPattern
- Validation → Processing → Formatting pipeline
- Error propagation

```bash
python examples/02_sequential_pattern.py
```

---

### [03_parallel_pattern.py](03_parallel_pattern.py)
**Parallel Pattern (Fan-out)**

Run multiple agents concurrently on the same input.

Key concepts:
- ParallelPattern
- Concurrent execution
- Result aggregation
- Multiple analysis (sentiment, length, keywords)

```bash
python examples/03_parallel_pattern.py
```

---

### [04_router_pattern.py](04_router_pattern.py)
**Router Pattern (Conditional Dispatch)**

Route messages to different agents based on content.

Key concepts:
- RouterPattern
- Intent-based routing
- Specialized agents (weather, news, calculator, general)

```bash
python examples/04_router_pattern.py
```

---

### [05_tool_usage.py](05_tool_usage.py)
**Tool Usage**

Create and use tools within agents.

Key concepts:
- Tool interface
- ToolResult
- Search and calculator tools
- Error handling

```bash
python examples/05_tool_usage.py
```

---

### [06_pattern_composition.py](06_pattern_composition.py)
**Pattern Composition**

Compose patterns to create complex workflows.

Key concepts:
- Patterns of patterns
- Sequential [ Parallel [ ... ], Router { ... } ]
- Metadata propagation
- Multi-stage processing

```bash
python examples/06_pattern_composition.py
```

---

## Learning Path

We recommend following the examples in order:

1. **01_basic_agent.py** - Start here to understand the fundamentals
2. **02_sequential_pattern.py** - Learn to chain agents
3. **03_parallel_pattern.py** - Learn concurrent processing
4. **04_router_pattern.py** - Learn conditional routing
5. **05_tool_usage.py** - Learn tool integration
6. **06_pattern_composition.py** - Put it all together

## Next Steps

- Read the [API Documentation](../docs/API.md) for detailed reference
- Check out [Architecture](../ARCHITECTURE.md) for design principles
- See [Benchmarks](../benchmarks/test_overhead.py) for performance details

## Need Help?

- Review the [Vision Document](../AGENKIT_VISION.md) for the big picture
- Check [tests/](../tests/) for more usage examples
- Open an issue on GitHub (coming soon)
