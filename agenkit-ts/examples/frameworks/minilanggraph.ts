/**
 * MiniLangGraph (TypeScript) — LangGraph.js Equivalent Built on Agenkit
 *
 * Demonstrates how LangGraph.js graph-based workflow patterns can be built
 * ON TOP of Agenkit primitives, showing toolkit philosophy.
 *
 * LangGraph.js Key Concepts:
 * - StateGraph<S>:    directed graph whose nodes share typed state
 * - addNode():        register a node function
 * - addEdge():        unconditional edge between nodes
 * - addConditionalEdges(): branch based on a routing function
 * - compile():        produce an executable CompiledGraph
 * - MemorySaver:      in-memory state persistence across runs
 * - END:              terminal sentinel — stops graph execution
 *
 * Pattern Mappings:
 *   LangGraph.StateGraph          → Agenkit custom graph orchestration
 *   LangGraph.addConditionalEdges → Agenkit RouterAgent / conditional routing
 *   LangGraph.MemorySaver         → Agenkit checkpointing
 *   LangGraph.MessagesState       → Agenkit conversation history (GraphState)
 *
 * Migration guide: docs/migrations/langgraphjs-to-agenkit.md
 *
 * Setup:
 *   ollama serve && ollama pull llama3.2
 *   npx ts-node examples/frameworks/minilanggraph.ts
 */

import { createMessage } from '../../src/index.js';
import { OpenAICompatibleAgent } from '../../src/llm/openai-compatible.js';
import type { Message } from '../../src/core/interfaces.js';

// ---------------------------------------------------------------------------
// Sentinel — mirrors LangGraph END constant
// ---------------------------------------------------------------------------

/** Terminal sentinel. When a node routes to END, the graph stops. */
export const END = '__end__' as const;
type EndToken = typeof END;

// ---------------------------------------------------------------------------
// GraphState — shared typed state threaded through every node
// ---------------------------------------------------------------------------

/** Shared state object passed to and returned from every node. */
interface GraphState {
  messages: Message[];
  next: string;
  metadata: Record<string, unknown>;
}

function createState(partial: Partial<GraphState> = {}): GraphState {
  return {
    messages: partial.messages ?? [],
    next: partial.next ?? '',
    metadata: partial.metadata ?? {},
  };
}

function lastContent(state: GraphState): string {
  if (state.messages.length === 0) return '';
  return state.messages[state.messages.length - 1].content as string;
}

// ---------------------------------------------------------------------------
// Node and condition function types
// ---------------------------------------------------------------------------

/** A graph node: receives state, returns updated state. */
type NodeFn = (state: GraphState) => Promise<GraphState>;

/** A routing function: inspects state, returns next node name or END. */
type ConditionFn = (state: GraphState) => string;

// ---------------------------------------------------------------------------
// StateGraph — mirrors LangGraph.StateGraph
// ---------------------------------------------------------------------------

interface ConditionalEntry {
  condition: ConditionFn;
  mapping: Record<string, string>;
}

/**
 * Directed graph with shared typed state (mirrors LangGraph.StateGraph<S>).
 * Call compile() to produce a runnable CompiledGraph.
 */
class StateGraph {
  private nodes = new Map<string, NodeFn>();
  private edges = new Map<string, string>();
  private conditional = new Map<string, ConditionalEntry>();
  private entry: string | null = null;

  /** Register a node function (mirrors addNode). */
  addNode(name: string, fn: NodeFn): this {
    this.nodes.set(name, fn);
    return this;
  }

  /** Add an unconditional edge (mirrors addEdge). */
  addEdge(from: string, to: string | EndToken): this {
    this.edges.set(from, to);
    return this;
  }

  /**
   * Add a conditional branch from a node (mirrors addConditionalEdges).
   *
   * @param from - Source node name
   * @param condition - Returns a routing key
   * @param mapping - Maps routing keys to node names / END
   */
  addConditionalEdges(
    from: string,
    condition: ConditionFn,
    mapping: Record<string, string | EndToken>
  ): this {
    this.conditional.set(from, { condition, mapping });
    return this;
  }

