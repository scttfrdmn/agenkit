package agui

import (
	"context"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// MockAgentWithConfidence is a mock agent that returns configurable confidence
type MockAgentWithConfidence struct {
	name       string
	response   string
	confidence float64
}

func NewMockAgentWithConfidence(name, response string, confidence float64) *MockAgentWithConfidence {
	return &MockAgentWithConfidence{
		name:       name,
		response:   response,
		confidence: confidence,
	}
}

func (m *MockAgentWithConfidence) Name() string {
	return m.name
}

func (m *MockAgentWithConfidence) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	response := agenkit.NewMessage("assistant", m.response)
	response.Metadata = map[string]interface{}{
		"confidence": m.confidence,
	}
	return response, nil
}

func (m *MockAgentWithConfidence) Capabilities() []string {
	return []string{"chat"}
}

func (m *MockAgentWithConfidence) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:     m.name,
		Capabilities:  m.Capabilities(),
		InternalState: make(map[string]interface{}),
		Metadata:      make(map[string]interface{}),
	}
}

func TestNewAGUIHumanInLoopAdapter(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	adapter := NewAGUIHumanInLoopAdapter(agent, "CustomName", true)

	if adapter == nil {
		t.Fatal("NewAGUIHumanInLoopAdapter() returned nil")
	}

	if adapter.AgentName() != "CustomName" {
		t.Errorf("AgentName() = %s, want CustomName", adapter.AgentName())
	}

	if !adapter.emitInterrupts {
		t.Error("emitInterrupts should be true")
	}
}

func TestAGUIHumanInLoopAdapter_RegularAgent(t *testing.T) {
	// Test with regular agent (not HumanInLoopAgent)
	agent := NewMockAgent("TestAgent", "Hello world")
	adapter := NewAGUIHumanInLoopAdapter(agent, "", true)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	events := []AGUIEvent{}
	for event := range adapter.StreamEvents(ctx, message) {
		events = append(events, event)
	}

	// Should behave like regular adapter (no Interrupt events)
	if len(events) < 4 {
		t.Fatalf("Expected at least 4 events, got %d", len(events))
	}

	// Check no Interrupt events
	for _, event := range events {
		if _, ok := event.(*Interrupt); ok {
			t.Error("Regular agent should not emit Interrupt events")
		}
	}
}

func TestAGUIHumanInLoopAdapter_WithApproval(t *testing.T) {
	// Create agent with low confidence (requires approval)
	baseAgent := NewMockAgentWithConfidence("TestAgent", "Low confidence response", 0.6)

	// Create HumanInLoopAgent with approval function
	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             baseAgent,
		ApprovalFunc:      patterns.SimpleApprovalFunc(true), // Auto-approve
		ApprovalThreshold: 0.8,
	})
	if err != nil {
		t.Fatalf("Failed to create HumanInLoopAgent: %v", err)
	}

	// Wrap with AGUI adapter
	adapter := NewAGUIHumanInLoopAdapter(hilAgent, "", true)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	events := []AGUIEvent{}
	for event := range adapter.StreamEvents(ctx, message) {
		events = append(events, event)
	}

	// Should have: MetadataEvent, Interrupt (for approval), TextMessageStart, chunks, TextMessageComplete
	if len(events) < 5 {
		t.Fatalf("Expected at least 5 events with HITL, got %d", len(events))
	}

	// Check for MetadataEvent
	metadata, ok := events[0].(*MetadataEvent)
	if !ok {
		t.Errorf("First event should be MetadataEvent, got %T", events[0])
	}

	// Check metadata includes HITL capabilities
	if metadata != nil {
		caps, ok := metadata.Data["capabilities"].([]string)
		if !ok {
			t.Error("Metadata should include capabilities")
		} else {
			hasHITL := false
			for _, cap := range caps {
				if cap == "human-in-loop" {
					hasHITL = true
					break
				}
			}
			if !hasHITL {
				t.Error("Capabilities should include 'human-in-loop'")
			}
		}

		supportsHITL, ok := metadata.Data["supports_hitl"].(bool)
		if !ok || !supportsHITL {
			t.Error("Metadata should have supports_hitl = true")
		}
	}

	// Check for Interrupt event
	var interruptEvent *Interrupt
	for _, event := range events {
		if interrupt, ok := event.(*Interrupt); ok {
			interruptEvent = interrupt
			break
		}
	}

	if interruptEvent == nil {
		t.Error("Expected Interrupt event for approval")
	} else {
		if interruptEvent.Reason != InterruptReasonApprovalRequired {
			t.Errorf("Interrupt reason = %s, want %s", interruptEvent.Reason, InterruptReasonApprovalRequired)
		}

		// Check context includes approval status
		approvalStatus, ok := interruptEvent.Context["approval_status"].(string)
		if !ok || approvalStatus != "approved" {
			t.Errorf("Interrupt context approval_status = %v, want approved", interruptEvent.Context["approval_status"])
		}

		// Check confidence
		confidence, ok := interruptEvent.Context["confidence"].(float64)
		if !ok || confidence != 0.6 {
			t.Errorf("Interrupt context confidence = %v, want 0.6", interruptEvent.Context["confidence"])
		}
	}

	// Check for TextMessageComplete with approval metadata
	var completeEvent *TextMessageComplete
	for _, event := range events {
		if complete, ok := event.(*TextMessageComplete); ok {
			completeEvent = complete
			break
		}
	}

	if completeEvent == nil {
		t.Error("Expected TextMessageComplete event")
	} else {
		approvalStatus, ok := completeEvent.Metadata["approval_status"].(string)
		if !ok || approvalStatus != "approved" {
			t.Errorf("Complete event approval_status = %v, want approved", completeEvent.Metadata["approval_status"])
		}
	}
}

