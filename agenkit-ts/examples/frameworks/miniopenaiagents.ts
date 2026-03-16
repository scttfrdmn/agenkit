/**
 * MiniOpenAIAgents (TypeScript) — OpenAI Agents SDK Equivalent Built on Agenkit
 *
 * Demonstrates how the OpenAI Agents SDK (TypeScript-first, January 2026)
 * patterns can be built ON TOP of Agenkit primitives.
 *
 * OpenAI Agents SDK Key Concepts (TypeScript, v0.0.x):
 * - Agent:          named agent with instructions, tools, and handoffs
 * - FunctionTool:   wraps a TS function as a callable tool
 * - Handoff:        routes execution to a target agent
 * - Runner:         executes agents; run() async streaming, runSync() blocking
 * - RunResult:      finalOutput string + full messages history
 *
 * Pattern Mappings:
 *   OAI.Agent       → Agenkit Agent (base interface)
 *   OAI.Runner      → Agenkit agent.process() / streaming loop
 *   OAI.FunctionTool → Agenkit Tool class
 *   OAI.handoff()   → Agenkit RouterAgent / conditional dispatch
 *   OAI.RunResult   → Agenkit Message (final assistant message)
 *
 * Migration guide: docs/migrations/openaiagents-to-agenkit.md
 *
 * Setup:
 *   ollama serve && ollama pull llama3.2
 *   npx ts-node examples/frameworks/miniopenaiagents.ts
 */

import { createMessage } from '../../src/index.js';
import { OpenAICompatibleAgent } from '../../src/llm/openai-compatible.js';
import type { Message } from '../../src/core/interfaces.js';

// ---------------------------------------------------------------------------
// FunctionTool — mirrors OAI FunctionTool / @function_tool
// ---------------------------------------------------------------------------

/**
 * A callable tool wrapping a TypeScript function.
 * Equivalent to the @function_tool decorator in the OpenAI Agents SDK.
 */
interface FunctionTool {
  name: string;
  description: string;
  execute(args: Record<string, string>): Promise<string>;
}

/** Helper to create a FunctionTool inline. */
function functionTool(
  name: string,
  description: string,
  fn: (args: Record<string, string>) => Promise<string>
): FunctionTool {
  return { name, description, execute: fn };
}

// ---------------------------------------------------------------------------
// Handoff — mirrors OAI handoff()
// ---------------------------------------------------------------------------

/**
 * Routes execution from one agent to a target agent.
 * Equivalent to handoff(targetAgent) in the OpenAI Agents SDK.
 */
interface Handoff {
  agent: OAIAgent;
}

// ---------------------------------------------------------------------------
// RunResult — mirrors OAI RunResult
// ---------------------------------------------------------------------------

/**
 * Outcome of Runner.runSync() or Runner.run().
 * Equivalent to the RunResult returned by the OpenAI Agents SDK Runner.
 */
interface RunResult {
  finalOutput: string;
  messages: Message[];
}

// ---------------------------------------------------------------------------
// OAIAgent — mirrors OAI Agent
// ---------------------------------------------------------------------------

/**
 * Named agent with instructions, tools, and optional handoff targets.
 * Equivalent to new Agent({ name, instructions, tools, handoffs }).
 */
class OAIAgent {
  readonly name: string;
  readonly instructions: string;
  readonly llm: OpenAICompatibleAgent;
  readonly tools: FunctionTool[];
  readonly handoffs: Handoff[];

  constructor(config: {
    name: string;
    instructions: string;
    llm: OpenAICompatibleAgent;
    tools?: FunctionTool[];
    handoffs?: Handoff[];
  }) {
    this.name = config.name;
    this.instructions = config.instructions;
    this.llm = config.llm;
    this.tools = config.tools ?? [];
    this.handoffs = config.handoffs ?? [];
  }

  toolMap(): Map<string, FunctionTool> {
    return new Map(this.tools.map((t) => [t.name, t]));
  }

  handoffMap(): Map<string, OAIAgent> {
    return new Map(this.handoffs.map((h) => [h.agent.name, h.agent]));
  }
}

// ---------------------------------------------------------------------------
// execute — core loop shared by Runner.run and Runner.runSync
// ---------------------------------------------------------------------------

