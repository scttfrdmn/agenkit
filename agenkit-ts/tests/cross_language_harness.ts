#!/usr/bin/env node
/**
 * TypeScript test harness for cross-language equivalence testing.
 *
 * Implements the JSON protocol for executing pattern tests.
 */

const PROTOCOL_VERSION = "1.0";
const VERSION = "0.2.0";

// Exit codes
const EXIT_SUCCESS = 0;
const EXIT_ERROR = 1;
const EXIT_PROTOCOL_ERROR = 2;
const EXIT_TIMEOUT = 3;
const EXIT_INTERNAL_ERROR = 4;

// Protocol message structures
interface Request {
  protocol_version: string;
  request_id: string;
  command: string;
  payload: Record<string, any>;
}

interface ProtocolResponse {
  protocol_version: string;
  request_id: string;
  status: string;
  result?: Record<string, any>;
  error?: ErrorInfo;
}

interface ErrorInfo {
  type: string;
  message: string;
  details?: Record<string, any>;
  stack_trace?: string;
}

interface Message {
  role: string;
  content: string;
  metadata?: Record<string, any>;
}

interface BehaviorData {
  turns?: number;
  tool_calls?: string[];
  sub_agents?: string[];
  iterations?: number;
}

interface ExecutionInfo {
  duration_ms: number;
  llm_calls?: number;
  tokens_used?: number;
  memory_bytes?: number;
}

// Pattern registry
const supportedPatterns: Record<string, boolean> = {
  reflection: true,
  sequential: true,
  parallel: true,
  router: true,
  react: true,
  conversational: true,
  agents_as_tools: true,
  fallback: true,
  supervisor: true,
  planning: true,
  task: true,
  collaborative: true,
  human_in_loop: true,
  autonomous: true,
  multiagent: true,
  orchestration: true,
  memory: true,
  reasoning_with_tools: true,
};

/**
 * Read stdin asynchronously
 */
function readStdin(): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    process.stdin.on('data', (chunk) => chunks.push(chunk));
    process.stdin.on('end', () => resolve(Buffer.concat(chunks).toString('utf-8')));
    process.stdin.on('error', reject);
  });
}

/**
 * Write response to stdout and exit
 */
function writeResponse(response: ProtocolResponse, exitCode: number = EXIT_SUCCESS): never {
  console.log(JSON.stringify(response));
  process.exit(exitCode);
}

/**
 * Write error response and exit
 */
function writeErrorResponse(
  requestId: string,
  errorType: string,
  message: string,
  exitCode: number = EXIT_ERROR
): never {
  const response: ProtocolResponse = {
    protocol_version: PROTOCOL_VERSION,
    request_id: requestId,
    status: 'error',
    error: {
      type: errorType,
      message: message,
    },
  };
  writeResponse(response, exitCode);
}

/**
 * Handle incoming request
 */
function handleRequest(request: Request): ProtocolResponse {
  // Validate protocol version
  if (request.protocol_version !== PROTOCOL_VERSION) {
    return {
      protocol_version: PROTOCOL_VERSION,
      request_id: request.request_id,
      status: 'error',
      error: {
        type: 'ProtocolError',
        message: `Protocol version mismatch: expected ${PROTOCOL_VERSION}, got ${request.protocol_version}`,
      },
    };
  }

  // Route command
  let result: Record<string, any> | undefined;
  let error: ErrorInfo | undefined;

  try {
    switch (request.command) {
      case 'execute_test':
        result = executeTest(request.payload);
        break;
      case 'get_info':
        result = getInfo();
        break;
      case 'health_check':
        result = healthCheck();
        break;
      default:
        error = {
          type: 'CommandNotFound',
          message: `Unknown command: ${request.command}`,
        };
    }
  } catch (e) {
    error = {
      type: e instanceof Error ? e.constructor.name : 'Error',
      message: e instanceof Error ? e.message : String(e),
      stack_trace: e instanceof Error ? e.stack : undefined,
    };
  }

  // Build response
  const response: ProtocolResponse = {
    protocol_version: PROTOCOL_VERSION,
    request_id: request.request_id,
    status: error ? 'error' : 'success',
  };

  if (error) {
    response.error = error;
  } else {
    response.result = result;
  }

  return response;
}

/**
 * Execute a test scenario
 */
