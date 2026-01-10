/**
 * Message serialization and deserialization for protocol adapter.
 *
 * Provides encoding/decoding functions for Message objects and protocol envelopes.
 */

import { randomUUID } from 'crypto';
import { Message, ToolResult } from '../core/interfaces';
import {
  InvalidMessageError,
  MalformedPayloadError,
  UnsupportedVersionError,
} from './errors';

export const PROTOCOL_VERSION = '1.0';

/**
 * Protocol envelope for request/response communication.
 */
export interface ProtocolEnvelope {
  version: string;
  type: 'request' | 'response' | 'error' | 'heartbeat' | 'register' | 'unregister' | 'stream_chunk' | 'stream_end';
  id: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

/**
 * Encode a Message object to a dictionary for JSON serialization.
 *
 * @param message The Message to encode
 * @returns Dictionary representation of the message
 */
export function encodeMessage(message: Message): Record<string, unknown> {
  return {
    role: message.role,
    content: message.content,
    metadata: message.metadata || {},
    timestamp: message.timestamp || new Date().toISOString(),
  };
}

/**
 * Decode a dictionary to a Message object.
 *
 * @param data Dictionary representation of a message
 * @returns Decoded Message object
 * @throws MalformedPayloadError if message data is invalid
 */
export function decodeMessage(data: Record<string, unknown>): Message {
  try {
    // Parse timestamp if present, otherwise use current time
    let timestamp = data.timestamp as string | undefined;
    if (!timestamp) {
      timestamp = new Date().toISOString();
    }

    return {
      role: data.role as string,
      content: data.content,
      metadata: (data.metadata as Record<string, unknown>) || {},
      timestamp,
    };
  } catch (error) {
    throw new MalformedPayloadError(
      `Failed to decode message: ${error}`,
      { data },
    );
  }
}

/**
 * Encode a ToolResult object to a dictionary for JSON serialization.
 *
 * @param result The ToolResult to encode
 * @returns Dictionary representation of the tool result
 */
export function encodeToolResult(result: ToolResult): Record<string, unknown> {
  return {
    success: result.success,
    output: result.output,
    error: result.error,
    metadata: result.metadata || {},
  };
}

/**
 * Decode a dictionary to a ToolResult object.
 *
 * @param data Dictionary representation of a tool result
 * @returns Decoded ToolResult object
 * @throws MalformedPayloadError if tool result data is invalid
 */
export function decodeToolResult(data: Record<string, unknown>): ToolResult {
  try {
    return {
      success: data.success as boolean,
      output: data.output,
      error: data.error as string | undefined,
      metadata: (data.metadata as Record<string, unknown>) || {},
    };
  } catch (error) {
    throw new MalformedPayloadError(
      `Failed to decode tool result: ${error}`,
      { data },
    );
  }
}

/**
 * Create a protocol request envelope.
 *
 * @param method Method name ("process" or "stream")
 * @param agentName Name of the target agent (for agent requests)
 * @param payload Request payload
 * @returns Request envelope dictionary
 */
export function createRequestEnvelope(
  method: string,
  agentName?: string,
  payload?: Record<string, unknown>,
): ProtocolEnvelope {
  return {
    version: PROTOCOL_VERSION,
    type: 'request',
    id: randomUUID(),
    timestamp: new Date().toISOString(),
    payload: {
      method,
      ...(agentName ? { agent_name: agentName } : {}),
      ...(payload || {}),
    },
  };
}

/**
 * Create a protocol response envelope.
 *
 * @param requestId ID of the request being responded to
 * @param payload Response payload
 * @returns Response envelope dictionary
 */
export function createResponseEnvelope(
  requestId: string,
  payload: Record<string, unknown>,
): ProtocolEnvelope {
  return {
    version: PROTOCOL_VERSION,
    type: 'response',
    id: requestId,
    timestamp: new Date().toISOString(),
    payload,
  };
}

/**
 * Create a protocol error envelope.
 *
 * @param requestId ID of the request that failed
 * @param errorCode Error code
 * @param errorMessage Human-readable error message
 * @param errorDetails Additional error details
 * @returns Error envelope dictionary
 */
export function createErrorEnvelope(
  requestId: string,
  errorCode: string,
  errorMessage: string,
  errorDetails?: Record<string, unknown>,
): ProtocolEnvelope {
  return {
    version: PROTOCOL_VERSION,
    type: 'error',
    id: requestId,
    timestamp: new Date().toISOString(),
    payload: {
      error_code: errorCode,
      error_message: errorMessage,
      error_details: errorDetails || {},
    },
  };
}

/**
 * Create a protocol stream chunk envelope.
 *
 * @param requestId ID of the streaming request
 * @param message Message chunk payload
 * @returns Stream chunk envelope dictionary
 */
export function createStreamChunkEnvelope(
  requestId: string,
  message: Record<string, unknown>,
): ProtocolEnvelope {
  return {
    version: PROTOCOL_VERSION,
    type: 'stream_chunk',
    id: requestId,
    timestamp: new Date().toISOString(),
    payload: { message },
  };
}

/**
 * Create a protocol stream end envelope.
 *
 * @param requestId ID of the streaming request
 * @returns Stream end envelope dictionary
 */
export function createStreamEndEnvelope(requestId: string): ProtocolEnvelope {
  return {
    version: PROTOCOL_VERSION,
    type: 'stream_end',
    id: requestId,
    timestamp: new Date().toISOString(),
    payload: {},
  };
}

/**
 * Validate a protocol envelope.
 *
 * @param envelope Envelope to validate
 * @throws InvalidMessageError if envelope is invalid
 * @throws UnsupportedVersionError if protocol version is not supported
 */
export function validateEnvelope(envelope: Record<string, unknown>): void {
  // Check required fields
  if (!envelope.version) {
    throw new InvalidMessageError("Missing 'version' field in envelope");
  }

  if (envelope.version !== PROTOCOL_VERSION) {
    throw new UnsupportedVersionError(
      `Unsupported protocol version: ${envelope.version}`,
      { version: envelope.version },
    );
  }

  if (!envelope.type) {
    throw new InvalidMessageError("Missing 'type' field in envelope");
  }

  const validTypes = new Set([
    'request',
    'response',
    'error',
    'heartbeat',
    'register',
    'unregister',
    'stream_chunk',
    'stream_end',
  ]);

  if (!validTypes.has(envelope.type as string)) {
    throw new InvalidMessageError(
      `Invalid message type: ${envelope.type}`,
      { type: envelope.type },
    );
  }

  if (!envelope.id) {
    throw new InvalidMessageError("Missing 'id' field in envelope");
  }

  if (!envelope.payload) {
    throw new InvalidMessageError("Missing 'payload' field in envelope");
  }
}

/**
 * Encode an envelope to bytes for transmission.
 *
 * @param envelope Envelope dictionary to encode
 * @returns UTF-8 encoded JSON bytes
 */
export function encodeBytes(envelope: ProtocolEnvelope): Buffer {
  return Buffer.from(JSON.stringify(envelope), 'utf-8');
}

/**
 * Decode bytes to an envelope dictionary.
 *
 * @param data UTF-8 encoded JSON bytes
 * @returns Envelope dictionary
 * @throws MalformedPayloadError if data cannot be decoded
 */
export function decodeBytes(data: Buffer): ProtocolEnvelope {
  try {
    const envelope = JSON.parse(data.toString('utf-8')) as Record<string, unknown>;
    validateEnvelope(envelope);
    return envelope as ProtocolEnvelope;
  } catch (error) {
    if (error instanceof MalformedPayloadError ||
        error instanceof InvalidMessageError ||
        error instanceof UnsupportedVersionError) {
      throw error;
    }
    throw new MalformedPayloadError(`Failed to decode envelope: ${error}`);
  }
}
