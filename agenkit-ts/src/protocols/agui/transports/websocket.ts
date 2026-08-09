/**
 * AG-UI WebSocket Transport
 *
 * Implements bidirectional WebSocket transport for AG-UI protocol.
 * Provides lower latency and bidirectional communication compared to HTTP/SSE.
 *
 * Reference: https://docs.ag-ui.com/protocol/transports
 *
 * Example (ws library):
 *   import { WebSocketServer } from 'ws';
 *   import { createWebSocketHandler } from './agui/transports/websocket';
 *
 *   const wss = new WebSocketServer({ port: 8080 });
 *   wss.on('connection', createWebSocketHandler(myAgent));
 *
 * Example (Express + ws):
 *   import express from 'express';
 *   import { WebSocketServer } from 'ws';
 *   import { AGUIWebSocketHandler } from './agui/transports/websocket';
 *
 *   const app = express();
 *   const server = app.listen(3000);
 *   const wss = new WebSocketServer({ server });
 *
 *   wss.on('connection', (ws) => {
 *     const handler = new AGUIWebSocketHandler(myAgent);
 *     handler.handle(ws);
 *   });
 */

import { Agent, Message } from '../../../core/interfaces.js';
import { AGUIAdapter } from '../adapter.js';
import {
  AGUIEvent,
  AGUI_METADATA_SCHEMA_VERSION,
  MetadataEvent,
  ErrorEvent,
  HeartbeatEvent,
} from '../events.js';

/**
 * WebSocket interface (compatible with ws library)
 */
export interface WebSocket {
  send(data: string): void;
  on(event: 'message' | 'close' | 'error', handler: (...args: any[]) => void): void;
  close(): void;
}

/**
 * Formats AG-UI events for WebSocket transmission.
 *
 * WebSocket messages are JSON objects with the event data.
 */
export class WebSocketMessageFormat {
  /**
   * Format AG-UI event as WebSocket message (JSON string).
   *
   * @param event - AG-UI event to format
   * @returns JSON string for WebSocket transmission
   */
  static formatEvent(event: AGUIEvent): string {
    const eventData = event.toJSON();
    return JSON.stringify(eventData);
  }

  /**
   * Parse WebSocket message (JSON string) to dictionary.
   *
   * @param message - JSON string from WebSocket
   * @returns Parsed object
   * @throws Error if message is not valid JSON
   */
  static parseMessage(message: string): Record<string, any> {
    try {
      const result = JSON.parse(message);
      return typeof result === 'object' && result !== null ? result : { data: result };
    } catch (error) {
      throw new Error(`Invalid JSON in WebSocket message: ${error}`);
    }
  }
}

/**
 * Configuration for WebSocket handler
 */
export interface WebSocketHandlerConfig {
  /** Optional agent name override */
  agentName?: string;
  /** Whether to send metadata event on connect */
  sendMetadata?: boolean;
  /** Seconds between heartbeat events (null = no heartbeats) */
  heartbeatInterval?: number | null;
  /** Maximum message size in bytes */
  maxMessageSize?: number;
}

/**
 * Manages streaming AG-UI events over WebSocket.
 *
 * Handles bidirectional communication, allowing both sending events
 * to the client and receiving messages from the client.
 */
export class AGUIWebSocketStream {
  private readonly adapter: AGUIAdapter;
  private readonly sendCallback: (message: string) => void;
  private readonly heartbeatInterval: number | null;

  /**
   * Initialize WebSocket stream.
   *
   * @param adapter - AG-UI adapter wrapping the agent
   * @param sendCallback - Function to send messages to WebSocket
   * @param heartbeatInterval - Seconds between heartbeat events (null = no heartbeats)
   */
  constructor(
    adapter: AGUIAdapter,
    sendCallback: (message: string) => void,
    heartbeatInterval: number | null = 30.0,
  ) {
    this.adapter = adapter;
    this.sendCallback = sendCallback;
    this.heartbeatInterval = heartbeatInterval;
  }

  /**
   * Stream AG-UI events for a message.
   *
   * @param message - Input message to process
   * @yields AG-UI events from agent's response
   */
  async *streamEvents(message: Message): AsyncGenerator<AGUIEvent, void, undefined> {
    for await (const event of this.adapter.streamEvents(message)) {
      yield event;
    }
  }

  /**
   * Send AG-UI event over WebSocket.
   *
   * @param event - Event to send
   */
  async sendEvent(event: AGUIEvent): Promise<void> {
    const formatted = WebSocketMessageFormat.formatEvent(event);
    this.sendCallback(formatted);
  }
}

/**
 * WebSocket handler for AG-UI protocol.
 *
 * Handles bidirectional WebSocket communication with automatic
 * event streaming and message processing.
 *
 * Usage:
 *   import { WebSocketServer } from 'ws';
 *   import { AGUIWebSocketHandler } from './agui/transports/websocket';
 *
 *   const wss = new WebSocketServer({ port: 8080 });
 *   wss.on('connection', (ws) => {
 *     const handler = new AGUIWebSocketHandler(myAgent);
 *     handler.handle(ws);
 *   });
 */
export class AGUIWebSocketHandler {
  private readonly agent: Agent;
  private readonly agentName?: string;
  private readonly sendMetadata: boolean;
  private readonly adapter: AGUIAdapter;
  private heartbeatInterval: number | null;
  private heartbeatTimer?: NodeJS.Timeout;

