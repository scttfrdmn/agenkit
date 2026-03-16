# Migrating from Mastra to Agenkit

**Target Audience**: TypeScript developers using Mastra for workflow-based agent systems
**Difficulty**: Beginner to Intermediate
**Time to Read**: 10-12 minutes

---

## Overview

### Why Migrate to Agenkit?

**Language Support**:
- **6 languages**: Python, Go, TypeScript, Rust, C++, Zig (Mastra is TypeScript-only)
- The same agent patterns available in Python for data science workflows
- Deploy performance-critical agents in Go or Rust

**Flexibility**:
- **Any LLM**: OpenAI, Anthropic, Gemini, local Ollama — not just OpenAI-compatible
- **11+ patterns**: ReAct, Sequential, Router, Parallel, Planning, Conversational, and more
- **No Vercel dependency**: No cloud infrastructure lock-in

**Production**:
- **OpenTelemetry**: Standard observability across all languages
- **Circuit breakers, retry, timeout**: Infrastructure-level resilience
- **Memory hierarchy**: Working, episodic, semantic memory

### Key Conceptual Differences

| Mastra | Agenkit | Notes |
|--------|---------|-------|
| **`Step<I, O>`** | **Agent** or function | More flexible |
| **`Workflow`** | **SequentialAgent** or custom pipeline | Simpler |
| **`Workflow.step()`** | **SequentialAgent([...])** | Declarative |
| **`Workflow.then()`** | **Output passed to next agent** | Automatic |
| **`Workflow.branch()`** | **RouterAgent** | Explicit |
| **`Workflow.commit()`** | **No compile step** | Ready immediately |
| **`CompiledWorkflow.execute()`** | **`await agent.process()`** | Async |
| **`MastraAgent`** | **Agent** base class | Same concept |
| **`MastraContext`** | **Message metadata** | Lighter |

### What You Gain

✅ **Multi-language**: Python, Go, TypeScript, Rust, C++, Zig
✅ **No compile step**: Agents run immediately without `workflow.commit()`
✅ **Any LLM**: Not restricted to OpenAI-compatible APIs
✅ **Richer patterns**: 11+ orchestration patterns beyond workflows
✅ **OpenTelemetry**: Standard observability

### What You Lose

❌ **Typed I/O**: Mastra's `Step<I, O>` has compile-time input/output type checking
❌ **Mastra integrations**: No native Mastra tool library
❌ **Built-in observability UI**: Use Jaeger/Grafana with OpenTelemetry instead
❌ **Workflow visualization**: No graph rendering of step dependencies

---

## Pattern Mapping Table

| Mastra | Agenkit Equivalent | Notes |
|--------|-------------------|-------|
| `new Step({ id, execute })` | `Agent` subclass or function | OOP |
| `new Workflow({ name })` | `SequentialAgent([...])` | Declarative |
| `.step(myStep)` | Pass agent to `SequentialAgent` | Same |
| `.then(nextStep)` | Next agent in sequence | Automatic |
| `.branch([{ when, step }])` | `RouterAgent(classifier, agents)` | Explicit |
| `.commit()` | Not needed — ready immediately | Simpler |
| `.execute({ input })` | `await agent.process(message)` | Async |
| `new MastraAgent({ name, model })` | `Agent` with `OpenAILLM` | Same concept |
| `context.getStepResult(id)` | Previous agent response in pipeline | Via Message |
| `new WorkflowResult(output)` | `Message(role="assistant", content=...)` | Standard |

---

## Common Patterns

### Pattern 1: Simple Workflow

**Mastra Code:**
```typescript
import { Step, Workflow } from '@mastra/core';

const validateInput = new Step({
  id: 'validate',
  execute: async ({ context }) => {
    const input = context.triggerData.text as string;
    return { validated: input.trim() };
  },
});

const processText = new Step({
  id: 'process',
  execute: async ({ context }) => {
    const { validated } = context.getStepResult<{ validated: string }>('validate')!;
    return { result: `Processed: ${validated}` };
  },
});

const workflow = new Workflow({ name: 'text-pipeline' })
  .step(validateInput)
  .then(processText)
  .commit();

const result = await workflow.execute({ input: { text: 'Hello World' } });
console.log(result.result);
```

**Agenkit TypeScript Equivalent:**
```typescript
import { createMessage } from 'agenkit';
import { SequentialAgent } from 'agenkit/patterns';

class ValidateStep extends Agent {
  get name() { return 'validate'; }
  get capabilities() { return ['validation']; }

  async process(message: Message): Promise<Message> {
    const validated = message.content.trim();
    return createMessage({ role: 'assistant', content: validated });
  }
}

class ProcessStep extends Agent {
  get name() { return 'process'; }
  get capabilities() { return ['processing']; }

  async process(message: Message): Promise<Message> {
    return createMessage({
      role: 'assistant',
      content: `Processed: ${message.content}`
    });
  }
}

const pipeline = new SequentialAgent([new ValidateStep(), new ProcessStep()]);
const result = await pipeline.process(
  createMessage({ role: 'user', content: 'Hello World' })
);
console.log(result.content);
```

---

### Pattern 2: Conditional Branching

