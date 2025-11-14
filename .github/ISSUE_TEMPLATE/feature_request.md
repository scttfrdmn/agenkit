---
name: Feature Request
about: Suggest an idea for Agenkit
title: '[Feature]: '
labels: enhancement
assignees: ''
---

## Problem Statement

**Is your feature request related to a problem?**

A clear and concise description of what the problem is. Ex: "I'm always frustrated when [...]" or "It's difficult to [...]"

## Proposed Solution

A clear and concise description of what you want to happen.

**Example API (if applicable):**

```python
# Python
from agenkit import NewFeature

# How you'd like to use it
feature = NewFeature(config=...)
result = await feature.do_something()
```

or

```go
// Go
feature := NewFeature(config)
result, err := feature.DoSomething(ctx)
```

## Alternatives Considered

A clear and concise description of any alternative solutions or features you've considered.

1. **Alternative A**: Description...
2. **Alternative B**: Description...

**Why the proposed solution is better:**

## Use Cases

Describe the use cases this feature would enable:

1. **Use Case 1**: As a [user type], I want to [action] so that [benefit]
2. **Use Case 2**: When building [system type], this would help [...]
3. **Use Case 3**: ...

## Implementation Considerations

**Scope:**
- [ ] Python implementation
- [ ] Go implementation
- [ ] Cross-language compatibility needed
- [ ] Breaking change (requires major version bump)
- [ ] Backward compatible

**Affected Components:**
- [ ] Core interfaces
- [ ] Transport layer
- [ ] Middleware
- [ ] Observability
- [ ] Documentation

**Complexity Estimate:**
- [ ] Small (< 1 day)
- [ ] Medium (1-3 days)
- [ ] Large (> 3 days)
- [ ] Unknown

## Additional Context

Add any other context, mockups, or examples about the feature request here.

**Related Issues/PRs:**
- #123
- #456

**Links to similar features in other frameworks:**
- LangChain: [link]
- CrewAI: [link]

## Acceptance Criteria

How will we know this feature is complete and working correctly?

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
- [ ] Tests added (Python)
- [ ] Tests added (Go) (if applicable)
- [ ] Documentation updated
- [ ] Example added (if applicable)
