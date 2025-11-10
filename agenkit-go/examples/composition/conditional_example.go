/*
Conditional Composition Example

WHY USE CONDITIONAL COMPOSITION?
--------------------------------
1. Intent Routing: Route to specialized agents based on request type
2. Resource Optimization: Use expensive resources only when needed
3. Domain Expertise: Leverage specialized agents for specific domains
4. Load Balancing: Distribute work based on agent capacity
5. Personalization: Route based on user preferences/tier

WHEN TO USE:
- Multi-domain systems (code, docs, customer service)
- Tiered service offerings (free, pro, enterprise)
- Language-specific routing
- Complexity-based routing (simple → fast, complex → powerful)
- User-specific routing (preferences, permissions)

WHEN NOT TO USE:
- Single domain/purpose
- All requests need same processing (use SequentialAgent)
- Want all agents to run (use ParallelAgent)
- Routing logic is trivial (simple if/else is clearer)

TRADE-OFFS:
- Routing Complexity vs Agent Specialization
- Maintenance (N agents) vs Performance (optimized per case)
- Classification accuracy vs routing speed

Run with: go run agenkit-go/examples/composition/conditional_example.go
*/

package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/composition"
)

// CodeAgent is specialized in code generation
type CodeAgent struct{}

func (a *CodeAgent) Name() string { return "code-specialist" }
func (a *CodeAgent) Capabilities() []string { return []string{"code_generation", "debugging"} }

func (a *CodeAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(200 * time.Millisecond)

	code := `func fibonacci(n int) int {
    if n <= 1 {
        return n
    }
    return fibonacci(n-1) + fibonacci(n-2)
}`

	return agenkit.NewMessage("agent", fmt.Sprintf("Here's the implementation:\n```go\n%s\n```", code)).
		WithMetadata("type", "code").
		WithMetadata("language", "go"), nil
}

// DocsAgent is specialized in documentation
type DocsAgent struct{}

func (a *DocsAgent) Name() string { return "docs-specialist" }
func (a *DocsAgent) Capabilities() []string { return []string{"documentation", "explanations"} }

func (a *DocsAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(150 * time.Millisecond)

	docs := `# Understanding Goroutines

Goroutines are lightweight threads managed by Go:

1. **go keyword**: Launches a goroutine
2. **Channels**: Communicate between goroutines
3. **Benefits**: Better than OS threads, cleaner than callbacks

Example: go processData()`

	return agenkit.NewMessage("agent", docs).
		WithMetadata("type", "documentation").
		WithMetadata("format", "markdown"), nil
}

// GeneralAgent handles other requests
type GeneralAgent struct{}

func (a *GeneralAgent) Name() string { return "general-assistant" }
func (a *GeneralAgent) Capabilities() []string { return []string{"general_qa", "conversation"} }

func (a *GeneralAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(100 * time.Millisecond)

	return agenkit.NewMessage("agent", "I'm here to help! I can answer general questions and assist with various tasks.").
		WithMetadata("type", "general"), nil
}

// Example 1: Intent-based routing
func example1IntentRouting() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 1: Intent-Based Routing")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: Multi-domain assistant with specialized agents")

	// Create router with specialized agents
	router := composition.NewConditionalAgent("multi-domain-router", &GeneralAgent{})

	// Route code requests to code agent
	router.AddRoute(
		func(msg *agenkit.Message) bool {
			lower := strings.ToLower(msg.Content)
			keywords := []string{"code", "function", "implement", "debug", "bug"}
			for _, keyword := range keywords {
				if strings.Contains(lower, keyword) {
					return true
				}
			}
			return false
		},
		&CodeAgent{},
	)

	// Route documentation requests to docs agent
	router.AddRoute(
		func(msg *agenkit.Message) bool {
			lower := strings.ToLower(msg.Content)
			keywords := []string{"explain", "document", "how does", "what is", "tutorial"}
			for _, keyword := range keywords {
				if strings.Contains(lower, keyword) {
					return true
				}
			}
			return false
		},
		&DocsAgent{},
	)

	// Test different request types
	requests := []string{
		"Write a function to calculate fibonacci",
		"Explain how goroutines work",
		"How are you today?",
	}

	ctx := context.Background()

	for _, query := range requests {
		fmt.Printf("\nQuery: %s\n", query)
		result, _ := router.Process(ctx, agenkit.NewMessage("user", query))

		fmt.Printf("Routed to: %v\n", result.Metadata["conditional_agent_used"])
		fmt.Printf("Response type: %v\n", result.Metadata["type"])
		fmt.Printf("Preview: %s\n", result.Content[:min(80, len(result.Content))])
	}

	fmt.Println("\nWHY CONDITIONAL ROUTING?")
	fmt.Println("  - Code agent: Optimized for syntax, patterns, best practices")
	fmt.Println("  - Docs agent: Optimized for clear explanations, tutorials")
	fmt.Println("  - General agent: Handles everything else")
	fmt.Println("  - Better than single agent trying to do everything")
}

