// Package main demonstrates the HumanInLoopAgent pattern.
//
// # Human approval gates for high-stakes decisions
//
// Use cases:
//   - Financial approvals
//   - Content moderation
//   - Critical system changes
//
// Run with: go run human-in-loop_usage.go
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// SimpleAgent is a basic agent for demonstration
type SimpleAgent struct {
	name string
}

func (a *SimpleAgent) Name() string {
	return a.name
}

func (a *SimpleAgent) Capabilities() []string {
	return []string{"demo"}
}

func (a *SimpleAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Printf("   🤖 %s processing...\n", a.name)
	time.Sleep(100 * time.Millisecond)

	// Simulate varying confidence levels based on agent name
	var confidence float64
	switch a.name {
	case "Agent2":
		confidence = 0.7 // Medium confidence - will require approval
	case "Agent3":
		confidence = 0.5 // Low confidence - will require approval
	default:
		confidence = 0.9 // High confidence by default
	}

	result := agenkit.NewMessage("agent", fmt.Sprintf("%s processed: %s", a.name, message.Content))
	result.WithMetadata("confidence", confidence)
	return result, nil
}

func (a *SimpleAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    a.Name(),
		Capabilities: a.Capabilities(),
	}
}

func main() {
	fmt.Println("=== HumanInLoopAgent Demo ===")

	// Create agents with different confidence levels
	agent1 := &SimpleAgent{name: "Agent1"} // High confidence (0.9) - no approval needed
	agent2 := &SimpleAgent{name: "Agent2"} // Medium confidence (0.7) - requires approval
	agent3 := &SimpleAgent{name: "Agent3"} // Low confidence (0.5) - requires approval

	ctx := context.Background()

	// Example 1: High confidence agent (bypasses approval)
	fmt.Println("\n📝 Example 1: High confidence agent (bypasses approval)")
	hilAgent1, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             agent1,
		ApprovalThreshold: 0.8, // Agent1 has 0.9 confidence
		ApprovalFunc:      patterns.SimpleApprovalFunc(true),
	})
	if err != nil {
		log.Fatalf("Failed to create HumanInLoopAgent: %v", err)
	}

	msg1 := agenkit.NewMessage("user", "Analyze this data")
	result1, err := hilAgent1.Process(ctx, msg1)
	if err != nil {
		log.Fatalf("Failed to process message: %v", err)
	}
	fmt.Printf("   Result: %s\n", result1.Content)
	fmt.Printf("   Status: %v\n", result1.Metadata["approval_status"])

	// Example 2: Medium confidence agent (requires approval, auto-approved)
	fmt.Println("\n📝 Example 2: Medium confidence agent (requires approval)")
	hilAgent2, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             agent2,
		ApprovalThreshold: 0.8,                               // Agent2 has 0.7 confidence
		ApprovalFunc:      patterns.SimpleApprovalFunc(true), // Auto-approve
	})
	if err != nil {
		log.Fatalf("Failed to create HumanInLoopAgent: %v", err)
	}

	msg2 := agenkit.NewMessage("user", "Make a decision")
	result2, err := hilAgent2.Process(ctx, msg2)
	if err != nil {
		log.Fatalf("Failed to process message: %v", err)
	}
	fmt.Printf("   Result: %s\n", result2.Content)
	fmt.Printf("   Status: %v\n", result2.Metadata["approval_status"])
	fmt.Printf("   Feedback: %v\n", result2.Metadata["approval_feedback"])

	// Example 3: Low confidence agent (requires approval, auto-rejected)
	fmt.Println("\n📝 Example 3: Low confidence agent (requires approval, rejected)")
	hilAgent3, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             agent3,
		ApprovalThreshold: 0.8,                                // Agent3 has 0.5 confidence
		ApprovalFunc:      patterns.SimpleApprovalFunc(false), // Auto-reject
	})
	if err != nil {
		log.Fatalf("Failed to create HumanInLoopAgent: %v", err)
	}

	msg3 := agenkit.NewMessage("user", "Execute action")
	result3, err := hilAgent3.Process(ctx, msg3)
	if err != nil {
		log.Fatalf("Failed to process message: %v", err)
	}
	fmt.Printf("   Result: %s\n", result3.Content)
	fmt.Printf("   Status: %v\n", result3.Metadata["approval_status"])

	// Example 4: Confidence-based approval function
	fmt.Println("\n📝 Example 4: Confidence-based approval (dynamic thresholds)")
	hilAgent4, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             agent2,
		ApprovalThreshold: 0.8,
		// Auto-reject below 0.5, auto-approve above 0.75
		ApprovalFunc: patterns.ConfidenceBasedApprovalFunc(0.5, 0.75),
	})
	if err != nil {
		log.Fatalf("Failed to create HumanInLoopAgent: %v", err)
	}

	msg4 := agenkit.NewMessage("user", "Process with dynamic rules")
	result4, err := hilAgent4.Process(ctx, msg4)
	if err != nil {
		log.Fatalf("Failed to process message: %v", err)
	}
	fmt.Printf("   Result: %s\n", result4.Content)
	fmt.Printf("   Status: %v\n", result4.Metadata["approval_status"])
	if feedback, ok := result4.Metadata["approval_feedback"]; ok {
		fmt.Printf("   Feedback: %v\n", feedback)
	}

	fmt.Println("\n✅ HumanInLoopAgent pattern examples completed")
	fmt.Println("\nUse cases:")
	fmt.Println("  • Financial approvals (high-stakes transactions)")
	fmt.Println("  • Content moderation (edge cases)")
	fmt.Println("  • Critical system changes (require human oversight)")
	fmt.Println("  • Medical decisions (verify treatment plans)")
}
