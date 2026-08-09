package agui

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// MockAgent is a simple agent for testing
type MockAgent struct {
	name         string
	capabilities []string
	response     string
	err          error
}

func NewMockAgent(name, response string) *MockAgent {
	return &MockAgent{
		name:         name,
		capabilities: []string{"chat", "test"},
		response:     response,
	}
}

func (m *MockAgent) Name() string {
	return m.name
}

func (m *MockAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if m.err != nil {
		return nil, m.err
	}

	return &agenkit.Message{
		Role:      "assistant",
		Content:   m.response,
		Metadata:  map[string]interface{}{"test": true},
		Timestamp: time.Now().UTC(),
	}, nil
}

func (m *MockAgent) Capabilities() []string {
	return m.capabilities
}

func (m *MockAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:     m.name,
		Capabilities:  m.capabilities,
		InternalState: make(map[string]interface{}),
		Metadata:      make(map[string]interface{}),
	}
}

func TestNewAGUIAdapter(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	adapter := NewAGUIAdapter(agent)

	if adapter.Agent() != agent {
		t.Error("Agent() did not return wrapped agent")
	}

	if adapter.AgentName() != "TestAgent" {
		t.Errorf("AgentName() = %s, want TestAgent", adapter.AgentName())
	}
}

func TestNewAGUIAdapterWithConfig(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	config := AGUIAdapterConfig{
		AgentName:         "CustomName",
		EmitHeartbeats:    true,
		HeartbeatInterval: 10.0,
	}
	adapter := NewAGUIAdapterWithConfig(agent, config)

	if adapter.AgentName() != "CustomName" {
		t.Errorf("AgentName() = %s, want CustomName", adapter.AgentName())
	}

	if !adapter.emitHeartbeats {
		t.Error("emitHeartbeats should be true")
	}

	if adapter.heartbeatInterval != 10.0 {
		t.Errorf("heartbeatInterval = %f, want 10.0", adapter.heartbeatInterval)
	}
}

func TestStreamEvents_Success(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello world")
	adapter := NewAGUIAdapter(agent)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	events := []AGUIEvent{}
	for event := range adapter.StreamEvents(ctx, message) {
		events = append(events, event)
	}

	// Should have: MetadataEvent, TextMessageStart, TextMessageChunk(s), TextMessageComplete
	if len(events) < 4 {
		t.Fatalf("Expected at least 4 events, got %d", len(events))
	}

	// Check first event is MetadataEvent
	if _, ok := events[0].(*MetadataEvent); !ok {
		t.Errorf("First event should be MetadataEvent, got %T", events[0])
	}

	// Check second event is TextMessageStart
	if _, ok := events[1].(*TextMessageStart); !ok {
		t.Errorf("Second event should be TextMessageStart, got %T", events[1])
	}

	// Check last event is TextMessageComplete
	lastEvent := events[len(events)-1]
	complete, ok := lastEvent.(*TextMessageComplete)
	if !ok {
		t.Errorf("Last event should be TextMessageComplete, got %T", lastEvent)
	}

	if complete.Content != "Hello world" {
		t.Errorf("Complete.ContentString() = %s, want 'Hello world'", complete.Content)
	}

	if complete.FinishReason != "stop" {
		t.Errorf("Complete.FinishReason = %s, want stop", complete.FinishReason)
	}
}

func TestStreamEvents_WithError(t *testing.T) {
	agent := NewMockAgent("TestAgent", "")
	agent.err = errors.New("test error")

	adapter := NewAGUIAdapter(agent)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	events := []AGUIEvent{}
	for event := range adapter.StreamEvents(ctx, message) {
		events = append(events, event)
	}

	// Should have: MetadataEvent, TextMessageStart, ErrorEvent, TextMessageComplete
	if len(events) < 4 {
		t.Fatalf("Expected at least 4 events, got %d", len(events))
	}

	// Find ErrorEvent
	var errorEvent *ErrorEvent
	for _, event := range events {
		if e, ok := event.(*ErrorEvent); ok {
			errorEvent = e
			break
		}
	}

	if errorEvent == nil {
		t.Error("Expected ErrorEvent in stream")
	} else {
		if errorEvent.ErrorMessage != "test error" {
			t.Errorf("ErrorMessage = %s, want 'test error'", errorEvent.ErrorMessage)
		}
	}

	// Check last event is TextMessageComplete with error
	lastEvent := events[len(events)-1]
	complete, ok := lastEvent.(*TextMessageComplete)
	if !ok {
		t.Errorf("Last event should be TextMessageComplete, got %T", lastEvent)
	}

	if complete.FinishReason != "error" {
		t.Errorf("Complete.FinishReason = %s, want error", complete.FinishReason)
	}
}

func TestStreamEvents_NoMetadata(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	adapter := NewAGUIAdapter(agent)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	config := StreamEventsConfig{
		EmitMetadata: false,
	}

	events := []AGUIEvent{}
	for event := range adapter.StreamEventsWithConfig(ctx, message, config) {
		events = append(events, event)
	}

	// First event should NOT be MetadataEvent
	if _, ok := events[0].(*MetadataEvent); ok {
		t.Error("First event should not be MetadataEvent when EmitMetadata is false")
	}

	// First event should be TextMessageStart
	if _, ok := events[0].(*TextMessageStart); !ok {
		t.Errorf("First event should be TextMessageStart, got %T", events[0])
	}
}

