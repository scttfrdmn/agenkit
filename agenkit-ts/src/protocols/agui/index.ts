/**
 * AG-UI (Agent-User Interaction) Protocol
 *
 * Provides streaming agent-to-frontend communication using the AG-UI protocol.
 *
 * Reference: https://docs.ag-ui.com
 *
 * @packageDocumentation
 */

// Event types and classes
export {
  AGUI_METADATA_SCHEMA_VERSION,
  EventType,
  InterruptReason,
  InterruptAction,
  AttachmentType,
  BaseEvent,
  AGUIEvent,
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
} from './events.js';

// Core adapter
export {
  AGUIAdapter,
  AGUIAdapterConfig,
  wrapAgentAsAGUI,
} from './adapter.js';

// Human-in-the-loop integration
export {
  AGUIHumanInLoopAdapter,
  AGUIHumanInLoopConfig,
  wrapHITLAgentAsAGUI,
} from './hitl.js';

// HTTP/SSE transport
export {
  SSEFormatter,
  AGUISSEStream,
  SSEStreamConfig,
  SSEHandlerConfig,
  createSSEHandler,
  createSSEResponseIterator,
  sseKeepAlive,
} from './transports/http.js';

// WebSocket transport
export {
  WebSocket,
  WebSocketMessageFormat,
  WebSocketHandlerConfig,
  AGUIWebSocketStream,
  AGUIWebSocketHandler,
  createWebSocketHandler,
} from './transports/websocket.js';
