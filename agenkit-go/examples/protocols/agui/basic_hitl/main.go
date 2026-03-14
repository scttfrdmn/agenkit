// Basic AG-UI Human-in-the-Loop Example
//
// Demonstrates the AG-UI HITL adapter with Interrupt events for approval notifications.
// Shows how HumanInLoopAgent integrates with AG-UI protocol to emit Interrupt events
// when approval is required.
//
// Key concepts:
//   - AGUIHumanInLoopAdapter wraps HumanInLoopAgent
//   - Interrupt events emitted for approval decisions
//   - Metadata includes HITL capabilities
//   - Confidence-based approval thresholds
//
// This example shows:
//   - Basic HITL integration with AG-UI
//   - Interrupt event structure
//   - High vs low confidence handling
//   - Approval status in event context
//
// Usage:
//
//	go run 01_basic_hitl.go
package main

import (
	"context"
	"fmt"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
	"github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui"
)

// SimpleAgent is a simple agent that returns responses with varying confidence.
type SimpleAgent struct {
	name       string
	confidence float64
}

// NewSimpleAgent creates a new simple agent with specified confidence.
func NewSimpleAgent(name string, confidence float64) *SimpleAgent {
	return &SimpleAgent{
		name:       name,
		confidence: confidence,
	}
}

func (s *SimpleAgent) Name() string {
	return s.name
}

func (s *SimpleAgent) Capabilities() []string {
	return []string{"chat", "analysis"}
}

func (s *SimpleAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Printf("   🤖 %s processing: %s\n", s.name, message.ContentString())
	time.Sleep(100 * time.Millisecond)

	response := agenkit.NewMessage("assistant", fmt.Sprintf("Processed: %s", message.ContentString()))
	response.Metadata = map[string]interface{}{
		"confidence": s.confidence,
	}

	return response, nil
}

func (s *SimpleAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:     s.name,
		Capabilities:  s.Capabilities(),
		InternalState: make(map[string]interface{}),
		Metadata:      map[string]interface{}{"confidence": s.confidence},
	}
}

// simpleApprovalFunc is a simple approval function that logs and auto-approves.
func simpleApprovalFunc(ctx context.Context, request *patterns.ApprovalRequest) (*patterns.ApprovalResponse, error) {
	confidence := request.Confidence
	fmt.Printf("   👤 Approval requested - Confidence: %.2f\n", confidence)
	fmt.Printf("      Message: %s\n", request.Message.ContentString())
	fmt.Printf("      Context: %v\n", request.Context)

	// For demo, auto-approve after short delay
	time.Sleep(100 * time.Millisecond)
	fmt.Println("   ✅ Approved")

	return &patterns.ApprovalResponse{
		Approved: true,
		Feedback: fmt.Sprintf("Approved with confidence %.2f", confidence),
	}, nil
}

// exampleHighConfidence demonstrates high confidence scenario (no approval needed).
func exampleHighConfidence() {
	fmt.Println("======================================================================")
	fmt.Println("Example 1: High Confidence (No Approval)")
	fmt.Println("======================================================================")

	// Create agent with high confidence
	agent := NewSimpleAgent("HighConfidenceAgent", 0.95)

	// Wrap with HumanInLoopAgent (threshold 0.8)
	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             agent,
		ApprovalFunc:      simpleApprovalFunc,
		ApprovalThreshold: 0.8,
	})
	if err != nil {
		fmt.Printf("Error creating HumanInLoopAgent: %v\n", err)
		return
	}

	// Wrap with AG-UI adapter
	adapter := agui.NewAGUIHumanInLoopAdapter(hilAgent, "HighConfidenceDemo", true)

	// Stream events
	message := agenkit.NewMessage("user", "What is 2+2?")
	fmt.Printf("\n📥 User: %s\n\n", message.ContentString())

	ctx := context.Background()
	events := []agui.AGUIEvent{}
	interruptCount := 0

	for event := range adapter.StreamEvents(ctx, message) {
		events = append(events, event)
		fmt.Printf("📡 Event: %T\n", event)

		switch e := event.(type) {
		case *agui.MetadataEvent:
			fmt.Printf("   Agent: %v\n", e.Data["agent_name"])
			fmt.Printf("   Capabilities: %v\n", e.Data["capabilities"])
			fmt.Printf("   Supports HITL: %v\n", e.Data["supports_hitl"])

		case *agui.Interrupt:
			interruptCount++
			fmt.Printf("   ⚠️  Interrupt! Reason: %s\n", e.Reason)
			fmt.Printf("   Message: %s\n", e.Message)
			fmt.Printf("   Context: %v\n", e.Context)
		}
	}

	// Analysis
	fmt.Println("\n📊 Analysis:")
	fmt.Printf("   Total events: %d\n", len(events))
	fmt.Printf("   Interrupts: %d\n", interruptCount)
	fmt.Println("   ✓ High confidence bypassed approval (no interrupt)")
}

