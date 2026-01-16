# Quick Reference: TypeScript → Python Migration

**For**: TypeScript developers migrating Agenkit code to Python
**Time**: 15 minute read
**Full Details**: See [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) and [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md)

---

## Key Differences at a Glance

| Aspect | TypeScript | Python |
|--------|------------|--------|
| **Typing** | Static (compile-time) | Dynamic (runtime, optional hints) |
| **Errors** | Exceptions (`try/catch`) | Exceptions (`try/except`) |
| **Concurrency** | Promises + async/await | async/await + asyncio |
| **Memory** | GC (V8) | GC + refcounting |
| **Performance** | Fast (JIT) | Slower (interpreted) |
| **Deployment** | Node.js + packages | Interpreter + packages |
| **Type checking** | tsc, compile-time | mypy, optional |

---

## Message Creation

### TypeScript
```typescript
import { Message } from '@agenkit/core';

const msg: Message = {
    role: 'user',
    content: 'Hello!',
    metadata: {
        key: 'value',
        count: 42,
    },
};
```

### Python
```python
from agenkit import Message

msg = Message(
    role="user",
    content="Hello!",
    metadata={
        "key": "value",
        "count": 42,
    }
)
```

**Changes**:
- Import path: `@agenkit/core` → `agenkit`
- Object literal `{ }` → Constructor call `Message(...)`
- Single quotes `'...'` → Double quotes `"..."` (Pythonic convention)
- Interface → `@dataclass` or regular class
- `Record<string, any>` → `dict` or `Dict[str, Any]`

---

## Agent Implementation

### TypeScript
```typescript
import { Agent, Message } from '@agenkit/core';

class MyAgent implements Agent {
    private config: Config;

    constructor(config: Config) {
        this.config = config;
    }

    get name(): string {
        return 'my-agent';
    }

    get capabilities(): string[] {
        return ['text', 'analysis'];
    }

    async process(message: Message): Promise<Message> {
        return {
            role: 'assistant',
            content: 'Response',
        };
    }
}
```

### Python
```python
from agenkit import Agent, Message
from typing import List

class MyAgent(Agent):
    def __init__(self, config: dict):
        self.config = config

    @property
    def name(self) -> str:
        return "my-agent"

    @property
    def capabilities(self) -> List[str]:
        return ["text", "analysis"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content="Response"
        )
```

**Changes**:
- `implements Agent` → `(Agent)` inheritance (duck typing)
- `private config` → `self.config` (no private fields)
- `constructor()` → `__init__(self, ...)`
- `get name()` → `@property` decorator
- `Promise<Message>` → No need to wrap (async functions return coroutines)
- `string[]` → `List[str]` or `list[str]` (Python 3.10+)
- Object literal `{ }` → Constructor call

---

## Error Handling

### TypeScript
```typescript
try {
    const result = await agent.process(message);
    // Use result
} catch (error) {
    if (error instanceof AgentError) {
        throw new Error(`Process failed: ${error.message}`);
    }
    throw error;  // Re-throw unknown
}
```

### Python
```python
try:
    result = await agent.process(message)
    # Use result
except AgentError as e:
    raise RuntimeError(f"Process failed: {e}") from e
# Unknown exceptions propagate automatically
```

**Changes**:
- `catch (error)` → `except Exception as e`
- `instanceof` → `isinstance()` or exception type in `except`
- `throw new Error()` → `raise RuntimeError()` or custom exception
- Error wrapping: `throw new Error(...)` → `raise ... from e`
- `try/catch/finally` → `try/except/finally` (very similar!)

**Custom Error Types**:

**TypeScript**:
```typescript
class AgentError extends Error {
    constructor(
        public agentName: string,
        message: string,
        public cause?: Error
    ) {
        super(message);
        this.name = 'AgentError';
    }
}

throw new AgentError('my-agent', 'Timeout');
```

**Python**:
```python
class AgentError(Exception):
    def __init__(self, agent_name: str, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.agent_name = agent_name
        self.cause = cause

raise AgentError("my-agent", "Timeout")
```

---

## Concurrency

### TypeScript (Promises)
```typescript
// Create promise
const promise = agent.process(message);

// Await promise
const result = await promise;

// Run multiple in parallel
const [result1, result2, result3] = await Promise.all([
    agent1.process(msg),
    agent2.process(msg),
    agent3.process(msg),
]);

// Race
const fastest = await Promise.race([
    agent1.process(msg),
    agent2.process(msg),
]);

// AllSettled (handle failures)
const results = await Promise.allSettled([
    agent1.process(msg),
    agent2.process(msg),
]);
```

