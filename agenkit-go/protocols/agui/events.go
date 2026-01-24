// Package agui implements the AG-UI (Agent-User Interaction) protocol for Go.
//
// AG-UI provides streaming agent interactions with frontends using structured events.
//
// Reference: https://docs.ag-ui.com/protocol/events
//
// Event Types:
//   - TEXT_MESSAGE_START, TEXT_MESSAGE_CHUNK, TEXT_MESSAGE_COMPLETE
//   - TOOL_CALL_START, TOOL_CALL_CHUNK, TOOL_CALL_COMPLETE
//   - STATE_DELTA (shared state synchronization)
//   - INTERRUPT (human-in-the-loop)
//   - ERROR (error reporting)
//   - ATTACHMENT (multimodal support)
package agui

import (
	"encoding/json"
	"time"
)

// EventType represents AG-UI event types
type EventType string

const (
	// Text message events
	EventTypeTextMessageStart    EventType = "text_message_start"
	EventTypeTextMessageChunk    EventType = "text_message_chunk"
	EventTypeTextMessageComplete EventType = "text_message_complete"

	// Tool call events
	EventTypeToolCallStart    EventType = "tool_call_start"
	EventTypeToolCallChunk    EventType = "tool_call_chunk"
	EventTypeToolCallComplete EventType = "tool_call_complete"

	// State management
	EventTypeStateDelta EventType = "state_delta"

	// Human-in-the-loop
	EventTypeInterrupt EventType = "interrupt"

	// Error handling
	EventTypeError EventType = "error"

	// Multimodal
	EventTypeAttachment EventType = "attachment"

	// Metadata events
	EventTypeMetadata  EventType = "metadata"
	EventTypeHeartbeat EventType = "heartbeat"
)

// InterruptReason represents reasons for agent interruption (HITL)
type InterruptReason string

const (
	InterruptReasonApprovalRequired    InterruptReason = "approval_required"
	InterruptReasonClarificationNeeded InterruptReason = "clarification_needed"
	InterruptReasonToolConfirmation    InterruptReason = "tool_confirmation"
	InterruptReasonEscalation          InterruptReason = "escalation"
	InterruptReasonUserRequested       InterruptReason = "user_requested"
)

// InterruptAction represents actions user can take in response to interruption
type InterruptAction string

const (
	InterruptActionApprove  InterruptAction = "approve"
	InterruptActionReject   InterruptAction = "reject"
	InterruptActionEdit     InterruptAction = "edit"
	InterruptActionRetry    InterruptAction = "retry"
	InterruptActionEscalate InterruptAction = "escalate"
	InterruptActionCancel   InterruptAction = "cancel"
)

// AttachmentType represents types of attachments for multimodal support
type AttachmentType string

const (
	AttachmentTypeImage      AttachmentType = "image"
	AttachmentTypeAudio      AttachmentType = "audio"
	AttachmentTypeVideo      AttachmentType = "video"
	AttachmentTypeFile       AttachmentType = "file"
	AttachmentTypeTranscript AttachmentType = "transcript"
)