func TestAGUIHumanInLoopAdapter_WithRejection(t *testing.T) {
	// Create agent with low confidence
	baseAgent := NewMockAgentWithConfidence("TestAgent", "Low confidence response", 0.5)

	// Create HumanInLoopAgent with rejection
	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             baseAgent,
		ApprovalFunc:      patterns.SimpleApprovalFunc(false), // Auto-reject
		ApprovalThreshold: 0.8,
	})
	if err != nil {
		t.Fatalf("Failed to create HumanInLoopAgent: %v", err)
	}

	// Wrap with AGUI adapter
	adapter := NewAGUIHumanInLoopAdapter(hilAgent, "", true)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	events := []AGUIEvent{}
	for event := range adapter.StreamEvents(ctx, message) {
		events = append(events, event)
	}

	// Check for Interrupt event with rejection
	var interruptEvent *Interrupt
	for _, event := range events {
		if interrupt, ok := event.(*Interrupt); ok {
			interruptEvent = interrupt
			break
		}
	}

	if interruptEvent == nil {
		t.Error("Expected Interrupt event for rejection")
	} else {
		approvalStatus, ok := interruptEvent.Context["approval_status"].(string)
		if !ok || approvalStatus != "rejected" {
			t.Errorf("Interrupt context approval_status = %v, want rejected", interruptEvent.Context["approval_status"])
		}
	}

	// Check TextMessageComplete has rejection metadata
	var completeEvent *TextMessageComplete
	for _, event := range events {
		if complete, ok := event.(*TextMessageComplete); ok {
			completeEvent = complete
			break
		}
	}

	if completeEvent == nil {
		t.Error("Expected TextMessageComplete event")
	} else {
		approvalStatus, ok := completeEvent.Metadata["approval_status"].(string)
		if !ok || approvalStatus != "rejected" {
			t.Errorf("Complete event approval_status = %v, want rejected", completeEvent.Metadata["approval_status"])
		}

		// Content should be rejection message
		if completeEvent.Content != "Action rejected by human reviewer" {
			t.Errorf("Rejection message = %s, want 'Action rejected by human reviewer'", completeEvent.Content)
		}
	}
}

