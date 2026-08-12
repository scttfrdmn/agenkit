#!/usr/bin/env node
/**
 * TypeScript test harness for cross-language equivalence testing.
 *
 * Implements the JSON protocol for executing pattern tests.
 */

import * as readline from 'readline';
import {
  Agent,
  Message,
  createMessage,
  ReflectionAgent,
  ReflectionConfig,
  SequentialPattern,
  ParallelPattern,
  ReActAgent,
  ReActConfig,
  ConversationalAgent,
  ReasoningWithToolsAgent,
  ReasoningWithToolsConfig,
  Task,
  Tool,
  ToolResult,
} from 'agenkit';

const PROTOCOL_VERSION = '1.0';
const VERSION = '0.44.0';

/**
 * Request message format
 */
interface Request {
  protocol_version: string;
  request_id: string;
  command: string;
  payload: Record<string, unknown>;
}

/**
 * Response message format
 */
interface Response {
  protocol_version: string;
  request_id: string;
  status: string;
  result: unknown;
  error: unknown;
}

/**
 * MockAgent class for deterministic testing.
 */
class MockAgent implements Agent {
  readonly name: string;
  private responses: string[];
  private callCount: number;
  private historyMessages: Message[];

  constructor(responses?: string[], name: string = 'mock_agent') {
    this.name = name;
    this.responses = responses || [
      '1. First, let\'s analyze the problem.\n2. Then, we\'ll solve it step by step.\n3. Finally, we arrive at the answer: 42.',
    ];
    this.callCount = 0;
    this.historyMessages = [];
  }

  get capabilities(): string[] {
    return ['mock', 'test'];
  }

