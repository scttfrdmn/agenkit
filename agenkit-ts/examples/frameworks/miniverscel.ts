/**
 * MiniVercel — Vercel AI SDK Equivalent Built on Agenkit
 *
 * Demonstrates how Vercel AI SDK (TypeScript-only, `ai` package) patterns can
 * be built ON TOP of Agenkit primitives.
 *
 * The Vercel AI SDK is TypeScript-only with no Python/Go equivalent.
 * Its key API surface:
 * - streamText():     streams tokens from a model with optional tool use
 * - generateText():   single-call text generation (non-streaming)
 * - tool():           wraps a Zod-validated function as a model tool
 * - generateObject(): generates structured JSON matching a Zod schema
 * - TextStreamPart:   union type for streaming events (text-delta, tool-call, finish)
 *
 * Pattern Mappings:
 *   AI.streamText()    → Agenkit agent.processStream() async generator
 *   AI.generateText()  → Agenkit agent.process()
 *   AI.tool()          → Agenkit Tool interface
 *   AI.generateObject  → Agenkit structured-output prompt + JSON.parse
 *   AI.TextStreamPart  → Agenkit Message chunk
 *
 * Migration guide: docs/migrations/vercelai-to-agenkit.md
 *
 * Setup:
 *   ollama serve && ollama pull llama3.2
 *   npx ts-node examples/frameworks/miniverscel.ts
 */

import { createMessage } from '../../src/index.js';
import { OpenAICompatibleAgent } from '../../src/llm/openai-compatible.js';

// ---------------------------------------------------------------------------
// Minimal Zod-like schema (no external dependency)
// ---------------------------------------------------------------------------

/** Simplified schema descriptor — mirrors Zod's z.object() API surface. */
interface ZodSchema<T extends Record<string, unknown>> {
  parse(value: unknown): T;
  describe(): Record<string, string>;
}

/** Create a simple object schema from a field descriptor map. */
function zodObject<T extends Record<string, unknown>>(
  fields: Record<keyof T & string, string>
): ZodSchema<T> {
  return {
    parse(value: unknown): T {
      if (typeof value !== 'object' || value === null) {
        throw new Error('Expected an object');
      }
      return value as T;
    },
    describe(): Record<string, string> {
      return fields as Record<string, string>;
    },
  };
}

// ---------------------------------------------------------------------------
// TextStreamPart — mirrors Vercel AI SDK TextStreamPart union
// ---------------------------------------------------------------------------

/** Union of streaming event types from streamText(). */
type TextStreamPart =
  | { type: 'text-delta'; textDelta: string }
  | { type: 'tool-call'; toolName: string; args: Record<string, string> }
  | { type: 'tool-result'; toolName: string; result: string }
  | { type: 'finish'; finishReason: string; text: string };

// ---------------------------------------------------------------------------
// VercelTool — mirrors AI.tool()
// ---------------------------------------------------------------------------

/**
 * A model-callable tool with a schema and execute function.
 * Equivalent to tool({ description, parameters, execute }) in the Vercel AI SDK.
 */
interface VercelTool<T extends Record<string, unknown>> {
  description: string;
  parameters: ZodSchema<T>;
  execute(args: T): Promise<string>;
}

/** Helper to create a VercelTool inline. */
function tool<T extends Record<string, unknown>>(config: VercelTool<T>): VercelTool<T> {
  return config;
}

// ---------------------------------------------------------------------------
// MockModel — wraps OpenAICompatibleAgent for Vercel-style API
// ---------------------------------------------------------------------------

/** Thin wrapper that adapts OpenAICompatibleAgent to the Vercel model interface. */
class MockModel {
  constructor(readonly agent: OpenAICompatibleAgent) {}

  async complete(prompt: string): Promise<string> {
    try {
      const resp = await this.agent.process(createMessage('user', prompt));
      return resp.content as string;
    } catch {
      return '[LLM not running — showing structure only]';
    }
  }
}

