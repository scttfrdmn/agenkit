/**
 * AG-UI Protocol Event Types and Data Structures
 *
 * Implements the AG-UI (Agent-User Interaction) protocol event types
 * for streaming agent interactions with frontends.
 *
 * Reference: https://docs.ag-ui.com/protocol/events
 *
 * Event Types Implemented:
 * - TEXT_MESSAGE_START, TEXT_MESSAGE_CHUNK, TEXT_MESSAGE_COMPLETE
 * - TOOL_CALL_START, TOOL_CALL_CHUNK, TOOL_CALL_COMPLETE
 * - STATE_DELTA (shared state synchronization)
 * - INTERRUPT (human-in-the-loop)
 * - ERROR (error reporting)
 * - ATTACHMENT (multimodal support)
 * - METADATA, HEARTBEAT (system events)
 */

/**
 * agenkit's own metadata-event schema version -- NOT a version of the AG-UI
 * wire protocol itself. AG-UI (docs.ag-ui.com) has no numbered spec revision
 * to align with, so this was previously a made-up "1.0" that looked like an
 * upstream protocol version but wasn't (agenkit#781 item D: "a wrong
 * version is worse than an absent one"). One named constant per language,
 * so all emitters advertise the same value and a bump can't drift between
 * them.
 */
export const AGUI_METADATA_SCHEMA_VERSION = '1.0';

/**
 * AG-UI event type enumeration
 */
export enum EventType {
  // Text message events
  TEXT_MESSAGE_START = 'text_message_start',
  TEXT_MESSAGE_CHUNK = 'text_message_chunk',
  TEXT_MESSAGE_COMPLETE = 'text_message_complete',

  // Tool call events
  TOOL_CALL_START = 'tool_call_start',
  TOOL_CALL_CHUNK = 'tool_call_chunk',
  TOOL_CALL_COMPLETE = 'tool_call_complete',

  // State management
  STATE_DELTA = 'state_delta',

  // Human-in-the-loop
  INTERRUPT = 'interrupt',
  INTERRUPT_RESPONSE = 'interrupt_response',

  // Error handling
  ERROR = 'error',

  // Multimodal
  ATTACHMENT = 'attachment',

  // Metadata events
  METADATA = 'metadata',
  HEARTBEAT = 'heartbeat',
}

/**
 * Reasons for agent interruption (HITL)
 */
export enum InterruptReason {
  APPROVAL_REQUIRED = 'approval_required',
  CLARIFICATION_NEEDED = 'clarification_needed',
  TOOL_CONFIRMATION = 'tool_confirmation',
  ESCALATION = 'escalation',
  USER_REQUESTED = 'user_requested',
}

/**
 * Actions user can take in response to interruption
 */
export enum InterruptAction {
  APPROVE = 'approve',
  REJECT = 'reject',
  EDIT = 'edit',
  RETRY = 'retry',
  ESCALATE = 'escalate',
  CANCEL = 'cancel',
  CONTINUE = 'continue',
}

/**
 * Types of attachments for multimodal support
 */
export enum AttachmentType {
  IMAGE = 'image',
  AUDIO = 'audio',
  VIDEO = 'video',
  FILE = 'file',
  TRANSCRIPT = 'transcript',
}

/**
 * Base interface for all AG-UI events
 */
export interface BaseEvent {
  event_type: EventType;
  timestamp: string;
  event_id?: string;
  metadata?: Record<string, any>;
}

/**
 * Base class for AG-UI events with common functionality
 */
export abstract class AGUIEvent implements BaseEvent {
  event_type: EventType;
  timestamp: string;
  event_id?: string;
  metadata: Record<string, any>;

  constructor(
    eventType: EventType,
    metadata: Record<string, any> = {},
    eventId?: string,
  ) {
    this.event_type = eventType;
    this.timestamp = new Date().toISOString();
    this.event_id = eventId;
    this.metadata = metadata;
  }

