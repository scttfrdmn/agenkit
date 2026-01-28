// Advanced AG-UI HITL Approval Patterns
//
// Demonstrates advanced Human-in-the-Loop patterns with custom approval logic,
// multi-stage approval, approval with modifications, and complex decision workflows.
//
// Key concepts:
//   - Multi-level approval thresholds
//   - Approval with content modifications
//   - Contextual approval decisions
//   - Custom approval UI patterns
//   - Approval audit trails
//
// This example shows:
//   - Dynamic approval thresholds
//   - Approval with modifications
//   - Multi-stage approval workflow
//   - Approval context and metadata
//   - Custom approval UI integration
//
// Usage:
//
//	go run 04_advanced_approval.go
package main

import (
	"context"
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
	"github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui"
)

// ApprovalLogEntry represents an entry in the approval audit log.
type ApprovalLogEntry struct {
	Timestamp   time.Time
	Amount      int
	Confidence  float64
	RiskLevel   string
	Decision    string
	Tier        int
	Approver    string
	Feedback    string
	Modified    bool
}

// Global approval audit log
var approvalLog []ApprovalLogEntry

// FinancialAgent is an agent that processes financial transactions.
type FinancialAgent struct {
	name string
}

func NewFinancialAgent(name string) *FinancialAgent {
	return &FinancialAgent{name: name}
}

func (f *FinancialAgent) Name() string {
	return f.name
}

func (f *FinancialAgent) Capabilities() []string {
	return []string{"finance", "transactions", "risk-assessment"}
}

func (f *FinancialAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := strings.ToLower(message.Content)

	// Extract amount
	amount := extractAmount(content)

	// Calculate confidence based on amount and type
	confidence := calculateConfidence(amount)

	// Determine transaction type
	txType := "transaction"
	if strings.Contains(content, "wire") || strings.Contains(content, "international") {
		confidence *= 0.8 // Lower confidence for wire transfers
		txType = "wire_transfer"
	} else if strings.Contains(content, "payment") {
		txType = "payment"
	}

	// Determine risk level
	riskLevel := "low"
	if amount > 25000 {
		riskLevel = "high"
	} else if amount > 5000 {
		riskLevel = "medium"
	}

	response := agenkit.NewMessage("assistant", fmt.Sprintf("Processing %s for $%s", txType, formatAmount(amount)))
	response.Metadata = map[string]interface{}{
		"confidence":       confidence,
		"amount":           amount,
		"transaction_type": txType,
		"risk_level":       riskLevel,
	}

	return response, nil
}

func (f *FinancialAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:     f.name,
		Capabilities:  f.Capabilities(),
		InternalState: make(map[string]interface{}),
		Metadata:      make(map[string]interface{}),
	}
}

// extractAmount extracts the dollar amount from text.
func extractAmount(text string) int {
	// Match $X,XXX or $XXX patterns
	re := regexp.MustCompile(`\$([0-9,]+)`)
	matches := re.FindStringSubmatch(text)
	if len(matches) > 1 {
		amountStr := strings.ReplaceAll(matches[1], ",", "")
		if amount, err := strconv.Atoi(amountStr); err == nil {
			return amount
		}
	}
	return 1000 // Default
}

// calculateConfidence calculates confidence based on amount.
func calculateConfidence(amount int) float64 {
	if amount < 1000 {
		return 0.95
	} else if amount < 10000 {
		return 0.85
	} else if amount < 50000 {
		return 0.7
	}
	return 0.4
}

// formatAmount formats an amount with comma separators.
func formatAmount(amount int) string {
	s := strconv.Itoa(amount)
	n := len(s)
	if n <= 3 {
		return s
	}

	// Add commas
	var result strings.Builder
	for i, digit := range s {
		if i > 0 && (n-i)%3 == 0 {
			result.WriteRune(',')
		}
		result.WriteRune(digit)
	}
	return result.String()
}