  /** Set the entry point node (mirrors setEntryPoint). */
  setEntryPoint(name: string): this {
    this.entry = name;
    return this;
  }

  /** Compile into a runnable graph (mirrors compile()). */
  compile(checkpointer?: MemorySaver): CompiledGraph {
    if (!this.entry) throw new Error('No entry point set — call setEntryPoint() first');
    return new CompiledGraph(
      new Map(this.nodes),
      new Map(this.edges),
      new Map(this.conditional),
      this.entry,
      checkpointer
    );
  }
}

// ---------------------------------------------------------------------------
// CompiledGraph — mirrors LangGraph CompiledGraph / Pregel
// ---------------------------------------------------------------------------

/**
 * Runnable graph (mirrors LangGraph's compiled app).
 * Call invoke() to execute from the entry point.
 */
class CompiledGraph {
  private maxSteps = 20;

  constructor(
    private nodes: Map<string, NodeFn>,
    private edges: Map<string, string>,
    private conditional: Map<string, ConditionalEntry>,
    private entryNode: string,
    private checkpointer?: MemorySaver
  ) {}

  /**
   * Run the graph from the entry point (mirrors compiledGraph.invoke()).
   *
   * @param initial - Initial GraphState fields
   * @param config - Optional thread_id for MemorySaver persistence
   * @returns Final GraphState after execution
   */
  async invoke(
    initial: Partial<GraphState>,
    config?: { thread_id?: string }
  ): Promise<GraphState> {
    // Optionally resume from saved state.
    let state: GraphState;
    if (config?.thread_id && this.checkpointer) {
      const saved = this.checkpointer.load(config.thread_id);
      state = saved
        ? { ...saved, messages: [...saved.messages, ...(initial.messages ?? [])] }
        : createState(initial);
    } else {
      state = createState(initial);
    }

    let current: string = this.entryNode;
    const executionPath: string[] = [];

    for (let step = 0; step < this.maxSteps; step++) {
      if (current === END || !this.nodes.has(current)) break;

      executionPath.push(current);
      const nodeFn = this.nodes.get(current)!;
      state = await nodeFn(state);

      // Determine next node.
      let nextNode: string = END;
      if (this.conditional.has(current)) {
        const { condition, mapping } = this.conditional.get(current)!;
        const key = condition(state);
        nextNode = mapping[key] ?? END;
      } else if (this.edges.has(current)) {
        nextNode = this.edges.get(current)!;
      }

      current = nextNode;
    }

    state.metadata.executionPath = executionPath;

    if (config?.thread_id && this.checkpointer) {
      this.checkpointer.save(config.thread_id, state);
    }

    return state;
  }
}

// ---------------------------------------------------------------------------
// MemorySaver — mirrors LangGraph.MemorySaver
// ---------------------------------------------------------------------------

/**
 * In-memory state persistence across graph runs (mirrors LangGraph.MemorySaver).
 * Pattern: LangGraph.MemorySaver → Agenkit checkpointing
 */
class MemorySaver {
  private store = new Map<string, GraphState>();

  /** Save state under a thread ID. */
  save(threadId: string, state: GraphState): void {
    this.store.set(threadId, { ...state, messages: [...state.messages] });
  }

  /** Load state for a thread ID, or undefined if not found. */
  load(threadId: string): GraphState | undefined {
    return this.store.get(threadId);
  }

  /** List all saved thread IDs. */
  listThreads(): string[] {
    return [...this.store.keys()];
  }
}

// ---------------------------------------------------------------------------
// Demo examples
// ---------------------------------------------------------------------------

