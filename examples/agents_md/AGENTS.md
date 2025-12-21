# Example AGENTS.md

This is an example AGENTS.md file showing the standard format for providing
instructions to AI coding agents.

## Setup

To set up this example project:

```bash
# Install dependencies
pip install agenkit

# Set API keys (if using LLMs)
export OPENAI_API_KEY="sk-..."
```

## Code Style

Follow these coding conventions:

- Use type hints for all function signatures
- Follow PEP 8 style guidelines
- Use descriptive variable names (no single letters except loop counters)
- Add docstrings to all public functions
- Keep functions under 50 lines when possible

Example:
```python
def calculate_total(items: list[float]) -> float:
    """Calculate the total sum of items."""
    return sum(items)
```

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_agents_md.py

# Run with coverage
pytest --cov=agenkit
```

Write tests for all new features. Aim for 80%+ coverage.

## Architecture

This project uses a layered architecture:

- `agenkit/`: Core agent framework
- `agenkit/agents_md/`: AGENTS.md support module
  - `parser.py`: Parse AGENTS.md files
  - `validator.py`: Validate format
  - `integration.py`: Inject context into agents
- `examples/`: Example code demonstrating features
- `tests/`: Test suite

## Common Patterns

### Pattern 1: Wrapping Agents with Middleware

```python
from agenkit import Agent
from agenkit.agents_md import AgentsMdMiddleware

agent = MyAgent()
agent_with_context = AgentsMdMiddleware(agent, project_root=".")
```

### Pattern 2: Parsing AGENTS.md Manually

```python
from agenkit.agents_md import parse_agents_md

doc = parse_agents_md("./AGENTS.md")
setup = doc.get_section(SectionType.SETUP)
```

## Deployment

For production deployment:

1. Set environment variables
2. Use production LLM keys
3. Enable monitoring
4. Configure rate limiting

See `docs/deployment/` for detailed instructions.