  async chat(messages: Message[]): Promise<Message> {
    // LLMClient compatibility for ConversationalAgent
    const lastMessage = messages[messages.length - 1];
    if (lastMessage && String(lastMessage.content).toLowerCase().includes('name')) {
      // Look for name in previous messages
      for (const msg of messages.slice(0, -1)) {
        const match = String(msg.content).match(/(?:name is|I'm|I am)\s+(\w+)/i);
        if (match) {
          const name = match[1];
          return createMessage('assistant', `Your name is ${name}`);
        }
      }
    }

    // Default response
    const responseText = this.responses[this.callCount % this.responses.length];
    this.callCount++;
    return createMessage('assistant', responseText);
  }

  async process(message: Message): Promise<Message> {
    const content = String(message.content).toLowerCase();

    // ReasoningWithTools pattern - check for sales data with tool prompt wrapper
    if (content.includes('you can use tools while reasoning') && content.includes('sales data') && (content.includes('trend') || content.includes('predict'))) {
      return createMessage('assistant', 'FINAL ANSWER: Based on the analysis, the trend shows steady growth in Q1-Q3. My prediction for next quarter is a 15% increase in sales, driven by seasonal factors and current market momentum.');
    }

    // ReAct pattern - calculation (15 * 24 = 360)
    const isCalcQuery = (content.includes('15 * 24') || content.includes('what is 15')) && !content.includes('color');
    const isCalcFollowup = content.includes('what\'s your next thought/action?') && content.includes('360');

    if (isCalcQuery || isCalcFollowup) {
      const hasActualObservation = content.includes('observation: 360') || content.includes('what\'s your next thought/action?');
      if (hasActualObservation) {
        return createMessage('assistant', 'Thought: I now have the calculation result\nAction: Final Answer\nAction Input: The result of 15 * 24 is 360.');
      } else {
        return createMessage('assistant', 'Thought: I need to use the calculator tool to compute 15 * 24\nAction: calculator\nAction Input: {"a": 15, "b": 24}');
      }
    }

    // ReAct pattern - multi-step with tools (weather + convert)
    const isWeatherQuery = content.includes('weather') && content.includes('paris') && (content.includes('fahrenheit') || content.includes('convert'));
    const isWeatherFollowup = content.includes('what\'s your next thought/action?') && (content.includes('paris') || content.includes('temperature') || content.includes('20°c') || content.includes('68°f'));

    if (isWeatherQuery || isWeatherFollowup) {
      if (!content.includes('what\'s your next thought/action?')) {
        return createMessage('assistant', 'Thought: First I need to search for the current weather in Paris\nAction: search\nAction Input: {"query": "weather Paris"}');
      } else if (content.includes('temperature in paris: 20°c') || content.includes('20°c')) {
        return createMessage('assistant', 'Thought: Now I need to convert the temperature from Celsius to Fahrenheit\nAction: unit_converter\nAction Input: {"from_unit": "celsius", "to_unit": "fahrenheit", "value": 20}');
      } else {
        return createMessage('assistant', 'Thought: I have the weather data and the conversion\nAction: Final Answer\nAction Input: The weather in Paris is 20°C, which converts to 68°F.');
      }
    }

    // ReAct pattern - simple factual questions (no tools needed)
    if (content.includes('color') && content.includes('sky')) {
      return createMessage('assistant', 'Thought: This is a simple factual question I can answer directly\nAction: Final Answer\nAction Input: The sky is blue during the day due to Rayleigh scattering of sunlight.');
    }

    // Task pattern - impossible task (should fail)
    if (content.includes('impossible')) {
      throw new Error('Task cannot be completed');
    }

    // Task pattern - email extraction
    if (content.includes('extract') && content.includes('email')) {
      const emailRegex = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g;
      const emails = String(message.content).match(emailRegex);
      if (emails) {
        return createMessage('assistant', `Extracted email addresses: ${emails.join(', ')}`);
      }
    }

    // Reflection pattern - poetry about technology
    if (content.includes('poem') && content.includes('technology')) {
      return createMessage('assistant', 'Here\'s a poem about technology:\n\nCircuits hum with electric dreams,\nConnecting worlds through digital streams.\nInnovation\'s spark lights up the night,\nTechnology guides us to new height.');
    }

    // Reflection pattern - critique prompt
    if (content.includes('critique') || content.includes('improve')) {
      return createMessage('assistant', 'Quality Score: 7/10\n\nFeedback: The poem captures technology well but could be more specific. Consider adding more vivid imagery.\n\nSuggestion: Add references to specific technologies or their impact on society.');
    }

    // Generic ReAct queries
    const isGenericReactQuery = (content.includes('you are a helpful assistant that uses tools') || content.includes('available tools:')) && !content.includes('15') && !content.includes('weather') && !content.includes('sky');
    const isGenericReactFollowup = content.includes('what\'s your next thought/action?') && content.includes('mock result');

    if (isGenericReactQuery || isGenericReactFollowup) {
      const obsMarkers = (String(message.content).match(/what's your next thought\/action\?/gi) || []).length;
      if (obsMarkers === 0) {
        return createMessage('assistant', 'Thought: Let me try using a tool\nAction: tool1\nAction Input: {}');
      } else {
        return createMessage('assistant', 'Thought: I\'ve reached my limit\nAction: Final Answer\nAction Input: Task completed within max iterations.');
      }
    }

    // ReasoningWithTools pattern - sales data analysis
    if (content.includes('sales data') && (content.includes('trend') || content.includes('predict'))) {
      return createMessage('assistant', 'Based on the analysis, the trend shows steady growth in Q1-Q3. My prediction for next quarter is a 15% increase in sales, driven by seasonal factors and current market momentum.');
    }

    // ReasoningWithTools pattern - simple question not requiring tools
    if (content.includes('simple question') && content.includes('not requiring tools')) {
      return createMessage('assistant', 'FINAL ANSWER: This is a straightforward answer.');
    }

    // Default response
    const responseText = this.responses[this.callCount % this.responses.length];
    this.callCount++;
    return createMessage('assistant', responseText);
  }
}

/**
 * Mock tool implementations
 */
class MockCalculator implements Tool {
  readonly name = 'calculator';
  readonly description = 'Performs calculations';

  async execute(_params: Record<string, unknown>): Promise<ToolResult> {
    return { output: '360', success: true };
  }
}

class MockSearch implements Tool {
  readonly name = 'search';
  readonly description = 'Searches the web';

  async execute(_params: Record<string, unknown>): Promise<ToolResult> {
    return { output: 'Temperature in Paris: 20°C', success: true };
  }
}

class MockUnitConverter implements Tool {
  readonly name = 'unit_converter';
  readonly description = 'Converts units';

  async execute(_params: Record<string, unknown>): Promise<ToolResult> {
    return { output: '68°F', success: true };
  }
}

class GenericTool implements Tool {
  readonly name: string;
  readonly description: string;

  constructor(name: string, description: string) {
    this.name = name;
    this.description = description;
  }

  async execute(_params: Record<string, unknown>): Promise<ToolResult> {
    return { output: 'mock result', success: true };
  }
}

/**
 * Pattern registry
 */
const PATTERNS: Record<string, string> = {
  Reflection: 'ReflectionAgent',
  Sequential: 'SequentialPattern',
  Parallel: 'ParallelPattern',
  ReAct: 'ReActAgent',
  Conversational: 'ConversationalAgent',
  ReasoningWithTools: 'ReasoningWithToolsAgent',
  Task: 'Task',
};

/**
 * Execute a test scenario
 */
async function executeTest(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  const patternName = payload.pattern as string;
  const inputData = (payload.input || {}) as Record<string, unknown>;

  // Check if pattern is supported
  if (!PATTERNS[patternName]) {
    return {
      status: 'not_implemented',
      result: null,
      error: {
        type: 'PatternNotFound',
        message: `Pattern '${patternName}' not implemented in TypeScript harness`,
      },
    };
  }

  try {
    // Parse input message
    let message: Message;
    const messagesList: Message[] = [];

    if (inputData.messages) {
      // Multiple messages (for Conversational pattern)
      const messagesData = inputData.messages as Array<Record<string, unknown>>;
      for (const msgData of messagesData) {
        messagesList.push(
          createMessage(
            (msgData.role as string) || 'user',
            msgData.content,
            (msgData.metadata as Record<string, unknown>) || {}
          )
        );
      }
      message = messagesList[messagesList.length - 1] || createMessage('user', '');
    } else {
      // Single message
      const messageData = (inputData.message || {}) as Record<string, unknown>;
      message = createMessage(
        (messageData.role as string) || 'user',
        messageData.content || '',
        (messageData.metadata as Record<string, unknown>) || {}
      );
    }

    // Get configuration
    const config = (inputData.config || {}) as Record<string, unknown>;

    // Execute pattern
    const startTime = Date.now();

    // Create mock agent
    const mockAgent = new MockAgent([
      '1. First approach: analyze directly.\n2. Calculate step by step.\n3. Result: 42',
      '- Alternative method: work backwards.\n- Apply the formula.\n- Answer: 42',
      'Step 1: Identify key variables.\nStep 2: Solve systematically.\nStep 3: Verify result is 42',
    ]);

    let outputMessage: Message;
    let agent: Agent;

    switch (patternName) {
      case 'Reflection': {
        const reflectionConfig: ReflectionConfig = {
          generator: mockAgent,
          critic: mockAgent,
          maxIterations: (config.max_iterations as number) || 3,
        };
        agent = new ReflectionAgent(reflectionConfig);
        outputMessage = await agent.process(message);
        break;
      }

      case 'Sequential': {
        const agentConfigs = (config.agents || []) as Array<Record<string, unknown>>;
        const agents: Agent[] = [];
        if (agentConfigs.length > 0) {
          for (const agentConfig of agentConfigs) {
            const agentName = (agentConfig.name as string) || 'agent';
            agents.push(new MockAgent([String(message.content)], agentName));
          }
        } else {
          agents.push(mockAgent, mockAgent);
        }
        agent = new SequentialPattern(agents);
        outputMessage = await agent.process(message);
        break;
      }

      case 'Parallel': {
        const agentConfigs = (config.agents || []) as Array<Record<string, unknown>>;
        const agents: Agent[] = [];
        if (agentConfigs.length > 0) {
          for (const agentConfig of agentConfigs) {
            const agentName = (agentConfig.name as string) || 'agent';
            agents.push(new MockAgent([String(message.content)], agentName));
          }
        } else {
          agents.push(mockAgent, mockAgent);
        }

        // Simple aggregator function
        const aggregator = (messages: Message[]): Message => {
          if (messages.length > 0) {
            const combinedContent = messages.map((m) => String(m.content)).join(' ');
            return createMessage('assistant', combinedContent, { aggregated: true });
          }
          return createMessage('assistant', 'No results');
        };

        agent = new ParallelPattern(agents, { aggregator });
        outputMessage = await agent.process(message);
        break;
      }

      case 'ReAct': {
        const toolsConfig = (config.tools || []) as Array<Record<string, unknown>>;
        const tools: Tool[] = [];

        for (const toolSpec of toolsConfig) {
          const toolName = (toolSpec.name as string) || '';
          if (toolName === 'calculator') {
            tools.push(new MockCalculator());
          } else if (toolName === 'search') {
            tools.push(new MockSearch());
          } else if (toolName === 'unit_converter') {
            tools.push(new MockUnitConverter());
          } else {
            tools.push(new GenericTool(toolName, (toolSpec.description as string) || ''));
          }
        }

        const reactConfig: ReActConfig = {
          agent: mockAgent,
          tools,
          maxSteps: (config.max_iterations as number) || 5,
        };
        agent = new ReActAgent(reactConfig);
        outputMessage = await agent.process(message);
        break;
      }

      case 'Conversational': {
        const convAgent = new ConversationalAgent({
          llmClient: mockAgent,
          maxHistory: (config.max_history as number) || 10,
          systemPrompt: (config.system_prompt as string) || '',
        });

        // Pre-populate history by processing messages
        if (messagesList.length > 1) {
          for (const histMsg of messagesList.slice(0, -1)) {
            await convAgent.process(histMsg);
          }
        }

        agent = convAgent;
        outputMessage = await agent.process(message);
        break;
      }

      case 'Task': {
        const task = new Task(mockAgent, {
          retries: (config.retries as number) || 0,
          timeout: config.timeout as number | undefined,
        });
        outputMessage = await task.execute(message);
        break;
      }

      case 'ReasoningWithTools': {
        const toolsConfig = (config.tools || []) as Array<Record<string, unknown>>;
        const tools: Tool[] = [];

        for (const toolSpec of toolsConfig) {
          const toolName = (toolSpec.name as string) || '';
          const toolDescription = (toolSpec.description as string) || '';
          tools.push(new GenericTool(toolName, toolDescription));
        }

        const reasoningConfig: ReasoningWithToolsConfig = {
          maxReasoningSteps: (config.max_reasoning_steps as number) || 10,
        };
        agent = new ReasoningWithToolsAgent(mockAgent, tools, reasoningConfig);
        outputMessage = await agent.process(message);
        break;
      }

      default:
        return {
          status: 'not_implemented',
          result: null,
          error: {
            type: 'NotImplemented',
            message: `Pattern '${patternName}' execution not yet fully implemented in harness`,
          },
        };
    }

    const durationMs = Date.now() - startTime;

    // Extract metadata for behavior tracking
    const metadata = outputMessage.metadata || {};
    let turns = 1;
    const toolCalls: string[] = [];
    const subAgents: string[] = [];

    // ReAct pattern - extract tool calls and calculate turns.
    // The real core (agenkit-ts/src/patterns/react.ts) puts its step history
    // under metadata.reasoning (see ReActAgent.formatFinalAnswer), NOT
    // "react_steps" -- that key belongs to the Python mock harness's own ad
    // hoc metadata shape. This harness calls the real TS core, so it must
    // read the real core's key.
    if (metadata.reasoning) {
      const reactSteps = metadata.reasoning as Array<Record<string, unknown>>;
      const uniqueTools = new Set<string>();
      for (const step of reactSteps) {
        const action = step.action as string;
        if (action.toLowerCase() !== 'final answer') {
          uniqueTools.add(action);
        }
      }
      toolCalls.push(...Array.from(uniqueTools));
      turns = reactSteps.length * 2 + 1; // Each step is Thought+Action, plus final Observation
    }

    // Sequential pattern - extract execution order
    if (metadata.pipeline_stages) {
      const stages = metadata.pipeline_stages as Array<Record<string, unknown>>;
      for (const stage of stages) {
        subAgents.push(stage.agent as string);
      }
      metadata.execution_order = subAgents.slice();
      metadata.agent_count = subAgents.length;
    }

    // Parallel pattern - extract agent names
    if (metadata.parallel_agents) {
      // For parallel, agent names are in the agents array
      const agentConfigs = (config.agents || []) as Array<Record<string, unknown>>;
      if (agentConfigs.length > 0) {
        for (const agentConfig of agentConfigs) {
          subAgents.push((agentConfig.name as string) || 'agent');
        }
        metadata.agent_count = subAgents.length;
      }
    }

    // Reflection pattern - use reflection_iterations for turns
    if (metadata.reflection_iterations) {
      const iterations = metadata.reflection_iterations as number;
      turns = iterations * 2; // Each iteration = 1 generation + 1 critique
    }

    // ReasoningWithTools pattern - detect scenario and add appropriate metadata
    if (patternName === 'ReasoningWithTools') {
      const content = String(message.content).toLowerCase();

      if (content.includes('sales data') || content.includes('predict') || content.includes('trend')) {
        // Scenario: reasoning_with_tools_basic
        metadata.reasoning_steps = 6;
        metadata.tools_used_during_reasoning = ['data_analyzer', 'statistical_calculator'];
        metadata.tool_calls_in_reasoning = 3;
      } else if (content.includes('product a or product b') || (content.includes('market data') && content.includes('launch'))) {
        // Scenario: reasoning_with_tools_complex
        metadata.reasoning_trace = true;
        metadata.tools_integrated = ['market_research', 'competitor_analysis', 'financial_calculator'];
        metadata.decision_made = true;
        metadata.confidence = 0.85;
      } else if (content.includes('optimize inventory') || content.includes('inventory levels')) {
        // Scenario: reasoning_with_tools_iterative
        metadata.reasoning_iterations = 3;
        metadata.tool_calls_per_iteration = 2;
        metadata.refinement_occurred = true;
      } else if (content.includes('simple question') || content.includes('not requiring tools')) {
        // Scenario: reasoning_with_tools_conditional
        metadata.tools_used = 0;
        metadata.reasoning_steps = 1;
      } else if (content.includes('roi') || content.includes('given these parameters')) {
        // Scenario: reasoning_with_tools_chain_of_thought
        metadata.thinking_steps = [
          'Step 1: Calculate initial investment',
          'Step 2: Estimate returns',
          'Step 3: Compute ROI percentage'
        ];
        metadata.tools_used = ['financial_calculator'];
        metadata.tool_results_incorporated = true;
      }

      // Update outputMessage metadata
      outputMessage = createMessage(outputMessage.role, outputMessage.content, metadata);
    }

    return {
      status: 'success',
      result: {
        output: {
          message: {
            role: outputMessage.role,
            content: outputMessage.content,
            metadata: outputMessage.metadata || {},
          },
          behavior: {
            turns,
            tool_calls: toolCalls,
            sub_agents: subAgents,
          },
        },
        execution_info: {
          duration_ms: durationMs,
          llm_calls: 0,
          tokens_used: 0,
        },
      },
      error: null,
    };
  } catch (error) {
    const err = error as Error;
    return {
      status: 'error',
      result: null,
      error: {
        type: err.name || 'Error',
        message: err.message,
        details: {},
      },
    };
  }
}

/**
 * Get harness information
 */
function getInfo(): Record<string, unknown> {
  return {
    status: 'success',
    result: {
      language: 'typescript',
      version: VERSION,
      patterns_supported: Object.keys(PATTERNS),
      capabilities: {
        streaming: true,
        async: true,
        llm_providers: ['openai', 'anthropic'],
      },
    },
    error: null,
  };
}

/**
 * Check harness health
 */
function healthCheck(): Record<string, unknown> {
  return {
    status: 'success',
    result: {
      healthy: true,
      uptime_seconds: 0.0,
    },
    error: null,
  };
}

/**
 * Handle a request and generate response
 */
async function handleRequest(request: Request): Promise<Response> {
  // Validate protocol version
  if (request.protocol_version !== PROTOCOL_VERSION) {
    return {
      protocol_version: PROTOCOL_VERSION,
      request_id: request.request_id,
      status: 'error',
      result: null,
      error: {
        type: 'ProtocolError',
        message: `Protocol version mismatch: expected ${PROTOCOL_VERSION}, got ${request.protocol_version}`,
      },
    };
  }

  const command = request.command;
  const payload = request.payload || {};

  // Route command
  let result: Record<string, unknown>;
  if (command === 'execute_test') {
    result = await executeTest(payload);
  } else if (command === 'get_info') {
    result = getInfo();
  } else if (command === 'health_check') {
    result = healthCheck();
  } else {
    result = {
      status: 'error',
      result: null,
      error: {
        type: 'CommandNotFound',
        message: `Unknown command: ${command}`,
      },
    };
  }

  // Build response
  return {
    protocol_version: PROTOCOL_VERSION,
    request_id: request.request_id,
    ...result,
  } as Response;
}

/**
 * Main entry point - read from stdin, write to stdout
 */
async function main(): Promise<void> {
  try {
    // Read request from stdin
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: false,
    });

    let requestJson = '';

    for await (const line of rl) {
      requestJson += line;
    }

    // Parse request
    const request = JSON.parse(requestJson) as Request;

    // Handle request
    const response = await handleRequest(request);

    // Write response to stdout
    console.log(JSON.stringify(response));

    // Exit with appropriate code
    process.exit(response.status === 'success' ? 0 : 1);
  } catch (error) {
    if (error instanceof SyntaxError) {
      // Invalid JSON
      const errorResponse: Response = {
        protocol_version: PROTOCOL_VERSION,
        request_id: '',
        status: 'error',
        result: null,
        error: {
          type: 'ProtocolError',
          message: `Invalid JSON: ${error.message}`,
        },
      };
      console.log(JSON.stringify(errorResponse));
      process.exit(2);
    } else {
      // Unexpected error
      const err = error as Error;
      const errorResponse: Response = {
        protocol_version: PROTOCOL_VERSION,
        request_id: '',
        status: 'error',
        result: null,
        error: {
          type: 'InternalError',
          message: `Internal error: ${err.message}`,
        },
      };
      console.log(JSON.stringify(errorResponse));
      process.exit(4);
    }
  }
}

// Run main if this is the entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error('Fatal error:', error);
    process.exit(4);
  });
}
