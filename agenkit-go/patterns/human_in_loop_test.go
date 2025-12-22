package patterns

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestHumanInLoopAgent_Constructor tests valid construction
func TestHumanInLoopAgent_Constructor(t *testing.T) {
	agent := &extendedMockAgent{name: "agent", response: "result"}
	approvalFunc := SimpleApprovalFunc(true)

	config := &HumanInLoopConfig{
		Agent:             agent,
		ApprovalThreshold: 0.8,
		ApprovalFunc:      approvalFunc,
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if hil == nil {
		t.Fatal("expected non-nil HumanInLoopAgent")
	}
	if hil.Name() != "HumanInLoopAgent" {
		t.Errorf("expected name 'HumanInLoopAgent', got '%s'", hil.Name())
	}
}

// TestHumanInLoopAgent_ConstructorNilConfig tests error case with nil config
func TestHumanInLoopAgent_ConstructorNilConfig(t *testing.T) {
	_, err := NewHumanInLoopAgent(nil)
	if err == nil {
		t.Fatal("expected error for nil config")
	}
	if !strings.Contains(err.Error(), "config") {
		t.Errorf("expected 'config' error, got %v", err)
	}
}

// TestHumanInLoopAgent_ConstructorNilAgent tests error case with nil agent
func TestHumanInLoopAgent_ConstructorNilAgent(t *testing.T) {
	config := &HumanInLoopConfig{
		Agent:        nil,
		ApprovalFunc: SimpleApprovalFunc(true),
	}

	_, err := NewHumanInLoopAgent(config)
	if err == nil {
		t.Fatal("expected error for nil agent")
	}
	if !strings.Contains(err.Error(), "agent") {
		t.Errorf("expected 'agent' error, got %v", err)
	}
}

// TestHumanInLoopAgent_ConstructorNilApprovalFunc tests error case with nil approval function
func TestHumanInLoopAgent_ConstructorNilApprovalFunc(t *testing.T) {
	config := &HumanInLoopConfig{
		Agent:        &extendedMockAgent{name: "agent"},
		ApprovalFunc: nil,
	}

	_, err := NewHumanInLoopAgent(config)
	if err == nil {
		t.Fatal("expected error for nil approval function")
	}
	if !strings.Contains(err.Error(), "approval function") {
		t.Errorf("expected 'approval function' error, got %v", err)
	}
}

// TestHumanInLoopAgent_ConstructorInvalidThreshold tests error case with invalid threshold
func TestHumanInLoopAgent_ConstructorInvalidThreshold(t *testing.T) {
	tests := []struct {
		threshold float64
		name      string
	}{
		{-0.1, "negative"},
		{1.5, "above 1"},
	}

	for _, tt := range tests {
		config := &HumanInLoopConfig{
			Agent:             &extendedMockAgent{name: "agent"},
			ApprovalThreshold: tt.threshold,
			ApprovalFunc:      SimpleApprovalFunc(true),
		}

		_, err := NewHumanInLoopAgent(config)
		if err == nil {
			t.Errorf("expected error for %s threshold", tt.name)
		}
		if !strings.Contains(err.Error(), "between 0 and 1") {
			t.Errorf("expected threshold validation error, got: %v", err)
		}
	}
}

// TestHumanInLoopAgent_ConstructorDefaultThreshold tests default threshold
func TestHumanInLoopAgent_ConstructorDefaultThreshold(t *testing.T) {
	config := &HumanInLoopConfig{
		Agent:             &extendedMockAgent{name: "agent"},
		ApprovalThreshold: 0, // Should default to 0.8
		ApprovalFunc:      SimpleApprovalFunc(true),
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if hil.approvalThreshold != 0.8 {
		t.Errorf("expected default threshold=0.8, got %f", hil.approvalThreshold)
	}
}

// TestHumanInLoopAgent_HighConfidenceBypassed tests high confidence bypassing approval
func TestHumanInLoopAgent_HighConfidenceBypassed(t *testing.T) {
	agent := &extendedMockAgent{
		name: "agent",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			resp := agenkit.NewMessage("assistant", "high confidence result")
			resp.WithMetadata("confidence", 0.95)
			return resp, nil
		},
	}

	config := &HumanInLoopConfig{
		Agent:             agent,
		ApprovalThreshold: 0.8,
		ApprovalFunc:      SimpleApprovalFunc(true),
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := hil.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "high confidence result" {
		t.Errorf("expected original result, got '%s'", result.Content)
	}

	// Check metadata
	if result.Metadata["approval_needed"] != false {
		t.Error("expected approval_needed=false for high confidence")
	}
	if result.Metadata["approval_status"] != "bypassed" {
		t.Errorf("expected approval_status='bypassed', got %v", result.Metadata["approval_status"])
	}
}

// TestHumanInLoopAgent_LowConfidenceApproved tests low confidence with approval
func TestHumanInLoopAgent_LowConfidenceApproved(t *testing.T) {
	agent := &extendedMockAgent{
		name: "agent",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			resp := agenkit.NewMessage("assistant", "low confidence result")
			resp.WithMetadata("confidence", 0.6)
			return resp, nil
		},
	}

	config := &HumanInLoopConfig{
		Agent:             agent,
		ApprovalThreshold: 0.8,
		ApprovalFunc:      SimpleApprovalFunc(true),
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := hil.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should still get result because approval was granted
	if result.Content != "low confidence result" {
		t.Errorf("expected original result, got '%s'", result.Content)
	}

	// Check metadata
	if result.Metadata["approval_needed"] != true {
		t.Error("expected approval_needed=true for low confidence")
	}
	if result.Metadata["approval_status"] != "approved" {
		t.Errorf("expected approval_status='approved', got %v", result.Metadata["approval_status"])
	}
}

// TestHumanInLoopAgent_LowConfidenceRejected tests low confidence with rejection
func TestHumanInLoopAgent_LowConfidenceRejected(t *testing.T) {
	agent := &extendedMockAgent{
		name: "agent",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			resp := agenkit.NewMessage("assistant", "risky action")
			resp.WithMetadata("confidence", 0.5)
			return resp, nil
		},
	}

	config := &HumanInLoopConfig{
		Agent:             agent,
		ApprovalThreshold: 0.8,
		ApprovalFunc:      SimpleApprovalFunc(false), // Auto-reject
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := hil.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should get rejection message
	if !strings.Contains(result.Content, "rejected") {
		t.Errorf("expected rejection message, got '%s'", result.Content)
	}

	// Check metadata
	if result.Metadata["approval_status"] != "rejected" {
		t.Errorf("expected approval_status='rejected', got %v", result.Metadata["approval_status"])
	}
	if result.Metadata["original_response"] != "risky action" {
		t.Errorf("expected original_response in metadata, got %v", result.Metadata["original_response"])
	}
}

// TestHumanInLoopAgent_ApprovedWithModifications tests approval with modifications
func TestHumanInLoopAgent_ApprovedWithModifications(t *testing.T) {
	agent := &extendedMockAgent{
		name: "agent",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			resp := agenkit.NewMessage("assistant", "original response")
			resp.WithMetadata("confidence", 0.6)
			return resp, nil
		},
	}

	approvalFunc := func(ctx context.Context, request *ApprovalRequest) (*ApprovalResponse, error) {
		return &ApprovalResponse{
			Approved:        true,
			Feedback:        "Approved with changes",
			ModifiedMessage: agenkit.NewMessage("assistant", "modified response"),
		}, nil
	}

	config := &HumanInLoopConfig{
		Agent:             agent,
		ApprovalThreshold: 0.8,
		ApprovalFunc:      approvalFunc,
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := hil.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should get modified response
	if result.Content != "modified response" {
		t.Errorf("expected 'modified response', got '%s'", result.Content)
	}

	// Check metadata
	if result.Metadata["approval_status"] != "approved_with_modifications" {
		t.Errorf("expected approval_status='approved_with_modifications', got %v", result.Metadata["approval_status"])
	}
	if result.Metadata["original_response"] != "original response" {
		t.Errorf("expected original_response in metadata")
	}
}

// TestHumanInLoopAgent_AgentError tests error from underlying agent
func TestHumanInLoopAgent_AgentError(t *testing.T) {
	agent := &extendedMockAgent{
		name: "agent",
		err:  errors.New("agent failed"),
	}

	config := &HumanInLoopConfig{
		Agent:        agent,
		ApprovalFunc: SimpleApprovalFunc(true),
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = hil.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error from agent failure")
	}
	if !strings.Contains(err.Error(), "agent execution failed") {
		t.Errorf("expected agent error, got: %v", err)
	}
}

// TestHumanInLoopAgent_ApprovalFuncError tests error from approval function
func TestHumanInLoopAgent_ApprovalFuncError(t *testing.T) {
	agent := &extendedMockAgent{
		name: "agent",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			resp := agenkit.NewMessage("assistant", "result")
			resp.WithMetadata("confidence", 0.5)
			return resp, nil
		},
	}

	approvalFunc := func(ctx context.Context, request *ApprovalRequest) (*ApprovalResponse, error) {
		return nil, errors.New("approval system down")
	}

	config := &HumanInLoopConfig{
		Agent:             agent,
		ApprovalThreshold: 0.8,
		ApprovalFunc:      approvalFunc,
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = hil.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error from approval function")
	}
	if !strings.Contains(err.Error(), "approval request failed") {
		t.Errorf("expected approval error, got: %v", err)
	}
}

// TestHumanInLoopAgent_NilMessage tests nil message handling
func TestHumanInLoopAgent_NilMessage(t *testing.T) {
	config := &HumanInLoopConfig{
		Agent:        &extendedMockAgent{name: "agent"},
		ApprovalFunc: SimpleApprovalFunc(true),
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, err = hil.Process(context.Background(), nil)
	if err == nil {
		t.Fatal("expected error for nil message")
	}
	if !strings.Contains(err.Error(), "cannot be nil") {
		t.Errorf("expected 'cannot be nil' error, got: %v", err)
	}
}

// TestHumanInLoopAgent_Capabilities tests capabilities
func TestHumanInLoopAgent_Capabilities(t *testing.T) {
	agent := &extendedMockAgent{name: "agent", capabilities: []string{"cap1", "cap2"}}

	config := &HumanInLoopConfig{
		Agent:        agent,
		ApprovalFunc: SimpleApprovalFunc(true),
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	caps := hil.Capabilities()

	expectedCaps := map[string]bool{
		"cap1":          true,
		"cap2":          true,
		"human-in-loop": true,
		"approval":      true,
		"oversight":     true,
	}

	if len(caps) != len(expectedCaps) {
		t.Errorf("expected %d capabilities, got %d: %v", len(expectedCaps), len(caps), caps)
	}
}

// TestHumanInLoopAgent_CustomConfidenceKey tests custom confidence key
func TestHumanInLoopAgent_CustomConfidenceKey(t *testing.T) {
	agent := &extendedMockAgent{
		name: "agent",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			resp := agenkit.NewMessage("assistant", "result")
			resp.WithMetadata("custom_confidence", 0.95)
			return resp, nil
		},
	}

	config := &HumanInLoopConfig{
		Agent:             agent,
		ApprovalThreshold: 0.8,
		ApprovalFunc:      SimpleApprovalFunc(true),
		ConfidenceKey:     "custom_confidence",
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := hil.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should bypass approval with high custom confidence
	if result.Metadata["approval_status"] != "bypassed" {
		t.Errorf("expected approval bypassed with custom confidence key")
	}
}

// TestHumanInLoopAgent_MissingConfidence tests missing confidence defaults to 0
func TestHumanInLoopAgent_MissingConfidence(t *testing.T) {
	agent := &extendedMockAgent{
		name:     "agent",
		response: "no confidence",
	}

	approvalCalled := false
	approvalFunc := func(ctx context.Context, request *ApprovalRequest) (*ApprovalResponse, error) {
		approvalCalled = true
		if request.Confidence != 0.0 {
			t.Errorf("expected confidence=0.0 for missing confidence, got %f", request.Confidence)
		}
		return &ApprovalResponse{Approved: true}, nil
	}

	config := &HumanInLoopConfig{
		Agent:             agent,
		ApprovalThreshold: 0.8,
		ApprovalFunc:      approvalFunc,
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = hil.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !approvalCalled {
		t.Error("expected approval to be called for missing confidence (defaults to 0)")
	}
}

// TestHumanInLoopAgent_ConfidenceBasedApprovalFunc tests confidence-based approval
func TestHumanInLoopAgent_ConfidenceBasedApprovalFunc(t *testing.T) {
	tests := []struct {
		confidence       float64
		rejectBelow      float64
		autoApproveAbove float64
		expectApproved   bool
		name             string
	}{
		{0.3, 0.5, 0.7, false, "below reject threshold"},
		{0.6, 0.5, 0.7, false, "in manual range"},
		{0.75, 0.5, 0.7, true, "above auto-approve within HumanInLoop threshold"},
	}

	for _, tt := range tests {
		agent := &extendedMockAgent{
			name: "agent",
			processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
				resp := agenkit.NewMessage("assistant", "result")
				resp.WithMetadata("confidence", tt.confidence)
				return resp, nil
			},
		}

		approvalFunc := ConfidenceBasedApprovalFunc(tt.rejectBelow, tt.autoApproveAbove)

		config := &HumanInLoopConfig{
			Agent:             agent,
			ApprovalThreshold: 0.8,
			ApprovalFunc:      approvalFunc,
		}

		hil, err := NewHumanInLoopAgent(config)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}

		msg := agenkit.NewMessage("user", "test")
		result, err := hil.Process(context.Background(), msg)
		if err != nil {
			t.Fatalf("unexpected error for %s: %v", tt.name, err)
		}

		approved := result.Metadata["approval_status"] == "approved"
		rejected := result.Metadata["approval_status"] == "rejected"

		if tt.expectApproved && !approved {
			t.Errorf("%s: expected approval, got status=%v", tt.name, result.Metadata["approval_status"])
		}
		if !tt.expectApproved && !rejected {
			t.Errorf("%s: expected rejection, got status=%v", tt.name, result.Metadata["approval_status"])
		}
	}
}

// TestHumanInLoopAgent_ApprovalRequestContext tests approval request context
func TestHumanInLoopAgent_ApprovalRequestContext(t *testing.T) {
	agent := &extendedMockAgent{
		name: "agent",
		processFunc: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
			resp := agenkit.NewMessage("assistant", "result")
			resp.WithMetadata("confidence", 0.6)
			return resp, nil
		},
	}

	var capturedRequest *ApprovalRequest
	approvalFunc := func(ctx context.Context, request *ApprovalRequest) (*ApprovalResponse, error) {
		capturedRequest = request
		return &ApprovalResponse{Approved: true}, nil
	}

	config := &HumanInLoopConfig{
		Agent:             agent,
		ApprovalThreshold: 0.8,
		ApprovalFunc:      approvalFunc,
	}

	hil, err := NewHumanInLoopAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test input")
	_, err = hil.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if capturedRequest == nil {
		t.Fatal("expected approval request to be captured")
	}

	// Check request fields
	if capturedRequest.Confidence != 0.6 {
		t.Errorf("expected confidence=0.6, got %f", capturedRequest.Confidence)
	}
	if capturedRequest.Message.Content != "result" {
		t.Errorf("expected message content='result', got '%s'", capturedRequest.Message.Content)
	}
	if capturedRequest.Context["agent"] != "agent" {
		t.Errorf("expected agent context, got %v", capturedRequest.Context["agent"])
	}
	if capturedRequest.Context["original_message"] != "test input" {
		t.Errorf("expected original_message context")
	}
}
