# Getting Started with Agenkit - TypeScript

**Complete guide to building type-safe AI agents with Agenkit in TypeScript**

## Table of Contents

1. [Installation](#installation)
2. [Your First Agent](#your-first-agent)
3. [Core Concepts](#core-concepts)
4. [Using Patterns](#using-patterns)
5. [Adding Middleware](#adding-middleware)
6. [Working with LLMs](#working-with-llms)
7. [Browser Support](#browser-support)
8. [Testing Your Agents](#testing-your-agents)
9. [Next Steps](#next-steps)

---

## Installation

### Prerequisites

- Node.js 18+ or Bun
- npm, yarn, or pnpm package manager
- TypeScript 5.0+

### Install with npm

```bash
npm install agenkit
npm install --save-dev typescript @types/node
```

### Install with yarn

```bash
yarn add agenkit
yarn add --dev typescript @types/node
```

### Install with pnpm

```bash
pnpm add agenkit
pnpm add -D typescript @types/node
```

### Verify Installation

Create `test.ts`:
```typescript
import { Agent, Message } from 'agenkit';

console.log('Agenkit loaded successfully!');
```

```bash
npx ts-node test.ts
# Output: Agenkit loaded successfully!
```

---

## Your First Agent

Let's create a simple agent that processes messages:

### Step 1: Create Your Agent

Create a file `agent.ts`:

```typescript
import { Agent, Message } from 'agenkit';

/**
 * A simple agent that greets users
 */
export class GreetingAgent implements Agent {
    get name(): string {
        return 'greeting-agent';
    }

    async process(message: Message): Promise<Message> {
        const userMessage = String(message.content);

        return {
            role: 'assistant',
            content: `Hello! You said: '${userMessage}'. How can I help you today?`,
        };
    }
}
```

### Step 2: Use Your Agent

Create `index.ts`:

```typescript
import { Message } from 'agenkit';
import { GreetingAgent } from './agent';

async function main() {
    // Create agent instance
    const agent = new GreetingAgent();

    // Create a user message
    const userMsg: Message = {
        role: 'user',
        content: 'Hi there!',
    };

    // Process the message
    const response = await agent.process(userMsg);

    // Print the response
    console.log(`${agent.name}: ${response.content}`);
}

main().catch(console.error);
```

### Step 3: Run It

```bash
npx ts-node index.ts
# Output: greeting-agent: Hello! You said: 'Hi there!'. How can I help you today?
```

**🎉 Congratulations!** You've created your first Agenkit agent in TypeScript.

---

## Core Concepts

### The Agent Interface

Every agent in Agenkit implements the `Agent` interface:

```typescript
interface Agent {
    readonly name: string;
    process(message: Message): Promise<Message>;
}
```

**That's the entire interface.** Everything else is optional.

**Important:** Use `get name()` getter syntax, not a method:

```typescript
// ✅ CORRECT
class MyAgent implements Agent {
    get name(): string {
        return 'my-agent';
    }
}

// ❌ WRONG
class MyAgent implements Agent {
    name(): string {  // This is a method, not a getter!
        return 'my-agent';
    }
}
```

### Messages

Messages are the unit of communication:

```typescript
import { Message, createMessage } from 'agenkit';

// Create a message
const msg: Message = {
    role: 'user',           // Who sent it: "user", "assistant", "system"
    content: 'Hello!',      // The message content (string or object)
    metadata: {             // Optional metadata
        source: 'web',
    },
};

// Or use the helper
const msg2 = createMessage('user', 'Hello!', { source: 'web' });

// Access message properties (with type safety)
console.log(msg.role);      // "user"
console.log(msg.content);   // "Hello!"
console.log(msg.metadata);  // { source: "web" }
```

### Type Safety

TypeScript provides compile-time type checking:

```typescript
import { Agent, Message } from 'agenkit';

class TypeSafeAgent implements Agent {
    get name(): string {
        return 'type-safe-agent';
    }

    async process(message: Message): Promise<Message> {
        // TypeScript knows message is a Message type
        const content = message.content;  // Type: unknown

        // Type guard for safety
        if (typeof content !== 'string') {
            throw new Error('Expected string content');
        }

        // Now TypeScript knows content is a string
        const upperContent = content.toUpperCase();

        return {
            role: 'assistant',
            content: upperContent,
        };
    }
}
```

### Tools

Tools let agents take actions:

```typescript
import { Tool, ToolResult } from 'agenkit';

export class CalculatorTool implements Tool {
    get name(): string {
        return 'calculator';
    }

    get description(): string {
        return 'Performs basic arithmetic operations';
    }

    async execute(params: Record<string, unknown>): Promise<ToolResult> {
        const operation = params.operation as string;
        const a = params.a as number;
        const b = params.b as number;

        let result: number;
        switch (operation) {
            case 'add':
                result = a + b;
                break;
            case 'multiply':
                result = a * b;
                break;
            default:
                return {
                    output: null,
                    error: `Unknown operation: ${operation}`,
                };
        }

        return { output: result };
    }
}
```

---

## Using Patterns

Agenkit includes 18 pre-built patterns for common agent architectures.

### Reflection Pattern

Iteratively improve outputs through self-critique:

```typescript
import { ReflectionAgent, ReflectionConfig } from 'agenkit';
import { Generator, Critic } from './my-agents';  // Your custom agents

// Configure reflection
const config: ReflectionConfig = {
    maxIterations: 3,        // Maximum improvement cycles
    qualityThreshold: 0.8,   // Stop when quality is good enough
    stopOnRepeat: true,      // Stop if output doesn't change
};

// Create reflection agent
const agent = new ReflectionAgent({
    generator: new Generator(),    // Generates initial output
    critic: new Critic(),         // Critiques and suggests improvements
    ...config,
});

// Use it
const response = await agent.process({
    role: 'user',
    content: 'Write a haiku about coding',
});

// Response includes iteration metadata
console.log(response.metadata?.iterations);          // Number of cycles
console.log(response.metadata?.final_quality_score); // Quality of output
```

### Sequential Pattern

Chain multiple agents in sequence:

```typescript
import { SequentialPattern } from 'agenkit';
import { ResearchAgent, SummaryAgent, FormatterAgent } from './agents';

// Create a pipeline: research → summarize → format
const pipeline = new SequentialPattern([
    new ResearchAgent(),      // Gathers information
    new SummaryAgent(),       // Summarizes findings
    new FormatterAgent(),     // Formats final output
]);

// Input flows through each agent in order
const response = await pipeline.process({
    role: 'user',
    content: 'Research quantum computing',
});
```

### Parallel Pattern

Run multiple agents concurrently and aggregate results:

```typescript
import { ParallelPattern } from 'agenkit';
import { TechnicalAgent, BusinessAgent, UserAgent } from './agents';

// Run multiple specialized agents in parallel
const parallel = new ParallelPattern([
    new TechnicalAgent(),     // Technical perspective
    new BusinessAgent(),      // Business perspective
    new UserAgent(),         // User perspective
]);

// All agents process simultaneously (Promise.all)
const response = await parallel.process({
    role: 'user',
    content: 'Analyze this product idea',
});
```

### ReAct Pattern

Reasoning + Acting with tool use:

```typescript
import { ReActAgent, ReActConfig } from 'agenkit';
import { ReasoningAgent } from './agents';
import { SearchTool, CalculatorTool } from './tools';

// Configure ReAct
const config: ReActConfig = {
    maxSteps: 5,              // Maximum reasoning steps
    tools: [
        new SearchTool(),     // Web search capability
        new CalculatorTool(), // Math calculations
    ],
};

// Create ReAct agent
const agent = new ReActAgent(new ReasoningAgent(), config);

// Agent will alternate between thinking and acting
const response = await agent.process({
    role: 'user',
    content: "What's the population of Tokyo divided by the population of NYC?",
});

// Response includes reasoning trace
console.log(response.metadata?.steps);       // Reasoning steps
console.log(response.metadata?.tool_calls);  // Tools used
```

---

## Adding Middleware

Middleware adds production features without changing your agent code.

### Retry Logic

Automatically retry failed operations:

```typescript
import { RetryMiddleware, RetryConfig } from 'agenkit';

// Configure retries
const config: RetryConfig = {
    maxAttempts: 3,              // Try up to 3 times
    backoffFactor: 2.0,          // Exponential backoff
    initialDelay: 1000,          // Start with 1 second
    maxDelay: 30000,             // Cap at 30 seconds
};

// Wrap your agent
const resilientAgent = new RetryMiddleware(myAgent, config);

// Now handles transient failures automatically
const response = await resilientAgent.process(message);
```

### Circuit Breaker

Prevent cascading failures:

```typescript
import { CircuitBreakerMiddleware, CircuitBreakerConfig } from 'agenkit';

// Configure circuit breaker
const config: CircuitBreakerConfig = {
    failureThreshold: 5,          // Open after 5 failures
    timeout: 60000,              // Stay open for 60 seconds
    successThreshold: 2,         // Close after 2 successes
};

// Wrap your agent
const protectedAgent = new CircuitBreakerMiddleware(myAgent, config);

// Fails fast when circuit is open
try {
    const response = await protectedAgent.process(message);
} catch (error) {
    if (error.name === 'CircuitBreakerError') {
        console.log('Circuit is open - service unavailable');
    }
}
```

### Timeout

Set maximum execution time:

```typescript
import { TimeoutMiddleware, TimeoutConfig } from 'agenkit';

// Configure timeout
const config: TimeoutConfig = {
    timeout: 30000,              // 30 second timeout
    gracePeriod: 5000,          // 5 second grace for cleanup
};

// Wrap your agent
const timedAgent = new TimeoutMiddleware(myAgent, config);

// Will cancel after 30 seconds
try {
    const response = await timedAgent.process(message);
} catch (error) {
    if (error.name === 'TimeoutError') {
        console.log('Agent took too long to respond');
    }
}
```

### Stacking Middleware

Combine multiple middleware layers:

```typescript
import {
    RetryMiddleware,
    CircuitBreakerMiddleware,
    TimeoutMiddleware,
    RateLimiterMiddleware,
    Agent,
} from 'agenkit';

// Stack middleware (innermost to outermost)
let agent: Agent = myAgent;
agent = new TimeoutMiddleware(agent, timeoutConfig);
agent = new CircuitBreakerMiddleware(agent, circuitConfig);
agent = new RetryMiddleware(agent, retryConfig);
agent = new RateLimiterMiddleware(agent, rateConfig);

// Now has full production resilience
const response = await agent.process(message);
```

---

## Working with LLMs

### OpenAI Integration

```typescript
import { OpenAIAgent, OpenAIConfig } from 'agenkit';

// Create OpenAI agent
const config: OpenAIConfig = {
    model: 'gpt-4',
    apiKey: process.env.OPENAI_API_KEY!,
};

const agent = new OpenAIAgent(config);

// Use it like any agent
const response = await agent.process({
    role: 'user',
    content: 'Explain quantum computing',
});
```

### Anthropic (Claude) Integration

```typescript
import { AnthropicAgent, AnthropicConfig } from 'agenkit';

// Create Claude agent
const config: AnthropicConfig = {
    model: 'claude-3-opus-20240229',
    apiKey: process.env.ANTHROPIC_API_KEY!,
};

const agent = new AnthropicAgent(config);

const response = await agent.process({
    role: 'user',
    content: 'Write a function to calculate Fibonacci numbers',
});
```

### Custom LLM Integration

```typescript
import { Agent, Message } from 'agenkit';

export class CustomLLMAgent implements Agent {
    private apiUrl: string;
    private apiKey: string;

    constructor(apiUrl: string, apiKey: string) {
        this.apiUrl = apiUrl;
        this.apiKey = apiKey;
    }

    get name(): string {
        return 'custom-llm';
    }

    async process(message: Message): Promise<Message> {
        // Call your LLM API
        const response = await fetch(this.apiUrl, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: message.content,
            }),
        });

        const result = await response.json();

        return {
            role: 'assistant',
            content: result.completion,
        };
    }
}
```

---

## Browser Support

Agenkit works in browsers! Perfect for client-side AI applications.

### Browser Setup

```html
<!DOCTYPE html>
<html>
<head>
    <title>Agenkit in Browser</title>
</head>
<body>
    <script type="module">
        import { Agent, Message } from 'https://esm.sh/agenkit';

        class BrowserAgent {
            get name() {
                return 'browser-agent';
            }

            async process(message) {
                return {
                    role: 'assistant',
                    content: `Browser processed: ${message.content}`,
                };
            }
        }

        // Use the agent
        const agent = new BrowserAgent();
        const response = await agent.process({
            role: 'user',
            content: 'Hello from browser!',
        });

        console.log(response.content);
    </script>
</body>
</html>
```

### Browser-Safe LLM Calls

**⚠️ Security Warning:** Never expose API keys in browser code!

Use a backend proxy:

```typescript
// frontend/agent.ts
export class ProxiedLLMAgent implements Agent {
    private backendUrl: string;

    constructor(backendUrl: string) {
        this.backendUrl = backendUrl;
    }

    get name(): string {
        return 'proxied-llm';
    }

    async process(message: Message): Promise<Message> {
        // Call your backend (which has the API key)
        const response = await fetch(`${this.backendUrl}/api/agent`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
            credentials: 'include',  // Include cookies for auth
        });

        if (!response.ok) {
            throw new Error('Backend request failed');
        }

        return await response.json();
    }
}
```

```typescript
// backend/server.ts (Node.js)
import express from 'express';
import { OpenAIAgent } from 'agenkit';

const app = express();
app.use(express.json());

const llmAgent = new OpenAIAgent({
    model: 'gpt-4',
    apiKey: process.env.OPENAI_API_KEY!,  // Safe on server
});

app.post('/api/agent', async (req, res) => {
    try {
        const { message } = req.body;
        const response = await llmAgent.process(message);
        res.json(response);
    } catch (error) {
        res.status(500).json({ error: 'Processing failed' });
    }
});

app.listen(3000);
```

---

## Testing Your Agents

### Unit Testing with Vitest

```typescript
import { describe, it, expect } from 'vitest';
import { Message } from 'agenkit';
import { GreetingAgent } from './agent';

describe('GreetingAgent', () => {
    it('should respond with a greeting', async () => {
        const agent = new GreetingAgent();

        const response = await agent.process({
            role: 'user',
            content: 'Hello',
        });

        expect(response.role).toBe('assistant');
        expect(response.content).toContain('Hello');
    });

    it('should have correct name', () => {
        const agent = new GreetingAgent();
        expect(agent.name).toBe('greeting-agent');
    });
});
```

### Integration Testing with Jest

```typescript
import { SequentialPattern, Agent, Message } from 'agenkit';

class MockAgent implements Agent {
    constructor(private response: string) {}

    get name(): string {
        return 'mock-agent';
    }

    async process(message: Message): Promise<Message> {
        return {
            role: 'assistant',
            content: this.response,
        };
    }
}

describe('SequentialPattern', () => {
    it('should process through all agents', async () => {
        const pipeline = new SequentialPattern([
            new MockAgent('Step 1 complete'),
            new MockAgent('Step 2 complete'),
            new MockAgent('Step 3 complete'),
        ]);

        const response = await pipeline.process({
            role: 'user',
            content: 'Start pipeline',
        });

        expect(response.content).toContain('Step 3 complete');
    });
});
```

### Type Testing

```typescript
import { Agent, Message } from 'agenkit';
import { expectType, expectError } from 'tsd';

// Verify interface compliance
class TestAgent implements Agent {
    get name(): string {
        return 'test';
    }

    async process(message: Message): Promise<Message> {
        return message;
    }
}

// Type checks
expectType<Agent>(new TestAgent());
expectError<Agent>({ name: 'wrong' });  // Missing process method
```

---

## Next Steps

### Learn More

- **[Pattern Guide](../patterns/README.md)** - Detailed guide to all 18 patterns
- **[API Reference](../api/typescript/README.md)** - Complete API documentation
- **[Best Practices](../best-practices/TYPESCRIPT.md)** - Production deployment tips
- **[Examples](../../agenkit-ts/examples/)** - Working examples

### Full-Stack Development

- **[Next.js Integration](../frameworks/NEXTJS.md)** - Build AI-powered web apps
- **[Express.js Integration](../frameworks/EXPRESS.md)** - Backend API servers
- **[React Integration](../frameworks/REACT.md)** - Client-side AI agents

### Deploy to Production

- **[Docker Deployment](../deployment/DOCKER.md)** - Containerize your agents
- **[Vercel/Netlify](../deployment/SERVERLESS.md)** - Serverless deployment
- **[Monitoring & Observability](../observability/README.md)** - Track agent performance

### Migrate from Other Languages

Coming from Python or another language?

- **[Python → TypeScript Migration](../migration/PYTHON_TO_TYPESCRIPT.md)** - Migrate from Python
- **[Go → TypeScript Migration](../migration/GO_TO_TYPESCRIPT.md)** - Migrate from Go

---

## Quick Reference

### Installation
```bash
npm install agenkit
```

### Minimal Agent
```typescript
import { Agent, Message } from 'agenkit';

class MyAgent implements Agent {
    get name(): string {
        return 'my-agent';
    }

    async process(message: Message): Promise<Message> {
        return {
            role: 'assistant',
            content: 'Response',
        };
    }
}
```

### Common Imports
```typescript
// Core
import { Agent, Message, Tool, ToolResult, createMessage } from 'agenkit';

// Patterns
import {
    ReflectionAgent, ReActAgent, SequentialPattern,
    ParallelPattern, ConversationalAgent
} from 'agenkit';

// Middleware
import {
    RetryMiddleware, CircuitBreakerMiddleware,
    TimeoutMiddleware, RateLimiterMiddleware
} from 'agenkit';

// Adapters
import { OpenAIAgent, AnthropicAgent } from 'agenkit';
```

---

**Ready to build?** Check out the [examples](../../agenkit-ts/examples/) for working code you can run right now.

**Browser tip:** Agenkit works in all modern browsers - build client-side AI experiences!
