/**
 * Transport layer for agent communication.
 *
 * Provides various transport implementations (HTTP, WebSocket, TCP)
 * and utilities for remote agent communication.
 */

// Base classes and interfaces
export { Transport, parseEndpoint, MAX_MESSAGE_SIZE } from './transport';

// Error types
export {
  ProtocolError,
  ProtocolErrorCode,
  ConnectionError,
  ConnectionTimeoutError,
  ConnectionClosedError,
  InvalidMessageError,
  UnsupportedVersionError,
  MalformedPayloadError,
  AgentNotFoundError,
  AgentUnavailableError,
  AgentTimeoutError,
  ToolNotFoundError,
  ToolExecutionFailedError,
  RegistrationFailedError,
  DuplicateAgentError,
  RemoteExecutionError,
} from './errors';

// Codec
export {
  PROTOCOL_VERSION,
  ProtocolEnvelope,
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
} from './codec';

// Transport implementations
export { HTTPAgent, HttpTransportConfig, HttpTransportError } from './http';
export { WebSocketAgent, WebSocketTransportConfig, WebSocketTransportError } from './websocket';
export { TCPTransport } from './tcp';
export { GRPCTransport, GRPCTransportConfig } from './grpc-transport';

// Legacy gRPC implementation (standalone, doesn't extend Transport)
export { GrpcAgent, GrpcServer, GrpcTransportError, GrpcTransportConfig, GrpcServerConfig } from './grpc';

// Remote agent
export { RemoteAgent, RemoteAgentConfig } from './remote';
