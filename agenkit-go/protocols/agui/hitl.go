// AG-UI Human-in-the-Loop Integration
//
// Integrates the HumanInLoopAgent pattern with AG-UI protocol using Interrupt events.
// Provides streaming approval workflow where agents can request human approval via
// Interrupt events, and frontends can respond with InterruptResponse messages.
//
// Key concepts:
//   - Interrupt events for approval requests
//   - InterruptResponse for approval decisions
//   - Streaming approval workflow
//   - Integration with HumanInLoopAgent pattern
//
// Example:
//
//	import (
//	    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
//	    "github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui"
//	)
//
//	// Create human-in-loop agent
//	hilAgent, _ := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
//	    Agent:             myAgent,
//	    ApprovalFunc:      myApprovalFunc,
//	    ApprovalThreshold: 0.8,
//	})
//
//	// Wrap with AG-UI adapter
//	adapter := agui.NewAGUIHumanInLoopAdapter(hilAgent)
//
//	// Stream events (includes Interrupt events for approval requests)
//	for event := range adapter.StreamEvents(ctx, userMessage) {
//	    if interrupt, ok := event.(*agui.Interrupt); ok {
//	        // Frontend displays approval request
//	        // User responds via InterruptResponse
//	    }
//	}
package agui

import (
	"context"
	"fmt"
	"sync"

	"github.com/google/uuid"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// AGUIHumanInLoopAdapter is an AG-UI adapter with human-in-the-loop support via Interrupt events.
//
// This adapter integrates the HumanInLoopAgent pattern with AG-UI protocol.
// When an agent requires approval (confidence < threshold), an Interrupt event
// is emitted to request human approval. The frontend can respond via
// InterruptResponse.
//
// The adapter handles:
//   - Converting approval requests to Interrupt events
//   - Processing InterruptResponse from frontend
//   - Streaming approval workflow
//   - Metadata about approval decisions
//
// Example:
//
//	hilAgent, _ := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
//	    Agent:             myAgent,
//	    ApprovalFunc:      myApprovalFunc,
//	    ApprovalThreshold: 0.8,
//	})
//
//	adapter := agui.NewAGUIHumanInLoopAdapter(hilAgent)
//	for event := range adapter.StreamEvents(ctx, message) {
//	    if interrupt, ok := event.(*agui.Interrupt); ok {
//	        // Display approval request to user
//	    }
//	}
type AGUIHumanInLoopAdapter struct {
	*AGUIAdapter
	emitInterrupts    bool
	pendingInterrupts map[string]interface{}
	mu                sync.Mutex
}

// NewAGUIHumanInLoopAdapter creates a new AG-UI human-in-loop adapter.
//
// Parameters:
//   - agent: Agent to wrap (HumanInLoopAgent or regular Agent)
//   - agentName: Optional agent name for metadata (empty string uses agent's name)
//   - emitInterrupts: Whether to emit Interrupt events for approval requests
//
// If agent is not a HumanInLoopAgent or emitInterrupts is false,
// behaves like a standard AGUIAdapter.
func NewAGUIHumanInLoopAdapter(agent agenkit.Agent, agentName string, emitInterrupts bool) *AGUIHumanInLoopAdapter {
	baseAdapter := NewAGUIAdapter(agent)
	if agentName != "" {
		baseAdapter.agentName = agentName
	}

	return &AGUIHumanInLoopAdapter{
		AGUIAdapter:       baseAdapter,
		emitInterrupts:    emitInterrupts,
		pendingInterrupts: make(map[string]interface{}),
	}
}

// StreamEvents streams AG-UI events with interrupt support.
//
// When the agent requires approval, emits an Interrupt event to notify
// the frontend about the approval decision.
//
// Note: This implementation emits Interrupt events after the approval
// decision has been made (informational). For true bidirectional HITL,
// use a custom approval_func that integrates with your transport layer.
//
// Parameters:
//   - ctx: Context for cancellation
//   - message: Input message to process
//
// Returns:
//   - Channel of AG-UI events (includes Interrupt events for approval notifications)
//
// Example:
//
//	for event := range adapter.StreamEvents(ctx, message) {
//	    if interrupt, ok := event.(*agui.Interrupt); ok {
//	        // Approval decision was made
//	        fmt.Printf("Approval: %v\n", interrupt.Context["approval_status"])
//	    }
//	}
func (h *AGUIHumanInLoopAdapter) StreamEvents(ctx context.Context, message *agenkit.Message) <-chan AGUIEvent {
	eventChan := make(chan AGUIEvent, 10)

	go func() {
		defer close(eventChan)

		// Check if agent is a HumanInLoopAgent
		_, isHIL := h.agent.(*patterns.HumanInLoopAgent)

		// For regular agents or if interrupts disabled, use standard streaming
		if !isHIL || !h.emitInterrupts {
			// Stream from base adapter
			for event := range h.AGUIAdapter.StreamEvents(ctx, message) {
				select {
				case eventChan <- event:
				case <-ctx.Done():
					return
				}
			}
			return
		}

		// Emit metadata first
		select {
		case eventChan <- h.createMetadataEvent():
		case <-ctx.Done():
			return
		}

		// Process message (HumanInLoopAgent will handle approval synchronously)
		response, err := h.agent.Process(ctx, message)
		if err != nil {
			// Emit error event
			select {
			case eventChan <- h.createErrorEvent(h.generateMessageID(), err):
			case <-ctx.Done():
				return
			}
			return
		}

		// Check if approval was involved (approved, rejected, or bypassed)
		var approvalStatus string
		if response.Metadata != nil {
			if status, ok := response.Metadata["approval_status"].(string); ok {
				approvalStatus = status
			}
		}

		// Emit Interrupt event if approval was part of the flow (not bypassed)
		if approvalStatus == "approved" || approvalStatus == "rejected" || approvalStatus == "approved_with_modifications" {
			interruptID := uuid.New().String()
			confidence := 0.0
			if response.Metadata != nil {
				if conf, ok := response.Metadata["confidence"].(float64); ok {
					confidence = conf
				}
			}

			// Emit informational Interrupt event about the approval
			interrupt := NewInterrupt(
				interruptID,
				InterruptReasonApprovalRequired,
				fmt.Sprintf("Approval %s (confidence: %.2f)", approvalStatus, confidence),
			)
			interrupt.Context = map[string]interface{}{
				"approval_status":    approvalStatus,
				"confidence":         confidence,
				"approval_threshold": response.Metadata["approval_threshold"],
				"approval_needed":    true,
			}
			interrupt.Actions = []InterruptAction{} // No actions - already decided
			interrupt.TimeoutSeconds = nil

			select {
			case eventChan <- interrupt:
			case <-ctx.Done():
				return
			}
		}

		// Stream the response content as text message events
		msgID := h.generateMessageID()

		// Emit TextMessageStart
		startEvent := NewTextMessageStart(msgID, "assistant")
		startEvent.Metadata = map[string]interface{}{
			"agent_name": h.agentName,
		}
		select {
		case eventChan <- startEvent:
		case <-ctx.Done():
			return
		}

		// Extract content
		content := ""
		if cs := response.ContentString(); cs != "" {
			content = cs
		}

		// Stream content in chunks
		chunkSize := 50
		for i := 0; i < len(content); i += chunkSize {
			end := i + chunkSize
			if end > len(content) {
				end = len(content)
			}
			chunk := content[i:end]

			chunkEvent := NewTextMessageChunk(msgID, chunk)
			chunkEvent.Metadata = map[string]interface{}{
				"chunk_index": i / chunkSize,
			}

			select {
			case eventChan <- chunkEvent:
			case <-ctx.Done():
				return
			}
		}

		// Emit completion
		completeEvent := NewTextMessageComplete(msgID, content, "stop")
		if response.Metadata != nil {
			completeEvent.Metadata = make(map[string]interface{})
			completeEvent.Metadata["agent_name"] = h.agentName
			for k, v := range response.Metadata {
				completeEvent.Metadata[k] = v
			}
		}

		select {
		case eventChan <- completeEvent:
		case <-ctx.Done():
			return
		}
	}()

	return eventChan
}

// StreamEventsWithConfig streams events with custom configuration.
//
// Parameters:
//   - ctx: Context for cancellation
//   - message: Input message to process
//   - config: Configuration for streaming behavior
//
// Returns:
//   - Channel of AG-UI events
func (h *AGUIHumanInLoopAdapter) StreamEventsWithConfig(
	ctx context.Context,
	message *agenkit.Message,
	config StreamEventsConfig,
) <-chan AGUIEvent {
	eventChan := make(chan AGUIEvent, 10)

	go func() {
		defer close(eventChan)

		// Check if agent is a HumanInLoopAgent
		_, isHIL := h.agent.(*patterns.HumanInLoopAgent)

		// For regular agents or if interrupts disabled, use standard streaming
		if !isHIL || !h.emitInterrupts {
			// Stream from base adapter
			for event := range h.AGUIAdapter.StreamEventsWithConfig(ctx, message, config) {
				select {
				case eventChan <- event:
				case <-ctx.Done():
					return
				}
			}
			return
		}

		// Emit metadata if requested
		if config.EmitMetadata {
			select {
			case eventChan <- h.createMetadataEvent():
			case <-ctx.Done():
				return
			}
		}

		// Process message (HumanInLoopAgent will handle approval synchronously)
		response, err := h.agent.Process(ctx, message)
		if err != nil {
			// Emit error event
			msgID := config.MessageID
			if msgID == "" {
				msgID = h.generateMessageID()
			}
			select {
			case eventChan <- h.createErrorEvent(msgID, err):
			case <-ctx.Done():
				return
			}
			return
		}

		// Check if approval was involved
		var approvalStatus string
		if response.Metadata != nil {
			if status, ok := response.Metadata["approval_status"].(string); ok {
				approvalStatus = status
			}
		}

		// Emit Interrupt event if approval was part of the flow
		if approvalStatus == "approved" || approvalStatus == "rejected" || approvalStatus == "approved_with_modifications" {
			interruptID := uuid.New().String()
			confidence := 0.0
			if response.Metadata != nil {
				if conf, ok := response.Metadata["confidence"].(float64); ok {
					confidence = conf
				}
			}

			interrupt := NewInterrupt(
				interruptID,
				InterruptReasonApprovalRequired,
				fmt.Sprintf("Approval %s (confidence: %.2f)", approvalStatus, confidence),
			)
			interrupt.Context = map[string]interface{}{
				"approval_status":    approvalStatus,
				"confidence":         confidence,
				"approval_threshold": response.Metadata["approval_threshold"],
				"approval_needed":    true,
			}
			interrupt.Actions = []InterruptAction{}
			interrupt.TimeoutSeconds = nil

			select {
			case eventChan <- interrupt:
			case <-ctx.Done():
				return
			}
		}

		// Use provided message ID or generate one
		msgID := config.MessageID
		if msgID == "" {
			msgID = h.generateMessageID()
		}

		// Emit TextMessageStart
		startEvent := NewTextMessageStart(msgID, "assistant")
		startEvent.Metadata = map[string]interface{}{
			"agent_name": h.agentName,
		}
		select {
		case eventChan <- startEvent:
		case <-ctx.Done():
			return
		}

		// Extract content
		content := ""
		if cs := response.ContentString(); cs != "" {
			content = cs
		}

		// Stream content in chunks
		chunkSize := 50
		for i := 0; i < len(content); i += chunkSize {
			end := i + chunkSize
			if end > len(content) {
				end = len(content)
			}
			chunk := content[i:end]

			chunkEvent := NewTextMessageChunk(msgID, chunk)
			chunkEvent.Metadata = map[string]interface{}{
				"chunk_index": i / chunkSize,
			}

			select {
			case eventChan <- chunkEvent:
			case <-ctx.Done():
				return
			}
		}

		// Emit completion
		completeEvent := NewTextMessageComplete(msgID, content, "stop")
		if response.Metadata != nil {
			completeEvent.Metadata = make(map[string]interface{})
			completeEvent.Metadata["agent_name"] = h.agentName
			for k, v := range response.Metadata {
				completeEvent.Metadata[k] = v
			}
		}

		select {
		case eventChan <- completeEvent:
		case <-ctx.Done():
			return
		}
	}()

	return eventChan
}

// HandleInterruptResponse handles InterruptResponse from frontend.
//
// This is called when the frontend responds to an Interrupt event.
// Updates the pending interrupt context with the approval decision.
//
// Parameters:
//   - interruptResponse: Response from frontend with approval decision
//
// Returns:
//   - Error if interrupt_id not found in pending interrupts
func (h *AGUIHumanInLoopAdapter) HandleInterruptResponse(interruptResponse *InterruptResponse) error {
	h.mu.Lock()
	defer h.mu.Unlock()

	interruptID := interruptResponse.InterruptID
	context, ok := h.pendingInterrupts[interruptID]
	if !ok {
		return fmt.Errorf("unknown interrupt_id: %s", interruptID)
	}

	// Get response from context
	contextMap, ok := context.(map[string]interface{})
	if !ok {
		return fmt.Errorf("invalid context type")
	}

	response, ok := contextMap["response"].(*agenkit.Message)
	if !ok {
		return fmt.Errorf("response not found in context")
	}

	// Update response metadata based on user action
	if response.Metadata == nil {
		response.Metadata = make(map[string]interface{})
	}

	switch interruptResponse.Action {
	case InterruptActionApprove:
		response.Metadata["approval_status"] = "approved"
		if interruptResponse.Data != nil {
			if feedback, ok := interruptResponse.Data["feedback"].(string); ok && feedback != "" {
				response.Metadata["approval_feedback"] = feedback
			}
		}

	case InterruptActionReject:
		response.Metadata["approval_status"] = "rejected"
		if interruptResponse.Data != nil {
			if reason, ok := interruptResponse.Data["reason"].(string); ok && reason != "" {
				response.Metadata["rejection_reason"] = reason
			}
		}

	case InterruptActionEdit:
		response.Metadata["approval_status"] = "approved_with_modifications"
		response.Metadata["original_response"] = response.ContentString()
		if interruptResponse.Data != nil {
			if modifiedContent, ok := interruptResponse.Data["modified_content"].(string); ok && modifiedContent != "" {
				response.Content = modifiedContent
			}
		}
	}

	// Remove from pending
	delete(h.pendingInterrupts, interruptID)

	return nil
}

// createMetadataEvent creates metadata event with HITL capabilities.
func (h *AGUIHumanInLoopAdapter) createMetadataEvent() *MetadataEvent {
	// Get base metadata from parent
	baseMetadata := h.AGUIAdapter.createMetadataEvent()

	// Add HITL capabilities if agent supports it
	if _, isHIL := h.agent.(*patterns.HumanInLoopAgent); isHIL {
		// Extend capabilities
		caps, ok := baseMetadata.Data["capabilities"].([]string)
		if !ok {
			caps = []string{}
		}
		caps = append(caps, "human-in-loop", "approval", "interrupts")
		baseMetadata.Data["capabilities"] = caps

		// Add HITL metadata
		baseMetadata.Data["supports_hitl"] = true
	}

	return baseMetadata
}