func TestAGUIHumanInLoopAdapter_HighConfidence(t *testing.T) {
	// Create agent with high confidence (bypasses approval)
	baseAgent := NewMockAgentWithConfidence("TestAgent", "High confidence response", 0.95)

	// Create HumanInLoopAgent
	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             baseAgent,
		ApprovalFunc:      patterns.SimpleApprovalFunc(true),
		ApprovalThreshold: 0.8,
	})
	if err != nil {
		t.Fatalf("Failed to create HumanInLoopAgent: %v", err)
	}

	// Wrap with AGUI adapter
	adapter := NewAGUIHumanInLoopAdapter(hilAgent, "", true)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	events := []AGUIEvent{}
	for event := range adapter.StreamEvents(ctx, message) {
		events = append(events, event)
	}

	// Should NOT have Interrupt event (bypassed due to high confidence)
	for _, event := range events {
		if _, ok := event.(*Interrupt); ok {
			t.Error("High confidence should not emit Interrupt event (bypassed)")
		}
	}

	// Check TextMessageComplete has bypassed status
	var completeEvent *TextMessageComplete
	for _, event := range events {
		if complete, ok := event.(*TextMessageComplete); ok {
			completeEvent = complete
			break
		}
	}

	if completeEvent == nil {
		t.Error("Expected TextMessageComplete event")
	} else {
		approvalStatus, ok := completeEvent.Metadata["approval_status"].(string)
		if !ok || approvalStatus != "bypassed" {
			t.Errorf("Complete event approval_status = %v, want bypassed", completeEvent.Metadata["approval_status"])
		}
	}
}

func TestAGUIHumanInLoopAdapter_InterruptsDisabled(t *testing.T) {
	// Create agent with low confidence
	baseAgent := NewMockAgentWithConfidence("TestAgent", "Low confidence", 0.6)

	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             baseAgent,
		ApprovalFunc:      patterns.SimpleApprovalFunc(true),
		ApprovalThreshold: 0.8,
	})
	if err != nil {
		t.Fatalf("Failed to create HumanInLoopAgent: %v", err)
	}

	// Create adapter with interrupts DISABLED
	adapter := NewAGUIHumanInLoopAdapter(hilAgent, "", false)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	events := []AGUIEvent{}
	for event := range adapter.StreamEvents(ctx, message) {
		events = append(events, event)
	}

	// Should NOT have Interrupt event (disabled)
	for _, event := range events {
		if _, ok := event.(*Interrupt); ok {
			t.Error("Interrupts disabled - should not emit Interrupt event")
		}
	}
}

func TestAGUIHumanInLoopAdapter_StreamEventsWithConfig(t *testing.T) {
	baseAgent := NewMockAgentWithConfidence("TestAgent", "Test response", 0.7)

	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             baseAgent,
		ApprovalFunc:      patterns.SimpleApprovalFunc(true),
		ApprovalThreshold: 0.8,
	})
	if err != nil {
		t.Fatalf("Failed to create HumanInLoopAgent: %v", err)
	}

	adapter := NewAGUIHumanInLoopAdapter(hilAgent, "", true)

	message := agenkit.NewMessage("user", "Hi")
	ctx := context.Background()

	config := StreamEventsConfig{
		MessageID:    "custom-msg-id",
		EmitMetadata: false,
	}

	events := []AGUIEvent{}
	for event := range adapter.StreamEventsWithConfig(ctx, message, config) {
		events = append(events, event)
	}

	// Should not have MetadataEvent (EmitMetadata = false)
	if _, ok := events[0].(*MetadataEvent); ok {
		t.Error("EmitMetadata = false, but got MetadataEvent")
	}

	// Check custom message ID is used
	var startEvent *TextMessageStart
	for _, event := range events {
		if start, ok := event.(*TextMessageStart); ok {
			startEvent = start
			break
		}
	}

	if startEvent == nil {
		t.Error("Expected TextMessageStart event")
	} else if startEvent.MessageID != "custom-msg-id" {
		t.Errorf("MessageID = %s, want custom-msg-id", startEvent.MessageID)
	}
}

