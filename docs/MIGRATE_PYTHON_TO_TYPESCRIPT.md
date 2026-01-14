# Quick Reference: Python → TypeScript Migration

**For**: Python developers migrating Agenkit code to TypeScript
**Time**: 15 minute read
**Full Details**: See [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md) and [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md)

---

## Key Differences at a Glance

| Aspect | Python | TypeScript |
|--------|--------|------------|
| **Typing** | Dynamic, optional hints | Static, structural |
| **Errors** | Exceptions (`try/except`) | Exceptions (`try/catch`) |
| **Concurrency** | `async/await` + `asyncio` | `async/await` + Promises |
| **Memory** | GC + refcounting | GC (V8) |
| **Performance** | Slow (interpreted) | Similar (JIT compiled) |
| **Deployment** | Interpreter + packages | Browser + Node.js |

---

## Message Creation

### Python
```python
from agenkit import Message
from datetime import datetime

msg = Message(
    role="user",
    content="Hello!",
    metadata={"key": "value"},
    timestamp=datetime.now()
)
```

### TypeScript
```typescript
import { Message } from '@agenkit/core';

const msg: Message = {
    role: 'user',
    content: 'Hello!',
    metadata: { key: 'value' },
    timestamp: new Date()
};
```

**Changes**:
- Import path: `agenkit` → `@agenkit/core`
- Constructor call → Object literal
- Type hints: `Message(...)` → `: Message = {...}`
- Datetime: `datetime.now()` → `new Date()`
- String quotes: `"..."` → `'...'` (convention)

---

## Agent Implementation

### Python
```python
from agenkit import Agent, Message

class MyAgent(Agent):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["text", "analysis"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content=f"Processed: {message.content}"
        )
```

### TypeScript
```typescript
import { Agent, Message } from '@agenkit/core';

class MyAgent implements Agent {
    constructor(private _name: string) {}

    get name(): string {
        return this._name;
    }

    get capabilities(): string[] {
        return ['text', 'analysis'];
    }

    async process(message: Message): Promise<Message> {
        return {
            role: 'assistant',
            content: `Processed: ${message.content}`
        };
    }
}
```

**Changes**:
- Inheritance: `class MyAgent(Agent)` → `class MyAgent implements Agent`
- Constructor: `__init__` → `constructor`
- Private fields: `self._name` → `private _name` (in constructor)
- Property decorator: `@property` → `get propertyName()`
- Type hints: `-> Message` → `: Promise<Message>`
- String interpolation: `f"..."` → `` `...` `` (template literals)
- Return: `Message(...)` → `{ ... }` (object literal)

---

## Error Handling

### Python
```python
from agenkit import AgentError

try:
    result = await agent.process(message)
    # Use result
except AgentError as e:
    raise RuntimeError(f"process failed: {e}") from e
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    await cleanup()
```

### TypeScript
```typescript
import { AgentError } from '@agenkit/core';

try {
    const result = await agent.process(message);
    // Use result
} catch (error) {
    if (error instanceof AgentError) {
        throw new Error(`process failed: ${error.message}`);
    }
    console.error(`Unexpected error: ${error}`);
} finally {
    await cleanup();
}
```

**Changes**:
- Exception syntax: `except` → `catch`
- Error binding: `as e` → `(error)`
- Error chaining: `raise ... from e` → throw with `cause` property
- Type check: `except AgentError` → `if (error instanceof AgentError)`
- Finally block: Same syntax (works identically!)

---

## Concurrency

### Python (asyncio)
```python
import asyncio

# Launch coroutine as task
async def process_async():
    try:
        result = await agent.process(message)
        # Use result
    except Exception as e:
        print(f"Error: {e}")

task = asyncio.create_task(process_async())

# Wait for multiple
results = await asyncio.gather(
    agent1.process(message),
    agent2.process(message),
    agent3.process(message)
)

# With timeout
try:
    result = await asyncio.wait_for(
        agent.process(message),
        timeout=5.0
    )
except asyncio.TimeoutError:
    print("Timed out")
```

### TypeScript (Promises)
```typescript
// Launch promise
async function processAsync() {
    try {
        const result = await agent.process(message);
        // Use result
    } catch (error) {
        console.error(`Error: ${error}`);
    }
}

// Create detached promise
processAsync();  // Runs independently

// Wait for multiple
const [result1, result2, result3] = await Promise.all([
    agent1.process(message),
    agent2.process(message),
    agent3.process(message)
]);

// With timeout
const result = await Promise.race([
    agent.process(message),
    new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Timeout')), 5000)
    )
]);
```

