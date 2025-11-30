// Package main demonstrates the HumanInLoopAgent pattern.
//
// Human approval gates for high-stakes decisions
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
	
	result := agenkit.NewMessage("agent", fmt.Sprintf("%s processed: %s", a.name, message.Content))
	return result, nil
}

func main() {
	fmt.Println("=== HumanInLoopAgent Demo ===")
	
	// Create agents
	agent1 := &SimpleAgent{name: "Agent1"}
	agent2 := &SimpleAgent{name: "Agent2"}
	agent3 := &SimpleAgent{name: "Agent3"}
	
	// Create pattern (example - adjust based on pattern type)
	// pattern := patterns.NewHumanInLoopAgent(...)
	
	fmt.Println("\n✅ HumanInLoopAgent pattern example")
	fmt.Println("\nNote: This is a minimal template.")
	fmt.Println("See Python examples for complete implementations.")
}
