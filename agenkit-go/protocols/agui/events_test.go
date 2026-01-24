package agui

import (
	"encoding/json"
	"testing"
)

func TestEventTypes(t *testing.T) {
	tests := []struct {
		name      string
		eventType EventType
		expected  string
	}{
		{"TextMessageStart", EventTypeTextMessageStart, "text_message_start"},
		{"TextMessageChunk", EventTypeTextMessageChunk, "text_message_chunk"},
		{"TextMessageComplete", EventTypeTextMessageComplete, "text_message_complete"},
		{"ToolCallStart", EventTypeToolCallStart, "tool_call_start"},
		{"Interrupt", EventTypeInterrupt, "interrupt"},
		{"Error", EventTypeError, "error"},
		{"Metadata", EventTypeMetadata, "metadata"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if string(tt.eventType) != tt.expected {
				t.Errorf("EventType %s = %s, want %s", tt.name, tt.eventType, tt.expected)
			}
		})
	}
}

func TestInterruptReasons(t *testing.T) {
	tests := []struct {
		name     string
		reason   InterruptReason
		expected string
	}{
		{"ApprovalRequired", InterruptReasonApprovalRequired, "approval_required"},
		{"ClarificationNeeded", InterruptReasonClarificationNeeded, "clarification_needed"},
		{"ToolConfirmation", InterruptReasonToolConfirmation, "tool_confirmation"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if string(tt.reason) != tt.expected {
				t.Errorf("InterruptReason %s = %s, want %s", tt.name, tt.reason, tt.expected)
			}
		})
	}
}

func TestTextMessageStart(t *testing.T) {
	event := NewTextMessageStart("msg-123", "assistant")

	if event.GetEventType() != EventTypeTextMessageStart {
		t.Errorf("EventType = %s, want %s", event.GetEventType(), EventTypeTextMessageStart)
	}

	if event.MessageID != "msg-123" {
		t.Errorf("MessageID = %s, want msg-123", event.MessageID)
	}

	if event.Role != "assistant" {
		t.Errorf("Role = %s, want assistant", event.Role)
	}

	if event.GetTimestamp() == "" {
		t.Error("Timestamp should not be empty")
	}
}

func TestTextMessageChunk(t *testing.T) {
	event := NewTextMessageChunk("msg-123", "Hello ")

	if event.GetEventType() != EventTypeTextMessageChunk {
		t.Errorf("EventType = %s, want %s", event.GetEventType(), EventTypeTextMessageChunk)
	}

	if event.Content != "Hello " {
		t.Errorf("Content = %s, want 'Hello '", event.Content)
	}
}

func TestTextMessageComplete(t *testing.T) {
	event := NewTextMessageComplete("msg-123", "Hello world", "stop")

	if event.GetEventType() != EventTypeTextMessageComplete {
		t.Errorf("EventType = %s, want %s", event.GetEventType(), EventTypeTextMessageComplete)
	}

	if event.Content != "Hello world" {
		t.Errorf("Content = %s, want 'Hello world'", event.Content)
	}

	if event.FinishReason != "stop" {
		t.Errorf("FinishReason = %s, want stop", event.FinishReason)
	}
}

func TestToolCallStart(t *testing.T) {
	args := map[string]interface{}{
		"query": "weather in SF",
	}
	event := NewToolCallStart("tool-123", "get_weather", args)

	if event.GetEventType() != EventTypeToolCallStart {
		t.Errorf("EventType = %s, want %s", event.GetEventType(), EventTypeToolCallStart)
	}

	if event.ToolName != "get_weather" {
		t.Errorf("ToolName = %s, want get_weather", event.ToolName)
	}

	if query, ok := event.Arguments["query"].(string); !ok || query != "weather in SF" {
		t.Errorf("Arguments[query] = %v, want 'weather in SF'", event.Arguments["query"])
	}
}

func TestInterrupt(t *testing.T) {
	event := NewInterrupt("int-123", InterruptReasonApprovalRequired, "Approval needed")

	if event.GetEventType() != EventTypeInterrupt {
		t.Errorf("EventType = %s, want %s", event.GetEventType(), EventTypeInterrupt)
	}

	if event.Reason != InterruptReasonApprovalRequired {
		t.Errorf("Reason = %s, want %s", event.Reason, InterruptReasonApprovalRequired)
	}

	if event.Message != "Approval needed" {
		t.Errorf("Message = %s, want 'Approval needed'", event.Message)
	}

	// Test adding context and actions
	event.Context["confidence"] = 0.6
	event.Actions = []InterruptAction{InterruptActionApprove, InterruptActionReject}

	if conf, ok := event.Context["confidence"].(float64); !ok || conf != 0.6 {
		t.Errorf("Context[confidence] = %v, want 0.6", event.Context["confidence"])
	}

	if len(event.Actions) != 2 {
		t.Errorf("len(Actions) = %d, want 2", len(event.Actions))
	}
}

func TestErrorEvent(t *testing.T) {
	event := NewErrorEvent("ValueError", "Invalid input", true)

	if event.GetEventType() != EventTypeError {
		t.Errorf("EventType = %s, want %s", event.GetEventType(), EventTypeError)
	}

	if event.ErrorCode != "ValueError" {
		t.Errorf("ErrorCode = %s, want ValueError", event.ErrorCode)
	}

	if event.ErrorMessage != "Invalid input" {
		t.Errorf("ErrorMessage = %s, want 'Invalid input'", event.ErrorMessage)
	}

	if !event.Recoverable {
		t.Error("Recoverable should be true")
	}
}