async function exampleLinearGraph(agent: OpenAICompatibleAgent): Promise<void> {
  console.log('='.repeat(60));
  console.log('Example 1: Linear Graph  (preprocess → generate → END)');
  console.log('='.repeat(60));

  const graph = new StateGraph()
    .addNode('preprocess', async (state) => {
      const raw = lastContent(state).trim().toLowerCase();
      return {
        ...state,
        messages: [...state.messages, createMessage('system', `[preprocessed] ${raw}`)],
      };
    })
    .addNode('generate', async (state) => {
      try {
        const resp = await agent.process(createMessage('user', lastContent(state)));
        return {
          ...state,
          messages: [...state.messages, createMessage('assistant', resp.content as string)],
        };
      } catch {
        return {
          ...state,
          messages: [...state.messages, createMessage('assistant', '[LLM not running — showing structure only]')],
        };
      }
    })
    .addEdge('preprocess', 'generate')
    .addEdge('generate', END)
    .setEntryPoint('preprocess')
    .compile();

  console.log('\n   // LangGraph.js equivalent:');
  console.log('   const graph = new StateGraph(MessagesAnnotation)');
  console.log("     .addNode('preprocess', preprocessFn)");
  console.log("     .addNode('generate', generateFn)");
  console.log("     .addEdge('preprocess', 'generate')");
  console.log("     .addEdge('generate', END)");
  console.log("     .compile();");
  console.log('   const result = await graph.invoke({ messages: [new HumanMessage("...")] });');

  const result = await graph.invoke({
    messages: [createMessage('user', '  What is Agenkit?  ')],
  });
  const path = (result.metadata.executionPath as string[]).join(' → ');
  console.log(`\n   Execution path: ${path} → END`);
  console.log(`   Messages: ${result.messages.length}`);
  console.log('   Pattern: LangGraph.StateGraph → Agenkit SequentialAgent / custom graph');
}

async function exampleConditionalRouting(agent: OpenAICompatibleAgent): Promise<void> {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 2: Conditional Routing  (classify → branch)');
  console.log('='.repeat(60));

  const graph = new StateGraph()
    .addNode('classify', async (state) => {
      const content = lastContent(state).toLowerCase();
      let intent = 'creative';
      if (content.includes('what') || content.includes('how') || content.includes('define')) {
        intent = 'factual';
      } else if (content.trim() === '') {
        intent = 'empty';
      }
      return {
        ...state,
        next: intent,
        messages: [...state.messages, createMessage('system', `[intent: ${intent}]`)],
      };
    })
    .addNode('answer_factual', async (state) => {
      try {
        const resp = await agent.process(createMessage('user', `[factual] ${lastContent(state)}`));
        return { ...state, messages: [...state.messages, createMessage('assistant', resp.content as string)] };
      } catch {
        return { ...state, messages: [...state.messages, createMessage('assistant', '[factual answer — LLM not running]')] };
      }
    })
    .addNode('answer_creative', async (state) => {
      try {
        const resp = await agent.process(createMessage('user', `[creative] ${lastContent(state)}`));
        return { ...state, messages: [...state.messages, createMessage('assistant', resp.content as string)] };
      } catch {
        return { ...state, messages: [...state.messages, createMessage('assistant', '[creative answer — LLM not running]')] };
      }
    })
    .addConditionalEdges('classify', (s) => s.next, {
      factual: 'answer_factual',
      creative: 'answer_creative',
      empty: END,
    })
    .addEdge('answer_factual', END)
    .addEdge('answer_creative', END)
    .setEntryPoint('classify')
    .compile();

  console.log('\n   // LangGraph.js equivalent:');
  console.log("   graph.addConditionalEdges('classify', routeByIntent, {");
  console.log("     factual: 'answer_factual', creative: 'answer_creative', empty: END");
  console.log('   });');
  console.log('\n   // Agenkit equivalent:');
  console.log('   const router = new RouterAgent({ classifier, agents: { factual, creative } });');

  const queries = [
    { label: 'factual', text: 'What is a transformer model?' },
    { label: 'creative', text: 'Write a haiku about distributed systems.' },
  ];

  for (const q of queries) {
    const res = await graph.invoke({ messages: [createMessage('user', q.text)] });
    const path = (res.metadata.executionPath as string[]).join(' → ');
    console.log(`\n   [${q.label}] "${q.text}"`);
    console.log(`   Path: ${path} → END`);
  }
  console.log('\n   Pattern: LangGraph.addConditionalEdges → Agenkit RouterAgent / conditional routing');
}