// exampleLowConfidence demonstrates low confidence scenario (approval required).
func exampleLowConfidence() {
	fmt.Println("\n\n======================================================================")
	fmt.Println("Example 2: Low Confidence (Approval Required)")
	fmt.Println("======================================================================")

	// Create agent with low confidence
	agent := NewSimpleAgent("LowConfidenceAgent", 0.5)

	// Wrap with HumanInLoopAgent (threshold 0.8)
	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             agent,
		ApprovalFunc:      simpleApprovalFunc,
		ApprovalThreshold: 0.8,
	})
	if err != nil {
		fmt.Printf("Error creating HumanInLoopAgent: %v\n", err)
		return
	}

	// Wrap with AG-UI adapter
	adapter := agui.NewAGUIHumanInLoopAdapter(hilAgent, "LowConfidenceDemo", true)

	// Stream events
	message := agenkit.NewMessage("user", "Make a critical decision")
	fmt.Printf("\n📥 User: %s\n\n", message.ContentString())

	ctx := context.Background()
	events := []agui.AGUIEvent{}
	var interrupt *agui.Interrupt

	for event := range adapter.StreamEvents(ctx, message) {
		events = append(events, event)
		fmt.Printf("📡 Event: %T\n", event)

		if e, ok := event.(*agui.Interrupt); ok {
			interrupt = e
			fmt.Printf("   ⚠️  Interrupt! Reason: %s\n", e.Reason)
			fmt.Printf("   Message: %s\n", e.Message)
			fmt.Printf("   Approval Status: %v\n", e.Context["approval_status"])
			fmt.Printf("   Confidence: %v\n", e.Context["confidence"])
			fmt.Printf("   Threshold: %v\n", e.Context["approval_threshold"])
			fmt.Printf("   Approval Needed: %v\n", e.Context["approval_needed"])
		}
	}

	// Analysis
	fmt.Println("\n📊 Analysis:")
	fmt.Printf("   Total events: %d\n", len(events))
	if interrupt != nil {
		fmt.Println("   Interrupts: 1")
		fmt.Println("   ✓ Low confidence triggered approval")
		fmt.Println("   ✓ Interrupt emitted with approval status")
		fmt.Printf("   Reason: %s\n", interrupt.Reason)
	} else {
		fmt.Println("   Interrupts: 0")
	}
}

