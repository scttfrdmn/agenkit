# Agent Patterns

The 11 foundational patterns for building AI agents.

## Core Patterns

Agenkit provides **11 production-tested patterns** for common agent use cases:

| Pattern | Description | Complexity | Use Case |
|---------|-------------|------------|----------|
| **[ReAct](react.md)** | Reasoning + Acting loop | ⭐ | General problem solving |
| **[Reflection](reflection.md)** | Self-critique and improvement | ⭐⭐ | Quality improvement |
| **[Agents-as-Tools](agents-as-tools.md)** | Agents calling other agents | ⭐⭐ | Modular systems |
| **[Orchestration](orchestration.md)** | Coordinate multiple agents | ⭐⭐⭐ | Complex workflows |
| **[Conversational](conversational.md)** | Stateful conversations | ⭐ | Chatbots, assistants |
| **[Task](task.md)** | Goal-oriented execution | ⭐⭐ | Specific objectives |
| **[Multiagent](multiagent.md)** | Parallel collaboration | ⭐⭐⭐ | Team coordination |
| **[Planning](planning.md)** | Multi-step planning | ⭐⭐⭐ | Strategic tasks |
| **[Autonomous](autonomous.md)** | Self-directed agents | ⭐⭐⭐⭐ | Autonomous systems |
| **[Memory Hierarchy](memory-hierarchy.md)** | Tiered memory | ⭐⭐⭐ | Context management |
| **[Reasoning with Tools](reasoning-with-tools.md)** | Tool-augmented reasoning | ⭐⭐⭐ | Complex problem solving |

---

## Pattern Examples

Each pattern includes:
- **Concept**: What is it?
- **When to use**: Use cases and scenarios
- **How it works**: Implementation details
- **Code examples**: Python, Go, TypeScript, Rust, C++, Zig
- **Best practices**: Tips and gotchas

See the [examples directory](../../examples/patterns/) for complete working examples.

---

## Quick Reference

### Most Popular Patterns

1. **ReAct** - Start here! General-purpose reasoning
2. **Conversational** - For chatbots and assistants
3. **Orchestration** - For complex multi-agent systems

### By Use Case

**Building a Chatbot?** → Conversational, Memory Hierarchy

**Need Complex Reasoning?** → ReAct, Reasoning with Tools, Planning

**Multi-Agent System?** → Orchestration, Multiagent, Agents-as-Tools

**Self-Improving Agent?** → Reflection, Autonomous

---

## Related Documentation

- [Advanced Reasoning Techniques](../reasoning/index.md)
- [Tutorials](../tutorials/index.md)
- [Examples](../examples/index.md)
- [API Reference](../api/index.md)

---

For detailed pattern documentation, see [docs/patterns/](../../docs/patterns/) in the repository.