async function exampleMemorySaver(agent: OpenAICompatibleAgent): Promise<void> {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 3: MemorySaver  (state persistence across runs)');
  console.log('='.repeat(60));

  const memory = new MemorySaver();

  const graph = new StateGraph()
    .addNode('chat', async (state) => {
      try {
        const resp = await agent.process(createMessage('user', lastContent(state)));
        return { ...state, messages: [...state.messages, createMessage('assistant', resp.content as string)] };
      } catch {
        return { ...state, messages: [...state.messages, createMessage('assistant', '[LLM not running — showing structure only]')] };
      }
    })
    .addEdge('chat', END)
    .setEntryPoint('chat')
    .compile(memory);

  console.log('\n   // LangGraph.js equivalent:');
  console.log('   const memory = new MemorySaver();');
  console.log('   const app = graph.compile({ checkpointer: memory });');
  console.log("   const config = { configurable: { thread_id: 'user-42' } };");
  console.log("   await app.invoke({ messages: [new HumanMessage('My name is Alex.')] }, config);");
  console.log("   await app.invoke({ messages: [new HumanMessage('What is my name?')] }, config);");
  console.log('\n   // Agenkit equivalent:');
  console.log('   const agent = new ConversationalAgent({ llm, maxHistory: 10 });');

  const config = { thread_id: 'user-session-42' };

  await graph.invoke(
    { messages: [createMessage('user', 'My name is Alex.')] },
    config
  );

  const run2 = await graph.invoke(
    { messages: [createMessage('user', 'What is my name?')] },
    config
  );

  console.log(`\n   Thread '${config.thread_id}' — messages after 2 runs: ${run2.messages.length}`);
  console.log(`   Saved threads: ${memory.listThreads().join(', ')}`);
  console.log('   Pattern: LangGraph.MemorySaver → Agenkit ConversationalAgent (built-in history)');
}

async function main(): Promise<void> {
  console.log('╔' + '='.repeat(58) + '╗');
  console.log('║' + ' '.repeat(4) + 'MiniLangGraph (TS) — LangGraph.js Built on Agenkit' + ' '.repeat(4) + '║');
  console.log('╚' + '='.repeat(58) + '╝');
  console.log('\n   Demonstrate: LangGraph.js StateGraph patterns ON TOP of Agenkit');

  const agent = new OpenAICompatibleAgent({
    baseURL: 'http://localhost:11434/v1',
    model: 'llama3.2',
    apiKey: 'ollama',
  });

  await exampleLinearGraph(agent);
  await exampleConditionalRouting(agent);
  await exampleMemorySaver(agent);

  console.log('\n\n' + '='.repeat(60));
  console.log('MiniLangGraph (TypeScript) Examples Complete');
  console.log('='.repeat(60));
  console.log('\nKey Takeaways:');
  console.log('   Agenkit covers every core LangGraph.js concept:');
  console.log('     - StateGraph<S>        → custom graph executor');
  console.log('     - addNode / addEdge    → explicit wiring');
  console.log('     - addConditionalEdges  → RouterAgent / condition functions');
  console.log('     - MemorySaver          → ConversationalAgent (built-in history)');
  console.log('     - END sentinel         → graph termination');
  console.log('\nMigration guide: docs/migrations/langgraphjs-to-agenkit.md');
}

main().catch((err: unknown) => {
  console.error('Error:', err);
  process.exit(1);
});
