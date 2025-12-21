# AGENTS.md Support

Give AI agents automatic context about your project with AGENTS.md.

## What is AGENTS.md?

**AGENTS.md** is an industry standard format (from OpenAI/Agentic AI Foundation) for providing instructions to AI coding agents.

Think of it as a **"README for AI agents"**.

### The Problem

When using AI assistants, you constantly repeat:
- "Follow PEP 8 style"
- "Add type hints"
- "Use pytest for testing"
- "Follow our error handling pattern"

This is repetitive and inconsistent across different AI tools.

### The Solution

Create a single `AGENTS.md` file documenting your project conventions:

```markdown
# AGENTS.md

## Setup
```bash
pip install -r requirements.txt
```

## Code Style
- Use type hints on all functions
- Follow PEP 8
- Max line length: 88 chars

## Testing
- Use pytest
- Aim for 80% coverage
- Test files: test_*.py
```

AI tools (Cursor, Windsurf, Continue, Agenkit, etc.) automatically read and apply these instructions.

---

## Quick Start

### 1. Create AGENTS.md

```markdown
# AGENTS.md

## Setup
How to install and configure

## Code Style
Your coding conventions

## Testing
How to run tests
```

### 2. Use with Agenkit

```python
from agenkit.agents_md import AgentsMdMiddleware

# Wrap your agent
agent = MyLLMAgent()
agent_with_context = AgentsMdMiddleware(agent, project_root=".")

# Context injected automatically!
response = await agent_with_context.process(message)
```

That's it! Your agent now has full project context.

---

## Features

### Parser
Parse AGENTS.md files into structured data:

```python
from agenkit.agents_md import parse_agents_md

doc = parse_agents_md("./AGENTS.md")
setup = doc.get_section(SectionType.SETUP)
print(setup.content)
```

### Validator
Validate format and completeness:

```python
from agenkit.agents_md import validate_agents_md

result = validate_agents_md(doc, strict=True)
if not result.is_valid:
    for issue in result.issues:
        print(issue)
```

### Middleware
Automatic context injection:

```python
from agenkit.agents_md import AgentsMdMiddleware

# Auto-discover and inject
agent = AgentsMdMiddleware(base_agent, project_root=".")
```

---

## Standard Sections

| Section | Purpose |
|---------|---------|
| **Setup** | Installation & configuration |
| **Code Style** | Coding conventions |
| **Testing** | Test procedures |
| **Architecture** | System design |
| **Patterns** | Common patterns |
| **Deployment** | Production procedures |
| **Security** | Security practices |
| **Contributing** | Contribution guidelines |

---

## Hierarchical Support

Support nested AGENTS.md files:

```
project/
├── AGENTS.md           # Global rules
├── frontend/
│   └── AGENTS.md       # Frontend-specific
└── backend/
    └── AGENTS.md       # Backend-specific
```

Agenkit automatically finds and merges all relevant AGENTS.md files, with more specific rules overriding general ones.

---

## Adoption

- **60,000+** projects using AGENTS.md
- **30+** AI tools with support
- **Industry standard** format

Tools that support AGENTS.md:
- Cursor
- Windsurf
- Continue
- GitHub Copilot (via extensions)
- Claude Code (Agenkit)
- And many more...

---

## Benefits

✅ **No Repetition**: Document once, use everywhere

✅ **Consistency**: Same instructions across all AI tools

✅ **Living Documentation**: Keep it current with code

✅ **Automatic**: Zero manual work with middleware

✅ **Standard**: Works with 30+ tools

---

## Learn More

- [Quick Start Guide](quick-start.md)
- [Format Specification](format.md)
- [Best Practices](best-practices.md)
- [Examples](examples.md)

---

## Complete Documentation

For the full guide, see [docs/AGENTS_MD.md](../../docs/AGENTS_MD.md) in the repository.

---

## Example Code

```python
"""
Complete example using AGENTS.md with Agenkit.
"""
from agenkit import Agent, Message
from agenkit.agents_md import AgentsMdMiddleware

# Your LLM agent
class MyLLMAgent(Agent):
    async def process(self, message: Message) -> Message:
        # Your LLM logic here
        pass

# Wrap with AGENTS.md middleware
agent = MyLLMAgent()
agent_with_context = AgentsMdMiddleware(agent, project_root=".")

# Now when you use the agent, it has full project context
# from AGENTS.md automatically!
response = await agent_with_context.process(Message(
    role="user",
    content="Write a function to calculate totals"
))

# The agent's response will follow your code style,
# testing conventions, and architectural patterns
# from AGENTS.md - without you repeating them!
```

---

## Resources

- [AGENTS.md Specification](https://agents.md/)
- [Agenkit Examples](../../examples/agents_md/)
- [API Reference](../api/python.md)

---

**Start using AGENTS.md today!** It's the easiest way to give AI agents context about your project.
