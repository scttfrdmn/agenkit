// Package main demonstrates the Human-in-Loop pattern for human oversight.
//
// The Human-in-Loop pattern wraps agents with approval gates for high-stakes
// decisions. When agent confidence is below a threshold, human approval is
// requested before proceeding.
//
// This example shows:
//   - Confidence-based approval gates
//   - Different approval strategies
//   - High-stakes decision handling
//   - Automatic vs manual approval paths
//
// Run with: go run human_in_loop_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"math/rand"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// TradingAgent makes trading decisions
type TradingAgent struct {
	minConfidence float64
}

func (t *TradingAgent) Name() string {
	return "TradingAgent"
}

func (t *TradingAgent) Capabilities() []string {
	return []string{"trading", "analysis"}
}

func (t *TradingAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    t.Name(),
		Capabilities: t.Capabilities(),
	}
}

func (t *TradingAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   📊 Trading agent analyzing...")
	time.Sleep(100 * time.Millisecond)

	// Simulate confidence calculation
	confidence := t.minConfidence + rand.Float64()*(1.0-t.minConfidence)

	action := "BUY"
	amount := 1000 + rand.Intn(9000)

	response := fmt.Sprintf("Trading Recommendation: %s $%d of STOCK\n"+
		"Analysis: Market conditions favor this position.\n"+
		"Risk level: %s",
		action, amount,
		map[bool]string{true: "LOW", false: "MEDIUM"}[confidence > 0.85])

	result := agenkit.NewMessage("agent", response)
	result.WithMetadata("confidence", confidence).
		WithMetadata("action", action).
		WithMetadata("amount", amount)

	return result, nil
}

// ModerationAgent makes content moderation decisions
type ModerationAgent struct{}

func (m *ModerationAgent) Name() string {
	return "ModerationAgent"
}

func (m *ModerationAgent) Capabilities() []string {
	return []string{"moderation", "safety"}
}

func (m *ModerationAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *ModerationAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   🛡️  Moderation agent reviewing...")
	time.Sleep(80 * time.Millisecond)

	// Simulate moderation with varying confidence
	content := strings.ToLower(message.Content)
	action := "APPROVE"
	confidence := 0.95

	// Ambiguous cases have lower confidence
	if strings.Contains(content, "borderline") {
		action = "FLAG"
		confidence = 0.65
	} else if strings.Contains(content, "clear") {
		confidence = 0.98
	}

	response := fmt.Sprintf("Moderation Decision: %s\n"+
		"Analysis: Content reviewed against community guidelines.\n"+
		"Severity: %s",
		action,
		map[bool]string{true: "LOW", false: "MEDIUM"}[confidence > 0.8])

	result := agenkit.NewMessage("agent", response)
	result.WithMetadata("confidence", confidence).
		WithMetadata("action", action)

	return result, nil
}

// MedicalAgent makes treatment recommendations
type MedicalAgent struct{}

func (m *MedicalAgent) Name() string {
	return "MedicalAgent"
}

func (m *MedicalAgent) Capabilities() []string {
	return []string{"medical", "diagnosis"}
}

func (m *MedicalAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *MedicalAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   ⚕️  Medical agent analyzing...")
	time.Sleep(120 * time.Millisecond)

	// Medical decisions always require high confidence
	confidence := 0.70 + rand.Float64()*0.25

	treatment := "Treatment Plan A"
	if confidence > 0.85 {
		treatment = "Standard Protocol"
	}

	response := fmt.Sprintf("Medical Recommendation: %s\n"+
		"Diagnosis: Based on symptoms and history.\n"+
		"Confidence: %.0f%%\n"+
		"Note: This recommendation requires physician approval.",
		treatment, confidence*100)

	result := agenkit.NewMessage("agent", response)
	result.WithMetadata("confidence", confidence).
		WithMetadata("treatment", treatment)

	return result, nil
}