**Mastra Code:**
```typescript
const classify = new Step({
  id: 'classify',
  execute: async ({ context }) => {
    const text = context.triggerData.text as string;
    return { type: text.includes('?') ? 'question' : 'statement' };
  },
});

const answerQuestion = new Step({
  id: 'answer',
  execute: async ({ context }) => {
    return { result: 'Here is the answer...' };
  },
});

const processStatement = new Step({
  id: 'process_statement',
  execute: async ({ context }) => {
    return { result: 'Statement acknowledged.' };
  },
});

const workflow = new Workflow({ name: 'classifier' })
  .step(classify)
  .branch([
    { when: async ({ context }) => context.getStepResult('classify')?.type === 'question',
      step: answerQuestion },
    { when: async ({ context }) => context.getStepResult('classify')?.type === 'statement',
      step: processStatement },
  ])
  .commit();
```

**Agenkit TypeScript Equivalent:**
```typescript
import { RouterAgent, RouterConfig } from 'agenkit/patterns';

const router = new RouterAgent(new RouterConfig(
  (message) => message.content.includes('?') ? 'question' : 'statement',
  {
    'question': answerAgent,
    'statement': statementAgent,
  }
));
const result = await router.process(createMessage({ role: 'user', content: 'What is Agenkit?' }));
```

---

### Pattern 3: MastraAgent

**Mastra Code:**
```typescript
import { MastraAgent } from '@mastra/core';
import { openai } from '@ai-sdk/openai';

const agent = new MastraAgent({
  name: 'assistant',
  model: openai('gpt-4o-mini'),
  instructions: 'You are a helpful assistant.',
});

const response = await agent.generate('Tell me about Agenkit');
console.log(response.text);
```

**Agenkit TypeScript Equivalent:**
```typescript
import { OpenAICompatibleAgent } from 'agenkit/llm/openai-compatible';
import { createMessage } from 'agenkit';

const agent = new OpenAICompatibleAgent({
  baseURL: 'https://api.openai.com/v1',
  model: 'gpt-4o-mini',
  systemPrompt: 'You are a helpful assistant.',
});

const response = await agent.process(
  createMessage({ role: 'user', content: 'Tell me about Agenkit' })
);
console.log(response.content);
```

---

### Pattern 4: Parallel Steps

**Mastra Code:**
```typescript
import { Workflow, Step } from '@mastra/core';

// Mastra supports parallel via Promise.all in execute
const parallelWorkflow = new Workflow({ name: 'parallel' })
  .step(new Step({
    id: 'gather_data',
    execute: async ({ context }) => {
      const [news, wiki, docs] = await Promise.all([
        fetchNews(context.triggerData.topic),
        fetchWiki(context.triggerData.topic),
        fetchDocs(context.triggerData.topic),
      ]);
      return { news, wiki, docs };
    },
  }))
  .commit();
```

**Agenkit TypeScript Equivalent:**
```typescript
import { ParallelAgent } from 'agenkit/patterns';

const parallel = new ParallelAgent([newsAgent, wikiAgent, docsAgent]);
const results = await parallel.process(
  createMessage({ role: 'user', content: topic })
);
// results.content contains merged output from all three
```

---

## Step-by-Step Migration

### Step 1: Replace Step with Agent class

```typescript
// Before
const myStep = new Step({
  id: 'transform',
  execute: async ({ context }) => {
    const input = context.triggerData.text;
    return { output: transform(input) };
  },
});

// After
class TransformAgent extends Agent {
  get name() { return 'transform'; }
  get capabilities() { return ['transformation']; }

  async process(message: Message): Promise<Message> {
    return createMessage({
      role: 'assistant',
      content: transform(message.content),
    });
  }
}
```

### Step 2: Replace Workflow with SequentialAgent

```typescript
// Before
const workflow = new Workflow({ name: 'pipeline' })
  .step(step1)
  .then(step2)
  .then(step3)
  .commit();
const result = await workflow.execute({ input: data });

// After
const pipeline = new SequentialAgent([agent1, agent2, agent3]);
const result = await pipeline.process(createMessage({ role: 'user', content: data }));
```

### Step 3: Replace branch() with RouterAgent

```typescript
// Before
workflow.branch([
  { when: async ({ context }) => classify(context) === 'a', step: stepA },
  { when: async ({ context }) => classify(context) === 'b', step: stepB },
]);

// After
const router = new RouterAgent(new RouterConfig(
  (msg) => classify(msg.content),
  { 'a': agentA, 'b': agentB }
));
```

### Step 4: Remove .commit()

```typescript
// Before
const compiled = workflow.commit();
const result = await compiled.execute({ input: data });

// After
// No commit needed — agents run directly
const result = await agent.process(message);
```

---

## Common Pitfalls

1. **`context.getStepResult(id)`**: In Agenkit, each agent receives the previous agent's output as its input `Message` — no explicit result lookup
2. **Typed `Step<I, O>`**: Agenkit TypeScript agents use `Message` as universal I/O — add Zod parsing inside `process()` for type safety
3. **`.commit()` requirement**: Agenkit agents are ready immediately — no compile step
4. **`triggerData` vs `content`**: Mastra passes `context.triggerData` as the workflow input; Agenkit passes `message.content`

---

## FAQ

**Q: Does Agenkit support type-safe step I/O like Mastra's `Step<I, O>`?**
A: Use Zod schemas inside the agent's `process()` method to parse and validate `message.content`.

**Q: Can I visualize Agenkit workflows like Mastra's step graph?**
A: No built-in visualization, but OpenTelemetry traces show the execution path in Jaeger/Grafana.

**Q: Is there a Mastra-compatible CLI for Agenkit?**
A: Not currently. Run agents via `ts-node` or compile with `tsc`.

---

## Reference

- TypeScript example: `agenkit-ts/examples/frameworks/minimastra.ts`
- Agenkit TypeScript source: `agenkit-ts/src/`
- Framework comparison: `docs/FRAMEWORK_COMPARISON.md`