// ---------------------------------------------------------------------------
// streamText() — mirrors AI.streamText()
// ---------------------------------------------------------------------------

/**
 * Stream tokens from a model, yielding TextStreamPart events.
 * Equivalent to the streamText() function in the Vercel AI SDK.
 *
 * @param config - Model, prompt, and optional tools
 * @yields TextStreamPart events: text-delta, tool-call, tool-result, finish
 */
async function* streamText(config: {
  model: MockModel;
  prompt: string;
  tools?: Record<string, VercelTool<Record<string, unknown>>>;
  system?: string;
}): AsyncGenerator<TextStreamPart> {
  const { model, prompt, tools = {}, system = '' } = config;

  const toolDescriptions = Object.entries(tools)
    .map(([name, t]) => `${name}: ${t.description} (params: ${JSON.stringify(t.parameters.describe())})`)
    .join('\n');

  const fullPrompt = [
    system,
    toolDescriptions ? `Available tools:\n${toolDescriptions}\nCall with: TOOL_CALL: <name> ARGS: <json>` : '',
    `User: ${prompt}`,
  ]
    .filter(Boolean)
    .join('\n\n');

  const text = await model.complete(fullPrompt);

  // Check for tool call in the response.
  if ('TOOL_CALL:' in text || text.includes('TOOL_CALL:')) {
    const idx = text.indexOf('TOOL_CALL:');
    if (idx >= 0) {
      const line = text.slice(idx + 10).split('\n')[0];
      const [toolName, argsJson] = line.split(' ARGS:');
      const name = toolName.trim();

      let args: Record<string, unknown> = {};
      try {
        args = JSON.parse((argsJson ?? '{}').trim()) as Record<string, unknown>;
      } catch {
        args = { input: (argsJson ?? '').trim() };
      }

      yield { type: 'tool-call', toolName: name, args: args as Record<string, string> };

      if (name in tools) {
        const result = await tools[name].execute(args as Record<string, unknown>);
        yield { type: 'tool-result', toolName: name, result };

        // Continue with tool result in context.
        const followUp = await model.complete(`${fullPrompt}\nTool result for ${name}: ${result}\nFinal answer:`);
        for (const word of followUp.split(/\s+/)) {
          yield { type: 'text-delta', textDelta: word + ' ' };
        }
        yield { type: 'finish', finishReason: 'tool_calls', text: followUp };
        return;
      }
    }
  }

  // No tool call — stream the text word by word.
  for (const word of text.split(/\s+/)) {
    yield { type: 'text-delta', textDelta: word + ' ' };
  }
  yield { type: 'finish', finishReason: 'stop', text };
}

// ---------------------------------------------------------------------------
// generateText() — mirrors AI.generateText()
// ---------------------------------------------------------------------------

/**
 * Generate text from a model in a single call (non-streaming).
 * Equivalent to generateText() in the Vercel AI SDK.
 *
 * @param config - Model and prompt
 * @returns Object with text field
 */
async function generateText(config: { model: MockModel; prompt: string; system?: string }): Promise<{ text: string }> {
  const { model, prompt, system = '' } = config;
  const fullPrompt = system ? `${system}\n\n${prompt}` : prompt;
  const text = await model.complete(fullPrompt);
  return { text };
}

// ---------------------------------------------------------------------------
// generateObject() — mirrors AI.generateObject()
// ---------------------------------------------------------------------------

/**
 * Generate a structured JSON object matching a schema.
 * Equivalent to generateObject() in the Vercel AI SDK.
 *
 * @param config - Model, prompt, and schema
 * @returns Parsed object matching the schema
 */