  /**
   * Convert event to plain object for JSON serialization
   */
  toJSON(): Record<string, any> {
    return {
      event_type: this.event_type,
      timestamp: this.timestamp,
      event_id: this.event_id,
      ...this.getEventData(),
      ...this.metadata, // Spread metadata at top level
    };
  }

  /**
   * Convert event to JSON string
   */
  toString(): string {
    return JSON.stringify(this.toJSON());
  }

  /**
   * Get event-specific data for serialization
   */
  protected abstract getEventData(): Record<string, any>;
}

/**
 * Start of a text message from the agent
 *
 * Signals that the agent is beginning to generate a text response.
 */
export class TextMessageStart extends AGUIEvent {
  message_id?: string;
  role: string;

  constructor(
    role: string = 'assistant',
    messageId?: string,
    metadata: Record<string, any> = {},
  ) {
    super(EventType.TEXT_MESSAGE_START, metadata);
    this.message_id = messageId;
    this.role = role;
  }

  protected getEventData(): Record<string, any> {
    return {
      message_id: this.message_id,
      role: this.role,
    };
  }
}

/**
 * Chunk of text message content (streaming)
 *
 * Contains incremental text content as the agent generates the response.
 */
export class TextMessageChunk extends AGUIEvent {
  message_id?: string;
  content: string;

  constructor(
    content: string,
    messageId?: string,
    metadata: Record<string, any> = {},
  ) {
    super(EventType.TEXT_MESSAGE_CHUNK, metadata);
    this.message_id = messageId;
    this.content = content;
  }

  protected getEventData(): Record<string, any> {
    return {
      message_id: this.message_id,
      content: this.content,
    };
  }
}

/**
 * Complete text message from the agent
 *
 * Signals that the agent has finished generating the text response.
 */
export class TextMessageComplete extends AGUIEvent {
  message_id?: string;
  content: string;
  finish_reason?: string;

  constructor(
    content: string,
    finishReason?: string,
    messageId?: string,
    metadata: Record<string, any> = {},
  ) {
    super(EventType.TEXT_MESSAGE_COMPLETE, metadata);
    this.message_id = messageId;
    this.content = content;
    this.finish_reason = finishReason;
  }

  protected getEventData(): Record<string, any> {
    return {
      message_id: this.message_id,
      content: this.content,
      finish_reason: this.finish_reason,
    };
  }
}

/**
 * Start of a tool call execution
 *
 * Signals that the agent is beginning to execute a tool.
 */
export class ToolCallStart extends AGUIEvent {
  tool_call_id?: string;
  tool_name: string;
  arguments: Record<string, any>;

  constructor(
    toolName: string,
    args: Record<string, any> = {},
    toolCallId?: string,
    metadata: Record<string, any> = {},
  ) {
    super(EventType.TOOL_CALL_START, metadata);
    this.tool_call_id = toolCallId;
    this.tool_name = toolName;
    this.arguments = args;
  }

  protected getEventData(): Record<string, any> {
    return {
      tool_call_id: this.tool_call_id,
      tool_name: this.tool_name,
      arguments: this.arguments,
    };
  }
}

/**
 * Chunk of tool call execution progress (streaming)
 *
 * Contains incremental updates about tool execution progress.
 */
export class ToolCallChunk extends AGUIEvent {
  tool_call_id?: string;
  progress: string;
  percentage?: number;

  constructor(
    progress: string,
    percentage?: number,
    toolCallId?: string,
    metadata: Record<string, any> = {},
  ) {
    super(EventType.TOOL_CALL_CHUNK, metadata);
    this.tool_call_id = toolCallId;
    this.progress = progress;
    this.percentage = percentage;
  }

  protected getEventData(): Record<string, any> {
    return {
      tool_call_id: this.tool_call_id,
      progress: this.progress,
      percentage: this.percentage,
    };
  }
}

/**
 * Complete tool call result
 *
 * Contains the final result of tool execution.
 */
export class ToolCallComplete extends AGUIEvent {
  tool_call_id?: string;
  tool_name: string;
  result: any;
  success: boolean;
  error?: string;