async function execute(agent: OAIAgent, input: string): Promise<RunResult> {
  const messages: Message[] = [createMessage('user', input)];
  let current = agent;
  const maxSteps = 10;

  for (let step = 0; step < maxSteps; step++) {
    const toolNames = current.tools.map((t) => t.name).join(', ');
    const handoffNames = current.handoffs.map((h) => h.agent.name).join(', ');

    const systemParts: string[] = [current.instructions];
    if (toolNames) {
      systemParts.push(`Available tools: ${toolNames}. Call with: TOOL: <name> ARGS: <value>`);
    }
    if (handoffNames) {
      systemParts.push(`Available handoffs: ${handoffNames}. Hand off with: HANDOFF: <agent_name>`);
    }

    const promptMsgs = [createMessage('system', systemParts.join('\n')), ...messages];

    let reply: string;
    try {
      const resp = await current.llm.process(createMessage('user',
        promptMsgs.map((m) => `${m.role}: ${m.content as string}`).join('\n')
      ));
      reply = resp.content as string;
    } catch {
      reply = '[LLM not running — showing structure only]';
      messages.push(createMessage('assistant', reply));
      return { finalOutput: reply, messages };
    }

    messages.push(createMessage('assistant', reply));

    // Check for TOOL: call.
    const toolIdx = reply.indexOf('TOOL:');
    if (toolIdx >= 0) {
      const line = reply.slice(toolIdx + 5).split('\n')[0];
      const [toolName, argsRaw] = line.split(' ARGS:');
      const toolFn = current.toolMap().get(toolName.trim());
      if (toolFn) {
        const result = await toolFn.execute({ input: (argsRaw ?? '').trim() });
        messages.push(createMessage('tool', `[${toolFn.name}] ${result}`));
        continue;
      }
    }

    // Check for HANDOFF: routing.
    const handoffIdx = reply.indexOf('HANDOFF:');
    if (handoffIdx >= 0) {
      const targetName = reply.slice(handoffIdx + 8).split('\n')[0].trim();
      const target = current.handoffMap().get(targetName);
      if (target) {
        console.log(`   → Handing off to: ${target.name}`);
        current = target;
        continue;
      }
    }

    return { finalOutput: reply, messages };
  }

  const last = messages[messages.length - 1]?.content as string ?? '';
  return { finalOutput: last, messages };
}

// ---------------------------------------------------------------------------
// Runner — mirrors OAI Runner
// ---------------------------------------------------------------------------

/**
 * Executes OAIAgent instances (mirrors the OpenAI Agents SDK Runner class).
 *
 * OpenAI Agents SDK:
 *   Runner.run_sync(agent, input)  → RunResult
 *   await Runner.run(agent, input) → async streaming
 */
const Runner = {
  /**
   * Execute agent synchronously and return a RunResult.
   * Pattern: OAI.Runner.run_sync → execute() then return result
   */
  async runSync(agent: OAIAgent, input: string): Promise<RunResult> {
    return execute(agent, input);
  },

  /**
   * Execute agent and yield output as an async iterable of string chunks.
   * Pattern: OAI.Runner.run (streaming) → AsyncGenerator<string>
   */
  async *run(agent: OAIAgent, input: string): AsyncGenerator<string> {
    const result = await execute(agent, input);
    // Simulate streaming by yielding words one at a time.
    for (const word of result.finalOutput.split(/\s+/)) {
      yield word + ' ';
    }
  },
};

// ---------------------------------------------------------------------------
// Demo examples
// ---------------------------------------------------------------------------

async function exampleTriageHandoff(llm: OpenAICompatibleAgent): Promise<void> {
  console.log('='.repeat(60));
  console.log('Example 1: Triage Agent + Handoff (billing vs tech support)');
  console.log('='.repeat(60));

  const billingAgent = new OAIAgent({
    name: 'billing',
    instructions: 'You are a billing specialist. Help with invoices, payments, and subscriptions.',
    llm,
  });

  const techAgent = new OAIAgent({
    name: 'tech_support',
    instructions: 'You are a technical support specialist. Help with bugs, errors, and API questions.',
    llm,
  });

  const triageAgent = new OAIAgent({
    name: 'triage',
    instructions:
      'You are a triage agent. Route requests to the right specialist:\n' +
      '- billing: for payment, invoice, subscription questions\n' +
      '- tech_support: for technical issues, bugs, API questions\n' +
      'Always start with: HANDOFF: <agent_name>',
    llm,
    handoffs: [{ agent: billingAgent }, { agent: techAgent }],
  });

  console.log('\n   // OpenAI Agents SDK equivalent:');
  console.log("   const billing = new Agent({ name: 'billing', instructions: '...' });");
  console.log("   const triage = new Agent({ name: 'triage', handoffs: [handoff(billing), handoff(tech)] });");
  console.log('   const result = await Runner.run_sync(triage, "I get 401 errors on the API.");');
  console.log('\n   // Agenkit equivalent:');
  console.log('   const router = new RouterAgent({ agents: { billing, tech } });');

  const result = await Runner.runSync(triageAgent, 'I keep getting a 401 error on the API.');
  console.log(`\n   Messages exchanged: ${result.messages.length}`);
  console.log(`   Final output: ${(result.finalOutput).substring(0, 80)}...`);
  console.log('   Pattern: OAI.Agent + handoff() → Agenkit RouterAgent / conditional dispatch');
}

