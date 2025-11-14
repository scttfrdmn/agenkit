/**
 * Local agent adapter - wraps functions as agents.
 *
 * Enables using simple TypeScript functions as agents without implementing
 * the full Agent interface.
 */

import { Agent, Message, createMessage, validateMessage } from '../core/interfaces';

/**
 * Function signature for local agent processing.
 */
export type ProcessFunction = (message: Message) => Promise<Message>;

/**
 * Function signature for streaming local agent processing.
 */
export type ProcessStreamFunction = (
  message: Message,
) => AsyncGenerator<Message, void, undefined>;

/**
 * Configuration for LocalAgent.
 */
export interface LocalAgentConfig {
  /** Agent name */
  name: string;

  /** Processing function */
  process: ProcessFunction;

  /** Optional streaming function */
  processStream?: ProcessStreamFunction;

  /** Optional capabilities */
  capabilities?: string[];
}

/**
 * LocalAgent wraps a function to implement the Agent interface.
 *
 * Features:
 * - Zero network overhead
 * - Full async/await support
 * - Optional streaming support
 * - Automatic message validation
 *
 * Usage:
 *   const agent = new LocalAgent({
 *     name: 'echo',
 *     process: async (msg) => ({
 *       role: 'assistant',
 *       content: `Echo: ${msg.content}`,
 *     }),
 *   });
 *
 *   const response = await agent.process({
 *     role: 'user',
 *     content: 'Hello!',
 *   });
 */
export class LocalAgent implements Agent {
  readonly name: string;
  readonly capabilities?: string[];

  private processFn: ProcessFunction;
  private processStreamFn?: ProcessStreamFunction;

  constructor(config: LocalAgentConfig) {
    this.name = config.name;
    this.processFn = config.process;
    this.processStreamFn = config.processStream;
    this.capabilities = config.capabilities;
  }

  /**
   * Process a message through the wrapped function.
   *
   * @param message Input message
   * @returns Response message
   */
  async process(message: Message): Promise<Message> {
    // Validate input
    validateMessage(message);

    // Add timestamp if missing
    if (!message.timestamp) {
      message.timestamp = new Date().toISOString();
    }

    // Process through function
    const response = await this.processFn(message);

    // Validate output
    validateMessage(response);

    // Add timestamp to response if missing
    if (!response.timestamp) {
      response.timestamp = new Date().toISOString();
    }

    return response;
  }

  /**
   * Process a message with streaming response.
   *
   * @param message Input message
   * @returns Async iterator of response chunks
   */
  async *processStream(message: Message): AsyncGenerator<Message, void, undefined> {
    if (!this.processStreamFn) {
      throw new Error(`Agent ${this.name} does not support streaming`);
    }

    // Validate input
    validateMessage(message);

    // Add timestamp if missing
    if (!message.timestamp) {
      message.timestamp = new Date().toISOString();
    }

    // Stream through function
    for await (const chunk of this.processStreamFn(message)) {
      // Validate each chunk
      validateMessage(chunk);

      // Add timestamp if missing
      if (!chunk.timestamp) {
        chunk.timestamp = new Date().toISOString();
      }

      yield chunk;
    }
  }
}

/**
 * Helper function to create a simple echo agent for testing.
 *
 * @param name Agent name
 * @returns Echo agent
 */
export function createEchoAgent(name: string = 'echo'): LocalAgent {
  return new LocalAgent({
    name,
    process: async (message: Message) =>
      createMessage('assistant', `Echo: ${message.content}`),
    capabilities: ['echo'],
  });
}

/**
 * Helper function to create a simple counter agent for testing.
 *
 * @param name Agent name
 * @returns Counter agent that increments a counter on each message
 */
export function createCounterAgent(name: string = 'counter'): LocalAgent {
  let count = 0;

  return new LocalAgent({
    name,
    process: async (message: Message) => {
      count++;
      return createMessage('assistant', `Message ${count}: ${message.content}`, {
        count,
      });
    },
    capabilities: ['counter'],
  });
}
