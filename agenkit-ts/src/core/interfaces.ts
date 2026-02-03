/**
 * Core interfaces for agenkit TypeScript implementation.
 *
 * Minimal, composable interfaces for AI agents with focus on:
 * - Simplicity: Few required methods
 * - Composability: Easy to wrap and extend
 * - Type safety: Full TypeScript support
 * - Performance: Minimal overhead
 */

import { IntrospectionResult } from './introspection.js';

/**
 * Universal message format for agent communication.
 *
 * Design decisions:
 * - role: Identifies message source ("user", "assistant", "system", "tool")
 * - content: Flexible type - string, object, array, or any serializable data
 * - metadata: Extension point for framework-specific data
 * - timestamp: ISO 8601 timestamp for ordering and debugging
 *
 * Usage:
 *   const msg: Message = {
 *     role: 'user',
 *     content: 'Hello, agent!',
 *   };
 *   const response = await agent.process(msg);
 */
export interface Message {
  /** Message source: "user", "assistant", "system", or "tool" */
  role: string;

  /** Message content - can be string, object, or any serializable data */
  content: unknown;

  /** Optional metadata for framework-specific data */
  metadata?: Record<string, unknown>;

  /** ISO 8601 timestamp - defaults to now if not provided */
  timestamp?: string;
}

/**
 * Result from tool execution.
 *
 * Contains the output from a tool call along with metadata about the execution.
 */
export interface ToolResult {
  /** Tool output - can be any serializable data */
  output: unknown;

  /** Whether the tool execution was successful */
  success: boolean;

  /** Optional error message if execution failed */
  error?: string;

  /** Optional metadata about the execution */
  metadata?: Record<string, unknown>;
}

/**
 * Tool interface - deterministic operations for agents.
 *
 * Design decisions:
 * - Async execute: Tools typically do I/O
 * - Flexible parameters: Tools accept any JSON-serializable input
 * - Rich metadata: name, description, and schema for LLM selection
 *
 * Usage:
 *   class SearchTool implements Tool {
 *     name = 'search';
 *     description = 'Search the web';
 *
 *     async execute(params: { query: string }): Promise<ToolResult> {
 *       const results = await searchAPI(params.query);
 *       return { output: results, success: true };
 *     }
 *   }
 */
export interface Tool {
  /** Tool identifier - must be unique within a tool set */
  readonly name: string;

  /** What this tool does - used by LLMs to decide when to call it */
  readonly description: string;

  /**
   * JSON schema for tool parameters.
   * Used by LLMs to understand how to call the tool.
   */
  parametersSchema?: Record<string, unknown>;

  /**
   * Execute the tool with given parameters.
   *
   * @param params Tool parameters (validated against schema if provided)
   * @param signal Optional AbortSignal for cancellation support
   * @returns Tool execution result
   */
  execute(params: Record<string, unknown>, signal?: AbortSignal): Promise<ToolResult>;
}

/**
 * Agent interface - minimal contract for agent communication.
 *
 * Design decisions:
 * - Only 2 required methods (name, process)
 * - Optional streaming support via processStream
 * - No state in interface (agents manage their own state)
 * - Async process (agents typically do I/O)
 *
 * Performance characteristics:
 * - Minimal overhead vs direct function call
 * - No dynamic dispatch on hot path
 * - Single allocation per message
 *
 * Usage:
 *   class SimpleAgent implements Agent {
 *     name = 'simple';
 *
 *     async process(message: Message): Promise<Message> {
 *       return {
 *         role: 'assistant',
 *         content: `Processed: ${message.content}`,
 *       };
 *     }
 *   }
 */
export interface Agent {
  /** Agent identifier */
  readonly name: string;

  /**
   * Process a message and return a response.
   *
   * @param message Input message
   * @returns Response message
   */
  process(message: Message): Promise<Message>;

  /**
   * Process a message with streaming response (optional).
   *
   * @param message Input message
   * @returns Async iterator of response chunks
   */
  processStream?(message: Message): AsyncGenerator<Message, void, undefined>;

  /**
   * What this agent can do (optional).
   *
   * @returns List of capabilities
   */
  readonly capabilities?: string[];

  /**
   * Examine agent's internal state, memory, and capabilities (optional).
   *
   * This is introspection (examining "what I know"), not reflection
   * (analyzing "how I did"). Returns a snapshot of current internal state.
   *
   * Introspection is useful for:
   * - Debugging: Examine agent state during development
   * - Monitoring: Track agent state in production
   * - Coordination: Agents can inspect each other's capabilities
   * - Testing: Verify agent state in tests
   * - Explainability: Understand what an agent "knows"
   *
   * Default implementation using createDefaultIntrospectionResult:
   *   introspect(): IntrospectionResult {
   *     return createDefaultIntrospectionResult(this);
   *   }
   *
   * Custom implementation with memory and state:
   *   introspect(): IntrospectionResult {
   *     return {
   *       timestamp: new Date().toISOString(),
   *       agentName: this.name,
   *       capabilities: this.capabilities || [],
   *       memoryState: {
   *         shortTermCount: this.memory.shortTerm.length,
   *         longTermCount: this.memory.longTerm.length,
   *       },
   *       internalState: {
   *         messageCount: this.messageCount,
   *         hasMemory: true,
   *       },
   *       metadata: {},
   *     };
   *   }
   *
   * @returns IntrospectionResult with current state information
   */
  introspect?(): IntrospectionResult;
}