func TestAGUIHumanInLoopAdapter_HandleInterruptResponse(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	adapter := NewAGUIHumanInLoopAdapter(agent, "", true)

	// Add a pending interrupt
	interruptID := "test-interrupt-123"
	response := agenkit.NewMessage("assistant", "Original response")
	response.Metadata = make(map[string]interface{})

	adapter.mu.Lock()
	adapter.pendingInterrupts[interruptID] = map[string]interface{}{
		"response": response,
	}
	adapter.mu.Unlock()

	// Handle approve action
	interruptResponse := &InterruptResponse{
		InterruptID: interruptID,
		Action:      InterruptActionApprove,
		Data: map[string]interface{}{
			"feedback": "Looks good!",
		},
	}

	err := adapter.HandleInterruptResponse(interruptResponse)
	if err != nil {
		t.Fatalf("HandleInterruptResponse() error = %v", err)
	}

	// Check metadata updated
	approvalStatus, ok := response.Metadata["approval_status"].(string)
	if !ok || approvalStatus != "approved" {
		t.Errorf("approval_status = %v, want approved", response.Metadata["approval_status"])
	}

	feedback, ok := response.Metadata["approval_feedback"].(string)
	if !ok || feedback != "Looks good!" {
		t.Errorf("approval_feedback = %v, want 'Looks good!'", response.Metadata["approval_feedback"])
	}

	// Check interrupt removed from pending
	adapter.mu.Lock()
	_, exists := adapter.pendingInterrupts[interruptID]
	adapter.mu.Unlock()

	if exists {
		t.Error("Interrupt should be removed from pending after handling")
	}
}

func TestAGUIHumanInLoopAdapter_HandleInterruptResponse_Reject(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	adapter := NewAGUIHumanInLoopAdapter(agent, "", true)

	interruptID := "test-interrupt-456"
	response := agenkit.NewMessage("assistant", "Original response")
	response.Metadata = make(map[string]interface{})

	adapter.mu.Lock()
	adapter.pendingInterrupts[interruptID] = map[string]interface{}{
		"response": response,
	}
	adapter.mu.Unlock()

	// Handle reject action
	interruptResponse := &InterruptResponse{
		InterruptID: interruptID,
		Action:      InterruptActionReject,
		Data: map[string]interface{}{
			"reason": "Not appropriate",
		},
	}

	err := adapter.HandleInterruptResponse(interruptResponse)
	if err != nil {
		t.Fatalf("HandleInterruptResponse() error = %v", err)
	}

	approvalStatus, ok := response.Metadata["approval_status"].(string)
	if !ok || approvalStatus != "rejected" {
		t.Errorf("approval_status = %v, want rejected", response.Metadata["approval_status"])
	}

	reason, ok := response.Metadata["rejection_reason"].(string)
	if !ok || reason != "Not appropriate" {
		t.Errorf("rejection_reason = %v, want 'Not appropriate'", response.Metadata["rejection_reason"])
	}
}

func TestAGUIHumanInLoopAdapter_HandleInterruptResponse_Edit(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	adapter := NewAGUIHumanInLoopAdapter(agent, "", true)

	interruptID := "test-interrupt-789"
	response := agenkit.NewMessage("assistant", "Original response")
	response.Metadata = make(map[string]interface{})

	adapter.mu.Lock()
	adapter.pendingInterrupts[interruptID] = map[string]interface{}{
		"response": response,
	}
	adapter.mu.Unlock()

	// Handle edit action
	interruptResponse := &InterruptResponse{
		InterruptID: interruptID,
		Action:      InterruptActionEdit,
		Data: map[string]interface{}{
			"modified_content": "Modified response",
		},
	}

	err := adapter.HandleInterruptResponse(interruptResponse)
	if err != nil {
		t.Fatalf("HandleInterruptResponse() error = %v", err)
	}

	approvalStatus, ok := response.Metadata["approval_status"].(string)
	if !ok || approvalStatus != "approved_with_modifications" {
		t.Errorf("approval_status = %v, want approved_with_modifications", response.Metadata["approval_status"])
	}

	originalResponse, ok := response.Metadata["original_response"].(string)
	if !ok || originalResponse != "Original response" {
		t.Errorf("original_response = %v, want 'Original response'", response.Metadata["original_response"])
	}

	if response.Content != "Modified response" {
		t.Errorf("Content = %s, want 'Modified response'", response.Content)
	}
}

func TestAGUIHumanInLoopAdapter_HandleInterruptResponse_UnknownID(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	adapter := NewAGUIHumanInLoopAdapter(agent, "", true)

	interruptResponse := &InterruptResponse{
		InterruptID: "unknown-id",
		Action:      InterruptActionApprove,
	}

	err := adapter.HandleInterruptResponse(interruptResponse)
	if err == nil {
		t.Error("Expected error for unknown interrupt_id")
	}
}
