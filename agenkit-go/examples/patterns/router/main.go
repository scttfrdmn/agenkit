// Package main demonstrates the Router pattern for conditional routing.
//
// The Router pattern classifies incoming messages and routes them to
// appropriate specialist agents based on intent, category, or other
// classification criteria.
//
// This example shows:
//   - Intent classification and routing
//   - Multiple routing strategies (keyword-based, LLM-based)
//   - Handling unknown intents with defaults
//   - Building customer service routing systems
//
// Run with: go run router_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// BillingAgent handles billing inquiries
type BillingAgent struct{}

func (b *BillingAgent) Name() string {
	return "BillingSpecialist"
}

func (b *BillingAgent) Capabilities() []string {
	return []string{"billing", "payments", "invoices"}
}

func (b *BillingAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    b.Name(),
		Capabilities: b.Capabilities(),
	}
}

func (b *BillingAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   💰 Billing specialist handling request...")

	response := fmt.Sprintf("Billing Department Response:\n\nRegarding your inquiry: '%s'\n\n"+
		"I can help you with:\n"+
		"- Invoice questions\n"+
		"- Payment processing\n"+
		"- Billing disputes\n"+
		"- Subscription changes\n\n"+
		"Please provide your account number for assistance.",
		message.Content)

	return agenkit.NewMessage("agent", response), nil
}

// TechnicalAgent handles technical support
type TechnicalAgent struct{}

func (t *TechnicalAgent) Name() string {
	return "TechnicalSupport"
}

func (t *TechnicalAgent) Capabilities() []string {
	return []string{"technical", "support", "troubleshooting"}
}

func (t *TechnicalAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    t.Name(),
		Capabilities: t.Capabilities(),
	}
}

func (t *TechnicalAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   🔧 Technical support handling request...")

	response := fmt.Sprintf("Technical Support Response:\n\nRegarding your issue: '%s'\n\n"+
		"I can help you with:\n"+
		"- Technical troubleshooting\n"+
		"- Software configuration\n"+
		"- Error resolution\n"+
		"- System optimization\n\n"+
		"Let's diagnose the problem together.",
		message.Content)

	return agenkit.NewMessage("agent", response), nil
}

// AccountAgent handles account management
type AccountAgent struct{}

func (a *AccountAgent) Name() string {
	return "AccountManager"
}

func (a *AccountAgent) Capabilities() []string {
	return []string{"account", "profile", "settings"}
}

func (a *AccountAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    a.Name(),
		Capabilities: a.Capabilities(),
	}
}

func (a *AccountAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   👤 Account manager handling request...")

	response := fmt.Sprintf("Account Management Response:\n\nRegarding your account: '%s'\n\n"+
		"I can help you with:\n"+
		"- Profile updates\n"+
		"- Security settings\n"+
		"- Account preferences\n"+
		"- Data management\n\n"+
		"How can I assist with your account today?",
		message.Content)

	return agenkit.NewMessage("agent", response), nil
}

// GeneralAgent handles general inquiries
type GeneralAgent struct{}

func (g *GeneralAgent) Name() string {
	return "GeneralInquiries"
}

func (g *GeneralAgent) Capabilities() []string {
	return []string{"general", "information"}
}

func (g *GeneralAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    g.Name(),
		Capabilities: g.Capabilities(),
	}
}

func (g *GeneralAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   ℹ️  General inquiries handling request...")

	response := fmt.Sprintf("General Inquiries Response:\n\nThank you for contacting us: '%s'\n\n"+
		"I can help you with:\n"+
		"- General information\n"+
		"- Product inquiries\n"+
		"- Service overview\n"+
		"- Routing to specialists\n\n"+
		"How may I assist you today?",
		message.Content)

	return agenkit.NewMessage("agent", response), nil
}

// MockLLMAgent simulates an LLM for classification
type MockLLMAgent struct{}

func (m *MockLLMAgent) Name() string {
	return "MockLLM"
}

func (m *MockLLMAgent) Capabilities() []string {
	return []string{"classification", "llm"}
}

func (m *MockLLMAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *MockLLMAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simple classification based on content
	content := strings.ToLower(message.Content)

	category := "general"
	if strings.Contains(content, "classify") {
		// Extract category from classification prompt
		if strings.Contains(content, "billing") {
			category = "billing"
		} else if strings.Contains(content, "technical") {
			category = "technical"
		} else if strings.Contains(content, "account") {
			category = "account"
		}
	}

	return agenkit.NewMessage("assistant", category), nil
}

