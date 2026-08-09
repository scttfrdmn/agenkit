/**
 * Comprehensive tests for AG-UI adapter.
 *
 * Tests cover:
 * - Adapter construction
 * - Event streaming
 * - Message processing
 * - Metadata emission
 * - Error handling
 * - Chunking behavior
 */

import { describe, it, expect } from 'vitest';
import { Agent, Message } from '../../../core/interfaces';
import {
  AGUIAdapter,
  AGUI_METADATA_SCHEMA_VERSION,
  TextMessageStart,
  TextMessageChunk,
  TextMessageComplete,
  MetadataEvent,
  ErrorEvent,
} from '../index';

// Mock agent for testing
class MockAgent implements Agent {
  readonly name = 'MockAgent';
  readonly capabilities = ['test'];

  constructor(
    private response: string,
    private confidence: number = 0.9,
  ) {}

  async process(message: Message): Promise<Message> {
    return {
      role: 'assistant',
      content: this.response,
      metadata: {
        confidence: this.confidence,
        processing_time: 10,
      },
      timestamp: new Date().toISOString(),
    };
  }
}

// Error agent for testing
class ErrorAgent implements Agent {
  readonly name = 'ErrorAgent';
  readonly capabilities = ['test'];

  async process(_message: Message): Promise<Message> {
    throw new Error('Processing failed');
  }
}

