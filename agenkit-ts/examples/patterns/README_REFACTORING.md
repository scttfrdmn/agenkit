# TypeScript Pattern Examples - Mock Agent Refactoring

## Overview

All TypeScript pattern examples have been refactored to use mock agents instead of requiring API keys. This makes the examples:

- ✅ Runnable without API keys
- ✅ Zero cost to demonstrate patterns
- ✅ Consistent with Python, Rust, and C++ examples
- ✅ Easy to understand pattern mechanics
- ✅ Simple to swap in real LLM adapters for production

## How to Run

```bash
npm run build
node dist/examples/patterns/<pattern-name>.js
```

No environment variables needed!

## Refactoring Status

### ✅ Completed

1. **reflection-pattern.ts** - Uses CodeGeneratorAgent and CodeCriticAgent mocks
2. **react-pattern.ts** - Uses MockReasoningAgent with tools
3. **conversational-pattern.ts** - Uses MockConversationalLLM

### 🔄 In Progress

4. **multiagent-pattern.ts** 
5. **task-pattern.ts**
6. **planning-pattern.ts**
7. **orchestration-pattern.ts**
8. **agents-as-tools-pattern.ts**
9. **autonomous-pattern.ts**
10. **reasoning-with-tools-pattern.ts**
11. **memory-hierarchy-pattern.ts**

## Pattern for Mock Agents

Each mock agent:
- Implements the `Agent` interface
- Provides realistic simulated behavior
- Progressive improvement where applicable
- Demonstrates the pattern clearly

Example:
```typescript
class MockAgent implements Agent {
  name(): string {
    return 'MockAgent';
  }

  capabilities(): string[] {
    return ['capability1', 'capability2'];
  }

  async process(message: Message): Promise<Message> {
    // Simulate realistic behavior
    const response = simulateBehavior(message.content);
    return createMessage({ role: 'assistant', content: response });
  }
}
```

## Production Usage

To use real LLMs, simply replace mock agents:

```typescript
// Development (no API key)
const mockAgent = new MockAgent();

// Production (with API key)
const anthropicAgent = new AnthropicAdapter({
  model: 'claude-3-5-sonnet-20241022',
  temperature: 0.7,
});

// Use the same pattern code
const reflectionAgent = new ReflectionAgent({
  agent: anthropicAgent,  // or mockAgent
  reflector: criticAgent,
  maxIterations: 3,
});
```

## Key Principle

Pattern examples should work with ANY adapter - users can plug in their preferred LLM. This refactoring aligns TypeScript with the cross-language parity goal.

