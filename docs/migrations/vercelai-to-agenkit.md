# Migrating from Vercel AI SDK to Agenkit

**Target Audience**: TypeScript/Next.js developers using the Vercel AI SDK (`ai` package)
**Difficulty**: Beginner to Intermediate
**Time to Read**: 10-12 minutes

---

## Overview

### Why Migrate to Agenkit?

**Language Support**:
- **6 languages**: Python, Go, TypeScript, Rust, C++, Zig (Vercel AI SDK is TypeScript-only)
- Run the same agent logic in Python for data science / ML pipelines
- Deploy performance-critical agents in Go or Rust

**Infrastructure Independence**:
- **No Vercel lock-in**: Deploy anywhere — bare metal, AWS, GCP, self-hosted
- **Any LLM**: OpenAI, Anthropic, Gemini, local Ollama, vLLM, SGLang — not just Vercel-supported providers
- **No Next.js required**: Works in any Node.js, Deno, or Bun environment

**Production Features**:
- **OpenTelemetry**: Standard observability (traces, metrics, logs) across all languages
- **Circuit breakers, retry, timeout**: Infrastructure-level resilience built in
- **Memory hierarchy**: Working, episodic, semantic memory
- **11+ agent patterns**: ReAct, Sequential, Router, Parallel, Planning, Conversational, and more

### Key Conceptual Differences

| Vercel AI SDK | Agenkit | Notes |
|--------------|---------|-------|
| **`streamText()`** | **`agent.processStream()`** | Async generator |
| **`generateText()`** | **`agent.process()`** | Single call |
| **`tool()`** | **`Tool` interface** | Same concept |
| **`generateObject()`** | **structured-output prompt + `JSON.parse`** | Explicit |
| **`TextStreamPart`** | **`Message` chunk** | Simpler union |
| **`useChat()` hook** | **AG-UI streaming protocol** | Framework-agnostic |
| **`CoreMessage[]`** | **`Message[]`** | Compatible shape |
| **Zod schema validation** | **TypeScript interfaces + runtime guards** | No Zod dep |

### What You Gain

✅ **Multi-language**: Python, Go, TypeScript, Rust, C++, Zig
✅ **Infrastructure freedom**: Deploy anywhere, no Vercel required
✅ **Any LLM provider**: Not restricted to Vercel's provider list
✅ **Richer patterns**: 11+ orchestration patterns beyond simple streaming
✅ **OpenTelemetry**: Standard observability, compatible with any backend
✅ **Long-running agents**: Memory, checkpointing, session recovery

### What You Lose

❌ **`useChat()` / `useCompletion()` React hooks**: Must use AG-UI protocol or write your own hook
❌ **Vercel Edge Runtime integration**: Not optimised for Edge Functions
❌ **Zod-native schema validation**: Use `zod` independently if needed
❌ **`@ai-sdk/provider` ecosystem**: Third-party Vercel provider packages don't apply

---

## Pattern Mapping Table

| Vercel AI SDK | Agenkit TypeScript | Notes |
|--------------|-------------------|-------|
| `streamText({ model, prompt })` | `agent.processStream(message)` | Async generator |
| `generateText({ model, prompt })` | `await agent.process(message)` | Returns `Message` |
| `tool({ description, parameters, execute })` | `{ name, description, execute }` `Tool` | Same shape |
| `generateObject({ model, schema, prompt })` | Structured prompt + `JSON.parse(response.content)` | Explicit |
| `TextStreamPart` union | `Message` with chunk content | Simpler |
| `createOpenAI(config)` | `new OpenAICompatibleAgent(config)` | Direct |
| `createAnthropic(config)` | `new AnthropicAgent(config)` (Python/TS) | Direct |
| `openai('gpt-4o')` | `new OpenAICompatibleAgent({ model: 'gpt-4o' })` | Direct |
| `experimental_streamData` | `Message.metadata` | Standard field |
| `formatStreamPart()` | Not needed — `Message` is already structured | Simpler |

---

## Common Patterns

### Pattern 1: Basic Text Generation

**Vercel AI SDK:**
```typescript
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';

const { text } = await generateText({
  model: openai('gpt-4o'),
  prompt: 'Explain what Agenkit is in one sentence.',
});
console.log(text);
```

**Agenkit TypeScript Equivalent:**
```typescript
import { createMessage } from 'agenkit';
import { OpenAICompatibleAgent } from 'agenkit/llm';

const agent = new OpenAICompatibleAgent({
  baseURL: 'https://api.openai.com/v1',
  model: 'gpt-4o',
  apiKey: process.env.OPENAI_API_KEY!,
});

const response = await agent.process(
  createMessage('user', 'Explain what Agenkit is in one sentence.')
);
console.log(response.content);
```