func main() {
	fmt.Println("=== Router Pattern Demo ===")
	fmt.Println("Demonstrating intelligent request routing")

	ctx := context.Background()

	// Create specialist agents
	billing := &BillingAgent{}
	technical := &TechnicalAgent{}
	account := &AccountAgent{}
	general := &GeneralAgent{}

	// Example 1: Keyword-based classification
	fmt.Println("📊 Example 1: Keyword-Based Routing")
	fmt.Println(strings.Repeat("-", 50))

	keywordClassifier := patterns.NewSimpleClassifier(
		&MockLLMAgent{},
		map[string][]string{
			"billing":   {"invoice", "payment", "bill", "charge", "subscription"},
			"technical": {"error", "bug", "not working", "broken", "crash"},
			"account":   {"password", "login", "profile", "settings", "update"},
			"general":   {"information", "question", "help", "about"},
		},
	)

	router, err := patterns.NewRouterAgent(&patterns.RouterConfig{
		Classifier: keywordClassifier,
		Agents: map[string]agenkit.Agent{
			"billing":   billing,
			"technical": technical,
			"account":   account,
			"general":   general,
		},
		DefaultKey: "general",
	})
	if err != nil {
		log.Fatalf("Failed to create router: %v", err)
	}

	// Test different request types
	testRequests := []string{
		"I have a question about my invoice",
		"The app keeps crashing on startup",
		"How do I reset my password?",
		"What are your business hours?",
	}

	for i, req := range testRequests {
		fmt.Printf("\nRequest %d: %s\n", i+1, req)

		message := agenkit.NewMessage("user", req)
		result, err := router.Process(ctx, message)
		if err != nil {
			log.Printf("Routing failed: %v", err)
			continue
		}

		if category, ok := result.Metadata["routed_category"].(string); ok {
			fmt.Printf("   → Routed to: %s\n", category)
		}
		if agent, ok := result.Metadata["routed_agent"].(string); ok {
			fmt.Printf("   → Agent: %s\n", agent)
		}
	}

	// Example 2: LLM-based classification
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 2: LLM-Based Classification")
	fmt.Println(strings.Repeat("-", 50))

	llmClassifier := patterns.NewLLMClassifier(
		&MockLLMAgent{},
		[]string{"billing", "technical", "account", "general"},
	)

	llmRouter, err := patterns.NewRouterAgent(&patterns.RouterConfig{
		Classifier: llmClassifier,
		Agents: map[string]agenkit.Agent{
			"billing":   billing,
			"technical": technical,
			"account":   account,
			"general":   general,
		},
	})
	if err != nil {
		log.Fatalf("Failed to create LLM router: %v", err)
	}

	complexRequest := agenkit.NewMessage("user",
		"I'm having trouble accessing my account after making a payment. The system shows an error.")

	fmt.Printf("\nComplex request: %s\n", complexRequest.Content)

	result, err := llmRouter.Process(ctx, complexRequest)
	if err != nil {
		log.Fatalf("LLM routing failed: %v", err)
	}

	if category, ok := result.Metadata["routed_category"].(string); ok {
		fmt.Printf("\n   → Classified as: %s\n", category)
	}

	fmt.Printf("\n📤 Response preview:\n%s\n",
		truncate(result.Content, 150))

	// Example 3: Handling unknown categories with default
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 3: Default Routing")
	fmt.Println(strings.Repeat("-", 50))

	unknownRequest := agenkit.NewMessage("user",
		"Can you tell me about your company?")

	fmt.Printf("\nUnknown category request: %s\n", unknownRequest.Content)

	result, err = router.Process(ctx, unknownRequest)
	if err != nil {
		log.Fatalf("Should have used default: %v", err)
	}

	if category, ok := result.Metadata["routed_category"].(string); ok {
		fmt.Printf("   → Routed to default: %s\n", category)
	}

	// Example 4: Router without default (strict mode)
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 4: Strict Routing (No Default)")
	fmt.Println(strings.Repeat("-", 50))

	strictRouter, err := patterns.NewRouterAgent(&patterns.RouterConfig{
		Classifier: keywordClassifier,
		Agents: map[string]agenkit.Agent{
			"billing":   billing,
			"technical": technical,
		},
		// No default key - will error on unknown categories
	})
	if err != nil {
		log.Fatalf("Failed to create strict router: %v", err)
	}

	ambiguousRequest := agenkit.NewMessage("user", "Hello, I need help")

	fmt.Printf("\nAmbiguous request: %s\n", ambiguousRequest.Content)

	_, err = strictRouter.Process(ctx, ambiguousRequest)
	if err != nil {
		fmt.Printf("   ✓ Correctly rejected: %v\n", err)
	}

	// Example 5: Multi-level routing
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 5: Multi-Level Routing")
	fmt.Println(strings.Repeat("-", 50))

	// Create a sub-router for technical issues
	techKeywords := map[string][]string{
		"software": {"app", "software", "program", "install"},
		"hardware": {"device", "hardware", "screen", "keyboard"},
	}

	techSubRouter, err := patterns.NewRouterAgent(&patterns.RouterConfig{
		Classifier: patterns.NewSimpleClassifier(&MockLLMAgent{}, techKeywords),
		Agents: map[string]agenkit.Agent{
			"software": technical,
			"hardware": technical,
		},
		DefaultKey: "software",
	})
	if err != nil {
		log.Fatalf("Failed to create tech sub-router: %v", err)
	}

	multiRouter, err := patterns.NewRouterAgent(&patterns.RouterConfig{
		Classifier: keywordClassifier,
		Agents: map[string]agenkit.Agent{
			"billing":   billing,
			"technical": techSubRouter, // Nested router
			"account":   account,
			"general":   general,
		},
	})
	if err != nil {
		log.Fatalf("Failed to create multi-level router: %v", err)
	}

	techRequest := agenkit.NewMessage("user", "My keyboard is not working properly")

	fmt.Printf("\nNested routing request: %s\n", techRequest.Content)
	fmt.Println("   Level 1: Main router → technical")
	fmt.Println("   Level 2: Tech sub-router → hardware specialist")

	_, err = multiRouter.Process(ctx, techRequest)
	if err != nil {
		log.Fatalf("Multi-level routing failed: %v", err)
	}

	fmt.Printf("\n📤 Routed successfully through nested routers\n")

	fmt.Println("\n✅ Router pattern demo complete!")
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}
