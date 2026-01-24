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

// Transports will be added when implemented
// export * from './transports/http.js';
// export * from './transports/websocket.js';
