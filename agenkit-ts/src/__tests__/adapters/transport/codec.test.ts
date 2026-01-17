/**
 * Tests for message codec (serialization/deserialization).
 *
 * Tests encoding, decoding, and protocol envelope operations.
 */

import { describe, it, expect } from 'vitest';
import type { Message, ToolResult } from '../../../core/interfaces';
import {
  PROTOCOL_VERSION,
  encodeMessage,
  decodeMessage,
  encodeToolResult,
  decodeToolResult,
  createRequestEnvelope,
  createResponseEnvelope,
  createErrorEnvelope,
  createStreamChunkEnvelope,
  createStreamEndEnvelope,
  validateEnvelope,
  encodeBytes,
  decodeBytes,
} from '../../../transports/codec';
import {
  InvalidMessageError,
  MalformedPayloadError,
  UnsupportedVersionError,
} from '../../../transports/errors';

// ============================================
// Message Encoding Tests
// ============================================

describe('Codec: Message Encoding', () => {
  it('should encode basic message', () => {
    const message: Message = {
      role: 'user',
      content: 'Hello',
      metadata: {},
    };

    const encoded = encodeMessage(message);

    expect(encoded.role).toBe('user');
    expect(encoded.content).toBe('Hello');
    expect(encoded.metadata).toEqual({});
    expect(encoded.timestamp).toBeDefined();
  });

  it('should preserve message content types', () => {
    const messages: Message[] = [
      { role: 'user', content: 'String content', metadata: {} },
      { role: 'user', content: { type: 'object' }, metadata: {} },
      { role: 'user', content: ['array', 'content'], metadata: {} },
      { role: 'user', content: 12345, metadata: {} },
    ];

    for (const message of messages) {
      const encoded = encodeMessage(message);
      expect(encoded.content).toEqual(message.content);
    }
  });

  it('should preserve metadata', () => {
    const message: Message = {
      role: 'user',
      content: 'Hello',
      metadata: {
        userId: 'alice',
        sessionId: '123',
        custom: { nested: 'value' },
      },
    };

    const encoded = encodeMessage(message);

    expect(encoded.metadata).toEqual(message.metadata);
  });

  it('should add timestamp if missing', () => {
    const message: Message = {
      role: 'user',
      content: 'Hello',
      metadata: {},
    };

    const encoded = encodeMessage(message);

    expect(encoded.timestamp).toBeDefined();
    expect(typeof encoded.timestamp).toBe('string');
  });

  it('should preserve existing timestamp', () => {
    const timestamp = '2026-01-17T12:00:00.000Z';
    const message: Message = {
      role: 'user',
      content: 'Hello',
      metadata: {},
      timestamp,
    };

    const encoded = encodeMessage(message);

    expect(encoded.timestamp).toBe(timestamp);
  });
});

// ============================================
// Message Decoding Tests
// ============================================

describe('Codec: Message Decoding', () => {
  it('should decode basic message', () => {
    const data = {
      role: 'assistant',
      content: 'Hello!',
      metadata: {},
      timestamp: '2026-01-17T12:00:00.000Z',
    };

    const message = decodeMessage(data);

    expect(message.role).toBe('assistant');
    expect(message.content).toBe('Hello!');
    expect(message.metadata).toEqual({});
    expect(message.timestamp).toBe('2026-01-17T12:00:00.000Z');
  });

  it('should add timestamp if missing', () => {
    const data = {
      role: 'assistant',
      content: 'Hello!',
      metadata: {},
    };

    const message = decodeMessage(data);

    expect(message.timestamp).toBeDefined();
    expect(typeof message.timestamp).toBe('string');
  });

  it('should decode message with partial fields', () => {
    // decodeMessage doesn't validate - it just assigns fields
    // Validation happens when message is used
    const partialData = {
      role: 'user',
      content: 'Hello',
      // Missing metadata - should be added
    };

    const message = decodeMessage(partialData);

    expect(message.role).toBe('user');
    expect(message.content).toBe('Hello');
    expect(message.metadata).toEqual({});
  });

  it('should handle missing metadata', () => {
    const data = {
      role: 'user',
      content: 'Hello',
    };

    const message = decodeMessage(data);

    expect(message.metadata).toEqual({});
  });
});

// ============================================
// Roundtrip Tests
// ============================================

describe('Codec: Message Roundtrip', () => {
  it('should preserve message through encode-decode cycle', () => {
    const original: Message = {
      role: 'user',
      content: 'Hello, world!',
      metadata: {
        userId: 'alice',
        custom: { nested: true },
      },
      timestamp: '2026-01-17T12:00:00.000Z',
    };

    const encoded = encodeMessage(original);
    const decoded = decodeMessage(encoded);

    expect(decoded.role).toBe(original.role);
    expect(decoded.content).toBe(original.content);
    expect(decoded.metadata).toEqual(original.metadata);
    expect(decoded.timestamp).toBe(original.timestamp);
  });

  it('should handle complex content', () => {
    const original: Message = {
      role: 'user',
      content: {
        text: 'Hello',
        data: [1, 2, 3],
        nested: { key: 'value' },
      },
      metadata: {},
    };

    const encoded = encodeMessage(original);
    const decoded = decodeMessage(encoded);

    expect(decoded.content).toEqual(original.content);
  });
});

