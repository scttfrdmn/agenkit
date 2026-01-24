/**
 * AG-UI Core Adapter
 *
 * Wraps any Agenkit agent and translates Agent.process() calls into AG-UI event streams.
 * Enables agents to communicate with frontends using the AG-UI protocol.
 *
 * Reference: https://docs.ag-ui.com/protocol
 *
 * Example:
 *   import { AGUIAdapter } from './agui/adapter';
 *   import { TextMessageChunk } from './agui/events';
 *
 *   // Wrap any agent
 *   const agent = new MyAgent();
 *   const aguiAgent = new AGUIAdapter(agent);
 *
 *   // Process returns AG-UI events
 *   for await (const event of aguiAgent.streamEvents(message)) {
 *     if (event instanceof TextMessageChunk) {
 *       process.stdout.write(event.content);
 *     }
 *   }
 */

import { Agent, Message } from '../../core/interfaces.js';
import {
  AGUIEvent,
  ErrorEvent,
  HeartbeatEvent,
  MetadataEvent,
  TextMessageChunk,
  TextMessageComplete,
  TextMessageStart,
} from './events.js';
import { randomUUID } from 'crypto';

/**
 * Configuration for AG-UI adapter
 */
export interface AGUIAdapterConfig {
  /** Whether to emit heartbeat events */
  emitHeartbeats?: boolean;
  /** Seconds between heartbeat events (if enabled) */
  heartbeatInterval?: number;
  /** Custom agent name override */
  agentName?: string;
  /** Chunk size for streaming text (characters per chunk) */
  chunkSize?: number;
}

/**
 * Wraps an Agenkit agent to produce AG-UI protocol events.
 *
 * Converts standard Agent.process() calls into streaming AG-UI events
 * that can be consumed by frontends implementing the AG-UI protocol.
 *
 * Features:
 * - Automatic event generation from agent responses
 * - Streaming text message support
 * - Error handling with ErrorEvents
 * - Metadata emission for agent capabilities
 * - Message ID tracking for correlation
 *
 * Example:
 *   // Wrap any agent
 *   const agent = new MyReActAgent(llm, tools);
 *   const agui = new AGUIAdapter(agent);
 *
 *   // Stream events to frontend
 *   const message = { role: 'user', content: 'What\'s the weather?' };
 *   for await (const event of agui.streamEvents(message)) {
 *     // Send event to frontend via HTTP/SSE or WebSocket
 *     await sendToFrontend(event.toString());
 *   }
 */
export class AGUIAdapter {
  private readonly agent: Agent;
  private readonly agentName: string;
  private readonly emitHeartbeats: boolean;
  private readonly heartbeatInterval: number;
  private readonly chunkSize: number;
  private heartbeatSequence: number = 0;

  /**
   * Initialize AG-UI adapter for an agent.
   *
   * @param agent - The Agenkit agent to wrap
   * @param config - Optional configuration
   */
  constructor(agent: Agent, config: AGUIAdapterConfig = {}) {
    this.agent = agent;
    this.agentName = config.agentName || agent.name;
    this.emitHeartbeats = config.emitHeartbeats || false;
    this.heartbeatInterval = config.heartbeatInterval || 30.0;
    this.chunkSize = config.chunkSize || 50;
  }

  /**
   * Get the wrapped agent
   */
  getAgent(): Agent {
    return this.agent;
  }

  /**
   * Get the agent's name
   */
  getAgentName(): string {
    return this.agentName;
  }