### Python (async/await)
```python
import asyncio

# Create coroutine (like Promise)
coro = agent.process(message)

# Await coroutine
result = await coro

# Run multiple in parallel
result1, result2, result3 = await asyncio.gather(
    agent1.process(msg),
    agent2.process(msg),
    agent3.process(msg),
)

# Race (first to complete)
done, pending = await asyncio.wait(
    [agent1.process(msg), agent2.process(msg)],
    return_when=asyncio.FIRST_COMPLETED
)
fastest = done.pop().result()

# Gather with error handling
results = await asyncio.gather(
    agent1.process(msg),
    agent2.process(msg),
    return_exceptions=True  # Like allSettled
)
```

**Changes**:
- `Promise` → Coroutine (created by `async def`)
- `Promise.all()` → `asyncio.gather()`
- `Promise.race()` → `asyncio.wait(..., return_when=FIRST_COMPLETED)`
- `Promise.allSettled()` → `asyncio.gather(..., return_exceptions=True)`
- `new Promise((resolve, reject) => ...)` → `async def` function
- No explicit Promise constructor needed in Python

---

## Patterns

### Sequential

**TypeScript**:
```typescript
import { SequentialAgent } from '@agenkit/patterns';

const sequential = new SequentialAgent({
    agents: [agent1, agent2, agent3],
});

const result = await sequential.process(message);
```

**Python**:
```python
from agenkit.patterns import SequentialAgent

sequential = SequentialAgent(
    agents=[agent1, agent2, agent3]
)

result = await sequential.process(message)
```

### Parallel

**TypeScript**:
```typescript
import { ParallelAgent } from '@agenkit/patterns';

const parallel = new ParallelAgent({
    agents: [agentA, agentB, agentC],
});

const result = await parallel.process(message);
```

**Python**:
```python
from agenkit.patterns import ParallelAgent

parallel = ParallelAgent(
    agents=[agent_a, agent_b, agent_c]
)

result = await parallel.process(message)
```

### Router

**TypeScript**:
```typescript
import { RouterAgent } from '@agenkit/patterns';

const router = new RouterAgent({
    router: (msg: Message) => {
        if (msg.content.includes('urgent')) {
            return 'fast';
        }
        return 'thorough';
    },
    agents: {
        fast: fastAgent,
        thorough: thoroughAgent,
    },
});
```

**Python**:
```python
from agenkit.patterns import RouterAgent

def router_fn(msg: Message) -> str:
    if "urgent" in msg.content:
        return "fast"
    return "thorough"

router = RouterAgent(
    router=router_fn,
    agents={
        "fast": fast_agent,
        "thorough": thorough_agent,
    }
)
```

**Changes**:
- Arrow function `(msg) => { }` → Regular function `def router_fn(msg):`
- `includes()` → `in` operator
- Object literal config → Named parameters
- CamelCase → snake_case (naming convention)

---

## Common Gotchas

### 1. Undefined vs None

**TypeScript**: `undefined` and `null` are different
```typescript
let value: string | undefined = undefined;
let nullable: string | null = null;

// Check for both
if (value !== undefined && value !== null) {
    // Use value
}
```

**Python**: Only `None` exists
```python
value: str | None = None

# Simple check
if value is not None:
    # Use value
```

**Migration**: Replace `undefined` and `null` with `None`

### 2. Array/Object Methods

**TypeScript**: Rich array methods
```typescript
const numbers = [1, 2, 3, 4, 5];

// Map
const doubled = numbers.map(x => x * 2);

// Filter
const evens = numbers.filter(x => x % 2 === 0);

// Reduce
const sum = numbers.reduce((acc, x) => acc + x, 0);

// Find
const found = numbers.find(x => x > 3);
```

**Python**: List comprehensions and functions
```python
numbers = [1, 2, 3, 4, 5]

# Map (list comprehension preferred)
doubled = [x * 2 for x in numbers]

# Filter
evens = [x for x in numbers if x % 2 == 0]

# Reduce
from functools import reduce
sum_val = reduce(lambda acc, x: acc + x, numbers, 0)
# Or just: sum(numbers)

# Find
found = next((x for x in numbers if x > 3), None)
```

**Migration**:
- `.map()` → List comprehension `[... for x in ...]`
- `.filter()` → List comprehension with condition `[x for x in ... if ...]`
- `.reduce()` → `functools.reduce()` or built-in functions
- `.find()` → `next(generator, default)`
- `.forEach()` → `for x in ...` loop

### 3. Type Annotations

**TypeScript**: Compile-time type checking
```typescript
// Types enforced by TypeScript compiler
function process(value: string): number {
    return parseInt(value);
}

process(123);  // Compile error!
```

