/**
 * AG-UI HTTP/SSE Transport
 *
 * Implements Server-Sent Events (SSE) transport for AG-UI protocol over HTTP.
 * Provides Express-compatible handlers for serving AG-UI event streams.
 *
 * Reference: https://docs.ag-ui.com/protocol/transports
 *
 * Example (Express):
 *   import express from 'express';
 *   import { createSSEHandler } from './agui/transports/http';
 *
 *   const app = express();
 *   app.post('/chat', createSSEHandler(myAgent));
 *
 * Example (Manual):
 *   import { AGUISSEStream } from './agui/transports/http';
 *
 *   const stream = new AGUISSEStream(adapter, message);
 *   for await (const chunk of stream) {
 *     res.write(chunk);
 *   }
 */

import { Agent, Message } from '../../../core/interfaces.js';
import { AGUIAdapter } from '../adapter.js';
import { AGUIEvent } from '../events.js';

/**
 * Formats AG-UI events as Server-Sent Events (SSE).
 *
 * SSE format:
 *   data: {"event_type": "text_message_chunk", ...}\n\n
 *
 * With event name:
 *   event: text_message_chunk
 *   data: {...}\n\n
 */
export class SSEFormatter {
  /**
   * Format AG-UI event as SSE message.
   *
   * @param event - AG-UI event to format
   * @param includeEventName - Whether to include "event:" line
   * @returns SSE-formatted string
   *
   * Example:
   *   const event = new TextMessageChunk("Hello");
   *   const sse = SSEFormatter.formatEvent(event);
   *   // => 'data: {"event_type": "text_message_chunk", "content": "Hello", ...}\n\n'
   */
  static formatEvent(event: AGUIEvent, includeEventName: boolean = false): string {
    const eventData = event.toJSON();
    const eventJson = JSON.stringify(eventData);

    if (includeEventName) {
      const eventName = event.event_type;
      return `event: ${eventName}\ndata: ${eventJson}\n\n`;
    } else {
      return `data: ${eventJson}\n\n`;
    }
  }

  /**
   * Format SSE comment (keeps connection alive).
   *
   * @param comment - Comment text
   * @returns SSE comment line
   */
  static formatComment(comment: string): string {
    return `: ${comment}\n\n`;
  }

  /**
   * Format SSE retry directive.
   *
   * @param milliseconds - Reconnection time in milliseconds
   * @returns SSE retry line
   */
  static formatRetry(milliseconds: number): string {
    return `retry: ${milliseconds}\n\n`;
  }
}

/**
 * Configuration for SSE stream
 */
export interface SSEStreamConfig {
  /** Whether to include "event:" lines in SSE output */
  includeEventNames?: boolean;
  /** Seconds between ping comments (null = no pings) */
  pingInterval?: number | null;
}

/**
 * Async iterator that produces SSE-formatted AG-UI events.
 *
 * Can be used directly with Express StreamingResponse or Node.js Response.
 *
 * Example:
 *   const stream = new AGUISSEStream(adapter, message);
 *   for await (const chunk of stream) {
 *     res.write(chunk);
 *   }
 */
export class AGUISSEStream {
  private readonly adapter: AGUIAdapter;
  private readonly message: Message;
  private readonly includeEventNames: boolean;
  private readonly pingInterval: number | null;

  /**
   * Initialize SSE stream.
   *
   * @param adapter - AG-UI adapter wrapping the agent
   * @param message - Input message to process
   * @param config - Optional stream configuration
   */
  constructor(adapter: AGUIAdapter, message: Message, config: SSEStreamConfig = {}) {
    this.adapter = adapter;
    this.message = message;
    this.includeEventNames = config.includeEventNames || false;
    this.pingInterval = config.pingInterval !== undefined ? config.pingInterval : null;
  }

  /**
   * Stream SSE-formatted events
   */
  async *[Symbol.asyncIterator](): AsyncGenerator<string, void, undefined> {
    try {
      // Stream events from adapter
      for await (const event of this.adapter.streamEvents(this.message)) {
        yield SSEFormatter.formatEvent(event, this.includeEventNames);
      }

      // Send final comment to indicate completion
      yield SSEFormatter.formatComment('stream_complete');
    } catch (error) {
      // Send error as SSE comment
      const errorMsg = error instanceof Error ? error.message : String(error);
      yield SSEFormatter.formatComment(`error: ${errorMsg}`);
      throw error;
    }
  }
}

/**
 * Request handler interface for Express/Node.js
 */
export type RequestHandler = (req: any, res: any) => Promise<void>;

/**
 * Configuration for SSE handler
 */