  constructor(
    toolName: string,
    result: any,
    success: boolean = true,
    error?: string,
    toolCallId?: string,
    metadata: Record<string, any> = {},
  ) {
    super(EventType.TOOL_CALL_COMPLETE, metadata);
    this.tool_call_id = toolCallId;
    this.tool_name = toolName;
    this.result = result;
    this.success = success;
    this.error = error;
  }

  protected getEventData(): Record<string, any> {
    return {
      tool_call_id: this.tool_call_id,
      tool_name: this.tool_name,
      result: this.result,
      success: this.success,
      error: this.error,
    };
  }
}

/**
 * Incremental state update (event sourcing pattern)
 *
 * Contains partial state changes to synchronize agent and frontend state.
 * Instead of sending full state snapshots, only changes are transmitted.
 */
export class StateDelta extends AGUIEvent {
  delta: Record<string, any>;
  path?: string[];

  constructor(
    delta: Record<string, any>,
    path?: string[],
    metadata: Record<string, any> = {},
  ) {
    super(EventType.STATE_DELTA, metadata);
    this.delta = delta;
    this.path = path;
  }

  protected getEventData(): Record<string, any> {
    return {
      delta: this.delta,
      path: this.path,
    };
  }
}

/**
 * Request for human intervention (HITL)
 *
 * Signals that the agent requires human input to proceed.
 */
export class Interrupt extends AGUIEvent {
  reason: InterruptReason;
  message: string;
  available_actions: InterruptAction[];
  context: Record<string, any>;
  interrupt_id?: string;

  constructor(
    reason: InterruptReason,
    message: string,
    availableActions: InterruptAction[] = [],
    context: Record<string, any> = {},
    interruptId?: string,
    metadata: Record<string, any> = {},
  ) {
    super(EventType.INTERRUPT, metadata);
    this.reason = reason;
    this.message = message;
    this.available_actions = availableActions;
    this.context = context;
    this.interrupt_id = interruptId;
  }

  protected getEventData(): Record<string, any> {
    return {
      reason: this.reason,
      message: this.message,
      available_actions: this.available_actions,
      context: this.context,
      interrupt_id: this.interrupt_id,
    };
  }
}

/**
 * Human response to an interrupt
 *
 * Contains the user's decision in response to an interrupt event.
 */
export class InterruptResponse extends AGUIEvent {
  interrupt_id: string;
  action: InterruptAction;
  data?: any;

  constructor(
    interruptId: string,
    action: InterruptAction,
    data?: any,
    metadata: Record<string, any> = {},
  ) {
    super(EventType.INTERRUPT_RESPONSE, metadata);
    this.interrupt_id = interruptId;
    this.action = action;
    this.data = data;
  }

  protected getEventData(): Record<string, any> {
    return {
      interrupt_id: this.interrupt_id,
      action: this.action,
      data: this.data,
    };
  }
}

/**
 * Error event for reporting failures
 */
export class ErrorEvent extends AGUIEvent {
  error_code: string;
  error_message: string;
  recoverable: boolean;
  details?: any;

  constructor(
    errorCode: string,
    errorMessage: string,
    recoverable: boolean = true,
    details?: any,
    metadata: Record<string, any> = {},
  ) {
    super(EventType.ERROR, metadata);
    this.error_code = errorCode;
    this.error_message = errorMessage;
    this.recoverable = recoverable;
    this.details = details;
  }

  protected getEventData(): Record<string, any> {
    return {
      error_code: this.error_code,
      error_message: this.error_message,
      recoverable: this.recoverable,
      details: this.details,
    };
  }
}

/**
 * Attachment for multimodal content
 */
export class Attachment extends AGUIEvent {
  attachment_type: AttachmentType;
  content_type: string;
  url?: string;
  data?: string;
  filename?: string;
  size?: number;

  constructor(
    attachmentType: AttachmentType,
    contentType: string,
    url?: string,
    data?: string,
    filename?: string,
    size?: number,
    metadata: Record<string, any> = {},
  ) {
    super(EventType.ATTACHMENT, metadata);
    this.attachment_type = attachmentType;
    this.content_type = contentType;
    this.url = url;
    this.data = data;
    this.filename = filename;
    this.size = size;
  }

