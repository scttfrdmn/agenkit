/**
 * Error types for transport layer.
 *
 * Provides a hierarchy of error types for transport-level errors,
 * protocol errors, and remote execution errors.
 */

/**
 * Standard error codes for protocol-level errors.
 */
export enum ProtocolErrorCode {
  // Connection errors
  CONNECTION_FAILED = 'CONNECTION_FAILED',
  CONNECTION_TIMEOUT = 'CONNECTION_TIMEOUT',
  CONNECTION_CLOSED = 'CONNECTION_CLOSED',

  // Protocol errors
  INVALID_MESSAGE = 'INVALID_MESSAGE',
  UNSUPPORTED_VERSION = 'UNSUPPORTED_VERSION',
  MALFORMED_PAYLOAD = 'MALFORMED_PAYLOAD',

  // Agent errors
  AGENT_NOT_FOUND = 'AGENT_NOT_FOUND',
  AGENT_UNAVAILABLE = 'AGENT_UNAVAILABLE',
  AGENT_TIMEOUT = 'AGENT_TIMEOUT',

  // Tool errors
  TOOL_NOT_FOUND = 'TOOL_NOT_FOUND',
  TOOL_EXECUTION_FAILED = 'TOOL_EXECUTION_FAILED',

  // Registry errors
  REGISTRATION_FAILED = 'REGISTRATION_FAILED',
  DUPLICATE_AGENT = 'DUPLICATE_AGENT',
}

/**
 * Base exception for protocol adapter errors.
 */
export class ProtocolError extends Error {
  constructor(
    public readonly code: ProtocolErrorCode,
    message: string,
    public readonly details: Record<string, unknown> = {},
  ) {
    super(`${code}: ${message}`);
    this.name = 'ProtocolError';
  }
}

/**
 * Connection-related errors.
 */
export class ConnectionError extends ProtocolError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(ProtocolErrorCode.CONNECTION_FAILED, message, details);
    this.name = 'ConnectionError';
  }
}

/**
 * Connection timeout errors.
 */
export class ConnectionTimeoutError extends ProtocolError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(ProtocolErrorCode.CONNECTION_TIMEOUT, message, details);
    this.name = 'ConnectionTimeoutError';
  }
}

/**
 * Connection closed errors.
 */
export class ConnectionClosedError extends ProtocolError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(ProtocolErrorCode.CONNECTION_CLOSED, message, details);
    this.name = 'ConnectionClosedError';
  }
}

/**
 * Invalid message format errors.
 */
export class InvalidMessageError extends ProtocolError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(ProtocolErrorCode.INVALID_MESSAGE, message, details);
    this.name = 'InvalidMessageError';
  }
}

/**
 * Unsupported protocol version errors.
 */
export class UnsupportedVersionError extends ProtocolError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(ProtocolErrorCode.UNSUPPORTED_VERSION, message, details);
    this.name = 'UnsupportedVersionError';
  }
}

/**
 * Malformed payload errors.
 */
export class MalformedPayloadError extends ProtocolError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(ProtocolErrorCode.MALFORMED_PAYLOAD, message, details);
    this.name = 'MalformedPayloadError';
  }
}

/**
 * Agent not found in registry errors.
 */
export class AgentNotFoundError extends ProtocolError {
  constructor(agentName: string, details: Record<string, unknown> = {}) {
    super(
      ProtocolErrorCode.AGENT_NOT_FOUND,
      `Agent '${agentName}' not found in registry`,
      details,
    );
    this.name = 'AgentNotFoundError';
  }
}

/**
 * Agent unavailable errors.
 */
export class AgentUnavailableError extends ProtocolError {
  constructor(agentName: string, details: Record<string, unknown> = {}) {
    super(
      ProtocolErrorCode.AGENT_UNAVAILABLE,
      `Agent '${agentName}' is unavailable`,
      details,
    );
    this.name = 'AgentUnavailableError';
  }
}

/**
 * Agent timeout errors.
 */
export class AgentTimeoutError extends ProtocolError {
  constructor(agentName: string, timeout: number, details: Record<string, unknown> = {}) {
    super(
      ProtocolErrorCode.AGENT_TIMEOUT,
      `Agent '${agentName}' timed out after ${timeout}ms`,
      details,
    );
    this.name = 'AgentTimeoutError';
  }
}

/**
 * Tool not found errors.
 */
export class ToolNotFoundError extends ProtocolError {
  constructor(toolName: string, details: Record<string, unknown> = {}) {
    super(
      ProtocolErrorCode.TOOL_NOT_FOUND,
      `Tool '${toolName}' not found`,
      details,
    );
    this.name = 'ToolNotFoundError';
  }
}

/**
 * Tool execution failed errors.
 */
export class ToolExecutionFailedError extends ProtocolError {
  constructor(toolName: string, reason: string, details: Record<string, unknown> = {}) {
    super(
      ProtocolErrorCode.TOOL_EXECUTION_FAILED,
      `Tool '${toolName}' execution failed: ${reason}`,
      details,
    );
    this.name = 'ToolExecutionFailedError';
  }
}

/**
 * Registration failed errors.
 */
export class RegistrationFailedError extends ProtocolError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(ProtocolErrorCode.REGISTRATION_FAILED, message, details);
    this.name = 'RegistrationFailedError';
  }
}

/**
 * Duplicate agent registration errors.
 */
export class DuplicateAgentError extends ProtocolError {
  constructor(agentName: string, details: Record<string, unknown> = {}) {
    super(
      ProtocolErrorCode.DUPLICATE_AGENT,
      `Agent '${agentName}' is already registered`,
      details,
    );
    this.name = 'DuplicateAgentError';
  }
}

/**
 * Error occurred during remote agent execution.
 */
export class RemoteExecutionError extends Error {
  constructor(
    public readonly agentName: string,
    public readonly originalError: string,
    public readonly details: Record<string, unknown> = {},
  ) {
    super(`Remote execution failed on agent '${agentName}': ${originalError}`);
    this.name = 'RemoteExecutionError';
  }
}