**Key Differences:**
- No named `text` field — use `response.content`
- The agent object is reusable; no `openai()` factory per call
- Works identically with Anthropic, Ollama, or any other provider

---

### Pattern 2: Token Streaming

**Vercel AI SDK:**
```typescript
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';

const { textStream } = await streamText({
  model: openai('gpt-4o'),
  prompt: 'Write a haiku about TypeScript.',
});

for await (const chunk of textStream) {
  process.stdout.write(chunk);
}
```

**Agenkit TypeScript Equivalent:**
```typescript
import { createMessage } from 'agenkit';
import { OpenAICompatibleAgent } from 'agenkit/llm';

const agent = new OpenAICompatibleAgent({
  baseURL: 'https://api.openai.com/v1',
  model: 'gpt-4o',
  apiKey: process.env.OPENAI_API_KEY!,
});

for await (const chunk of agent.processStream(
  createMessage('user', 'Write a haiku about TypeScript.')
)) {
  process.stdout.write(chunk.content as string);
}
```

**Key Differences:**
- `agent.processStream()` returns an `AsyncGenerator<Message>` directly
- No destructuring needed — iterate directly
- Each chunk is a full `Message` object; content is the token delta

---

### Pattern 3: Tools / Function Calling

**Vercel AI SDK:**
```typescript
import { streamText, tool } from 'ai';
import { openai } from '@ai-sdk/openai';
import { z } from 'zod';

const result = await streamText({
  model: openai('gpt-4o'),
  prompt: 'What is the weather in Tokyo?',
  tools: {
    weather: tool({
      description: 'Get the current weather for a location',
      parameters: z.object({ location: z.string() }),
      execute: async ({ location }) => `22°C, partly cloudy in ${location}`,
    }),
  },
});

for await (const part of result.fullStream) {
  if (part.type === 'tool-call') {
    console.log(`Tool: ${part.toolName}(${JSON.stringify(part.args)})`);
  } else if (part.type === 'tool-result') {
    console.log(`Result: ${part.result}`);
  } else if (part.type === 'text-delta') {
    process.stdout.write(part.textDelta);
  }
}
```

**Agenkit TypeScript Equivalent:**
```typescript
import { createMessage, ReActAgent } from 'agenkit';
import { OpenAICompatibleAgent } from 'agenkit/llm';

const llm = new OpenAICompatibleAgent({
  baseURL: 'https://api.openai.com/v1',
  model: 'gpt-4o',
  apiKey: process.env.OPENAI_API_KEY!,
});

const weatherTool = {
  name: 'weather',
  description: 'Get the current weather for a location',
  parameters: { location: 'string — city name' },
  async execute({ location }: { location: string }): Promise<string> {
    return `22°C, partly cloudy in ${location}`;
  },
};

const agent = new ReActAgent({ llm, tools: [weatherTool] });
const response = await agent.process(
  createMessage('user', 'What is the weather in Tokyo?')
);
console.log(response.content);
```

**Key Differences:**
- `ReActAgent` handles the tool-call loop automatically (reason → act → observe)
- No Zod dependency — describe parameters as plain objects or TypeScript interfaces
- `response.content` is the final text after all tool calls complete
- To observe individual tool calls, use `agent.processStream()` and check `message.metadata.toolCall`

---

### Pattern 4: Structured Object Generation

**Vercel AI SDK:**
```typescript
import { generateObject } from 'ai';
import { openai } from '@ai-sdk/openai';
import { z } from 'zod';

const { object } = await generateObject({
  model: openai('gpt-4o'),
  prompt: 'Describe the Agenkit framework.',
  schema: z.object({
    name: z.string(),
    language: z.string(),
    primaryUseCase: z.string(),
    yearReleased: z.number(),
  }),
});

console.log(object.name, object.language);
```

**Agenkit TypeScript Equivalent:**
```typescript
import { createMessage } from 'agenkit';
import { OpenAICompatibleAgent } from 'agenkit/llm';

interface FrameworkInfo {
  name: string;
  language: string;
  primaryUseCase: string;
  yearReleased: number;
}

const agent = new OpenAICompatibleAgent({
  baseURL: 'https://api.openai.com/v1',
  model: 'gpt-4o',
  apiKey: process.env.OPENAI_API_KEY!,
});

const structuredPrompt =
  'Describe the Agenkit framework.\n\n' +
  'Respond with ONLY a JSON object with this shape:\n' +
  '{ "name": string, "language": string, "primaryUseCase": string, "yearReleased": number }';

const response = await agent.process(createMessage('user', structuredPrompt));
const object = JSON.parse(response.content as string) as FrameworkInfo;
console.log(object.name, object.language);
```

