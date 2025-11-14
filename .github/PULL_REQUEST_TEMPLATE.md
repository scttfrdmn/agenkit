# Pull Request

## Description

**What does this PR do?**

A clear and concise description of the changes.

**Related Issue(s):**

Closes #(issue number)

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Test improvement

## Implementation

**Approach:**

Explain your implementation approach and any important design decisions.

**Key Changes:**

- Changed X in Y to handle Z
- Added new module/class for...
- Updated documentation to reflect...

## Testing

### Test Coverage

- [ ] **Python tests added/updated**
  - [ ] Unit tests
  - [ ] Integration tests (if applicable)
  - [ ] All existing tests pass

- [ ] **Go tests added/updated** (if applicable)
  - [ ] Unit tests
  - [ ] Integration tests (if applicable)
  - [ ] All existing tests pass

- [ ] **Cross-language tests** (if applicable)
  - [ ] Python ↔ Go communication tested
  - [ ] Both directions working

### How to Test

Describe how reviewers can test your changes:

```python
# Python example
from agenkit import ...

# Steps to test
agent = ...
result = await agent.call(...)
assert result == expected
```

or

```go
// Go example
agent := ...
result, err := agent.Call(ctx, ...)
// Verify result
```

## Documentation

- [ ] **Code comments** added for complex logic
- [ ] **Docstrings/GoDoc** added for public APIs
- [ ] **README** updated (if applicable)
- [ ] **Agent Patterns Guide** updated (if applicable)
- [ ] **Examples** added or updated (if applicable)
- [ ] **CHANGELOG** updated

## Checklist

- [ ] My code follows the style guidelines (see CONTRIBUTING.md)
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

### Python-Specific (if applicable)

- [ ] Type hints added
- [ ] `ruff check .` passes
- [ ] `mypy agenkit/` passes
- [ ] `pytest tests/` passes

### Go-Specific (if applicable)

- [ ] Code formatted with `go fmt`
- [ ] `go vet ./...` passes
- [ ] `golangci-lint run` passes (or explain why not)
- [ ] `go test ./...` passes

### Cross-Language (if applicable)

- [ ] Feature parity between Python and Go
- [ ] Proto definitions updated (if needed)
- [ ] Transport compatibility maintained
- [ ] Both languages tested together

## Breaking Changes

**Is this a breaking change?**

- [ ] No
- [ ] Yes (explain below)

**If yes, describe the breaking changes:**

- What breaks?
- Migration path for users?
- Version bump needed? (major/minor)

## Screenshots/Examples (if applicable)

Add screenshots, example output, or usage examples to help explain your changes.

## Performance Impact

**Does this change affect performance?**

- [ ] No impact expected
- [ ] Improves performance (explain how)
- [ ] May degrade performance (explain why acceptable)
- [ ] Unknown (needs benchmarking)

**Benchmark results (if applicable):**

```
Before: ...
After: ...
Improvement: X%
```

## Additional Notes

Any additional information for reviewers:

- Deployment considerations?
- Follow-up work needed?
- Known limitations?
- Alternative approaches considered?

---

**For Reviewers:**

Please check:
- [ ] Code quality and style
- [ ] Test coverage adequate
- [ ] Documentation clear
- [ ] No obvious bugs
- [ ] Design makes sense
- [ ] Backward compatibility (if not breaking)
