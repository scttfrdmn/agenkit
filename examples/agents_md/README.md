# AGENTS.md Support Examples

Examples demonstrating AGENTS.md support in Agenkit.

## What is AGENTS.md?

**AGENTS.md** is a standard format for providing instructions to AI coding agents. It's like a README but specifically for AI assistants working on your codebase.

### Benefits

- **Automatic Context**: Agents learn your project conventions automatically
- **Consistency**: Same instructions across all AI tools (Cursor, Windsurf, Continue, etc.)
- **No Repetition**: Document once, use everywhere
- **Hierarchical**: Support nested AGENTS.md files in subdirectories

### Standard Sections

- **Setup**: Installation and configuration
- **Code Style**: Coding conventions and patterns
- **Testing**: How to run and write tests
- **Architecture**: System design and organization
- **Patterns**: Common patterns used in the codebase
- **Deployment**: Production deployment procedures

## Examples

### 1. Basic Usage

**File**: `basic_usage.py`

Demonstrates:
- Parsing AGENTS.md files
- Accessing sections
- Validating format
- Converting to prompt context

```bash
python examples/agents_md/basic_usage.py
```

### 2. Middleware Integration

**File**: `middleware_integration.py`

Demonstrates:
- Using `AgentsMdMiddleware` to wrap agents
- Automatic context injection
- How context improves agent responses

```bash
python examples/agents_md/middleware_integration.py
```

### 3. Example AGENTS.md

**File**: `AGENTS.md`

A complete example AGENTS.md file showing:
- All standard sections
- Code examples
- Best practices
- Documentation patterns

## Quick Start

### 1. Create AGENTS.md in Your Project

```markdown
# AGENTS.md

## Setup
Instructions for setting up the project

## Code Style
Your coding conventions

## Testing
How to run tests

## Architecture
System design overview

## Common Patterns
Frequently used patterns
```

### 2. Use in Your Agent

```python
from agenkit import Agent, Message
from agenkit.agents_md import AgentsMdMiddleware

# Your agent
agent = MyLLMAgent()

# Wrap with AGENTS.md middleware
agent_with_context = AgentsMdMiddleware(agent, project_root=".")

# Agent now has project context automatically
response = await agent_with_context.process(
    Message(role="user", content="Write a function following our code style")
)
```

### 3. Parse Manually (Optional)

```python
from agenkit.agents_md import parse_agents_md, validate_agents_md

# Parse
doc = parse_agents_md("./AGENTS.md")

# Validate
result = validate_agents_md(doc)
if not result.is_valid:
    for issue in result.issues:
        print(issue)

# Get specific sections
setup = doc.get_section(SectionType.SETUP)
print(setup.content)
```

## API Reference

### Parser

```python
from agenkit.agents_md import parse_agents_md

# Parse single file
doc = parse_agents_md("./AGENTS.md")

# Find all AGENTS.md in hierarchy
from agenkit.agents_md import find_agents_md_hierarchy

hierarchy = find_agents_md_hierarchy(".")
```

### Validator

```python
from agenkit.agents_md import validate_agents_md

result = validate_agents_md(doc)
print(result.is_valid)
print(result.issues)
print(result.recommendations)
```

### Middleware

```python
from agenkit.agents_md import AgentsMdMiddleware

# Auto-discovery and injection
agent = AgentsMdMiddleware(base_agent, project_root=".")

# Clear cache to reload files
agent.clear_cache()

# Manually reload
agent.reload()
```

### Data Structures

```python
from agenkit.agents_md.types import (
    AgentsMdDocument,
    AgentsMdSection,
    SectionType,
)

# Section types
SectionType.SETUP
SectionType.CODE_STYLE
SectionType.TESTING
SectionType.ARCHITECTURE
SectionType.PATTERNS
SectionType.DEPLOYMENT
SectionType.SECURITY
SectionType.CONTRIBUTING
SectionType.CUSTOM

# Document methods
doc.get_section(SectionType.SETUP)
doc.has_section(SectionType.TESTING)
doc.to_prompt_context()
```

## Best Practices

### 1. Start Simple

Begin with just Setup and Code Style:

```markdown
## Setup
pip install -r requirements.txt

## Code Style
- Use type hints
- Follow PEP 8
- Add docstrings
```

### 2. Add Examples

Include code examples in sections:

```markdown
## Code Style

Use type hints:
```python
def calculate(x: int, y: int) -> int:
    return x + y
```
```

### 3. Keep It Current

Update AGENTS.md when conventions change. Think of it as living documentation.

### 4. Use Hierarchical Structure

Root `AGENTS.md` for project-wide rules, subdirectory `AGENTS.md` for module-specific:

```
project/
├── AGENTS.md           # Project-wide conventions
├── src/
│   └── api/
│       └── AGENTS.md   # API-specific patterns
```

### 5. Validate Regularly

```bash
# Create a validation script
python -c "
from agenkit.agents_md import parse_agents_md, validate_agents_md
doc = parse_agents_md('./AGENTS.md')
result = validate_agents_md(doc, strict=True)
exit(0 if result.is_valid else 1)
"
```

## Use Cases

### Use Case 1: Consistent Code Style

**Problem**: AI agents generate code in different styles
**Solution**: Document style in AGENTS.md

```markdown
## Code Style
- Function names: snake_case
- Class names: PascalCase
- Constants: UPPER_CASE
- Max line length: 88 chars
```

### Use Case 2: Project Setup

**Problem**: Agents don't know how to set up project
**Solution**: Document setup in AGENTS.md

```markdown
## Setup
1. `uv sync` - Install dependencies
2. `cp .env.example .env` - Configure environment
3. `uv run pytest` - Verify setup
```

### Use Case 3: Testing Standards

**Problem**: Agents write tests inconsistently
**Solution**: Document testing in AGENTS.md

```markdown
## Testing
- Use pytest
- Aim for 80% coverage
- Test file naming: test_*.py
- Use fixtures for setup
```

## Integration with Tools

AGENTS.md is supported by:
- **Cursor**: Reads automatically
- **Windsurf**: Auto-discovery
- **Continue**: Built-in support
- **GitHub Copilot**: Via extensions
- **Claude Code (Agenkit)**: Full support via middleware

## Resources

- [AGENTS.md Specification](https://agents.md/)
- [Agenkit Documentation](../../docs/)
- [Example AGENTS.md](AGENTS.md)

## Related Examples

- [LLM Integration](../llm/) - Using AGENTS.md with LLMs
- [Patterns](../patterns/) - Agent patterns with context
- [Observability](../observability/) - Monitoring context injection

---

**Start using AGENTS.md today!** It's the easiest way to give AI agents context about your project.