**Key Differences:**
- No Zod schema — write a JSON shape description in the prompt
- Parse with `JSON.parse` and cast to your TypeScript interface
- For runtime validation, add a type guard or use `zod.parse()` on the result independently

---

### Pattern 5: Multi-Turn Conversation

**Vercel AI SDK:**
```typescript
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';

const messages: CoreMessage[] = [
  { role: 'system', content: 'You are a helpful coding assistant.' },
  { role: 'user', content: 'How do I reverse a string in TypeScript?' },
];

const { text } = await generateText({ model: openai('gpt-4o'), messages });
messages.push({ role: 'assistant', content: text });
messages.push({ role: 'user', content: 'Show me the same in Python.' });

const { text: text2 } = await generateText({ model: openai('gpt-4o'), messages });
console.log(text2);
```

**Agenkit TypeScript Equivalent:**
```typescript
import { createMessage, ConversationalAgent } from 'agenkit';
import { OpenAICompatibleAgent } from 'agenkit/llm';

const llm = new OpenAICompatibleAgent({
  baseURL: 'https://api.openai.com/v1',
  model: 'gpt-4o',
  apiKey: process.env.OPENAI_API_KEY!,
});

const agent = new ConversationalAgent({
  llm,
  systemPrompt: 'You are a helpful coding assistant.',
});

const r1 = await agent.process(
  createMessage('user', 'How do I reverse a string in TypeScript?')
);
console.log(r1.content);

const r2 = await agent.process(
  createMessage('user', 'Show me the same in Python.')
);
console.log(r2.content);
```

**Key Differences:**
- `ConversationalAgent` maintains message history automatically
- No manual `messages.push()` — history is managed by the agent
- `systemPrompt` is set once at construction, not per-call

---

### Pattern 6: Streaming with `useChat()` React Hook

**Vercel AI SDK:**
```tsx
import { useChat } from 'ai/react';

export default function Chat() {
  const { messages, input, handleInputChange, handleSubmit } = useChat({
    api: '/api/chat',
  });

  return (
    <div>
      {messages.map(m => (
        <div key={m.id}>{m.role}: {m.content}</div>
      ))}
      <form onSubmit={handleSubmit}>
        <input value={input} onChange={handleInputChange} />
      </form>
    </div>
  );
}
```

**Agenkit Equivalent (AG-UI protocol):**

Agenkit uses the **AG-UI streaming protocol** for UI integration, which is framework-agnostic.
Instead of a React hook, create an API route that returns an AG-UI stream:

```typescript
// pages/api/chat.ts (Next.js) or any HTTP handler
import { createMessage, ConversationalAgent } from 'agenkit';
import { OpenAICompatibleAgent } from 'agenkit/llm';
import { AGUIProtocol } from 'agenkit/agui';

const llm = new OpenAICompatibleAgent({
  baseURL: 'https://api.openai.com/v1',
  model: 'gpt-4o',
  apiKey: process.env.OPENAI_API_KEY!,
});

export async function POST(req: Request) {
  const { messages } = await req.json() as { messages: Array<{ role: string; content: string }> };
  const latest = messages[messages.length - 1];

  const agent = new ConversationalAgent({ llm });
  const stream = agent.processStream(createMessage(latest.role, latest.content));

  return AGUIProtocol.streamResponse(stream);
}
```

Client-side (framework-agnostic):
```typescript
const res = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ messages }),
});
// Read Server-Sent Events from the AG-UI stream
for await (const event of AGUIProtocol.parseStream(res.body!)) {
  if (event.type === 'text-delta') process.stdout.write(event.content);
}
```

---

## TextStreamPart vs Message

The Vercel AI SDK uses a `TextStreamPart` discriminated union:

```typescript
// Vercel AI SDK TextStreamPart
type TextStreamPart =
  | { type: 'text-delta'; textDelta: string }
  | { type: 'tool-call'; toolName: string; args: unknown }
  | { type: 'tool-result'; toolName: string; result: unknown }
  | { type: 'finish'; finishReason: string; usage: Usage };
```

Agenkit uses a unified `Message` type with a `metadata` bag for tool info:

```typescript
// Agenkit Message (simplified)
interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string | unknown;         // token delta or full text
  metadata?: Record<string, unknown>; // toolCall, toolResult, finishReason, usage
}
```

**Mapping:**

| `TextStreamPart` field | `Message` field |
|------------------------|----------------|
| `type: 'text-delta'` | `role: 'assistant'`, `content: delta` |
| `type: 'tool-call'` | `role: 'assistant'`, `metadata.toolCall: { name, args }` |
| `type: 'tool-result'` | `role: 'tool'`, `content: result` |
| `type: 'finish'` | `metadata.finishReason`, `metadata.usage` |

---

## Provider Migration

### OpenAI

