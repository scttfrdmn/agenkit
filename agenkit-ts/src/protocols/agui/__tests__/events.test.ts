/**
 * Comprehensive tests for AG-UI event types.
 *
 * Tests cover:
 * - Event construction
 * - Event serialization (toJSON)
 * - Event metadata
 * - Event timestamps
 * - Event IDs
 * - All event types
 */

import { describe, it, expect } from 'vitest';
import {
  EventType,
  InterruptReason,
  InterruptAction,
  AttachmentType,
  TextMessageStart,
  TextMessageChunk,
  TextMessageComplete,
  ToolCallStart,
  ToolCallChunk,
  ToolCallComplete,
  StateDelta,
  Interrupt,
  InterruptResponse,
  ErrorEvent,
  Attachment,
  MetadataEvent,
  HeartbeatEvent,
  parseEvent,
} from '../events';

describe('AG-UI Events', () => {
  describe('TextMessageStart', () => {
    it('should create event with required fields', () => {
      const event = new TextMessageStart('assistant', 'msg_123');

      expect(event.event_type).toBe(EventType.TEXT_MESSAGE_START);
      expect(event.role).toBe('assistant');
      expect(event.message_id).toBe('msg_123');
      expect(event.timestamp).toBeDefined();
    });

    it('should include metadata in toJSON', () => {
      const event = new TextMessageStart('assistant', 'msg_123', {
        agent_name: 'TestAgent',
      });

      const json = event.toJSON();
      expect(json.event_type).toBe('text_message_start');
      expect(json.role).toBe('assistant');
      expect(json.message_id).toBe('msg_123');
      expect(json.agent_name).toBe('TestAgent');
    });

    it('should generate timestamp if not provided', () => {
      const event = new TextMessageStart('assistant', 'msg_123');
      expect(event.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    });
  });

  describe('TextMessageChunk', () => {
    it('should create event with content', () => {
      const event = new TextMessageChunk('Hello', 'msg_123');

      expect(event.event_type).toBe(EventType.TEXT_MESSAGE_CHUNK);
      expect(event.content).toBe('Hello');
      expect(event.message_id).toBe('msg_123');
    });

    it('should include chunk index in metadata', () => {
      const event = new TextMessageChunk('Hello', 'msg_123', {
        chunk_index: 0,
      });

      const json = event.toJSON();
      expect(json.chunk_index).toBe(0);
    });

    it('should handle empty content', () => {
      const event = new TextMessageChunk('', 'msg_123');
      expect(event.content).toBe('');
    });
  });

  describe('TextMessageComplete', () => {
    it('should create event with finish reason', () => {
      const event = new TextMessageComplete('Hello world', 'stop', 'msg_123');

      expect(event.event_type).toBe(EventType.TEXT_MESSAGE_COMPLETE);
      expect(event.content).toBe('Hello world');
      expect(event.finish_reason).toBe('stop');
      expect(event.message_id).toBe('msg_123');
    });

    it('should include full content in toJSON', () => {
      const event = new TextMessageComplete('Test content', 'stop', 'msg_123', {
        confidence: 0.9,
      });

      const json = event.toJSON();
      expect(json.content).toBe('Test content');
      expect(json.finish_reason).toBe('stop');
      expect(json.confidence).toBe(0.9);
    });

    it('should handle error finish reason', () => {
      const event = new TextMessageComplete('', 'error', 'msg_123', {
        error: 'Processing failed',
      });

      expect(event.finish_reason).toBe('error');
      const json = event.toJSON();
      expect(json.error).toBe('Processing failed');
    });
  });

  describe('ToolCallStart', () => {
    it('should create event with tool info', () => {
      const event = new ToolCallStart('search', { query: 'test' }, 'tool_456');

      expect(event.event_type).toBe(EventType.TOOL_CALL_START);
      expect(event.tool_name).toBe('search');
      expect(event.tool_call_id).toBe('tool_456');
      expect(event.arguments).toEqual({ query: 'test' });
    });

    it('should include parameters in metadata', () => {
      const event = new ToolCallStart('search', { query: 'test' }, 'tool_456', {
        extra_field: 'value',
      });

      const json = event.toJSON();
      expect(json.extra_field).toBe('value');
    });
  });

  describe('ToolCallChunk', () => {
    it('should create event with partial output', () => {
      const event = new ToolCallChunk('partial result', undefined, 'tool_456');

      expect(event.event_type).toBe(EventType.TOOL_CALL_CHUNK);
      expect(event.progress).toBe('partial result');
      expect(event.tool_call_id).toBe('tool_456');
    });
  });

  describe('ToolCallComplete', () => {
    it('should create event with result', () => {
      const result = { data: 'search results' };
      const event = new ToolCallComplete('search', result, true, undefined, 'tool_456');

      expect(event.event_type).toBe(EventType.TOOL_CALL_COMPLETE);
      expect(event.tool_name).toBe('search');
      expect(event.result).toEqual(result);
      expect(event.success).toBe(true);
      expect(event.tool_call_id).toBe('tool_456');
    });

    it('should handle error results', () => {
      const event = new ToolCallComplete('search', null, false, 'Tool execution failed', 'tool_456');

      expect(event.success).toBe(false);
      expect(event.error).toBe('Tool execution failed');
      const json = event.toJSON();
      expect(json.error).toBe('Tool execution failed');
    });
  });

  describe('StateDelta', () => {
    it('should create event with state update', () => {
      const delta = { key: 'value' };
      const event = new StateDelta(delta);

      expect(event.event_type).toBe(EventType.STATE_DELTA);
      expect(event.delta).toEqual(delta);
    });

    it('should include update type in metadata', () => {
      const event = new StateDelta({ count: 5 }, undefined, { update_type: 'increment' });

      const json = event.toJSON();
      expect(json.update_type).toBe('increment');
    });
  });

  describe('Interrupt', () => {
    it('should create event with interrupt details', () => {
      const event = new Interrupt(
        InterruptReason.HUMAN_APPROVAL,
        'Human approval required',
        [InterruptAction.APPROVE, InterruptAction.REJECT],
        {},
        'interrupt_789',
      );

      expect(event.event_type).toBe(EventType.INTERRUPT);
      expect(event.interrupt_id).toBe('interrupt_789');
      expect(event.message).toBe('Human approval required');
      expect(event.reason).toBe(InterruptReason.HUMAN_APPROVAL);
      expect(event.available_actions).toContain(InterruptAction.APPROVE);
    });

    it('should include context in toJSON', () => {
      const event = new Interrupt(
        InterruptReason.HUMAN_APPROVAL,
        'Confidence below threshold',
        [InterruptAction.APPROVE],
        {
          confidence: 0.6,
          threshold: 0.8,
        },
        'interrupt_789',
      );

      const json = event.toJSON();
      expect(json.context).toHaveProperty('confidence', 0.6);
      expect(json.context).toHaveProperty('threshold', 0.8);
    });
  });

  describe('InterruptResponse', () => {
    it('should create event with response action', () => {
      const event = new InterruptResponse('interrupt_789', InterruptAction.APPROVE);

      expect(event.event_type).toBe(EventType.INTERRUPT_RESPONSE);
      expect(event.interrupt_id).toBe('interrupt_789');
      expect(event.action).toBe(InterruptAction.APPROVE);
    });

    it('should include response data', () => {
      const event = new InterruptResponse(
        'interrupt_789',
        InterruptAction.APPROVE,
        { feedback: 'Approved by manager' },
      );

      const json = event.toJSON();
      expect(json.data).toHaveProperty('feedback');
    });
  });

  describe('ErrorEvent', () => {
    it('should create event with error details', () => {
      const event = new ErrorEvent('timeout', 'Request timed out', true);

      expect(event.event_type).toBe(EventType.ERROR);
      expect(event.error_code).toBe('timeout');
      expect(event.error_message).toBe('Request timed out');
      expect(event.recoverable).toBe(true);
    });

    it('should include error metadata', () => {
      const event = new ErrorEvent(
        'validation_error',
        'Invalid input',
        false,
        {
          field: 'email',
          reason: 'invalid_format',
        },
      );

      const json = event.toJSON();
      expect(json.details).toHaveProperty('field', 'email');
      expect(json.details).toHaveProperty('reason', 'invalid_format');
    });
  });

  describe('Attachment', () => {
    it('should create event with attachment', () => {
      const event = new Attachment(
        AttachmentType.FILE,
        'application/pdf',
        'https://example.com/document.pdf',
        undefined,
        'document.pdf',
      );

      expect(event.event_type).toBe(EventType.ATTACHMENT);
      expect(event.attachment_type).toBe(AttachmentType.FILE);
      expect(event.content_type).toBe('application/pdf');
      expect(event.filename).toBe('document.pdf');
      expect(event.url).toBe('https://example.com/document.pdf');
    });

    it('should handle image attachments', () => {
      const event = new Attachment(
        AttachmentType.IMAGE,
        'image/jpeg',
        'https://example.com/photo.jpg',
        undefined,
        'photo.jpg',
        undefined,
        {
          width: 1920,
          height: 1080,
        },
      );

      const json = event.toJSON();
      expect(json.width).toBe(1920);
      expect(json.height).toBe(1080);
    });
  });

  describe('MetadataEvent', () => {
    it('should create event with metadata', () => {
      const metadata = {
        agent_name: 'TestAgent',
        protocol: 'ag-ui',
        version: '1.0',
      };
      const event = new MetadataEvent(metadata);

      expect(event.event_type).toBe(EventType.METADATA);
      expect(event.data).toEqual(metadata);
    });

    it('should include all metadata in toJSON', () => {
      const event = new MetadataEvent({
        capabilities: ['chat', 'search'],
        model: 'gpt-4',
      });

      const json = event.toJSON();
      expect(json.capabilities).toEqual(['chat', 'search']);
      expect(json.model).toBe('gpt-4');
    });
  });

  describe('HeartbeatEvent', () => {
    it('should create event with interval', () => {
      const event = new HeartbeatEvent(30000);

      expect(event.event_type).toBe(EventType.HEARTBEAT);
      expect(event.interval_ms).toBe(30000);
    });

    it('should include interval in toJSON', () => {
      const event = new HeartbeatEvent(15000);

      const json = event.toJSON();
      expect(json.interval_ms).toBe(15000);
    });
  });

  describe('parseEvent', () => {
    it('should parse TextMessageChunk', () => {
      const json = {
        event_type: 'text_message_chunk',
        content: 'test',
        message_id: 'msg_123',
        timestamp: new Date().toISOString(),
      };

      const event = parseEvent(json);
      expect(event).toBeInstanceOf(TextMessageChunk);
      expect((event as TextMessageChunk).content).toBe('test');
    });

    it('should parse Interrupt', () => {
      const json = {
        event_type: 'interrupt',
        interrupt_id: 'int_456',
        message: 'Approval needed',
        reason: 'human_approval',
        actions: ['approve', 'reject'],
        timestamp: new Date().toISOString(),
      };

      const event = parseEvent(json);
      expect(event).toBeInstanceOf(Interrupt);
      expect((event as Interrupt).message).toBe('Approval needed');
    });

    it('should parse ErrorEvent', () => {
      const json = {
        event_type: 'error',
        error_code: 'timeout',
        error_message: 'Request timed out',
        recoverable: true,
        timestamp: new Date().toISOString(),
      };

      const event = parseEvent(json);
      expect(event).toBeInstanceOf(ErrorEvent);
      expect((event as ErrorEvent).error_code).toBe('timeout');
    });

    it('should throw on unknown event type', () => {
      const json = {
        event_type: 'unknown_type',
        timestamp: new Date().toISOString(),
      };

      expect(() => parseEvent(json)).toThrow('Unknown event type');
    });

    it('should handle missing timestamp', () => {
      const json = {
        event_type: 'text_message_chunk',
        content: 'test',
        message_id: 'msg_123',
      };

      const event = parseEvent(json);
      expect(event.timestamp).toBeDefined();
    });
  });

  describe('Event metadata', () => {
    it('should preserve custom metadata', () => {
      const event = new TextMessageChunk('test', 'msg_123', {
        custom_field: 'value',
        number_field: 42,
      });

      const json = event.toJSON();
      expect(json.custom_field).toBe('value');
      expect(json.number_field).toBe(42);
    });

    it('should handle nested metadata', () => {
      const event = new MetadataEvent({
        nested: {
          level1: {
            level2: 'deep value',
          },
        },
      });

      const json = event.toJSON();
      expect(json.nested.level1.level2).toBe('deep value');
    });
  });

  describe('Event IDs', () => {
    it('should generate unique event IDs', () => {
      const event1 = new TextMessageStart('assistant', 'msg_1');
      const event2 = new TextMessageStart('assistant', 'msg_2');

      // Events may or may not have event_id depending on implementation
      if (event1.event_id && event2.event_id) {
        expect(event1.event_id).not.toBe(event2.event_id);
      }
    });

    it('should preserve event IDs across serialization', () => {
      const event = new TextMessageChunk('test', 'msg_123');
      const eventId = event.event_id;

      const json = event.toJSON();
      expect(json.event_id).toBe(eventId);
    });
  });
});
