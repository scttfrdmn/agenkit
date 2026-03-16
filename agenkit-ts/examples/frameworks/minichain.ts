/**
 * MiniChain — LangChain.js Equivalent Built on Agenkit
 *
 * Demonstrates how LangChain.js patterns can be built ON TOP of Agenkit
 * primitives, showing toolkit philosophy for chain-based composition.
 *
 * LangChain.js Key Concepts:
 * - LLMChain:        single prompt template → LLM → string result
 * - SequentialChain: pipe multiple chains; each output feeds the next
 * - ConversationChain: stateful chat with multi-turn history
 * - RouterChain:     keyword-based dispatch to specialized sub-chains
 * - PromptTemplate:  parametric prompt string with {variable} slots
 *
 * Pattern Mappings:
 *   LangChain.LLMChain          → Agenkit LLM adapter + prompt template
 *   LangChain.SequentialChain   → Agenkit SequentialAgent / pipeline
 *   LangChain.ConversationChain → Agenkit ConversationalAgent (built-in history)
 *   LangChain.RouterChain       → Agenkit RouterAgent / conditional dispatch
 *   LangChain.PromptTemplate    → Agenkit Message content string
 *
 * Migration guide: docs/migrations/langchainjs-to-agenkit.md
 *
 * Setup:
 *   ollama serve && ollama pull llama3.2
 *   npx ts-node examples/frameworks/minichain.ts
 */

import { createMessage } from '../../src/index.js';
import { OpenAICompatibleAgent } from '../../src/llm/openai-compatible.js';
import type { Message } from '../../src/core/interfaces.js';

// ---------------------------------------------------------------------------
// PromptTemplate — mirrors LangChain.PromptTemplate
// ---------------------------------------------------------------------------

/**
 * Parametric prompt string with {variable} substitution slots.
 * Equivalent to new PromptTemplate({ template: "...", inputVariables: [...] })
 */
class PromptTemplate {
  constructor(private template: string) {}

  /**
   * Render the template by substituting all {key} slots.
   *
   * @param values - Map of variable names to string values
   * @returns Rendered prompt string
   */
  format(values: Record<string, string>): string {
    return this.template.replace(/\{(\w+)\}/g, (_, key) => values[key] ?? `{${key}}`);
  }
}

// ---------------------------------------------------------------------------
// Chain interface — mirrors LangChain Chain base class
// ---------------------------------------------------------------------------

/** Common interface for all chain types (mirrors LangChain's Chain base). */
interface Chain {
  run(input: string): Promise<string>;
}

// ---------------------------------------------------------------------------
// LLMChain — mirrors LangChain.LLMChain
// ---------------------------------------------------------------------------

/**
 * Renders a PromptTemplate with the input, then calls the LLM once.
 * Equivalent to new LLMChain({ llm, prompt }).
 */
class LLMChain implements Chain {
  constructor(
    private agent: OpenAICompatibleAgent,
    private prompt: PromptTemplate
  ) {}

  /**
   * Run the chain: fill template, call LLM, return string output.
   *
   * @param input - Value for the {input} slot in the template
   * @returns LLM response string
   */
  async run(input: string): Promise<string> {
    const rendered = this.prompt.format({ input });
    const message = createMessage('user', rendered);
    const response = await this.agent.process(message);
    return response.content as string;
  }
}

// ---------------------------------------------------------------------------
// SequentialChain — mirrors LangChain.SequentialChain
// ---------------------------------------------------------------------------

/**
 * Pipes multiple chains sequentially; each output becomes the next input.
 * Equivalent to new SequentialChain({ chains: [...] }).
 */
class SequentialChain implements Chain {
  constructor(private chains: Chain[]) {}

  /**
   * Run all chains in order, threading output → input.
   *
   * @param input - Initial input for the first chain
   * @returns Output of the last chain
   */
  async run(input: string): Promise<string> {
    let current = input;
    for (const chain of this.chains) {
      current = await chain.run(current);
    }
    return current;
  }
}

// ---------------------------------------------------------------------------
// ConversationChain — mirrors LangChain.ConversationChain
// ---------------------------------------------------------------------------

/**
 * Stateful conversation chain that accumulates message history.
 * Equivalent to new ConversationChain({ llm, memory: new BufferMemory() }).
 */
class ConversationChain implements Chain {
  private history: Message[] = [];

  constructor(
    private agent: OpenAICompatibleAgent,
    private system: string = 'You are a helpful assistant.'
  ) {}

