// Package main demonstrates the FallbackAgent pattern.
//
// # Sequential retry across multiple agents with automatic failover
//
// Use cases:
//   - Resilient service calls
//   - Multi-provider fallback
//   - Error recovery
//
// Run with: go run fallback_usage.go
package main

import (
	"context"
	"fmt"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
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

func (a *SimpleAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    a.Name(),
		Capabilities: a.Capabilities(),
	}
}

func (a *SimpleAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Printf("   🤖 %s processing...\n", a.name)
	time.Sleep(100 * time.Millisecond)

	result := agenkit.NewMessage("agent", fmt.Sprintf("%s processed: %s", a.name, message.Content))
	return result, nil
}

func main() {
	fmt.Println("=== FallbackAgent Demo ===")
	fmt.Println("\n✅ FallbackAgent pattern example")
	fmt.Println("\nNote: This is a minimal template.")
	fmt.Println("See examples/patterns/fallback/main.go for complete implementation.")
}
