---
name: Bug Report
about: Create a report to help us improve
title: '[Bug]: '
labels: bug
assignees: ''
---

## Description

A clear and concise description of what the bug is.

## To Reproduce

Steps to reproduce the behavior:

1. Create agent with '...'
2. Call with messages '...'
3. Observe error '...'

**Minimal code example:**

```python
# Python
from agenkit import Agent, Message

agent = MyAgent()
response = await agent.call([
    Message(role="user", content="...")
])
# Error occurs here
```

or

```go
// Go
agent := NewMyAgent()
response, err := agent.Call(ctx, messages)
// Error occurs here
```

## Expected Behavior

A clear and concise description of what you expected to happen.

## Actual Behavior

What actually happened, including error messages.

**Error Output:**
```
Paste error message/stack trace here
```

## Environment

**Python:**
- Agenkit version: [e.g., 0.1.0]
- Python version: [e.g., 3.10.5]
- OS: [e.g., macOS 13.2, Ubuntu 22.04]
- Install method: [pip, conda, source]

**Go:**
- Agenkit version: [e.g., 0.1.0]
- Go version: [e.g., 1.21.5]
- OS: [e.g., Linux amd64]
- Go modules version: [from go.mod]

**Transport (if relevant):**
- Transport type: [HTTP, gRPC, WebSocket]
- Client language: [Python, Go]
- Server language: [Python, Go]

## Additional Context

Add any other context about the problem here:
- Does it happen consistently or intermittently?
- Does it work with a different transport/language?
- Any relevant logs or traces?

## Possible Solution

If you have ideas about what might be causing this or how to fix it, please share!