// SimpleQueryAgent handles fast queries
type SimpleQueryAgent struct{}

func (a *SimpleQueryAgent) Name() string { return "simple-query-agent" }
func (a *SimpleQueryAgent) Capabilities() []string { return []string{"simple_qa"} }

func (a *SimpleQueryAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(50 * time.Millisecond)

	text := strings.ToLower(message.Content)
	var response string

	if strings.Contains(text, "weather") {
		response = "Today is sunny, 72°F."
	} else if strings.Contains(text, "time") {
		response = "It's 2:30 PM."
	} else {
		response = "Simple answer to your question."
	}

	return agenkit.NewMessage("agent", response).
		WithMetadata("complexity", "simple").
		WithMetadata("latency", 0.05).
		WithMetadata("cost", 0.0001), nil
}

// ComplexQueryAgent handles powerful queries
type ComplexQueryAgent struct{}

func (a *ComplexQueryAgent) Name() string { return "complex-query-agent" }
func (a *ComplexQueryAgent) Capabilities() []string { return []string{"complex_reasoning"} }

func (a *ComplexQueryAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(500 * time.Millisecond)

	return agenkit.NewMessage("agent", "After careful analysis considering multiple perspectives: [detailed response]").
		WithMetadata("complexity", "complex").
		WithMetadata("latency", 0.5).
		WithMetadata("cost", 0.01), nil
}

// Example 2: Complexity-based routing
func example2ComplexityRouting() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 2: Complexity-Based Routing")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: Optimize cost and latency based on query complexity")

	router := composition.NewConditionalAgent("complexity-router", &ComplexQueryAgent{})

	// Route simple queries to fast agent
	router.AddRoute(
		func(msg *agenkit.Message) bool {
			lower := strings.ToLower(msg.Content)
			// Simple queries are short and use simple words
			simplePatterns := []string{"what is", "when", "where", "who", "weather", "time"}
			for _, pattern := range simplePatterns {
				if strings.Contains(lower, pattern) {
					return true
				}
			}
			return len(strings.Fields(msg.Content)) <= 5
		},
		&SimpleQueryAgent{},
	)

	queries := []string{
		"What is the weather?",
		"Analyze the socioeconomic impacts of climate change",
		"What time is it?",
		"Compare machine learning architectures",
	}

	fmt.Println("\nProcessing queries with complexity-based routing...")

	ctx := context.Background()
	var totalCost float64
	var totalLatency float64

	for _, query := range queries {
		fmt.Printf("\nQuery: %s\n", query)
		result, _ := router.Process(ctx, agenkit.NewMessage("user", query))

		complexity := result.Metadata["complexity"]
		latency := result.Metadata["latency"].(float64)
		cost := result.Metadata["cost"].(float64)

		totalCost += cost
		totalLatency += latency

		fmt.Printf("  Complexity: %v\n", complexity)
		fmt.Printf("  Latency: %.2fs\n", latency)
		fmt.Printf("  Cost: $%.4f\n", cost)
	}

	fmt.Println("\nPerformance Summary:")
	fmt.Printf("  Total Latency: %.2fs\n", totalLatency)
	fmt.Printf("  Total Cost: $%.4f\n", totalCost)

	allComplex := 0.5 * 4
	allComplexCost := 0.01 * 4

	fmt.Println("\nWithout Routing (all complex):")
	fmt.Printf("  Total Latency: %.2fs\n", allComplex)
	fmt.Printf("  Total Cost: $%.4f\n", allComplexCost)
	fmt.Printf("\n  Savings: %.0f%% cost, %.0f%% latency\n",
		(allComplexCost-totalCost)/allComplexCost*100,
		(allComplex-totalLatency)/allComplex*100)
}

