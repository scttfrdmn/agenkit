/**
 * MiniMastra — Mastra Equivalent Built on Agenkit
 *
 * Demonstrates how Mastra (TypeScript-native workflow + agent framework)
 * patterns can be built ON TOP of Agenkit primitives.
 *
 * Mastra is TypeScript-only with no Python/Go equivalent.
 * Key abstractions:
 * - Step<I, O>:         atomic unit of work with typed input/output and context
 * - Workflow:           fluent builder for step-based pipelines
 * - Workflow.step():    append a step to the linear flow
 * - Workflow.then():    chain output of previous step to the next
 * - Workflow.branch():  conditional branching based on output key
 * - Workflow.commit():  compile the workflow into a runnable CompiledWorkflow
 * - CompiledWorkflow:   execute(input) → WorkflowResult
 * - MastraAgent:        LLM-backed agent with instructions and a model
 * - MastraContext:      shared context object threaded through all steps
 *
 * Pattern Mappings:
 *   Mastra.Step          → Agenkit Agent / process step
 *   Mastra.Workflow      → Agenkit SequentialAgent or custom pipeline
 *   Mastra.branch()      → Agenkit RouterAgent / conditional dispatch
 *   Mastra.MastraAgent   → Agenkit Agent (base interface)
 *   Mastra.MastraContext → Agenkit Message metadata / conversation state
 *
 * Migration guide: docs/migrations/mastra-to-agenkit.md
 *
 * Setup:
 *   ollama serve && ollama pull llama3.2
 *   npx ts-node examples/frameworks/minimastra.ts
 */

import { createMessage } from '../../src/index.js';
import { OpenAICompatibleAgent } from '../../src/llm/openai-compatible.js';

// ---------------------------------------------------------------------------
// MastraContext — shared context object threaded through steps
// ---------------------------------------------------------------------------

/**
 * Shared context threaded through every step execution.
 * Equivalent to Mastra's context object (runId, variables, triggerData).
 */
interface MastraContext {
  runId: string;
  variables: Record<string, unknown>;
  triggerData?: unknown;
}

