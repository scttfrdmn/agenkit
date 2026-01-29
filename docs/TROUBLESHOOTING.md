# Troubleshooting Guide

**Quick solutions to common Agenkit issues**

---

## Table of Contents

- [v0.50.0 Migration Issues](#v050-migration-issues)
- [Parameter Validation Errors](#parameter-validation-errors)
- [Timeout Issues](#timeout-issues)
- [LLM Adapter Errors](#llm-adapter-errors)
- [Cross-Language Issues](#cross-language-issues)
- [Performance Issues](#performance-issues)
- [Deployment Issues](#deployment-issues)
- [Testing Issues](#testing-issues)

---

## v0.50.0 Migration Issues

### Python: AttributeError: 'TimeoutConfig' has no attribute 'timeout_ms'

**Error:**
```python
AttributeError: 'TimeoutConfig' object has no attribute 'timeout_ms'
```

**Cause:** You're using v0.49.0 code with v0.50.0 library (or vice versa).

**Solution:**
```python
# OLD (v0.49.0):
TimeoutDecorator(agent, timeout=30.0)  # seconds

# NEW (v0.50.0):
TimeoutDecorator(agent, timeout_ms=30000)  # milliseconds
```

**Quick fix for all timeouts:**
```bash
# Find all timeout parameters
grep -r "timeout=" agenkit/

# Update to timeout_ms (multiply by 1000)
# timeout=30.0 → timeout_ms=30000
# timeout=5.0 → timeout_ms=5000
```

### Python: TypeError: __init__() got an unexpected keyword argument 'timeout'

**Cause:** v0.50.0 removed the `timeout` parameter in favor of `timeout_ms`.

**Solution:** Update all timeout parameters:
```python
# Middleware
TimeoutDecorator(agent, timeout_ms=30000)
RateLimiterDecorator(agent, rate=10, max_wait_ms=30000)

# Circuit breaker
CircuitBreakerDecorator(agent, recovery_timeout_ms=60000)
```

### Go: cannot use userIDExtractor (type func(*Message) string) as type func(*Message) *string

**Error:**
```
cannot use userIDExtractor (type func(*Message) string) as type func(*Message) *string in argument to NewRateLimiterDecorator
```

**Cause:** v0.50.0 changed `UserIDExtractor` to return `*string` instead of `string`.

**Solution:**
```go
// OLD (v0.49.0):
userIDExtractor := func(msg *Message) string {
    if userID, ok := msg.Metadata["user_id"].(string); ok {
        return userID
    }
    return ""  // Sentinel value
}

// NEW (v0.50.0):
userIDExtractor := func(msg *Message) *string {
    if userID, ok := msg.Metadata["user_id"].(string); ok {
        return &userID
    }
    return nil  // Proper nil for "no value"
}
```

---

## Parameter Validation Errors

### ValueError: temperature must be between 0 and 2, got 3.0

**Cause:** v0.50.0 enforces LLM parameter validation at construction.

**Solution:** Use valid parameter ranges:
```python
# Temperature: 0.0 - 2.0
llm = OpenAILLM(
    api_key="...",
    model="gpt-4-turbo",
    temperature=0.7  # ✅ Valid (0-2)
)

# WRONG:
llm = OpenAILLM(temperature=3.0)  # ❌ ValueError
```

**Valid ranges:**
- `temperature`: 0.0 - 2.0
- `max_tokens`: > 0
- `top_p`: 0.0 - 1.0

### ValueError: max_tokens must be positive, got 0

**Cause:** `max_tokens` must be at least 1.

**Solution:**
```python
# WRONG:
llm = OpenAILLM(max_tokens=0)  # ❌ ValueError

# CORRECT:
llm = OpenAILLM(max_tokens=1024)  # ✅ Valid
```

### Go: panic: invalid temperature: 3.000000

**Cause:** Go validation panics on invalid parameters.

**Solution:**
```go
// Use functional options with valid ranges
llm, err := llm.NewOpenAI(
    llm.WithAPIKey(os.Getenv("OPENAI_API_KEY")),
    llm.WithModel("gpt-4-turbo"),
    llm.WithTemperature(0.7),  // Must be 0-2
)
if err != nil {
    log.Fatal(err)  // Handle validation error
}
```

---

## Timeout Issues

### Agent operations timing out unexpectedly

**Symptom:** Agents timeout even though LLM responds quickly.

**Cause 1:** Timeout too short for middleware overhead.

**Solution:**
```python
# WRONG: Timeout shorter than LLM response time
agent = TimeoutDecorator(agent, timeout_ms=100)  # Too short!

# CORRECT: Account for middleware overhead
agent = TimeoutDecorator(agent, timeout_ms=30000)  # 30 seconds
```

**Cause 2:** Middleware stacking multiplies timeouts.

**Solution:**
```python
# Each middleware has its own timeout
agent = RetryDecorator(agent, max_attempts=3)  # 3 retries
agent = TimeoutDecorator(agent, timeout_ms=10000)  # 10s per attempt

# Total possible time: 3 attempts × 10s = 30s
# Set outer timeout accordingly
```

### asyncio.TimeoutError in Python

**Cause:** Using `asyncio.wait_for` with shorter timeout than agent's timeout.

**Solution:**
```python
# WRONG:
async def main():
    agent = TimeoutDecorator(agent, timeout_ms=30000)
    result = await asyncio.wait_for(
        agent.process(message),
        timeout=5.0  # ❌ Shorter than agent timeout!
    )

# CORRECT: Outer timeout ≥ agent timeout
async def main():
    agent = TimeoutDecorator(agent, timeout_ms=30000)
    result = await asyncio.wait_for(
        agent.process(message),
        timeout=35.0  # ✅ Longer than agent timeout
    )
```

---

## LLM Adapter Errors

### AuthenticationError: Invalid API key

**Cause:** API key not set or incorrect.

**Solution:**
```python
# Option 1: Environment variable (recommended)
import os
llm = OpenAILLM(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4-turbo"
)

# Option 2: Direct (for testing only)
llm = OpenAILLM(
    api_key="sk-...",
    model="gpt-4-turbo"
)
```

**Verify API key:**
```bash
# Check environment variable is set
echo $OPENAI_API_KEY

# Test API key with curl
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### RateLimitError: Rate limit exceeded

**Cause:** Making too many requests to LLM provider.

**Solution:**
```python
from agenkit.middleware import RateLimiterDecorator

# Add rate limiting
agent = RateLimiterDecorator(
    agent,
    rate=10,  # 10 requests per second
    max_wait_ms=30000  # Wait up to 30s for token
)

# Process requests (automatically rate-limited)
results = await asyncio.gather(*[
    agent.process(msg) for msg in messages
])
```

### InvalidRequestError: model not found

**Cause:** Model name is incorrect or not available.

**Solution:**
```python
# Check available models
# OpenAI: gpt-4-turbo, gpt-4o, gpt-3.5-turbo
# Anthropic: claude-3-5-sonnet-20241022, claude-3-opus-20240229

# WRONG:
llm = OpenAILLM(model="gpt-5")  # ❌ Doesn't exist

# CORRECT:
llm = OpenAILLM(model="gpt-4-turbo")  # ✅ Valid model
```

---

## Cross-Language Issues

### Python agent can't call Go service

**Symptom:** Connection refused or timeout when Python agent calls Go service.

**Cause:** Service not running or wrong port.

**Solution:**
```bash
# Check if Go service is running
netstat -an | grep 8080

# Start Go service
cd agenkit-go
go run examples/http_server.go

# Test connection
curl http://localhost:8080/health
```

### Type mismatches between languages

**Symptom:** JSON serialization errors when crossing language boundaries.

**Solution:** Use consistent message formats:
```python
# Python
message = Message(
    role="user",
    content="Hello",
    metadata={"key": "value"}  # Use JSON-serializable types only
)

# Go
message := &Message{
    Role:    "user",
    Content: "Hello",
    Metadata: map[string]interface{}{
        "key": "value",  // Compatible with Python
    },
}
```

**Avoid:**
- Python: datetime objects, custom classes
- Go: channels, functions
- TypeScript: undefined (use null)

---

## Performance Issues

### Agent responses are slow

**Symptom:** 5-10 second response times.

**Diagnosis:**
```python
import time

async def profile_agent(agent, message):
    start = time.time()
    
    # Profile LLM call
    llm_start = time.time()
    result = await agent.process(message)
    llm_time = time.time() - llm_start
    
    total_time = time.time() - start
    
    print(f"LLM time: {llm_time:.2f}s")
    print(f"Middleware overhead: {(total_time - llm_time):.2f}s")
    
    return result
```

**Common causes:**

1. **Too many retries:**
```python
# WRONG: 10 retries = 10x latency on failure
agent = RetryDecorator(agent, max_attempts=10)

# CORRECT: 2-3 retries is sufficient
agent = RetryDecorator(agent, max_attempts=3)
```

2. **Sequential when parallel is better:**
```python
# WRONG: Sequential (slow)
results = []
for message in messages:
    result = await agent.process(message)
    results.append(result)

# CORRECT: Parallel (fast)
results = await asyncio.gather(*[
    agent.process(msg) for msg in messages
])
```

3. **Using Python when Go would be faster:**
```bash
# Python baseline: 1.02ms per request
python examples/benchmark.py

# Go: 18.5x faster (0.055ms per request)
cd agenkit-go && go run examples/benchmark.go
```

### Memory leaks in long-running agents

**Symptom:** Memory usage grows over time.

**Cause:** Not cleaning up message history in conversational agents.

**Solution:**
```python
from agenkit.patterns import ConversationalAgent

# Use sliding window to limit history
agent = ConversationalAgent(
    llm,
    history_strategy="sliding_window",
    max_messages=10  # Keep only last 10 messages
)

# Or use token-based limits
agent = ConversationalAgent(
    llm,
    history_strategy="token_based",
    max_tokens=4000  # Limit history to 4K tokens
)
```

---

## Deployment Issues

### Docker container won't start

**Symptom:** Container exits immediately.

**Solution:**
```bash
# Check logs
docker logs agenkit-container

# Common issue: Missing environment variables
docker run -e OPENAI_API_KEY=$OPENAI_API_KEY agenkit

# Or use .env file
docker run --env-file .env agenkit
```

### Kubernetes pod crashes with OOMKilled

**Symptom:** Pod crashes with exit code 137.

**Cause:** Insufficient memory allocation.

**Solution:**
```yaml
# deployment.yaml
resources:
  requests:
    memory: "512Mi"  # Increase from default
  limits:
    memory: "1Gi"    # Increase limit
```

**Monitor memory usage:**
```bash
kubectl top pods
kubectl describe pod <pod-name>
```

### Kubernetes HPA not scaling

**Symptom:** Pods don't scale under load.

**Cause:** Metrics server not installed or no resource requests.

**Solution:**
```bash
# Check metrics server
kubectl top nodes

# If not installed:
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify HPA
kubectl get hpa
kubectl describe hpa agenkit-hpa
```

---

## Testing Issues

### Tests fail with "async function not awaited"

**Cause:** Forgetting `await` in async tests.

**Solution:**
```python
import pytest

# WRONG:
@pytest.mark.asyncio
async def test_agent():
    result = agent.process(message)  # ❌ Missing await
    assert result.content == "expected"

# CORRECT:
@pytest.mark.asyncio
async def test_agent():
    result = await agent.process(message)  # ✅ With await
    assert result.content == "expected"
```

### Go tests hang indefinitely

**Cause:** Goroutine deadlock or missing context cancellation.

**Solution:**
```go
func TestAgent(t *testing.T) {
    // WRONG: No timeout
    ctx := context.Background()
    
    // CORRECT: With timeout
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
    
    result, err := agent.Process(ctx, message)
    if err != nil {
        t.Fatal(err)
    }
}
```

### TypeScript tests fail with "Cannot find module"

**Cause:** Missing dependencies or incorrect tsconfig.

**Solution:**
```bash
# Install dependencies
npm install

# Check tsconfig.json
cat tsconfig.json
# Ensure "moduleResolution": "node"

# Run with ts-node
npx ts-node --esm tests/test.ts
```

---

## Quick Diagnostic Commands

### Check Agenkit Installation

```bash
# Python
python -c "import agenkit; print(agenkit.__version__)"

# Go
go list -m github.com/yourusername/agenkit-go

# TypeScript
npm list agenkit
```

### Verify API Keys

```bash
# OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Anthropic
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-3-5-sonnet-20241022","messages":[],"max_tokens":1}'
```

### Test Network Connectivity

```bash
# Test HTTP endpoint
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"test"}'

# Test WebSocket
wscat -c ws://localhost:8765
```

### Monitor Agent Performance

```python
from agenkit.observability import configure_observability

# Enable tracing
configure_observability(
    service_name="my-agent",
    exporter_type="jaeger",
    jaeger_endpoint="http://localhost:14268/api/traces"
)

# View traces at http://localhost:16686
```

---

## Getting Help

If you can't find a solution here:

1. **Check the docs:**
   - [Getting Started Guides](getting-started/) - Language-specific guides
   - [Agent Patterns Book](../../agent-patterns-book) - Pattern documentation
   - [API Reference](API.md) - Complete API docs

2. **Search existing issues:**
   - https://github.com/yourusername/agenkit/issues

3. **Ask for help:**
   - GitHub Discussions: https://github.com/yourusername/agenkit/discussions
   - Create an issue: https://github.com/yourusername/agenkit/issues/new

4. **Provide context:**
   - Agenkit version
   - Language and version (Python 3.13, Go 1.23, etc.)
   - Code snippet reproducing the issue
   - Full error message with stack trace

---

**Version**: v0.50.0  
**Last Updated**: January 28, 2026
