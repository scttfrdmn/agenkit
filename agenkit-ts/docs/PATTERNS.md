# Agenkit Agent Patterns Guide

A comprehensive guide to the 11 agent patterns in Agenkit TypeScript.

## Table of Contents

- [Overview](#overview)
- [Pattern Comparison](#pattern-comparison)
- [Composition Patterns](#composition-patterns)
  - [Sequential](#sequential)
  - [Parallel](#parallel)
- [Enhancement Patterns](#enhancement-patterns)
  - [Reflection](#reflection)
  - [ReAct](#react)
  - [Planning](#planning)
- [Specialized Patterns](#specialized-patterns)
  - [Task](#task)
  - [Conversational](#conversational)
  - [AgentsAsTools](#agentsastools)
- [Advanced Patterns](#advanced-patterns)
  - [Autonomous](#autonomous)
  - [Multiagent](#multiagent)
  - [MemoryHierarchy](#memoryhierarchy)
- [Pattern Selection Guide](#pattern-selection-guide)
- [Composing Patterns](#composing-patterns)

---

## Overview

Agent patterns are reusable architectural templates that solve common problems in AI agent design. Agenkit provides 11 production-ready patterns you can use immediately or combine for complex workflows.

### Why Patterns Matter

1. **Proven Solutions** — Patterns encode best practices from production systems
2. **Composability** — All patterns implement `Agent` and work together seamlessly
3. **Type Safety** — Full TypeScript generics, interfaces, and inference
4. **Async-Native** — Every pattern is built on `async/await` and `Promise.all`

### Pattern Categories

- **Composition** (Sequential, Parallel) — Combine multiple agents
- **Enhancement** (Reflection, ReAct, Planning) — Improve agent quality
- **Specialized** (Task, Conversational, AgentsAsTools) — Domain-specific behavior
- **Advanced** (Autonomous, Multiagent, MemoryHierarchy) — Complex orchestration

---

## Pattern Comparison

| Pattern | Complexity | Best For | TypeScript Primitive |
|---------|-----------|----------|---------------------|
| Sequential | Low | Data pipelines | `for...of` async loop |
| Parallel | Medium | Independent tasks | `Promise.all` |
| Reflection | Medium | Self-correction | Async iteration |
| ReAct | Medium | Decision-making | Tool dispatch loop |
| Planning | High | Multi-step workflows | Async step execution |
| Task | Low | Focused processing | Single `async` function |
| Conversational | Medium | Chatbots | History array + context |
| AgentsAsTools | High | Tool orchestration | Tool registry Map |
| Autonomous | Very High | Goal pursuit | Async goal loop |
| Multiagent | Very High | Agent collaboration | Concurrent coordination |
| MemoryHierarchy | High | Long-running agents | Tiered storage |

---

## Composition Patterns

### Sequential

**Purpose:** Process messages through multiple agents in order, where each agent's output becomes the next agent's input.

**When to Use:**
- Data transformation pipelines (validate → process → format)
- Multi-stage enrichment workflows
- When the output of step N must feed step N+1
- ETL-style processing

**ASCII Diagram:**

```
Input → Agent1 → Agent2 → Agent3 → Output
          ↓         ↓         ↓
       (result1) (result2) (result3)
```

**Implementation:**

```typescript
import { SequentialAgent, LocalAgent, createMessage } from '@agenkit/core';

// Stage 1: Validate input
const validator = new LocalAgent({
  name: 'validator',
  process: async (msg) => {
    const content = msg.content as string;
    if (content.trim().length === 0) {
      throw new Error('empty input');
    }
    return { role: 'assistant', content: content.trim() };
  },
});

// Stage 2: Process
const processor = new LocalAgent({
  name: 'processor',
  process: async (msg) => ({
    role: 'assistant',
    content: (msg.content as string).toUpperCase(),
  }),
});

// Stage 3: Format output
const formatter = new LocalAgent({
  name: 'formatter',
  process: async (msg) => ({
    role: 'assistant',
    content: `[RESULT]: ${msg.content}`,
    metadata: { formatted: true },
  }),
});

// Chain agents into a pipeline
const pipeline = new SequentialAgent(
  [validator, processor, formatter],
  { name: 'text-pipeline' }
);

const response = await pipeline.process(
  createMessage('user', '  hello world  ')
);
console.log(response.content);
// "[RESULT]: HELLO WORLD"
```

**Manual Sequential Pattern:**

```typescript
// Without SequentialAgent — explicit async loop
async function processSequentially(
  agents: Agent[],
  initialMessage: Message
): Promise<Message> {
  let current = initialMessage;
  for (const agent of agents) {
    current = await agent.process(current);
  }
  return current;
}
```

**Trade-offs:**
- Simple and predictable
- Slow — agents run one at a time
- Failure in any stage stops the pipeline (unless `stopOnError: false`)

---

### Parallel

**Purpose:** Process a message with multiple agents concurrently, then merge results.

**When to Use:**
- Independent tasks that don't depend on each other
- Fan-out data gathering (search multiple sources simultaneously)
- Generating multiple candidate responses
- When latency matters and tasks are independent

**ASCII Diagram:**

```
              ┌→ Agent1 →┐
Input ────────┼→ Agent2 →┼──→ Merge → Output
              └→ Agent3 →┘
```

**Implementation:**

```typescript
import { ParallelAgent, LocalAgent, createMessage } from '@agenkit/core';

// Three independent research agents
const webSearchAgent = new LocalAgent({
  name: 'web-search',
  process: async (msg) => ({
    role: 'assistant',
    content: `Web results for: ${msg.content}`,
  }),
});

const databaseAgent = new LocalAgent({
  name: 'database',
  process: async (msg) => ({
    role: 'assistant',
    content: `DB records for: ${msg.content}`,
  }),
});

const cacheAgent = new LocalAgent({
  name: 'cache',
  process: async (msg) => ({
    role: 'assistant',
    content: `Cached data for: ${msg.content}`,
  }),
});

// Run all three concurrently
const parallel = new ParallelAgent(
  [webSearchAgent, databaseAgent, cacheAgent],
  {
    name: 'multi-source',
    // Optional: custom merge function
    merge: (responses) => ({
      role: 'assistant',
      content: responses.map((r) => r.content).join('\n---\n'),
      metadata: { sourceCount: responses.length },
    }),
  }
);

// Get merged result
const merged = await parallel.process(createMessage('user', 'TypeScript'));
console.log(merged.content);

// Or get all results individually
const allResults = await parallel.processAll(createMessage('user', 'TypeScript'));
allResults.forEach((r, i) => console.log(`Source ${i + 1}: ${r.content}`));
```

**Manual Parallel Pattern:**

```typescript
// Without ParallelAgent — explicit Promise.all
const message = createMessage('user', 'query');

const [result1, result2, result3] = await Promise.all([
  webSearchAgent.process(message),
  databaseAgent.process(message),
  cacheAgent.process(message),
]);

// Merge manually
const combined = [result1, result2, result3]
  .map((r) => r.content)
  .join('\n');
```

**Concurrent Fan-Out with Error Handling:**

```typescript
// Use Promise.allSettled to handle partial failures
const results = await Promise.allSettled(
  agents.map((a) => a.process(message))
);

const successes = results
  .filter((r): r is PromiseFulfilledResult<Message> => r.status === 'fulfilled')
  .map((r) => r.value);

const failures = results
  .filter((r): r is PromiseRejectedResult => r.status === 'rejected')
  .map((r) => r.reason);

console.log(`${successes.length} succeeded, ${failures.length} failed`);
```

**Trade-offs:**
- Very fast — all agents run simultaneously
- Requires all agents to be independent (no data dependencies)
- Higher resource usage than sequential

---

## Enhancement Patterns

### Reflection

**Purpose:** Iteratively improve output quality through a draft-critique-refine loop.

**When to Use:**
- Writing tasks (essays, code, documentation)
- Tasks where quality is more important than speed
- When the first response is rarely optimal
- Self-correction workflows

**ASCII Diagram:**

```
Input → Draft → Critique → Refine → (quality check) → Output
          ↑____________________________|
              (repeat up to maxIterations)
```

**Implementation:**

```typescript
import { ReflectionAgent, LocalAgent, createMessage } from '@agenkit/core';

// The base agent generates drafts
const writerAgent = new LocalAgent({
  name: 'writer',
  process: async (msg) => ({
    role: 'assistant',
    content: `Draft: ${msg.content}... [initial response]`,
    metadata: { iteration: 0 },
  }),
});

// Wrap with reflection
const reflectingWriter = new ReflectionAgent(writerAgent, {
  maxIterations: 3,
  reflectionPrompt: 'Critique this response and improve it. Focus on: clarity, completeness, accuracy.',
});

const response = await reflectingWriter.process(
  createMessage('user', 'Explain async/await in TypeScript')
);
console.log(response.content);
console.log(`Iterations: ${response.metadata?.iterations}`);
```

**Custom Reflection Loop:**

```typescript
import { Agent, Message, createMessage } from '@agenkit/core';

async function reflectAndImprove(
  agent: Agent,
  message: Message,
  maxIterations = 3
): Promise<Message> {
  let current = await agent.process(message);
  let iteration = 0;

  while (iteration < maxIterations) {
    const critique = await agent.process(
      createMessage('user', `Critique and improve: ${current.content}`)
    );

    // Check if improvement is significant (application-specific)
    if (isGoodEnough(critique)) break;

    current = critique;
    iteration++;
  }

  return current;
}

function isGoodEnough(response: Message): boolean {
  const content = response.content as string;
  return content.length > 200 && !content.includes('improve');
}
```

**Trade-offs:**
- Higher output quality
- Multiple LLM calls (slow, higher cost)
- Returns to the same agent — bias can persist across iterations

---

### ReAct

**Purpose:** Interleave reasoning ("thought") and action (tool calls) until an answer is found.

**When to Use:**
- Complex questions requiring information lookup
- Tasks needing multiple tool invocations
- When the agent must decide which tools to use dynamically
- Question-answering over external data

**ASCII Diagram:**

```
Input → Thought → Action (tool call) → Observation → Thought → ... → Answer
```

**Implementation:**

```typescript
import { ReActAgent, LocalAgent, createMessage } from '@agenkit/core';
import type { Tool, ToolResult } from '@agenkit/core';

// Define tools
class CalculatorTool implements Tool {
  readonly name = 'calculator';
  readonly description = 'Perform arithmetic calculations';
  readonly parametersSchema = {
    type: 'object',
    properties: {
      expression: { type: 'string', description: 'Math expression to evaluate' },
    },
    required: ['expression'],
  };

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const expr = params.expression as string;
    try {
      // In production, use a safe expression evaluator
      const result = Function(`"use strict"; return (${expr})`)();
      return { output: result, success: true };
    } catch (error) {
      return { output: null, success: false, error: `invalid expression: ${expr}` };
    }
  }
}

class WikipediaTool implements Tool {
  readonly name = 'wikipedia';
  readonly description = 'Look up facts on Wikipedia';
  readonly parametersSchema = {
    type: 'object',
    properties: {
      query: { type: 'string', description: 'Search query' },
    },
    required: ['query'],
  };

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const query = params.query as string;
    // In production, use the Wikipedia API
    return {
      output: `Wikipedia article about: ${query}`,
      success: true,
      metadata: { query },
    };
  }
}

// Build the ReAct agent
const llmBase = new LocalAgent({
  name: 'llm',
  process: async (msg) => ({
    role: 'assistant',
    content: msg.content,
  }),
});

const reactAgent = new ReActAgent(
  llmBase,
  [new CalculatorTool(), new WikipediaTool()],
  {
    maxIterations: 8,
    systemPrompt:
      'Use the calculator for math and wikipedia for facts. ' +
      'Think step by step before taking action.',
  }
);

const response = await reactAgent.process(
  createMessage('user', "What is 15% of the population of Paris (2.1 million)?")
);
console.log(response.content);
```

**Implementing a Custom Tool:**

```typescript
import type { Tool, ToolResult } from '@agenkit/core';

class DatabaseTool implements Tool {
  readonly name = 'database';
  readonly description = 'Query the product database';
  readonly parametersSchema = {
    type: 'object',
    properties: {
      table: { type: 'string' },
      filter: { type: 'object' },
    },
    required: ['table'],
  };

  constructor(private readonly db: DatabaseClient) {}

  async execute(
    params: Record<string, unknown>,
    signal?: AbortSignal
  ): Promise<ToolResult> {
    const table = params.table as string;
    const filter = params.filter as Record<string, unknown> | undefined;

    try {
      const rows = await this.db.query(table, filter, { signal });
      return { output: rows, success: true, metadata: { rowCount: rows.length } };
    } catch (error) {
      return {
        output: null,
        success: false,
        error: error instanceof Error ? error.message : 'query failed',
      };
    }
  }
}
```

**Trade-offs:**
- Flexible — agent decides which tools to use
- Multiple LLM calls (latency and cost)
- Tool selection quality depends on LLM capability

---

### Planning

**Purpose:** Break a complex task into a structured plan, then execute each step.

**When to Use:**
- Long-horizon tasks with multiple dependencies
- Tasks requiring coordinated multi-step execution
- When the full solution needs to be understood before starting
- Project management, research, code generation

**ASCII Diagram:**

```
Input → Planner → [Step1, Step2, Step3] → Execute each → Aggregate → Output
```

**Implementation:**

```typescript
import { PlanningAgent, LocalAgent, createMessage } from '@agenkit/core';

// Planner: generates a step-by-step plan
const plannerAgent = new LocalAgent({
  name: 'planner',
  process: async (msg) => ({
    role: 'assistant',
    content: JSON.stringify({
      task: msg.content,
      steps: [
        { id: 1, action: 'research', description: 'Gather background information' },
        { id: 2, action: 'analyze', description: 'Analyze the gathered data' },
        { id: 3, action: 'synthesize', description: 'Produce the final output' },
      ],
    }),
  }),
});

// Executor: carries out individual steps
const executorAgent = new LocalAgent({
  name: 'executor',
  process: async (msg) => ({
    role: 'assistant',
    content: `Executed: ${msg.content}`,
    metadata: { completed: true },
  }),
});

const planningAgent = new PlanningAgent(plannerAgent, executorAgent, {
  maxSteps: 10,
  planningPrompt: 'Create a concise step-by-step plan to accomplish:',
});

const response = await planningAgent.process(
  createMessage('user', 'Write a technical overview of TypeScript generics')
);
console.log(response.content);
```

**Trade-offs:**
- Great for complex, multi-step tasks
- Upfront planning cost (slower to start)
- Plan may need revision if early steps fail

---

## Specialized Patterns

### Task

**Purpose:** Execute a specific named task with focused behavior.

**When to Use:**
- Single-responsibility agents
- Batch job processors
- Named operations with well-defined inputs and outputs
- Microservice-style agent decomposition

**Implementation:**

```typescript
import { TaskAgent, createMessage } from '@agenkit/core';

// A focused sentiment analysis task
const sentimentAnalyzer = new TaskAgent({
  name: 'sentiment-analyzer',
  taskName: 'analyze-sentiment',
  capabilities: ['sentiment-analysis', 'text-classification'],
  process: async (message, taskName) => {
    const text = message.content as string;
    const sentiment = analyzeSentiment(text);

    return {
      role: 'assistant',
      content: sentiment,
      metadata: {
        task: taskName,
        inputLength: text.length,
      },
    };
  },
});

const response = await sentimentAnalyzer.process(
  createMessage('user', 'TypeScript is fantastic for large codebases!')
);
console.log(response.content); // "positive"

function analyzeSentiment(text: string): string {
  const positive = ['great', 'fantastic', 'excellent', 'love', 'good'];
  const lower = text.toLowerCase();
  if (positive.some((word) => lower.includes(word))) return 'positive';
  return 'neutral';
}
```

---

### Conversational

**Purpose:** Maintain dialogue context across multiple turns.

**When to Use:**
- Chatbots and interactive assistants
- Multi-turn question answering
- Context-aware help desks
- Personalized experiences that require history

**ASCII Diagram:**

```
Turn 1: [user: "Hi, I'm Alice"] → [assistant: "Hello Alice!"]
Turn 2: [user: "What's my name?"] → [assistant: "Your name is Alice."]
         ↑ history injected automatically
```

**Implementation:**

```typescript
import { ConversationalAgent, LocalAgent, createMessage } from '@agenkit/core';

const llmAgent = new LocalAgent({
  name: 'llm',
  process: async (msg) => ({
    role: 'assistant',
    content: `Response to: ${msg.content}`,
  }),
});

const chat = new ConversationalAgent(llmAgent, {
  maxHistoryLength: 20,
  systemPrompt: 'You are a helpful assistant. Be concise and friendly.',
});

// Multi-turn conversation
const turn1 = await chat.process(createMessage('user', "My favorite color is blue."));
console.log(turn1.content);

const turn2 = await chat.process(createMessage('user', "What is my favorite color?"));
console.log(turn2.content); // Should reference blue from history

console.log(`History size: ${chat.getHistory().length}`);
chat.clearHistory(); // Reset for new conversation
```

**Custom History Management:**

```typescript
import { Agent, Message, createMessage } from '@agenkit/core';

class ConversationTracker {
  private history: Message[] = [];

  constructor(
    private readonly agent: Agent,
    private readonly maxHistory: number = 20
  ) {}

  async send(userMessage: Message): Promise<Message> {
    // Inject history as context
    const contextualMessage = createMessage('user', userMessage.content, {
      conversation_history: this.history.slice(-this.maxHistory),
    });

    const response = await this.agent.process(contextualMessage);

    // Record the exchange
    this.history.push(userMessage, response);

    // Trim if too long
    if (this.history.length > this.maxHistory * 2) {
      this.history = this.history.slice(-this.maxHistory * 2);
    }

    return response;
  }

  clearHistory(): void {
    this.history = [];
  }

  getHistory(): readonly Message[] {
    return this.history;
  }
}
```

**Trade-offs:**
- Natural, context-aware conversations
- Memory grows with conversation length
- Context window limits how much history can be used

---

### AgentsAsTools

**Purpose:** Allow an orchestrator agent to call other specialized agents as tools.

**When to Use:**
- Complex workflows requiring multiple specialized capabilities
- Building composable agent pipelines
- When the orchestrator needs to decide which specialist to invoke
- Agent delegation and capability routing

**ASCII Diagram:**

```
User → Orchestrator → [calls translator] → [calls summarizer] → Response
                  ↘→ [calls calculator] ↗
```

**Implementation:**

```typescript
import { AgentsAsToolsAgent, LocalAgent, createMessage } from '@agenkit/core';

// Specialist agents
const translationAgent = new LocalAgent({
  name: 'translator',
  capabilities: ['translation'],
  process: async (msg) => ({
    role: 'assistant',
    content: `Translated: ${msg.content}`,
  }),
});

const summaryAgent = new LocalAgent({
  name: 'summarizer',
  capabilities: ['summarization'],
  process: async (msg) => ({
    role: 'assistant',
    content: `Summary: ${(msg.content as string).slice(0, 50)}...`,
  }),
});

const codeAgent = new LocalAgent({
  name: 'coder',
  capabilities: ['code-generation'],
  process: async (msg) => ({
    role: 'assistant',
    content: `function solution() { /* ${msg.content} */ }`,
  }),
});

// Orchestrator that can call any specialist
const orchestratorBase = new LocalAgent({
  name: 'orchestrator-llm',
  process: async (msg) => ({
    role: 'assistant',
    content: msg.content,
  }),
});

const orchestrator = new AgentsAsToolsAgent(orchestratorBase, {
  tools: {
    translate: translationAgent,
    summarize: summaryAgent,
    code: codeAgent,
  },
});

// Register additional tools dynamically
orchestrator.registerTool('math', calculatorAgent);

const response = await orchestrator.process(
  createMessage('user', 'Summarize this and translate to Spanish.')
);
console.log(response.content);
```

---

## Advanced Patterns

### Autonomous

**Purpose:** Self-directed agent that pursues a high-level goal over many steps without human intervention.

**When to Use:**
- Long-horizon tasks that require dozens of steps
- Research automation
- Software development tasks (write, test, fix loop)
- When the full plan cannot be known in advance

**ASCII Diagram:**

```
Goal → Plan → Act → Observe → Update plan → Act → ... → Goal achieved
           ↑___________________________|
              (up to maxSteps iterations)
```

**Implementation:**

```typescript
import { AutonomousAgent, createMessage } from '@agenkit/core';
import type { Tool } from '@agenkit/core';

class FileReadTool implements Tool {
  readonly name = 'read_file';
  readonly description = 'Read a file from the filesystem';
  readonly parametersSchema = {
    type: 'object',
    properties: { path: { type: 'string' } },
    required: ['path'],
  };

  async execute(params: Record<string, unknown>) {
    // Implementation...
    return { output: `Contents of ${params.path}`, success: true };
  }
}

class FileWriteTool implements Tool {
  readonly name = 'write_file';
  readonly description = 'Write content to a file';
  readonly parametersSchema = {
    type: 'object',
    properties: {
      path: { type: 'string' },
      content: { type: 'string' },
    },
    required: ['path', 'content'],
  };

  async execute(params: Record<string, unknown>) {
    // Implementation...
    return { output: `Wrote to ${params.path}`, success: true };
  }
}

const auto = new AutonomousAgent(llmAgent, {
  goal: 'Read the TypeScript files in src/, identify common patterns, and write a summary to PATTERNS.md',
  maxSteps: 30,
  tools: [new FileReadTool(), new FileWriteTool()],
  onStep: (step, message) => {
    console.log(`Step ${step}: ${String(message.content).slice(0, 80)}...`);
  },
});

const result = await auto.run();
console.log('Completed:', result.content);

// Stop early if needed
// auto.stop(); // can be called from another async context
```

**Trade-offs:**
- Can solve complex tasks without human guidance
- Unpredictable execution path (may fail or go off-track)
- Resource-intensive (many LLM calls)
- Requires careful tool design to avoid unsafe side effects

---

### Multiagent

**Purpose:** Coordinate a team of specialized agents toward a shared goal.

**When to Use:**
- Large tasks that can be decomposed across specialists
- Peer review workflows (one agent writes, another critiques)
- Distributed problem-solving
- Simulation with multiple AI agents

**ASCII Diagram:**

```
                  ┌─ ResearchAgent ─┐
                  ├─ AnalystAgent   ├─→ CoordinatorAgent → Output
User → Dispatch ──┤                 │
                  └─ WriterAgent  ──┘
```

**Implementation:**

```typescript
import { MultiagentSystem, LocalAgent, createMessage } from '@agenkit/core';

// Specialized agents
const researcher = new LocalAgent({
  name: 'researcher',
  capabilities: ['research', 'fact-finding'],
  process: async (msg) => ({
    role: 'assistant',
    content: `Research findings: ${msg.content}`,
    metadata: { agent: 'researcher' },
  }),
});

const analyst = new LocalAgent({
  name: 'analyst',
  capabilities: ['analysis', 'data-interpretation'],
  process: async (msg) => ({
    role: 'assistant',
    content: `Analysis: ${msg.content}`,
    metadata: { agent: 'analyst' },
  }),
});

const writer = new LocalAgent({
  name: 'writer',
  capabilities: ['writing', 'summarization'],
  process: async (msg) => ({
    role: 'assistant',
    content: `Report: ${msg.content}`,
    metadata: { agent: 'writer' },
  }),
});

// Coordinator decides which agents to involve
const coordinator = new LocalAgent({
  name: 'coordinator',
  process: async (msg) => ({
    role: 'assistant',
    content: `Coordinated: ${msg.content}`,
  }),
});

const system = new MultiagentSystem({
  name: 'research-team',
  agents: {
    researcher,
    analyst,
    writer,
  },
  coordinator,
});

// Add agents dynamically
system.addAgent('fact-checker', factCheckerAgent);

const response = await system.process(
  createMessage('user', 'Produce a competitive analysis report.')
);

// Get results from all agents
const allResults = await system.coordinate(createMessage('user', 'Start research'));
allResults.forEach((r) => console.log(`${r.metadata?.agent}: ${r.content}`));
```

---

### MemoryHierarchy

**Purpose:** Provide agents with layered memory: working (current context), short-term (recent history), and long-term (persistent storage).

**When to Use:**
- Long-running conversational agents
- Agents that need to remember facts from earlier sessions
- When context windows are limited but full history matters
- Personalized assistants that learn user preferences

**ASCII Diagram:**

```
New Message → Working Memory (5 msgs) → Short-Term (100 msgs) → Long-Term (unlimited)
                 ↓ (most recent)            ↓ (recent sessions)    ↓ (all history)
              Active context            Secondary lookup          Persistent store
```

**Implementation:**

```typescript
import { MemoryHierarchyAgent, LocalAgent, createMessage } from '@agenkit/core';

const baseAgent = new LocalAgent({
  name: 'memory-agent-llm',
  process: async (msg) => ({
    role: 'assistant',
    content: `Response with context: ${msg.content}`,
  }),
});

const memoryAgent = new MemoryHierarchyAgent(baseAgent, {
  workingMemorySize: 5,      // last 5 messages in active context
  shortTermSize: 100,        // last 100 messages in fast storage
  longTermStorage: {         // optional persistent storage
    get: async (key) => undefined,
    set: async (key, value) => {},
    search: async (query) => [],
  },
});

// Simulate a long conversation
const turns = [
  'My name is Alice.',
  'I work at a tech company.',
  "I'm building an AI assistant.",
  'What is my name?',
  'What do I do for work?',
];

for (const turn of turns) {
  const response = await memoryAgent.process(createMessage('user', turn));
  console.log(`User: ${turn}`);
  console.log(`Agent: ${response.content}`);
  console.log();
}

console.log(`Working memory: ${memoryAgent.getWorkingMemory().length} messages`);
memoryAgent.clearWorkingMemory();
```

**Manual Memory Management:**

```typescript
import { Message, createMessage } from '@agenkit/core';

class SimpleMemory {
  private working: Message[] = [];
  private shortTerm: Message[] = [];

  constructor(
    private readonly workingSize = 5,
    private readonly shortTermSize = 100
  ) {}

  push(message: Message): void {
    this.working.unshift(message);
    this.shortTerm.unshift(message);

    if (this.working.length > this.workingSize) {
      this.working.pop();
    }
    if (this.shortTerm.length > this.shortTermSize) {
      this.shortTerm.pop();
    }
  }

  getContext(): Message[] {
    return [...this.working].reverse();
  }

  search(query: string): Message[] {
    return this.shortTerm.filter((m) =>
      typeof m.content === 'string' && m.content.includes(query)
    );
  }
}
```

---

## Pattern Selection Guide

Use this guide to choose the right pattern:

### "I need to transform data in stages"
→ Use **Sequential**

### "I need to gather from multiple sources at once"
→ Use **Parallel** (with `Promise.all`)

### "I need better quality output through iteration"
→ Use **Reflection**

### "My agent needs to use tools to answer questions"
→ Use **ReAct**

### "I have a complex multi-step task to decompose"
→ Use **Planning**

### "I need focused, single-purpose processing"
→ Use **Task**

### "I'm building a chatbot or interactive assistant"
→ Use **Conversational**

### "I need to delegate to specialist agents"
→ Use **AgentsAsTools**

### "I need a self-directed agent to pursue a goal"
→ Use **Autonomous**

### "I need multiple agents to collaborate"
→ Use **Multiagent**

### "I need persistent memory across sessions"
→ Use **MemoryHierarchy**

---

## Composing Patterns

Patterns are fully composable — any pattern implements `Agent` and can be used inside another pattern.

### Sequential + Parallel (Fan-out/Fan-in)

```typescript
import { SequentialAgent, ParallelAgent, LocalAgent, createMessage } from '@agenkit/core';

const input = new LocalAgent({ name: 'input', process: async (m) => m });

// Fan out to three parallel agents
const parallel = new ParallelAgent([
  new LocalAgent({ name: 'a', process: async (m) => ({ role: 'assistant', content: `A: ${m.content}` }) }),
  new LocalAgent({ name: 'b', process: async (m) => ({ role: 'assistant', content: `B: ${m.content}` }) }),
  new LocalAgent({ name: 'c', process: async (m) => ({ role: 'assistant', content: `C: ${m.content}` }) }),
]);

// Fan in to a single summarizer
const summarizer = new LocalAgent({
  name: 'summarizer',
  process: async (m) => ({ role: 'assistant', content: `Summary: ${m.content}` }),
});

const pipeline = new SequentialAgent([input, parallel, summarizer]);

const response = await pipeline.process(createMessage('user', 'Process this'));
```

### Reflection + ReAct

```typescript
import { ReflectionAgent, ReActAgent, createMessage } from '@agenkit/core';

// ReAct agent that can use tools
const reactBase = new ReActAgent(llmAgent, [searchTool, calculatorTool]);

// Wrap with reflection for self-improvement
const reflectedReact = new ReflectionAgent(reactBase, {
  maxIterations: 2,
  reflectionPrompt: 'Was the answer accurate and complete? Improve if needed:',
});

const response = await reflectedReact.process(
  createMessage('user', 'Research the history of TypeScript and summarize key milestones')
);
```

### Conversational + MemoryHierarchy

```typescript
import { ConversationalAgent, MemoryHierarchyAgent, createMessage } from '@agenkit/core';

// Add long-term memory to a conversational agent
const conversational = new ConversationalAgent(llmAgent, {
  systemPrompt: 'You are a personalized assistant.',
});

const withMemory = new MemoryHierarchyAgent(conversational, {
  workingMemorySize: 10,
  shortTermSize: 200,
});

// Conversation persists across sessions
await withMemory.process(createMessage('user', 'Remember: I prefer TypeScript over JavaScript.'));
```

### Production-Ready Composition

```typescript
import {
  ReActAgent,
  RetryMiddleware,
  TimeoutMiddleware,
  CachingMiddleware,
  TracingAgent,
  createMessage,
} from '@agenkit/core';

// Build the core agent
const core = new ReActAgent(llmAgent, [searchTool, calculatorTool], {
  maxIterations: 8,
});

// Layer on resilience middleware
let agent: Agent = core;
agent = new RetryMiddleware(agent, { maxRetries: 3, initialDelayMs: 1000 });
agent = new TimeoutMiddleware(agent, { timeoutMs: 30000 });
agent = new CachingMiddleware(agent, { ttlMs: 60000, maxSize: 100 });

// Add observability outermost
agent = new TracingAgent(agent, { serviceName: 'react-agent' });

const response = await agent.process(
  createMessage('user', 'What is the GDP of France?')
);
```

---

## Summary

All 11 patterns share three properties:

1. **Implement `Agent`** — Every pattern has `name`, `process()`, and optional `processStream()`
2. **Async-native** — All patterns use `Promise` and `AsyncGenerator` idiomatically
3. **Composable** — Any pattern can be wrapped by any other pattern or middleware

The choice of pattern depends on your data flow, latency requirements, and the complexity of the task. For most production systems, you will combine 2-4 patterns with 2-3 middleware layers.