func main() {
	fmt.Println("=== Human-in-Loop Pattern Demo ===")
	fmt.Println("Demonstrating human oversight for critical decisions")

	ctx := context.Background()

	// Example 1: High-confidence auto-approval
	fmt.Println("📊 Example 1: High-Confidence Auto-Approval")
	fmt.Println(strings.Repeat("-", 50))

	trader := &TradingAgent{minConfidence: 0.85}

	// Auto-approve high confidence decisions
	autoApproval := patterns.SimpleApprovalFunc(true)

	safeTrade, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             trader,
		ApprovalThreshold: 0.80,
		ApprovalFunc:      autoApproval,
	})
	if err != nil {
		log.Fatalf("Failed to create safe trade agent: %v", err)
	}

	trade := agenkit.NewMessage("user", "Execute trade based on current market conditions")

	fmt.Printf("\n📥 Request: %s\n", trade.Content)
	fmt.Println("\nProcessing with approval threshold of 0.80...")

	result, err := safeTrade.Process(ctx, trade)
	if err != nil {
		log.Fatalf("Trade failed: %v", err)
	}

	fmt.Printf("\n📤 Result:\n%s\n", result.Content)

	if confidence, ok := result.Metadata["confidence"].(float64); ok {
		fmt.Printf("\nMetrics:\n")
		fmt.Printf("  Confidence: %.2f\n", confidence)
	}
	if status, ok := result.Metadata["approval_status"].(string); ok {
		fmt.Printf("  Status: %s\n", status)
	}

	// Example 2: Low-confidence requires approval
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 2: Low-Confidence Approval Required")
	fmt.Println(strings.Repeat("-", 50))

	riskyTrader := &TradingAgent{minConfidence: 0.50}

	// Reject low confidence decisions
	rejectApproval := patterns.SimpleApprovalFunc(false)

	riskyTrade, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             riskyTrader,
		ApprovalThreshold: 0.80,
		ApprovalFunc:      rejectApproval,
	})
	if err != nil {
		log.Fatalf("Failed to create risky trade agent: %v", err)
	}

	fmt.Println("\nProcessing risky trade (likely low confidence)...")

	result, err = riskyTrade.Process(ctx, trade)
	if err != nil {
		log.Fatalf("Trade processing failed: %v", err)
	}

	fmt.Printf("\n📤 Result:\n%s\n", result.Content)

	if confidence, ok := result.Metadata["confidence"].(float64); ok {
		fmt.Printf("\nMetrics:\n")
		fmt.Printf("  Confidence: %.2f\n", confidence)
	}
	if status, ok := result.Metadata["approval_status"].(string); ok {
		fmt.Printf("  Status: %s\n", status)
	}
	if reason, ok := result.Metadata["rejection_reason"].(string); ok {
		fmt.Printf("  Reason: %s\n", reason)
	}

	// Example 3: Confidence-based approval strategy
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 3: Tiered Approval Strategy")
	fmt.Println(strings.Repeat("-", 50))

	moderator := &ModerationAgent{}

	// Use confidence-based approval with thresholds
	tieredApproval := patterns.ConfidenceBasedApprovalFunc(0.50, 0.90)

	smartModerator, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             moderator,
		ApprovalThreshold: 0.80,
		ApprovalFunc:      tieredApproval,
	})
	if err != nil {
		log.Fatalf("Failed to create smart moderator: %v", err)
	}

	cases := []string{
		"Clear violation of guidelines",
		"Borderline content requiring review",
		"Obviously acceptable content",
	}

	fmt.Println("\nTesting tiered approval strategy:")
	fmt.Println("  < 0.50: Auto-reject")
	fmt.Println("  0.50-0.90: Manual review")
	fmt.Println("  >= 0.90: Auto-approve")

	for i, testCase := range cases {
		fmt.Printf("Case %d: %s\n", i+1, testCase)

		msg := agenkit.NewMessage("user", testCase)
		result, err := smartModerator.Process(ctx, msg)
		if err != nil {
			log.Printf("  Error: %v", err)
			continue
		}

		if confidence, ok := result.Metadata["confidence"].(float64); ok {
			fmt.Printf("  Confidence: %.2f\n", confidence)
		}
		if status, ok := result.Metadata["approval_status"].(string); ok {
			fmt.Printf("  Status: %s\n", status)
		}
		fmt.Println()
	}

	// Example 4: Medical decisions always require review
	fmt.Println(strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 4: Critical Domain (Medical)")
	fmt.Println(strings.Repeat("-", 50))

	doctor := &MedicalAgent{}

	// Very high threshold for medical decisions
	medicalApproval := func(ctx context.Context, request *patterns.ApprovalRequest) (*patterns.ApprovalResponse, error) {
		fmt.Printf("\n   ⚠️  HUMAN REVIEW REQUIRED\n")
		fmt.Printf("   Confidence: %.2f\n", request.Confidence)
		fmt.Printf("   Threshold: %.2f\n", request.Context["approval_threshold"].(float64))
		fmt.Printf("   Decision: Forwarding to medical professional for approval\n\n")

		// Simulate physician approval
		return &patterns.ApprovalResponse{
			Approved: true,
			Feedback: "Reviewed and approved by Dr. Smith",
		}, nil
	}

	medicalAI, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             doctor,
		ApprovalThreshold: 0.95, // Very high threshold
		ApprovalFunc:      medicalApproval,
	})
	if err != nil {
		log.Fatalf("Failed to create medical AI: %v", err)
	}

	diagnosis := agenkit.NewMessage("user", "Patient presenting with symptoms X, Y, Z")

	fmt.Printf("\n📥 Case: %s\n", diagnosis.Content)

	result, err = medicalAI.Process(ctx, diagnosis)
	if err != nil {
		log.Fatalf("Medical review failed: %v", err)
	}

	fmt.Printf("📤 Result:\n%s\n", result.Content)

	if status, ok := result.Metadata["approval_status"].(string); ok {
		fmt.Printf("\nStatus: %s\n", status)
	}
	if feedback, ok := result.Metadata["approval_feedback"].(string); ok {
		fmt.Printf("Approved by: %s\n", feedback)
	}

	// Example 5: Modified approval (human edits AI suggestion)
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 5: Approval with Modifications")
	fmt.Println(strings.Repeat("-", 50))

	modifyingApproval := func(ctx context.Context, request *patterns.ApprovalRequest) (*patterns.ApprovalResponse, error) {
		fmt.Println("\n   👤 Human reviewer modifying suggestion...")

		// Simulate human modifying the recommendation
		original := request.Message.Content
		modified := strings.Replace(original, "BUY", "BUY (reduced amount)", 1)
		modified = strings.Replace(modified, "$1000", "$500", 1)

		modifiedMsg := agenkit.NewMessage("agent", modified)
		modifiedMsg.Metadata = request.Message.Metadata

		return &patterns.ApprovalResponse{
			Approved:        true,
			Feedback:        "Approved with risk reduction",
			ModifiedMessage: modifiedMsg,
		}, nil
	}

	conservativeTrader, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             riskyTrader,
		ApprovalThreshold: 0.80,
		ApprovalFunc:      modifyingApproval,
	})
	if err != nil {
		log.Fatalf("Failed to create conservative trader: %v", err)
	}

	fmt.Println("\nProcessing trade with human modification...")

	result, err = conservativeTrader.Process(ctx, trade)
	if err != nil {
		log.Fatalf("Modified trade failed: %v", err)
	}

	fmt.Printf("\n📤 Modified Result:\n%s\n", result.Content)

	if status, ok := result.Metadata["approval_status"].(string); ok {
		fmt.Printf("\nStatus: %s\n", status)
	}
	if feedback, ok := result.Metadata["approval_feedback"].(string); ok {
		fmt.Printf("Feedback: %s\n", feedback)
	}
	if original, ok := result.Metadata["original_response"].(string); ok {
		fmt.Printf("\nOriginal (before modification):\n%s\n", original)
	}

	// Example 6: Bypass for high confidence
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 6: High-Confidence Bypass")
	fmt.Println(strings.Repeat("-", 50))

	highConfTrader := &TradingAgent{minConfidence: 0.90}

	bypassTrader, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             highConfTrader,
		ApprovalThreshold: 0.80,
		ApprovalFunc:      rejectApproval, // Would reject if called
	})
	if err != nil {
		log.Fatalf("Failed to create bypass trader: %v", err)
	}

	fmt.Println("\nProcessing high-confidence trade (should bypass approval)...")

	result, err = bypassTrader.Process(ctx, trade)
	if err != nil {
		log.Fatalf("Bypass trade failed: %v", err)
	}

	if confidence, ok := result.Metadata["confidence"].(float64); ok {
		fmt.Printf("Confidence: %.2f\n", confidence)
	}
	if status, ok := result.Metadata["approval_status"].(string); ok {
		fmt.Printf("Status: %s\n", status)
	}
	if status, ok := result.Metadata["approval_status"].(string); ok && status == "bypassed" {
		fmt.Println("\n✓ Approval bypassed due to high confidence")
	}

	fmt.Println("\n✅ Human-in-Loop pattern demo complete!")
	fmt.Println("\nKey Takeaways:")
	fmt.Println("  - Use appropriate thresholds for your domain")
	fmt.Println("  - Critical domains (medical, financial) need human oversight")
	fmt.Println("  - Confidence-based gating provides flexibility")
	fmt.Println("  - Always validate human approval mechanisms in production")
}
