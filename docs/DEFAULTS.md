# Canonical Default Configuration Values

This document is the authoritative reference for default configuration values across
all agenkit language implementations. When adding a new language or pattern, consult
this table to ensure consistency.

## Default Values by Setting

| Setting | Python | Go | TypeScript | Rust | C++ | Zig |
|---|---|---|---|---|---|---|
| `max_history` | `10` | `10` | `10` | `10` | `10` | `10` |
| `max_steps` | `10` | `10` | `10` | `10` | `10` | `10` |
| `verbose` | `False` | `false` | `false` | `false` | `false` | `false` |
| `include_system` | `True` | `true` | `true` | `true` | `true` | `true` |
| `checkpoint max_depth` | `10` | `10` | `10` | `10` | `10` | `10` |
| `default_key` / `route` | `None` | `nil` | `undefined` | `None` | `nullptr` | `null` |

## Equivalent Initialization Patterns

The following examples show how to configure the same settings in each language.

### ConversationalAgent with max_history=20

**Python (recommended)**
```python
from agenkit.patterns import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(llm_client=llm, max_history=20)
agent = ConversationalAgent(config)
```

**Go**
```go
agent, err := patterns.NewConversationalAgent(&patterns.ConversationalConfig{
    Agent:      llmAgent,
    MaxHistory: 20,
})
```

**TypeScript**
```typescript
const agent = new ConversationalAgent({
  llmClient: llm,
  maxHistory: 20,
});
```

**Rust**
```rust
let agent = ConversationalAgent::new(ConversationalConfig {
    llm_client: llm,
    max_history: 20,
    ..Default::default()
});
```

### ReActAgent with verbose=true, max_steps=15

**Python**
```python
from agenkit.patterns import ReActAgent, ReActConfig

config = ReActConfig(agent=llm_agent, tools=tools, verbose=True, max_steps=15)
agent = ReActAgent(config)
```

**Go**
```go
agent, err := patterns.NewReActAgent(&patterns.ReActConfig{
    Agent:    llmAgent,
    Tools:    tools,
    Verbose:  true,
    MaxSteps: 15,
})
```

**TypeScript**
```typescript
const agent = new ReActAgent({
  agent: llmAgent,
  tools,
  verbose: true,
  maxSteps: 15,
});
```

### RouterAgent with defaultKey

**Python**
```python
from agenkit.patterns import RouterAgent, RouterConfig

config = RouterConfig(agents=agents, default_key="fallback")
agent = RouterAgent(config)
```

**Go**
```go
agent, err := patterns.NewRouterAgent(&patterns.RouterConfig{
    Agents:     agents,
    DefaultKey: "fallback",
})
```

## Notes on Specific Defaults

### `verbose` (default: `false`)

In all languages, `verbose` defaults to `false`. When `verbose=true`, the agent
includes full step-by-step reasoning traces in its final output — useful for
debugging but noisy in production.

> **Go change (v0.69.0):** Prior to v0.69.0, Go's `ReActAgent` incorrectly
> defaulted `Verbose` to `true` when no config fields were set. This was a bug
> — the zero value of `bool` in Go is `false`, which is the correct canonical
> default. Code that relied on the old implicit `verbose=true` behavior should
> now set `Verbose: true` explicitly.

### `max_history` / `max_steps` (default: `10`)

Both settings cap the amount of state an agent accumulates. The default of `10`
is a reasonable balance for most workloads. Increase for long-running agents that
need more context; decrease to reduce token usage.

### `include_system` (default: `true`)

When `true`, the system prompt is stored as the first message in the conversation
history and is included in every LLM call. Set to `false` only if the underlying
LLM client handles system prompts through a separate API parameter.

### `default_key` / `default_route` (default: `None`/`nil`)

The router's fallback destination when no routing rule matches. If `None`/`nil`,
unmatched messages raise an error. Set to a valid agent key to enable graceful
fallback routing.

## Related Documentation

- [Migration Guides](migrations/) — step-by-step upgrade instructions
- [Framework Comparison Matrix](framework_comparison_matrix.md) — per-framework
  defaults and feature support
- [ARCHITECTURE.md](../ARCHITECTURE.md) — design principles behind these choices