  /**
   * Process message and stream AG-UI events.
   *
   * Converts agent's response into a stream of AG-UI events:
   * 1. MetadataEvent (optional) - Agent capabilities
   * 2. TextMessageStart - Beginning of response
   * 3. TextMessageChunk(s) - Streaming content
   * 4. TextMessageComplete - End of response
   *
   * @param message - Input message to process
   * @param messageId - Optional message ID (auto-generated if not provided)
   * @param emitMetadata - Whether to emit metadata event first
   * @yields AG-UI events representing the agent's response
   *
   * Example:
   *   for await (const event of adapter.streamEvents(userMessage)) {
   *     if (event instanceof TextMessageChunk) {
   *       process.stdout.write(event.content);
   *     } else if (event instanceof TextMessageComplete) {
   *       console.log(`\n[Finished: ${event.finish_reason}]`);
   *     }
   *   }
   */
  async *streamEvents(
    message: Message,
    messageId?: string,
    emitMetadata: boolean = true,
  ): AsyncGenerator<AGUIEvent, void, undefined> {
    const msgId = messageId || this.generateMessageId();

    // Emit metadata about agent capabilities
    if (emitMetadata) {
      yield this.createMetadataEvent();
    }

    // Emit text message start
    yield new TextMessageStart('assistant', msgId, {
      agent_name: this.agentName,
    });

    try {
      // Process message with agent
      const response = await this.agent.process(message);

      // Extract content
      const content =
        typeof response.content === 'string'
          ? response.content
          : JSON.stringify(response.content);

      // Stream content in chunks (simulating streaming)
      // In a real streaming implementation, this would yield as content arrives
      for (let i = 0; i < content.length; i += this.chunkSize) {
        const chunk = content.slice(i, i + this.chunkSize);
        yield new TextMessageChunk(chunk, msgId, {
          chunk_index: Math.floor(i / this.chunkSize),
        });
      }

      // Emit completion
      yield new TextMessageComplete(content, 'stop', msgId, {
        agent_name: this.agentName,
        response_metadata: response.metadata,
      });
    } catch (error) {
      // Convert exceptions to error events
      yield this.createErrorEvent(msgId, error as Error);

      // Also emit a completion with error
      yield new TextMessageComplete('', 'error', msgId, {
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  /**
   * Process message and return final result (non-streaming).
   *
   * Convenience method that consumes all events and returns the
   * final message. Use streamEvents() if you need streaming.
   *
   * @param message - Input message to process
   * @param messageId - Optional message ID
   * @returns Final response message
   */
  async process(message: Message, messageId?: string): Promise<Message> {
    let finalContent = '';
    let finalMetadata: Record<string, unknown> = {};

    // Consume all events
    for await (const event of this.streamEvents(message, messageId, false)) {
      if (event instanceof TextMessageComplete) {
        finalContent = event.content;
        finalMetadata = event.metadata;
      }
    }

    return {
      role: 'assistant',
      content: finalContent,
      metadata: finalMetadata,
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Generate a unique message ID
   */
  protected generateMessageId(): string {
    return `msg_${randomUUID()}`;
  }

  /**
   * Create a metadata event with agent capabilities
   */
  private createMetadataEvent(): MetadataEvent {
    const metadata: Record<string, any> = {
      agent_name: this.agentName,
      protocol: 'ag-ui',
      protocol_version: '1.0',
      capabilities: {
        streaming: true,
        tool_calls: false,
        interrupts: false,
        multimodal: false,
      },
    };

    // Add agent capabilities if available
    if (this.agent.capabilities) {
      metadata.agent_capabilities = this.agent.capabilities;
    }

    return new MetadataEvent(metadata);
  }

  /**
   * Create an error event from an exception
   */
  protected createErrorEvent(messageId: string, error: Error): ErrorEvent {
    return new ErrorEvent(
      'agent_error',
      error.message || 'Unknown error',
      true,
      {
        message_id: messageId,
        error_type: error.name,
        stack: error.stack,
      },
    );
  }

  /**
   * Create a heartbeat event
   */
  private createHeartbeatEvent(): HeartbeatEvent {
    this.heartbeatSequence++;
    return new HeartbeatEvent(this.heartbeatInterval * 1000, {
      sequence: this.heartbeatSequence,
      agent_name: this.agentName,
    });
  }
}

/**
 * Convenience function to wrap an agent with AG-UI adapter
 *
 * @param agent - Agent to wrap
 * @param config - Optional configuration
 * @returns Wrapped AG-UI adapter
 */
export function wrapAgentAsAGUI(
  agent: Agent,
  config?: AGUIAdapterConfig,
): AGUIAdapter {
  return new AGUIAdapter(agent, config);
}