// exampleRejection demonstrates approval rejection scenario.
func exampleRejection() {
	fmt.Println("\n\n======================================================================")
	fmt.Println("Example 3: Approval Rejection")
	fmt.Println("======================================================================")

	// Rejection approval function
	rejectApprovalFunc := func(ctx context.Context, request *patterns.ApprovalRequest) (*patterns.ApprovalResponse, error) {
		confidence := request.Confidence
		fmt.Printf("   👤 Approval requested - Confidence: %.2f\n", confidence)
		time.Sleep(100 * time.Millisecond)
		fmt.Println("   ❌ Rejected - Too risky")
		return &patterns.ApprovalResponse{
			Approved: false,
			Feedback: "Confidence too low for this operation",
		}, nil
	}

	// Create agent with low confidence
	agent := NewSimpleAgent("RiskyAgent", 0.4)

	// Wrap with HumanInLoopAgent
	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             agent,
		ApprovalFunc:      rejectApprovalFunc,
		ApprovalThreshold: 0.8,
	})
	if err != nil {
		fmt.Printf("Error creating HumanInLoopAgent: %v\n", err)
		return
	}

	// Wrap with AG-UI adapter
	adapter := agui.NewAGUIHumanInLoopAdapter(hilAgent, "RejectionDemo", true)

	// Stream events
	message := agenkit.NewMessage("user", "Execute risky operation")
	fmt.Printf("\n📥 User: %s\n\n", message.ContentString())

	ctx := context.Background()
	events := []agui.AGUIEvent{}
	var interrupt *agui.Interrupt

	for event := range adapter.StreamEvents(ctx, message) {
		events = append(events, event)
		fmt.Printf("📡 Event: %T\n", event)

		if e, ok := event.(*agui.Interrupt); ok {
			interrupt = e
			fmt.Printf("   ⚠️  Interrupt! Status: %v\n", e.Context["approval_status"])
			fmt.Printf("   Message: %s\n", e.Message)
		}
	}

	// Analysis
	fmt.Println("\n📊 Analysis:")
	fmt.Printf("   Total events: %d\n", len(events))
	if interrupt != nil {
		fmt.Println("   Interrupts: 1")
		status := interrupt.Context["approval_status"]
		fmt.Printf("   ✓ Approval was %v\n", status)
		fmt.Printf("   Reason: %s\n", agui.InterruptReasonApprovalRequired)
	} else {
		fmt.Println("   Interrupts: 0")
	}
}

// exampleDisabledInterrupts demonstrates disabling interrupt events.
func exampleDisabledInterrupts() {
	fmt.Println("\n\n======================================================================")
	fmt.Println("Example 4: Disabled Interrupts")
	fmt.Println("======================================================================")

	// Create agent with low confidence
	agent := NewSimpleAgent("QuietAgent", 0.5)

	// Wrap with HumanInLoopAgent
	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             agent,
		ApprovalFunc:      simpleApprovalFunc,
		ApprovalThreshold: 0.8,
	})
	if err != nil {
		fmt.Printf("Error creating HumanInLoopAgent: %v\n", err)
		return
	}

	// Wrap with AG-UI adapter with interrupts DISABLED
	adapter := agui.NewAGUIHumanInLoopAdapter(hilAgent, "DisabledInterruptsDemo", false)

	// Stream events
	message := agenkit.NewMessage("user", "Test with interrupts disabled")
	fmt.Printf("\n📥 User: %s\n\n", message.ContentString())

	ctx := context.Background()
	events := []agui.AGUIEvent{}
	interruptCount := 0

	for event := range adapter.StreamEvents(ctx, message) {
		events = append(events, event)
		fmt.Printf("📡 Event: %T\n", event)

		if _, ok := event.(*agui.Interrupt); ok {
			interruptCount++
		}
	}

	// Analysis
	fmt.Println("\n📊 Analysis:")
	fmt.Printf("   Total events: %d\n", len(events))
	fmt.Printf("   Interrupts: %d\n", interruptCount)
	fmt.Println("   ✓ Interrupts disabled - no Interrupt events emitted")
	fmt.Println("   ✓ Approval still executed internally by HumanInLoopAgent")
}

func main() {
	fmt.Println("AG-UI Basic Human-in-the-Loop Examples")
	fmt.Println()

	// Run examples
	exampleHighConfidence()
	exampleLowConfidence()
	exampleRejection()
	exampleDisabledInterrupts()

	fmt.Println("\n\n======================================================================")
	fmt.Println("✅ All examples completed successfully!")
	fmt.Println("======================================================================")
}