// tieredApprovalFunc implements multi-tiered approval based on amount and risk.
//
// Approval tiers:
//   - < $1,000: Auto-approve
//   - $1,000 - $10,000: Manager approval
//   - $10,000 - $50,000: Director approval
//   - > $50,000: Executive approval + modifications
func tieredApprovalFunc(ctx context.Context, request *patterns.ApprovalRequest) (*patterns.ApprovalResponse, error) {
	amount := 0
	if amt, ok := request.Message.Metadata["amount"].(int); ok {
		amount = amt
	}

	confidence := request.Confidence

	riskLevel := "unknown"
	if risk, ok := request.Message.Metadata["risk_level"].(string); ok {
		riskLevel = risk
	}

	fmt.Println("\n============================================================")
	fmt.Println("Tiered Approval Request")
	fmt.Println("============================================================")
	fmt.Printf("Amount:      $%s\n", formatAmount(amount))
	fmt.Printf("Confidence:  %.2f\n", confidence)
	fmt.Printf("Risk Level:  %s\n", riskLevel)

	// Create log entry
	logEntry := ApprovalLogEntry{
		Timestamp:  time.Now(),
		Amount:     amount,
		Confidence: confidence,
		RiskLevel:  riskLevel,
	}

	// Simulate review time
	time.Sleep(200 * time.Millisecond)

	if amount < 1000 {
		fmt.Println("✓ Auto-approved (Tier 0: < $1,000)")
		logEntry.Decision = "auto_approved"
		logEntry.Tier = 0
		logEntry.Approver = "System"
		logEntry.Feedback = "Auto-approved"
		approvalLog = append(approvalLog, logEntry)

		return &patterns.ApprovalResponse{
			Approved: true,
			Feedback: "Auto-approved",
		}, nil

	} else if amount < 10000 {
		fmt.Println("✓ Manager approved (Tier 1: $1K-$10K)")
		logEntry.Decision = "manager_approved"
		logEntry.Tier = 1
		logEntry.Approver = "Manager"
		logEntry.Feedback = "Approved by Manager"
		approvalLog = append(approvalLog, logEntry)

		return &patterns.ApprovalResponse{
			Approved: true,
			Feedback: "Approved by Manager",
		}, nil

	} else if amount < 50000 {
		fmt.Println("✓ Director approved (Tier 2: $10K-$50K)")
		logEntry.Decision = "director_approved"
		logEntry.Tier = 2
		logEntry.Approver = "Director"
		logEntry.Feedback = "Approved by Director"
		approvalLog = append(approvalLog, logEntry)

		return &patterns.ApprovalResponse{
			Approved: true,
			Feedback: "Approved by Director",
		}, nil

	} else {
		// High-value transaction: Executive approval with modifications
		fmt.Println("⚠️  Executive review required (Tier 3: > $50K)")
		fmt.Println("   → Adding compliance review requirement")

		logEntry.Decision = "executive_approved_modified"
		logEntry.Tier = 3
		logEntry.Approver = "Executive"
		logEntry.Feedback = "Executive approval with compliance review"
		logEntry.Modified = true
		approvalLog = append(approvalLog, logEntry)

		// Modify the message to add compliance requirement
		originalContent := request.Message.Content
		modifiedContent := originalContent + " [REQUIRES COMPLIANCE REVIEW]"

		modifiedMessage := agenkit.NewMessage(request.Message.Role, modifiedContent)
		modifiedMessage.Metadata = make(map[string]interface{})
		for k, v := range request.Message.Metadata {
			modifiedMessage.Metadata[k] = v
		}
		modifiedMessage.Metadata["compliance_review_required"] = true
		modifiedMessage.Metadata["executive_approved"] = true

		return &patterns.ApprovalResponse{
			Approved:        true,
			Feedback:        "Executive approval granted with compliance review requirement",
			ModifiedMessage: modifiedMessage,
		}, nil
	}
}