**Changes**:
- Task creation: `asyncio.create_task()` → Just call async function
- Gather: `asyncio.gather()` → `Promise.all()`
- Timeout: `asyncio.wait_for()` → `Promise.race()` with timeout promise
- Event loop: Implicit in both languages
- Destructuring: `results[0]` → `[result1, ...]` (TypeScript array destructuring)

---

## Patterns

### Sequential

**Python**:
```python
from agenkit.patterns import SequentialAgent

sequential = SequentialAgent(agents=[agent1, agent2])
result = await sequential.process(message)
```

**TypeScript**:
```typescript
import { SequentialAgent } from '@agenkit/patterns';

const sequential = new SequentialAgent({
    agents: [agent1, agent2]
});
const result = await sequential.process(message);
```

### Parallel

**Python**:
```python
from agenkit.patterns import ParallelAgent

parallel = ParallelAgent(agents=[agent_a, agent_b])
result = await parallel.process(message)
```

**TypeScript**:
```typescript
import { ParallelAgent } from '@agenkit/patterns';

const parallel = new ParallelAgent({
    agents: [agentA, agentB]
});
const result = await parallel.process(message);
```

**Changes**:
- Constructor: Named parameters → Object parameter
- Variable naming: `agent_a` → `agentA` (camelCase convention)
- `new` keyword required in TypeScript

---

## Common Gotchas

### 1. None vs undefined/null

**Python**: Single null value
```python
value: str | None = None
if value is None:
    # Handle missing value
    pass
```

**TypeScript**: Two null values
```typescript
let value: string | undefined = undefined;
let other: string | null = null;

if (value === undefined) {
    // Handle missing value
}

// Check both
if (value == null) {  // Checks both undefined and null
    // Handle missing value
}
```

**Best Practice**: Use `undefined` for optional parameters, `null` for explicit absence.

### 2. Duck Typing vs Structural Typing

**Python**: Runtime checking
```python
# No interface needed, just implement methods
class MyAgent:
    @property
    def name(self) -> str:
        return "agent"

    async def process(self, msg: Message) -> Message:
        return msg

# Works at runtime if methods exist
agent: Agent = MyAgent()
```

**TypeScript**: Compile-time checking
```typescript
// Must explicitly implement interface
interface Agent {
    name: string;
    process(msg: Message): Promise<Message>;
}

class MyAgent implements Agent {
    get name(): string {
        return 'agent';
    }

    async process(msg: Message): Promise<Message> {
        return msg;
    }
}

// Type-checked at compile time
const agent: Agent = new MyAgent();
```

**Migration Tip**: TypeScript will catch type mismatches before runtime.

### 3. List/Dict Syntax

**Python**: Built-in literals
```python
# List
items: list[str] = ["a", "b", "c"]
items.append("d")

# Dict
metadata: dict[str, any] = {
    "key": "value",
    "count": 42
}
metadata["new_key"] = "new_value"
```

**TypeScript**: Array/Object/Map
```typescript
// Array
const items: string[] = ['a', 'b', 'c'];
items.push('d');

// Object (like Python dict for string keys)
const metadata: Record<string, any> = {
    key: 'value',
    count: 42
};
metadata.newKey = 'new_value';

// Map (for non-string keys)
const map = new Map<string, number>();
map.set('key', 42);
```

### 4. String Formatting

**Python**: Multiple options
```python
# f-strings (preferred)
message = f"Agent {name} processed {count} messages"

# format method
message = "Agent {} processed {} messages".format(name, count)

# % formatting (old)
message = "Agent %s processed %d messages" % (name, count)
```

**TypeScript**: Template literals
```typescript
// Template literals (only option)
const message = `Agent ${name} processed ${count} messages`;

// Multiline
const long = `
    Agent: ${name}
    Count: ${count}
`;
```

### 5. Import/Export

**Python**: Import statements
```python
# Import module
from agenkit import Agent, Message
from agenkit.patterns import SequentialAgent

# Import specific
from typing import List, Dict, Optional

# Relative imports
from .agent import MyAgent
from ..utils import helper
```

**TypeScript**: ES modules
```typescript
// Import named exports
import { Agent, Message } from '@agenkit/core';
import { SequentialAgent } from '@agenkit/patterns';

// Import types
import type { Agent, Message } from '@agenkit/core';

// Relative imports
import { MyAgent } from './agent';
import { helper } from '../utils';

// Export
export class MyAgent implements Agent { }
export { MyAgent };
```

---