async function exampleFunctionTool(llm: OpenAICompatibleAgent): Promise<void> {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 2: FunctionTool (mock order DB lookup)');
  console.log('='.repeat(60));

  const lookupOrder = functionTool(
    'lookup_order',
    'Look up an order status by order ID.',
    async (args) => {
      const orders: Record<string, string> = {
        'ORD-001': 'Shipped — arrives 2026-03-20',
        'ORD-002': 'Processing — payment pending',
        'ORD-003': 'Delivered — 2026-03-10',
      };
      const id = (args.input ?? '').trim();
      return orders[id] ?? `Order "${id}" not found`;
    }
  );

  const supportAgent = new OAIAgent({
    name: 'support',
    instructions:
      'You are a helpful support agent. Use tools when needed.\n' +
      'To call a tool: TOOL: <name> ARGS: <argument>',
    llm,
    tools: [lookupOrder],
  });

  console.log('\n   // OpenAI Agents SDK equivalent:');
  console.log('   const lookupOrder = tool({');
  console.log('     name: "lookup_order",');
  console.log('     description: "Look up order status",');
  console.log("     parameters: z.object({ order_id: z.string() }),");
  console.log('     execute: async ({ order_id }) => orders[order_id],');
  console.log('   });');
  console.log('\n   // Agenkit equivalent:');
  console.log("   const tool: Tool = { name: 'lookup_order', execute: async (input) => ... };");

  const result = await Runner.runSync(supportAgent, 'Where is my order ORD-001?');
  console.log(`\n   Tool: ${lookupOrder.name} — ${lookupOrder.description}`);
  console.log(`   Messages: ${result.messages.length}`);
  console.log(`   Output: ${(result.finalOutput).substring(0, 80)}...`);
  console.log('   Pattern: OAI.FunctionTool → Agenkit Tool class');
}

async function exampleStreaming(llm: OpenAICompatibleAgent): Promise<void> {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 3: Async Streaming  (Runner.run)');
  console.log('='.repeat(60));

  const agent = new OAIAgent({
    name: 'assistant',
    instructions: 'You are a helpful assistant. Be concise.',
    llm,
  });

  console.log('\n   // OpenAI Agents SDK equivalent:');
  console.log("   for await (const event of Runner.run(agent, 'Explain Agenkit in one sentence.')) {");
  console.log("     if (event.type === 'raw_response_event') process.stdout.write(event.data.delta);");
  console.log('   }');
  console.log('\n   // Agenkit equivalent:');
  console.log('   for await (const chunk of agent.processStream(message)) {');
  console.log('     process.stdout.write(chunk.content as string);');
  console.log('   }');

  console.log('\n   Streaming output: ');
  process.stdout.write('   ');
  for await (const chunk of Runner.run(agent, 'Explain Agenkit in one sentence.')) {
    process.stdout.write(chunk);
  }
  console.log('\n   Pattern: OAI.Runner.run() streaming → Agenkit agent.processStream()');
}

async function main(): Promise<void> {
  console.log('╔' + '='.repeat(58) + '╗');
  console.log('║' + ' '.repeat(3) + 'MiniOpenAIAgents (TS) — OpenAI Agents SDK on Agenkit' + ' '.repeat(3) + '║');
  console.log('╚' + '='.repeat(58) + '╝');
  console.log('\n   Demonstrate: OpenAI Agents SDK patterns ON TOP of Agenkit (TypeScript)');

  const llm = new OpenAICompatibleAgent({
    baseURL: 'http://localhost:11434/v1',
    model: 'llama3.2',
    apiKey: 'ollama',
  });

  await exampleTriageHandoff(llm);
  await exampleFunctionTool(llm);
  await exampleStreaming(llm);

  console.log('\n\n' + '='.repeat(60));
  console.log('MiniOpenAIAgents (TypeScript) Examples Complete');
  console.log('='.repeat(60));
  console.log('\nKey Takeaways:');
  console.log('   Agenkit covers every core OpenAI Agents SDK TS concept:');
  console.log('     - Agent           → OAIAgent (name, instructions, tools, handoffs)');
  console.log('     - FunctionTool    → functionTool() helper / Agenkit Tool');
  console.log('     - handoff(agent)  → Handoff routing / Agenkit RouterAgent');
  console.log('     - Runner.runSync  → execute() promise');
  console.log('     - Runner.run      → async generator streaming');
  console.log('     - RunResult       → finalOutput + messages history');
  console.log('\nMigration guide: docs/migrations/openaiagents-to-agenkit.md');
}

main().catch((err: unknown) => {
  console.error('Error:', err);
  process.exit(1);
});