/**
 * Helper function to create a Message with defaults.
 *
 * @param role Message role or message object
 * @param content Message content (if role is string)
 * @param metadata Optional metadata (if role is string)
 * @returns Complete message with timestamp
 */
export function createMessage(
  role: string | Partial<Message>,
  content?: unknown,
  metadata?: Record<string, unknown>,
): Message {
  // Object syntax: createMessage({ role, content })
  if (typeof role === 'object') {
    return {
      role: role.role || 'user',
      content: role.content,
      metadata: role.metadata || {},
      timestamp: role.timestamp || new Date().toISOString(),
    };
  }

  // Positional syntax: createMessage('user', 'Hello')
  return {
    role,
    content,
    metadata: metadata || {},
    timestamp: new Date().toISOString(),
  };
}

/**
 * Helper function to validate a message.
 *
 * Validates message structure and size limits:
 * - Role: non-empty, <= 20 characters, one of: user, assistant, system, tool, agent
 * - Content: <= 16MB
 * - Metadata: <= 100 keys, each key <= 50 characters, each value <= 16MB
 *
 * @param message Message to validate
 * @throws Error if message is invalid
 */
export function validateMessage(message: Message): void {
  // Role validation
  if (!message.role || typeof message.role !== 'string') {
    throw new Error('Message role must be a non-empty string');
  }

  if (message.role.length > 20) {
    throw new Error(
      `Message role exceeds maximum length of 20 characters (got ${message.role.length})`,
    );
  }

  // Validate role is one of the allowed values
  const allowedRoles = new Set(['user', 'assistant', 'system', 'tool', 'agent']);
  if (!allowedRoles.has(message.role)) {
    throw new Error(
      `Invalid message role: ${message.role}. Must be one of: ${Array.from(allowedRoles).join(', ')}`,
    );
  }

  // Content validation
  if (message.content === undefined || message.content === null) {
    throw new Error('Message content cannot be undefined or null');
  }

  // Content size validation - max 16MB
  const contentStr =
    typeof message.content === 'string'
      ? message.content
      : JSON.stringify(message.content);
  const contentSize = new TextEncoder().encode(contentStr).length;
  const maxContentSize = 16 * 1024 * 1024; // 16MB

  if (contentSize > maxContentSize) {
    throw new Error(
      `Message content exceeds maximum size of ${maxContentSize} bytes (got ${contentSize} bytes)`,
    );
  }

  // Metadata validation
  if (message.metadata) {
    const metadataKeys = Object.keys(message.metadata);

    // Max 100 keys
    if (metadataKeys.length > 100) {
      throw new Error(
        `Message metadata exceeds maximum of 100 keys (got ${metadataKeys.length})`,
      );
    }

    // Validate each key and value
    const maxKeyLength = 50;
    const maxValueSize = 16 * 1024 * 1024; // 16MB

    for (const [key, value] of Object.entries(message.metadata)) {
      // Key length validation
      if (key.length > maxKeyLength) {
        throw new Error(
          `Metadata key '${key.substring(0, 20)}...' exceeds maximum length of ${maxKeyLength} characters (got ${key.length})`,
        );
      }

      // Value size validation
      const valueStr = typeof value === 'string' ? value : JSON.stringify(value);
      const valueSize = new TextEncoder().encode(valueStr).length;

      if (valueSize > maxValueSize) {
        throw new Error(
          `Metadata value for key '${key}' exceeds maximum size of ${maxValueSize} bytes (got ${valueSize} bytes)`,
        );
      }
    }
  }
}

/**
 * Helper function to create a validated message.
 *
 * Creates a message and validates it against size and structure constraints.
 * This is a convenience function that combines createMessage() and validateMessage().
 *
 * @param role Message role
 * @param content Message content
 * @param metadata Optional metadata
 * @returns Validated message
 * @throws Error if message is invalid
 *
 * @example
 * ```typescript
 * const msg = createValidatedMessage('user', 'Hello, agent!', {
 *   sessionId: '123',
 * });
 * ```
 */
export function createValidatedMessage(
  role: string,
  content: unknown,
  metadata?: Record<string, unknown>,
): Message {
  const message = createMessage(role, content, metadata);
  validateMessage(message);
  return message;
}