## Type System Differences

### Python Type Hints

```python
from typing import List, Dict, Optional, Union, Any

# Optional (can be None)
name: Optional[str] = None

# Union types
value: Union[str, int] = "text"

# Generic types
items: List[str] = ["a", "b"]
metadata: Dict[str, Any] = {"key": "value"}

# Function signatures
def process(msg: Message) -> Message:
    return msg

async def async_process(msg: Message) -> Message:
    return msg
```

### TypeScript Types

```typescript
// Optional (can be undefined)
let name: string | undefined;
let name?: string;  // Same as above

// Union types
let value: string | number = 'text';

// Generic types
const items: string[] = ['a', 'b'];
const metadata: Record<string, any> = { key: 'value' };

// Function signatures
function process(msg: Message): Message {
    return msg;
}

async function asyncProcess(msg: Message): Promise<Message> {
    return msg;
}

// Arrow functions
const process = (msg: Message): Message => msg;
```

**Key Differences**:
- Python: `Optional[T]` → TypeScript: `T | undefined` or `T?`
- Python: `List[T]` → TypeScript: `T[]` or `Array<T>`
- Python: `Dict[K, V]` → TypeScript: `Record<K, V>` or `Map<K, V>`
- Python: `Union[A, B]` → TypeScript: `A | B`
- Python: `Any` → TypeScript: `any` or `unknown`

---

## Testing

### Python (pytest)
```python
import pytest
from agenkit import Message

@pytest.mark.asyncio
async def test_agent():
    agent = MyAgent()
    msg = Message(role="user", content="Test")

    result = await agent.process(msg)

    assert result.content == "Expected"

@pytest.mark.asyncio
async def test_agent_error():
    agent = MyAgent()

    with pytest.raises(AgentError):
        await agent.process(invalid_msg)
```

### TypeScript (Vitest/Jest)
```typescript
import { describe, it, expect } from 'vitest';
import { Message } from '@agenkit/core';
import { MyAgent } from './agent';

describe('MyAgent', () => {
    it('should process message', async () => {
        const agent = new MyAgent();
        const msg: Message = {
            role: 'user',
            content: 'Test'
        };

        const result = await agent.process(msg);

        expect(result.content).toBe('Expected');
    });

    it('should throw on error', async () => {
        const agent = new MyAgent();

        await expect(agent.process(invalidMsg))
            .rejects
            .toThrow(AgentError);
    });
});
```

**Changes**:
- Test decorator: `@pytest.mark.asyncio` → None needed (native async support)
- Test structure: `async def test_xxx()` → `describe/it` blocks
- Assertions: `assert x == y` → `expect(x).toBe(y)`
- Exception testing: `with pytest.raises()` → `expect().rejects.toThrow()`

---

## Performance Considerations

| Operation | Python | TypeScript | Notes |
|-----------|--------|------------|-------|
| Agent creation | ~1μs | ~500ns | TS 2x faster |
| Message processing | ~10μs | ~5μs | TS 2x faster |
| Sequential (3 agents) | ~30μs | ~15μs | Consistent overhead |
| Parallel (3 agents) | ~20μs | ~5μs | TS better (no GIL) |

**When to use TypeScript**:
- Web applications (browser + Node.js)
- Frontend integration
- Universal deployment (same code everywhere)
- Type safety at compile time
- Better IDE support and refactoring
- NPM ecosystem (2M+ packages)

**When to keep Python**:
- ML/AI integration (PyTorch, TensorFlow, scikit-learn)
- Data science workflows (NumPy, pandas)
- Scientific computing
- Quick scripting and prototyping
- When Python ecosystem is critical

---

## Migration Checklist

- [ ] Convert `class MyAgent(Agent)` to `class MyAgent implements Agent`
- [ ] Replace `__init__` with `constructor`
- [ ] Change `@property` to `get propertyName()`
- [ ] Update imports: `from agenkit` → `from '@agenkit/core'`
- [ ] Convert constructor calls to object literals where appropriate
- [ ] Replace `except` with `catch` in error handling
- [ ] Update type hints: `->` → `:`, `list[T]` → `T[]`
- [ ] Change string formatting: `f"..."` → `` `...` ``
- [ ] Replace `None` with `undefined` or `null`
- [ ] Update naming: `snake_case` → `camelCase`
- [ ] Convert `asyncio.gather()` to `Promise.all()`
- [ ] Update tests: `pytest` → `vitest` or `jest`
- [ ] Add `new` keyword for class instantiation
- [ ] Update project: `pyproject.toml` → `package.json`