function executeTest(payload: Record<string, any>): Record<string, any> {
  // Parse test payload
  const pattern = payload.pattern;
  if (typeof pattern !== 'string') {
    throw new Error('Pattern name is required');
  }

  // Normalize pattern name to lowercase for case-insensitive matching
  const patternLower = pattern.toLowerCase();

  const scenarioId = payload.scenario_id;
  if (typeof scenarioId !== 'string') {
    throw new Error('Scenario ID is required');
  }

  const input = payload.input;
  if (!input || typeof input !== 'object') {
    throw new Error('Input is required');
  }

  // Check if pattern is supported
  if (!supportedPatterns[patternLower]) {
    throw new Error(`Pattern '${pattern}' not implemented in TypeScript harness`);
  }

  // Parse input message
  const messageData = input.message;
  if (!messageData || typeof messageData !== 'object') {
    throw new Error('Input message is required');
  }

  const message: Message = {
    role: messageData.role || 'user',
    content: messageData.content || '',
    metadata: messageData.metadata || {},
  };

  // Get configuration
  const config = input.config || {};

  // Execute pattern
  const startTime = Date.now();
  const outputMessage = executePattern(patternLower, message, config);
  const duration = Date.now() - startTime;

  // Build execution info
  const executionInfo: ExecutionInfo = {
    duration_ms: duration,
    llm_calls: 0, // TODO: Track actual LLM calls
    tokens_used: 0, // TODO: Track actual token usage
  };

  // Return result
  return {
    output: {
      message: {
        role: outputMessage.role,
        content: outputMessage.content,
        metadata: outputMessage.metadata,
      },
      behavior: {
        turns: 1, // TODO: Track actual turns
        tool_calls: [],
        sub_agents: [],
      },
    },
    execution_info: executionInfo,
  };
}

/**
 * Execute a pattern with given message and config
 */
function executePattern(
  patternName: string,
  message: Message,
  config: Record<string, any>
): Message {
  // This is a simplified implementation that returns mock responses
  // TODO: Implement actual pattern execution based on patternName and config

  switch (patternName) {
    case 'reflection':
      return executeReflection(message, config);
    case 'sequential':
      return executeSequential(message, config);
    case 'parallel':
      return executeParallel(message, config);
    default:
      // Mock response for now
      return {
        role: 'assistant',
        content: `Mock response for ${patternName} pattern`,
        metadata: {
          pattern: patternName,
          mock: true,
        },
      };
  }
}

/**
 * Execute reflection pattern
 */
function executeReflection(message: Message, config: Record<string, any>): Message {
  // TODO: Implement actual reflection pattern execution
  // For now, return a mock response

  const maxIterations = config.max_iterations || 3;

  return {
    role: 'assistant',
    content: `Reflected response to: ${message.content}`,
    metadata: {
      iterations: 1,
      improved: true,
      max_iterations: maxIterations,
    },
  };
}

/**
 * Execute sequential pattern
 */
function executeSequential(message: Message, config: Record<string, any>): Message {
  // TODO: Implement actual sequential pattern execution
  const agents = config.agents || [];
  const agentCount = agents.length;

  return {
    role: 'assistant',
    content: `Sequential result: ${message.content}`,
    metadata: {
      agent_count: agentCount,
    },
  };
}

/**
 * Execute parallel pattern
 */
function executeParallel(message: Message, config: Record<string, any>): Message {
  // TODO: Implement actual parallel pattern execution
  const agents = config.agents || [];
  const agentCount = agents.length;

  return {
    role: 'assistant',
    content: `Parallel result: ${message.content}`,
    metadata: {
      agent_count: agentCount,
    },
  };
}

/**
 * Get harness information
 */
function getInfo(): Record<string, any> {
  return {
    language: 'typescript',
    version: VERSION,
    patterns_supported: Object.keys(supportedPatterns),
    capabilities: {
      streaming: true,
      async: true,
      llm_providers: ['openai', 'anthropic'],
    },
  };
}

/**
 * Check harness health
 */
function healthCheck(): Record<string, any> {
  return {
    healthy: true,
    uptime_seconds: 0.0, // Stateless harness
  };
}

/**
 * Main entry point
 */
async function main() {
  try {
    // Read request from stdin
    const requestData = await readStdin();

    // Parse request
    let request: Request;
    try {
      request = JSON.parse(requestData);
    } catch (e) {
      writeErrorResponse(
        '',
        'ProtocolError',
        `Invalid JSON: ${e instanceof Error ? e.message : String(e)}`,
        EXIT_PROTOCOL_ERROR
      );
    }

    // Handle request
    const response = handleRequest(request);

    // Write response
    const exitCode = response.status === 'success' ? EXIT_SUCCESS : EXIT_ERROR;
    writeResponse(response, exitCode);
  } catch (e) {
    writeErrorResponse(
      '',
      'InternalError',
      `Internal error: ${e instanceof Error ? e.message : String(e)}`,
      EXIT_INTERNAL_ERROR
    );
  }
}

// Run main
main();