// contextualApprovalFunc implements contextual approval based on risk and timing.
func contextualApprovalFunc(ctx context.Context, request *patterns.ApprovalRequest) (*patterns.ApprovalResponse, error) {
	amount := 0
	if amt, ok := request.Message.Metadata["amount"].(int); ok {
		amount = amt
	}

	confidence := request.Confidence

	riskLevel := "unknown"
	if risk, ok := request.Message.Metadata["risk_level"].(string); ok {
		riskLevel = risk
	}

	txType := "unknown"
	if tx, ok := request.Message.Metadata["transaction_type"].(string); ok {
		txType = tx
	}

	fmt.Println("\n============================================================")
	fmt.Println("Contextual Approval Request")
	fmt.Println("============================================================")
	fmt.Printf("Amount:       $%s\n", formatAmount(amount))
	fmt.Printf("Type:         %s\n", txType)
	fmt.Printf("Risk Level:   %s\n", riskLevel)
	fmt.Printf("Confidence:   %.2f\n", confidence)
	fmt.Printf("Time:         %s\n", time.Now().Format("15:04:05 MST"))

	// Check if it's business hours (9 AM - 5 PM)
	hour := time.Now().Hour()
	businessHours := hour >= 9 && hour < 17

	// Contextual decision logic
	time.Sleep(200 * time.Millisecond)

	// Wire transfers require extra scrutiny
	if txType == "wire_transfer" {
		if !businessHours {
			fmt.Println("❌ REJECTED: Wire transfers not allowed outside business hours")
			return &patterns.ApprovalResponse{
				Approved: false,
				Feedback: "Wire transfers must be processed during business hours (9 AM - 5 PM)",
			}, nil
		}
		if riskLevel == "high" {
			fmt.Println("⚠️  APPROVED WITH CONDITIONS: High-risk wire transfer")
			return &patterns.ApprovalResponse{
				Approved: true,
				Feedback: "Approved with enhanced monitoring and dual authorization required",
			}, nil
		}
	}

	// High-risk transactions
	if riskLevel == "high" {
		if confidence < 0.5 {
			fmt.Println("❌ REJECTED: High risk + low confidence")
			return &patterns.ApprovalResponse{
				Approved: false,
				Feedback: "Insufficient confidence for high-risk transaction",
			}, nil
		}
		fmt.Println("✓ APPROVED: High-risk transaction with acceptable confidence")
		return &patterns.ApprovalResponse{
			Approved: true,
			Feedback: fmt.Sprintf("Approved high-risk transaction (confidence: %.2f)", confidence),
		}, nil
	}

	// Default approval
	fmt.Println("✓ APPROVED: Standard approval")
	return &patterns.ApprovalResponse{
		Approved: true,
		Feedback: "Standard approval granted",
	}, nil
}

// Example 1: Tiered approval workflow
func exampleTieredApproval() {
	fmt.Println("==============================================================")
	fmt.Println("Example 1: Tiered Approval Workflow")
	fmt.Println("==============================================================")

	agent := NewFinancialAgent("FinancialAgent")

	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             agent,
		ApprovalFunc:      tieredApprovalFunc,
		ApprovalThreshold: 0.8,
	})
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	adapter := agui.NewAGUIHumanInLoopAdapter(hilAgent, "TieredApproval", true)

	// Test different amounts
	testCases := []struct {
		description string
		message     string
		expectedTier int
	}{
		{"Small transaction", "Process payment of $500", 0},
		{"Medium transaction", "Process payment of $5,000", 1},
		{"Large transaction", "Process payment of $25,000", 2},
		{"Very large transaction", "Process wire transfer of $75,000", 3},
	}

	for _, tc := range testCases {
		fmt.Printf("\n📝 Test: %s\n", tc.description)
		fmt.Printf("   Message: %s\n", tc.message)

		message := agenkit.NewMessage("user", tc.message)
		ctx := context.Background()

		interruptFound := false
		for event := range adapter.StreamEvents(ctx, message) {
			if interrupt, ok := event.(*agui.Interrupt); ok {
				interruptFound = true
				fmt.Printf("\n   🚨 Interrupt Event:\n")
				fmt.Printf("      Status: %v\n", interrupt.Context["approval_status"])
				fmt.Printf("      Confidence: %.2f\n", interrupt.Context["confidence"].(float64))
			}
		}

		if !interruptFound {
			fmt.Println("   ✓ No approval needed (high confidence)")
		}
	}
}