// ============================================
// ToolResult Encoding/Decoding Tests
// ============================================

describe('Codec: ToolResult', () => {
  it('should encode tool result success', () => {
    const result: ToolResult = {
      success: true,
      output: { result: 'success' },
      metadata: {},
    };

    const encoded = encodeToolResult(result);

    expect(encoded.success).toBe(true);
    expect(encoded.output).toEqual({ result: 'success' });
    expect(encoded.metadata).toEqual({});
  });

  it('should encode tool result error', () => {
    const result: ToolResult = {
      success: false,
      output: null,
      error: 'Operation failed',
      metadata: {},
    };

    const encoded = encodeToolResult(result);

    expect(encoded.success).toBe(false);
    expect(encoded.error).toBe('Operation failed');
  });

  it('should decode tool result', () => {
    const data = {
      success: true,
      output: { data: 'test' },
      metadata: { timestamp: '2026-01-17' },
    };

    const result = decodeToolResult(data);

    expect(result.success).toBe(true);
    expect(result.output).toEqual({ data: 'test' });
    expect(result.metadata?.timestamp).toBe('2026-01-17');
  });

  it('should handle tool result roundtrip', () => {
    const original: ToolResult = {
      success: true,
      output: { result: 'data' },
      metadata: { custom: 'value' },
    };

    const encoded = encodeToolResult(original);
    const decoded = decodeToolResult(encoded);

    expect(decoded).toEqual(original);
  });
});

// ============================================
// Protocol Envelope Creation Tests
// ============================================

describe('Codec: Protocol Envelopes', () => {
  it('should create request envelope', () => {
    const envelope = createRequestEnvelope('process', 'test-agent', {
      message: { content: 'Hello' },
    });

    expect(envelope.version).toBe(PROTOCOL_VERSION);
    expect(envelope.type).toBe('request');
    expect(envelope.id).toBeDefined();
    expect(envelope.timestamp).toBeDefined();
    expect(envelope.payload.method).toBe('process');
    expect(envelope.payload.agent_name).toBe('test-agent');
  });

  it('should create request without agent name', () => {
    const envelope = createRequestEnvelope('list_agents');

    expect(envelope.version).toBe(PROTOCOL_VERSION);
    expect(envelope.type).toBe('request');
    expect(envelope.payload.method).toBe('list_agents');
    expect(envelope.payload.agent_name).toBeUndefined();
  });

  it('should create response envelope', () => {
    const requestId = 'test-123';
    const envelope = createResponseEnvelope(requestId, {
      message: { content: 'Response' },
    });

    expect(envelope.version).toBe(PROTOCOL_VERSION);
    expect(envelope.type).toBe('response');
    expect(envelope.id).toBe(requestId);
    expect(envelope.payload.message).toEqual({ content: 'Response' });
  });

  it('should create error envelope', () => {
    const requestId = 'test-123';
    const envelope = createErrorEnvelope(
      requestId,
      'AGENT_NOT_FOUND',
      'Agent does not exist',
      { agentName: 'missing-agent' }
    );

    expect(envelope.version).toBe(PROTOCOL_VERSION);
    expect(envelope.type).toBe('error');
    expect(envelope.id).toBe(requestId);
    expect(envelope.payload.error_code).toBe('AGENT_NOT_FOUND');
    expect(envelope.payload.error_message).toBe('Agent does not exist');
    expect(envelope.payload.error_details).toEqual({ agentName: 'missing-agent' });
  });

  it('should create stream chunk envelope', () => {
    const requestId = 'test-123';
    const envelope = createStreamChunkEnvelope(requestId, {
      content: 'Chunk data',
    });

    expect(envelope.version).toBe(PROTOCOL_VERSION);
    expect(envelope.type).toBe('stream_chunk');
    expect(envelope.id).toBe(requestId);
    expect(envelope.payload.message).toEqual({ content: 'Chunk data' });
  });

  it('should create stream end envelope', () => {
    const requestId = 'test-123';
    const envelope = createStreamEndEnvelope(requestId);

    expect(envelope.version).toBe(PROTOCOL_VERSION);
    expect(envelope.type).toBe('stream_end');
    expect(envelope.id).toBe(requestId);
    expect(envelope.payload).toEqual({});
  });
});

// ============================================
// Envelope Validation Tests
// ============================================

