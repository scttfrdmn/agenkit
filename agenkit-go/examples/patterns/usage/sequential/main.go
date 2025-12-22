// Package main demonstrates the SequentialAgent pattern.
//
// # Pipeline-style agent composition where each agent's output feeds the next
//
// Use cases:
//   - Multi-stage data transformation
//   - Document processing
//   - Step-by-step refinement
//
// Run with: go run sequential_usage.go
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

func (a *SimpleAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Printf("   🤖 %s processing...\n", a.name)
	time.Sleep(100 * time.Millisecond)

	result := agenkit.NewMessage("agent", fmt.Sprintf("%s processed: %s", a.name, message.Content))
	return result, nil
}

func main() {
	fmt.Println("=== SequentialAgent Demo ===")

	// Example agents would be created here
	// agent1 := &SimpleAgent{name: "Agent1"}
	// agent2 := &SimpleAgent{name: "Agent2"}
	// agent3 := &SimpleAgent{name: "Agent3"}

	// Create pattern (example - adjust based on pattern type)
	// pattern := patterns.NewSequentialAgent(...)

	fmt.Println("\n✅ SequentialAgent pattern example")
	fmt.Println("\nNote: This is a minimal template.")
	fmt.Println("See Python examples for complete implementations.")
}