// Example 2: Contextual approval
func exampleContextualApproval() {
	fmt.Println("\n\n==============================================================")
	fmt.Println("Example 2: Contextual Approval (Risk & Timing)")
	fmt.Println("==============================================================")

	agent := NewFinancialAgent("FinancialAgent")

	hilAgent, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             agent,
		ApprovalFunc:      contextualApprovalFunc,
		ApprovalThreshold: 0.8,
	})
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	adapter := agui.NewAGUIHumanInLoopAdapter(hilAgent, "ContextualApproval", true)

	testCases := []string{
		"Process wire transfer of $30,000",
		"Process payment of $50,000",
		"Process international wire of $100,000",
	}

	for _, tc := range testCases {
		fmt.Printf("\n📝 Test: %s\n", tc)

		message := agenkit.NewMessage("user", tc)
		ctx := context.Background()

		for event := range adapter.StreamEvents(ctx, message) {
			if interrupt, ok := event.(*agui.Interrupt); ok {
				fmt.Printf("   🚨 Decision: %v\n", interrupt.Context["approval_status"])
			}
		}
	}
}

// Example 3: Approval audit trail
func exampleAuditTrail() {
	fmt.Println("\n\n==============================================================")
	fmt.Println("Example 3: Approval Audit Trail")
	fmt.Println("==============================================================")

	if len(approvalLog) == 0 {
		fmt.Println("No approvals logged yet")
		return
	}

	fmt.Println("Approval History:")
	fmt.Println("─────────────────────────────────────────────────────────────")

	for i, entry := range approvalLog {
		fmt.Printf("\n%d. %s\n", i+1, entry.Timestamp.Format("2006-01-02 15:04:05"))
		fmt.Printf("   Amount:      $%s\n", formatAmount(entry.Amount))
		fmt.Printf("   Risk Level:  %s\n", entry.RiskLevel)
		fmt.Printf("   Confidence:  %.2f\n", entry.Confidence)
		fmt.Printf("   Tier:        %d (%s)\n", entry.Tier, entry.Approver)
		fmt.Printf("   Decision:    %s\n", entry.Decision)
		fmt.Printf("   Modified:    %v\n", entry.Modified)
		if entry.Feedback != "" {
			fmt.Printf("   Feedback:    %s\n", entry.Feedback)
		}
	}

	// Summary statistics
	fmt.Println("\n─────────────────────────────────────────────────────────────")
	fmt.Println("Summary Statistics:")
	fmt.Printf("   Total Approvals: %d\n", len(approvalLog))

	tierCounts := make(map[int]int)
	totalAmount := 0
	modifiedCount := 0

	for _, entry := range approvalLog {
		tierCounts[entry.Tier]++
		totalAmount += entry.Amount
		if entry.Modified {
			modifiedCount++
		}
	}

	fmt.Printf("   Total Amount:    $%s\n", formatAmount(totalAmount))
	fmt.Printf("   Modified:        %d\n", modifiedCount)
	fmt.Println("\n   Approvals by Tier:")
	for tier := 0; tier <= 3; tier++ {
		if count, ok := tierCounts[tier]; ok {
			fmt.Printf("      Tier %d: %d\n", tier, count)
		}
	}
}

func main() {
	fmt.Println("AG-UI Advanced Approval Patterns Examples")
	fmt.Println()

	// Initialize approval log
	approvalLog = []ApprovalLogEntry{}

	// Run examples
	exampleTieredApproval()
	exampleContextualApproval()
	exampleAuditTrail()

	fmt.Println("\n\n==============================================================")
	fmt.Println("✅ All examples completed successfully!")
	fmt.Println("==============================================================")
}