describe('Codec: Envelope Validation', () => {
  it('should validate valid envelope', () => {
    const envelope = {
      version: PROTOCOL_VERSION,
      type: 'request',
      id: 'test-123',
      timestamp: new Date().toISOString(),
      payload: { method: 'process' },
    };

    expect(() => validateEnvelope(envelope)).not.toThrow();
  });

  it('should reject missing version', () => {
    const envelope = {
      type: 'request',
      id: 'test-123',
      payload: {},
    };

    expect(() => validateEnvelope(envelope)).toThrow(InvalidMessageError);
    expect(() => validateEnvelope(envelope)).toThrow("Missing 'version' field");
  });

  it('should reject unsupported version', () => {
    const envelope = {
      version: '99.0',
      type: 'request',
      id: 'test-123',
      payload: {},
    };

    expect(() => validateEnvelope(envelope)).toThrow(UnsupportedVersionError);
  });

  it('should reject missing type', () => {
    const envelope = {
      version: PROTOCOL_VERSION,
      id: 'test-123',
      payload: {},
    };

    expect(() => validateEnvelope(envelope)).toThrow(InvalidMessageError);
    expect(() => validateEnvelope(envelope)).toThrow("Missing 'type' field");
  });

  it('should reject invalid type', () => {
    const envelope = {
      version: PROTOCOL_VERSION,
      type: 'invalid_type',
      id: 'test-123',
      payload: {},
    };

    expect(() => validateEnvelope(envelope)).toThrow(InvalidMessageError);
    expect(() => validateEnvelope(envelope)).toThrow('Invalid message type');
  });

  it('should reject missing id', () => {
    const envelope = {
      version: PROTOCOL_VERSION,
      type: 'request',
      payload: {},
    };

    expect(() => validateEnvelope(envelope)).toThrow(InvalidMessageError);
    expect(() => validateEnvelope(envelope)).toThrow("Missing 'id' field");
  });

  it('should reject missing payload', () => {
    const envelope = {
      version: PROTOCOL_VERSION,
      type: 'request',
      id: 'test-123',
    };

    expect(() => validateEnvelope(envelope)).toThrow(InvalidMessageError);
    expect(() => validateEnvelope(envelope)).toThrow("Missing 'payload' field");
  });

  it('should accept all valid types', () => {
    const validTypes = [
      'request',
      'response',
      'error',
      'heartbeat',
      'register',
      'unregister',
      'stream_chunk',
      'stream_end',
    ];

    for (const type of validTypes) {
      const envelope = {
        version: PROTOCOL_VERSION,
        type,
        id: 'test-123',
        payload: {},
      };

      expect(() => validateEnvelope(envelope)).not.toThrow();
    }
  });
});

// ============================================
// Bytes Encoding/Decoding Tests
// ============================================

describe('Codec: Bytes Encoding', () => {
  it('should encode envelope to bytes', () => {
    const envelope = createRequestEnvelope('process');
    const bytes = encodeBytes(envelope);

    expect(Buffer.isBuffer(bytes)).toBe(true);
    expect(bytes.length).toBeGreaterThan(0);
  });

  it('should decode bytes to envelope', () => {
    const original = createRequestEnvelope('process', 'test-agent');
    const bytes = encodeBytes(original);
    const decoded = decodeBytes(bytes);

    expect(decoded.version).toBe(original.version);
    expect(decoded.type).toBe(original.type);
    expect(decoded.id).toBe(original.id);
    expect(decoded.payload).toEqual(original.payload);
  });

  it('should handle roundtrip', () => {
    const original = createRequestEnvelope('process', 'test-agent', {
      message: {
        role: 'user',
        content: 'Hello, world!',
        metadata: { custom: 'value' },
      },
    });

    const bytes = encodeBytes(original);
    const decoded = decodeBytes(bytes);

    expect(decoded).toEqual(original);
  });

  it('should throw on malformed bytes', () => {
    const invalidBytes = Buffer.from('invalid json', 'utf-8');

    expect(() => decodeBytes(invalidBytes)).toThrow(MalformedPayloadError);
  });

  it('should throw on invalid envelope in bytes', () => {
    const invalidEnvelope = { invalid: 'envelope' };
    const bytes = Buffer.from(JSON.stringify(invalidEnvelope), 'utf-8');

    expect(() => decodeBytes(bytes)).toThrow();
  });

  it('should handle unicode characters', () => {
    const envelope = createRequestEnvelope('process', 'test-agent', {
      message: {
        content: '🔥 Hello, 世界! ✨',
      },
    });

    const bytes = encodeBytes(envelope);
    const decoded = decodeBytes(bytes);

    expect(decoded.payload.message).toEqual(envelope.payload.message);
  });

  it('should handle large payloads', () => {
    const largeContent = 'x'.repeat(10000);
    const envelope = createRequestEnvelope('process', 'test-agent', {
      message: { content: largeContent },
    });

    const bytes = encodeBytes(envelope);
    const decoded = decodeBytes(bytes);

    expect(decoded.payload.message).toEqual({ content: largeContent });
  });
});
