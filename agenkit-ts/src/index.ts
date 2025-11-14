/**
 * Agenkit TypeScript - Minimal, composable interfaces for AI agents.
 *
 * @packageDocumentation
 */

// Core interfaces
export {
  Agent,
  Message,
  Tool,
  ToolResult,
  createMessage,
  validateMessage,
} from './core/interfaces';

// Adapters
export {
  LocalAgent,
  ProcessFunction,
  ProcessStreamFunction,
  LocalAgentConfig,
  createEchoAgent,
  createCounterAgent,
} from './adapters/local';

// Transports
export { HTTPAgent, HttpTransportConfig, HttpTransportError } from './transports/http';
export {
  WebSocketAgent,
  WebSocketTransportConfig,
  WebSocketTransportError,
} from './transports/websocket';

// Middleware
export { Middleware, applyMiddleware, BaseMiddleware } from './middleware/base';
export { RetryMiddleware, RetryConfig, retry } from './middleware/retry';
export { TimeoutMiddleware, TimeoutConfig, TimeoutError, timeout } from './middleware/timeout';
export {
  CircuitBreakerMiddleware,
  CircuitBreakerConfig,
  CircuitBreakerError,
  CircuitState,
  circuitBreaker,
} from './middleware/circuit-breaker';

// LLM Adapters
export { OpenAIAgent, OpenAIConfig } from './llm/openai';
export { AnthropicAgent, AnthropicConfig } from './llm/anthropic';
