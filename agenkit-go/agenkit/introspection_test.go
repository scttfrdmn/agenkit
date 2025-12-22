package agenkit

import (
	"context"
	"testing"
	"time"
)

// SimpleAgent is a test agent with basic capabilities
type SimpleAgent struct {
	name         string
	capabilities []string
}

func NewSimpleAgent() *SimpleAgent {
	return &SimpleAgent{
		name:         "simple",
		capabilities: []string{"test", "simple"},
	}
}

func (a *SimpleAgent) Name() string {
	return a.name
}

func (a *SimpleAgent) Process(ctx context.Context, message *Message) (*Message, error) {
	return NewMessage("assistant", "Processed: "+message.Content), nil
}

func (a *SimpleAgent) Capabilities() []string {
	return a.capabilities
}

func (a *SimpleAgent) Introspect() *IntrospectionResult {
	return DefaultIntrospectionResult(a)
}

// AgentWithMemory is a test agent that has memory state
type AgentWithMemory struct {
	name         string
	capabilities []string
	memory       map[string][]string
	messageCount int
}

func NewAgentWithMemory() *AgentWithMemory {
	return &AgentWithMemory{
		name:         "memory_agent",
		capabilities: []string{"memory", "stateful"},
		memory: map[string][]string{
			"short_term": {"item1", "item2"},
			"long_term":  {"memory1"},
		},
		messageCount: 0,
	}
}

func (a *AgentWithMemory) Name() string {
	return a.name
}

func (a *AgentWithMemory) Process(ctx context.Context, message *Message) (*Message, error) {
	a.messageCount++
	return NewMessage("assistant", "Processed"), nil
}

func (a *AgentWithMemory) Capabilities() []string {
	return a.capabilities
}

func (a *AgentWithMemory) Introspect() *IntrospectionResult {
	result, _ := NewIntrospectionResult(
		a.Name(),
		a.Capabilities(),
		map[string]interface{}{
			"short_term_count": len(a.memory["short_term"]),
			"long_term_count":  len(a.memory["long_term"]),
		},
		map[string]interface{}{
			"message_count": a.messageCount,
			"has_memory":    true,
		},
		nil,
	)
	return result
}

// Tests

func TestIntrospectionResultCreation(t *testing.T) {
	result, err := NewIntrospectionResult(
		"test",
		[]string{"test"},
		nil,
		make(map[string]interface{}),
		make(map[string]interface{}),
	)

	if err != nil {
		t.Fatalf("Failed to create IntrospectionResult: %v", err)
	}

	if result.AgentName != "test" {
		t.Errorf("Expected agent_name 'test', got '%s'", result.AgentName)
	}

	if len(result.Capabilities) != 1 || result.Capabilities[0] != "test" {
		t.Errorf("Expected capabilities ['test'], got %v", result.Capabilities)
	}

	if result.MemoryState != nil {
		t.Errorf("Expected MemoryState to be nil, got %v", result.MemoryState)
	}

	if result.InternalState == nil {
		t.Error("Expected InternalState to be initialized")
	}
}

func TestIntrospectionResultValidation(t *testing.T) {
	// Empty agent name should fail
	_, err := NewIntrospectionResult(
		"",
		[]string{},
		nil,
		make(map[string]interface{}),
		nil,
	)
	if err == nil {
		t.Error("Expected error for empty agent_name")
	}

	// Nil capabilities should be initialized to empty slice
	result, err := NewIntrospectionResult(
		"test",
		nil,
		nil,
		make(map[string]interface{}),
		nil,
	)
	if err != nil {
		t.Fatalf("Failed to create IntrospectionResult with nil capabilities: %v", err)
	}
	if result.Capabilities == nil {
		t.Error("Expected Capabilities to be initialized to empty slice")
	}

	// Nil internal_state should be initialized to empty map
	result, err = NewIntrospectionResult(
		"test",
		[]string{},
		nil,
		nil,
		nil,
	)
	if err != nil {
		t.Fatalf("Failed to create IntrospectionResult with nil internal_state: %v", err)
	}
	if result.InternalState == nil {
		t.Error("Expected InternalState to be initialized to empty map")
	}
}

func TestBasicIntrospection(t *testing.T) {
	agent := NewSimpleAgent()
	result := agent.Introspect()

	if result.AgentName != "simple" {
		t.Errorf("Expected agent_name 'simple', got '%s'", result.AgentName)
	}

	expectedCaps := []string{"test", "simple"}
	if len(result.Capabilities) != len(expectedCaps) {
		t.Errorf("Expected %d capabilities, got %d", len(expectedCaps), len(result.Capabilities))
	}
	for i, cap := range expectedCaps {
		if result.Capabilities[i] != cap {
			t.Errorf("Expected capability[%d] '%s', got '%s'", i, cap, result.Capabilities[i])
		}
	}

	if result.MemoryState != nil {
		t.Errorf("Expected MemoryState to be nil, got %v", result.MemoryState)
	}

	if result.InternalState == nil {
		t.Error("Expected InternalState to be initialized")
	}

	if result.Timestamp.IsZero() {
		t.Error("Expected non-zero Timestamp")
	}
}