/** Create a context with a unique run ID. */
function createContext(overrides: Partial<MastraContext> = {}): MastraContext {
  return {
    runId: `run-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    variables: {},
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Step — mirrors Mastra Step<I, O>
// ---------------------------------------------------------------------------

/**
 * Atomic unit of work with typed input/output.
 * Equivalent to createStep({ id, execute }) in Mastra.
 */
interface Step<I, O> {
  id: string;
  execute(input: I, context: MastraContext): Promise<O>;
}

/** Helper to create a Step inline. */
function createStep<I, O>(
  id: string,
  executeFn: (input: I, context: MastraContext) => Promise<O>
): Step<I, O> {
  return { id, execute: executeFn };
}

// ---------------------------------------------------------------------------
// WorkflowResult — mirrors Mastra WorkflowResult
// ---------------------------------------------------------------------------

/**
 * Outcome of a compiled workflow execution.
 * Equivalent to Mastra's WorkflowRunResult.
 */
interface WorkflowResult<O> {
  output: O;
  stepOutputs: Map<string, unknown>;
  runId: string;
}

// ---------------------------------------------------------------------------
// CompiledWorkflow — mirrors Mastra CompiledWorkflow
// ---------------------------------------------------------------------------

/** Internal representation of a step in the compiled DAG. */
type StepNode =
  | { kind: 'sequential'; step: Step<unknown, unknown> }
  | { kind: 'branch'; condition: (output: unknown) => string; branches: Record<string, Step<unknown, unknown>> };

/**
 * Runnable compiled workflow (mirrors Mastra CompiledWorkflow).
 * Produced by Workflow.commit().
 */
class CompiledWorkflow<I = unknown, O = unknown> {
  constructor(private nodes: StepNode[]) {}

  /**
   * Execute the workflow from start to finish.
   *
   * @param input - Initial input for the first step
   * @returns WorkflowResult with final output and per-step outputs
   */
  async execute(input: I): Promise<WorkflowResult<O>> {
    const context = createContext();
    const stepOutputs = new Map<string, unknown>();
    let current: unknown = input;

    for (const node of this.nodes) {
      if (node.kind === 'sequential') {
        current = await node.step.execute(current, context);
        stepOutputs.set(node.step.id, current);
      } else if (node.kind === 'branch') {
        const key = node.condition(current);
        const branch = node.branches[key];
        if (!branch) {
          throw new Error(`No branch found for key "${key}"`);
        }
        console.log(`   → Workflow branching: "${key}"`);
        current = await branch.execute(current, context);
        stepOutputs.set(`branch:${key}:${branch.id}`, current);
      }
    }

    return { output: current as O, stepOutputs, runId: context.runId };
  }
}

// ---------------------------------------------------------------------------
// Workflow — mirrors Mastra Workflow (fluent builder)
// ---------------------------------------------------------------------------

/**
 * Fluent workflow builder (mirrors Mastra's Workflow class).
 *
 * Mastra usage:
 *   const workflow = new Workflow({ name: "research" })
 *     .step(classifyStep)
 *     .branch(
 *       (output) => output.type,
 *       { expert: expertStep, general: generalStep }
 *     )
 *     .then(summarizeStep)
 *     .commit();
 */
class Workflow {
  private nodes: StepNode[] = [];

  /**
   * Append a step to the workflow (mirrors Workflow.step()).
   * @param step - Step to append
   */
  step<I, O>(s: Step<I, O>): this {
    this.nodes.push({ kind: 'sequential', step: s as Step<unknown, unknown> });
    return this;
  }

  /**
   * Chain the output of the previous step into the next (mirrors Workflow.then()).
   * Semantically identical to step() in this implementation.
   * @param step - Step to chain
   */
  then<I, O>(s: Step<I, O>): this {
    return this.step(s);
  }

  /**
   * Add a conditional branch (mirrors Workflow.branch()).
   *
   * @param condition - Function mapping previous output to a branch key
   * @param branches  - Map of branch keys to Step handlers
   */
  branch<I, O>(
    condition: (output: I) => string,
    branches: Record<string, Step<I, O>>
  ): this {
    this.nodes.push({
      kind: 'branch',
      condition: condition as (output: unknown) => string,
      branches: branches as Record<string, Step<unknown, unknown>>,
    });
    return this;
  }

  /**
   * Compile the workflow into a runnable CompiledWorkflow (mirrors Workflow.commit()).
   * @returns CompiledWorkflow ready to execute
   */
  commit<I = unknown, O = unknown>(): CompiledWorkflow<I, O> {
    return new CompiledWorkflow<I, O>([...this.nodes]);
  }
}

// ---------------------------------------------------------------------------
// MastraAgent — mirrors Mastra Agent
// ---------------------------------------------------------------------------

/**
 * LLM-backed agent with instructions and a model.
 * Equivalent to new Agent({ name, instructions, model }) in Mastra.
 */
class MastraAgent {
  constructor(
    readonly name: string,
    readonly instructions: string,
    readonly model: OpenAICompatibleAgent
  ) {}

  /**
   * Generate a response to the given input.
   *
   * @param input - User input string
   * @returns Agent response string
   */
  async generate(input: string): Promise<string> {
    const prompt = `${this.instructions}\n\nUser: ${input}\nAssistant:`;
    try {
      const resp = await this.model.process(createMessage('user', prompt));
      return resp.content as string;
    } catch {
      return '[LLM not running — showing structure only]';
    }
  }
}

// ---------------------------------------------------------------------------
// Demo types
// ---------------------------------------------------------------------------

interface ResearchInput {
  topic: string;
}

interface ClassifyOutput {
  topic: string;
  type: 'expert' | 'general';
  confidence: number;
}

interface ResearchOutput {
  topic: string;
  type: string;
  findings: string;
}

interface SummaryOutput {
  summary: string;
  topic: string;
  type: string;
}

// ---------------------------------------------------------------------------
// Demo examples
// ---------------------------------------------------------------------------

async function exampleResearchWorkflow(agent: OpenAICompatibleAgent): Promise<void> {
  console.log('='.repeat(60));
  console.log('Example 1: Research Workflow with Branching');
  console.log('='.repeat(60));

  // Step: classify the topic as expert or general
  const classifyStep = createStep<ResearchInput, ClassifyOutput>(
    'classify',
    async (input, _ctx) => {
      const expertKeywords = ['quantum', 'neural', 'cryptography', 'topology', 'biochemistry'];
      const isExpert = expertKeywords.some((kw) => input.topic.toLowerCase().includes(kw));
      const result: ClassifyOutput = {
        topic: input.topic,
        type: isExpert ? 'expert' : 'general',
        confidence: isExpert ? 0.92 : 0.78,
      };
      console.log(`\n   [classify] topic="${input.topic}" → type="${result.type}" (${result.confidence})`);
      return result;
    }
  );

  // Expert branch step
  const expertResearchStep = createStep<ClassifyOutput, ResearchOutput>(
    'expert_research',
    async (input, _ctx) => {
      const mastra = new MastraAgent(
        'expert',
        'You are a domain expert. Provide technically precise, in-depth analysis.',
        agent
      );
      const findings = await mastra.generate(`Provide expert analysis of: ${input.topic}`);
      return { topic: input.topic, type: 'expert', findings };
    }
  );

  // General branch step
  const generalResearchStep = createStep<ClassifyOutput, ResearchOutput>(
    'general_research',
    async (input, _ctx) => {
      const mastra = new MastraAgent(
        'generalist',
        'You are a helpful assistant. Explain topics clearly for a general audience.',
        agent
      );
      const findings = await mastra.generate(`Explain in simple terms: ${input.topic}`);
      return { topic: input.topic, type: 'general', findings };
    }
  );

  // Final summarize step
  const summarizeStep = createStep<ResearchOutput, SummaryOutput>(
    'summarize',
    async (input, _ctx) => {
      const mastra = new MastraAgent(
        'summarizer',
        'You are a concise summarizer. Produce a 1-2 sentence summary.',
        agent
      );
      const summary = await mastra.generate(
        `Summarize in 1-2 sentences: ${input.findings}`
      );
      return { summary, topic: input.topic, type: input.type };
    }
  );

  const workflow = new Workflow()
    .step(classifyStep)
    .branch(
      (output: ClassifyOutput) => output.type,
      {
        expert: expertResearchStep,
        general: generalResearchStep,
      }
    )
    .then(summarizeStep)
    .commit<ResearchInput, SummaryOutput>();

  console.log('\n   // Mastra equivalent:');
  console.log('   const workflow = new Workflow({ name: "research" })');
  console.log('     .step(classifyStep)');
  console.log('     .branch(');
  console.log('       (output) => output.type,');
  console.log('       { expert: expertResearchStep, general: generalResearchStep }');
  console.log('     )');
  console.log('     .then(summarizeStep)');
  console.log('     .commit();');
  console.log('   const result = await workflow.execute({ topic: "quantum computing" });');
  console.log('\n   // Agenkit equivalent:');
  console.log('   const router = new RouterAgent({ classifier, agents: { expert, general } });');
  console.log('   const pipeline = new SequentialAgent([router, summarize]);');

  const topics = ['quantum computing algorithms', 'how to make coffee'];

  for (const topic of topics) {
    console.log(`\n   Topic: "${topic}"`);
    const result = await workflow.execute({ topic });
    console.log(`   Summary: ${result.output.summary.substring(0, 80)}...`);
    console.log(`   Branch taken: ${result.output.type} | Steps: ${result.stepOutputs.size}`);
    console.log(`   Run ID: ${result.runId}`);
  }

  console.log('\n   Pattern: Mastra.Workflow + branch() → Agenkit RouterAgent + SequentialAgent');
}

async function exampleAgentWithTools(agent: OpenAICompatibleAgent): Promise<void> {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 2: MastraAgent with Tool-Use Step');
  console.log('='.repeat(60));

  const lookupStep = createStep<{ query: string }, { query: string; result: string }>(
    'lookup',
    async (input, ctx) => {
      console.log(`\n   [lookup] context runId=${ctx.runId} query="${input.query}"`);
      // Mock database lookup
      const db: Record<string, string> = {
        agenkit: 'Cross-language AI agent toolkit (Python, Go, TypeScript, Rust, C++, Zig)',
        mastra: 'TypeScript-native workflow and agent framework',
        dspy: 'Declarative LM programming framework from Stanford NLP',
      };
      const key = Object.keys(db).find((k) => input.query.toLowerCase().includes(k));
      return {
        query: input.query,
        result: key ? db[key] : `No data found for "${input.query}"`,
      };
    }
  );

  const answerStep = createStep<{ query: string; result: string }, { answer: string }>(
    'answer',
    async (input, _ctx) => {
      const mastra = new MastraAgent(
        'answer_agent',
        'You are a knowledgeable assistant. Use the provided context to answer questions.',
        agent
      );
      const answer = await mastra.generate(
        `Context: ${input.result}\nQuestion: ${input.query}\nAnswer:`
      );
      return { answer };
    }
  );

  const workflow = new Workflow()
    .step(lookupStep)
    .then(answerStep)
    .commit<{ query: string }, { answer: string }>();

  console.log('\n   // Mastra equivalent:');
  console.log('   const agent = new Agent({ name: "answer", instructions: "...", model: openai("gpt-4o") });');
  console.log('   const workflow = new Workflow({ name: "lookup_and_answer" })');
  console.log('     .step(lookupStep)');
  console.log('     .then(answerStep)');
  console.log('     .commit();');

  const result = await workflow.execute({ query: 'What is Agenkit?' });
  console.log(`\n   Answer: ${result.output.answer.substring(0, 100)}...`);
  console.log(`   Steps completed: ${result.stepOutputs.size}`);
  console.log('   Pattern: Mastra.Workflow.step() + MastraAgent → Agenkit SequentialAgent + Agent');
}

async function main(): Promise<void> {
  console.log('╔' + '='.repeat(58) + '╗');
  console.log('║' + ' '.repeat(10) + 'MiniMastra — Mastra Built on Agenkit' + ' '.repeat(12) + '║');
  console.log('╚' + '='.repeat(58) + '╝');
  console.log('\n   Demonstrate: Mastra workflow patterns ON TOP of Agenkit (TypeScript-only)');
  console.log('   Note: Mastra has no Python/Go equivalent — TypeScript-native only.');

  const agent = new OpenAICompatibleAgent({
    baseURL: 'http://localhost:11434/v1',
    model: 'llama3.2',
    apiKey: 'ollama',
  });

  await exampleResearchWorkflow(agent);
  await exampleAgentWithTools(agent);

  console.log('\n\n' + '='.repeat(60));
  console.log('MiniMastra Examples Complete');
  console.log('='.repeat(60));
  console.log('\nKey Takeaways:');
  console.log('   Agenkit covers every core Mastra concept:');
  console.log('     - Step<I, O>       → typed process step / Agenkit Agent');
  console.log('     - Workflow.step()  → SequentialAgent / pipeline composition');
  console.log('     - Workflow.then()  → output-to-input chaining');
  console.log('     - Workflow.branch() → RouterAgent / conditional dispatch');
  console.log('     - Workflow.commit() → CompiledWorkflow.execute()');
  console.log('     - MastraAgent      → Agenkit Agent base interface');
  console.log('     - MastraContext    → shared run context / message metadata');
  console.log('\nMigration guide: docs/migrations/mastra-to-agenkit.md');
  console.log('\nWhy Agenkit over Mastra?');
  console.log('   6 languages (Python, Go, TypeScript, Rust, C++, Zig)');
  console.log('   No Vercel/cloud dependency');
  console.log('   OpenTelemetry observability built-in');
  console.log('   11+ patterns (ReAct, Sequential, Router, Parallel, ...)');
}

main().catch((err: unknown) => {
  console.error('Error:', err);
  process.exit(1);
});