describe('AGUIAdapter', () => {
  describe('Constructor', () => {
    it('should create adapter with agent', () => {
      const agent = new MockAgent('test');
      const adapter = new AGUIAdapter(agent);

      expect(adapter).toBeDefined();
    });

    it('should use custom agent name', () => {
      const agent = new MockAgent('test');
      const adapter = new AGUIAdapter(agent, {
        agentName: 'CustomAgent',
      });

      expect(adapter).toBeDefined();
    });

    it('should use custom chunk size', () => {
      const agent = new MockAgent('test');
      const adapter = new AGUIAdapter(agent, {
        chunkSize: 10,
      });

      expect(adapter).toBeDefined();
    });
  });

  describe('Event streaming', () => {
    it('should emit metadata event first', async () => {
      const agent = new MockAgent('Hello');
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, true)) {
        events.push(event);
      }

      expect(events[0]).toBeInstanceOf(MetadataEvent);
      const metadata = events[0] as MetadataEvent;
      expect(metadata.data.agent_name).toBe('MockAgent');
    });

    it('should emit TextMessageStart event', async () => {
      const agent = new MockAgent('Hello');
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, 'msg_123', false)) {
        events.push(event);
      }

      expect(events[0]).toBeInstanceOf(TextMessageStart);
      const start = events[0] as TextMessageStart;
      expect(start.role).toBe('assistant');
      expect(start.message_id).toBe('msg_123');
    });

    it('should emit TextMessageChunk events', async () => {
      const agent = new MockAgent('Hello');
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        if (event instanceof TextMessageChunk) {
          events.push(event);
        }
      }

      expect(events.length).toBeGreaterThan(0);
      expect(events[0]).toBeInstanceOf(TextMessageChunk);
    });

    it('should emit TextMessageComplete event last', async () => {
      const agent = new MockAgent('Hello');
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      const lastEvent = events[events.length - 1];
      expect(lastEvent).toBeInstanceOf(TextMessageComplete);
      const complete = lastEvent as TextMessageComplete;
      expect(complete.content).toBe('Hello');
      expect(complete.finish_reason).toBe('stop');
    });

    it('should skip metadata when emitMetadata is false', async () => {
      const agent = new MockAgent('Hello');
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      const hasMetadata = events.some((e) => e instanceof MetadataEvent);
      expect(hasMetadata).toBe(false);
    });
  });

  describe('Chunking behavior', () => {
    it('should chunk long content', async () => {
      const longContent = 'a'.repeat(1000);
      const agent = new MockAgent(longContent);
      const adapter = new AGUIAdapter(agent, { chunkSize: 100 });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const chunks = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        if (event instanceof TextMessageChunk) {
          chunks.push(event);
        }
      }

      expect(chunks.length).toBe(10); // 1000 / 100
      expect(chunks[0].content).toHaveLength(100);
    });

    it('should handle content shorter than chunk size', async () => {
      const agent = new MockAgent('Hi');
      const adapter = new AGUIAdapter(agent, { chunkSize: 100 });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const chunks = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        if (event instanceof TextMessageChunk) {
          chunks.push(event);
        }
      }

      expect(chunks.length).toBe(1);
      expect(chunks[0].content).toBe('Hi');
    });

    it('should include chunk index in metadata', async () => {
      const agent = new MockAgent('Hello World');
      const adapter = new AGUIAdapter(agent, { chunkSize: 5 });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const chunks = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        if (event instanceof TextMessageChunk) {
          chunks.push(event);
        }
      }

      expect(chunks[0].metadata?.chunk_index).toBe(0);
      expect(chunks[1].metadata?.chunk_index).toBe(1);
    });
  });

  describe('Error handling', () => {
    it('should emit error event on agent failure', async () => {
      const agent = new ErrorAgent();
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      const errorEvent = events.find((e) => e instanceof ErrorEvent);
      expect(errorEvent).toBeDefined();
      expect((errorEvent as ErrorEvent).error_message).toContain('Processing failed');
    });

    it('should emit complete event with error finish reason', async () => {
      const agent = new ErrorAgent();
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      const completeEvent = events.find((e) => e instanceof TextMessageComplete);
      expect(completeEvent).toBeDefined();
      expect((completeEvent as TextMessageComplete).finish_reason).toBe('error');
    });
  });

  describe('Metadata', () => {
    it('should include agent capabilities in metadata', async () => {
      const agent = new MockAgent('test');
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, true)) {
        if (event instanceof MetadataEvent) {
          events.push(event);
        }
      }

      const metadata = events[0] as MetadataEvent;
      expect(metadata.data.agent_capabilities).toEqual(['test']);
    });

    it('should include protocol info in metadata', async () => {
      const agent = new MockAgent('test');
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, true)) {
        if (event instanceof MetadataEvent) {
          events.push(event);
        }
      }

      const metadata = events[0] as MetadataEvent;
      expect(metadata.data.protocol).toBe('ag-ui');
      expect(metadata.data.protocol_version).toBe(AGUI_METADATA_SCHEMA_VERSION);
    });
  });

  describe('Message content handling', () => {
    it('should handle string content', async () => {
      const agent = new MockAgent('Hello');
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        if (event instanceof TextMessageComplete) {
          events.push(event);
        }
      }

      const complete = events[0] as TextMessageComplete;
      expect(complete.content).toBe('Hello');
    });

    it('should serialize non-string content', async () => {
      class ObjectAgent implements Agent {
        readonly name = 'ObjectAgent';

        async process(_message: Message): Promise<Message> {
          return {
            role: 'assistant',
            content: { type: 'response', data: 'test' },
            timestamp: new Date().toISOString(),
          };
        }
      }

      const agent = new ObjectAgent();
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        if (event instanceof TextMessageComplete) {
          events.push(event);
        }
      }

      const complete = events[0] as TextMessageComplete;
      expect(complete.content).toContain('type');
      expect(complete.content).toContain('response');
    });
  });

  describe('Message ID generation', () => {
    it('should generate unique message IDs', async () => {
      const agent = new MockAgent('test');
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const ids = new Set<string>();
      for (let i = 0; i < 3; i++) {
        for await (const event of adapter.streamEvents(message, undefined, false)) {
          if (event instanceof TextMessageStart) {
            ids.add(event.message_id);
          }
        }
      }

      expect(ids.size).toBe(3);
    });

    it('should use provided message ID', async () => {
      const agent = new MockAgent('test');
      const adapter = new AGUIAdapter(agent);

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, 'custom_id', false)) {
        if (event instanceof TextMessageStart) {
          events.push(event);
        }
      }

      const start = events[0] as TextMessageStart;
      expect(start.message_id).toBe('custom_id');
    });
  });
});
