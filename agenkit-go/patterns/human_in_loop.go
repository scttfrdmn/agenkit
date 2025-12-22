// Package patterns provides reusable agent composition patterns.
//
// Human-in-Loop pattern implements agent execution with human approval
// for high-stakes decisions. When agent confidence is below a threshold,
// human approval is requested before proceeding.
//
// Key concepts:
//   - Confidence-based approval gates
//   - Human oversight for critical decisions
//   - Configurable approval thresholds
//   - Callback-based approval mechanism
//
// Performance characteristics:
//   - Time: O(agent) + human response time (when approval needed)
//   - Memory: O(1) for message passing
//   - Blocking on human input when required
package patterns

import (
	"context"
	"fmt"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ApprovalRequest contains information about a pending approval decision.
type ApprovalRequest struct {
	// Message is the agent's proposed response
	Message *agenkit.Message
	// Confidence is the agent's confidence level (0.0 to 1.0)
	Confidence float64
	// Context provides additional decision context
	Context map[string]interface{}
	// Timestamp when approval was requested
	Timestamp time.Time
}

// ApprovalResponse represents the human's decision.
type ApprovalResponse struct {
	// Approved indicates if the action is approved
	Approved bool
	// Feedback provides optional human feedback
	Feedback string
	// ModifiedMessage is an optional modified version (if approved with changes)
	ModifiedMessage *agenkit.Message
}

// ApprovalFunc is called when human approval is needed.
//
// The function receives an approval request and should return the human's
// decision. This can be synchronous (blocking for user input) or asynchronous
// (using a queue/callback system).
//
// If the context is cancelled, the function should return immediately.
type ApprovalFunc func(ctx context.Context, request *ApprovalRequest) (*ApprovalResponse, error)

// HumanInLoopAgent wraps an agent with human approval gates.
//
// The agent executes normally, but when confidence is below the threshold,
// human approval is requested before returning the response. This provides
// oversight for high-stakes decisions while allowing autonomous operation
// for routine tasks.
//
// Example use cases:
//   - Financial trading: approve large transactions
//   - Content moderation: verify edge cases
//   - Healthcare: approve treatment recommendations
//   - Legal: review contract changes
//   - Security: approve access grants
//
// The human-in-loop pattern is ideal when autonomous operation needs
// human oversight for critical or uncertain decisions.
type HumanInLoopAgent struct {
	name              string
	agent             agenkit.Agent
	approvalThreshold float64
	approvalFunc      ApprovalFunc
	confidenceKey     string
}

// HumanInLoopConfig configures a HumanInLoopAgent.
type HumanInLoopConfig struct {
	// Agent to wrap with human approval
	Agent agenkit.Agent
	// ApprovalThreshold for requiring approval (0.0 to 1.0, default: 0.8)
	// Responses with confidence below this require approval
	ApprovalThreshold float64
	// ApprovalFunc is called when approval is needed
	ApprovalFunc ApprovalFunc
	// ConfidenceKey specifies metadata key for confidence (default: "confidence")
	ConfidenceKey string
}

// NewHumanInLoopAgent creates a new human-in-loop agent.
//
// Parameters:
//   - config: Configuration with agent and approval settings
//
// The approval threshold determines when human approval is required.
// A threshold of 0.8 means approval is needed when confidence < 0.8.
// The agent's response metadata should include a confidence value.
func NewHumanInLoopAgent(config *HumanInLoopConfig) (*HumanInLoopAgent, error) {
	if config == nil {
		return nil, fmt.Errorf("config is required")
	}
	if config.Agent == nil {
		return nil, fmt.Errorf("agent is required")
	}
	if config.ApprovalFunc == nil {
		return nil, fmt.Errorf("approval function is required")
	}

	threshold := config.ApprovalThreshold
	if threshold == 0 {
		threshold = 0.8
	}
	if threshold < 0 || threshold > 1 {
		return nil, fmt.Errorf("approval threshold must be between 0 and 1 (got %.2f)", threshold)
	}

	confidenceKey := config.ConfidenceKey
	if confidenceKey == "" {
		confidenceKey = "confidence"
	}

	return &HumanInLoopAgent{
		name:              "HumanInLoopAgent",
		agent:             config.Agent,
		approvalThreshold: threshold,
		approvalFunc:      config.ApprovalFunc,
		confidenceKey:     confidenceKey,
	}, nil
}

// Name returns the agent's identifier.
func (h *HumanInLoopAgent) Name() string {
	return h.name
}

// Capabilities returns the agent's capabilities plus human-in-loop.
func (h *HumanInLoopAgent) Capabilities() []string {
	caps := h.agent.Capabilities()
	return append(caps, "human-in-loop", "approval", "oversight")
}

// Process executes the agent with human approval when needed.
//
// The process follows these steps:
//  1. Execute underlying agent
//  2. Extract confidence from response metadata
//  3. If confidence < threshold, request human approval
//  4. Return approved response or rejection message
//
// If approval is denied, a message indicating rejection is returned.
// If approval includes modifications, the modified message is returned.
//
// The final message includes metadata about the approval process.
func (h *HumanInLoopAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if message == nil {
		return nil, fmt.Errorf("message cannot be nil")
	}

	// Execute underlying agent
	response, err := h.agent.Process(ctx, message)
	if err != nil {
		return nil, fmt.Errorf("agent execution failed: %w", err)
	}

	// Extract confidence from metadata
	confidence := h.extractConfidence(response)

	// Check if approval needed
	needsApproval := confidence < h.approvalThreshold

	// Add approval metadata
	if response.Metadata == nil {
		response.Metadata = make(map[string]interface{})
	}
	response.Metadata["approval_needed"] = needsApproval
	response.Metadata["confidence"] = confidence
	response.Metadata["approval_threshold"] = h.approvalThreshold

	// If high confidence, return without approval
	if !needsApproval {
		response.Metadata["approval_status"] = "bypassed"
		return response, nil
	}

	// Request human approval
	request := &ApprovalRequest{
		Message:    response,
		Confidence: confidence,
		Context: map[string]interface{}{
			"agent":                h.agent.Name(),
			"approval_threshold":   h.approvalThreshold,
			"original_message":     message.Content,
			"confidence_shortfall": h.approvalThreshold - confidence,
		},
		Timestamp: time.Now().UTC(),
	}

	approval, err := h.approvalFunc(ctx, request)
	if err != nil {
		return nil, fmt.Errorf("approval request failed: %w", err)
	}

	// Handle approval decision
	if !approval.Approved {
		// Request denied
		rejectionMsg := agenkit.NewMessage("agent",
			"Action rejected by human reviewer")

		if approval.Feedback != "" {
			rejectionMsg.WithMetadata("rejection_reason", approval.Feedback)
		}

		rejectionMsg.Metadata["approval_status"] = "rejected"
		rejectionMsg.Metadata["original_response"] = response.Content
		rejectionMsg.Metadata["confidence"] = confidence

		return rejectionMsg, nil
	}

	// Request approved
	finalResponse := response
	if approval.ModifiedMessage != nil {
		// Use modified version
		finalResponse = approval.ModifiedMessage
		finalResponse.Metadata["approval_status"] = "approved_with_modifications"
		finalResponse.Metadata["original_response"] = response.Content
	} else {
		finalResponse.Metadata["approval_status"] = "approved"
	}

	if approval.Feedback != "" {
		finalResponse.Metadata["approval_feedback"] = approval.Feedback
	}

	return finalResponse, nil
}

// extractConfidence gets confidence value from message metadata.
func (h *HumanInLoopAgent) extractConfidence(message *agenkit.Message) float64 {
	if message.Metadata == nil {
		return 0.0
	}

	confidenceVal, ok := message.Metadata[h.confidenceKey]
	if !ok {
		return 0.0
	}

	// Try to convert to float64
	switch v := confidenceVal.(type) {
	case float64:
		return v
	case float32:
		return float64(v)
	case int:
		return float64(v)
	case int64:
		return float64(v)
	default:
		return 0.0
	}
}

// SimpleApprovalFunc creates a basic approval function for testing/demos.
//
// This function automatically approves or rejects based on a static decision.
// For production use, implement a custom ApprovalFunc that prompts humans.
func SimpleApprovalFunc(autoApprove bool) ApprovalFunc {
	return func(ctx context.Context, request *ApprovalRequest) (*ApprovalResponse, error) {
		return &ApprovalResponse{
			Approved: autoApprove,
			Feedback: fmt.Sprintf("Auto-%s (confidence: %.2f)",
				map[bool]string{true: "approved", false: "rejected"}[autoApprove],
				request.Confidence),
		}, nil
	}
}

// ConsoleApprovalFunc creates an approval function that prompts via console.
//
// This is useful for CLI applications and demos. For production web/mobile
// apps, implement a custom ApprovalFunc using your UI framework.
//
// Note: This function is not included in the actual implementation as it
// would require fmt.Scan which doesn't work well in all contexts. Users
// should implement their own approval functions based on their needs.
//
// Example implementation:
//
//	func ConsoleApprovalFunc(ctx context.Context, request *ApprovalRequest) (*ApprovalResponse, error) {
//	    fmt.Printf("\nApproval Required (confidence: %.2f)\n", request.Confidence)
//	    fmt.Printf("Message: %s\n", request.Message.Content)
//	    fmt.Print("Approve? (y/n): ")
//
//	    var response string
//	    fmt.Scan(&response)
//
//	    return &ApprovalResponse{
//	        Approved: strings.ToLower(response) == "y",
//	    }, nil
//	}

// ConfidenceBasedApprovalFunc creates an approval function with dynamic thresholds.
//
// This allows different approval rules based on confidence levels. For example:
//   - Very low confidence (< 0.5): always reject
//   - Low confidence (0.5-0.7): require approval
//   - Medium confidence (0.7-0.8): require approval
//   - High confidence (>= 0.8): auto-approve
func ConfidenceBasedApprovalFunc(rejectBelow float64, autoApproveAbove float64) ApprovalFunc {
	return func(ctx context.Context, request *ApprovalRequest) (*ApprovalResponse, error) {
		if request.Confidence < rejectBelow {
			return &ApprovalResponse{
				Approved: false,
				Feedback: fmt.Sprintf("Confidence too low (%.2f < %.2f)",
					request.Confidence, rejectBelow),
			}, nil
		}

		if request.Confidence >= autoApproveAbove {
			return &ApprovalResponse{
				Approved: true,
				Feedback: fmt.Sprintf("Auto-approved (%.2f >= %.2f)",
					request.Confidence, autoApproveAbove),
			}, nil
		}

		// In this range, you would typically prompt a human
		// For this example, we'll reject to be safe
		return &ApprovalResponse{
			Approved: false,
			Feedback: fmt.Sprintf("Manual approval required (%.2f in threshold range)",
				request.Confidence),
		}, nil
	}
}