**Vercel AI SDK:**
```typescript
import { openai } from '@ai-sdk/openai';
const model = openai('gpt-4o');
```

**Agenkit:**
```typescript
import { OpenAICompatibleAgent } from 'agenkit/llm';
const agent = new OpenAICompatibleAgent({
  baseURL: 'https://api.openai.com/v1',
  model: 'gpt-4o',
  apiKey: process.env.OPENAI_API_KEY!,
});
```

### Anthropic

**Vercel AI SDK:**
```typescript
import { anthropic } from '@ai-sdk/anthropic';
const model = anthropic('claude-opus-4-5');
```

**Agenkit:**
```typescript
// TypeScript (via OpenAI-compat endpoint) or use Python/Go for native Anthropic support
import { OpenAICompatibleAgent } from 'agenkit/llm';
const agent = new OpenAICompatibleAgent({
  baseURL: 'https://api.anthropic.com/v1',
  model: 'claude-opus-4-5',
  apiKey: process.env.ANTHROPIC_API_KEY!,
});
```

### Local (Ollama)

**Vercel AI SDK:**
```typescript
import { ollama } from 'ollama-ai-provider';
const model = ollama('llama3.2');
```

**Agenkit:**
```typescript
import { OpenAICompatibleAgent } from 'agenkit/llm';
const agent = new OpenAICompatibleAgent({
  baseURL: 'http://localhost:11434/v1',
  model: 'llama3.2',
  apiKey: 'ollama',
});
```

---

## Step-by-Step Migration Checklist

### Step 1: Install Agenkit

```bash
npm install agenkit
# Remove Vercel AI SDK and provider packages
npm uninstall ai @ai-sdk/openai @ai-sdk/anthropic
```

### Step 2: Replace Provider Factories

Find all `openai(...)`, `anthropic(...)`, `createOpenAI(...)` calls and replace with
the appropriate Agenkit agent constructor (see Provider Migration above).

### Step 3: Replace `generateText()` Calls

```typescript
// Before
const { text } = await generateText({ model, prompt });

// After
const response = await agent.process(createMessage('user', prompt));
const text = response.content as string;
```

### Step 4: Replace `streamText()` Calls

```typescript
// Before
const { textStream } = await streamText({ model, prompt });
for await (const chunk of textStream) { ... }

// After
for await (const chunk of agent.processStream(createMessage('user', prompt))) {
  const delta = chunk.content as string;
  ...
}
```

### Step 5: Replace `tool()` Definitions

```typescript
// Before (Vercel + Zod)
const myTool = tool({
  description: '...',
  parameters: z.object({ input: z.string() }),
  execute: async ({ input }) => `result: ${input}`,
});

// After (Agenkit)
const myTool = {
  name: 'myTool',
  description: '...',
  async execute({ input }: { input: string }): Promise<string> {
    return `result: ${input}`;
  },
};
```

### Step 6: Replace `generateObject()` Calls

```typescript
// Before
const { object } = await generateObject({ model, prompt, schema: z.object({ ... }) });

// After
const structuredPrompt = `${prompt}\n\nRespond with ONLY valid JSON: { "field": value }`;
const response = await agent.process(createMessage('user', structuredPrompt));
const object = JSON.parse(response.content as string);
```

### Step 7: Replace `useChat()` Hooks

Migrate to AG-UI protocol (see Pattern 6 above), or keep the Vercel AI SDK
for the React layer while using Agenkit for the backend agent logic.

---

## Working Example

See `agenkit-ts/examples/frameworks/miniverscel.ts` for a complete, runnable
demonstration of all Vercel AI SDK patterns built on Agenkit primitives:

```bash
# Requires Ollama running locally
ollama serve && ollama pull llama3.2
npx ts-node agenkit-ts/examples/frameworks/miniverscel.ts
```

The example demonstrates:
- `streamText()` → `agent.processStream()` async generator
- `streamText()` with tools → `ReActAgent`
- `generateText()` → `agent.process()`
- `generateObject()` → structured-output prompt + `JSON.parse`
- `TextStreamPart` union → `Message` chunk

---

## Summary

The Vercel AI SDK is an excellent choice for Next.js / Vercel-hosted applications.
If you need **multi-language support**, **infrastructure independence**, or
**production-grade agent patterns** beyond simple streaming, Agenkit provides
a full migration path with equivalent coverage of every core API concept.

| Vercel AI SDK | Agenkit |
|--------------|---------|
| TypeScript only | 6 languages |
| Vercel/Next.js optimised | Runs anywhere |
| Zod-native schema validation | TypeScript interfaces + explicit JSON |
| `useChat()` React hook | AG-UI protocol (framework-agnostic) |
| Provider ecosystem | OpenAI-compatible + native adapters |
| Simple streaming | 11+ agent patterns |