  /**
   * Send a message, keeping full history for context.
   *
   * @param input - User message text
   * @returns Assistant response string
   */
  async run(input: string): Promise<string> {
    this.history.push(createMessage('user', input));

    // Build prompt with system context + full history.
    const contextParts: string[] = [
      `System: ${this.system}`,
      '',
      ...this.history.map((m) => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content as string}`),
    ];

    const prompt = contextParts.join('\n') + '\nAssistant:';
    const message = createMessage('user', prompt);
    const response = await this.agent.process(message);
    const reply = response.content as string;

    this.history.push(createMessage('assistant', reply));
    return reply;
  }

  /** Return number of messages in history. */
  get historyLength(): number {
    return this.history.length;
  }
}

// ---------------------------------------------------------------------------
// RouterChain — mirrors LangChain.RouterChain
// ---------------------------------------------------------------------------

/**
 * Routes the input to a specialist chain based on keyword matching.
 * Equivalent to MultiPromptChain / RouterOutputParser in LangChain.js.
 */
class RouterChain implements Chain {
  constructor(
    private routes: Map<string, Chain>,
    private keywords: Map<string, string[]>,
    private defaultRoute: string
  ) {}

  /**
   * Classify the input by keyword matching and dispatch to the matching chain.
   *
   * @param input - User query
   * @returns Output from the matched specialist chain
   */
  async run(input: string): Promise<string> {
    const lower = input.toLowerCase();
    let selected = this.defaultRoute;

    for (const [route, kws] of this.keywords.entries()) {
      if (kws.some((kw) => lower.includes(kw))) {
        selected = route;
        break;
      }
    }

    const chain = this.routes.get(selected);
    if (!chain) {
      return `[RouterChain: no chain found for route "${selected}"]`;
    }

    console.log(`   → RouterChain dispatching to: "${selected}"`);
    return chain.run(input);
  }
}

// ---------------------------------------------------------------------------
// Demo examples
// ---------------------------------------------------------------------------

async function exampleLLMChain(agent: OpenAICompatibleAgent): Promise<void> {
  console.log('='.repeat(60));
  console.log('Example 1: LLMChain (PromptTemplate → LLM → string)');
  console.log('='.repeat(60));

  const prompt = new PromptTemplate('Summarize the following in one sentence: {input}');
  const chain = new LLMChain(agent, prompt);

  console.log('\n   // LangChain.js equivalent:');
  console.log('   const prompt = PromptTemplate.fromTemplate("Summarize: {input}");');
  console.log('   const chain = new LLMChain({ llm, prompt });');
  console.log('   const result = await chain.invoke({ input: "..." });');
  console.log('\n   // Agenkit equivalent:');
  console.log('   const response = await agent.process(createMessage("user", rendered));');

  try {
    const result = await chain.run('Agenkit is a cross-language AI agent toolkit supporting Python, Go, TypeScript, Rust, C++, and Zig.');
    console.log(`\n   Result: ${(result).substring(0, 100)}...`);
  } catch {
    console.log('\n   [LLM not running — showing structure only]');
  }
  console.log('   Pattern: LangChain.LLMChain → Agenkit LLM adapter + prompt template');
}

async function exampleSequentialChain(agent: OpenAICompatibleAgent): Promise<void> {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 2: SequentialChain (pipeline composition)');
  console.log('='.repeat(60));

  const summarizeChain = new LLMChain(
    agent,
    new PromptTemplate('Summarize in one sentence: {input}')
  );
  const translateChain = new LLMChain(
    agent,
    new PromptTemplate('Translate to formal English: {input}')
  );
  const pipeline = new SequentialChain([summarizeChain, translateChain]);

  console.log('\n   // LangChain.js equivalent:');
  console.log('   const chain = new SequentialChain({');
  console.log('     chains: [summarizeChain, translateChain],');
  console.log('     inputVariables: ["input"],');
  console.log('   });');
  console.log('\n   // Agenkit equivalent:');
  console.log('   const pipeline = new SequentialAgent([summarize, translate]);');

  try {
    const result = await pipeline.run('Neural networks are computing systems inspired by biological neural networks.');
    console.log(`\n   Pipeline output: ${(result).substring(0, 100)}...`);
  } catch {
    console.log('\n   [LLM not running — showing structure only]');
  }
  console.log('   Pattern: LangChain.SequentialChain → Agenkit SequentialAgent / pipeline');
}

async function exampleConversationChain(agent: OpenAICompatibleAgent): Promise<void> {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 3: ConversationChain (multi-turn with history)');
  console.log('='.repeat(60));

  const conversation = new ConversationChain(
    agent,
    'You are a helpful assistant that remembers context.'
  );

  console.log('\n   // LangChain.js equivalent:');
  console.log('   const conversation = new ConversationChain({');
  console.log('     llm, memory: new BufferMemory()');
  console.log('   });');
  console.log('   await conversation.predict({ input: "My name is Alice." });');
  console.log('   await conversation.predict({ input: "What is my name?" });');
  console.log('\n   // Agenkit equivalent:');
  console.log('   const agent = new ConversationalAgent({ llm, maxHistory: 10 });');

  const turns = [
    'My name is Alice.',
    'What is my name?',
    'Tell me a fun fact about my name.',
  ];

  for (const userInput of turns) {
    console.log(`\n   User: ${userInput}`);
    try {
      const reply = await conversation.run(userInput);
      console.log(`   Assistant: ${(reply).substring(0, 80)}...`);
    } catch {
      console.log('   [LLM not running — showing structure only]');
    }
  }
  console.log(`\n   History length: ${conversation.historyLength} messages`);
  console.log('   Pattern: LangChain.ConversationChain → Agenkit ConversationalAgent (built-in history)');
}

async function exampleRouterChain(agent: OpenAICompatibleAgent): Promise<void> {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 4: RouterChain (keyword-based dispatch)');
  console.log('='.repeat(60));

  const codingChain = new LLMChain(agent, new PromptTemplate('Answer this coding question concisely: {input}'));
  const scienceChain = new LLMChain(agent, new PromptTemplate('Answer this science question accurately: {input}'));
  const generalChain = new LLMChain(agent, new PromptTemplate('Answer helpfully: {input}'));

  const routes = new Map<string, Chain>([
    ['coding', codingChain],
    ['science', scienceChain],
    ['general', generalChain],
  ]);
  const keywords = new Map<string, string[]>([
    ['coding', ['code', 'function', 'class', 'typescript', 'javascript', 'python', 'bug', 'error']],
    ['science', ['physics', 'chemistry', 'biology', 'quantum', 'atom', 'molecule', 'gravity']],
  ]);

  const router = new RouterChain(routes, keywords, 'general');

  console.log('\n   // LangChain.js equivalent:');
  console.log('   const router = MultiPromptChain.fromLLMAndPrompts(llm, promptInfos);');
  console.log('   const result = await router.call({ input: "..." });');
  console.log('\n   // Agenkit equivalent:');
  console.log('   const router = new RouterAgent({ classifier, agents: { coding, science, general } });');

  const queries = [
    'How do I write an async function in TypeScript?',
    'What is the speed of light?',
    'What should I have for dinner?',
  ];

  for (const query of queries) {
    console.log(`\n   Query: ${query}`);
    try {
      const result = await router.run(query);
      console.log(`   Answer: ${(result).substring(0, 80)}...`);
    } catch {
      console.log('   [LLM not running — showing structure only]');
    }
  }
  console.log('\n   Pattern: LangChain.RouterChain → Agenkit RouterAgent / conditional dispatch');
}

async function main(): Promise<void> {
  console.log('╔' + '='.repeat(58) + '╗');
  console.log('║' + ' '.repeat(7) + 'MiniChain — LangChain.js Built on Agenkit' + ' '.repeat(9) + '║');
  console.log('╚' + '='.repeat(58) + '╝');
  console.log('\n   Demonstrate: LangChain.js chain patterns ON TOP of Agenkit');

  const agent = new OpenAICompatibleAgent({
    baseURL: 'http://localhost:11434/v1',
    model: 'llama3.2',
    apiKey: 'ollama',
  });

  await exampleLLMChain(agent);
  await exampleSequentialChain(agent);
  await exampleConversationChain(agent);
  await exampleRouterChain(agent);

  console.log('\n\n' + '='.repeat(60));
  console.log('MiniChain Examples Complete');
  console.log('='.repeat(60));
  console.log('\nKey Takeaways:');
  console.log('   Agenkit covers every core LangChain.js chain concept:');
  console.log('     - LLMChain          → LLM adapter + PromptTemplate + process()');
  console.log('     - SequentialChain   → output-to-input piping / SequentialAgent');
  console.log('     - ConversationChain → history accumulation / ConversationalAgent');
  console.log('     - RouterChain       → keyword dispatch / RouterAgent');
  console.log('     - PromptTemplate    → {variable} slot substitution');
  console.log('\nMigration guide: docs/migrations/langchainjs-to-agenkit.md');
  console.log('\nWhy Agenkit over LangChain.js?');
  console.log('   6 languages (Python, Go, TypeScript, Rust, C++, Zig)');
  console.log('   No LangChain dependency — standalone toolkit');
  console.log('   11+ patterns (ReAct, Sequential, Router, Parallel, ...)');
  console.log('   OpenTelemetry observability built-in');
}

main().catch((err: unknown) => {
  console.error('Error:', err);
  process.exit(1);
});