  /**
   * Initialize WebSocket handler.
   *
   * @param agent - Agent to serve over WebSocket
   * @param config - Optional configuration
   */
  constructor(agent: Agent, config: WebSocketHandlerConfig = {}) {
    this.agent = agent;
    this.agentName = config.agentName;
    this.sendMetadata = config.sendMetadata !== false;
    this.adapter = new AGUIAdapter(agent, { agentName: config.agentName });
    this.heartbeatInterval = config.heartbeatInterval !== undefined ? config.heartbeatInterval : 30;
  }

  /**
   * Handle WebSocket connection.
   *
   * @param ws - WebSocket connection
   */
  async handle(ws: WebSocket): Promise<void> {
    try {
      // Send metadata on connect
      if (this.sendMetadata) {
        const metadata = await this.createMetadataEvent();
        ws.send(WebSocketMessageFormat.formatEvent(metadata));
      }

      // Start heartbeat if configured
      if (this.heartbeatInterval && this.heartbeatInterval > 0) {
        this.startHeartbeat(ws);
      }

      // Handle incoming messages
      ws.on('message', async (data: any) => {
        try {
          const message = data.toString();
          await this.handleMessage(ws, message);
        } catch (error) {
          const errorEvent = new ErrorEvent(
            'message_error',
            error instanceof Error ? error.message : String(error),
            true,
          );
          ws.send(WebSocketMessageFormat.formatEvent(errorEvent));
        }
      });

      // Handle connection close
      ws.on('close', () => {
        this.stopHeartbeat();
      });

      // Handle errors
      ws.on('error', (error: Error) => {
        console.error('WebSocket error:', error);
        this.stopHeartbeat();
      });
    } catch (error) {
      console.error('Error handling WebSocket connection:', error);
      ws.close();
    }
  }

  /**
   * Handle incoming WebSocket message.
   *
   * @param ws - WebSocket connection
   * @param messageStr - Raw message string
   */
  private async handleMessage(ws: WebSocket, messageStr: string): Promise<void> {
    try {
      // Parse message
      const messageData = WebSocketMessageFormat.parseMessage(messageStr);

      // Extract message type
      const messageType = messageData.type || 'message';

      switch (messageType) {
        case 'message': {
          // Process user message
          const content = messageData.content || messageData.message || '';
          const message: Message = {
            role: 'user',
            content,
            timestamp: new Date().toISOString(),
          };

          // Stream response events
          for await (const event of this.adapter.streamEvents(message)) {
            ws.send(WebSocketMessageFormat.formatEvent(event));
          }
          break;
        }

        case 'ping': {
          // Respond with pong
          const pong = {
            type: 'pong',
            timestamp: new Date().toISOString(),
          };
          ws.send(JSON.stringify(pong));
          break;
        }

        default: {
          // Unknown message type
          const error = new ErrorEvent('unknown_message_type', `Unknown message type: ${messageType}`, true);
          ws.send(WebSocketMessageFormat.formatEvent(error));
        }
      }
    } catch (error) {
      const errorEvent = new ErrorEvent(
        'message_processing_error',
        error instanceof Error ? error.message : String(error),
        true,
      );
      ws.send(WebSocketMessageFormat.formatEvent(errorEvent));
    }
  }

  /**
   * Create metadata event with agent capabilities.
   */
  private async createMetadataEvent(): Promise<MetadataEvent> {
    const metadata: Record<string, any> = {
      agent_name: this.agentName || this.agent.name,
      protocol: 'ag-ui',
      protocol_version: AGUI_METADATA_SCHEMA_VERSION,
      transport: 'websocket',
      capabilities: {
        streaming: true,
        bidirectional: true,
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
   * Start sending periodic heartbeat events.
   */
  private startHeartbeat(ws: WebSocket): void {
    if (!this.heartbeatInterval || this.heartbeatInterval <= 0) {
      return;
    }

    this.heartbeatTimer = setInterval(() => {
      try {
        const heartbeat = new HeartbeatEvent(this.heartbeatInterval! * 1000);
        ws.send(WebSocketMessageFormat.formatEvent(heartbeat));
      } catch (error) {
        console.error('Error sending heartbeat:', error);
        this.stopHeartbeat();
      }
    }, this.heartbeatInterval * 1000);
  }

  /**
   * Stop sending heartbeat events.
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = undefined;
    }
  }
}

/**
 * Create a WebSocket connection handler function.
 *
 * Convenience function for creating WebSocket handlers with minimal boilerplate.
 *
 * @param agent - Agent to serve
 * @param config - Optional configuration
 * @returns WebSocket connection handler
 *
 * Example:
 *   import { WebSocketServer } from 'ws';
 *   import { createWebSocketHandler } from './agui/transports/websocket';
 *
 *   const wss = new WebSocketServer({ port: 8080 });
 *   wss.on('connection', createWebSocketHandler(myAgent, {
 *     heartbeatInterval: 30,
 *     sendMetadata: true
 *   }));
 */
export function createWebSocketHandler(
  agent: Agent,
  config: WebSocketHandlerConfig = {},
): (ws: WebSocket) => void {
  return (ws: WebSocket) => {
    const handler = new AGUIWebSocketHandler(agent, config);
    handler.handle(ws);
  };
}