func TestStateDelta(t *testing.T) {
	delta := map[string]interface{}{
		"counter": 42,
		"status":  "active",
	}
	event := NewStateDelta("state-123", delta, 5)

	if event.GetEventType() != EventTypeStateDelta {
		t.Errorf("EventType = %s, want %s", event.GetEventType(), EventTypeStateDelta)
	}

	if event.Version != 5 {
		t.Errorf("Version = %d, want 5", event.Version)
	}

	if counter, ok := event.Delta["counter"].(int); !ok || counter != 42 {
		t.Errorf("Delta[counter] = %v, want 42", event.Delta["counter"])
	}
}

func TestAttachment(t *testing.T) {
	event := NewAttachment("att-123", AttachmentTypeImage, "image/png")

	if event.GetEventType() != EventTypeAttachment {
		t.Errorf("EventType = %s, want %s", event.GetEventType(), EventTypeAttachment)
	}

	if event.AttachmentType != AttachmentTypeImage {
		t.Errorf("AttachmentType = %s, want %s", event.AttachmentType, AttachmentTypeImage)
	}

	if event.MimeType != "image/png" {
		t.Errorf("MimeType = %s, want image/png", event.MimeType)
	}
}

func TestMetadataEvent(t *testing.T) {
	data := map[string]interface{}{
		"agent_name": "TestAgent",
		"version":    "1.0",
	}
	event := NewMetadataEvent(data)

	if event.GetEventType() != EventTypeMetadata {
		t.Errorf("EventType = %s, want %s", event.GetEventType(), EventTypeMetadata)
	}

	if name, ok := event.Data["agent_name"].(string); !ok || name != "TestAgent" {
		t.Errorf("Data[agent_name] = %v, want TestAgent", event.Data["agent_name"])
	}
}

func TestHeartbeatEvent(t *testing.T) {
	event := NewHeartbeatEvent(42)

	if event.GetEventType() != EventTypeHeartbeat {
		t.Errorf("EventType = %s, want %s", event.GetEventType(), EventTypeHeartbeat)
	}

	if event.SequenceNumber != 42 {
		t.Errorf("SequenceNumber = %d, want 42", event.SequenceNumber)
	}
}

func TestEventJSONSerialization(t *testing.T) {
	tests := []struct {
		name  string
		event AGUIEvent
	}{
		{"TextMessageStart", NewTextMessageStart("msg-1", "user")},
		{"TextMessageChunk", NewTextMessageChunk("msg-1", "Hello")},
		{"TextMessageComplete", NewTextMessageComplete("msg-1", "Hello world", "stop")},
		{"Interrupt", NewInterrupt("int-1", InterruptReasonApprovalRequired, "Need approval")},
		{"Error", NewErrorEvent("TestError", "Something went wrong", true)},
		{"Metadata", NewMetadataEvent(map[string]interface{}{"key": "value"})},
		{"Heartbeat", NewHeartbeatEvent(1)},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			jsonData, err := tt.event.ToJSON()
			if err != nil {
				t.Fatalf("ToJSON() error = %v", err)
			}

			// Verify it's valid JSON
			var decoded map[string]interface{}
			if err := json.Unmarshal(jsonData, &decoded); err != nil {
				t.Fatalf("JSON unmarshal error = %v", err)
			}

			// Verify event_type field exists
			if _, ok := decoded["event_type"]; !ok {
				t.Error("JSON missing event_type field")
			}

			// Verify timestamp field exists
			if _, ok := decoded["timestamp"]; !ok {
				t.Error("JSON missing timestamp field")
			}
		})
	}
}

func TestParseEvent(t *testing.T) {
	tests := []struct {
		name      string
		jsonData  string
		eventType EventType
		wantError bool
	}{
		{
			name:      "TextMessageStart",
			jsonData:  `{"event_type":"text_message_start","timestamp":"2024-01-24T00:00:00Z","message_id":"msg-1","role":"assistant"}`,
			eventType: EventTypeTextMessageStart,
		},
		{
			name:      "TextMessageChunk",
			jsonData:  `{"event_type":"text_message_chunk","timestamp":"2024-01-24T00:00:00Z","message_id":"msg-1","content":"Hello"}`,
			eventType: EventTypeTextMessageChunk,
		},
		{
			name:      "Interrupt",
			jsonData:  `{"event_type":"interrupt","timestamp":"2024-01-24T00:00:00Z","interrupt_id":"int-1","reason":"approval_required","message":"Need approval"}`,
			eventType: EventTypeInterrupt,
		},
		{
			name:      "InvalidJSON",
			jsonData:  `{invalid json`,
			wantError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			event, err := ParseEvent([]byte(tt.jsonData))

			if tt.wantError {
				if err == nil {
					t.Error("ParseEvent() expected error, got nil")
				}
				return
			}

			if err != nil {
				t.Fatalf("ParseEvent() error = %v", err)
			}

			if event.GetEventType() != tt.eventType {
				t.Errorf("EventType = %s, want %s", event.GetEventType(), tt.eventType)
			}
		})
	}
}

func TestInterruptResponse(t *testing.T) {
	resp := NewInterruptResponse("int-123", InterruptActionApprove)

	if resp.InterruptID != "int-123" {
		t.Errorf("InterruptID = %s, want int-123", resp.InterruptID)
	}

	if resp.Action != InterruptActionApprove {
		t.Errorf("Action = %s, want %s", resp.Action, InterruptActionApprove)
	}

	if resp.Timestamp == "" {
		t.Error("Timestamp should not be empty")
	}

	// Test with data
	resp.Data["feedback"] = "Looks good"
	if feedback, ok := resp.Data["feedback"].(string); !ok || feedback != "Looks good" {
		t.Errorf("Data[feedback] = %v, want 'Looks good'", resp.Data["feedback"])
	}
}