// BaseEvent is the base structure for all AG-UI events
type BaseEvent struct {
	EventType EventType              `json:"event_type"`
	Timestamp string                 `json:"timestamp"`
	EventID   *string                `json:"event_id,omitempty"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

// NewBaseEvent creates a new BaseEvent with current timestamp
func NewBaseEvent(eventType EventType) BaseEvent {
	now := time.Now().UTC().Format(time.RFC3339)
	return BaseEvent{
		EventType: eventType,
		Timestamp: now,
		Metadata:  make(map[string]interface{}),
	}
}

// AGUIEvent is the interface that all AG-UI events implement
type AGUIEvent interface {
	GetEventType() EventType
	GetTimestamp() string
	ToJSON() ([]byte, error)
}

// GetEventType returns the event type
func (e *BaseEvent) GetEventType() EventType {
	return e.EventType
}

// GetTimestamp returns the event timestamp
func (e *BaseEvent) GetTimestamp() string {
	return e.Timestamp
}

// ToJSON converts the event to JSON
func (e *BaseEvent) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// TextMessageStart event indicates start of a text message
type TextMessageStart struct {
	BaseEvent
	MessageID string                 `json:"message_id"`
	Role      string                 `json:"role"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

// NewTextMessageStart creates a new TextMessageStart event
func NewTextMessageStart(messageID, role string) *TextMessageStart {
	return &TextMessageStart{
		BaseEvent: NewBaseEvent(EventTypeTextMessageStart),
		MessageID: messageID,
		Role:      role,
		Metadata:  make(map[string]interface{}),
	}
}

// ToJSON converts the event to JSON
func (e *TextMessageStart) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// TextMessageChunk event represents a chunk of streaming text
type TextMessageChunk struct {
	BaseEvent
	MessageID string                 `json:"message_id"`
	Content   string                 `json:"content"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

// NewTextMessageChunk creates a new TextMessageChunk event
func NewTextMessageChunk(messageID, content string) *TextMessageChunk {
	return &TextMessageChunk{
		BaseEvent: NewBaseEvent(EventTypeTextMessageChunk),
		MessageID: messageID,
		Content:   content,
		Metadata:  make(map[string]interface{}),
	}
}

// ToJSON converts the event to JSON
func (e *TextMessageChunk) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// TextMessageComplete event indicates completion of a text message
type TextMessageComplete struct {
	BaseEvent
	MessageID    string                 `json:"message_id"`
	Content      string                 `json:"content"`
	FinishReason string                 `json:"finish_reason"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}

// NewTextMessageComplete creates a new TextMessageComplete event
func NewTextMessageComplete(messageID, content, finishReason string) *TextMessageComplete {
	return &TextMessageComplete{
		BaseEvent:    NewBaseEvent(EventTypeTextMessageComplete),
		MessageID:    messageID,
		Content:      content,
		FinishReason: finishReason,
		Metadata:     make(map[string]interface{}),
	}
}

// ToJSON converts the event to JSON
func (e *TextMessageComplete) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// ToolCallStart event indicates start of a tool call
type ToolCallStart struct {
	BaseEvent
	ToolCallID string                 `json:"tool_call_id"`
	ToolName   string                 `json:"tool_name"`
	Arguments  map[string]interface{} `json:"arguments,omitempty"`
	Metadata   map[string]interface{} `json:"metadata,omitempty"`
}

// NewToolCallStart creates a new ToolCallStart event
func NewToolCallStart(toolCallID, toolName string, arguments map[string]interface{}) *ToolCallStart {
	if arguments == nil {
		arguments = make(map[string]interface{})
	}
	return &ToolCallStart{
		BaseEvent:  NewBaseEvent(EventTypeToolCallStart),
		ToolCallID: toolCallID,
		ToolName:   toolName,
		Arguments:  arguments,
		Metadata:   make(map[string]interface{}),
	}
}

// ToJSON converts the event to JSON
func (e *ToolCallStart) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// ToolCallChunk event represents a chunk of tool execution output
type ToolCallChunk struct {
	BaseEvent
	ToolCallID string                 `json:"tool_call_id"`
	Content    string                 `json:"content"`
	Metadata   map[string]interface{} `json:"metadata,omitempty"`
}

// NewToolCallChunk creates a new ToolCallChunk event
func NewToolCallChunk(toolCallID, content string) *ToolCallChunk {
	return &ToolCallChunk{
		BaseEvent:  NewBaseEvent(EventTypeToolCallChunk),
		ToolCallID: toolCallID,
		Content:    content,
		Metadata:   make(map[string]interface{}),
	}
}

// ToJSON converts the event to JSON
func (e *ToolCallChunk) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// ToolCallComplete event indicates completion of a tool call
type ToolCallComplete struct {
	BaseEvent
	ToolCallID string                 `json:"tool_call_id"`
	Result     interface{}            `json:"result"`
	Error      *string                `json:"error,omitempty"`
	Metadata   map[string]interface{} `json:"metadata,omitempty"`
}

// NewToolCallComplete creates a new ToolCallComplete event
func NewToolCallComplete(toolCallID string, result interface{}, err *string) *ToolCallComplete {
	return &ToolCallComplete{
		BaseEvent:  NewBaseEvent(EventTypeToolCallComplete),
		ToolCallID: toolCallID,
		Result:     result,
		Error:      err,
		Metadata:   make(map[string]interface{}),
	}
}

// ToJSON converts the event to JSON
func (e *ToolCallComplete) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// StateDelta event for shared state synchronization
type StateDelta struct {
	BaseEvent
	StateID string                 `json:"state_id"`
	Delta   map[string]interface{} `json:"delta"`
	Version int64                  `json:"version"`
}

// NewStateDelta creates a new StateDelta event
func NewStateDelta(stateID string, delta map[string]interface{}, version int64) *StateDelta {
	if delta == nil {
		delta = make(map[string]interface{})
	}
	return &StateDelta{
		BaseEvent: NewBaseEvent(EventTypeStateDelta),
		StateID:   stateID,
		Delta:     delta,
		Version:   version,
	}
}

// ToJSON converts the event to JSON
func (e *StateDelta) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// Interrupt event for human-in-the-loop interactions
type Interrupt struct {
	BaseEvent
	InterruptID    string                 `json:"interrupt_id"`
	Reason         InterruptReason        `json:"reason"`
	Message        string                 `json:"message"`
	Context        map[string]interface{} `json:"context,omitempty"`
	Actions        []InterruptAction      `json:"actions,omitempty"`
	TimeoutSeconds *int                   `json:"timeout_seconds,omitempty"`
}

// NewInterrupt creates a new Interrupt event
func NewInterrupt(interruptID string, reason InterruptReason, message string) *Interrupt {
	return &Interrupt{
		BaseEvent:   NewBaseEvent(EventTypeInterrupt),
		InterruptID: interruptID,
		Reason:      reason,
		Message:     message,
		Context:     make(map[string]interface{}),
		Actions:     []InterruptAction{},
	}
}

// ToJSON converts the event to JSON
func (e *Interrupt) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// InterruptResponse represents user response to an interrupt
type InterruptResponse struct {
	InterruptID string                 `json:"interrupt_id"`
	Action      InterruptAction        `json:"action"`
	Data        map[string]interface{} `json:"data,omitempty"`
	Timestamp   string                 `json:"timestamp"`
}

// NewInterruptResponse creates a new InterruptResponse
func NewInterruptResponse(interruptID string, action InterruptAction) *InterruptResponse {
	return &InterruptResponse{
		InterruptID: interruptID,
		Action:      action,
		Data:        make(map[string]interface{}),
		Timestamp:   time.Now().UTC().Format(time.RFC3339),
	}
}

// ErrorEvent represents an error during agent execution
type ErrorEvent struct {
	BaseEvent
	ErrorCode    string                 `json:"error_code"`
	ErrorMessage string                 `json:"error_message"`
	ErrorDetails map[string]interface{} `json:"error_details,omitempty"`
	Recoverable  bool                   `json:"recoverable"`
}

// NewErrorEvent creates a new ErrorEvent
func NewErrorEvent(code, message string, recoverable bool) *ErrorEvent {
	return &ErrorEvent{
		BaseEvent:    NewBaseEvent(EventTypeError),
		ErrorCode:    code,
		ErrorMessage: message,
		ErrorDetails: make(map[string]interface{}),
		Recoverable:  recoverable,
	}
}

// ToJSON converts the event to JSON
func (e *ErrorEvent) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// Attachment represents multimodal attachments
type Attachment struct {
	BaseEvent
	AttachmentID   string                 `json:"attachment_id"`
	AttachmentType AttachmentType         `json:"attachment_type"`
	URL            *string                `json:"url,omitempty"`
	Data           *string                `json:"data,omitempty"`
	MimeType       string                 `json:"mime_type"`
	Size           *int64                 `json:"size,omitempty"`
	Metadata       map[string]interface{} `json:"metadata,omitempty"`
}

// NewAttachment creates a new Attachment event
func NewAttachment(attachmentID string, attachmentType AttachmentType, mimeType string) *Attachment {
	return &Attachment{
		BaseEvent:      NewBaseEvent(EventTypeAttachment),
		AttachmentID:   attachmentID,
		AttachmentType: attachmentType,
		MimeType:       mimeType,
		Metadata:       make(map[string]interface{}),
	}
}

// ToJSON converts the event to JSON
func (e *Attachment) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// MetadataEvent contains agent metadata and capabilities
type MetadataEvent struct {
	BaseEvent
	Data map[string]interface{} `json:"data"`
}

// NewMetadataEvent creates a new MetadataEvent
func NewMetadataEvent(data map[string]interface{}) *MetadataEvent {
	if data == nil {
		data = make(map[string]interface{})
	}
	return &MetadataEvent{
		BaseEvent: NewBaseEvent(EventTypeMetadata),
		Data:      data,
	}
}

// ToJSON converts the event to JSON
func (e *MetadataEvent) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// HeartbeatEvent for connection keep-alive
type HeartbeatEvent struct {
	BaseEvent
	SequenceNumber int64 `json:"sequence_number"`
}

// NewHeartbeatEvent creates a new HeartbeatEvent
func NewHeartbeatEvent(sequenceNumber int64) *HeartbeatEvent {
	return &HeartbeatEvent{
		BaseEvent:      NewBaseEvent(EventTypeHeartbeat),
		SequenceNumber: sequenceNumber,
	}
}

// ToJSON converts the event to JSON
func (e *HeartbeatEvent) ToJSON() ([]byte, error) {
	return json.Marshal(e)
}

// ParseEvent parses a JSON-encoded AG-UI event
func ParseEvent(data []byte) (AGUIEvent, error) {
	// First parse to get event type
	var base BaseEvent
	if err := json.Unmarshal(data, &base); err != nil {
		return nil, err
	}

	// Parse to specific type based on event_type
	switch base.EventType {
	case EventTypeTextMessageStart:
		var event TextMessageStart
		if err := json.Unmarshal(data, &event); err != nil {
			return nil, err
		}
		return &event, nil

	case EventTypeTextMessageChunk:
		var event TextMessageChunk
		if err := json.Unmarshal(data, &event); err != nil {
			return nil, err
		}
		return &event, nil

	case EventTypeTextMessageComplete:
		var event TextMessageComplete
		if err := json.Unmarshal(data, &event); err != nil {
			return nil, err
		}
		return &event, nil

	case EventTypeToolCallStart:
		var event ToolCallStart
		if err := json.Unmarshal(data, &event); err != nil {
			return nil, err
		}
		return &event, nil

	case EventTypeToolCallChunk:
		var event ToolCallChunk
		if err := json.Unmarshal(data, &event); err != nil {
			return nil, err
		}
		return &event, nil

	case EventTypeToolCallComplete:
		var event ToolCallComplete
		if err := json.Unmarshal(data, &event); err != nil {
			return nil, err
		}
		return &event, nil

	case EventTypeStateDelta:
		var event StateDelta
		if err := json.Unmarshal(data, &event); err != nil {
			return nil, err
		}
		return &event, nil

	case EventTypeInterrupt:
		var event Interrupt
		if err := json.Unmarshal(data, &event); err != nil {
			return nil, err
		}
		return &event, nil

	case EventTypeError:
		var event ErrorEvent
		if err := json.Unmarshal(data, &event); err != nil {
			return nil, err
		}
		return &event, nil

	case EventTypeAttachment:
		var event Attachment
		if err := json.Unmarshal(data, &event); err != nil {
			return nil, err
		}
		return &event, nil

	case EventTypeMetadata:
		var event MetadataEvent
		if err := json.Unmarshal(data, &event); err != nil {
			return nil, err
		}
		return &event, nil

	case EventTypeHeartbeat:
		var event HeartbeatEvent
		if err := json.Unmarshal(data, &event); err != nil {
			return nil, err
		}
		return &event, nil

	default:
		// Unknown event type - return base event
		return &base, nil
	}
}
