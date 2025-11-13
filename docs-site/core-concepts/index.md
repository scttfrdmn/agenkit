# Core Concepts

Understanding Agenkit's fundamental concepts and design philosophy.

## Overview

Agenkit is built on three core principles:

1. **Minimal Interfaces** - Only what's required for interoperability
2. **Layered Architecture** - Independent, composable layers
3. **Language Agnostic** - Identical APIs across Python and Go

## Key Concepts

### [Architecture](architecture.md)
Learn how Agenkit's five layers work together to provide a complete agent framework.

### [Interfaces](interfaces.md)
Understand the core contracts: Agent, Message, Tool, and ToolResult.

### [Design Principles](design-principles.md)
Explore the philosophy behind Agenkit's design decisions.

## The Foundation

At its heart, Agenkit defines just **four primitives**:

```python
# 1. Agent - processes messages
class Agent:
    def process(message: Message) -> Message

# 2. Message - universal data format
@dataclass
class Message:
    role: str
    content: Any
    metadata: dict

# 3. Tool - executable functions
class Tool:
    def execute(**kwargs) -> ToolResult

# 4. ToolResult - tool execution results
@dataclass
class ToolResult:
    success: bool
    data: Any
```

Everything else in Agenkit builds on these four primitives.

## Design Philosophy

> **"Make the simple things simple, and the complex things possible."**

Agenkit achieves this through:

- **Minimal core** - Four interfaces, that's it
- **Decorator pattern** - Stack middleware like LEGO bricks
- **Protocol adapters** - Same interface, multiple transports
- **Type safety** - Full typing in both Python and Go
- **Production ready** - Error handling, observability, security

## Learning Path

1. Start with [Architecture](architecture.md) to understand the big picture
2. Deep dive into [Interfaces](interfaces.md) to learn the contracts
3. Review [Design Principles](design-principles.md) for the philosophy
4. Explore [Features](../features/index.md) to see what's built on top

Ready to dive in? Start with the [Architecture Guide](architecture.md) →
