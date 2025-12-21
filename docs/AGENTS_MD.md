# AGENTS.md Support

Complete guide to using AGENTS.md with Agenkit.

## Table of Contents

- [What is AGENTS.md?](#what-is-agentsmd)
- [Quick Start](#quick-start)
- [Format Specification](#format-specification)
- [Using with Agenkit](#using-with-agenkit)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)
- [Examples](#examples)
- [FAQ](#faq)

---

## What is AGENTS.md?

**AGENTS.md** is an emerging standard format (from OpenAI/Agentic AI Foundation) for providing instructions to AI coding agents.

### The Problem

When working with AI coding assistants, you often need to repeat:
- "Follow PEP 8 style"
- "Add type hints"
- "Write tests with pytest"
- "Use our standard error handling"

This gets repetitive and inconsistent across different AI tools.

### The Solution

**AGENTS.md** provides a single source of truth for project conventions:

```markdown
# AGENTS.md

## Code Style
- Follow PEP 8
- Use type hints on all functions
- Max line length: 88 chars

## Testing
- Use pytest for all tests
- Aim for 80% coverage
- Test files: test_*.py
```

AI tools (Cursor, Windsurf, Continue, Agenkit, etc.) automatically read and apply these instructions.

### Adoption

- **60,000+** projects using AGENTS.md
- **30+** AI tools with support
- **Standard format** across the industry

---

## Quick Start

### 1. Create AGENTS.md

Create `AGENTS.md` in your project root:

```markdown
# AGENTS.md

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env
```

## Code Style
- Use type hints
- Follow PEP 8
- Add docstrings to public functions

## Testing
Run tests with `pytest`
```

### 2. Use with Agenkit

```python
from agenkit import Agent, Message
from agenkit.agents_md import AgentsMdMiddleware

# Your agent
agent = MyLLMAgent()

# Wrap with AGENTS.md middleware
agent = AgentsMdMiddleware(agent, project_root=".")

# Agent automatically gets project context
response = await agent.process(Message(
    role="user",
    content="Write a function to calculate totals"
))
# Response will follow your code style from AGENTS.md!
```

### 3. Verify It Works

```python
from agenkit.agents_md import parse_agents_md, validate_agents_md

# Parse
doc = parse_agents_md("./AGENTS.md")

# Validate
result = validate_agents_md(doc)
if result.is_valid:
    print("✓ AGENTS.md is valid!")
else:
    for issue in result.issues:
        print(f"✗ {issue}")
```

---

## Format Specification

### Basic Structure

```markdown
# AGENTS.md

## Section Name
Section content with markdown formatting

## Another Section
More content
```

### Standard Sections

#### Setup
How to install and configure the project.

```markdown
## Setup

Install dependencies:
```bash
pip install -r requirements.txt
```

Configure:
```bash
cp .env.example .env
```
```

#### Code Style
Coding conventions and style guidelines.

```markdown
## Code Style

- Function names: `snake_case`
- Class names: `PascalCase`
- Constants: `UPPER_CASE`
- Max line length: 88 chars
- Use type hints on all functions

Example:
```python
def calculate_total(items: list[float]) -> float:
    """Calculate sum of items."""
    return sum(items)
```
```

#### Testing
How to run tests and testing conventions.

```markdown
## Testing

Run all tests:
```bash
pytest
```

Run specific test:
```bash
pytest tests/test_feature.py
```

Testing conventions:
- Use pytest fixtures
- Aim for 80% coverage
- Test files: `test_*.py`
```

#### Architecture
System design and module organization.

```markdown
## Architecture

Layered architecture:
- `src/api/`: HTTP API layer
- `src/services/`: Business logic
- `src/models/`: Data models
- `src/utils/`: Utilities

Follow dependency injection pattern.
```

#### Patterns
Common patterns used in the codebase.

```markdown
## Common Patterns

### Error Handling
```python
try:
    result = operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### Async Operations
Use `asyncio` for I/O operations:
```python
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        return await session.get(url)
```
```

#### Deployment
Production deployment procedures.

```markdown
## Deployment

Deploy to production:
```bash
./scripts/deploy.sh production
```

Environment variables:
- `DATABASE_URL`: PostgreSQL connection
- `REDIS_URL`: Redis cache
- `API_KEY`: Service API key
```

### Custom Sections

Add any sections relevant to your project:

```markdown
## Database
- Use migrations for schema changes
- Run `alembic upgrade head` after pull

## API Design
- RESTful endpoints
- JSON responses
- Use HTTP status codes correctly
```

---

## Using with Agenkit

### Middleware (Recommended)

Automatically inject AGENTS.md context:

```python
from agenkit.agents_md import AgentsMdMiddleware

# Wrap your agent
agent = MyLLMAgent()
agent_with_context = AgentsMdMiddleware(agent, project_root=".")

# Context injected automatically
response = await agent_with_context.process(message)
```

**Benefits**:
- Zero manual work
- Automatic discovery
- Hierarchical support (finds AGENTS.md in parent directories)
- Caching for performance

### Manual Parsing

For custom integration:

```python
from agenkit.agents_md import parse_agents_md

# Parse AGENTS.md
doc = parse_agents_md("./AGENTS.md")

# Access sections
setup = doc.get_section(SectionType.SETUP)
print(setup.content)

# Convert to prompt context
context = doc.to_prompt_context()
prompt = f"{context}\n\nUser: {user_message}"
```

### Hierarchical Context

Support nested AGENTS.md files:

```
project/
├── AGENTS.md           # Project-wide rules
├── src/
│   ├── api/
│   │   └── AGENTS.md   # API-specific rules
│   └── services/
│       └── AGENTS.md   # Service-specific rules
```

```python
from agenkit.agents_md import find_agents_md_hierarchy

# Find all AGENTS.md files
hierarchy = find_agents_md_hierarchy("./src/api")
# Returns: {
#   Path("."): root_doc,
#   Path("./src"): src_doc,
#   Path("./src/api"): api_doc,
# }

# Most specific rules win (api_doc overrides src_doc)
```

### Validation

Ensure AGENTS.md quality:

```python
from agenkit.agents_md import validate_agents_md

result = validate_agents_md(doc, strict=True)

# Check result
if not result.is_valid:
    print("Validation failed!")
    for issue in result.issues:
        print(f"  {issue.severity}: {issue.message}")

# Get recommendations
for rec in result.recommendations:
    print(f"Recommendation: {rec}")
```

### Caching

Middleware caches parsed documents:

```python
# Enable caching (default)
agent = AgentsMdMiddleware(agent, cache_enabled=True)

# Clear cache to reload
agent.clear_cache()

# Manually reload
agent.reload()
```

---

## Best Practices

### 1. Start Simple, Grow Organically

Begin with essentials:

```markdown
## Setup
pip install -r requirements.txt

## Code Style
- Use type hints
- Follow PEP 8
```

Add sections as needed.

### 2. Include Code Examples

Examples are clearer than rules:

```markdown
## Error Handling

Do this:
```python
try:
    result = operation()
except SpecificError:
    logger.error("Failed")
    raise
```

Not this:
```python
try:
    result = operation()
except:  # Too broad!
    pass
```
```

### 3. Keep It Current

Update AGENTS.md when conventions change. Treat it as living documentation.

**Good**: Update AGENTS.md in the same PR that changes conventions
**Bad**: Let AGENTS.md get stale and incorrect

### 4. Validate in CI

Add validation to CI:

```yaml
# .github/workflows/validate.yml
- name: Validate AGENTS.md
  run: |
    python -c "
    from agenkit.agents_md import parse_agents_md, validate_agents_md
    doc = parse_agents_md('./AGENTS.md')
    result = validate_agents_md(doc, strict=True)
    exit(0 if result.is_valid else 1)
    "
```

### 5. Use Hierarchical Structure

Global rules at root, specific rules in subdirectories:

```
project/
├── AGENTS.md           # Global: Python version, testing, CI/CD
├── frontend/
│   └── AGENTS.md       # Frontend: React patterns, styling
├── backend/
│   └── AGENTS.md       # Backend: API design, database
└── ml/
    └── AGENTS.md       # ML: Model training, data pipelines
```

### 6. Document "Why", Not Just "What"

```markdown
## Code Style

Use type hints on all functions.
**Why**: Type hints catch bugs early and improve IDE support.

Max line length: 88 chars.
**Why**: Readable on small screens, works with `black` formatter.
```

### 7. Link to Detailed Docs

AGENTS.md is a summary. Link to full docs:

```markdown
## Architecture

High-level overview:
- API layer handles HTTP
- Service layer contains business logic
- Data layer manages persistence

For detailed architecture, see [docs/architecture.md](docs/architecture.md)
```

---

## API Reference

### Parser

#### `parse_agents_md(path: str | Path) -> AgentsMdDocument`

Parse AGENTS.md file.

**Args**:
- `path`: Path to AGENTS.md file

**Returns**: Parsed document

**Raises**:
- `FileNotFoundError`: File doesn't exist
- `ValueError`: File is empty or invalid

**Example**:
```python
doc = parse_agents_md("./AGENTS.md")
```

#### `find_agents_md(start_dir: str | Path) -> list[Path]`

Find AGENTS.md files in hierarchy.

**Args**:
- `start_dir`: Directory to start search

**Returns**: List of AGENTS.md paths (closest first)

**Example**:
```python
files = find_agents_md("./src")
# [Path("./src/AGENTS.md"), Path("./AGENTS.md")]
```

#### `find_agents_md_hierarchy(start_dir: str | Path) -> dict[Path, AgentsMdDocument]`

Find and parse all AGENTS.md in hierarchy.

**Args**:
- `start_dir`: Directory to start search

**Returns**: Dict mapping directories to parsed documents

**Example**:
```python
hierarchy = find_agents_md_hierarchy(".")
for dir_path, doc in hierarchy.items():
    print(f"{dir_path}: {len(doc.sections)} sections")
```

### Validator

#### `validate_agents_md(doc: AgentsMdDocument, strict: bool = False) -> ValidationResult`

Validate AGENTS.md document.

**Args**:
- `doc`: Document to validate
- `strict`: If True, missing recommended sections are errors

**Returns**: Validation result

**Example**:
```python
result = validate_agents_md(doc, strict=True)
if not result.is_valid:
    for issue in result.issues:
        print(issue)
```

### Middleware

#### `AgentsMdMiddleware(agent, project_root=".", cache_enabled=True)`

Middleware that injects AGENTS.md context.

**Args**:
- `agent`: Agent to wrap
- `project_root`: Root directory for discovery
- `cache_enabled`: Whether to cache parsed documents

**Methods**:
- `clear_cache()`: Clear cached documents
- `reload()`: Reload from disk

**Example**:
```python
agent = AgentsMdMiddleware(base_agent, project_root=".")
response = await agent.process(message)
```

### Types

#### `AgentsMdDocument`

Parsed document.

**Attributes**:
- `path`: Path to file
- `sections`: List of sections
- `raw_content`: Original content
- `metadata`: Document metadata

**Methods**:
- `get_section(type)`: Get first section of type
- `get_sections(type)`: Get all sections of type
- `has_section(type)`: Check if section exists
- `to_prompt_context()`: Convert to prompt string

#### `AgentsMdSection`

A section from document.

**Attributes**:
- `type`: Section type
- `heading`: Heading text
- `content`: Section content
- `level`: Heading level (1-6)
- `line_number`: Starting line

**Methods**:
- `is_empty()`: Check if section is empty

#### `SectionType`

Standard section types.

**Values**:
- `SETUP`
- `CODE_STYLE`
- `TESTING`
- `ARCHITECTURE`
- `PATTERNS`
- `DEPLOYMENT`
- `SECURITY`
- `CONTRIBUTING`
- `CUSTOM`

---

## Examples

See [`examples/agents_md/`](../examples/agents_md/) for complete examples:

1. **Basic Usage** (`basic_usage.py`): Parsing and validation
2. **Middleware Integration** (`middleware_integration.py`): Automatic context injection
3. **Example AGENTS.md** (`AGENTS.md`): Complete format example

---

## FAQ

### Q: Do I need AGENTS.md to use Agenkit?

**A**: No! AGENTS.md is optional. It's a convenience feature to give agents project context automatically.

### Q: What if I don't have AGENTS.md?

**A**: Agenkit works fine without it. You'll just need to provide context in prompts manually.

### Q: Can I use AGENTS.md with other AI tools?

**A**: Yes! AGENTS.md is an industry standard supported by Cursor, Windsurf, Continue, and many others.

### Q: How does hierarchical merging work?

**A**: More specific AGENTS.md files (deeper in directory tree) take precedence. Root AGENTS.md provides defaults.

### Q: Should I commit AGENTS.md to git?

**A**: Yes! AGENTS.md should be version-controlled along with your code.

### Q: How often should I update AGENTS.md?

**A**: Update it whenever project conventions change. Think of it as living documentation.

### Q: Can I have multiple AGENTS.md files?

**A**: Yes! Place them in subdirectories for module-specific instructions. Agenkit automatically discovers and merges them.

### Q: What's the file size limit?

**A**: No hard limit, but keep it concise. Aim for < 5KB per file. Link to full docs for details.

### Q: Does middleware affect performance?

**A**: Minimal impact. Documents are cached and only parsed once. Reload only when files change.

### Q: Can I customize section types?

**A**: Yes! Use custom headings. Agenkit maps them to `SectionType.CUSTOM` and still includes them in context.

---

## Resources

- **Specification**: [https://agents.md/](https://agents.md/)
- **Examples**: [`examples/agents_md/`](../examples/agents_md/)
- **API Reference**: [API Documentation](https://agenkit.dev/api/)
- **Source Code**: [`agenkit/agents_md/`](../agenkit/agents_md/)

---

## Related Documentation

- [Migration Guides](migrations/) - Framework migrations
- [Pattern Library](patterns/) - Agent patterns
- [Tutorials](../tutorials/) - Step-by-step guides

---

**Start using AGENTS.md today!** It's the easiest way to give AI agents context about your project without repeating yourself.
