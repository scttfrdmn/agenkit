/**
 * Test helpers for pattern tests.
 *
 * Provides mock agents and utilities for comprehensive pattern testing.
 */

import { Agent, Message, createMessage } from '../../core/interfaces';

/**
 * Extended mock agent for flexible testing.
 *
 * Supports:
 * - Custom responses
 * - Error simulation
 * - Custom capabilities
 * - Custom process functions
 */
export class ExtendedMockAgent implements Agent {
  readonly name: string;
  private response: string;
  private error?: Error;
  private capabilitiesList: string[];
  private processFunc?: (message: Message) => Promise<Message>;

  constructor(config: {
    name: string;
    response?: string;
    error?: Error;
    capabilities?: string[];
    processFunc?: (message: Message) => Promise<Message>;
  }) {
    this.name = config.name;
    this.response = config.response || 'default response';
    this.error = config.error;
    this.capabilitiesList = config.capabilities || ['mock'];
    this.processFunc = config.processFunc;
  }

  get capabilities(): string[] {
    return this.capabilitiesList;
  }

  async process(message: Message): Promise<Message> {
    if (this.processFunc) {
      return this.processFunc(message);
    }
    if (this.error) {
      throw this.error;
    }
    return createMessage('assistant', this.response);
  }
}

/**
 * Creates a simple mock agent with fixed response.
 */
export function createMockAgent(name: string, response: string): Agent {
  return new ExtendedMockAgent({ name, response });
}

/**
 * Creates a mock agent that throws an error.
 */
export function createErrorAgent(name: string, errorMessage: string): Agent {
  return new ExtendedMockAgent({
    name,
    error: new Error(errorMessage),
  });
}

/**
 * Creates a mock agent that echoes input with a prefix.
 */
export function createEchoAgent(name: string, prefix: string): Agent {
  return new ExtendedMockAgent({
    name,
    processFunc: async (message: Message) => {
      return createMessage('assistant', `${prefix}${String(message.content)}`);
    },
  });
}

/**
 * Creates a mock agent that appends to input.
 */
export function createAppendAgent(name: string, suffix: string): Agent {
  return new ExtendedMockAgent({
    name,
    processFunc: async (message: Message) => {
      return createMessage('assistant', `${String(message.content)}${suffix}`);
    },
  });
}

/**
 * Creates a mock agent with custom metadata.
 */
export function createMetadataAgent(
  name: string,
  response: string,
  metadata: Record<string, unknown>,
): Agent {
  return new ExtendedMockAgent({
    name,
    processFunc: async () => {
      const msg = createMessage('assistant', response);
      msg.metadata = metadata;
      return msg;
    },
  });
}

/**
 * Creates a mock agent with confidence scoring.
 */
export function createConfidenceAgent(name: string, response: string, confidence: number): Agent {
  return createMetadataAgent(name, response, { confidence });
}

/**
 * Creates a mock agent that delays response.
 */
export function createDelayAgent(name: string, response: string, delayMs: number): Agent {
  return new ExtendedMockAgent({
    name,
    processFunc: async (message: Message) => {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
      return createMessage('assistant', response);
    },
  });
}

/**
 * Creates a mock agent that tracks call count.
 */
export class CallCountingAgent implements Agent {
  readonly name: string;
  callCount = 0;
  lastMessage?: Message;
  private response: string;

  constructor(name: string, response: string) {
    this.name = name;
    this.response = response;
  }

  get capabilities(): string[] {
    return ['mock', 'counting'];
  }

  async process(message: Message): Promise<Message> {
    this.callCount++;
    this.lastMessage = message;
    return createMessage('assistant', this.response);
  }

  reset(): void {
    this.callCount = 0;
    this.lastMessage = undefined;
  }
}

/**
 * Creates a mock agent that fails N times before succeeding.
 */
export class FlakyAgent implements Agent {
  readonly name: string;
  private failuresLeft: number;
  private response: string;
  private errorMessage: string;
  callCount = 0;

  constructor(name: string, response: string, failureCount: number, errorMessage: string) {
    this.name = name;
    this.response = response;
    this.failuresLeft = failureCount;
    this.errorMessage = errorMessage;
  }

  get capabilities(): string[] {
    return ['mock', 'flaky'];
  }

  async process(message: Message): Promise<Message> {
    this.callCount++;
    if (this.failuresLeft > 0) {
      this.failuresLeft--;
      throw new Error(this.errorMessage);
    }
    return createMessage('assistant', this.response);
  }

  reset(): void {
    this.callCount = 0;
  }
}

/**
 * Validates that a message has expected structure.
 */
export function validateMessage(message: Message): void {
  if (!message) {
    throw new Error('Message is null or undefined');
  }
  if (!message.role) {
    throw new Error('Message missing role');
  }
  if (message.content === undefined) {
    throw new Error('Message missing content');
  }
}

/**
 * Extracts metadata value safely.
 */
export function getMetadata(message: Message, key: string): unknown {
  return message.metadata?.[key];
}

/**
 * Checks if metadata contains key.
 */
export function hasMetadata(message: Message, key: string): boolean {
  return message.metadata !== undefined && key in message.metadata;
}