export interface SSEHandlerConfig {
  /** Optional agent name override */
  agentName?: string;
  /** Whether to include "event:" lines in SSE output */
  includeEventNames?: boolean;
  /** Allowed CORS origins (e.g., ['http://localhost:3000']) */
  corsOrigins?: string[];
  /** Request timeout in milliseconds */
  timeout?: number;
  /** Seconds between ping comments */
  pingInterval?: number;
}

/**
 * Create an Express/Node.js-compatible SSE handler.
 *
 * The handler expects a POST request with JSON body containing:
 *   { "message": "user message text", "message_id": "optional-id" }
 *
 * Returns a streaming SSE response with AG-UI events.
 *
 * @param agent - Agent to serve
 * @param config - Optional handler configuration
 * @returns Express-compatible request handler
 *
 * Example (Express):
 *   import express from 'express';
 *   import { createSSEHandler } from './agui/transports/http';
 *
 *   const app = express();
 *   app.use(express.json());
 *   app.post('/chat', createSSEHandler(myAgent, {
 *     corsOrigins: ['http://localhost:3000'],
 *     timeout: 30000
 *   }));
 *
 * Example (cURL test):
 *   curl -X POST http://localhost:3000/chat \
 *     -H "Content-Type: application/json" \
 *     -d '{"message": "Hello!"}' \
 *     -N
 */
export function createSSEHandler(agent: Agent, config: SSEHandlerConfig = {}): RequestHandler {
  const adapter = new AGUIAdapter(agent, { agentName: config.agentName });

  return async (req: any, res: any): Promise<void> => {
    // Set SSE headers
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    // Set CORS headers if configured
    if (config.corsOrigins && config.corsOrigins.length > 0) {
      const origin = req.headers.origin || req.headers.referer;
      if (config.corsOrigins.includes('*') || config.corsOrigins.includes(origin)) {
        res.setHeader('Access-Control-Allow-Origin', origin || '*');
        res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
      }
    }

    // Handle OPTIONS preflight
    if (req.method === 'OPTIONS') {
      res.status(204).end();
      return;
    }

    // Set timeout if configured
    if (config.timeout) {
      req.setTimeout(config.timeout);
      res.setTimeout(config.timeout);
    }

    try {
      // Parse request body
      const body = req.body || {};
      const messageContent = body.message || '';
      const messageId = body.message_id;

      // Create message
      const message: Message = {
        role: 'user',
        content: messageContent,
        timestamp: new Date().toISOString(),
      };

      // Create SSE stream
      const stream = new AGUISSEStream(adapter, message, {
        includeEventNames: config.includeEventNames,
        pingInterval: config.pingInterval,
      });

      // Stream events to response
      for await (const chunk of stream) {
        res.write(chunk);

        // Flush if available (helps with some Node.js versions)
        if (typeof (res as any).flush === 'function') {
          (res as any).flush();
        }
      }

      // End response
      res.end();
    } catch (error) {
      // Send error event
      const errorMsg = error instanceof Error ? error.message : String(error);
      res.write(SSEFormatter.formatComment(`error: ${errorMsg}`));
      res.end();
    }
  };
}

/**
 * Create SSE response iterator from agent and message.
 *
 * Convenience function for quickly creating SSE streams without
 * creating an adapter explicitly.
 *
 * @param agent - Agent to wrap
 * @param message - Message to process
 * @param agentName - Optional agent name
 * @param includeEventNames - Whether to include "event:" lines
 * @returns Async iterator yielding SSE-formatted strings
 *
 * Example:
 *   const iterator = createSSEResponseIterator(myAgent, message);
 *   for await (const chunk of iterator) {
 *     res.write(chunk);
 *   }
 */
export function createSSEResponseIterator(
  agent: Agent,
  message: Message,
  agentName?: string,
  includeEventNames: boolean = false,
): AsyncIterableIterator<string> {
  const adapter = new AGUIAdapter(agent, { agentName });
  const stream = new AGUISSEStream(adapter, message, { includeEventNames });
  return stream[Symbol.asyncIterator]();
}

/**
 * Express middleware for handling SSE connections with keep-alive pings.
 *
 * Use this before your SSE route to ensure connections stay alive.
 *
 * @param pingInterval - Seconds between ping comments (default: 15)
 * @returns Express middleware function
 *
 * Example:
 *   app.use('/chat', sseKeepAlive(15));
 *   app.post('/chat', createSSEHandler(myAgent));
 */
export function sseKeepAlive(pingInterval: number = 15): RequestHandler {
  return async (req: any, res: any, next?: any): Promise<void> => {
    if (req.headers.accept?.includes('text/event-stream')) {
      const intervalId = setInterval(() => {
        res.write(SSEFormatter.formatComment('ping'));
      }, pingInterval * 1000);

      // Clean up on connection close
      res.on('close', () => {
        clearInterval(intervalId);
      });
    }

    if (next) {
      next();
    }
  };
}