func TestIntrospectionWithMemory(t *testing.T) {
	agent := NewAgentWithMemory()
	result := agent.Introspect()

	if result.AgentName != "memory_agent" {
		t.Errorf("Expected agent_name 'memory_agent', got '%s'", result.AgentName)
	}

	expectedCaps := []string{"memory", "stateful"}
	if len(result.Capabilities) != len(expectedCaps) {
		t.Errorf("Expected %d capabilities, got %d", len(expectedCaps), len(result.Capabilities))
	}

	if result.MemoryState == nil {
		t.Fatal("Expected MemoryState to be present")
	}

	if result.MemoryState["short_term_count"] != 2 {
		t.Errorf("Expected short_term_count 2, got %v", result.MemoryState["short_term_count"])
	}

	if result.MemoryState["long_term_count"] != 1 {
		t.Errorf("Expected long_term_count 1, got %v", result.MemoryState["long_term_count"])
	}

	if result.InternalState["message_count"] != 0 {
		t.Errorf("Expected message_count 0, got %v", result.InternalState["message_count"])
	}

	if result.InternalState["has_memory"] != true {
		t.Errorf("Expected has_memory true, got %v", result.InternalState["has_memory"])
	}
}

func TestIntrospectionReflectsStateChanges(t *testing.T) {
	agent := NewAgentWithMemory()

	// Initial state
	result1 := agent.Introspect()
	if result1.InternalState["message_count"] != 0 {
		t.Errorf("Expected initial message_count 0, got %v", result1.InternalState["message_count"])
	}

	// Process a message
	ctx := context.Background()
	_, err := agent.Process(ctx, NewMessage("user", "test"))
	if err != nil {
		t.Fatalf("Failed to process message: %v", err)
	}

	// State should have changed
	result2 := agent.Introspect()
	if result2.InternalState["message_count"] != 1 {
		t.Errorf("Expected message_count 1 after processing, got %v", result2.InternalState["message_count"])
	}
}

func TestIntrospectionTimestamp(t *testing.T) {
	agent := NewSimpleAgent()
	before := time.Now().UTC()
	result := agent.Introspect()
	after := time.Now().UTC()

	if result.Timestamp.Before(before) || result.Timestamp.After(after) {
		t.Errorf("Expected timestamp between %v and %v, got %v", before, after, result.Timestamp)
	}
}

func TestIntrospectionWithMetadata(t *testing.T) {
	agent := NewSimpleAgent()
	result := agent.Introspect()

	// Default metadata should be empty
	if len(result.Metadata) != 0 {
		t.Errorf("Expected empty Metadata, got %v", result.Metadata)
	}

	// Can create result with metadata
	customResult, err := NewIntrospectionResult(
		"test",
		[]string{},
		nil,
		make(map[string]interface{}),
		map[string]interface{}{"custom": "data"},
	)
	if err != nil {
		t.Fatalf("Failed to create IntrospectionResult with metadata: %v", err)
	}

	if customResult.Metadata["custom"] != "data" {
		t.Errorf("Expected metadata['custom'] = 'data', got %v", customResult.Metadata["custom"])
	}
}

func TestDefaultIntrospectionResult(t *testing.T) {
	agent := NewSimpleAgent()
	result := DefaultIntrospectionResult(agent)

	if result.AgentName != agent.Name() {
		t.Errorf("Expected agent_name '%s', got '%s'", agent.Name(), result.AgentName)
	}

	if len(result.Capabilities) != len(agent.Capabilities()) {
		t.Errorf("Expected %d capabilities, got %d", len(agent.Capabilities()), len(result.Capabilities))
	}

	if result.MemoryState != nil {
		t.Errorf("Expected MemoryState to be nil, got %v", result.MemoryState)
	}

	if result.InternalState == nil || len(result.InternalState) != 0 {
		t.Errorf("Expected empty InternalState, got %v", result.InternalState)
	}

	if result.Metadata == nil || len(result.Metadata) != 0 {
		t.Errorf("Expected empty Metadata, got %v", result.Metadata)
	}
}

func TestIntrospectionResultValidate(t *testing.T) {
	// Valid result
	result := &IntrospectionResult{
		Timestamp:     time.Now().UTC(),
		AgentName:     "test",
		Capabilities:  []string{"test"},
		MemoryState:   nil,
		InternalState: make(map[string]interface{}),
		Metadata:      make(map[string]interface{}),
	}

	if err := result.Validate(); err != nil {
		t.Errorf("Expected valid result to pass validation, got error: %v", err)
	}

	// Empty agent name
	invalidResult := &IntrospectionResult{
		AgentName:     "",
		Capabilities:  []string{},
		InternalState: make(map[string]interface{}),
	}
	if err := invalidResult.Validate(); err == nil {
		t.Error("Expected error for empty agent_name")
	}

	// Nil capabilities
	invalidResult = &IntrospectionResult{
		AgentName:     "test",
		Capabilities:  nil,
		InternalState: make(map[string]interface{}),
	}
	if err := invalidResult.Validate(); err == nil {
		t.Error("Expected error for nil capabilities")
	}

	// Nil internal state
	invalidResult = &IntrospectionResult{
		AgentName:     "test",
		Capabilities:  []string{},
		InternalState: nil,
	}
	if err := invalidResult.Validate(); err == nil {
		t.Error("Expected error for nil internal_state")
	}
}