---

## Quick Start

```bash
# Python project structure
agenkit/
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── agent.py
│   └── patterns.py
└── tests/
    └── test_agent.py

# TypeScript equivalent
agenkit-ts/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts
│   ├── agent.ts
│   └── patterns.ts
└── tests/
    └── agent.test.ts
```

**Build/Run**:
```bash
# Python
python main.py
# or with uv
uv run python main.py

# TypeScript (development)
npm run dev     # or: yarn dev, pnpm dev
ts-node main.ts

# TypeScript (production)
npm run build   # Compile to JavaScript
node dist/main.js
```

**Package Installation**:
```bash
# Python
pip install agenkit
# or with uv
uv pip install agenkit

# TypeScript
npm install @agenkit/core
# or: yarn add, pnpm add
```

---

## File-by-File Migration Example

### Python: `agent.py`
```python
from agenkit import Agent, Message
from typing import List

class EchoAgent(Agent):
    def __init__(self, prefix: str = "Echo"):
        self._prefix = prefix

    @property
    def name(self) -> str:
        return "echo-agent"

    @property
    def capabilities(self) -> List[str]:
        return ["text"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content=f"{self._prefix}: {message.content}"
        )
```

### TypeScript: `agent.ts`
```typescript
import { Agent, Message } from '@agenkit/core';

export class EchoAgent implements Agent {
    constructor(private prefix: string = 'Echo') {}

    get name(): string {
        return 'echo-agent';
    }

    get capabilities(): string[] {
        return ['text'];
    }

    async process(message: Message): Promise<Message> {
        return {
            role: 'assistant',
            content: `${this.prefix}: ${message.content}`
        };
    }
}
```

---

## Environment Setup

### Python
```bash
# Install Python 3.11+
python --version

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install with uv (recommended)
pip install uv
uv pip install agenkit

# Run
uv run python main.py
```

### TypeScript
```bash
# Install Node.js 18+
node --version
npm --version

# Initialize project
npm init -y
npm install typescript ts-node @types/node --save-dev

# Install Agenkit
npm install @agenkit/core

# Setup TypeScript
npx tsc --init

# Run
npx ts-node main.ts
# or build and run
npx tsc
node dist/main.js
```

---

## Common Migration Patterns

### Pattern 1: Context Managers → Try/Finally

**Python**:
```python
async with timeout_context(5.0):
    result = await agent.process(message)
```

**TypeScript**:
```typescript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 5000);

try {
    const result = await agent.process(message);
} finally {
    clearTimeout(timeoutId);
}
```

### Pattern 2: Decorators → Class Patterns

**Python**:
```python
from functools import wraps

def retry(max_attempts: int = 3):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
        return wrapper
    return decorator

@retry(max_attempts=3)
async def process_message(msg: Message) -> Message:
    return await agent.process(msg)
```

**TypeScript**:
```typescript
// Use higher-order function or wrapper class
function retry<T>(
    fn: () => Promise<T>,
    maxAttempts: number = 3
): Promise<T> {
    return async function attempt(attemptsLeft: number): Promise<T> {
        try {
            return await fn();
        } catch (error) {
            if (attemptsLeft <= 1) throw error;
            return attempt(attemptsLeft - 1);
        }
    }(maxAttempts);
}

// Usage
const result = await retry(
    () => agent.process(msg),
    3
);
```

### Pattern 3: Multiple Inheritance → Composition

**Python**:
```python
class LoggingAgent(Agent, LoggerMixin):
    async def process(self, msg: Message) -> Message:
        self.log(f"Processing: {msg.content}")
        return await super().process(msg)
```

**TypeScript**:
```typescript
// Use composition instead
class LoggingAgent implements Agent {
    constructor(
        private agent: Agent,
        private logger: Logger
    ) {}

    get name(): string {
        return this.agent.name;
    }

    get capabilities(): string[] {
        return this.agent.capabilities;
    }

    async process(msg: Message): Promise<Message> {
        this.logger.log(`Processing: ${msg.content}`);
        return this.agent.process(msg);
    }
}
```

---

## Full Resources

- [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md) - Complete Python idioms guide
- [TypeScript Language Profile](LANGUAGE_PROFILE_TYPESCRIPT.md) - Complete TypeScript idioms guide
- [Main Migration Guide](MIGRATION.md) - Python → All languages
- [Agenkit Examples](../examples/) - Side-by-side code samples
- [TypeScript Handbook](https://www.typescriptlang.org/docs/) - Official TypeScript docs

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
