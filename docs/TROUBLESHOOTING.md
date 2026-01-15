# Troubleshooting & FAQ

**Common issues, debugging strategies, and frequently asked questions for agenkit.**

---

## Table of Contents

- [Quick Diagnosis](#quick-diagnosis)
- [Common Errors](#common-errors)
  - [Installation Issues](#installation-issues)
  - [Import Errors](#import-errors)
  - [Type Errors](#type-errors)
  - [Async/Await Errors](#asyncawait-errors)
  - [Pattern Errors](#pattern-errors)
  - [LLM Integration Errors](#llm-integration-errors)
- [Debugging Strategies](#debugging-strategies)
- [Performance Issues](#performance-issues)
- [Cross-Language Issues](#cross-language-issues)
- [Production Issues](#production-issues)
- [FAQ](#faq)
  - [General](#general)
  - [Patterns](#patterns)
  - [LLM Integration](#llm-integration)
  - [Performance](#performance)
  - [Migration](#migration)
  - [Best Practices](#best-practices)

---

## Quick Diagnosis

### Symptom Checklist

Use this checklist to quickly identify your issue category:

**Installation/Import Problems:**
- [ ] Can't install agenkit → [Installation Issues](#installation-issues)
- [ ] Import errors → [Import Errors](#import-errors)
- [ ] Version conflicts → [Installation Issues](#installation-issues)

**Runtime Errors:**
- [ ] Type errors → [Type Errors](#type-errors)
- [ ] Async/await errors → [Async/Await Errors](#asyncawait-errors)
- [ ] Pattern not working → [Pattern Errors](#pattern-errors)
- [ ] LLM not responding → [LLM Integration Errors](#llm-integration-errors)

**Performance Problems:**
- [ ] Slow response times → [Performance Issues](#performance-issues)
- [ ] High memory usage → [Performance Issues](#performance-issues)
- [ ] High costs → [Performance Issues](#performance-issues)

**Language-Specific:**
- [ ] Go compilation errors → [Cross-Language Issues](#cross-language-issues)
- [ ] TypeScript type errors → [Cross-Language Issues](#cross-language-issues)
- [ ] Rust ownership errors → [Cross-Language Issues](#cross-language-issues)

---

## Common Errors

### Installation Issues

#### Error: "Could not find a version that satisfies the requirement agenkit"

**Symptom:**
```bash
ERROR: Could not find a version that satisfies the requirement agenkit
ERROR: No matching distribution found for agenkit
```

**Cause:** Package not published or wrong package name.

**Solution:**
```bash
# Python - use correct package name
pip install agenkit-py  # or uv add agenkit-py

# If developing from source
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit
pip install -e .
```

#### Error: "Python version not supported"

**Symptom:**
```bash
ERROR: Package 'agenkit' requires a different Python: 3.8.0 not in '>=3.9'
```

**Cause:** Python version too old.

**Solution:**
```bash
# Check Python version
python --version

# Upgrade Python (using pyenv)
pyenv install 3.12.0
pyenv global 3.12.0

# Or use uv (recommended)
uv python install 3.12
```

#### Error: "Go module not found"

**Symptom:**
```bash
go: github.com/scttfrdmn/agenkit/agenkit-go@v0.44.0: not found
```

**Cause:** Module not in Go registry or wrong version.

**Solution:**
```bash
# Initialize Go module
go mod init your-project

# Add agenkit
go get github.com/scttfrdmn/agenkit/agenkit-go@latest

# Or from source
git clone https://github.com/scttfrdmn/agenkit.git
cd your-project
go mod edit -replace github.com/scttfrdmn/agenkit/agenkit-go=../agenkit/agenkit-go
go mod tidy
```

#### Error: "npm package not found"

**Symptom:**
```bash
npm ERR! 404 Not Found - GET https://registry.npmjs.org/@agenkit/core
```

**Cause:** Package not published to npm.

**Solution:**
```bash
# If developing from source
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-ts
npm install
npm link

# In your project
npm link @agenkit/core
```

---

### Import Errors

#### Error: "cannot import name 'Agent' from 'agenkit'"

**Symptom:**
```python
ImportError: cannot import name 'Agent' from 'agenkit'
```

**Cause:** Incorrect import path.

**Solution:**
```python
# ✅ Correct imports
from agenkit import Agent, Message
from agenkit.patterns import SequentialAgent, ParallelAgent
from agenkit.adapters import OpenAIAdapter

# ❌ Wrong imports
from agenkit.core import Agent  # Too specific
from agenkit import SequentialAgent  # Wrong module
```

#### Error: "Module 'agenkit' has no attribute 'patterns'"

**Symptom:**
```python
AttributeError: module 'agenkit' has no attribute 'patterns'
```

**Cause:** Old version or import caching issue.

**Solution:**
```bash
# Update to latest version
pip install --upgrade agenkit

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Restart Python interpreter
```

#### Error: TypeScript "Cannot find module '@agenkit/core'"

**Symptom:**
```typescript
error TS2307: Cannot find module '@agenkit/core' or its corresponding type declarations.
```

**Cause:** Package not installed or wrong path.

**Solution:**
```bash
# Install package
npm install @agenkit/core @agenkit/patterns

# Check tsconfig.json
{
  "compilerOptions": {
    "moduleResolution": "node",
    "esModuleInterop": true
  }
}
```

---

### Type Errors

#### Error: "Agent object has no attribute 'name'"

**Symptom:**
```python
AttributeError: 'MyAgent' object has no attribute 'name'
```

**Cause:** Forgot to implement `name` property.

**Solution:**
```python
# ✅ Correct implementation
class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "my-agent"

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content="response")

# ❌ Wrong - missing @property
class MyAgent(Agent):
    def name(self) -> str:  # Should be @property
        return "my-agent"
```

#### Error: TypeScript "Property 'name' does not exist on type 'MyAgent'"

**Symptom:**
```typescript
Property 'name' does not exist on type 'MyAgent'.
```

**Cause:** Used method instead of getter.

**Solution:**
```typescript
// ✅ Correct - getter
class MyAgent implements Agent {
    get name(): string {  // ← getter syntax
        return 'my-agent';
    }
}

// ❌ Wrong - method
class MyAgent implements Agent {
    name(): string {  // ← this is a method, not a getter
        return 'my-agent';
    }
}
```

#### Error: Go "cannot use agent (type *MyAgent) as type Agent"

**Symptom:**
```go
cannot use agent (type *MyAgent) as type core.Agent in argument to pattern.Process:
    *MyAgent does not implement core.Agent (missing method Process)
```

**Cause:** Method signature doesn't match interface.

**Solution:**
```go
// ✅ Correct - matches interface
type MyAgent struct{}

func (a *MyAgent) Name() string {
    return "my-agent"
}

func (a *MyAgent) Process(ctx context.Context, msg core.Message) (core.Message, error) {
    return core.Message{Role: "assistant", Content: "response"}, nil
}

// ❌ Wrong - missing context.Context
func (a *MyAgent) Process(msg core.Message) (core.Message, error) {
    // Missing ctx parameter
}
```

#### Error: Rust "the trait `Agent` is not implemented for `MyAgent`"

**Symptom:**
```rust
error[E0277]: the trait `Agent` is not implemented for `MyAgent`
```

**Cause:** Missing `#[async_trait]` or wrong method signature.

**Solution:**
```rust
// ✅ Correct
use async_trait::async_trait;

pub struct MyAgent;

#[async_trait]  // ← Required for async trait methods
impl Agent for MyAgent {
    fn name(&self) -> &str {
        "my-agent"
    }

    async fn process(&self, message: Message) -> Result<Message, Box<dyn Error + Send + Sync>> {
        Ok(Message {
            role: "assistant".to_string(),
            content: "response".to_string(),
            ..Default::default()
        })
    }
}

// ❌ Wrong - missing #[async_trait]
impl Agent for MyAgent {
    // ...
}
```

---

### Async/Await Errors

#### Error: "coroutine was never awaited"

**Symptom:**
```python
RuntimeWarning: coroutine 'Agent.process' was never awaited
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
```

**Cause:** Forgot to `await` async function.

**Solution:**
```python
# ✅ Correct
result = await agent.process(message)

# ❌ Wrong - missing await
result = agent.process(message)  # Returns coroutine object, not result

# ✅ Also correct - running in script
import asyncio

async def main():
    result = await agent.process(message)
    print(result)

asyncio.run(main())

# ❌ Wrong - trying to await in non-async function
def sync_function():
    result = await agent.process(message)  # SyntaxError
```

#### Error: "await is only valid in async functions"

**Symptom:**
```typescript
error TS1308: 'await' expression is only allowed within an async function.
```

**Cause:** Using `await` in non-async function.

**Solution:**
```typescript
// ✅ Correct
async function main() {
    const result = await agent.process(message);
}

// ❌ Wrong
function main() {
    const result = await agent.process(message);  // Error
}
```

#### Error: Go "cannot use goroutine with context"

**Symptom:**
```go
// Goroutine not receiving context updates
```

**Cause:** Not passing context to goroutines.

**Solution:**
```go
// ✅ Correct - pass context
func (a *MyAgent) Process(ctx context.Context, msg core.Message) (core.Message, error) {
    // Spawn goroutine with context
    go func() {
        select {
        case <-ctx.Done():
            return  // Respect cancellation
        case <-time.After(5 * time.Second):
            // Do work
        }
    }()
}

// ❌ Wrong - ignoring context
func (a *MyAgent) Process(ctx context.Context, msg core.Message) (core.Message, error) {
    go func() {
        time.Sleep(5 * time.Second)  // No cancellation
    }()
}
```

---

### Pattern Errors

#### Error: "SequentialAgent: no agents provided"

**Symptom:**
```python
ValueError: SequentialAgent requires at least one agent
```

**Cause:** Empty agents list.

**Solution:**
```python
# ✅ Correct
pipeline = SequentialAgent(
    agents=[agent1, agent2, agent3]
)

# ❌ Wrong
pipeline = SequentialAgent(agents=[])  # Empty list
```

#### Error: "ParallelAgent: aggregation function failed"

**Symptom:**
```python
TypeError: aggregation function must accept list[Message] and return Message
```

**Cause:** Incorrect aggregation function signature.

**Solution:**
```python
# ✅ Correct aggregation
def my_aggregator(results: list[Message]) -> Message:
    combined = "\n".join(msg.content for msg in results)
    return Message(role="assistant", content=combined)

parallel = ParallelAgent(
    agents=[agent1, agent2],
    aggregation=my_aggregator
)

# ❌ Wrong - wrong signature
def bad_aggregator(results: Message) -> Message:  # Should be list[Message]
    return results
```

#### Error: "RouterAgent: no route matched"

**Symptom:**
```python
RuntimeError: No route matched and no default agent provided
```

**Cause:** Missing default agent.

**Solution:**
```python
# ✅ Correct - with default
router = RouterAgent(
    routes={
        "billing": billing_agent,
        "technical": technical_agent
    },
    default_agent=general_agent  # ← Always provide default
)

# ❌ Wrong - no default
router = RouterAgent(
    routes={
        "billing": billing_agent,
        "technical": technical_agent
    }
    # No default - will error if no route matches
)
```

#### Error: "ReflectionAgent: infinite loop detected"

**Symptom:**
```python
RuntimeError: ReflectionAgent exceeded max_iterations (10)
```

**Cause:** Critic never approves, or improvement threshold too high.

**Solution:**
```python
# ✅ Correct - reasonable limits
refiner = ReflectionAgent(
    agent=writer,
    critic=critic,
    max_iterations=5,  # Reasonable limit
    improvement_threshold=0.8  # Achievable threshold
)

# ❌ Problematic
refiner = ReflectionAgent(
    agent=writer,
    critic=critic,
    max_iterations=100,  # Too high
    improvement_threshold=0.99  # Nearly impossible
)

# Debug: Add logging to critic
class Critic(Agent):
    async def process(self, message: Message) -> Message:
        score = self.evaluate(message.content)
        print(f"Critic score: {score}")  # ← Debug logging
        return Message(
            role="assistant",
            content=f"Score: {score}",
            metadata={"reflection_score": score}
        )
```

---

### LLM Integration Errors

#### Error: "OpenAI API key not found"

**Symptom:**
```python
AuthenticationError: No API key provided
```

**Cause:** Missing API key environment variable.

**Solution:**
```bash
# Set environment variable
export OPENAI_API_KEY="sk-..."

# Or in Python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."

# Or pass directly
from agenkit.adapters import OpenAIAdapter
llm = OpenAIAdapter(api_key="sk-...", model="gpt-4")
```

#### Error: "Rate limit exceeded"

**Symptom:**
```python
RateLimitError: Rate limit reached for gpt-4 in organization org-...
```

**Cause:** Too many requests to LLM API.

**Solution:**
```python
# Use rate limiting middleware
from agenkit.middleware import RateLimiter

agent = RateLimiter(
    agent=my_agent,
    max_requests=10,
    window_seconds=60  # 10 requests per minute
)

# Or use exponential backoff
from agenkit.middleware import RetryDecorator

agent = RetryDecorator(
    agent=my_agent,
    max_attempts=3,
    backoff_factor=2.0  # Exponential backoff
)
```

#### Error: "Context length exceeded"

**Symptom:**
```python
InvalidRequestError: This model's maximum context length is 8192 tokens
```

**Cause:** Input too long for model context window.

**Solution:**
```python
# Solution 1: Use model with larger context
llm = OpenAIAdapter(model="gpt-4-turbo")  # 128k context

# Solution 2: Truncate history
from agenkit.patterns import ConversationalAgent

agent = ConversationalAgent(
    llm=llm,
    max_history=10  # Keep only last 10 messages
)

# Solution 3: Summarize old messages
from agenkit.patterns import MemoryHierarchyAgent

agent = MemoryHierarchyAgent(
    llm=llm,
    short_term_size=10,
    long_term_size=100,
    summarization_interval=20  # Summarize every 20 messages
)
```

#### Error: "Model not found"

**Symptom:**
```python
NotFoundError: The model `gpt-5` does not exist
```

**Cause:** Typo in model name or model doesn't exist.

**Solution:**
```python
# ✅ Correct model names
OpenAIAdapter(model="gpt-4")
OpenAIAdapter(model="gpt-4-turbo")
OpenAIAdapter(model="gpt-3.5-turbo")

AnthropicAdapter(model="claude-3-5-sonnet-20241022")
AnthropicAdapter(model="claude-3-opus-20240229")

# ❌ Wrong
OpenAIAdapter(model="gpt-5")  # Doesn't exist
OpenAIAdapter(model="gpt4")  # Missing hyphen
```

---

## Debugging Strategies

### Enable Verbose Logging

**Python:**
```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or for specific logger
logger = logging.getLogger("agenkit")
logger.setLevel(logging.DEBUG)

# Use with patterns
agent = ReActAgent(
    llm=my_llm,
    tools=tools,
    verbose=True  # ← Enable verbose mode
)
```

**Go:**
```go
import "log"

// Enable debug logging
log.SetFlags(log.LstdFlags | log.Lshortfile)

// Add logging to your agent
func (a *MyAgent) Process(ctx context.Context, msg core.Message) (core.Message, error) {
    log.Printf("Processing message: %+v", msg)
    // ... process
    log.Printf("Result: %+v", result)
    return result, nil
}
```

**TypeScript:**
```typescript
// Enable debug logging
const DEBUG = true;

class MyAgent implements Agent {
    async process(message: Message): Promise<Message> {
        if (DEBUG) console.log('Processing:', message);
        const result = await this.doWork(message);
        if (DEBUG) console.log('Result:', result);
        return result;
    }
}
```

### Inspect Message Flow

**Add middleware for logging:**
```python
from agenkit import Agent, Message

class LoggingMiddleware(Agent):
    """Log all messages passing through."""

    def __init__(self, agent: Agent):
        self.agent = agent

    @property
    def name(self) -> str:
        return self.agent.name

    async def process(self, message: Message) -> Message:
        print(f"→ Input to {self.agent.name}: {message.content[:100]}...")

        result = await self.agent.process(message)

        print(f"← Output from {self.agent.name}: {result.content[:100]}...")
        print(f"   Metadata: {result.metadata}")

        return result

# Wrap agents
agent = LoggingMiddleware(my_agent)
```

### Test Components Individually

**Isolate the problem:**
```python
# Test 1: Agent works independently?
agent = MyAgent()
result = await agent.process(Message(role="user", content="test"))
assert result is not None

# Test 2: Pattern works with mock agents?
class MockAgent(Agent):
    @property
    def name(self) -> str:
        return "mock"

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content="mock response")

pipeline = SequentialAgent(agents=[MockAgent(), MockAgent()])
result = await pipeline.process(Message(role="user", content="test"))
assert result is not None

# Test 3: LLM adapter works?
llm = OpenAIAdapter(model="gpt-4")
response = await llm.complete("Say hello")
assert "hello" in response.lower()
```

### Use Breakpoints

**Python (pdb):**
```python
async def process(self, message: Message) -> Message:
    import pdb; pdb.set_trace()  # ← Breakpoint
    # ... your code
```

**TypeScript (debugger):**
```typescript
async process(message: Message): Promise<Message> {
    debugger;  // ← Breakpoint
    // ... your code
}
```

**Go (Delve):**
```bash
# Install delve
go install github.com/go-delve/delve/cmd/dlv@latest

# Run with debugger
dlv debug main.go
(dlv) break main.main
(dlv) continue
```

### Check Message Metadata

**Messages carry debugging info:**
```python
result = await agent.process(message)

# Inspect metadata
print(f"Agent: {result.metadata.get('agent_name')}")
print(f"Timestamp: {result.metadata.get('timestamp')}")
print(f"Execution time: {result.metadata.get('execution_time_ms')}ms")
print(f"LLM calls: {result.metadata.get('llm_calls')}")
print(f"Tokens: {result.metadata.get('tokens_used')}")
```

---

## Performance Issues

### Slow Response Times

**Problem:** Agent takes too long to respond.

**Diagnosis:**
```python
import time

async def benchmark_agent():
    start = time.time()

    # Time LLM call
    llm_start = time.time()
    llm_response = await llm.complete("test")
    llm_time = time.time() - llm_start

    # Time agent processing
    agent_start = time.time()
    result = await agent.process(message)
    agent_time = time.time() - agent_start

    total_time = time.time() - start

    print(f"LLM call: {llm_time:.2f}s ({llm_time/total_time*100:.1f}%)")
    print(f"Agent processing: {agent_time:.2f}s ({agent_time/total_time*100:.1f}%)")
    print(f"Total: {total_time:.2f}s")
```

**Solutions:**
```python
# 1. Use faster model
llm = OpenAIAdapter(model="gpt-3.5-turbo")  # Faster than gpt-4

# 2. Use streaming
llm = OpenAIAdapter(model="gpt-4", stream=True)

# 3. Parallel execution
parallel = ParallelAgent(agents=[agent1, agent2, agent3])  # Concurrent

# 4. Cache results
from agenkit.middleware import CachingMiddleware

agent = CachingMiddleware(agent=my_agent, ttl=3600)

# 5. Reduce max_iterations
react_agent = ReActAgent(
    llm=llm,
    tools=tools,
    max_iterations=5  # Lower limit
)
```

### High Memory Usage

**Problem:** Process uses too much memory.

**Diagnosis:**
```python
import tracemalloc

tracemalloc.start()

# Run your code
await agent.process(message)

# Check memory usage
current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 10**6:.1f} MB")
print(f"Peak: {peak / 10**6:.1f} MB")

tracemalloc.stop()
```

**Solutions:**
```python
# 1. Limit conversation history
agent = ConversationalAgent(
    llm=llm,
    max_history=10  # Lower limit
)

# 2. Use memory hierarchy
agent = MemoryHierarchyAgent(
    llm=llm,
    short_term_size=10,
    summarization_interval=20
)

# 3. Clear history periodically
if len(agent.history) > 100:
    agent.clear_history()

# 4. Use generators/streaming
async for chunk in llm.complete_stream(prompt):
    process_chunk(chunk)  # Don't accumulate in memory
```

### High LLM Costs

**Problem:** LLM API costs too high.

**Diagnosis:**
```python
# Track token usage
total_tokens = 0

class TokenCounter(Agent):
    def __init__(self, agent):
        self.agent = agent

    @property
    def name(self):
        return self.agent.name

    async def process(self, message: Message) -> Message:
        result = await self.agent.process(message)
        tokens = result.metadata.get("tokens_used", 0)
        global total_tokens
        total_tokens += tokens
        print(f"Tokens this call: {tokens}")
        print(f"Total tokens: {total_tokens}")
        return result
```

**Solutions:**
```python
# 1. Use cheaper models
llm = OpenAIAdapter(model="gpt-3.5-turbo")  # $0.0015/1K vs $0.03/1K

# 2. Use Fallback to try cheap first
from agenkit.patterns import FallbackAgent

cost_optimizer = FallbackAgent(
    agents=[
        cheap_model_agent,    # Try this first
        premium_model_agent   # Fallback if needed
    ]
)

# 3. Reduce prompt length
# Remove unnecessary context
prompt = f"{essential_context}\n{user_query}"

# 4. Limit iterations
reflect_agent = ReflectionAgent(
    agent=writer,
    critic=critic,
    max_iterations=3  # Lower limit
)

# 5. Cache aggressively
from agenkit.middleware import CachingMiddleware

agent = CachingMiddleware(
    agent=my_agent,
    ttl=86400  # Cache for 24 hours
)
```

---

## Cross-Language Issues

### Go: "undefined: context"

**Problem:**
```go
undefined: context
```

**Solution:**
```go
import "context"  // ← Add import

func (a *MyAgent) Process(ctx context.Context, msg core.Message) (core.Message, error) {
    // ...
}
```

### TypeScript: "Cannot use 'await' outside async function"

**Problem:**
```typescript
await is only valid in async functions
```

**Solution:**
```typescript
// ✅ Top-level await (if using ES modules)
const result = await agent.process(message);

// ✅ Or wrap in async function
async function main() {
    const result = await agent.process(message);
}
main();

// ✅ Or use .then()
agent.process(message).then(result => {
    console.log(result);
});
```

### Rust: "borrowed value does not live long enough"

**Problem:**
```rust
error[E0597]: `msg` does not live long enough
```

**Solution:**
```rust
// ✅ Clone when needed
async fn process(&self, message: Message) -> Result<Message, Box<dyn Error + Send + Sync>> {
    let content = message.content.clone();  // ← Clone to extend lifetime
    // ... use content
}

// ✅ Or take ownership
async fn process(&self, mut message: Message) -> Result<Message, Box<dyn Error + Send + Sync>> {
    // message is now owned by this function
}
```

### C++: "use of deleted function"

**Problem:**
```cpp
error: use of deleted function 'Message::Message(const Message&)'
```

**Solution:**
```cpp
// ✅ Use std::move for move-only types
Message response = std::move(message);

// ✅ Or use smart pointers
std::unique_ptr<Message> msg = std::make_unique<Message>(...);
```

### Zig: "expected type '[]const u8', found '*const [10:0]u8'"

**Problem:**
```zig
expected type '[]const u8', found '*const [10:0]u8'
```

**Solution:**
```zig
// ✅ Use slice syntax
const name: []const u8 = "my-agent";  // ← Slice type

// ❌ Wrong
const name: *const u8 = "my-agent";  // Pointer, not slice
```

---

## Production Issues

### High Error Rates

**Problem:** Many agent failures in production.

**Diagnosis:**
```python
# Track error rates
error_count = 0
total_count = 0

async def track_errors():
    global error_count, total_count
    try:
        result = await agent.process(message)
        total_count += 1
    except Exception as e:
        error_count += 1
        total_count += 1
        print(f"Error rate: {error_count/total_count*100:.1f}%")
        raise
```

**Solutions:**
```python
# 1. Use Fallback for reliability
from agenkit.patterns import FallbackAgent

reliable_agent = FallbackAgent(
    agents=[primary, backup, last_resort]
)

# 2. Add retry logic
from agenkit.middleware import RetryDecorator

agent = RetryDecorator(
    agent=my_agent,
    max_attempts=3,
    backoff_factor=2.0
)

# 3. Add circuit breaker
from agenkit.middleware import CircuitBreaker

agent = CircuitBreaker(
    agent=my_agent,
    failure_threshold=5,
    recovery_timeout=60
)

# 4. Add timeouts
from agenkit.middleware import TimeoutDecorator

agent = TimeoutDecorator(
    agent=my_agent,
    timeout_seconds=30
)
```

### Deployment Issues

**Problem:** Works locally, fails in production.

**Common Causes:**
1. **Environment variables not set**
2. **Network restrictions**
3. **Resource limits**
4. **Different Python/Node/Go versions**

**Solutions:**
```python
# 1. Check environment
import os
print(f"OPENAI_API_KEY set: {bool(os.getenv('OPENAI_API_KEY'))}")
print(f"Python version: {sys.version}")

# 2. Add health checks
from agenkit import Message

async def health_check():
    try:
        agent = MyAgent()
        result = await agent.process(Message(role="user", content="health check"))
        return {"status": "healthy", "response": result.content}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# 3. Add monitoring
import time

async def monitored_process(message):
    start = time.time()
    try:
        result = await agent.process(message)
        duration = time.time() - start
        log_metric("agent.success", 1, {"duration": duration})
        return result
    except Exception as e:
        duration = time.time() - start
        log_metric("agent.error", 1, {"duration": duration, "error": type(e).__name__})
        raise
```

---

## FAQ

### General

#### Q: What languages does agenkit support?

**A:** Agenkit provides 100% feature parity across 6 languages:
- Python
- Go
- TypeScript
- Rust
- C++
- Zig

All patterns, features, and APIs work identically in all languages.

#### Q: Is agenkit production-ready?

**A:** Yes. Agenkit has:
- 100% test coverage (3,310+ tests passing)
- Used in real production systems
- Framework overhead <0.01% of LLM call time
- Comprehensive error handling
- Performance benchmarks in all languages

#### Q: How does agenkit compare to LangChain?

**A:** Key differences:

| Feature | LangChain | Agenkit |
|---------|-----------|---------|
| Languages | Python only | 6 languages |
| Architecture | Monolithic | Modular/composable |
| Patterns | Limited | 18 patterns |
| Overhead | Higher | <0.01% |
| Lock-in | Higher | Escape hatches |
| Test coverage | Partial | 100% |

See [Framework Migration Guide](FRAMEWORK_MIGRATION.md) for details.

#### Q: Can I use agenkit with my existing framework?

**A:** Yes! Agenkit is designed for gradual adoption:

```python
# Wrap existing framework agent
class LangChainWrapper(Agent):
    def __init__(self, langchain_agent):
        self.lc_agent = langchain_agent

    @property
    def name(self) -> str:
        return "langchain-wrapper"

    async def process(self, message: Message) -> Message:
        # Convert agenkit → LangChain
        lc_input = message.content

        # Use LangChain agent
        lc_output = self.lc_agent.run(lc_input)

        # Convert LangChain → agenkit
        return Message(role="assistant", content=lc_output)

# Use in agenkit patterns
pipeline = SequentialAgent(
    agents=[
        LangChainWrapper(my_lc_agent),
        AgenkitAgent()
    ]
)
```

#### Q: How do I contribute to agenkit?

**A:** See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for:
- Development setup
- Code standards
- Testing requirements
- Pull request process

### Patterns

#### Q: Which pattern should I use?

**A:** Follow this decision tree:

```
Need multiple agents?
  ├─ Sequential → SequentialAgent
  ├─ Parallel → ParallelAgent
  ├─ Route to specialist → RouterAgent
  └─ Failover → FallbackAgent

Need quality improvement?
  ├─ Iterative refinement → ReflectionAgent
  ├─ With tools → ReActAgent
  ├─ Planned approach → PlanningAgent
  └─ Advanced reasoning → ReasoningWithTools

Need coordination?
  ├─ Oversight → SupervisorAgent
  ├─ Complex workflow → OrchestrationAgent
  ├─ Collaboration → Multiagent or Collaborative
  └─ Human approval → HumanInLoopAgent

Simple task?
  ├─ Chatbot → ConversationalAgent
  ├─ Single task → TaskAgent
  └─ Tool delegation → AgentsAsTools
```

See [Pattern Guide](PATTERN_GUIDE.md) for complete details.

#### Q: Can I combine patterns?

**A:** Yes! Patterns are designed to compose:

```python
# Sequential + Reflection
refiner = ReflectionAgent(agent=writer, critic=critic)
pipeline = SequentialAgent(agents=[extractor, refiner, formatter])

# Parallel + Router + Fallback
weather_ha = FallbackAgent(agents=[openai_weather, anthropic_weather])
stock_ha = FallbackAgent(agents=[openai_stock, anthropic_stock])
router = RouterAgent(routes={"weather": weather_ha, "stocks": stock_ha})
```

See [Pattern Composition](PATTERN_GUIDE.md#pattern-composition) section.

#### Q: How do I handle errors in patterns?

**A:** Use Fallback or middleware:

```python
# Option 1: Fallback pattern
reliable = FallbackAgent(agents=[primary, backup])

# Option 2: Retry middleware
from agenkit.middleware import RetryDecorator
agent = RetryDecorator(agent=my_agent, max_attempts=3)

# Option 3: Try-catch
try:
    result = await agent.process(message)
except Exception as e:
    # Handle error
    result = await fallback_agent.process(message)
```

### LLM Integration

#### Q: Which LLM providers are supported?

**A:** Agenkit supports all major providers via adapters:

- OpenAI (GPT-4, GPT-3.5, etc.)
- Anthropic (Claude 3.5, Claude 3, etc.)
- Local models (Ollama, LM Studio)
- Any provider via LiteLLM

```python
# OpenAI
from agenkit.adapters import OpenAIAdapter
llm = OpenAIAdapter(model="gpt-4")

# Anthropic
from agenkit.adapters import AnthropicAdapter
llm = AnthropicAdapter(model="claude-3-5-sonnet-20241022")

# Ollama (local)
from agenkit.adapters import OllamaAdapter
llm = OllamaAdapter(model="llama3.3")

# Any provider via LiteLLM
from agenkit.adapters import LiteLLMAdapter
llm = LiteLLMAdapter(model="bedrock/anthropic.claude-v2")
```

#### Q: How do I reduce LLM costs?

**A:** Multiple strategies:

```python
# 1. Use cheaper models
llm = OpenAIAdapter(model="gpt-3.5-turbo")  # 20x cheaper than GPT-4

# 2. Try cheap first, fallback to expensive
cost_optimizer = FallbackAgent(
    agents=[
        TaskAgent(llm=cheap_llm),
        TaskAgent(llm=premium_llm)
    ]
)

# 3. Cache aggressively
from agenkit.middleware import CachingMiddleware
agent = CachingMiddleware(agent=my_agent, ttl=86400)

# 4. Limit iterations
reflect = ReflectionAgent(agent=writer, critic=critic, max_iterations=3)

# 5. Shorter prompts
# Use essential context only
```

#### Q: How do I handle rate limits?

**A:** Use rate limiting middleware:

```python
from agenkit.middleware import RateLimiter

agent = RateLimiter(
    agent=my_agent,
    max_requests=10,
    window_seconds=60  # 10 requests per minute
)

# Or use exponential backoff
from agenkit.middleware import RetryDecorator

agent = RetryDecorator(
    agent=my_agent,
    max_attempts=5,
    backoff_factor=2.0  # Exponential backoff
)
```

### Performance

#### Q: Is agenkit fast?

**A:** Yes. Framework overhead is negligible:

- **Python**: 1-7 μs per pattern
- **Go**: 0.2-0.7 μs per pattern
- **TypeScript**: 1-6 μs per pattern
- **Rust**: 0.2-0.5 μs per pattern
- **C++**: 0.15-0.5 μs per pattern
- **Zig**: 0.15-0.3 μs per pattern

**LLM calls**: 100,000-500,000 μs

**Conclusion**: Framework overhead is <0.01% of total time.

See [Performance Benchmarks](PATTERN_BENCHMARK_RESULTS.md).

#### Q: Which language is fastest?

**A:** Compiled languages (Go, Rust, C++, Zig) are 5-100x faster than interpreted (Python, TypeScript) for compute-heavy tasks.

But LLM calls dominate latency (99.99%), so language choice matters more for:
- Team expertise
- Ecosystem (web, ML, systems)
- Development speed
- Type safety requirements

See [Cross-Language Migration Guide](CROSS_LANGUAGE_MIGRATION.md#performance-considerations).

#### Q: How do I optimize performance?

**A:** Follow this hierarchy:

1. **Optimize LLM calls** (biggest impact):
   - Use faster models (GPT-3.5 vs GPT-4)
   - Reduce prompt length
   - Use streaming
   - Cache results
   - Limit iterations

2. **Optimize patterns**:
   - Use Parallel for independent tasks
   - Reduce Sequential stages
   - Limit Reflection iterations

3. **Optimize framework** (smallest impact):
   - Use compiled language (Go, Rust, C++, Zig)
   - But gains are minimal vs LLM time

### Migration

#### Q: How long does migration take?

**A:** Depends on source:

| From | To | Time | Notes |
|------|----|----|-------|
| LangChain | Agenkit | 1-2 weeks | Clean mapping |
| LangGraph | Agenkit | 2-3 weeks | Workflow conversion |
| CrewAI | Agenkit | 1-2 weeks | Similar concepts |
| AutoGen | Agenkit | 2-3 weeks | Conversation management |
| Python | Go/TypeScript | 2-4 hours per agent | Easy syntax change |
| Python | Rust/C++/Zig | 4-16 hours per agent | New concepts |

#### Q: Can I migrate gradually?

**A:** Yes! Recommended approach:

```python
# Phase 1: Wrap existing agents
wrapped_agent = FrameworkWrapper(old_agent)

# Phase 2: Use with agenkit patterns
pipeline = SequentialAgent(agents=[wrapped_agent, new_agent])

# Phase 3: Replace gradually
pipeline = SequentialAgent(agents=[new_agent1, new_agent2])
```

See [Framework Migration Guide](FRAMEWORK_MIGRATION.md#gradual-migration-strategy).

#### Q: Will my code break during migration?

**A:** Minimize risk with:

1. **Regression tests**:
```python
def test_migration_equivalence():
    old_result = old_agent.run("test")
    new_result = await new_agent.process(Message(...))
    assert old_result == new_result.content
```

2. **A/B testing**:
```python
# Run both in parallel, compare results
old_result = old_agent.run(input)
new_result = await new_agent.process(Message(...))

if old_result != new_result.content:
    log_discrepancy(old_result, new_result)
```

3. **Gradual rollout**:
- 10% traffic to new system
- Monitor metrics
- Increase gradually

### Best Practices

#### Q: Should I use middleware?

**A:** Yes, for cross-cutting concerns:

```python
# ✅ Use middleware for
- Retry logic (RetryDecorator)
- Rate limiting (RateLimiter)
- Caching (CachingMiddleware)
- Timeouts (TimeoutDecorator)
- Logging (custom middleware)
- Metrics (custom middleware)

# ❌ Don't use middleware for
- Business logic (put in agent)
- Agent-specific behavior
```

#### Q: How should I structure my code?

**A:** Follow these conventions:

```
my-app/
├── agents/
│   ├── __init__.py
│   ├── validator.py      # One agent per file
│   ├── processor.py
│   └── formatter.py
├── patterns/
│   ├── __init__.py
│   └── pipelines.py      # Pattern compositions
├── middleware/
│   ├── __init__.py
│   └── custom.py         # Custom middleware
├── tests/
│   ├── test_agents.py    # Test each agent
│   ├── test_patterns.py  # Test compositions
│   └── test_e2e.py       # End-to-end tests
└── main.py               # Entry point
```

#### Q: How should I test agents?

**A:** Use this testing pyramid:

```python
# 1. Unit tests (many) - Test agents independently
@pytest.mark.asyncio
async def test_agent():
    agent = MyAgent()
    result = await agent.process(Message(role="user", content="test"))
    assert result.content == "expected"

# 2. Integration tests (some) - Test pattern compositions
@pytest.mark.asyncio
async def test_pipeline():
    pipeline = SequentialAgent(agents=[agent1, agent2])
    result = await pipeline.process(Message(role="user", content="input"))
    assert "expected" in result.content

# 3. E2E tests (few) - Test full system
@pytest.mark.asyncio
async def test_end_to_end():
    result = await full_system.process(Message(role="user", content="user query"))
    assert result.metadata["success"] == True
```

#### Q: How do I handle secrets?

**A:** Never hardcode secrets:

```python
# ❌ Wrong
llm = OpenAIAdapter(api_key="sk-...")  # Hardcoded!

# ✅ Correct - environment variables
import os
llm = OpenAIAdapter(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Also correct - secret manager
from my_secrets import get_secret
llm = OpenAIAdapter(api_key=get_secret("openai-api-key"))

# ✅ In production
# Use: AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, HashiCorp Vault
```

#### Q: Should I use type hints?

**A:** Yes (strongly recommended):

```python
# ✅ With type hints (catches errors early)
async def process(self, message: Message) -> Message:
    return Message(role="assistant", content="response")

# ❌ Without type hints (errors at runtime)
async def process(self, message):
    return Message(role="assistant", content="response")

# Run mypy to check types
mypy your_code.py
```

---

## Still Having Issues?

### Get Help

1. **Check documentation**:
   - [Getting Started Guides](getting-started/)
   - [Pattern Guide](PATTERN_GUIDE.md)
   - [Migration Guides](CROSS_LANGUAGE_MIGRATION.md)

2. **Search existing issues**:
   - [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)

3. **Ask the community**:
   - [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)

4. **Report a bug**:
   - [New Issue](https://github.com/scttfrdmn/agenkit/issues/new)

### When Reporting Issues

Include:
- [ ] Agenkit version (`pip show agenkit`)
- [ ] Language and version (Python 3.12, Go 1.22, etc.)
- [ ] Operating system
- [ ] Minimal reproducible example
- [ ] Full error message and stack trace
- [ ] What you expected vs what happened

**Good issue report:**
```markdown
**Environment:**
- agenkit version: 0.44.0
- Python version: 3.12.0
- OS: macOS 14.0

**Issue:**
SequentialAgent raises TypeError when processing messages.

**Minimal example:**
```python
from agenkit.patterns import SequentialAgent
from agenkit import Agent, Message

class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "test"

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content="response")

pipeline = SequentialAgent(agents=[MyAgent()])
result = await pipeline.process(Message(role="user", content="test"))
```

**Error:**
```
TypeError: 'NoneType' object is not iterable
  File "agenkit/patterns/sequential.py", line 45, in process
```

**Expected:**
Should process message successfully.
```

---

**Happy debugging! 🐛🔧**