**Python**: Optional runtime type hints
```python
# Types are hints, not enforced by Python
def process(value: str) -> int:
    return int(value)

process(123)  # No error! (unless using mypy)
```

**Migration**:
- TypeScript types are enforced
- Python types are hints (use `mypy` for static checking)
- Runtime behavior differs: Python is more permissive

### 4. JSON Handling

**TypeScript**: Built-in JSON with any
```typescript
// Parse JSON
const data = JSON.parse(jsonString);  // type: any

// Stringify
const json = JSON.stringify(data);

// Type assertion needed
const typed: Message = data as Message;
```

**Python**: json module
```python
import json

# Parse JSON
data = json.loads(json_string)  # type: Any

# Stringify
json_str = json.dumps(data)

# Type checking (duck typing)
msg = Message(**data)  # Constructor validates
```

### 5. Async Context and Event Loops

**TypeScript**: Single global event loop
```typescript
// Just use await anywhere in async function
async function main() {
    const result = await agent.process(msg);
}

// Top-level await (ES2022+)
await main();
```

**Python**: Explicit event loop management
```python
import asyncio

# Must run with asyncio
async def main():
    result = await agent.process(msg)

# Entry point
if __name__ == "__main__":
    asyncio.run(main())

# Or in Jupyter/IPython
await main()  # Top-level await supported
```

---

## Testing

### TypeScript (Jest/Vitest)
```typescript
import { describe, it, expect } from 'vitest';
import { MyAgent } from './agent';
import { Message } from '@agenkit/core';

describe('MyAgent', () => {
    it('should process message correctly', async () => {
        const agent = new MyAgent();
        const msg: Message = {
            role: 'user',
            content: 'Test',
        };

        const result = await agent.process(msg);

        expect(result.role).toBe('assistant');
        expect(result.content).toContain('Processed');
    });

    it('should handle errors', async () => {
        const agent = new MyAgent();
        const invalid: Message = {
            role: 'user',
            content: '',
        };

        await expect(agent.process(invalid))
            .rejects
            .toThrow('Empty content');
    });
});
```

### Python (pytest)
```python
import pytest
from agenkit import Message
from myagent import MyAgent

@pytest.mark.asyncio
async def test_agent_process():
    agent = MyAgent()
    msg = Message(role="user", content="Test")

    result = await agent.process(msg)

    assert result.role == "assistant"
    assert "Processed" in result.content

@pytest.mark.asyncio
async def test_agent_handles_errors():
    agent = MyAgent()
    invalid = Message(role="user", content="")

    with pytest.raises(ValueError, match="Empty content"):
        await agent.process(invalid)
```

**Changes**:
- `describe()` → No describe (use classes or file organization)
- `it()` → `def test_...()` or `async def test_...()`
- `expect().toBe()` → `assert ... ==`
- `expect().toContain()` → `assert ... in ...`
- `.rejects.toThrow()` → `pytest.raises()`
- `@pytest.mark.asyncio` decorator required for async tests

### Mocking

**TypeScript**:
```typescript
import { vi } from 'vitest';

it('should call agent', async () => {
    const mockAgent = {
        name: 'mock',
        capabilities: ['text'],
        process: vi.fn().mockResolvedValue({
            role: 'assistant',
            content: 'Mocked',
        }),
    };

    const result = await mockAgent.process(msg);

    expect(mockAgent.process).toHaveBeenCalledWith(msg);
});
```

**Python**:
```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_calls_agent():
    mock_agent = AsyncMock()
    mock_agent.name = "mock"
    mock_agent.capabilities = ["text"]
    mock_agent.process.return_value = Message(
        role="assistant",
        content="Mocked"
    )

    result = await mock_agent.process(msg)

    mock_agent.process.assert_called_once_with(msg)
```

---

## Performance Considerations

| Operation | TypeScript | Python | Notes |
|-----------|------------|--------|-------|
| Message creation | ~500ns | ~1μs | Python ~2x slower |
| Agent process (mock) | ~5μs | ~10μs | Python ~2x slower |
| Sequential (3 agents) | ~15μs | ~30μs | Consistent overhead |
| Parallel (3 agents) | ~5μs | ~20μs | Python GIL limitation |
| JSON parse/stringify | ~1-2μs | ~2-5μs | Python slower |

**Similarities**:
- Both single-threaded (event loop)
- Both have GC overhead
- Similar async/await patterns
- Comparable for I/O-bound work

**When to use Python**:
- Machine learning / AI integration (PyTorch, TensorFlow, Transformers)
- Data science (NumPy, pandas, Jupyter)
- Scientific computing
- Rapid prototyping
- Existing Python codebase