async function generateObject<T extends Record<string, unknown>>(config: {
  model: MockModel;
  prompt: string;
  schema: ZodSchema<T>;
}): Promise<{ object: T }> {
  const { model, prompt, schema } = config;
  const fields = schema.describe();
  const fieldList = Object.entries(fields)
    .map(([k, v]) => `  "${k}": "${v}"`)
    .join(',\n');

  const fullPrompt =
    `${prompt}\n\n` +
    `Respond with ONLY a JSON object matching this schema:\n{\n${fieldList}\n}`;

  const text = await model.complete(fullPrompt);

  // Extract JSON from response.
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[0]) as T;
      return { object: schema.parse(parsed) };
    } catch {
      // Fallback: construct from field descriptions.
    }
  }

  // Fallback: create object from field names.
  const fallback: Record<string, string> = {};
  for (const key of Object.keys(fields)) {
    fallback[key] = text.substring(0, 50);
  }
  return { object: schema.parse(fallback) };
}

// ---------------------------------------------------------------------------
// Demo examples
// ---------------------------------------------------------------------------

async function exampleStreamText(model: MockModel): Promise<void> {
  console.log('='.repeat(60));
  console.log('Example 1: streamText() — token streaming');
  console.log('='.repeat(60));

  console.log('\n   // Vercel AI SDK equivalent:');
  console.log("   const { textStream } = await streamText({ model: openai('gpt-4o'), prompt: '...' });");
  console.log('   for await (const chunk of textStream) process.stdout.write(chunk);');
  console.log('\n   // Agenkit equivalent:');
  console.log('   for await (const chunk of agent.processStream(message)) {');
  console.log('     process.stdout.write(chunk.content as string);');
  console.log('   }');

  console.log('\n   Streaming: ');
  process.stdout.write('   ');
  for await (const part of streamText({
    model,
    prompt: 'Explain what Agenkit is in one sentence.',
    system: 'You are a helpful assistant.',
  })) {
    if (part.type === 'text-delta') {
      process.stdout.write(part.textDelta);
    } else if (part.type === 'finish') {
      console.log(`\n   [finish reason: ${part.finishReason}]`);
    }
  }
  console.log('   Pattern: AI.streamText() → Agenkit agent.processStream() async generator');
}

async function exampleStreamTextWithTools(model: MockModel): Promise<void> {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 2: streamText() with tools');
  console.log('='.repeat(60));

  type WeatherArgs = { location: string };
  const weatherTool = tool<WeatherArgs>({
    description: 'Get the current weather for a location',
    parameters: zodObject<WeatherArgs>({ location: 'string — city name' }),
    async execute({ location }) {
      return `Weather in ${location}: 22°C, partly cloudy`;
    },
  });

  console.log('\n   // Vercel AI SDK equivalent:');
  console.log("   const { textStream } = await streamText({");
  console.log("     model, prompt: '...',");
  console.log("     tools: { weather: tool({ description: '...', parameters: z.object(...), execute }) }");
  console.log('   });');
  console.log('\n   // Agenkit equivalent:');
  console.log('   const agent = new ReActAgent({ llm, tools: [{ name: "weather", execute }] });');

  const events: TextStreamPart[] = [];
  for await (const part of streamText({
    model,
    prompt: 'What is the weather in Tokyo?',
    tools: { weather: weatherTool as VercelTool<Record<string, unknown>> },
  })) {
    events.push(part);
    if (part.type === 'tool-call') {
      console.log(`\n   Tool call: ${part.toolName}(${JSON.stringify(part.args)})`);
    } else if (part.type === 'tool-result') {
      console.log(`   Tool result: ${part.result}`);
    } else if (part.type === 'finish') {
      console.log(`   [finish: ${part.finishReason}]`);
    }
  }
  console.log(`\n   Events: ${events.map((e) => e.type).join(' → ')}`);
  console.log('   Pattern: AI.tool() → Agenkit Tool interface; streamText with tools → ReActAgent');
}