func TestStreamEvents_CustomMessageID(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	adapter := NewAGUIAdapter(agent)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	customID := "custom-msg-id"
	config := StreamEventsConfig{
		MessageID:    customID,
		EmitMetadata: false,
	}

	events := []AGUIEvent{}
	for event := range adapter.StreamEventsWithConfig(ctx, message, config) {
		events = append(events, event)
	}

	// Check that all message events use custom ID
	for _, event := range events {
		switch e := event.(type) {
		case *TextMessageStart:
			if e.MessageID != customID {
				t.Errorf("TextMessageStart.MessageID = %s, want %s", e.MessageID, customID)
			}
		case *TextMessageChunk:
			if e.MessageID != customID {
				t.Errorf("TextMessageChunk.MessageID = %s, want %s", e.MessageID, customID)
			}
		case *TextMessageComplete:
			if e.MessageID != customID {
				t.Errorf("TextMessageComplete.MessageID = %s, want %s", e.MessageID, customID)
			}
		}
	}
}

func TestStreamEvents_Chunks(t *testing.T) {
	// Test with content that will be split into chunks
	longResponse := "This is a long response that will be split into multiple chunks for streaming"
	agent := NewMockAgent("TestAgent", longResponse)
	adapter := NewAGUIAdapter(agent)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	chunkCount := 0
	var chunks []string

	for event := range adapter.StreamEvents(ctx, message) {
		if chunk, ok := event.(*TextMessageChunk); ok {
			chunkCount++
			chunks = append(chunks, chunk.Content)
		}
	}

	// Should have multiple chunks
	if chunkCount == 0 {
		t.Error("Expected at least one chunk")
	}

	// Concatenate chunks should equal original response
	concatenated := ""
	for _, chunk := range chunks {
		concatenated += chunk
	}

	if concatenated != longResponse {
		t.Errorf("Concatenated chunks = %s, want %s", concatenated, longResponse)
	}
}

func TestProcess_NonStreaming(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello world")
	adapter := NewAGUIAdapter(agent)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	result, err := adapter.Process(ctx, message)
	if err != nil {
		t.Fatalf("Process() error = %v", err)
	}

	if result.ContentString() != "Hello world" {
		t.Errorf("Content = %s, want 'Hello world'", result.ContentString())
	}

	if result.Role != "assistant" {
		t.Errorf("Role = %s, want assistant", result.Role)
	}
}

func TestProcess_WithCustomMessageID(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	adapter := NewAGUIAdapter(agent)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	customID := "my-msg-id"
	result, err := adapter.ProcessWithMessageID(ctx, message, customID)
	if err != nil {
		t.Fatalf("ProcessWithMessageID() error = %v", err)
	}

	if result.ContentString() != "Hello" {
		t.Errorf("Content = %s, want Hello", result.ContentString())
	}
}

func TestCreateMetadataEvent(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	agent.capabilities = []string{"chat", "tools", "memory"}
	adapter := NewAGUIAdapter(agent)

	metadata := adapter.createMetadataEvent()

	if metadata.GetEventType() != EventTypeMetadata {
		t.Errorf("EventType = %s, want %s", metadata.GetEventType(), EventTypeMetadata)
	}

	if name, ok := metadata.Data["agent_name"].(string); !ok || name != "TestAgent" {
		t.Errorf("agent_name = %v, want TestAgent", metadata.Data["agent_name"])
	}

	if caps, ok := metadata.Data["capabilities"].([]string); !ok || len(caps) != 3 {
		t.Errorf("capabilities = %v, want 3 items", metadata.Data["capabilities"])
	}

	if version, ok := metadata.Data["protocol_version"].(string); !ok || version != metadataSchemaVersion {
		t.Errorf("protocol_version = %v, want %s", metadata.Data["protocol_version"], metadataSchemaVersion)
	}
}

func TestCreateErrorEvent(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	adapter := NewAGUIAdapter(agent)

	testErr := errors.New("test error")
	errorEvent := adapter.createErrorEvent("msg-123", testErr)

	if errorEvent.GetEventType() != EventTypeError {
		t.Errorf("EventType = %s, want %s", errorEvent.GetEventType(), EventTypeError)
	}

	if errorEvent.ErrorMessage != "test error" {
		t.Errorf("ErrorMessage = %s, want 'test error'", errorEvent.ErrorMessage)
	}

	if msgID, ok := errorEvent.ErrorDetails["message_id"].(string); !ok || msgID != "msg-123" {
		t.Errorf("message_id = %v, want msg-123", errorEvent.ErrorDetails["message_id"])
	}

	if !errorEvent.Recoverable {
		t.Error("Recoverable should be true")
	}
}

func TestGenerateMessageID(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	adapter := NewAGUIAdapter(agent)

	id1 := adapter.generateMessageID()
	id2 := adapter.generateMessageID()

	// Should start with "msg-"
	if len(id1) < 4 || id1[:4] != "msg-" {
		t.Errorf("Message ID should start with 'msg-', got %s", id1)
	}

	// Should be unique
	if id1 == id2 {
		t.Error("Message IDs should be unique")
	}
}

func TestStreamEvents_ContextCancellation(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello world")
	adapter := NewAGUIAdapter(agent)

	message := agenkit.NewMessage("user", "Hi")
	ctx, cancel := context.WithCancel(context.Background())

	// Cancel context immediately
	cancel()

	events := []AGUIEvent{}
	for event := range adapter.StreamEvents(ctx, message) {
		events = append(events, event)
	}

	// Should have minimal events due to cancellation
	// Exact number depends on goroutine timing, but should be less than full stream
	if len(events) > 10 {
		t.Errorf("Expected few events after cancellation, got %d", len(events))
	}
}