**When to keep TypeScript**:
- Web frontend integration
- Node.js backend (existing ecosystem)
- Slightly better raw performance
- Stronger compile-time type safety
- Smaller deployment footprint

---

## Migration Checklist

- [ ] Convert `interface` to `Protocol` or duck-typed class
- [ ] Replace `constructor()` with `__init__(self, ...)`
- [ ] Change `private`/`public` to naming conventions (`_private`)
- [ ] Convert `get property()` to `@property` decorator
- [ ] Update error handling: `catch` → `except`, `throw` → `raise`
- [ ] Replace `undefined`/`null` with `None`
- [ ] Convert array methods: `.map()` → list comprehension
- [ ] Update imports: `@agenkit/core` → `agenkit`
- [ ] Add `@pytest.mark.asyncio` to async tests
- [ ] Replace `Promise.all()` with `asyncio.gather()`
- [ ] Convert `const`/`let` to just variable assignment
- [ ] Update string literals: single quotes → double quotes (convention)
- [ ] Replace `Record<K, V>` with `Dict[K, V]` or `dict`
- [ ] Add `asyncio.run()` entry point for CLI scripts
- [ ] Update naming: camelCase → snake_case

---

## Quick Start

### TypeScript Project Structure
```
agenkit-ts/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts
│   └── agent.ts
└── tests/
    └── agent.test.ts
```

### Python Equivalent
```
agenkit/
├── pyproject.toml
├── agenkit/
│   ├── __init__.py
│   └── agent.py
└── tests/
    └── test_agent.py
```

**Build/Run**:
```bash
# TypeScript
npm install
npm run build
npm test
node dist/index.js

# Python
pip install -e .  # or: uv pip install -e .
pytest
python -m agenkit
# or with uv
uv run pytest
uv run python -m agenkit
```

---

## Type System Comparison

### TypeScript
```typescript
// Structural typing
interface Agent {
    name: string;
    process(msg: Message): Promise<Message>;
}

// Union types
type Result = Message | Error;

// Generics
interface Box<T> {
    value: T;
}

// Type guards
function isMessage(obj: any): obj is Message {
    return 'role' in obj && 'content' in obj;
}

// Literal types
type Role = 'user' | 'assistant' | 'system';
```

### Python
```python
from typing import Protocol, Union, Generic, TypeVar, Literal

# Protocol (structural typing)
class Agent(Protocol):
    name: str
    async def process(self, msg: Message) -> Message: ...

# Union types
Result = Union[Message, Exception]  # or Message | Exception (3.10+)

# Generics
T = TypeVar('T')
class Box(Generic[T]):
    value: T

# Type guards (runtime)
def is_message(obj: object) -> bool:
    return hasattr(obj, 'role') and hasattr(obj, 'content')

# Literal types
Role = Literal['user', 'assistant', 'system']
```

---

## Null Safety Comparison

### TypeScript
```typescript
// Strict null checks (tsconfig)
let value: string | undefined;

// Optional chaining
const content = message?.content;

// Nullish coalescing
const text = message.content ?? 'default';

// Non-null assertion (avoid!)
const content = message.content!;
```

### Python
```python
from typing import Optional

# Optional type
value: Optional[str] = None  # or str | None

# No optional chaining (use if/else)
content = message.content if message else None

# Default with or
text = message.content or "default"

# Or with walrus operator (3.8+)
if (content := getattr(message, 'content', None)):
    # Use content
```

---

## Async Patterns Comparison

### TypeScript
```typescript
// Promise chain
agent1.process(msg)
    .then(result => agent2.process(result))
    .then(final => console.log(final))
    .catch(error => console.error(error));

// Async/await (preferred)
try {
    const result1 = await agent1.process(msg);
    const result2 = await agent2.process(result1);
    console.log(result2);
} catch (error) {
    console.error(error);
}

// Parallel with destructuring
const [a, b, c] = await Promise.all([
    fetchA(),
    fetchB(),
    fetchC(),
]);
```

### Python
```python
# No promise chains (use async/await)
try:
    result1 = await agent1.process(msg)
    result2 = await agent2.process(result1)
    print(result2)
except Exception as error:
    print(f"Error: {error}")

# Parallel with gather
a, b, c = await asyncio.gather(
    fetch_a(),
    fetch_b(),
    fetch_c(),
)
```

---

## Full Resources

- [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) - Complete TypeScript idioms
- [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md) - Complete Python idioms
- [Main Migration Guide](MIGRATION.md) - Python → All languages
- [Agenkit Examples](../examples/) - Side-by-side code samples
- [Python Documentation](../agenkit/) - Full Python API reference

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