  protected getEventData(): Record<string, any> {
    return {
      attachment_type: this.attachment_type,
      content_type: this.content_type,
      url: this.url,
      data: this.data,
      filename: this.filename,
      size: this.size,
    };
  }
}

/**
 * Metadata event for agent capabilities and configuration
 */
export class MetadataEvent extends AGUIEvent {
  data: Record<string, any>;

  constructor(data: Record<string, any>, metadata: Record<string, any> = {}) {
    super(EventType.METADATA, metadata);
    this.data = data;
  }

  protected getEventData(): Record<string, any> {
    return {
      ...this.data,
    };
  }
}

/**
 * Heartbeat event for keep-alive signaling
 */
export class HeartbeatEvent extends AGUIEvent {
  interval_ms?: number;

  constructor(intervalMs?: number, metadata: Record<string, any> = {}) {
    super(EventType.HEARTBEAT, metadata);
    this.interval_ms = intervalMs;
  }

  protected getEventData(): Record<string, any> {
    return {
      interval_ms: this.interval_ms,
    };
  }
}

/**
 * Parse a JSON event object into the appropriate event class
 */
export function parseEvent(data: Record<string, any>): AGUIEvent {
  const eventType = data.event_type as EventType;

  switch (eventType) {
    case EventType.TEXT_MESSAGE_START:
      return Object.assign(
        new TextMessageStart(data.role, data.message_id, data.metadata),
        data,
      );

    case EventType.TEXT_MESSAGE_CHUNK:
      return Object.assign(
        new TextMessageChunk(data.content, data.message_id, data.metadata),
        data,
      );

    case EventType.TEXT_MESSAGE_COMPLETE:
      return Object.assign(
        new TextMessageComplete(
          data.content,
          data.finish_reason,
          data.message_id,
          data.metadata,
        ),
        data,
      );

    case EventType.TOOL_CALL_START:
      return Object.assign(
        new ToolCallStart(
          data.tool_name,
          data.arguments,
          data.tool_call_id,
          data.metadata,
        ),
        data,
      );

    case EventType.TOOL_CALL_CHUNK:
      return Object.assign(
        new ToolCallChunk(
          data.progress,
          data.percentage,
          data.tool_call_id,
          data.metadata,
        ),
        data,
      );

    case EventType.TOOL_CALL_COMPLETE:
      return Object.assign(
        new ToolCallComplete(
          data.tool_name,
          data.result,
          data.success,
          data.error,
          data.tool_call_id,
          data.metadata,
        ),
        data,
      );

    case EventType.STATE_DELTA:
      return Object.assign(
        new StateDelta(data.delta, data.path, data.metadata),
        data,
      );

    case EventType.INTERRUPT:
      return Object.assign(
        new Interrupt(
          data.reason,
          data.message,
          data.available_actions,
          data.context,
          data.interrupt_id,
          data.metadata,
        ),
        data,
      );

    case EventType.INTERRUPT_RESPONSE:
      return Object.assign(
        new InterruptResponse(
          data.interrupt_id,
          data.action,
          data.data,
          data.metadata,
        ),
        data,
      );

    case EventType.ERROR:
      return Object.assign(
        new ErrorEvent(
          data.error_code,
          data.error_message,
          data.recoverable,
          data.details,
          data.metadata,
        ),
        data,
      );

    case EventType.ATTACHMENT:
      return Object.assign(
        new Attachment(
          data.attachment_type,
          data.content_type,
          data.url,
          data.data,
          data.filename,
          data.size,
          data.metadata,
        ),
        data,
      );

    case EventType.METADATA:
      return Object.assign(new MetadataEvent(data, data.metadata), data);

    case EventType.HEARTBEAT:
      return Object.assign(
        new HeartbeatEvent(data.interval_ms, data.metadata),
        data,
      );

    default:
      throw new Error(`Unknown event type: ${eventType}`);
  }
}