async function exampleGenerateText(model: MockModel): Promise<void> {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 3: generateText() — single-call generation');
  console.log('='.repeat(60));

  console.log('\n   // Vercel AI SDK equivalent:');
  console.log("   const { text } = await generateText({ model: openai('gpt-4o'), prompt: '...' });");
  console.log('\n   // Agenkit equivalent:');
  console.log('   const response = await agent.process(createMessage("user", prompt));');

  const { text } = await generateText({
    model,
    prompt: 'List three benefits of using a multi-language AI toolkit.',
    system: 'You are a concise technical writer.',
  });

  console.log(`\n   Generated text: ${text.substring(0, 100)}...`);
  console.log('   Pattern: AI.generateText() → Agenkit agent.process()');
}

async function exampleGenerateObject(model: MockModel): Promise<void> {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 4: generateObject() — structured JSON output');
  console.log('='.repeat(60));

  type FrameworkInfo = { name: string; language: string; primary_use_case: string; year: string };
  const schema = zodObject<FrameworkInfo>({
    name: 'string — framework name',
    language: 'string — primary programming language',
    primary_use_case: 'string — main use case',
    year: 'string — year released',
  });

  console.log('\n   // Vercel AI SDK equivalent:');
  console.log('   const { object } = await generateObject({');
  console.log("     model, prompt: 'Describe Agenkit',");
  console.log("     schema: z.object({ name: z.string(), language: z.string(), ... })");
  console.log('   });');
  console.log('\n   // Agenkit equivalent:');
  console.log('   const response = await agent.process(createMessage("user", structuredPrompt));');
  console.log('   const object = JSON.parse(response.content as string);');

  const { object } = await generateObject({
    model,
    prompt: 'Describe the Agenkit framework as structured data.',
    schema,
  });

  console.log('\n   Generated object:');
  console.log(`     name:             ${object.name}`);
  console.log(`     language:         ${object.language}`);
  console.log(`     primary_use_case: ${object.primary_use_case}`);
  console.log(`     year:             ${object.year}`);
  console.log('   Pattern: AI.generateObject() → Agenkit structured-output prompt + JSON.parse');
}

async function main(): Promise<void> {
  console.log('╔' + '='.repeat(58) + '╗');
  console.log('║' + ' '.repeat(8) + 'MiniVercel — Vercel AI SDK Built on Agenkit' + ' '.repeat(7) + '║');
  console.log('╚' + '='.repeat(58) + '╝');
  console.log('\n   Demonstrate: Vercel AI SDK patterns ON TOP of Agenkit (TypeScript-only)');
  console.log('   Note: The Vercel AI SDK has no Python/Go equivalent — TS-only.');

  const agent = new OpenAICompatibleAgent({
    baseURL: 'http://localhost:11434/v1',
    model: 'llama3.2',
    apiKey: 'ollama',
  });
  const model = new MockModel(agent);

  await exampleStreamText(model);
  await exampleStreamTextWithTools(model);
  await exampleGenerateText(model);
  await exampleGenerateObject(model);

  console.log('\n\n' + '='.repeat(60));
  console.log('MiniVercel Examples Complete');
  console.log('='.repeat(60));
  console.log('\nKey Takeaways:');
  console.log('   Agenkit covers every core Vercel AI SDK concept:');
  console.log('     - streamText()    → agent.processStream() async generator');
  console.log('     - generateText()  → agent.process() single call');
  console.log('     - tool()          → Agenkit Tool interface');
  console.log('     - generateObject  → structured-output prompt + JSON.parse');
  console.log('     - TextStreamPart  → text-delta / tool-call / tool-result / finish events');
  console.log('\nMigration guide: docs/migrations/vercelai-to-agenkit.md');
  console.log('\nWhy Agenkit over Vercel AI SDK?');
  console.log('   6 languages (Python, Go, TypeScript, Rust, C++, Zig)');
  console.log('   Not tied to Next.js / Vercel infrastructure');
  console.log('   OpenTelemetry observability built-in');
  console.log('   11+ patterns (ReAct, Sequential, Router, Parallel, ...)');
}

main().catch((err: unknown) => {
  console.error('Error:', err);
  process.exit(1);
});