// PremiumAgent provides advanced features
type PremiumAgent struct{}

func (a *PremiumAgent) Name() string { return "premium-service" }
func (a *PremiumAgent) Capabilities() []string { return []string{"premium", "advanced"} }

func (a *PremiumAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(300 * time.Millisecond)

	return agenkit.NewMessage("agent", "Premium response with advanced analysis and priority support.").
		WithMetadata("tier", "premium").
		WithMetadata("features", []string{"advanced_analysis", "priority", "personalization"}), nil
}

// FreeAgent provides basic features
type FreeAgent struct{}

func (a *FreeAgent) Name() string { return "free-service" }
func (a *FreeAgent) Capabilities() []string { return []string{"basic"} }

func (a *FreeAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(100 * time.Millisecond)

	return agenkit.NewMessage("agent", "Basic response. Upgrade to premium for advanced features!").
		WithMetadata("tier", "free").
		WithMetadata("features", []string{"basic"}), nil
}

// Example 3: User tier routing
func example3TierRouting() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 3: User Tier Routing")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: Different service levels for free vs premium users")

	router := composition.NewConditionalAgent("tier-router", &FreeAgent{})

	// Premium users get premium service
	router.AddRoute(
		composition.MetadataEquals("user_tier", "premium"),
		&PremiumAgent{},
	)

	// Test free user
	fmt.Println("\nTest 1: Free user")
	result, _ := router.Process(context.Background(),
		agenkit.NewMessage("user", "Analyze this data").
			WithMetadata("user_tier", "free"))
	fmt.Printf("  Service: %v\n", result.Metadata["tier"])
	fmt.Printf("  Features: %v\n", result.Metadata["features"])

	// Test premium user
	fmt.Println("\nTest 2: Premium user")
	result, _ = router.Process(context.Background(),
		agenkit.NewMessage("user", "Analyze this data").
			WithMetadata("user_tier", "premium"))
	fmt.Printf("  Service: %v\n", result.Metadata["tier"])
	fmt.Printf("  Features: %v\n", result.Metadata["features"])

	fmt.Println("\nTIER-BASED ROUTING:")
	fmt.Println("  - Monetization: Premium users get better service")
	fmt.Println("  - Cost control: Free users don't use expensive resources")
	fmt.Println("  - Clear value proposition for upgrades")
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func main() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("CONDITIONAL COMPOSITION EXAMPLES FOR AGENKIT-GO")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nConditional composition routes requests to specialized agents.")
	fmt.Println("Use it for intent routing, optimization, and personalization.")

	// Run examples
	example1IntentRouting()
	example2ComplexityRouting()
	example3TierRouting()

	// Summary
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("KEY TAKEAWAYS")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println(`
1. Use conditional composition when:
   - Multiple specialized agents (code, docs, data)
   - Optimization opportunities (simple vs complex)
   - User-specific routing (tier, language, preferences)
   - Cost/performance trade-offs based on input

2. Routing strategies:
   - Intent/Domain: keyword matching, classification
   - Complexity: length, patterns, keywords
   - User attributes: tier, permissions, preferences
   - Load balancing: round-robin, least loaded

3. Condition design principles:
   - Fast: Routing should be O(1) or O(log n)
   - Accurate: Misrouting hurts user experience
   - Observable: Log routing decisions
   - Testable: Unit test each condition
   - Maintainable: Clear, documented logic

4. When NOT to use:
   - Single domain/purpose (unnecessary complexity)
   - All agents must run (use ParallelAgent)
   - Simple if/else suffices (don't over-engineer)

5. Helper functions available:
   - ContentContains: Check message content
   - MetadataEquals: Check metadata values
   - And/Or/Not: Combine conditions

REAL-WORLD USE CASES:
✓ Multi-domain: Code/docs/data specialists
✓ Optimization: Simple (fast) vs complex (thorough)
✓ Monetization: Free/pro/enterprise tiers
✓ Language: English-only vs multilingual models

TRADE-OFF SUMMARY:
✓ Pros: Specialized agents, optimization, personalization
✗ Cons: Routing complexity, maintenance burden
→ Choose when: Specialization benefits > routing cost

Next steps:
- See sequential_example.go for pipeline patterns
- See parallel_example.go for concurrent execution
- See fallback_example.go for reliability patterns
	`)
}
